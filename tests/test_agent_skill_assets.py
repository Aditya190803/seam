from pathlib import Path


def test_agent_skill_assets_exist_and_match_npm_copy() -> None:
    root_skill = Path("skills/seam-code-search/SKILL.md")
    npm_skill = Path("npm/seam-skill/skills/seam-code-search/SKILL.md")
    package_skill = Path("seam/agent_skill/seam-code-search/SKILL.md")
    openai_yaml = Path("skills/seam-code-search/agents/openai.yaml")
    npm_openai_yaml = Path("npm/seam-skill/skills/seam-code-search/agents/openai.yaml")
    package_openai_yaml = Path("seam/agent_skill/seam-code-search/agents/openai.yaml")

    assert root_skill.exists()
    assert npm_skill.exists()
    assert package_skill.exists()
    assert openai_yaml.exists()
    assert npm_openai_yaml.exists()
    assert package_openai_yaml.exists()
    assert root_skill.read_text(encoding="utf-8") == npm_skill.read_text(encoding="utf-8")
    assert root_skill.read_text(encoding="utf-8") == package_skill.read_text(encoding="utf-8")
    assert openai_yaml.read_text(encoding="utf-8") == npm_openai_yaml.read_text(encoding="utf-8")
    assert openai_yaml.read_text(encoding="utf-8") == package_openai_yaml.read_text(encoding="utf-8")

    text = root_skill.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: seam-code-search" in text
    assert "description:" in text
    assert "seam search --json" in text
    assert "seam context --format xml" in text
