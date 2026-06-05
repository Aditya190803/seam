from seam.doctor import run_doctor


def test_doctor_reports_config_and_dependencies(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "home"))

    checks = run_doctor()
    names = {check.name for check in checks}

    assert "seam_home" in names
    assert "config" in names
    assert "fastmcp" in names
    assert any(check.name == "config" and check.ok for check in checks)
