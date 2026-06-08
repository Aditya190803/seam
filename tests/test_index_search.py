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

    keyword_results = search_code("ConnectionPool", path=repo, top_k=1, alpha=0.0)
    assert keyword_results[0].file == "db.py"

    files = list_indexed_files("*.py", path=repo)
    assert {item["path"] for item in files} == {"auth.py", "db.py"}

    snippet = get_chunk("auth.py", results[0].start_line, results[0].end_line, path=repo)
    assert "validate_jwt_token" in snippet

    status = index_status(repo)
    assert status.files == 2
    assert status.updated_file_paths == []

    (repo / "db.py").write_text("class ConnectionPool:\n    def acquire(self):\n        return 'new connection'\n", encoding="utf-8")
    stale_status = index_status(repo)
    assert stale_status.updated_file_paths == ["db.py"]


def test_selective_reindex_updates_one_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    one = repo / "one.py"
    two = repo / "two.py"
    one.write_text("def one():\n    return 'old'\n", encoding="utf-8")
    two.write_text("def two():\n    return 'stable'\n", encoding="utf-8")
    index_repo(repo)

    one.write_text("def one():\n    return 'new'\n", encoding="utf-8")
    stats = index_repo(repo, scope=one)

    assert stats.updated_file_paths == ["one.py"]
    assert search_code("new", path=repo, exact=True)[0].file == "one.py"
    assert search_code("stable", path=repo, exact=True)[0].file == "two.py"


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


def test_seamignore_excludes_files_from_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".seamignore").write_text("ignored.py\nfixtures/\n", encoding="utf-8")
    (repo / "kept.py").write_text("def kept():\n    return 'visible'\n", encoding="utf-8")
    (repo / "ignored.py").write_text("def ignored():\n    return 'hidden'\n", encoding="utf-8")
    fixtures = repo / "fixtures"
    fixtures.mkdir()
    (fixtures / "data.py").write_text("def fixture():\n    return 'hidden'\n", encoding="utf-8")

    stats = index_repo(repo)

    assert stats.files == 1
    files = {item["path"] for item in list_indexed_files("*", path=repo)}
    assert "kept.py" in files
    assert "ignored.py" not in files
    assert "fixtures/data.py" not in files


def test_search_filters_exact_min_score_and_dedup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def login():\n    return 'secret_token'\n", encoding="utf-8")
    (repo / "copy.py").write_text("def login():\n    return 'secret_token'\n", encoding="utf-8")
    (repo / "notes.md").write_text("secret_token should not be returned when excluded\n", encoding="utf-8")
    index_repo(repo)

    exact_results = search_code("secret_token", path=repo, exact=True, top_k=10)
    assert len(exact_results) == 2
    assert {result.file for result in exact_results} == {"notes.md"} | ({"auth.py", "copy.py"} & {result.file for result in exact_results})

    without_dedup = search_code("secret_token", path=repo, exact=True, top_k=10, dedup=False)
    assert {result.file for result in without_dedup} == {"auth.py", "copy.py", "notes.md"}

    py_results = search_code("secret_token", path=repo, exact=True, top_k=10, name="*.py")
    assert len(py_results) == 1
    assert py_results[0].file in {"auth.py", "copy.py"}

    excluded_results = search_code("secret_token", path=repo, exact=True, top_k=10, exclude=["*.md"])
    assert len(excluded_results) == 1
    assert excluded_results[0].file in {"auth.py", "copy.py"}

    assert search_code("secret_token", path=repo, exact=True, min_score=2.0) == []
