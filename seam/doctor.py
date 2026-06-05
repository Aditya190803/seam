from __future__ import annotations

import importlib.util
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import load_config, load_registry, seam_home


@dataclass(slots=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {"name": self.name, "ok": self.ok, "detail": self.detail}
        if self.hint:
            payload["hint"] = self.hint
        return payload


def _module_check(module: str, label: str, *, hint: str | None = None) -> DoctorCheck:
    found = importlib.util.find_spec(module) is not None
    return DoctorCheck(label, found, "installed" if found else "missing", hint if not found else None)


def _tcp_check(url: str | None, label: str) -> DoctorCheck:
    if not url:
        return DoctorCheck(label, False, "not configured", "Run seam config set qdrant_url http://localhost:6333")
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=2):
            return DoctorCheck(label, True, f"reachable at {host}:{port}")
    except OSError as exc:
        return DoctorCheck(label, False, f"unreachable: {exc}")


def run_doctor() -> list[DoctorCheck]:
    config = load_config()
    registry = load_registry()
    checks: list[DoctorCheck] = []

    home = seam_home()
    checks.append(DoctorCheck("seam_home", home.exists(), str(home), "Run any seam command to create it" if not home.exists() else None))
    checks.append(DoctorCheck("config", True, f"backend={config.backend}, embeddings={config.embedding_provider}/{config.embedding_model}"))
    checks.append(DoctorCheck("indexed_repos", bool(registry.get("repos")), f"{len(registry.get('repos', {}))} registered", "Run seam init [path]" if not registry.get("repos") else None))

    checks.extend(
        [
            _module_check("fastmcp", "fastmcp"),
            _module_check("lancedb", "lancedb", hint="Install seam-index with LanceDB support"),
            _module_check("qdrant_client", "qdrant_client", hint="Install qdrant-client"),
            _module_check("tree_sitter_language_pack", "tree_sitter_language_pack", hint="Install tree-sitter-language-pack"),
            _module_check("openai", "openai", hint="Install openai"),
            _module_check("watchdog", "watchdog"),
        ]
    )

    if config.embedding_provider in {"openai", "custom"}:
        env_name = config.openai_api_key_env
        checks.append(
            DoctorCheck(
                env_name,
                bool(os.environ.get(env_name)),
                "set" if os.environ.get(env_name) else "not set",
                f"Export {env_name}=..." if not os.environ.get(env_name) else None,
            )
        )
    elif config.embedding_provider == "ollama":
        base_url = config.embedding_base_url or "http://localhost:11434"
        try:
            urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=2).close()
            checks.append(DoctorCheck("ollama", True, f"reachable at {base_url}"))
        except (OSError, urllib.error.URLError) as exc:
            checks.append(DoctorCheck("ollama", False, f"unreachable at {base_url}: {exc}", "Start Ollama or switch embedding_provider"))

    if config.backend == "qdrant":
        checks.append(_tcp_check(config.qdrant_url, "qdrant"))
        env_name = config.qdrant_api_key_env
        if config.qdrant_url and "cloud" in config.qdrant_url:
            checks.append(
                DoctorCheck(
                    env_name,
                    bool(os.environ.get(env_name)),
                    "set" if os.environ.get(env_name) else "not set",
                    f"Export {env_name}=..." if not os.environ.get(env_name) else None,
                )
            )

    return checks
