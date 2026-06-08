# Changelog

All notable changes to Seam will be documented in this file.

## 1.0.0 - Initial public release

- First stable release of Seam.
- CLI for indexing, scoped reindexing, searching, exact grep search, status, index GC, watch, MCP serving, config, export/import, diagnostics, health checks, and context generation.
- Search improvements: repeatable `--path`, `--all-repos`, `--changed`, `--count`, `--mode`, `--alpha`, `--exact`, `--name`, `--exclude`, and `--min-score`.
- Indexing improvements: `.seamignore` glob exclusions, branch metadata, changed/deleted file paths in status, optional index size reporting, and optional index warming.
- Chunk metadata now includes enclosing scope information when available.
- JSON search output now includes `duration_ms` and `results`; schema is documented in `docs/seam.schema.json`.
- Local deterministic embeddings, OpenAI-compatible embeddings, and Ollama embeddings.
- SQLite, LanceDB, and Qdrant vector backends.
- Optional tree-sitter chunking with Python AST and structural fallbacks.
- Portable Agent Skill for Codex and Claude Code, bundled in the Python package and npm installer.
- Linux/macOS curl installer, Python installer options, npm skill installer, and release automation.

## 0.1.0 - Initial alpha

- CLI for indexing, searching, status, watch, MCP serving, config, export/import, diagnostics, and context generation.
- Local deterministic embeddings, OpenAI-compatible embeddings, and Ollama embeddings.
- SQLite, LanceDB, and Qdrant vector backends.
- Optional tree-sitter chunking with Python AST and structural fallbacks.
- Portable Agent Skill for Codex and Claude Code.
- Linux/macOS curl installer, Python installer options, npm skill installer, and release automation.
