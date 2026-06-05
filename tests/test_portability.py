from pathlib import Path

from seam.indexer import index_repo
from seam.portability import export_index, import_index
from seam.search import search_code


def test_export_import_index(tmp_path: Path, monkeypatch) -> None:
    seam_home = tmp_path / "home"
    monkeypatch.setenv("SEAM_HOME", str(seam_home))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def validate_jwt(token):\n    return token == 'ok'\n", encoding="utf-8")
    index_repo(repo)

    archive = tmp_path / "seam-export.tar.gz"
    exported = export_index(archive, repo_path=repo)
    assert archive.exists()
    assert exported["repo"]["path"] == str(repo.resolve())

    imported_repo = tmp_path / "imported-repo"
    imported_repo.mkdir()
    (imported_repo / "auth.py").write_text((repo / "auth.py").read_text(encoding="utf-8"), encoding="utf-8")
    imported = import_index(archive, repo_path=imported_repo)

    assert imported["repo"]["path"] == str(imported_repo.resolve())
    results = search_code("jwt validation", path=imported_repo, top_k=1)
    assert results[0].file == "auth.py"
