# Install Seam

## Recommended Linux/macOS installer

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash
```

Install CLI and agent skills:

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills
```

Install from a pinned tag after release:

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --version v0.1.0
```

## Python tool installers

From GitHub:

```bash
uv tool install git+https://github.com/Aditya190803/seam.git
pipx install git+https://github.com/Aditya190803/seam.git
python3 -m pip install --user git+https://github.com/Aditya190803/seam.git
```

From PyPI after publishing:

```bash
uv tool install seam-index
pipx install seam-index
python3 -m pip install --user seam-index
```

## Agent skill installer

```bash
npx @aditya190803/seam-skill install
```

## Docker

```bash
docker build -t seam-index .
docker run --rm -v "$PWD:/workspace" -v "$HOME/.seam:/data/.seam" seam-index init /workspace
```

## Verify

```bash
seam --help
seam doctor
```

## Uninstall

```bash
uv tool uninstall seam-index
pipx uninstall seam-index
python3 -m pip uninstall seam-index
rm -rf ~/.agents/skills/seam-code-search ~/.claude/skills/seam-code-search
```
