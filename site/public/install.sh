#!/usr/bin/env bash
set -euo pipefail

REPO="Aditya190803/seam"
BRANCH="main"
SOURCE="git"
METHOD="auto"
WITH_SKILLS="false"
INSTALL_AGENTS=""
INSTALL_ALL_AGENTS="true"
INSTALL_CLAUDE="true"
INSTALL_PI="true"
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
  --agent <name>       With --with-skills, target a skills.sh agent (repeatable)
  --codex              With --with-skills, install only Codex skill
  --claude             With --with-skills, install only Claude Code skill
  --pi                 With --with-skills, install only pi skill
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
    --agent)
      INSTALL_ALL_AGENTS="false"; INSTALL_AGENTS="${INSTALL_AGENTS:+$INSTALL_AGENTS,}${2:-}"; INSTALL_CLAUDE="false"; INSTALL_PI="false"; shift 2 ;;
    --codex)
      INSTALL_ALL_AGENTS="false"; INSTALL_AGENTS="codex"; INSTALL_CLAUDE="false"; INSTALL_PI="false"; shift ;;
    --claude)
      INSTALL_ALL_AGENTS="false"; INSTALL_AGENTS=""; INSTALL_CLAUDE="true"; INSTALL_PI="false"; shift ;;
    --pi)
      INSTALL_ALL_AGENTS="false"; INSTALL_AGENTS=""; INSTALL_CLAUDE="false"; INSTALL_PI="true"; shift ;;
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

install_skills() {
  have npx || { echo "npx not found. Install Node.js or install skills manually with npx skills add." >&2; exit 1; }

  echo "Installing Seam Code Search agent skill with skills.sh..."
  local source="https://github.com/${REPO}/tree/${BRANCH}/skills"
  local args=(skills add "$source" --skill seam-code-search --copy --yes)

  if [[ "$PROJECT_SCOPE" != "true" ]]; then
    args+=(--global)
  fi

  if [[ "$INSTALL_ALL_AGENTS" == "true" ]]; then
    args+=(--agent '*')
  else
    IFS=',' read -ra selected_agents <<< "$INSTALL_AGENTS"
    for agent in "${selected_agents[@]}"; do
      [[ -n "$agent" ]] && args+=(--agent "$agent")
    done
    [[ "$INSTALL_CLAUDE" == "true" ]] && args+=(--agent claude-code)
    [[ "$INSTALL_PI" == "true" ]] && args+=(--agent pi)
  fi

  npx "${args[@]}"
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
