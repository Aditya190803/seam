# Security policy

Seam is designed to be local-first.

## Source-code handling

- SQLite and LanceDB stores are local and may contain source snippets.
- Qdrant payloads intentionally contain metadata only: chunk id, relative path, line range, language, name, and content hash.
- Qdrant vectors may leave the machine when configured with a remote URL.
- Remote embedding providers receive chunk text as part of embedding requests. Use `embedding_provider=local` or `ollama` for offline operation.

## MCP server

`seam serve` defaults to stdio. HTTP mode binds to `127.0.0.1` and should not be exposed to untrusted networks without an authenticated reverse proxy.

## Reporting vulnerabilities

Open a private security advisory or contact the maintainers before public disclosure.
