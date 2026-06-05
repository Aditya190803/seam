# @aditya190803/seam-skill

Install the portable **Seam Code Search** Agent Skill for AI coding agents.

The skill teaches agents to use the `seam` CLI for semantic code search before reading many files.

## Install

User-level install for both Codex and Claude Code:

```bash
npx @aditya190803/seam-skill install
```

Project-level install into the current repository:

```bash
npx @aditya190803/seam-skill install --project
```

Install only for one agent:

```bash
npx @aditya190803/seam-skill install --codex
npx @aditya190803/seam-skill install --claude
```

## Skill locations

- Codex user scope: `~/.agents/skills/seam-code-search/SKILL.md`
- Claude Code user scope: `~/.claude/skills/seam-code-search/SKILL.md`
- Codex project scope: `.agents/skills/seam-code-search/SKILL.md`
- Claude Code project scope: `.claude/skills/seam-code-search/SKILL.md`

## Install Seam CLI

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash
```
