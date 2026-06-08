from pathlib import Path

ROOT_SKILL = Path("skills/seam-code-search/SKILL.md")
NPM_SKILL = Path("npm/seam-skill/skills/seam-code-search/SKILL.md")
PYTHON_SKILL = Path("seam/agent_skill/seam-code-search/SKILL.md")


def test_seam_code_search_skill_assets_match() -> None:
    assert ROOT_SKILL.exists()
    assert NPM_SKILL.exists()
    assert PYTHON_SKILL.exists()
    assert ROOT_SKILL.read_text(encoding="utf-8") == NPM_SKILL.read_text(encoding="utf-8")
    assert ROOT_SKILL.read_text(encoding="utf-8") == PYTHON_SKILL.read_text(encoding="utf-8")


def test_seam_code_search_skill_defaults_to_seam_first() -> None:
    text = ROOT_SKILL.read_text(encoding="utf-8")

    assert "Always use Seam CLI as the first retrieval layer" in text
    assert "command -v seam" not in text
    assert "seam doctor" not in text
    assert "seam watch" not in text
    assert "remote embeddings" not in text.lower()
    assert "If Seam gives weak results" not in text
    assert "fall back to `grep`/`rg`" in text
