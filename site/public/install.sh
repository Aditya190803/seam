#!/usr/bin/env bash
set -euo pipefail

REPO="Aditya190803/seam"
BRANCH="main"
SOURCE="git"
METHOD="auto"
WITH_SKILLS="false"
INSTALL_CODEX="true"
INSTALL_CLAUDE="true"
PROJECT_SCOPE="false"
PYPI_PACKAGE="seam-index"
GIT_SPEC="git+https://github.com/${REPO}.git"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

usage() {
  cat <<'EOF'
Install Seam CLI on Linux/macOS.

Usage:
  curl -fsSL https://seam.adityamer.dev/install.sh | bash
  curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- [options]

Options:
  --source git|pypi     Install from GitHub (default) or PyPI
  --method auto|uv|pipx|pip
                        Installer backend. auto prefers uv, then pipx, then pip --user
  --with-skills        Also install the Seam Code Search skill for AI coding agents
  --codex              With --with-skills, install only Codex skill
  --claude             With --with-skills, install only Claude Code skill
  --project            With --with-skills, install project-level skills in current directory
  --branch <name>      GitHub branch/tag for raw skill downloads and git install metadata
  --version <tag>      Alias for --branch, e.g. --version v0.1.0
  --help               Show this help

Examples:
  curl -fsSL https://seam.adityamer.dev/install.sh | bash
  curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills
  curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --source pypi --method pipx
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="${2:-}"; shift 2 ;;
    --method)
      METHOD="${2:-}"; shift 2 ;;
    --with-skills)
      WITH_SKILLS="true"; shift ;;
    --codex)
      INSTALL_CODEX="true"; INSTALL_CLAUDE="false"; shift ;;
    --claude)
      INSTALL_CODEX="false"; INSTALL_CLAUDE="true"; shift ;;
    --project)
      PROJECT_SCOPE="true"; shift ;;
    --branch|--version)
      BRANCH="${2:-}"; RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"; GIT_SPEC="git+https://github.com/${REPO}.git@${BRANCH}"; shift 2 ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

case "$SOURCE" in
  git) SPEC="$GIT_SPEC" ;;
  pypi) SPEC="$PYPI_PACKAGE" ;;
  *) echo "--source must be git or pypi" >&2; exit 1 ;;
esac

have() { command -v "$1" >/dev/null 2>&1; }

install_with_uv() {
  uv tool install --force "$SPEC"
}

install_with_pipx() {
  pipx install --force "$SPEC"
}

install_with_pip_user() {
  python3 -m pip install --user --upgrade "$SPEC"
}

install_cli() {
  echo "Installing Seam CLI from: $SPEC"
  case "$METHOD" in
    uv)
      have uv || { echo "uv not found. Install uv or use --method pipx/pip." >&2; exit 1; }
      install_with_uv ;;
    pipx)
      have pipx || { echo "pipx not found. Install pipx or use --method uv/pip." >&2; exit 1; }
      install_with_pipx ;;
    pip)
      have python3 || { echo "python3 not found." >&2; exit 1; }
      install_with_pip_user ;;
    auto)
      if have uv; then
        install_with_uv
      elif have pipx; then
        install_with_pipx
      elif have python3; then
        install_with_pip_user
      else
        echo "Need one of: uv, pipx, or python3 with pip." >&2
        exit 1
      fi ;;
    *) echo "--method must be auto, uv, pipx, or pip" >&2; exit 1 ;;
  esac

  echo ""
  echo "✓ Seam CLI installed. Verify with: seam --help"
  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Note: if 'seam' is not found, add ~/.local/bin to PATH:"
    echo "  export PATH=\"$HOME/.local/bin:$PATH\""
  fi
}

download() {
  local url="$1"
  local dest="$2"
  if have curl; then
    curl -fsSL "$url" -o "$dest"
  elif have wget; then
    wget -qO "$dest" "$url"
  else
    echo "Need curl or wget to download skill files." >&2
    exit 1
  fi
}

install_one_skill() {
  local root="$1"
  local dest="$root/seam-code-search"
  mkdir -p "$dest/agents"
  download "$RAW_BASE/skills/seam-code-search/SKILL.md" "$dest/SKILL.md"
  download "$RAW_BASE/skills/seam-code-search/agents/openai.yaml" "$dest/agents/openai.yaml"
  echo "✓ Installed Seam Code Search skill: $dest"
}

install_skills() {
  echo "Installing Seam Code Search agent skill..."
  if [[ "$INSTALL_CODEX" == "true" ]]; then
    if [[ "$PROJECT_SCOPE" == "true" ]]; then
      install_one_skill "$PWD/.agents/skills"
    else
      install_one_skill "$HOME/.agents/skills"
    fi
  fi
  if [[ "$INSTALL_CLAUDE" == "true" ]]; then
    if [[ "$PROJECT_SCOPE" == "true" ]]; then
      install_one_skill "$PWD/.claude/skills"
    else
      install_one_skill "$HOME/.claude/skills"
    fi
  fi
}

install_cli

if [[ "$WITH_SKILLS" == "true" ]]; then
  install_skills
else
  echo ""
  echo "Optional: install the AI agent skill with:"
  echo "  npx @aditya190803/seam-skill install"
  echo "or rerun this installer with:"
  echo "  curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills"
fi
