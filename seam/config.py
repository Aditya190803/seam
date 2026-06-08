from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "seam-local-hash-v1"


@dataclass(slots=True)
class SeamConfig:
    backend: str = "sqlite"
    embedding_provider: str = "local"
    embedding_model: str = DEFAULT_MODEL
    embedding_base_url: str | None = None
    openai_api_key_env: str = "OPENAI_API_KEY"
    qdrant_url: str | None = None
    qdrant_api_key_env: str = "QDRANT_API_KEY"
    hybrid_search: bool = True
    hybrid_alpha: float = 0.82

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SeamConfig:
        allowed = {field for field in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def seam_home() -> Path:
    return Path(os.environ.get("SEAM_HOME", str(Path.home() / ".seam"))).expanduser()


def config_path() -> Path:
    return seam_home() / "config.json"


def registry_path() -> Path:
    return seam_home() / "registry.json"


def indexes_dir() -> Path:
    return seam_home() / "indexes"


def ensure_home() -> None:
    seam_home().mkdir(parents=True, exist_ok=True)
    indexes_dir().mkdir(parents=True, exist_ok=True)


def load_config() -> SeamConfig:
    ensure_home()
    path = config_path()
    if not path.exists():
        cfg = SeamConfig()
        save_config(cfg)
        return cfg
    return SeamConfig.from_dict(json.loads(path.read_text()))


def save_config(config: SeamConfig) -> None:
    ensure_home()
    config_path().write_text(json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n")


def set_config_value(key: str, value: str) -> SeamConfig:
    config = load_config()
    if key not in config.__dataclass_fields__:
        valid = ", ".join(sorted(config.__dataclass_fields__))
        raise KeyError(f"Unknown config key '{key}'. Valid keys: {valid}")

    current = getattr(config, key)
    if isinstance(current, bool):
        parsed: Any = value.lower() in {"1", "true", "yes", "on"}
    elif isinstance(current, float):
        parsed = float(value)
    elif current is None and key.endswith("_url") and value.lower() in {"", "none", "null"}:
        parsed = None
    else:
        parsed = value
    setattr(config, key, parsed)
    save_config(config)
    return config


def load_registry() -> dict[str, Any]:
    ensure_home()
    path = registry_path()
    if not path.exists():
        data: dict[str, Any] = {"repos": {}}
        save_registry(data)
        return data
    return json.loads(path.read_text())


def save_registry(registry: dict[str, Any]) -> None:
    ensure_home()
    registry_path().write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")


def repo_id_for(path: Path) -> str:
    resolved = path.expanduser().resolve()
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", resolved.name).strip("-_.") or "repo"
    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:10]
    return f"{safe_name}-{digest}"


def index_path_for(path: Path) -> Path:
    return indexes_dir() / repo_id_for(path)


def register_repo(path: Path, *, last_indexed_at: str | None = None) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    repo_id = repo_id_for(resolved)
    registry = load_registry()
    entry = {
        "id": repo_id,
        "name": resolved.name,
        "path": str(resolved),
        "index_path": str(index_path_for(resolved)),
    }
    if last_indexed_at:
        entry["last_indexed_at"] = last_indexed_at
    registry.setdefault("repos", {})[repo_id] = entry
    save_registry(registry)
    return entry


def resolve_repo(path: Path | None = None) -> dict[str, Any]:
    registry = load_registry()
    repos: dict[str, Any] = registry.get("repos", {})

    if path is not None:
        resolved = path.expanduser().resolve()
        repo_id = repo_id_for(resolved)
        if repo_id in repos:
            return repos[repo_id]
        index_path = index_path_for(resolved)
        if index_path.exists():
            return register_repo(resolved)
        raise FileNotFoundError(f"No Seam index found for {resolved}. Run 'seam init {resolved}' first.")

    cwd = Path.cwd().resolve()
    cwd_id = repo_id_for(cwd)
    if cwd_id in repos:
        return repos[cwd_id]

    if len(repos) == 1:
        return next(iter(repos.values()))

    if not repos:
        raise FileNotFoundError("No Seam indexes found. Run 'seam init [path]' first.")

    choices = ", ".join(sorted(entry["path"] for entry in repos.values()))
    raise ValueError(f"Multiple repos are indexed. Pass --path. Indexed repos: {choices}")
