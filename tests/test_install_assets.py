from pathlib import Path


def test_site_install_script_matches_canonical_script() -> None:
    canonical = Path("scripts/install.sh")
    site_copy = Path("site/public/install.sh")

    assert canonical.exists()
    assert site_copy.exists()
    assert canonical.read_text(encoding="utf-8") == site_copy.read_text(encoding="utf-8")
    assert "https://seam.adityamer.dev/install.sh" in canonical.read_text(encoding="utf-8")
