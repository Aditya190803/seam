from pathlib import Path

from seam.context import build_context
from seam.indexer import index_repo


def test_build_context_markdown_and_xml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def validate_jwt(token):\n    return token == 'ok'\n", encoding="utf-8")
    index_repo(repo)

    markdown = build_context("jwt validation", path=repo, fmt="markdown")
    assert "# Seam context" in markdown
    assert "auth.py" in markdown

    xml = build_context("jwt validation", path=repo, fmt="xml")
    assert "<seam_context" in xml
    assert "<chunk" in xml
