from __future__ import annotations

from pathlib import Path

from .config import load_config, resolve_repo
from .embeddings import create_embedder
from .models import SearchResult
from .storage import create_store


def search_code(query: str, *, top_k: int = 5, path: Path | None = None, language: str | None = None) -> list[SearchResult]:
    config = load_config()
    entry = resolve_repo(path)
    store = create_store(Path(entry["index_path"]), config.backend, config)
    embedder = create_embedder(config)
    query_vector = embedder.embed(query)
    return store.search(query_vector, query, top_k=top_k, language=language, hybrid=config.hybrid_search)


def list_indexed_files(pattern: str = "*", *, path: Path | None = None) -> list[dict[str, object]]:
    config = load_config()
    entry = resolve_repo(path)
    store = create_store(Path(entry["index_path"]), config.backend, config)
    return store.list_files(pattern)


def get_chunk(file_path: str, start_line: int, end_line: int, *, path: Path | None = None) -> str:
    config = load_config()
    entry = resolve_repo(path)
    repo_path = Path(entry["path"])
    target = (repo_path / file_path).resolve()
    if not str(target).startswith(str(repo_path.resolve())):
        raise ValueError("file_path must stay inside the indexed repository")
    if target.exists():
        lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[start_line - 1 : end_line]).rstrip() + "\n"

    store = create_store(Path(entry["index_path"]), config.backend, config)
    snippet = store.get_stored_chunk(file_path, start_line, end_line)
    if snippet is None:
        raise FileNotFoundError(f"No chunk found for {file_path}:{start_line}-{end_line}")
    return snippet
