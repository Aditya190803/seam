from __future__ import annotations

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config, load_registry, resolve_repo, set_config_value
from .context import build_context
from .doctor import run_doctor
from .indexer import gc_index, index_repo, index_size, index_status
from .mcp_server import run_mcp_server
from .portability import export_index, import_index
from .search import search_code
from .skill_installer import install_agent_skill as _install_skill
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
    warm: bool = typer.Option(False, "--warm", help="Warm local index files after indexing."),
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
    if warm:
        _warm_index(Path(stats.index_path))
        console.print("✓ Warmed index cache")


@app.command("reindex")
def reindex_command(
    path: Path | None = typer.Argument(None, help="Repository, file, or directory path to re-index. Defaults to current directory or only indexed repo."),
) -> None:
    """Force a re-index of a repository, file, or directory subtree."""
    scope = None
    force = True
    if path is None:
        entry = resolve_repo(None)
        repo_path = Path(entry["path"])
    else:
        target = _path(path)
        if target.is_file():
            repo_path = _repo_for_scope(target)
            scope = target
            force = False
        elif _is_inside_indexed_repo(target):
            repo_path = _repo_for_scope(target)
            scope = target
            force = False
        else:
            repo_path = target
    label = f"{scope} in {repo_path}" if scope else str(repo_path)
    with console.status(f"Re-indexing {label}..."):
        stats = index_repo(repo_path, force=force, scope=scope)
    console.print(f"✓ Re-indexed {stats.files} files into {stats.chunks} chunks")
    if stats.updated_file_paths:
        console.print(f"✓ Updated: {', '.join(stats.updated_file_paths)}")
    if stats.deleted_file_paths:
        console.print(f"✓ Deleted: {', '.join(stats.deleted_file_paths)}")


def _repo_for_scope(scope: Path) -> Path:
    resolved = scope.resolve()
    registry = load_registry()
    candidates = [Path(entry["path"]).resolve() for entry in registry.get("repos", {}).values()]
    matches = [candidate for candidate in candidates if resolved.is_relative_to(candidate)]
    if matches:
        return max(matches, key=lambda candidate: len(str(candidate)))
    return Path(resolve_repo(None)["path"])


def _is_inside_indexed_repo(path: Path) -> bool:
    resolved = path.resolve()
    registry = load_registry()
    return any(resolved.is_relative_to(Path(entry["path"]).resolve()) for entry in registry.get("repos", {}).values())


