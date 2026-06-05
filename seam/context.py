from __future__ import annotations

import json
import xml.sax.saxutils as xml_escape
from pathlib import Path

from .search import search_code


def build_context(query: str, *, top_k: int = 5, path: Path | None = None, language: str | None = None, fmt: str = "markdown") -> str:
    results = search_code(query, top_k=top_k, path=path, language=language)
    fmt = fmt.lower()
    if fmt == "json":
        return json.dumps([result.to_dict() for result in results], indent=2)
    if fmt == "xml":
        chunks = [f'<seam_context query="{xml_escape.escape(query)}">']
        for result in results:
            attrs = {
                "rank": str(result.rank),
                "score": f"{result.score:.4f}",
                "file": result.file,
                "start_line": str(result.start_line),
                "end_line": str(result.end_line),
                "language": result.language,
            }
            if result.name:
                attrs["name"] = result.name
            attr_text = " ".join(f'{key}="{xml_escape.escape(value)}"' for key, value in attrs.items())
            chunks.append(f"  <chunk {attr_text}>")
            chunks.append(xml_escape.escape(result.snippet.rstrip()))
            chunks.append("  </chunk>")
        chunks.append("</seam_context>")
        return "\n".join(chunks) + "\n"
    if fmt == "markdown":
        lines = [f"# Seam context: {query}", ""]
        for result in results:
            name = f" — {result.name}" if result.name else ""
            lines.append(f"## {result.rank}. `{result.file}:L{result.start_line}-L{result.end_line}`{name}")
            lines.append(f"Score: `{result.score:.4f}` · Language: `{result.language}`")
            lines.append("")
            lines.append(f"```{result.language}")
            lines.append(result.snippet.rstrip())
            lines.append("```")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
    raise ValueError("fmt must be one of: markdown, xml, json")
