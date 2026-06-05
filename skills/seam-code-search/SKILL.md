---
name: seam-code-search
description: Use Seam CLI for semantic codebase search, indexed context retrieval, and agent-ready code snippets before reading many files. Trigger when locating code, understanding implementations, finding symbols, searching behavior, or gathering context from a repo.
metadata:
  short-description: Search indexed code with Seam CLI
---

# Seam Code Search

Use the `seam` CLI as the first retrieval layer for codebase understanding. Prefer Seam before broad `grep`, recursive file reads, or opening many files.

## Core workflow

1. Check whether Seam is installed:

   ```bash
   command -v seam && seam --help
   ```

2. Check index status from the repository root:

   ```bash
   seam status --json
   ```

3. If no index exists, initialize one:

   ```bash
   seam init .
   ```

4. Search for relevant code before reading files:

   ```bash
   seam search --json --top 5 "natural language description of what to find"
   ```

5. Use returned `file`, `start_line`, and `end_line` to read only the relevant ranges with the agent's normal file tools.

6. For prompt-ready context, ask Seam to format results:

   ```bash
   seam context --format xml --top 5 "natural language description"
   seam context --format markdown --top 5 "natural language description"
   seam context --format json --top 5 "natural language description"
   ```

## When to use which command

| Need | Command |
|---|---|
| Confirm index health | `seam status --json` |
| First-time setup | `seam init .` |
| Refresh everything | `seam reindex .` |
| Find relevant code chunks | `seam search --json "query"` |
| Generate context block | `seam context --format xml "query"` |
| Debug installation/config | `seam doctor` |
| Keep index fresh while editing | `seam watch .` |

## Query guidance

Write natural-language queries that describe behavior, not just identifiers:

- `where is jwt validation handled`
- `database connection pooling setup`
- `how background file watching updates the index`
- `MCP tool implementation for search_code`
- `configuration loading and repo registry logic`

Add filters when useful:

```bash
seam search --json --language python --top 10 "embedding provider abstraction"
```

## Error handling

- If `seam` is missing, tell the user to install it. Recommended Linux install:

  ```bash
  curl -fsSL https://seam.adityamer.dev/install.sh | bash
  ```

- If `seam status` says no index exists, run `seam init .` before searching.
- If results look stale, run `seam reindex .`.
- If remote embeddings or Qdrant fail, run `seam doctor` and inspect missing environment variables or unreachable services.
- Never upload raw source to remote services unless the user configured a remote embedding provider knowingly. The default local provider is offline.

## Response pattern

When using Seam in an answer:

1. Mention the query used.
2. Cite files and line ranges returned by Seam.
3. Read only the most relevant files/ranges before making code changes.
4. If Seam gives weak results, fall back to normal repo search and say so briefly.
