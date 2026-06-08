#!/usr/bin/env node
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const command = args[0];
const flags = args.slice(1);

function hasFlag(flag) {
  return flags.includes(flag);
}

function valuesFor(flag) {
  const values = [];
  for (let i = 0; i < flags.length; i += 1) {
    const arg = flags[i];
    if (arg === flag && flags[i + 1]) {
      values.push(flags[i + 1]);
      i += 1;
    } else if (arg.startsWith(`${flag}=`)) {
      values.push(arg.slice(flag.length + 1));
    }
  }
  return values;
}

function help() {
  console.log(`Seam agent skill installer

Usage:
  npx @aditya190803/seam-skill install [options]

This is a thin wrapper around the skills.sh CLI. By default it installs
seam-code-search globally to every skills.sh-supported agent.

Options:
  -g, --global      Install to user-level agent skill directories (default)
  --user            Alias for --global
  -p, --project     Install to project-level agent skill directories
  -a, --agent NAME  Target a skills.sh agent (repeatable, default: '*')
  --all             Install to all skills.sh-supported agents
  --copy            Copy files instead of symlinking (default for this wrapper)
  --no-copy         Let skills.sh use its default symlink behavior
  -y, --yes         Skip prompts (default for this wrapper)
  --dry-run         Print the delegated skills.sh command without running it
  --help            Show this help

Compatibility aliases:
  --codex           Same as --agent codex
  --agents          Same as --agent universal
  --claude          Same as --agent claude-code
  --pi              Same as --agent pi

Examples:
  npx @aditya190803/seam-skill install
  npx @aditya190803/seam-skill install --project
  npx @aditya190803/seam-skill install --agent claude-code --agent pi
`);
}

if (!command || command === "--help" || command === "-h" || hasFlag("--help") || hasFlag("-h")) {
  help();
  process.exit(0);
}

if (command !== "install") {
  console.error(`Unknown command: ${command}`);
  help();
  process.exit(1);
}

const packageRoot = path.resolve(__dirname, "..");
const source = path.join(packageRoot, "skills");

if (!fs.existsSync(path.join(source, "seam-code-search", "SKILL.md"))) {
  console.error(`Bundled skill not found: ${source}`);
  process.exit(1);
}

const skillArgs = ["skills", "add", source, "--skill", "seam-code-search"];

if (hasFlag("--project") || hasFlag("-p")) {
  // skills.sh defaults to project scope.
} else {
  skillArgs.push("--global");
}

const agents = valuesFor("--agent").concat(valuesFor("-a"));
if (hasFlag("--codex")) agents.push("codex");
if (hasFlag("--agents")) agents.push("universal");
if (hasFlag("--claude")) agents.push("claude-code");
if (hasFlag("--pi")) agents.push("pi");
if (hasFlag("--all") || agents.length === 0) agents.push("*");

for (const agent of [...new Set(agents)]) {
  skillArgs.push("--agent", agent);
}

if (!hasFlag("--no-copy")) {
  skillArgs.push("--copy");
}
if (!hasFlag("--yes") && !hasFlag("-y")) {
  skillArgs.push("--yes");
}

if (hasFlag("--dry-run")) {
  console.log(`[dry-run] npx ${skillArgs.join(" ")}`);
  process.exit(0);
}

const result = spawnSync("npx", skillArgs, { stdio: "inherit" });
if (result.error) {
  console.error(`Failed to run skills.sh CLI via npx: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 0);
