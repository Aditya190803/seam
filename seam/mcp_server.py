from __future__ import annotations

from pathlib import Path
from typing import Any

from .indexer import index_status as seam_index_status
from .search import get_chunk as seam_get_chunk
from .search import list_indexed_files
from .search import search_code as seam_search_code


def create_mcp_server():  # type: ignore[no-untyped-def]
    try:
        from fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("fastmcp is required to run 'seam serve'") from exc

    mcp = FastMCP("Seam")

    @mcp.tool
    def search_code(query: str, top_k: int = 5, repo_path: str | None = None, language: str | None = None) -> list[dict[str, Any]]:
        """Semantically search the indexed codebase. Use this before reading files to find the right location first."""
        path = Path(repo_path) if repo_path else None
        return [result.to_dict() for result in seam_search_code(query, top_k=top_k, path=path, language=language)]

    @mcp.tool
    def list_files(pattern: str = "*", repo_path: str | None = None) -> list[dict[str, object]]:
        """List files in the indexed codebase matching a glob pattern."""
        path = Path(repo_path) if repo_path else None
        return list_indexed_files(pattern, path=path)

    @mcp.tool
    def get_chunk(file_path: str, start_line: int, end_line: int, repo_path: str | None = None) -> str:
        """Retrieve exact source text for a specific file range."""
        path = Path(repo_path) if repo_path else None
        return seam_get_chunk(file_path, start_line, end_line, path=path)

    @mcp.tool
    def index_status(repo_path: str | None = None) -> dict[str, Any]:
        """Return current Seam index freshness, file count, coverage, and backend metadata."""
        path = Path(repo_path) if repo_path else None
        return seam_index_status(path).to_dict()

    return mcp


def run_mcp_server(*, http_port: int | None = None) -> None:
    mcp = create_mcp_server()
    if http_port is not None:
        try:
            mcp.run(transport="http", host="127.0.0.1", port=http_port)
            return
        except TypeError:
            mcp.run(transport="streamable-http", host="127.0.0.1", port=http_port)
            return
    mcp.run()
