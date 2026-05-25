"""Typer CLI entrypoint — `strudel-gen` command with subcommands."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from strudel_gen.bridge import BridgeManager
from strudel_gen.detect import detect, platform_install_hints
from strudel_gen.logging_setup import setup_logging
from strudel_gen.normalize import normalize_to_dbfs
from strudel_gen.recorder import RecorderScript
from strudel_gen.sc import SCManager

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


@app.command()
def session(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Boot and tear down without rendering")
    ] = False,
    duration: Annotated[
        int, typer.Option("--duration", "-d", help="Recording duration in seconds")
    ] = 10,
    timeout_sc: Annotated[
        float, typer.Option("--timeout-sc", help="Seconds to wait for SC boot")
    ] = 60.0,
    timeout_bridge: Annotated[
        float, typer.Option("--timeout-bridge", help="Seconds to wait for bridge")
    ] = 15.0,
) -> None:
    """Run a full recording session: boot SC, start bridge, record."""
    result = detect()
    if not result.sclang:
        console.print("[red]sclang not found. Run `strudel-gen doctor` for install hints.[/red]")
        raise typer.Exit(1)
    if not result.strudel_dir:
        console.print("[red]Strudel clone not found. Set STRUDEL_DIR env var.[/red]")
        raise typer.Exit(1)

    console.print("[bold]Starting SuperCollider...[/bold]")
    sc = SCManager(timeout=timeout_sc)
    sc.start()

    console.print("[bold]Starting OSC bridge...[/bold]")
    bridge = BridgeManager(timeout=timeout_bridge)
    bridge.start()

    console.print(f"[green]Session active. Duration: {duration}s (dry_run={dry_run})[/green]")

    # Let it run or record
    if dry_run:
        import time as _time

        console.print(f"[dim]Waiting {duration}s...[/dim]")
        _time.sleep(duration)

    console.print("[bold]Shutting down...[/bold]")
    bridge.stop()
    sc.stop()
    console.print("[green]Session complete.[/green]")


@app.command()
def render(
    _mood: Annotated[str, typer.Option("--mood", "-m", help="Mood description")] = "ambient drone",
    duration: Annotated[
        int, typer.Option("--duration", "-d", help="Recording duration in seconds")
    ] = 30,
    out: Annotated[Path, typer.Option("--out", "-o", help="Output WAV file path")] = Path(
        "soundscape.wav"
    ),
    _cpm: Annotated[int, typer.Option("--cpm", help="Cycles per minute")] = 20,
    pattern_file: Annotated[
        Path | None, typer.Option("--pattern", "-p", help="Path to a Strudel .js pattern file")
    ] = None,
    no_normalize: Annotated[
        bool, typer.Option("--no-normalize", help="Skip ffmpeg normalization")
    ] = False,
    timeout_sc: Annotated[float, typer.Option("--timeout-sc", help="SC boot timeout")] = 60.0,
    timeout_bridge: Annotated[
        float, typer.Option("--timeout-bridge", help="Bridge boot timeout")
    ] = 15.0,
) -> None:
    """Render a soundscape: boot services, record, normalize."""
    # _mood and _cpm reserved for future PatternSpec generation
    _ = (_mood, _cpm)
    det = detect()
    if not det.sclang:
        console.print("[red]sclang not found. Run `strudel-gen doctor` for hints.[/red]")
        raise typer.Exit(1)

    # Resolve output path
    out_path = out.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    console.print("[bold]Booting SuperCollider...[/bold]")
    sc_mgr = SCManager(timeout=timeout_sc)
    sc_mgr.start()

    console.print("[bold]Starting OSC bridge...[/bold]")
    bridge_mgr = BridgeManager(timeout=timeout_bridge)
    bridge_mgr.start()

    try:
        if pattern_file:
            pattern_path = pattern_file.expanduser().resolve()
            if pattern_path.exists():
                console.print(f"Pattern file: {pattern_path}")
                logger.info("Using pattern file: %s", pattern_path)
            else:
                logger.warning("Pattern file not found: %s", pattern_path)

        console.print("[bold]Triggering recording...[/bold]")
        rec = RecorderScript(
            output_path=out_path,
            duration=float(duration),
        )
        script = rec.generate()
        logger.debug("Recording script:\n%s", script)

        import subprocess

        record_result = subprocess.run(
            ["sclang", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=duration + 30,
        )
        logger.info("sclang recording exited with code %d", record_result.returncode)
        if record_result.stderr:
            logger.debug("sclang stderr: %s", record_result.stderr[:500])

        if out_path.exists():
            file_size = out_path.stat().st_size
            console.print(f"[green]Recorded {out_path} ({file_size / 1024:.1f} KB)[/green]")

            if not no_normalize:
                try:
                    console.print("[dim]Normalizing to -6 dBFS...[/dim]")
                    normalized = normalize_to_dbfs(out_path, target=-6.0)
                    console.print(f"[green]Normalized: {normalized}[/green]")
                except Exception as exc:
                    logger.warning("Normalization skipped: %s", exc)
                    console.print(f"[yellow]Normalization warning: {exc}[/yellow]")
        else:
            console.print("[red]Output file not found — recording may have failed.[/red]")

    finally:
        console.print("[bold]Shutting down...[/bold]")
        bridge_mgr.stop()
        sc_mgr.stop()

    console.print("[green]Render complete.[/green]")


def main() -> None:
    setup_logging()
    app()


if __name__ == "__main__":
    main()
