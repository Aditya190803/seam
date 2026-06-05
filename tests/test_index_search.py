from pathlib import Path

from seam.indexer import index_repo, index_status
from seam.search import get_chunk, list_indexed_files, search_code


def test_index_and_search_repo(tmp_path: Path, monkeypatch) -> None:
    seam_home = tmp_path / "seam-home"
    monkeypatch.setenv("SEAM_HOME", str(seam_home))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text(
        """
def validate_jwt_token(token):
    if token == "valid":
        return {"sub": "user"}
    raise ValueError("invalid token")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / "db.py").write_text(
        """
class ConnectionPool:
    def acquire(self):
        return "connection"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    stats = index_repo(repo)
    assert stats.files == 2
    assert stats.chunks >= 2

    results = search_code("where is jwt token validation handled", path=repo, top_k=2)
    assert results
    assert results[0].file == "auth.py"
    assert "validate_jwt_token" in results[0].snippet

    files = list_indexed_files("*.py", path=repo)
    assert {item["path"] for item in files} == {"auth.py", "db.py"}

    snippet = get_chunk("auth.py", results[0].start_line, results[0].end_line, path=repo)
    assert "validate_jwt_token" in snippet

    status = index_status(repo)
    assert status.files == 2


def test_incremental_index_removes_deleted_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "one.py"
    file_path.write_text("def one():\n    return 1\n", encoding="utf-8")

    assert index_repo(repo).files == 1
    file_path.unlink()
    stats = index_repo(repo)

    assert stats.files == 0
    assert stats.deleted_files == 1
