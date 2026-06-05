from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .chunker import chunk_text, detect_language, is_supported_text
from .config import SeamConfig, index_path_for, load_config, register_repo, repo_id_for
from .embeddings import create_embedder
from .models import IndexStats, utc_now_iso
from .storage import create_store

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".seam",
    "dist",
    "build",
    "target",
    ".next",
    ".turbo",
    "coverage",
}
IGNORE_FILES = {".DS_Store"}
MAX_FILE_BYTES = 1_500_000


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compute_merkle_tree(file_hashes: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Build a deterministic SHA-256 Merkle tree from relative file hashes."""
    root: dict[str, Any] = {}
    for relative_path, content_hash in sorted(file_hashes.items()):
        cursor = root
        parts = [part for part in relative_path.split("/") if part]
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        if parts:
            cursor[parts[-1]] = content_hash

    nodes: dict[str, str] = {}

    def digest_node(node: dict[str, Any] | str, prefix: str) -> str:
        if isinstance(node, str):
            value = hashlib.sha256(f"blob\0{prefix}\0{node}".encode()).hexdigest()
            nodes[prefix] = value
            return value

        child_entries: list[str] = []
        for name, child in sorted(node.items()):
            child_prefix = name if prefix == "." else f"{prefix}/{name}"
            child_hash = digest_node(child, child_prefix)
            child_entries.append(f"{name}\0{child_hash}")
        payload = "\n".join(child_entries)
        value = hashlib.sha256(f"tree\0{prefix}\0{payload}".encode()).hexdigest()
        nodes[prefix] = value
        return value

    return digest_node(root, "."), nodes


def iter_indexable_files(repo_path: Path) -> Iterator[Path]:
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [directory for directory in dirs if directory not in IGNORE_DIRS and not directory.startswith(".seam")]
        root_path = Path(root)
        for filename in files:
            if filename in IGNORE_FILES:
                continue
            path = root_path / filename
            if not is_supported_text(path):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
    except OSError:
        return None


def index_repo(path: Path, *, force: bool = False, config: SeamConfig | None = None) -> IndexStats:
    repo_path = path.expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")

    config = config or load_config()
    store = create_store(index_path_for(repo_path), config.backend, config)
    embedder = create_embedder(config)

    warnings: list[str] = []
    existing_provider = store.get_meta("embedding_provider")
    existing_model = store.get_meta("embedding_model")
    existing_backend = store.get_meta("backend")
    if existing_backend and existing_backend != config.backend:
        warnings.append(f"Backend changed from {existing_backend} to {config.backend}; rebuilding index metadata.")
        force = True
    if existing_provider and existing_model and (existing_provider != embedder.name or existing_model != embedder.model):
        warnings.append(
            f"Embedding model changed from {existing_provider}/{existing_model} to {embedder.name}/{embedder.model}; rebuilding index."
        )
        force = True

    if force:
        store.clear()

    known_hashes = store.file_hashes()
    seen_paths: set[str] = set()
    updated_files = 0
    skipped_files = 0

    for file_path in iter_indexable_files(repo_path):
        relative_path = file_path.relative_to(repo_path).as_posix()
        seen_paths.add(relative_path)
        try:
            stat = file_path.stat()
            content_hash = file_sha256(file_path)
        except OSError:
            continue

        if not force and known_hashes.get(relative_path) == content_hash:
            skipped_files += 1
            continue

        text = read_text(file_path)
        if text is None:
            continue
        language = detect_language(file_path)
        chunks = chunk_text(relative_path, text, language)
        snippets = [chunk.snippet for chunk in chunks]
        embeddings = embedder.embed_many(snippets) if snippets else []

        store.delete_chunks_for_file(relative_path)
        store.upsert_file(
            relative_path,
            language=language,
            content_hash=content_hash,
            size=stat.st_size,
            mtime=stat.st_mtime,
        )
        if chunks:
            store.upsert_chunks(chunks, embeddings)
        updated_files += 1

    deleted_files = 0
    for known_path in set(known_hashes) - seen_paths:
        store.delete_file(known_path)
        deleted_files += 1

    final_hashes = store.file_hashes()
    tree_hash, merkle_nodes = compute_merkle_tree(final_hashes)

    last_indexed_at = utc_now_iso()
    repo_id = repo_id_for(repo_path)
    store.set_meta("repo_id", repo_id)
    store.set_meta("repo_path", str(repo_path))
    store.set_meta("backend", config.backend)
    store.set_meta("embedding_provider", embedder.name)
    store.set_meta("embedding_model", embedder.model)
    store.set_meta("merkle_root", tree_hash)
    store.set_meta("merkle_nodes", merkle_nodes)
    store.set_meta("last_indexed_at", last_indexed_at)
    register_repo(repo_path, last_indexed_at=last_indexed_at)

    files, chunks = store.counts()
    return IndexStats(
        repo_id=repo_id,
        repo_path=str(repo_path),
        index_path=str(index_path_for(repo_path)),
        backend=config.backend,
        embedding_provider=embedder.name,
        embedding_model=embedder.model,
        files=files,
        chunks=chunks,
        last_indexed_at=last_indexed_at,
        updated_files=updated_files,
        deleted_files=deleted_files,
        skipped_files=skipped_files,
        languages=store.language_counts(),
        tree_hash=tree_hash,
        warnings=warnings,
    )


def index_status(path: Path | None = None) -> IndexStats:
    from .config import resolve_repo

    config = load_config()
    entry = resolve_repo(path)
    index_path = Path(entry["index_path"])
    store = create_store(index_path, config.backend, config)
    files, chunks = store.counts()
    meta = store.all_meta()
    return IndexStats(
        repo_id=meta.get("repo_id", entry["id"]),
        repo_path=meta.get("repo_path", entry["path"]),
        index_path=str(index_path),
        backend=meta.get("backend", config.backend),
        embedding_provider=meta.get("embedding_provider", config.embedding_provider),
        embedding_model=meta.get("embedding_model", config.embedding_model),
        files=files,
        chunks=chunks,
        last_indexed_at=meta.get("last_indexed_at", entry.get("last_indexed_at")),
        languages=store.language_counts(),
        tree_hash=meta.get("merkle_root"),
    )


def force_reindex(path: Path) -> IndexStats:
    return index_repo(path, force=True)
