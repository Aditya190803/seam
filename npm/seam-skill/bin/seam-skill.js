#!/usr/bin/env node
const fs = require("fs");
const os = require("os");
const path = require("path");

const args = process.argv.slice(2);
const command = args[0];
const flags = new Set(args.slice(1));

function help() {
  console.log(`Seam agent skill installer

Usage:
  npx @aditya190803/seam-skill install [options]

Options:
  --codex       Install only for Codex (~/.agents/skills or ./.agents/skills)
  --claude      Install only for Claude Code (~/.claude/skills or ./.claude/skills)
  --user        Install to user-level skill directories (default)
  --project     Install to project-level skill directories in the current directory
  --dry-run     Print planned actions without writing files
  --help        Show this help

Examples:
  npx @aditya190803/seam-skill install
  npx @aditya190803/seam-skill install --project
  npx @aditya190803/seam-skill install --codex
  npx @aditya190803/seam-skill install --claude --project
`);
}

if (!command || command === "--help" || command === "-h" || flags.has("--help") || flags.has("-h")) {
  help();
  process.exit(0);
}

if (command !== "install") {
  console.error(`Unknown command: ${command}`);
  help();
  process.exit(1);
}

const installCodex = flags.has("--codex") || !flags.has("--claude");
const installClaude = flags.has("--claude") || !flags.has("--codex");
const projectScope = flags.has("--project");
const userScope = flags.has("--user") || !projectScope;
const dryRun = flags.has("--dry-run");

const packageRoot = path.resolve(__dirname, "..");
const source = path.join(packageRoot, "skills", "seam-code-search");

function targetRoots() {
  const roots = [];
  if (installCodex) {
    roots.push({ agent: "Codex", root: userScope ? path.join(os.homedir(), ".agents", "skills") : path.join(process.cwd(), ".agents", "skills") });
  }
  if (installClaude) {
    roots.push({ agent: "Claude Code", root: userScope ? path.join(os.homedir(), ".claude", "skills") : path.join(process.cwd(), ".claude", "skills") });
  }
  return roots;
}

function copySkill(root) {
  const destination = path.join(root, "seam-code-search");
  if (dryRun) {
    console.log(`[dry-run] install ${source} -> ${destination}`);
    return destination;
  }
  fs.mkdirSync(root, { recursive: true });
  fs.rmSync(destination, { recursive: true, force: true });
  fs.cpSync(source, destination, { recursive: true });
  return destination;
}

if (!fs.existsSync(source)) {
  console.error(`Bundled skill not found: ${source}`);
  process.exit(1);
}

for (const target of targetRoots()) {
  const destination = copySkill(target.root);
  console.log(`✓ Installed Seam Code Search skill for ${target.agent}: ${destination}`);
}

console.log("\nNext steps:");
console.log("  1. Install the Seam CLI if needed:");
console.log("     curl -fsSL https://seam.adityamer.dev/install.sh | bash");
console.log("  2. In a repo, run: seam init .");
console.log("  3. Ask your agent to use the seam-code-search skill before reading many files.");
