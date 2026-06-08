from pathlib import Path

from typer.testing import CliRunner

from seam.cli import _is_inside_indexed_repo, app


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


def test_cli_search_exact_filters_and_grep(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def validate():\n    return 'secret_token'\n", encoding="utf-8")
    (repo / "readme.md").write_text("secret_token docs\n", encoding="utf-8")

    runner = CliRunner()
    assert runner.invoke(app, ["init", str(repo)]).exit_code == 0

    search_result = runner.invoke(
        app,
        ["search", "secret_token", "--path", str(repo), "--json", "--exact", "--name", "*.py"],
    )
    assert search_result.exit_code == 0, search_result.output
    assert "auth.py" in search_result.output
    assert "readme.md" not in search_result.output

    grep_result = runner.invoke(app, ["grep", "secret_token", "--path", str(repo), "--json", "--exclude", "*.md"])
    assert grep_result.exit_code == 0, grep_result.output
    assert "auth.py" in grep_result.output
    assert "readme.md" not in grep_result.output

    mode_result = runner.invoke(app, ["search", "secret_token", "--path", str(repo), "--json", "--mode", "keyword"])
    assert mode_result.exit_code == 0, mode_result.output
    assert "duration_ms" in mode_result.output
    assert "auth.py" in mode_result.output

    count_result = runner.invoke(app, ["search", "secret_token", "--path", str(repo), "--count"])
    assert count_result.exit_code == 0, count_result.output
    assert "auth.py: 1" in count_result.output

    size_result = runner.invoke(app, ["status", "--path", str(repo), "--json", "--size"])
    assert size_result.exit_code == 0, size_result.output
    assert "size_bytes" in size_result.output

    (repo / "readme.md").unlink()
    gc_result = runner.invoke(app, ["gc", "--path", str(repo), "--json"])
    assert gc_result.exit_code == 0, gc_result.output
    assert "readme.md" in gc_result.output


def test_cli_search_changed_filters_before_truncating(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(8):
        (repo / f"file_{index}.py").write_text(f"def func_{index}():\n    return 'needle common {index}'\n", encoding="utf-8")
    changed_file = repo / "zzz_changed.py"
    changed_file.write_text("def changed():\n    return 'needle common old'\n", encoding="utf-8")

    runner = CliRunner()
    assert runner.invoke(app, ["init", str(repo)]).exit_code == 0
    changed_file.write_text("def changed():\n    return 'needle common new'\n", encoding="utf-8")

    result = runner.invoke(app, ["search", "needle", "common", "--path", str(repo), "--changed", "--top", "1", "--json"])

    assert result.exit_code == 0, result.output
    assert "zzz_changed.py" in result.output


def test_indexed_repo_path_detection_rejects_prefix_sibling(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    sibling = tmp_path / "repo-other"
    repo.mkdir()
    sibling.mkdir()
    (repo / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (sibling / "b.py").write_text("def b():\n    return 2\n", encoding="utf-8")

    runner = CliRunner()
    assert runner.invoke(app, ["init", str(repo)]).exit_code == 0

    assert not _is_inside_indexed_repo(sibling / "b.py")


def test_cli_config_set_show(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    runner = CliRunner()

    set_result = runner.invoke(app, ["config", "set", "hybrid_search", "false"])
    assert set_result.exit_code == 0, set_result.output

    show_result = runner.invoke(app, ["config", "show", "--json"])
    assert show_result.exit_code == 0, show_result.output
    assert '"hybrid_search": false' in show_result.output
