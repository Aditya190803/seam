from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config, resolve_repo, set_config_value
from .context import build_context
from .doctor import run_doctor
from .indexer import index_repo, index_status
from .mcp_server import run_mcp_server
from .portability import export_index, import_index
from .search import search_code
from .skill_installer import install_agent_skill
from .watch import watch_repo

app = typer.Typer(help="Seam: index a codebase once, query it from any agent.", no_args_is_help=True)
config_app = typer.Typer(help="Manage Seam configuration.", no_args_is_help=True)
app.add_typer(config_app, name="config")
console = Console()


def _path(value: Path | None) -> Path:
    return (value or Path.cwd()).expanduser().resolve()


@app.command("init")
def init_command(
    path: Path | None = typer.Argument(None, help="Repository path to index. Defaults to current directory."),
    force: bool = typer.Option(False, "--force", help="Rebuild the index from scratch."),
) -> None:
    """Index a codebase for the first time or refresh an existing index."""
    repo_path = _path(path)
    with console.status(f"Indexing {repo_path}..."):
        stats = index_repo(repo_path, force=force)
    console.print(f"✓ Indexed [bold]{stats.files}[/bold] files into [bold]{stats.chunks}[/bold] chunks")
    console.print(f"✓ Backend: {stats.backend}; embeddings: {stats.embedding_provider}/{stats.embedding_model}")
    console.print(f"✓ Stored at {stats.index_path}")
    if stats.languages:
        langs = ", ".join(f"{lang} ({count})" for lang, count in sorted(stats.languages.items()))
        console.print(f"✓ Detected languages: {langs}")


@app.command("reindex")
def reindex_command(
    path: Path | None = typer.Argument(None, help="Repository path to re-index. Defaults to current directory or only indexed repo."),
) -> None:
    """Force a full re-index."""
    if path is None:
        entry = resolve_repo(None)
        repo_path = Path(entry["path"])
    else:
        repo_path = _path(path)
    with console.status(f"Re-indexing {repo_path}..."):
        stats = index_repo(repo_path, force=True)
    console.print(f"✓ Re-indexed {stats.files} files into {stats.chunks} chunks")


@app.command("search")
def search_command(
    query_parts: list[str] = typer.Argument(..., help="Natural language search query."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    top: int = typer.Option(5, "--top", min=1, max=100, help="Number of results to return."),
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
    language: str | None = typer.Option(None, "--language", help="Filter to a language, e.g. python."),
) -> None:
    """Semantic search over an indexed codebase."""
    query = " ".join(query_parts)
    results = search_code(query, top_k=top, path=path, language=language)
    if json_output:
        console.print_json(json.dumps([result.to_dict() for result in results]))
        return

    if not results:
        console.print("No results.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right", width=3)
    table.add_column("Score", justify="right", width=7)
    table.add_column("File")
    table.add_column("Lines", width=12)
    table.add_column("Name")
    for result in results:
        table.add_row(
            str(result.rank),
            f"{result.score:.2f}",
            result.file,
            f"L{result.start_line}–{result.end_line}",
            result.name or "",
        )
    console.print(table)

    for result in results:
        console.print(f"\n[bold]{result.rank}. {result.file}:L{result.start_line}–{result.end_line}[/bold]")
        console.print(result.snippet.rstrip())


@app.command("context")
def context_command(
    query_parts: list[str] = typer.Argument(..., help="Natural language search query."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, xml, or json."),
    top: int = typer.Option(5, "--top", min=1, max=100, help="Number of chunks to include."),
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
    language: str | None = typer.Option(None, "--language", help="Filter to a language, e.g. python."),
) -> None:
    """Generate ready-to-paste context from search results."""
    query = " ".join(query_parts)
    try:
        console.print(build_context(query, top_k=top, path=path, language=language, fmt=fmt), end="")
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("status")
def status_command(
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Show index freshness, file count, backend, and model."""
    stats = index_status(path)
    if json_output:
        console.print_json(json.dumps(stats.to_dict()))
        return

    table = Table(show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in stats.to_dict().items():
        if key == "languages":
            value = ", ".join(f"{k}: {v}" for k, v in sorted(value.items())) or "none"
        table.add_row(key, str(value))
    console.print(table)


@app.command("watch")
def watch_command(
    path: Path | None = typer.Argument(None, help="Repository path to watch. Defaults to current directory."),
    health_port: int = typer.Option(7731, "--health-port", help="Health endpoint port."),
) -> None:
    """Start a background watcher that refreshes the index on changes."""
    repo_path = _path(path)
    console.print(f"Watching {repo_path}")
    console.print(f"Health: http://127.0.0.1:{health_port}/health")
    watch_repo(repo_path, health_port=health_port)


@app.command("doctor")
def doctor_command(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """Check Seam configuration, dependencies, and service reachability."""
    checks = run_doctor()
    if json_output:
        console.print_json(json.dumps([check.to_dict() for check in checks]))
        raise typer.Exit(0 if all(check.ok for check in checks) else 1)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", width=8)
    table.add_column("Check")
    table.add_column("Detail")
    table.add_column("Hint")
    for check in checks:
        table.add_row("✓" if check.ok else "✗", check.name, check.detail, check.hint or "")
    console.print(table)
    raise typer.Exit(0 if all(check.ok for check in checks) else 1)


@app.command("install-skill")
def install_skill_command(
    codex: bool = typer.Option(True, "--codex/--no-codex", help="Install the Codex skill."),
    claude: bool = typer.Option(True, "--claude/--no-claude", help="Install the Claude Code skill."),
    project: bool = typer.Option(False, "--project", help="Install into .agents/.claude in the current project instead of user home."),
) -> None:
    """Install the Seam Code Search Agent Skill for Codex and Claude Code."""
    try:
        results = install_agent_skill(codex=codex, claude=claude, project=project)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    for result in results:
        console.print(f"✓ Installed Seam Code Search skill for {result.agent}: {result.path}")


@app.command("export")
def export_command(
    archive: Path = typer.Argument(..., help="Output .tar.gz archive path."),
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
) -> None:
    """Export a local Seam index archive."""
    result = export_index(archive, repo_path=path)
    console.print(f"✓ Exported index for {result['repo']['path']} to {result['archive']}")


@app.command("import")
def import_command(
    archive: Path = typer.Argument(..., help="Input archive created by seam export."),
    path: Path | None = typer.Option(None, "--path", help="Repository path to associate with the imported index."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing local index for this repo."),
) -> None:
    """Import a local Seam index archive."""
    result = import_index(archive, repo_path=path, overwrite=overwrite)
    console.print(f"✓ Imported index for {result['repo']['path']} to {result['index_path']}")


@app.command("serve")
def serve_command(
    http: int | None = typer.Option(None, "--http", help="Serve MCP over HTTP on this port. Defaults to stdio transport."),
) -> None:
    """Start the MCP server."""
    if http is None:
        console.print("Starting Seam MCP server on stdio transport")
    else:
        console.print(f"Starting Seam MCP server at http://127.0.0.1:{http}")
    run_mcp_server(http_port=http)


@config_app.command("show")
def config_show(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """Print current configuration."""
    config = load_config()
    if json_output:
        console.print_json(json.dumps(config.to_dict()))
        return
    table = Table(show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in config.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)


@config_app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)) -> None:
    """Set a config key."""
    try:
        config = set_config_value(key, value)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"✓ Set {key} = {getattr(config, key)}")


def main() -> None:
    app()
