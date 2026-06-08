---
name: seam-code-search
description: Always use Seam CLI as the first retrieval layer for any codebase understanding task. Default before grep, recursive reads, or opening files.
metadata:
  short-description: Search indexed code with Seam CLI
---

# Seam Code Search

Always use the `seam` CLI as the first retrieval layer for any codebase understanding task. Default to Seam before `grep`, recursive file reads, or opening files.

## Core workflow

1. Before the first search, quickly check index status from the repository root:

   ```bash
   seam status --json
   ```

2. If no index exists, initialize one automatically and proceed:

   ```bash
   seam init .
   ```

3. Search for relevant code before reading files:

   ```bash
   seam search --json --top 5 "natural language description of what to find"
   ```

4. Use returned `file`, `start_line`, and `end_line` to read only the relevant ranges with the agent's normal file tools.

5. For prompt-ready context, ask Seam to format results:

   ```bash
   seam context --format xml --top 5 "natural language description"
   seam context --format markdown --top 5 "natural language description"
   seam context --format json --top 5 "natural language description"
   ```

## When to use which command

| Command | Purpose |
|---|---|
| `seam status --json` | Quick index check (precondition before first search) |
| `seam init .` | Initialize index if none exists |
| `seam reindex .` | Refresh a stale index |
| `seam search --json "query"` | Find relevant code chunks |
| `seam context --format xml "query"` | Generate context blocks (XML, markdown, json) |

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

- If `seam status` says no index exists, run `seam init .` before searching.
- If results look stale, run `seam reindex .` or check whether the index is up to date with `seam status --json`.
- If results are weak or low relevance, fall back to `grep`/`rg` for exact or pattern-based matching.

## Response pattern

When using Seam in an answer:

1. Mention the query used.
2. Cite files and line ranges returned by Seam.
3. Read only the most relevant files/ranges before making code changes.
