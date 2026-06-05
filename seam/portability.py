from __future__ import annotations

import json
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from .config import index_path_for, load_config, register_repo, resolve_repo
from .storage import create_store

MANIFEST_NAME = "seam-export-manifest.json"
INDEX_PREFIX = "index"


def export_index(archive_path: Path, *, repo_path: Path | None = None) -> dict[str, Any]:
    entry = resolve_repo(repo_path)
    index_path = Path(entry["index_path"])
    if not index_path.exists():
        raise FileNotFoundError(f"Index path does not exist: {index_path}")

    config = load_config()
    store = create_store(index_path, config.backend, config)
    manifest = {
        "format": "seam-index-export-v1",
        "repo": entry,
        "meta": store.all_meta(),
        "backend": config.backend,
    }

    archive_path = archive_path.expanduser().resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="seam-export-") as tmp:
        manifest_path = Path(tmp) / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(manifest_path, arcname=MANIFEST_NAME)
            archive.add(index_path, arcname=INDEX_PREFIX)
    return {"archive": str(archive_path), "repo": entry, "index_path": str(index_path), "manifest": manifest}


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if not str(target).startswith(str(destination)):
            raise ValueError(f"Unsafe archive member path: {member.name}")
    archive.extractall(destination, filter="data")


def import_index(archive_path: Path, *, repo_path: Path | None = None, overwrite: bool = False) -> dict[str, Any]:
    archive_path = archive_path.expanduser().resolve()
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="seam-import-") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, tmp_path)

        manifest_path = tmp_path / MANIFEST_NAME
        extracted_index = tmp_path / INDEX_PREFIX
        if not manifest_path.exists() or not extracted_index.exists():
            raise ValueError("Archive is not a valid Seam export")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != "seam-index-export-v1":
            raise ValueError("Unsupported Seam export format")

        exported_repo = manifest.get("repo", {})
        target_repo = (repo_path or Path(exported_repo.get("path", "."))).expanduser().resolve()
        target_index = index_path_for(target_repo)
        if target_index.exists() and not overwrite:
            raise FileExistsError(f"Index already exists at {target_index}. Pass --overwrite to replace it.")

        if target_index.exists():
            import shutil

            shutil.rmtree(target_index)
        target_index.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copytree(extracted_index, target_index)
        entry = register_repo(target_repo, last_indexed_at=manifest.get("meta", {}).get("last_indexed_at"))

    return {"archive": str(archive_path), "repo": entry, "index_path": str(target_index)}
