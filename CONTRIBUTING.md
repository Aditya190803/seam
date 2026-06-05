# Contributing to Seam

Thanks for helping improve Seam.

## Development setup

```bash
uv sync --all-extras --dev
uv run seam --help
```

## Validation

Run the full local validation suite before opening a PR:

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall seam main.py scripts/benchmark.py
bash -n scripts/install.sh
node npm/seam-skill/bin/seam-skill.js install --dry-run
(cd npm/seam-skill && npm pack --dry-run)
uv build
```

## Release checklist

See [docs/release.md](docs/release.md).

## Security and privacy

See [SECURITY.md](SECURITY.md). Do not add telemetry or remote source-code upload behavior without explicit design review.
