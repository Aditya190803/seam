# @aditya190803/seam-skill

Install the portable **Seam Code Search** Agent Skill for AI coding agents.

This package delegates installation to the [skills.sh](https://www.skills.sh/docs) CLI, so it can target all supported agents instead of hardcoding only Codex/Claude paths.

## Install

Global install to all skills.sh-supported agents:

```bash
npx @aditya190803/seam-skill install
```

Project-level install into the current repository:

```bash
npx @aditya190803/seam-skill install --project
```

Install only for specific agents:

```bash
npx @aditya190803/seam-skill install --agent claude-code --agent pi
npx @aditya190803/seam-skill install --codex
npx @aditya190803/seam-skill install --claude
npx @aditya190803/seam-skill install --pi
```

## Install Seam CLI

```bash
curl -fsSL https://seam.adityamer.dev/install.sh | bash
```
