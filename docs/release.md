# Seam release checklist

## PyPI

1. Update `version` in `pyproject.toml` and `seam/__init__.py`.
2. Run validation:

   ```bash
   uv run pytest -q
   uv run python -m compileall seam main.py
   uv build
   ```

3. Tag a release and push it:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

The `Release` GitHub Actions workflow builds Python artifacts, publishes PyPI via trusted publishing, publishes the npm skill installer when `NPM_TOKEN` is configured, builds/pushes Docker to GHCR, generates `SHA256SUMS.txt`, and creates a GitHub release.

## npm skill installer

The npx installer lives in `npm/seam-skill` and publishes as `@aditya190803/seam-skill`.

```bash
cd npm/seam-skill
npm pack --dry-run
npm publish --access public
```

Smoke test before publishing:

```bash
node npm/seam-skill/bin/seam-skill.js install --dry-run
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

## Docker

Build and smoke-test locally:

```bash
docker build -t seam-index:local .
docker run --rm seam-index:local --help
```

Index a mounted repository:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -v "$HOME/.seam:/data/.seam" \
  seam-index:local init /workspace
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

Mention backend support for SQLite, LanceDB, and Qdrant; embedding support for local deterministic, OpenAI-compatible, and Ollama providers; FastMCP stdio/HTTP transport support; `seam install-skill`; and the npm/curl installers.
