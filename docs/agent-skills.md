# Seam Agent Skill

Seam ships a portable Agent Skill that teaches AI coding agents to use the `seam` CLI before reading many files.

## Install with npx

```bash
npx @aditya190803/seam-skill install
```

Project-local install:

```bash
npx @aditya190803/seam-skill install --project
```

Specific-agent installs:

```bash
npx @aditya190803/seam-skill install --agent claude-code --agent pi
npx @aditya190803/seam-skill install --codex
npx @aditya190803/seam-skill install --claude
```

## Install with Seam CLI

```bash
seam install-skill
seam install-skill --project
seam install-skill --no-claude
seam install-skill --no-codex
```

## Discovery locations

The npm installer delegates to `npx skills add`, so locations follow the skills.sh supported-agent table. By default it installs globally to all supported agents with `--agent '*'`; use `--project` for project scope or `--agent <name>` to limit targets.

## What the skill tells agents

- Check `seam status --json`.
- Run `seam init .` when no index exists.
- Use `seam search --json --top 5 "query"` before broad file reads.
- Use `seam context --format xml "query"` for prompt-ready context blocks.
- Cite returned files and line ranges before editing.

## Source

The canonical skill lives at `skills/seam-code-search/SKILL.md` and is also bundled into the Python package and npm installer.
