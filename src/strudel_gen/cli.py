"""Typer CLI entrypoint — `strudel-gen` command with subcommands."""

import json
import logging
import subprocess
import time as _time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from strudel_gen.bridge import BridgeManager
from strudel_gen.detect import detect, platform_install_hints
from strudel_gen.logging_setup import setup_logging
from strudel_gen.normalize import normalize_to_dbfs, to_mp3
from strudel_gen.recorder import RecorderScript
from strudel_gen.render_orchestrator import render_tidal
from strudel_gen.sc import SCManager

app = typer.Typer(
    name="strudel-gen",
    help="Generative ambient soundscape pipeline: Strudel → SuperDirt → WAV",
)
console = Console()
logger = logging.getLogger(__name__)

# Pattern files shipped with the package
_PATTERNS_DIR = Path(__file__).resolve().parent.parent / "patterns"
_SC_DIR = Path(__file__).resolve().parent.parent / "supercollider"


def _write_render_sidecar(
    out_path: Path,
    pattern_file: Path | None,
    engine: str,
    duration: int,
    normalized: bool,
    mp3_path: Path | None = None,
    target_dbfs: float = -6.0,
) -> Path:
    """Write a JSON sidecar next to the output WAV describing the render."""
    sidecar = out_path.with_suffix(".json")
    data: dict[str, object] = {
        "pattern": str(pattern_file) if pattern_file else None,
        "engine": engine,
        "duration_s": duration,
        "wav": str(out_path),
        "mp3": str(mp3_path) if mp3_path else None,
        "normalized": normalized,
        "target_dbfs": target_dbfs if normalized else None,
        "rendered_at": datetime.now(UTC).isoformat(),
    }
    sidecar.write_text(json.dumps(data, indent=2))
    logger.info("Wrote render sidecar: %s", sidecar)
    return sidecar


