from pathlib import Path

from seam.chunker import chunk_text, detect_language


def test_python_chunker_extracts_functions_and_classes() -> None:
    source = """
class AuthService:
    def validate_jwt(self, token):
        return token == "ok"


def helper():
    return "done"
""".strip()

    chunks = chunk_text("src/auth.py", source, "python")
    names = {chunk.name for chunk in chunks}

    assert "AuthService" in names
    assert "validate_jwt" in names
    assert "helper" in names
    assert all(chunk.content_hash for chunk in chunks)
    assert all(chunk.id for chunk in chunks)


def test_detect_language_for_typescript() -> None:
    assert detect_language(Path("src/index.ts")) == "typescript"
