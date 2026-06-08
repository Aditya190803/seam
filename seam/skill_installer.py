from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

SKILL_NAME = "seam-code-search"


@dataclass(slots=True)
class SkillInstallResult:
    agent: str
    path: Path

    def to_dict(self) -> dict[str, str]:
        return {"agent": self.agent, "path": str(self.path)}


def _skill_resource():  # type: ignore[no-untyped-def]
    return resources.files("seam.agent_skill").joinpath(SKILL_NAME)


def install_agent_skill(
    *,
    codex: bool = True,
    claude: bool = True,
    project: bool = False,
    root: Path | None = None,
    interactive: bool = False,
) -> list[SkillInstallResult]:
    """Install the bundled skill non-interactively, or delegate to the npm TUI."""
    if interactive:
        try:
            subprocess.run(["npx", "@aditya190803/seam-skill", "install"], check=True)
        except FileNotFoundError:
            print(
                "Error: npx not found. Install Node.js (https://nodejs.org) ",
                "or use the Seam curl installer which includes the skill:\n"
                "  curl -fsSL https://seam.adityamer.dev/install.sh | bash -s -- --with-skills",
                file=sys.stderr,
            )
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            sys.exit(exc.returncode)
        return []

    if not codex and not claude:
        raise ValueError("At least one of codex or claude must be enabled")

    base = (root or Path.cwd()).expanduser().resolve() if project else Path.home()
    targets: list[tuple[str, Path]] = []
    if codex:
        targets.append(("Codex", base / ".agents" / "skills" / SKILL_NAME))
    if claude:
        targets.append(("Claude Code", base / ".claude" / "skills" / SKILL_NAME))

    results: list[SkillInstallResult] = []
    with resources.as_file(_skill_resource()) as source:
        if not source.exists():
            raise FileNotFoundError(f"Bundled skill not found: {source}")
        for agent, destination in targets:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
            results.append(SkillInstallResult(agent=agent, path=destination))
    return results
