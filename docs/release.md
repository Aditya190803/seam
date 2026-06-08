# Seam release checklist

## Versioning

1. Update `version` in `pyproject.toml`, `seam/__init__.py`, and `npm/seam-skill/package.json`.
2. Update `CHANGELOG.md` with user-visible changes.
3. Verify skill assets stay in sync:
   - `skills/seam-code-search/SKILL.md`
   - `seam/agent_skill/seam-code-search/SKILL.md`
   - `npm/seam-skill/skills/seam-code-search/SKILL.md`

## Local validation

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall seam main.py scripts/benchmark.py
bash -n scripts/install.sh
node npm/seam-skill/bin/seam-skill.js install --dry-run
cd npm/seam-skill && npm pack --dry-run
cd ../..
uv build
```

## PyPI

The GitHub Release workflow publishes to PyPI on `v*.*.*` tag pushes via trusted publishing. Manual workflow dispatch publishes only when `publish=true`. Reruns query PyPI first and skip publishing when that package version already exists.

```bash
git tag v1.0.2
git push origin v1.0.2
```

## npm skill installer

The npx installer lives in `npm/seam-skill` and publishes as `@aditya190803/seam-skill`.

The Release workflow publishes it on tag pushes when `NPM_TOKEN` is configured, and on manual workflow dispatch when `publish=true` and `NPM_TOKEN` is configured. Reruns skip the publish step when the package version already exists on npm.

Manual smoke test:

```bash
node npm/seam-skill/bin/seam-skill.js install --dry-run
cd npm/seam-skill
npm pack --dry-run
```

## Linux curl installer

The curl installer is `scripts/install.sh` and is intended to be fetched from the Seam website:

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills
```

Validate locally:

```bash
bash -n scripts/install.sh
```

## Homebrew

A formula template lives at `packaging/homebrew/seam-index.rb`.

Before publishing a tap:

1. Replace `homepage`, source `url`, and `sha256`.
2. Run `brew update-python-resources seam-index` to vendor pinned Python resources.
3. Test with:

   ```bash
   brew install --build-from-source ./packaging/homebrew/seam-index.rb
   seam --help
   ```

## Release notes

Mention backend support for SQLite, LanceDB, and Qdrant; embedding support for local deterministic, OpenAI-compatible, and Ollama providers; FastMCP stdio/HTTP transport support; `seam install-skill`; npm/curl installers; scoped reindexing; `.seamignore`; grep/exact search; changed-file search; index GC; and JSON schema output.
