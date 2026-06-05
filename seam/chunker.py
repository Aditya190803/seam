from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any

from .models import CodeChunk

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".md": "markdown",
    ".markdown": "markdown",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}

TREE_SITTER_NODE_KINDS = {
    "function_definition",
    "class_definition",
    "function_declaration",
    "function_item",
    "method_definition",
    "method_declaration",
    "method_definition",
    "class_declaration",
    "class_body",
    "interface_declaration",
    "enum_declaration",
    "struct_item",
    "enum_item",
    "trait_item",
    "impl_item",
    "type_declaration",
    "type_spec",
    "variable_declarator",
    "lexical_declaration",
}

JS_DECL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z_$][\w$]*)|class\s+([A-Za-z_$][\w$]*)|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?[^=;]*=>)"
)

GENERIC_DECL_RE = re.compile(
    r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+|export\s+)*"
    r"(?:class|struct|enum|interface|trait|impl|fn|def|func|function)\s+([A-Za-z_][\w]*)"
)


def detect_language(path: Path) -> str:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), path.suffix.lower().lstrip(".") or "text")


def is_supported_text(path: Path) -> bool:
    return path.suffix.lower() in LANGUAGE_BY_EXTENSION


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(path: str, text: str, language: str) -> list[CodeChunk]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks = _chunk_tree_sitter(path, text, lines, language)
    if not chunks:
        if language == "python":
            chunks = _chunk_python(path, text, lines)
        elif language in {"javascript", "typescript"}:
            chunks = _chunk_js_like(path, lines, language)
        elif language == "markdown":
            chunks = _chunk_markdown(path, lines, language)
        else:
            chunks = _chunk_generic_structures(path, lines, language)

    if not chunks:
        chunks = _chunk_by_window(path, lines, language)
    return _finalize(chunks)


def _chunk_tree_sitter(path: str, text: str, lines: list[str], language: str) -> list[CodeChunk]:
    """Extract semantic chunks with tree-sitter-language-pack when available.

    The package downloads/loads grammars lazily. If a grammar is unavailable or
    parsing fails, callers fall back to Python AST and structural heuristics.
    """
    try:
        from tree_sitter_language_pack import get_parser
    except Exception:
        return []

    grammar = "tsx" if path.endswith(".tsx") else language
    try:
        parser = get_parser(grammar)
        tree = parser.parse(text)
        root = tree.root_node()
    except Exception:
        return []

    source_bytes = text.encode("utf-8")
    chunks: list[CodeChunk] = []
    seen: set[tuple[int, int, str]] = set()

    def walk(node: Any) -> None:
        kind = node.kind()
        if kind in TREE_SITTER_NODE_KINDS and node.is_named():
            start = node.start_position().row + 1
            end = node.end_position().row + 1
            key = (start, end, kind)
            if start <= end and key not in seen:
                seen.add(key)
                snippet = _slice(lines, start, end)
                if snippet.strip():
                    chunks.append(
                        CodeChunk(
                            file_path=path,
                            start_line=start,
                            end_line=end,
                            language=language,
                            snippet=snippet,
                            name=_tree_sitter_name(node, source_bytes),
                        )
                    )
        for index in range(node.named_child_count()):
            child = node.named_child(index)
            if child is not None:
                walk(child)

    walk(root)
    chunks = _filter_tree_sitter_chunks(chunks)
    return sorted(_split_large_chunks(chunks, lines), key=lambda chunk: (chunk.start_line, chunk.end_line))


def _tree_sitter_name(node: Any, source_bytes: bytes) -> str | None:
    name_node = None
    for field in ("name", "declarator", "type"):
        try:
            name_node = node.child_by_field_name(field)
        except Exception:
            name_node = None
        if name_node is not None:
            break
    if name_node is None:
        for index in range(node.named_child_count()):
            child = node.named_child(index)
            if child is not None and child.kind() in {"identifier", "type_identifier", "property_identifier"}:
                name_node = child
                break
    if name_node is None:
        return None
    try:
        byte_range = name_node.byte_range()
        raw = source_bytes[byte_range.start : byte_range.end].decode("utf-8", errors="ignore")
        match = re.search(r"[A-Za-z_$][\w$]*", raw)
        return match.group(0) if match else raw.strip() or None
    except Exception:
        return None


def _filter_tree_sitter_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    # Drop wrapper chunks that have the exact same range as a more specific named chunk.
    best_by_range: dict[tuple[int, int], CodeChunk] = {}
    for chunk in chunks:
        key = (chunk.start_line, chunk.end_line)
        existing = best_by_range.get(key)
        if existing is None or (chunk.name and not existing.name):
            best_by_range[key] = chunk
    return list(best_by_range.values())


