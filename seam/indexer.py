from __future__ import annotations

import fnmatch
import hashlib
import os
import subprocess
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


def load_seamignore(repo_path: Path) -> list[str]:
    ignore_file = repo_path / ".seamignore"
    if not ignore_file.exists():
        return []
    patterns: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def is_ignored_by_patterns(relative_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if fnmatch.fnmatch(relative_path, normalized) or fnmatch.fnmatch(relative_path, f"{normalized}/**"):
            return True
    return False


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


def current_branch(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    branch = result.stdout.strip()
    return branch or None


def iter_indexable_files(repo_path: Path, scope: Path | None = None) -> Iterator[Path]:
    seamignore = load_seamignore(repo_path)
    scope = scope.resolve() if scope is not None else None
    roots = [scope if scope.is_dir() else scope.parent] if scope else [repo_path]
    for walk_root in roots:
        for root, dirs, files in os.walk(walk_root):
            root_path = Path(root)
            kept_dirs = []
            for directory in dirs:
                dir_path = root_path / directory
                relative_dir = dir_path.relative_to(repo_path).as_posix()
                if directory in IGNORE_DIRS or directory.startswith(".seam") or is_ignored_by_patterns(relative_dir, seamignore):
                    continue
                kept_dirs.append(directory)
            dirs[:] = kept_dirs
            for filename in files:
                if filename in IGNORE_FILES:
                    continue
                path = root_path / filename
                if scope and scope.is_file() and path.resolve() != scope:
                    continue
                relative_path = path.relative_to(repo_path).as_posix()
                if is_ignored_by_patterns(relative_path, seamignore):
                    continue
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


def index_repo(path: Path, *, force: bool = False, config: SeamConfig | None = None, scope: Path | None = None) -> IndexStats:
    repo_path = path.expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")
    scope_path = scope.expanduser().resolve() if scope is not None else None
    if scope_path is not None and not scope_path.is_relative_to(repo_path):
        raise ValueError("scope must be inside the repository path")

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
    updated_file_paths: list[str] = []

    for file_path in iter_indexable_files(repo_path, scope=scope_path):
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
        updated_file_paths.append(relative_path)

    deleted_files = 0
    deleted_file_paths: list[str] = []
    scoped_known_paths = set(known_hashes)
    if scope_path is not None:
        relative_scope = scope_path.relative_to(repo_path).as_posix()
        if scope_path.is_file():
            scoped_known_paths = {relative_scope} if relative_scope in known_hashes else set()
        else:
            scoped_known_paths = {path for path in known_hashes if path == relative_scope or path.startswith(f"{relative_scope}/")}
    for known_path in scoped_known_paths - seen_paths:
        store.delete_file(known_path)
        deleted_files += 1
        deleted_file_paths.append(known_path)

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
    branch = current_branch(repo_path)
    store.set_meta("last_indexed_at", last_indexed_at)
    store.set_meta("branch", branch)
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
        updated_file_paths=updated_file_paths,
        deleted_file_paths=deleted_file_paths,
        branch=branch,
    )


def index_status(path: Path | None = None) -> IndexStats:
    from .config import resolve_repo

    config = load_config()
    entry = resolve_repo(path)
    index_path = Path(entry["index_path"])
    repo_path = Path(entry["path"])
    store = create_store(index_path, config.backend, config)
    files, chunks = store.counts()
    meta = store.all_meta()
    known_hashes = store.file_hashes()
    current_hashes: dict[str, str] = {}
    for file_path in iter_indexable_files(repo_path):
        relative_path = file_path.relative_to(repo_path).as_posix()
        try:
            current_hashes[relative_path] = file_sha256(file_path)
        except OSError:
            continue
    updated_file_paths = sorted(path for path, content_hash in current_hashes.items() if known_hashes.get(path) != content_hash)
    deleted_file_paths = sorted(set(known_hashes) - set(current_hashes))
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
        updated_files=len(updated_file_paths),
        deleted_files=len(deleted_file_paths),
        updated_file_paths=updated_file_paths,
        deleted_file_paths=deleted_file_paths,
        branch=current_branch(repo_path) or meta.get("branch"),
    )


def index_size(path: Path | None = None) -> int:
    from .config import resolve_repo

    entry = resolve_repo(path)
    root = Path(entry["index_path"])
    if not root.exists():
        return 0
    return sum(file.stat().st_size for file in root.rglob("*") if file.is_file())


def gc_index(path: Path | None = None) -> list[str]:
    from .config import resolve_repo

    config = load_config()
    entry = resolve_repo(path)
    store = create_store(Path(entry["index_path"]), config.backend, config)
    return store.gc_missing_files(Path(entry["path"]))


def force_reindex(path: Path) -> IndexStats:
    return index_repo(path, force=True)
