# Seam

Your codebase, indexed once. Queried by any agent, instantly.

Seam is a local-first CLI and MCP server that gives coding agents semantic access to a repository without re-reading the whole codebase on every task.

## Install

### Linux/macOS curl installer

Install from GitHub using the auto installer:

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash
```

Install the CLI plus the AI agent skill:

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills
```

Installer options:

```bash
# Prefer PyPI once the package is published
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --source pypi

# Force a specific installer backend
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --method uv
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --method pipx
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --method pip
```

### Python installers

```bash
uv tool install git+https://github.com/Aditya190803/seam.git
pipx install git+https://github.com/Aditya190803/seam.git
python3 -m pip install --user git+https://github.com/Aditya190803/seam.git
```

After PyPI release:

```bash
uv tool install seam-index
pipx install seam-index
python3 -m pip install --user seam-index
```

### AI agent skill installer

Install the portable Seam skill for Codex and Claude Code:

```bash
npx @aditya190803/seam-skill install
```

Project-local skill install:

```bash
npx @aditya190803/seam-skill install --project
```

The skill is installed to:

- Codex: `~/.agents/skills/seam-code-search` or `.agents/skills/seam-code-search`
- Claude Code: `~/.claude/skills/seam-code-search` or `.claude/skills/seam-code-search`

### Docker

```bash
docker build -t seam-index .
docker run --rm -v "$PWD:/workspace" -v "$HOME/.seam:/data/.seam" seam-index init /workspace
```

### Local development

```bash
uv sync
uv run seam --help
```

The package exposes a `seam` console command.

## Quick start

```bash
# Index the current repo
uv run seam init .

# Search with human-readable output
uv run seam search "where is JWT validation handled"

# Search with JSON output for agents
uv run seam search --json --top 5 "database connection pooling"

# Generate ready-to-paste context
uv run seam context --format xml "database connection pooling"

# Show index metadata
uv run seam status
```

Indexes and config are stored under `~/.seam` by default. Set `SEAM_HOME=/path/to/home` to override this location.

## Agent skill

Seam ships a portable Agent Skill at `skills/seam-code-search/SKILL.md`. It works with tools that support the Agent Skills format:

- Codex discovers repo skills in `.agents/skills/` and user skills in `~/.agents/skills/`.
- Claude Code discovers repo skills in `.claude/skills/` and user skills in `~/.claude/skills/`.

Install it with npx or the Seam CLI:

```bash
npx @aditya190803/seam-skill install
seam install-skill
```

See [docs/agent-skills.md](docs/agent-skills.md) for details. Once installed, ask an agent to “use Seam to find the relevant code” or invoke the skill directly if your agent supports explicit skill invocation.

## Commands

```bash
seam init [path]              Index a codebase
seam reindex [path]           Force a full re-index
seam search [opts] <query>    Search indexed code
seam context [opts] <query>   Generate markdown/xml/json context blocks
seam status                   Show index freshness and metadata
seam watch [path]             Watch files and refresh the index
seam serve                    Start MCP server on stdio transport
seam serve --http <port>      Start MCP server over HTTP when supported by FastMCP
seam export <archive.tar.gz>  Export a local index archive
seam import <archive.tar.gz>  Import a local index archive
seam doctor                   Check dependencies and service reachability
seam install-skill            Install the Seam Code Search Agent Skill
seam config show              Print current configuration
seam config set <key> <value> Set a configuration value
```

## Current implementation

This repository implements the Seam product shape with production backends where they can be used locally:

- Typer CLI for the PRD command surface
- Offline deterministic local embeddings by default
- OpenAI-compatible and Ollama embedding providers
- SQLite local vector store
- LanceDB local vector backend
- Qdrant remote vector backend using metadata-only payloads; source snippets stay in the local Seam metadata store and local repo
- Incremental file hashing, deletion detection, and persisted Merkle tree metadata
- Optional tree-sitter chunking through `tree-sitter-language-pack`, with Python AST and structural fallbacks
- Hybrid vector + keyword ranking
- Watchdog-based `seam watch` with `localhost:7731/health`
- FastMCP tools: `search_code`, `list_files`, `get_chunk`, `index_status`
- `seam export` / `seam import` for portable local index archives

The default is local SQLite + deterministic embeddings for zero-config, offline operation.

## Configuration

```bash
seam config show
seam config set embedding_provider local
seam config set backend sqlite   # or lancedb / qdrant
seam config set hybrid_search true
```

OpenAI-compatible embeddings can be selected with:

```bash
export OPENAI_API_KEY=...
seam config set embedding_provider openai
seam config set embedding_model text-embedding-3-small
seam reindex .
```

Qdrant can be selected with:

```bash
seam config set backend qdrant
seam config set qdrant_url http://localhost:6333
seam config set qdrant_api_key_env QDRANT_API_KEY
seam reindex .
```

Ollama embeddings can be selected with:

```bash
seam config set embedding_provider ollama
seam config set embedding_model nomic-embed-text
seam config set embedding_base_url http://localhost:11434
seam reindex .
```

## MCP

`seam serve` starts FastMCP on stdio, which is the most portable transport for local agents. `seam serve --http 7732` starts HTTP/streamable HTTP when supported by the installed FastMCP version. Unix socket transport from the PRD is not exposed directly by this FastMCP release; use stdio for local agent integrations.

## More docs

- [Install guide](docs/install.md)
- [Agent skill guide](docs/agent-skills.md)
- [Benchmarks](docs/benchmarks.md)
- [Release checklist](docs/release.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Development

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall seam main.py scripts/benchmark.py
```
