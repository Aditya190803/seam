from pathlib import Path

from typer.testing import CliRunner

from seam.cli import app
from seam.skill_installer import install_agent_skill


def test_install_agent_skill_project_scope(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    results = install_agent_skill(project=True)

    assert {result.agent for result in results} == {"Codex", "Claude Code"}
    assert (tmp_path / ".agents" / "skills" / "seam-code-search" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "seam-code-search" / "SKILL.md").exists()


def test_cli_install_skill_project_scope(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["install-skill", "--project"])

    assert result.exit_code == 0, result.output
    assert "Codex" in result.output
    assert (tmp_path / ".agents" / "skills" / "seam-code-search" / "SKILL.md").exists()
