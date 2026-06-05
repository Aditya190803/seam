from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from seam.config import SeamConfig, save_config
from seam.indexer import index_repo
from seam.search import search_code


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


def make_fixture_repo(path: Path, *, files: int, functions_per_file: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_index in range(files):
        lines: list[str] = []
        for function_index in range(functions_per_file):
            domain = ["auth", "database", "billing", "search", "cache", "agent"][function_index % 6]
            lines.extend(
                [
                    f"def {domain}_handler_{file_index}_{function_index}(value):",
                    f"    \"\"\"Handle {domain} workflow for benchmark fixture.\"\"\"",
                    f"    token = '{domain}-{file_index}-{function_index}'",
                    "    if value == token:",
                    "        return {'ok': True, 'token': token}",
                    "    return {'ok': False}",
                    "",
                ]
            )
        (path / f"module_{file_index:04d}.py").write_text("\n".join(lines), encoding="utf-8")


def benchmark(repo: Path, *, queries: list[str], repeat: int, backend: str, keep_home: bool) -> dict[str, Any]:
    seam_home = Path(tempfile.mkdtemp(prefix="seam-bench-home-"))
    os.environ["SEAM_HOME"] = str(seam_home)

    config = SeamConfig(backend=backend, embedding_provider="local")
    save_config(config)

    started = time.perf_counter()
    stats = index_repo(repo, force=True, config=config)
    index_seconds = time.perf_counter() - started

    timings: list[float] = []
    for _ in range(repeat):
        for query in queries:
            query_started = time.perf_counter()
            search_code(query, path=repo, top_k=5)
            timings.append((time.perf_counter() - query_started) * 1000)

    first_file = next(repo.glob("*.py"), None)
    incremental_seconds = None
    if first_file is not None:
        with first_file.open("a", encoding="utf-8") as handle:
            handle.write("\n\ndef benchmark_incremental_probe(value):\n    return value\n")
        update_started = time.perf_counter()
        index_repo(repo, config=config)
        incremental_seconds = time.perf_counter() - update_started

    result = {
        "repo": str(repo),
        "backend": backend,
        "files": stats.files,
        "chunks": stats.chunks,
        "tree_hash": stats.tree_hash,
        "index_seconds": round(index_seconds, 4),
        "incremental_seconds": round(incremental_seconds, 4) if incremental_seconds is not None else None,
        "query_count": len(timings),
        "query_ms_min": round(min(timings), 4) if timings else 0,
        "query_ms_mean": round(statistics.mean(timings), 4) if timings else 0,
        "query_ms_p50": round(percentile(timings, 50), 4),
        "query_ms_p95": round(percentile(timings, 95), 4),
        "query_ms_max": round(max(timings), 4) if timings else 0,
        "seam_home": str(seam_home),
    }

    if not keep_home:
        shutil.rmtree(seam_home, ignore_errors=True)
        result["seam_home"] = "deleted"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Seam indexing and query latency.")
    parser.add_argument("--repo", type=Path, help="Existing repository to benchmark. If omitted, a fixture repo is generated.")
    parser.add_argument("--files", type=int, default=250, help="Fixture file count when --repo is omitted.")
    parser.add_argument("--functions-per-file", type=int, default=8, help="Fixture functions per file when --repo is omitted.")
    parser.add_argument("--repeat", type=int, default=20, help="Number of times to repeat the query set.")
    parser.add_argument("--backend", choices=["sqlite", "lancedb"], default="sqlite", help="Backend to benchmark locally.")
    parser.add_argument("--keep-home", action="store_true", help="Keep the temporary SEAM_HOME after the run.")
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    args = parser.parse_args()

    fixture_root: Path | None = None
    if args.repo is None:
        fixture_root = Path(tempfile.mkdtemp(prefix="seam-bench-repo-"))
        repo = fixture_root / "repo"
        make_fixture_repo(repo, files=args.files, functions_per_file=args.functions_per_file)
    else:
        repo = args.repo.expanduser().resolve()

    queries = [
        "where is jwt auth validation handled",
        "database connection pooling logic",
        "billing workflow handler",
        "semantic search agent code",
        "cache token invalidation",
    ]

    try:
        result = benchmark(repo, queries=queries, repeat=args.repeat, backend=args.backend, keep_home=args.keep_home)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print("Seam benchmark")
            for key, value in result.items():
                print(f"{key}: {value}")
    finally:
        if fixture_root is not None:
            shutil.rmtree(fixture_root, ignore_errors=True)


if __name__ == "__main__":
    main()
