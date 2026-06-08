import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_cli_install_skill_interactive_delegates_to_npx(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    with patch("seam.skill_installer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        result = runner.invoke(app, ["install-skill", "--interactive"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(["npx", "@aditya190803/seam-skill", "install"], check=True)


def test_cli_install_skill_interactive_propagates_npx_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    with patch("seam.skill_installer.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(7, ["npx"])
        result = runner.invoke(app, ["install-skill", "--interactive"])

    assert result.exit_code == 7
