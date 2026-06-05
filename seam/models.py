from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class CodeChunk:
    file_path: str
    start_line: int
    end_line: int
    language: str
    snippet: str
    name: str | None = None
    content_hash: str | None = None
    id: str | None = None


@dataclass(slots=True)
class SearchResult:
    rank: int
    score: float
    file: str
    start_line: int
    end_line: int
    language: str
    snippet: str
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "rank": self.rank,
            "score": round(self.score, 4),
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "snippet": self.snippet,
        }
        if self.name:
            payload["name"] = self.name
        return payload


@dataclass(slots=True)
class IndexStats:
    repo_id: str
    repo_path: str
    index_path: str
    backend: str
    embedding_provider: str
    embedding_model: str
    files: int
    chunks: int
    last_indexed_at: str | None = None
    updated_files: int = 0
    deleted_files: int = 0
    skipped_files: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    tree_hash: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "repo_path": self.repo_path,
            "index_path": self.index_path,
            "backend": self.backend,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "files": self.files,
            "chunks": self.chunks,
            "last_indexed_at": self.last_indexed_at,
            "updated_files": self.updated_files,
            "deleted_files": self.deleted_files,
            "skipped_files": self.skipped_files,
            "languages": self.languages,
            "tree_hash": self.tree_hash,
            "warnings": self.warnings,
        }
