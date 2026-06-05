# Benchmarks

Run Seam's local benchmark harness with:

```bash
uv run python scripts/benchmark.py --json
```

By default it generates a temporary Python fixture repository, indexes it with the deterministic local embedding provider, runs a fixed query set, and reports:

- full index time
- incremental update time
- query p50/p95/max latency
- indexed file and chunk counts
- Merkle root hash

Benchmark an existing repository:

```bash
uv run python scripts/benchmark.py --repo /path/to/repo --repeat 50 --backend sqlite --json
uv run python scripts/benchmark.py --repo /path/to/repo --repeat 50 --backend lancedb --json
```

The PRD targets should be measured on a representative 100k+ line repository with warm local storage:

| Metric | Target |
|---|---:|
| Query latency p95 | < 100ms |
| Index freshness lag in watch mode | < 5s |
| Incremental update time | < 2s |

Remote embedding providers and Qdrant depend on network/service latency and should be benchmarked separately in the target deployment environment.