def _render_via_sc_script(
    scd_path: Path,
    out_path: Path,
    duration: float,
    sclang: str | None = None,
    timeout: float = 300.0,
) -> int:
    """Run a self-contained .scd script that boots, plays, records and exits.

    The script receives output path and duration as positional argv, then
    manages its own SC server lifecycle.

    Args:
        scd_path: Absolute path to the .scd render script.
        out_path: Absolute path for the output WAV file.
        duration: Recording duration in seconds.
        sclang: Path to sclang binary. Auto-detected if None.
        timeout: Maximum seconds to wait before killing sclang.

    Returns:
        sclang exit code (0 = success).
    """
    from strudel_gen.detect import _find_sclang

    sclang = sclang or _find_sclang() or "sclang"
    cmd = [sclang, str(scd_path), str(out_path), str(int(duration))]
    logger.info("Running SC script: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        timeout=timeout,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.debug("[sclang] %s", line)
    if result.stderr:
        for line in result.stderr.splitlines():
            logger.debug("[sclang stderr] %s", line)
    logger.info("sclang exited with code %d", result.returncode)
    return result.returncode


@app.callback()
def main_callback() -> None:
    """Initialize process-wide logging for all CLI entrypoints."""
    setup_logging()


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
        status = "✓" if ok else "✗"
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
        console.print("\n[green]✓ All prerequisites found![/green]")
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
    from strudel_gen.patterns.render import render_pattern as _render

    raw = spec.read_text()
    pattern_spec = PatternSpec.model_validate_json(raw)
    rendered = _render(pattern_spec)
    out.write_text(rendered)
    logger.info("Rendered pattern to %s", out)
    console.print(f"[green]✓[/green] Pattern written to {out}")


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

    if dry_run:
        console.print(f"[dim]Waiting {duration}s...[/dim]")
        _time.sleep(duration)

    console.print("[bold]Shutting down...[/bold]")
    bridge.stop()
    sc.stop()
    console.print("[green]Session complete.[/green]")


@app.command()
def render(
    engine: Annotated[
        str,
        typer.Option(
            "--engine",
            "-e",
            help=(
                "Render engine: 'tidal' (Tidal Cycles + SuperDirt, requires ghci+Tidal), "
                "'sc-native' (self-contained SC script, no Tidal needed). "
                "Inferred from --pattern extension if not specified."
            ),
        ),
    ] = "auto",
    mood: Annotated[
        str, typer.Option("--mood", "-m", help="Mood description (used when no --pattern given)")
    ] = "ambient drone",
    duration: Annotated[
        int, typer.Option("--duration", "-d", help="Recording duration in seconds")
    ] = 120,
    out: Annotated[Path, typer.Option("--out", "-o", help="Output WAV file path")] = Path(
        "soundscape.wav"
    ),
    cpm: Annotated[int, typer.Option("--cpm", help="Cycles per minute (Strudel path)")] = 20,
    pattern_file: Annotated[
        Path | None,
        typer.Option(
            "--pattern",
            "-p",
            help=(
                "Pattern file to render. "
                ".scd = self-contained SC script (recommended for automation). "
                ".tidal = Tidal Cycles pattern; uses ghci + SuperDirt. "
                ".js  = Strudel pattern; requires the Strudel REPL to be playing."
            ),
        ),
    ] = None,
    no_normalize: Annotated[
        bool, typer.Option("--no-normalize", help="Skip ffmpeg normalization")
    ] = False,
    mp3: Annotated[
        int | None,
        typer.Option("--mp3", help="Encode an MP3 sidecar at this bitrate in kbps (e.g. 320)."),
    ] = None,
    timeout_sc: Annotated[float, typer.Option("--timeout-sc", help="SC boot timeout")] = 60.0,
    timeout_bridge: Annotated[
        float, typer.Option("--timeout-bridge", help="Bridge boot timeout")
    ] = 15.0,
) -> None:
    """Render a soundscape to WAV.

    Render paths (inferred from --pattern extension unless --engine is set):

     \b
    --engine tidal / .tidal  Tidal Cycles pattern.
                              Boots SC + SuperDirt, starts ghci with BootTidal.hs,
                              evaluates the pattern, synchronizes recording via
                              filesystem flag, records audio, then hushes and exits.
                              Requires Tidal Cycles to be installed.

    \b
    --engine sc-native / .scd  Self-contained SuperCollider script.
                                Boots SC, plays the pattern, records, and exits.
                                Does NOT need pnpm / Tidal / Strudel.

    \b
    .js  Strudel pattern (for when you have the Strudel REPL already playing).
         Boots SC + OSC bridge, then records whatever SuperDirt is producing.
         NOTE: you must manually paste and play the .js file in the Strudel
         REPL before running this command.
    """
    _ = (mood, cpm)  # reserved for future LLM/preset pattern selection

    det = detect()
    if not det.sclang:
        console.print("[red]sclang not found. Run `strudel-gen doctor --verbose`.[/red]")
        raise typer.Exit(1)

    out_path = out.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve engine from pattern extension if not explicitly set
    resolved_engine = engine
    if resolved_engine == "auto" and pattern_file:
        ext = Path(pattern_file).suffix.lower()
        if ext == ".tidal":
            resolved_engine = "tidal"
        elif ext == ".scd":
            resolved_engine = "sc-native"
        elif ext == ".js":
            resolved_engine = "strudel-bridge"

    # ------------------------------------------------------------------
    # Engine: Tidal Cycles .tidal pattern (filesystem-flag sync)
    # ------------------------------------------------------------------
    if resolved_engine == "tidal":
        tidal_path = (pattern_file or Path()).expanduser().resolve() if pattern_file else None
        if not tidal_path or not tidal_path.exists():
            console.print(
                "[red]A valid --pattern <file>.tidal is required for --engine tidal[/red]"
            )
            raise typer.Exit(1)

        console.print(f"[bold]Tidal pattern:[/bold] {tidal_path.name}")
        console.print("[bold]Rendering via Tidal Cycles + SuperDirt...[/bold]")
        try:
            render_tidal(
                pattern_path=tidal_path,
                out_path=out_path,
                duration=float(duration),
                no_normalize=no_normalize,
            )
        except Exception as exc:
            console.print(f"[red]Render failed: {exc}[/red]")
            raise typer.Exit(1) from exc

    # ------------------------------------------------------------------
    # Engine: self-contained .scd script (preferred for automation)
    # ------------------------------------------------------------------
    elif resolved_engine == "sc-native":
        scd_path = (pattern_file or Path()).expanduser().resolve() if pattern_file else None
        if not scd_path or not scd_path.exists():
            ext_hint = ".scd" if resolved_engine == "sc-native" else ""
            console.print(
                f"[red]A valid --pattern <file>{ext_hint} is required for --engine"
                f" {resolved_engine}[/red]"
            )
            raise typer.Exit(1)

        console.print(f"[bold]Rendering via SC script:[/bold] {scd_path.name}")
        console.print(f"[dim]Output → {out_path}  |  Duration: {duration}s[/dim]")

        timeout = float(duration) + timeout_sc + 120.0
        rc = _render_via_sc_script(scd_path, out_path, float(duration), timeout=timeout)

        if rc != 0:
            console.print(f"[red]sclang exited with code {rc}. Check logs for details.[/red]")
            raise typer.Exit(rc)

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
            raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Engine: Strudel .js pattern (needs running REPL + bridge)
    # ------------------------------------------------------------------
    else:
        if pattern_file:
            console.print(f"[bold]Pattern:[/bold] {pattern_file}")
            console.print(
                "[yellow]NOTE: paste and play this file in the Strudel REPL "
                "before continuing.[/yellow]"
            )
        else:
            console.print(
                "[yellow]No --pattern given. Recording whatever SuperDirt produces.[/yellow]"
            )

        console.print("[bold]Booting SuperCollider...[/bold]")
        sc_mgr = SCManager(timeout=timeout_sc)
        sc_mgr.start()

        console.print("[bold]Starting OSC bridge...[/bold]")
        bridge_mgr = BridgeManager(timeout=timeout_bridge)
        bridge_mgr.start()

        try:
            rec = RecorderScript(output_path=out_path, duration=float(duration))
            script = rec.generate()
            logger.debug("Recording script:\n%s", script)

            console.print("[bold]Triggering recording...[/bold]")
            result = subprocess.run(
                ["sclang", "-"],
                input=script,
                capture_output=True,
                text=True,
                timeout=duration + 30,
            )
            logger.info("sclang recording exited with code %d", result.returncode)
            if result.stderr:
                logger.debug("sclang stderr: %s", result.stderr[:500])
        finally:
            console.print("[bold]Shutting down...[/bold]")
            bridge_mgr.stop()
            sc_mgr.stop()

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
            raise typer.Exit(1)

    # Common post-render: optional MP3 encode + JSON sidecar
    if out_path.exists():
        mp3_path: Path | None = None
        if mp3 is not None:
            try:
                mp3_path = to_mp3(out_path, mp3)
                console.print(f"[green]MP3:[/green] {mp3_path}")
            except Exception as exc:
                logger.warning("MP3 encoding skipped: %s", exc)
                console.print(f"[yellow]MP3 warning: {exc}[/yellow]")

        sidecar = _write_render_sidecar(
            out_path=out_path,
            pattern_file=pattern_file,
            engine=resolved_engine,
            duration=duration,
            normalized=not no_normalize,
            mp3_path=mp3_path,
        )
        console.print(f"[dim]Sidecar: {sidecar}[/dim]")

    console.print("[green]Render complete.[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
