from pathlib import Path

from typer.testing import CliRunner

from seam.cli import app


def test_cli_init_search_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def validate_jwt(token):\n    return token == 'ok'\n", encoding="utf-8")

    runner = CliRunner()
    init_result = runner.invoke(app, ["init", str(repo)])
    assert init_result.exit_code == 0, init_result.output
    assert "Indexed" in init_result.output

    search_result = runner.invoke(app, ["search", "jwt", "validation", "--path", str(repo), "--json"])
    assert search_result.exit_code == 0, search_result.output
    assert "auth.py" in search_result.output

    status_result = runner.invoke(app, ["status", "--path", str(repo), "--json"])
    assert status_result.exit_code == 0, status_result.output
    assert '"files": 1' in status_result.output


def test_cli_config_set_show(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    runner = CliRunner()

    set_result = runner.invoke(app, ["config", "set", "hybrid_search", "false"])
    assert set_result.exit_code == 0, set_result.output

    show_result = runner.invoke(app, ["config", "show", "--json"])
    assert show_result.exit_code == 0, show_result.output
    assert '"hybrid_search": false' in show_result.output