@app.command("search")
def search_command(
    query_parts: list[str] = typer.Argument(..., help="Natural language search query."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    top: int = typer.Option(5, "--top", min=1, max=100, help="Number of results to return."),
    path: list[Path] | None = typer.Option(None, "--path", help="Indexed repository path. Can be passed multiple times."),
    language: str | None = typer.Option(None, "--language", help="Filter to a language, e.g. python."),
    name: str | None = typer.Option(None, "--name", help="Filter to filename glob, e.g. '*.py' or 'src/*'."),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Exclude filename glob. Can be passed multiple times."),
    min_score: float | None = typer.Option(None, "--min-score", min=0.0, help="Discard results below this score."),
    alpha: float | None = typer.Option(None, "--alpha", min=0.0, max=1.0, help="Hybrid weighting: 1.0=vector only, 0.0=keyword only."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode: hybrid, semantic, or keyword."),
    exact: bool = typer.Option(False, "--exact", help="Treat the query as a literal or regex pattern."),
    no_dedup: bool = typer.Option(False, "--no-dedup", help="Return duplicate chunks instead of deduplicating by content hash."),
    all_repos: bool = typer.Option(False, "--all-repos", help="Search all indexed repositories."),
    changed: bool = typer.Option(False, "--changed", help="Restrict to files changed since the index."),
    count: bool = typer.Option(False, "--count", help="Print result counts per file."),
) -> None:
    """Semantic search over an indexed codebase."""
    query = " ".join(query_parts)
    started_at = time.perf_counter()
    if mode:
        normalized_mode = mode.lower()
        if normalized_mode == "semantic":
            alpha = 1.0
        elif normalized_mode == "keyword":
            alpha = 0.0
        elif normalized_mode != "hybrid":
            raise typer.BadParameter("--mode must be one of: hybrid, semantic, keyword")
    repo_paths = [Path(entry["path"]) for entry in load_registry().get("repos", {}).values()] if all_repos else list(path or [None])
    results = []
    candidate_top = 100 if changed else top
    for repo_path in repo_paths:
        results.extend(
            search_code(
                query,
                top_k=candidate_top,
                path=repo_path,
                language=language,
                name=name,
                exclude=exclude,
                min_score=min_score,
                exact=exact,
                dedup=not no_dedup,
                alpha=alpha,
            )
        )
    if changed:
        changed_files = set()
        for repo_path in repo_paths:
            status = index_status(repo_path)
            changed_files.update(status.updated_file_paths)
        results = [result for result in results if result.file in changed_files]
    results.sort(key=lambda result: result.score, reverse=True)
    for rank, result in enumerate(results[:top], start=1):
        result.rank = rank
    results = results[:top]
    if count:
        _print_counts(results, json_output=json_output, duration_ms=(time.perf_counter() - started_at) * 1000)
        return
    _print_search_results(results, json_output=json_output, duration_ms=(time.perf_counter() - started_at) * 1000)


def _print_search_results(results: list, *, json_output: bool, duration_ms: float | None = None) -> None:
    if json_output:
        payload = {"duration_ms": round(duration_ms or 0.0, 3), "results": [result.to_dict() for result in results]}
        console.print_json(json.dumps(payload))
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


def _print_counts(results: list, *, json_output: bool, duration_ms: float | None = None) -> None:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.file] = counts.get(result.file, 0) + 1
    if json_output:
        console.print_json(json.dumps({"duration_ms": round(duration_ms or 0.0, 3), "counts": counts}))
        return
    for file, value in sorted(counts.items()):
        console.print(f"{file}: {value}")


@app.command("grep")
def grep_command(
    pattern_parts: list[str] = typer.Argument(..., help="Literal or regex pattern to search for."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    top: int = typer.Option(20, "--top", min=1, max=500, help="Number of results to return."),
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
    language: str | None = typer.Option(None, "--language", help="Filter to a language, e.g. python."),
    name: str | None = typer.Option(None, "--name", help="Filter to filename glob, e.g. '*.py' or 'src/*'."),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="Exclude filename glob. Can be passed multiple times."),
) -> None:
    """Exact literal/regex search over indexed chunks."""
    pattern = " ".join(pattern_parts)
    started_at = time.perf_counter()
    results = search_code(pattern, top_k=top, path=path, language=language, name=name, exclude=exclude, exact=True)
    _print_search_results(results, json_output=json_output, duration_ms=(time.perf_counter() - started_at) * 1000)


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
    size: bool = typer.Option(False, "--size", help="Include index size on disk."),
) -> None:
    """Show index freshness, file count, backend, and model."""
    try:
        stats = index_status(path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"{exc} Initialize the index with `seam init .`.") from exc
    payload = stats.to_dict()
    if size:
        payload["size_bytes"] = index_size(path)
    if json_output:
        console.print_json(json.dumps(payload))
        return

    table = Table(show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in payload.items():
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


@app.command("check")
def check_command() -> None:
    """Script-friendly health check. Exits 0 when healthy, non-zero with one issue line otherwise."""
    checks = run_doctor()
    failed = next((check for check in checks if not check.ok), None)
    if failed is None:
        console.print("ok")
        return
    console.print(f"{failed.name}: {failed.detail}. {failed.hint or 'Run `seam doctor` for details.'}")
    raise typer.Exit(1)


@app.command("gc")
def gc_command(
    path: Path | None = typer.Option(None, "--path", help="Indexed repository path."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Remove index entries for files no longer on disk."""
    removed = gc_index(path)
    if json_output:
        console.print_json(json.dumps({"removed": removed, "removed_files": len(removed)}))
        return
    console.print(f"✓ Removed {len(removed)} stale files")


def _warm_index(index_path: Path) -> None:
    for file in index_path.rglob("*"):
        if file.is_file():
            with file.open("rb") as handle:
                while handle.read(1024 * 1024):
                    pass


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
    interactive: bool = typer.Option(False, "--interactive", help="Launch the interactive npx installer."),
) -> None:
    """Install the Seam Code Search Agent Skill for Codex and Claude Code."""
    try:
        results = _install_skill(codex=codex, claude=claude, project=project, interactive=interactive)
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


@config_app.command("list")
def config_list(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """Alias for `seam config show`."""
    config_show(json_output=json_output)


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