def _slice(lines: list[str], start_line: int, end_line: int) -> str:
    return "\n".join(lines[start_line - 1 : end_line]).rstrip() + "\n"


def _chunk_python(path: str, text: str, lines: list[str]) -> list[CodeChunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    chunks: list[CodeChunk] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if not start or not end:
            continue
        chunks.append(
            CodeChunk(
                file_path=path,
                start_line=start,
                end_line=end,
                language="python",
                snippet=_slice(lines, start, end),
                name=getattr(node, "name", None),
            )
        )
    return sorted(_split_large_chunks(chunks, lines), key=lambda chunk: (chunk.start_line, chunk.end_line))


def _chunk_js_like(path: str, lines: list[str], language: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    used_starts: set[int] = set()
    for index, line in enumerate(lines, start=1):
        match = JS_DECL_RE.match(line)
        if not match:
            continue
        name = next((group for group in match.groups() if group), None)
        end = _find_brace_end(lines, index)
        if end <= index and not line.rstrip().endswith(";"):
            end = min(len(lines), index + 40)
        used_starts.add(index)
        chunks.append(CodeChunk(path, index, end, language, _slice(lines, index, end), name=name))
    return sorted(_split_large_chunks(chunks, lines), key=lambda chunk: (chunk.start_line, chunk.end_line))


def _chunk_generic_structures(path: str, lines: list[str], language: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    starts: list[tuple[int, str | None]] = []
    for index, line in enumerate(lines, start=1):
        match = GENERIC_DECL_RE.match(line)
        if match:
            starts.append((index, match.group(1)))
    for pos, (start, name) in enumerate(starts):
        next_start = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines) + 1
        end = min(next_start - 1, start + 120, len(lines))
        chunks.append(CodeChunk(path, start, end, language, _slice(lines, start, end), name=name))
    return sorted(_split_large_chunks(chunks, lines), key=lambda chunk: (chunk.start_line, chunk.end_line))


def _chunk_markdown(path: str, lines: list[str], language: str) -> list[CodeChunk]:
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        if line.startswith("#"):
            starts.append((index, line.lstrip("#").strip() or "section"))
    chunks: list[CodeChunk] = []
    for pos, (start, name) in enumerate(starts):
        next_start = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines) + 1
        end = next_start - 1
        chunks.append(CodeChunk(path, start, end, language, _slice(lines, start, end), name=name))
    return _split_large_chunks(chunks, lines)


def _find_brace_end(lines: list[str], start_line: int) -> int:
    depth = 0
    seen_open = False
    for index in range(start_line, len(lines) + 1):
        line = re.sub(r"(['\"]).*?\1", "", lines[index - 1])
        for char in line:
            if char == "{":
                depth += 1
                seen_open = True
            elif char == "}":
                depth -= 1
                if seen_open and depth <= 0:
                    return index
    return start_line


def _chunk_by_window(path: str, lines: list[str], language: str, *, size: int = 80, overlap: int = 8) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    start = 1
    while start <= len(lines):
        end = min(len(lines), start + size - 1)
        chunks.append(CodeChunk(path, start, end, language, _slice(lines, start, end), name=f"lines_{start}_{end}"))
        if end == len(lines):
            break
        start = max(end - overlap + 1, start + 1)
    return chunks


def _split_large_chunks(chunks: list[CodeChunk], lines: list[str], *, max_lines: int = 180) -> list[CodeChunk]:
    output: list[CodeChunk] = []
    for chunk in chunks:
        if chunk.end_line - chunk.start_line + 1 <= max_lines:
            output.append(chunk)
            continue
        start = chunk.start_line
        part = 1
        while start <= chunk.end_line:
            end = min(chunk.end_line, start + max_lines - 1)
            output.append(
                CodeChunk(
                    file_path=chunk.file_path,
                    start_line=start,
                    end_line=end,
                    language=chunk.language,
                    snippet=_slice(lines, start, end),
                    name=f"{chunk.name or 'chunk'}_part_{part}",
                )
            )
            part += 1
            start = end + 1
    return output


def _finalize(chunks: list[CodeChunk]) -> list[CodeChunk]:
    finalized: list[CodeChunk] = []
    for chunk in chunks:
        content_hash = sha256_text(chunk.snippet)
        raw_id = f"{chunk.file_path}:{chunk.start_line}:{chunk.end_line}:{content_hash}"
        chunk.content_hash = content_hash
        chunk.id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()
        finalized.append(chunk)
    return finalized
