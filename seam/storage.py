from __future__ import annotations

import fnmatch
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Protocol

from .embeddings import cosine, tokenize
from .models import CodeChunk, SearchResult, utc_now_iso


class VectorStore(Protocol):
    backend_name: str

    def clear(self) -> None: ...
    def set_meta(self, key: str, value: Any) -> None: ...
    def get_meta(self, key: str, default: Any = None) -> Any: ...
    def all_meta(self) -> dict[str, Any]: ...
    def upsert_file(self, path: str, *, language: str, content_hash: str, size: int, mtime: float) -> None: ...
    def delete_file(self, path: str) -> None: ...
    def delete_chunks_for_file(self, path: str) -> None: ...
    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None: ...
    def file_hashes(self) -> dict[str, str]: ...
    def counts(self) -> tuple[int, int]: ...
    def language_counts(self) -> dict[str, int]: ...
    def search(self, query_vector: list[float], query: str, *, top_k: int = 5, language: str | None = None, hybrid: bool = True) -> list[SearchResult]: ...
    def list_files(self, pattern: str = "*") -> list[dict[str, Any]]: ...
    def get_stored_chunk(self, file_path: str, start_line: int, end_line: int) -> str | None: ...


def _keyword_score(query: str, *, file_path: str, name: str | None, snippet: str) -> float:
    query_terms = set(tokenize(query))
    if not query_terms:
        return 0.0
    haystack = f"{file_path} {name or ''} {snippet}"
    doc_terms = set(tokenize(haystack))
    return len(query_terms & doc_terms) / len(query_terms)


def _hybrid_score(vector_score: float, keyword_score: float, hybrid: bool) -> float:
    if not hybrid:
        return vector_score
    return (0.82 * vector_score) + (0.18 * keyword_score)


