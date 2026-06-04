# Seam implementation design

Date: 2026-06-04

## Scope

Implement the full Seam product shape from `SEAM_PRD.md` in this new Python repository, with a working local-first core and clear adapter boundaries for production backends.

## Architecture

Create a `seam/` package with focused modules:

- `cli.py` — Typer command surface for `init`, `watch`, `search`, `status`, `config`, `serve`, and `reindex`.
- `config.py` — global config, repo registry, and index path resolution under `~/.seam`.
- `models.py` — Pydantic/dataclass-style shared result and chunk models.
- `chunker.py` — language detection and semantic chunk extraction. Python uses `ast`; JS/TS and other languages use conservative structural heuristics.
- `embeddings.py` — embedding provider abstraction with deterministic local embeddings plus OpenAI-compatible and Ollama clients.
- `storage.py` — SQLite vector store that persists repository metadata, files, chunks, snippets, and embeddings.
- `indexer.py` — repo scanning, ignore rules, content hashing, incremental updates, and reindex orchestration.
- `search.py` — cosine similarity plus keyword scoring for hybrid search.
- `watch.py` — watchdog-based background updater and health endpoint.
- `mcp_server.py` — FastMCP-compatible tools for `search_code`, `list_files`, `get_chunk`, and `index_status`.

## Functional behavior

- `seam init [path]` scans a repository, chunks supported files, embeds chunks, and stores a local index.
- `seam search [--json] [--top n] <query>` searches the indexed repo and returns ranked code chunks.
- `seam status` reports freshness, file count, chunk count, backend, embedding provider, and index path.
- `seam config set/show` manages global settings such as backend, embedding provider, model, base URL, and API key env var name.
- `seam watch [path]` updates the index after filesystem changes and exposes `localhost:7731/health`.
- `seam serve` exposes MCP tools. Unix socket mode is represented in CLI help; HTTP/std transport is implemented through FastMCP where available.
- `seam reindex` forces a full rebuild.

## Storage and security

SQLite is the reliable default backend for this implementation. The config accepts `sqlite`, `lancedb`, and `qdrant`, but unsupported production backends fail clearly instead of silently uploading source. Raw snippets are stored only in the local SQLite index. Search output resolves relative paths against the local repository.

## Embeddings

The default provider is `local`, a deterministic hashed embedding model for offline tests and zero-configuration usage. OpenAI-compatible and Ollama providers are implemented behind the same interface and can be selected via config. Provider/model metadata is stored with the index so model changes can be detected.

## Testing

Add offline tests for chunking, indexing/search, config behavior, and CLI smoke paths. Tests use temporary repositories and deterministic local embeddings.
