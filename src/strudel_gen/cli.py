"""Typer CLI entrypoint — `strudel-gen` command with subcommands."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from strudel_gen.detect import detect, platform_install_hints
from strudel_gen.logging_setup import setup_logging

app = typer.Typer(
    name="strudel-gen",
    help="Generative ambient soundscape pipeline: Strudel \u2192 SuperDirt \u2192 WAV",
)
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def doctor(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed detection info")
    ] = False,
) -> None:
    """Check whether all prerequisites are installed."""
    result = detect()
    hints = platform_install_hints(result)

    table = Table(title="strudel-gen environment check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Path", style="dim")

    strudel_path = str(result.strudel_dir) if result.strudel_dir else "NOT FOUND"
    components: list[tuple[str, bool, str]] = [
        ("sclang (SuperCollider)", result.sclang is not None, result.sclang or "NOT FOUND"),
        ("node", result.node is not None, result.node or "NOT FOUND"),
        ("pnpm", result.pnpm is not None, result.pnpm or "NOT FOUND"),
        ("Strudel clone", result.strudel_dir is not None, strudel_path),
    ]

    all_ok = True
    for name, ok, path in components:
        status = "\u2713" if ok else "\u2717"
        if not ok:
            all_ok = False
        table.add_row(name, status, path)

    console.print(
        f"\nPlatform: [bold]{result.os_name}[/bold]" + (" (WSL)" if result.is_wsl else "")
    )
    console.print(table)

    if verbose and hints:
        console.print("\n[bold yellow]Install hints for missing components:[/bold yellow]")
        for comp, hint in hints.items():
            console.print(f"  [bold]{comp}:[/bold] {hint}")

    if all_ok:
        console.print("\n[green]\u2713 All prerequisites found![/green]")
        raise typer.Exit(0)
    else:
        console.print(
            "\n[yellow]Some prerequisites are missing. "
            "Run with --verbose for install hints.[/yellow]"
        )
        raise typer.Exit(1)


@app.command()
def render_pattern(
    spec: Annotated[Path, typer.Option(..., "--spec", help="Path to pattern spec JSON")],
    out: Annotated[Path, typer.Option(..., "--out", help="Output .js file path")],
) -> None:
    """Render a PatternSpec JSON into a Strudel .js file."""
    from strudel_gen.patterns.model import PatternSpec
    from strudel_gen.patterns.render import render_pattern

    raw = spec.read_text()
    pattern_spec = PatternSpec.model_validate_json(raw)
    rendered = render_pattern(pattern_spec)
    out.write_text(rendered)
    logger.info("Rendered pattern to %s", out)
    console.print(f"[green]\u2713[/green] Pattern written to {out}")


def main() -> None:
    setup_logging()
    app()


if __name__ == "__main__":
    main()
