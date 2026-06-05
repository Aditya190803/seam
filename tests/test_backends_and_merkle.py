from pathlib import Path

from seam.config import load_config, save_config
from seam.indexer import compute_merkle_tree, index_repo
from seam.search import search_code


def test_merkle_tree_changes_when_file_hash_changes() -> None:
    root_one, nodes_one = compute_merkle_tree({"src/a.py": "aaa", "src/b.py": "bbb"})
    root_two, nodes_two = compute_merkle_tree({"src/a.py": "aaa", "src/b.py": "ccc"})

    assert root_one != root_two
    assert "." in nodes_one
    assert "src/a.py" in nodes_one
    assert nodes_one["src/a.py"] == nodes_two["src/a.py"]
    assert nodes_one["src/b.py"] != nodes_two["src/b.py"]


def test_lancedb_backend_indexes_and_searches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEAM_HOME", str(tmp_path / "seam-home"))
    config = load_config()
    config.backend = "lancedb"
    save_config(config)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "auth.py").write_text("def validate_jwt(token):\n    return token == 'ok'\n", encoding="utf-8")

    stats = index_repo(repo, config=config)
    assert stats.backend == "lancedb"
    assert stats.tree_hash

    results = search_code("jwt validation", path=repo, top_k=1)
    assert results[0].file == "auth.py"