class SQLiteStore:
    backend_name = "sqlite"

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.index_path / "index.sqlite3"
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    language TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    indexed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    name TEXT,
                    content_hash TEXT NOT NULL,
                    snippet TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(file_path) REFERENCES files(path) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
                CREATE INDEX IF NOT EXISTS idx_chunks_language ON chunks(language);
                """
            )

    def clear(self) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM chunks")
            db.execute("DELETE FROM files")
            db.execute("DELETE FROM meta")

    def set_meta(self, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        with self.connect() as db:
            db.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, encoded),
            )

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def all_meta(self) -> dict[str, Any]:
        with self.connect() as db:
            rows = db.execute("SELECT key, value FROM meta").fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def upsert_file(self, path: str, *, language: str, content_hash: str, size: int, mtime: float) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO files(path, language, content_hash, size, mtime, indexed_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    language=excluded.language,
                    content_hash=excluded.content_hash,
                    size=excluded.size,
                    mtime=excluded.mtime,
                    indexed_at=excluded.indexed_at
                """,
                (path, language, content_hash, size, mtime, utc_now_iso()),
            )

    def delete_file(self, path: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM chunks WHERE file_path = ?", (path,))
            db.execute("DELETE FROM files WHERE path = ?", (path,))

    def delete_chunks_for_file(self, path: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM chunks WHERE file_path = ?", (path,))

    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        rows = []
        now = utc_now_iso()
        for chunk, embedding in zip(chunks, embeddings):
            if not chunk.id or not chunk.content_hash:
                raise ValueError("chunk id and content_hash are required before storage")
            rows.append(
                (
                    chunk.id,
                    chunk.file_path,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.language,
                    chunk.name,
                    chunk.content_hash,
                    chunk.snippet,
                    json.dumps(embedding),
                    now,
                )
            )
        with self.connect() as db:
            db.executemany(
                """
                INSERT INTO chunks(id, file_path, start_line, end_line, language, name, content_hash, snippet, embedding, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    file_path=excluded.file_path,
                    start_line=excluded.start_line,
                    end_line=excluded.end_line,
                    language=excluded.language,
                    name=excluded.name,
                    content_hash=excluded.content_hash,
                    snippet=excluded.snippet,
                    embedding=excluded.embedding,
                    updated_at=excluded.updated_at
                """,
                rows,
            )

    def file_hashes(self) -> dict[str, str]:
        with self.connect() as db:
            rows = db.execute("SELECT path, content_hash FROM files").fetchall()
        return {row["path"]: row["content_hash"] for row in rows}

    def counts(self) -> tuple[int, int]:
        with self.connect() as db:
            files = db.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"]
            chunks = db.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()["count"]
        return int(files), int(chunks)

    def language_counts(self) -> dict[str, int]:
        with self.connect() as db:
            rows = db.execute("SELECT language, COUNT(*) AS count FROM files GROUP BY language").fetchall()
        return {row["language"]: int(row["count"]) for row in rows}

    def iter_chunk_rows(self, *, language: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as db:
            if language:
                return db.execute("SELECT * FROM chunks WHERE language = ?", (language,)).fetchall()
            return db.execute("SELECT * FROM chunks").fetchall()

    def chunk_by_id(self, chunk_id: str) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()

    def search(self, query_vector: list[float], query: str, *, top_k: int = 5, language: str | None = None, hybrid: bool = True) -> list[SearchResult]:
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in self.iter_chunk_rows(language=language):
            embedding = json.loads(row["embedding"])
            vector_score = max(0.0, cosine(query_vector, embedding))
            score = _hybrid_score(
                vector_score,
                _keyword_score(query, file_path=row["file_path"], name=row["name"], snippet=row["snippet"]),
                hybrid,
            )
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[SearchResult] = []
        for rank, (score, row) in enumerate(scored[:top_k], start=1):
            results.append(_row_to_result(rank, score, row))
        return results

    def list_files(self, pattern: str = "*") -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT path, language, size, content_hash FROM files ORDER BY path").fetchall()
        return [
            {
                "path": row["path"],
                "language": row["language"],
                "size": int(row["size"]),
                "content_hash": row["content_hash"],
            }
            for row in rows
            if fnmatch.fnmatch(row["path"], pattern)
        ]

    def get_stored_chunk(self, file_path: str, start_line: int, end_line: int) -> str | None:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT snippet FROM chunks
                WHERE file_path = ? AND start_line = ? AND end_line = ?
                LIMIT 1
                """,
                (file_path, start_line, end_line),
            ).fetchone()
        return None if row is None else str(row["snippet"])


def _row_to_result(rank: int, score: float, row: sqlite3.Row) -> SearchResult:
    return SearchResult(
        rank=rank,
        score=float(score),
        file=row["file_path"],
        start_line=int(row["start_line"]),
        end_line=int(row["end_line"]),
        language=row["language"],
        snippet=row["snippet"],
        name=row["name"],
    )


class LanceDBStore:
    backend_name = "lancedb"

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.meta = SQLiteStore(index_path)
        self.lance_path = index_path / "lancedb"
        self.table_name = "chunks"

    def __getattr__(self, name: str) -> Any:
        return getattr(self.meta, name)

    def _connect(self):  # type: ignore[no-untyped-def]
        try:
            import lancedb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("lancedb is required for backend=lancedb") from exc
        self.lance_path.mkdir(parents=True, exist_ok=True)
        return lancedb.connect(str(self.lance_path))

    def _table_names(self, db: Any) -> list[str]:
        if hasattr(db, "list_tables"):
            tables = db.list_tables()
            if hasattr(tables, "tables"):
                return list(tables.tables)
            if isinstance(tables, dict):
                return list(tables.get("tables", []))
            return list(tables)
        return list(db.table_names())

    def clear(self) -> None:
        self.meta.clear()
        try:
            db = self._connect()
            if self.table_name in self._table_names(db):
                db.drop_table(self.table_name)
        except Exception:
            pass

    def delete_file(self, path: str) -> None:
        self.meta.delete_file(path)
        self._rebuild_table()

    def delete_chunks_for_file(self, path: str) -> None:
        self.meta.delete_chunks_for_file(path)
        self._rebuild_table()

    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
        self.meta.upsert_chunks(chunks, embeddings)
        self._rebuild_table()

    def _all_lance_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in self.meta.iter_chunk_rows():
            rows.append(
                {
                    "id": row["id"],
                    "file_path": row["file_path"],
                    "start_line": int(row["start_line"]),
                    "end_line": int(row["end_line"]),
                    "language": row["language"],
                    "name": row["name"] or "",
                    "content_hash": row["content_hash"],
                    "snippet": row["snippet"],
                    "vector": json.loads(row["embedding"]),
                }
            )
        return rows

    def _rebuild_table(self) -> None:
        rows = self._all_lance_rows()
        db = self._connect()
        if self.table_name in self._table_names(db):
            db.drop_table(self.table_name)
        if rows:
            db.create_table(self.table_name, data=rows)

    def search(self, query_vector: list[float], query: str, *, top_k: int = 5, language: str | None = None, hybrid: bool = True) -> list[SearchResult]:
        try:
            db = self._connect()
            if self.table_name not in self._table_names(db):
                return []
            table = db.open_table(self.table_name)
            limit = max(top_k * 8, top_k)
            builder = table.search(query_vector)
            if language:
                safe_language = language.replace("'", "''")
                builder = builder.where(f"language = '{safe_language}'")
            candidates = builder.limit(limit).to_list()
        except Exception:
            return self.meta.search(query_vector, query, top_k=top_k, language=language, hybrid=hybrid)

        scored: list[tuple[float, dict[str, Any]]] = []
        for item in candidates:
            distance = float(item.get("_distance", item.get("_score", 0.0)) or 0.0)
            vector_score = 1.0 / (1.0 + max(distance, 0.0))
            score = _hybrid_score(
                vector_score,
                _keyword_score(query, file_path=item["file_path"], name=item.get("name"), snippet=item.get("snippet", "")),
                hybrid,
            )
            scored.append((score, item))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [_dict_to_result(rank, score, item) for rank, (score, item) in enumerate(scored[:top_k], start=1)]


class QdrantStore:
    backend_name = "qdrant"

    def __init__(self, index_path: Path, *, url: str | None = None, api_key: str | None = None) -> None:
        self.index_path = index_path
        self.meta = SQLiteStore(index_path)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", index_path.name)
        self.collection_name = f"seam_{safe_name}"
        self.url = url or "http://localhost:6333"
        self.api_key = api_key

    def __getattr__(self, name: str) -> Any:
        return getattr(self.meta, name)

    def _client(self):  # type: ignore[no-untyped-def]
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("qdrant-client is required for backend=qdrant") from exc
        return QdrantClient(url=self.url, api_key=self.api_key)

    def clear(self) -> None:
        self.meta.clear()
        try:
            client = self._client()
            if client.collection_exists(self.collection_name):
                client.delete_collection(self.collection_name)
        except Exception:
            pass

    def _ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.http import models

        client = self._client()
        if not client.collection_exists(self.collection_name):
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )

    def _delete_points_for_file(self, file_path: str) -> None:
        try:
            from qdrant_client.http import models

            client = self._client()
            if not client.collection_exists(self.collection_name):
                return
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="file_path", match=models.MatchValue(value=file_path))]
                    )
                ),
            )
        except Exception:
            pass

    def delete_file(self, path: str) -> None:
        self.meta.delete_file(path)
        self._delete_points_for_file(path)

    def delete_chunks_for_file(self, path: str) -> None:
        self.meta.delete_chunks_for_file(path)
        self._delete_points_for_file(path)

    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
        self.meta.upsert_chunks(chunks, embeddings)
        if not chunks:
            return
        self._ensure_collection(len(embeddings[0]))
        from qdrant_client.http import models

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            if not chunk.id:
                continue
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.id)),
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.id,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "language": chunk.language,
                        "name": chunk.name,
                        "content_hash": chunk.content_hash,
                    },
                )
            )
        if points:
            self._client().upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vector: list[float], query: str, *, top_k: int = 5, language: str | None = None, hybrid: bool = True) -> list[SearchResult]:
        try:
            from qdrant_client.http import models

            client = self._client()
            if not client.collection_exists(self.collection_name):
                return []
            query_filter = None
            if language:
                query_filter = models.Filter(
                    must=[models.FieldCondition(key="language", match=models.MatchValue(value=language))]
                )
            try:
                response = client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=max(top_k * 8, top_k),
                    with_payload=True,
                )
            except AttributeError:
                response = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=max(top_k * 8, top_k),
                    with_payload=True,
                ).points
        except Exception:
            return self.meta.search(query_vector, query, top_k=top_k, language=language, hybrid=hybrid)

        scored: list[tuple[float, sqlite3.Row]] = []
        for point in response:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            if not chunk_id:
                continue
            row = self.meta.chunk_by_id(str(chunk_id))
            if row is None:
                continue
            vector_score = float(getattr(point, "score", 0.0) or 0.0)
            score = _hybrid_score(
                vector_score,
                _keyword_score(query, file_path=row["file_path"], name=row["name"], snippet=row["snippet"]),
                hybrid,
            )
            scored.append((score, row))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [_row_to_result(rank, score, row) for rank, (score, row) in enumerate(scored[:top_k], start=1)]


def _dict_to_result(rank: int, score: float, item: dict[str, Any]) -> SearchResult:
    name = item.get("name") or None
    return SearchResult(
        rank=rank,
        score=float(score),
        file=str(item["file_path"]),
        start_line=int(item["start_line"]),
        end_line=int(item["end_line"]),
        language=str(item["language"]),
        snippet=str(item.get("snippet", "")),
        name=str(name) if name else None,
    )


def create_store(index_path: Path, backend: str = "sqlite", config: Any | None = None) -> VectorStore:
    backend = backend.lower()
    if backend == "sqlite":
        return SQLiteStore(index_path)
    if backend == "lancedb":
        return LanceDBStore(index_path)
    if backend == "qdrant":
        api_key = None
        if config is not None:
            env_name = getattr(config, "qdrant_api_key_env", "QDRANT_API_KEY")
            api_key = os.environ.get(env_name)
            return QdrantStore(index_path, url=getattr(config, "qdrant_url", None), api_key=api_key)
        return QdrantStore(index_path, api_key=os.environ.get("QDRANT_API_KEY"))
    raise ValueError(f"Unknown backend '{backend}'. Valid backends: sqlite, lancedb, qdrant")
