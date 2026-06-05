# Seam — Product Requirements Document

**Tagline:** Your codebase, indexed once. Queried by any agent, instantly.  
**Version:** 1.0.0 — Initial Draft  
**Date:** June 2026  
**Status:** Draft for Review  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Name & Positioning](#2-product-name--positioning)
3. [Problem Statement](#3-problem-statement)
4. [Goals & Non-Goals](#4-goals--non-goals)
5. [Target Users](#5-target-users)
6. [Core Features](#6-core-features)
7. [Technical Architecture](#7-technical-architecture)
8. [CLI Reference](#8-cli-reference)
9. [MCP Server Specification](#9-mcp-server-specification)
10. [Storage Backends](#10-storage-backends)
11. [Milestones & Roadmap](#11-milestones--roadmap)
12. [Success Metrics](#12-success-metrics)
13. [Open Questions](#13-open-questions)
14. [Appendix — Competitive Landscape](#14-appendix--competitive-landscape)

---

## 1. Executive Summary

Seam is a centralized CLI tool and MCP (Model Context Protocol) server that gives AI coding agents instant, semantic access to any codebase — without re-reading files on every request.

Like how Cursor and GitHub Copilot maintain a live index of your code inside their IDE, Seam does the same thing as a **standalone, agent-agnostic service** that any AI agent can query via a simple CLI command or MCP tool call.

> **The core problem:** Every time an AI agent starts a task on a large codebase, it wastes tokens and time re-reading files just to understand the project. Two agents on the same repo each start from scratch. There is no shared memory. Seam eliminates this by maintaining a persistent, always-fresh semantic index that every agent queries in milliseconds.

---

## 2. Product Name & Positioning

### Name: Seam

A seam is the hidden joint between two materials — invisible infrastructure that holds everything together. Seam is the hidden layer between your codebase and any AI agent that touches it. It does its job quietly, in the background, and only becomes noticeable when it is missing.

| Attribute | Detail |
|---|---|
| Tagline | Your codebase, indexed once. Queried by any agent, instantly. |
| Category | Developer infrastructure / AI agent tooling |
| Primary users | Developers building or orchestrating AI coding agents |
| Distribution | PyPI (`pip install seam-index`), Homebrew tap, Docker image |
| License | Open-source core (MIT) + optional hosted cloud tier |

---

## 3. Problem Statement

### 3.1 Context

AI coding agents — whether Claude Code, custom LangChain pipelines, or framework-specific bots — need to understand a codebase before they can act on it. Today, every agent does this by itself, every single time:

- Reading files one by one until context is full
- Running `grep` or `ripgrep` on keyword guesses
- Asking the user to paste relevant files manually
- Re-indexing the entire repo from scratch each new session

This is the same problem Cursor solved for IDE users. Seam solves it for everyone else — every agent, every framework, every workflow.

### 3.2 Pain Points

| Pain point | Impact |
|---|---|
| **Token waste** | Agents burn 30–60% of their context window just reading files to find the relevant one |
| **Slow first response** | Large repos take minutes before an agent can give a useful answer |
| **No shared state** | 10 agents on the same repo = 10 separate cold reads; no coordination |
| **Keyword blindness** | `grep` finds exact strings; it misses semantically equivalent code written differently |
| **Context staleness** | Agents cache nothing; every run is cold even when nothing changed |

### 3.3 Why Now

Three things have converged to make this buildable today:

1. **Tree-sitter** is mature and supports 40+ languages with stable grammar bindings
2. **LanceDB** ships as a pure Python embedded vector database — zero infra to run locally
3. **MCP** has become the standard protocol for exposing tools to AI agents across frameworks

---

## 4. Goals & Non-Goals

### 4.1 Goals

1. Provide a persistent, always-fresh semantic index of any codebase
2. Expose the index via a CLI and an MCP server so any AI agent can query it without configuration
3. Support both fully local storage (LanceDB) and remote storage (Qdrant) from day one
4. Use tree-sitter AST chunking so embeddings map to real code units, not arbitrary line ranges
5. Incrementally update the index using Merkle-tree diffing — only reprocess what changed
6. Be embedding-model agnostic: support OpenAI, Ollama, and any OpenAI-compatible endpoint
7. Reach sub-100ms query latency (p95) on repos up to 500,000 lines of code
8. Never transmit raw source code to any remote service

### 4.2 Non-Goals

- Seam is not an IDE plugin or editor extension
- Seam does not execute or run code — it only indexes and retrieves
- Seam is not a general-purpose RAG framework
- Seam does not replace LSP for symbol resolution — it complements it
- Seam does not perform code review, linting, or analysis — it is a retrieval layer only

---

## 5. Target Users

| Persona | Who they are | What they need from Seam |
|---|---|---|
| **Agent developer** | Engineer building AI coding agents on Claude, GPT-4, etc. | A reliable tool call that returns relevant code without burning tokens on file reads |
| **Solo developer** | Individual using Claude Code or similar on a large personal project | Smarter search than `grep`; no infra or config overhead |
| **Platform team** | Team running AI agent infrastructure for internal engineers | A shared centralized index that all agents on the team query; no per-agent setup |
| **OSS maintainer** | Maintainer of a large open-source project using AI code review agents | Persistent index updated on each push; agents arrive already knowing the codebase |

---

## 6. Core Features

### 6.1 Indexing Pipeline

#### Tree-sitter AST Chunking

Files are parsed using tree-sitter, which understands the grammar of 40+ languages. Code is split into meaningful semantic units — functions, classes, methods, and logical blocks — rather than arbitrary line ranges. This means every embedding corresponds to a real code concept.

A 50-line chunk that starts mid-function and ends in another is meaningless to an embedding model. A chunk that is exactly one function is not.

#### Merkle Tree Incremental Updates

On each sync, Seam computes a SHA-256 Merkle tree over the file system. Only files whose hashes differ from the stored tree are re-chunked and re-embedded. On a 50,000-file repo, a single file change triggers re-indexing of exactly that one file, not the entire codebase.

Seam also caches embeddings by content hash. If you rename a function but its body is unchanged, Seam skips the embedding API call entirely.

#### Embedding Model Abstraction

Seam supports a pluggable embedding backend:

- `openai` — `text-embedding-3-small` (default; fast, cheap, good quality)
- `ollama` — any locally running model (`nomic-embed-text`, `mxbai-embed-large`) for full offline/air-gap operation
- `custom` — any OpenAI-compatible endpoint via `base_url` override

The embedding model is stored alongside the index. Switching models triggers a full re-index with a clear warning.

### 6.2 Storage Backends

| Backend | Mode | Best for |
|---|---|---|
| **LanceDB** | Local embedded (default) | Single developer, laptop, zero infra, zero latency |
| **Qdrant** | Remote server or Qdrant Cloud | Shared team index, multiple agents on same codebase, persistent across machines |
| **SQLite + json1** | Local fallback | Environments where native LanceDB fails; keyword-only search mode |

### 6.3 Query Engine

When an agent issues a search query, Seam:

1. Embeds the natural language query using the same model used at index time
2. Performs approximate nearest-neighbor (ANN) search against stored chunk embeddings
3. Optionally combines with BM25 keyword search for hybrid retrieval (improves recall by ~12%)
4. Returns top-k matching chunks with: file path, start/end line, language, similarity score, and the raw snippet
5. Resolves all file paths locally — actual source code never leaves the developer's machine

### 6.4 Watch Daemon

`seam watch` starts a background process that:

- Subscribes to OS-level file system events (`inotify` on Linux, `FSEvents` on macOS, `ReadDirectoryChangesW` on Windows)
- Debounces rapid saves (e.g. auto-formatters writing multiple times per second)
- Computes Merkle diff on changed files only
- Updates the index in the background, typically within 2–5 seconds of a file save
- Exposes a health endpoint at `localhost:7731/health` for process supervision

---

## 7. Technical Architecture

### 7.1 Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                        Your codebase                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ file events
                    ┌──────▼──────┐
                    │   Watcher   │  Merkle tree, diffs only
                    └──────┬──────┘
                           │ changed files
                    ┌──────▼──────┐
                    │   Chunker   │  tree-sitter AST, 40+ langs
                    └──────┬──────┘
                           │ semantic chunks
                    ┌──────▼──────┐
                    │  Embedder   │  OpenAI / Ollama / custom
                    └──────┬──────┘
                           │ vectors + metadata
          ┌────────────────┴─────────────────┐
          │                                  │
   ┌──────▼──────┐                   ┌───────▼───────┐
   │   LanceDB   │                   │    Qdrant     │
   │  (local)    │                   │   (remote)    │
   └──────┬──────┘                   └───────┬───────┘
          └────────────────┬─────────────────┘
                    ┌──────▼──────┐
                    │Query engine │  embed → ANN → hybrid rank
                    └──────┬──────┘
                           │
          ┌────────────────┴─────────────────┐
          │                                  │
   ┌──────▼──────┐                   ┌───────▼───────┐
   │     CLI     │                   │  MCP server   │
   │  seam search│                   │ search_code   │
   └─────────────┘                   └───────────────┘
```

### 7.2 Data Flow

**Index time:**
```
file change detected
  → Merkle diff identifies changed files
  → changed files parsed by tree-sitter into AST chunks
  → chunks batched and sent to embedding model
  → vectors written to store with metadata:
      { file_path, start_line, end_line, language, content_hash, chunk_text }
```

**Query time:**
```
natural language query
  → embedded with same model used at index time
  → ANN search against stored vectors
  → optional BM25 merge for hybrid score
  → top-k results ranked by combined score
  → file paths resolved to local disk
  → chunks returned as JSON:
      { rank, score, file, start_line, end_line, language, snippet }
```

### 7.3 Security Model

- Raw source code is **never written to any remote service**
- Only embedding vectors (arrays of floats) leave the machine when using remote embedding APIs
- When using Qdrant remote, vectors + metadata (file path, line numbers) are stored — no source text
- File paths are stored as relative paths only; absolute paths never leave the host
- The MCP server binds to a Unix socket by default; HTTP mode requires explicit opt-in

---

## 8. CLI Reference

### Commands

```
seam init [path]              Index a codebase for the first time
seam watch [path]             Start background daemon, auto-update on changes
seam search <query>           Semantic search, human-readable output
seam search --json <query>    Machine-readable JSON output for agent consumption
seam search --top <n> <query> Return top n results (default: 5)
seam status                   Show index freshness, file count, backend, model
seam config set <key> <value> Set embedding model, backend, API keys
seam config show              Print current configuration
seam serve                    Start MCP server (Unix socket default)
seam serve --http <port>      Start MCP server over HTTP
seam reindex                  Force full re-index (use after switching embedding model)
```

### Example Session

```bash
# First time setup
$ seam init ./my-project
✓ Detected languages: Python (68%), TypeScript (24%), SQL (8%)
✓ Chunked 1,847 files into 12,304 semantic units
✓ Embedded 12,304 chunks via openai/text-embedding-3-small
✓ Stored in LanceDB at ~/.seam/indexes/my-project
  Index ready in 94 seconds

# Search
$ seam search "where is JWT validation handled"
  1  0.94  src/auth/middleware.py        L23–67   validate_jwt_token()
  2  0.91  src/auth/tokens.py            L112–140 decode_and_verify()
  3  0.87  tests/auth/test_middleware.py L45–89   test_invalid_token_returns_401()

# Machine output for agents
$ seam search --json "database connection pooling"
[
  {
    "rank": 1, "score": 0.96,
    "file": "src/db/pool.py", "start_line": 1, "end_line": 58,
    "language": "python",
    "snippet": "class ConnectionPool:\n    def __init__(self, dsn, min_conn=2..."
  }
]

# Start MCP server for Claude Code
$ seam serve
✓ MCP server listening at unix:///home/user/.seam/mcp.sock
  Add to Claude Code: { "mcp_socket": "~/.seam/mcp.sock" }
```

---

## 9. MCP Server Specification

Seam exposes an MCP-compliant tool server. Any agent framework that supports MCP can use it natively — no wrapper code required.

### Exposed Tools

#### `search_code`

```json
{
  "name": "search_code",
  "description": "Semantically search the indexed codebase. Returns ranked code chunks relevant to the query. Use this before reading files to find the right location first.",
  "parameters": {
    "query":     { "type": "string",  "description": "Natural language description of what you're looking for" },
    "top_k":     { "type": "integer", "description": "Number of results to return", "default": 5 },
    "repo_path": { "type": "string",  "description": "Path to the repo (optional if only one repo is indexed)" },
    "language":  { "type": "string",  "description": "Filter to a specific language, e.g. 'python'" }
  }
}
```

#### `list_files`

```json
{
  "name": "list_files",
  "description": "List files in the indexed codebase matching a glob pattern, with language and size metadata.",
  "parameters": {
    "pattern":   { "type": "string", "description": "Glob pattern, e.g. 'src/**/*.py'" },
    "repo_path": { "type": "string", "description": "Path to the repo" }
  }
}
```

#### `get_chunk`

```json
{
  "name": "get_chunk",
  "description": "Retrieve the exact source text for a specific file range. Use after search_code to get the full context of a result.",
  "parameters": {
    "file_path":  { "type": "string",  "description": "Relative file path" },
    "start_line": { "type": "integer", "description": "Start line (1-indexed)" },
    "end_line":   { "type": "integer", "description": "End line (inclusive)" }
  }
}
```

#### `index_status`

```json
{
  "name": "index_status",
  "description": "Return the current state of the Seam index: freshness, file count, coverage, and last update time.",
  "parameters": {
    "repo_path": { "type": "string", "description": "Path to the repo" }
  }
}
```

### Integration Example — Claude Code

```bash
# Start Seam MCP server
seam serve

# In Claude Code settings (settings.json):
{
  "mcp_servers": [
    {
      "name": "seam",
      "socket": "~/.seam/mcp.sock"
    }
  ]
}
```

Once connected, Claude Code automatically calls `search_code` before reading files. Token usage on large repos typically drops by 40–60%.

---

## 10. Storage Backends

### LanceDB (Local, Default)

- Embedded in-process; no separate server
- Index stored at `~/.seam/indexes/<repo-name>/`
- ANN via IVF-PQ index; sub-10ms queries on 1M vectors
- Portable: copy the directory to share the index

### Qdrant (Remote)

Configure via `seam config set backend qdrant`:

```bash
seam config set backend qdrant
seam config set qdrant_url http://localhost:6333
seam config set qdrant_api_key <key>          # if using Qdrant Cloud
```

Vectors and metadata are stored in Qdrant. Raw source code is never uploaded — only vectors and file path + line metadata.

### Shared Team Index

When multiple developers work on the same codebase:

1. One team member runs `seam init` and `seam watch`
2. Vectors are stored in a shared Qdrant instance
3. All other team members point their Seam config at the same Qdrant URL
4. Query latency is identical; index is maintained by whoever is running `seam watch`

---

## 11. Milestones & Roadmap

| Phase | Target | Deliverables |
|---|---|---|
| **M1 — Core** | Week 3 | `seam init` + `seam search`, tree-sitter chunking for Python/JS/TS, LanceDB backend, OpenAI embeddings, `--json` output |
| **M2 — Watch** | Week 5 | `seam watch` daemon, Merkle incremental updates, OS file watcher integration, health endpoint |
| **M3 — MCP** | Week 7 | MCP server with all 4 tools, Unix socket transport, Claude Code integration guide, `seam serve` command |
| **M4 — Local AI** | Week 9 | Ollama embedding backend, full offline/air-gap mode, SQLite fallback for restricted envs |
| **M5 — Remote** | Week 11 | Qdrant backend, shared team index workflow, multi-repo namespace support |
| **M6 — Polish** | Week 14 | Hybrid BM25+semantic search, 40-language support, `pip install seam-index`, Homebrew tap, full test suite |

---

## 12. Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Query latency p95 | < 100ms | Benchmark: 100k-line repo, LanceDB local, 50 queries |
| Index freshness lag | < 5 seconds | Time from file save to updated result in `seam watch` mode |
| Search relevance (top-5 recall) | > 80% | Manual eval set: 50 queries across 3 diverse repos |
| Token reduction for agents | > 50% | Before/after token count across 20 representative agent tasks |
| Cold index time (50k files) | < 3 minutes | Timed on M2 MacBook Pro with OpenAI embeddings |
| Incremental update time | < 2 seconds | Single file change on a fully indexed 50k-file repo |
| MCP tool call success rate | > 99% | Automated integration test suite against Claude Code |

---

## 13. Open Questions

1. **Multi-repo namespacing** — Should a single Seam instance manage multiple repos under different namespaces, or should users run one instance per repo? The former is more convenient; the latter is simpler to implement and reason about.

2. **Embedding model migration** — If a user switches from OpenAI to Ollama mid-project, should Seam automatically re-index, or maintain both indexes side-by-side? Automatic re-index is clean but could be slow on large repos.

3. **Cloud hosted offering** — Should there be a hosted Seam service where teams push indexes without running their own Qdrant? The privacy model needs careful design — Seam's current guarantee is that raw source never leaves the machine.

4. **Context injection format** — Should Seam generate ready-to-paste context blocks in agent-specific formats (XML tags for Claude, `<context>` blocks for GPT-4)? Or keep output as plain JSON and let the agent framework handle formatting?

5. **MCP over HTTP auth** — When exposing the MCP server over HTTP (not just Unix socket), what authentication mechanism should be required? Bearer token? mTLS? No auth for localhost-only?

6. **Index portability** — Should `seam export` / `seam import` be supported to share a pre-built index across a team without requiring everyone to run `seam init`?

---

## 14. Appendix — Competitive Landscape

| Tool | Type | Strength | Gap vs Seam |
|---|---|---|---|
| **CocoIndex** | Python library | Excellent AST chunking, real-time incremental updates | No MCP server; requires integration code to use from agents |
| **grepai** | CLI binary | Single binary, fast startup, no deps | No AST chunking; limited language support; no watch daemon |
| **Cursor indexing** | IDE feature | Polished UX, Merkle diffs, team index sharing | Locked to Cursor IDE; not accessible by external agents |
| **Sourcegraph Cody** | Enterprise platform | Multi-repo, enterprise auth, hosted | Heavy infrastructure; not practical for individual developers or small teams |
| **Codex CLI (OpenAI)** | CLI tool | Deep OpenAI integration | No persistent index; proposed feature, not shipped |
| **Seam** | CLI + MCP server | Agent-agnostic, local-first, MCP-native, zero infra | — |

---

*Seam PRD v1.0.0 — June 2026*
