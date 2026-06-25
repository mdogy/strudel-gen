"""Render orchestrator — coordinates SC + Tidal + recorder + normalize."""

import contextlib
import logging
import subprocess
import tempfile
import threading
import time as _time
from pathlib import Path

from strudel_gen.normalize import normalize_to_dbfs
from strudel_gen.tidal_manager import TidalManager

logger = logging.getLogger(__name__)

_TIDAL_TIMEOUT = 90.0
_SC_TIMEOUT = 180.0


def _sc_stdout_drainer(
    stream: object,
    stop_event: threading.Event,
) -> None:
    """Drain sclang's stdout to prevent pipe-buffer deadlock.

    Runs in a daemon thread after SuperDirt is ready; discards lines
    until the process exits (signaled by stop_event or EOF).
    """
    assert hasattr(stream, "readline")
    while not stop_event.is_set():
        try:
            line = stream.readline()  # type: ignore[attr-defined]
            if not line:
                break
        except ValueError:
            break


def render_tidal(
    pattern_path: Path,
    out_path: Path,
    duration: float,
    no_normalize: bool = False,
    flag_poll_max: float = 600.0,
) -> None:
    """Render a .tidal pattern to WAV via SuperDirt.

    Uses the filesystem-flag synchronization pattern to avoid recording
    silence before Tidal OSC events start flowing.

    Args:
        pattern_path: Path to the .tidal file.
        out_path: Absolute output WAV path.
        duration: Recording duration in seconds.
        no_normalize: Skip ffmpeg normalization to -6 dBFS.
        flag_poll_max: Max seconds sclang polls for the flag before aborting.
    """
    flag_dir = Path(tempfile.mkdtemp(prefix="tidal-render-"))
    flag = flag_dir / "start-record.flag"

    record_scd = _make_record_scd(out_path, duration, flag, flag_poll_max)

    with tempfile.NamedTemporaryFile(suffix=".scd", mode="w", delete=False) as f:
        f.write(record_scd)
        tmp_scd = Path(f.name)

    try:
        logger.info("Starting SuperCollider with recording-trigger script...")
        sc_proc = subprocess.Popen(
            ["sclang", str(tmp_scd)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        drain_stop = threading.Event()

        deadline = _time.monotonic() + _SC_TIMEOUT
        superdirt_ready = False
        assert sc_proc.stdout is not None
        while _time.monotonic() < deadline:
            line = sc_proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            logger.debug("[sc] %s", line[:120])
            if "SuperDirt: listening" in line:
                superdirt_ready = True
                logger.info("SuperDirt ready.")
                # Start draining stdout in background to prevent
                # pipe-buffer deadlock and capture DIAG lines.
                drainer = threading.Thread(
                    target=_sc_stdout_drainer,
                    args=(sc_proc.stdout, drain_stop),
                    daemon=True,
                )
                drainer.start()
                break

        if not superdirt_ready:
            logger.error("SuperDirt did not become ready within %ss", _SC_TIMEOUT)
            sc_proc.terminate()
            raise RuntimeError("SuperDirt did not become ready")

        logger.info("Starting Tidal ghci...")
        tidal = TidalManager(timeout=_TIDAL_TIMEOUT)
        tidal.start()
        logger.info("Tidal ready.")

        logger.info("Evaluating pattern...")
        for line in pattern_path.read_text().strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("--"):
                logger.debug("  > %s", line)
                tidal.eval(line)

        logger.info("Letting pattern settle (2 s)...")
        _time.sleep(2.0)

        logger.info("Triggering recording (touching %s)...", flag)
        flag.touch()

        logger.info("Waiting for sclang to finish recording (~%d s)...", int(duration + 5))
        try:
            sc_proc.wait(timeout=duration + 60)
            logger.info("sclang exited with code %d", sc_proc.returncode)
        except subprocess.TimeoutExpired:
            logger.error("sclang did not exit within budget; killing")
            sc_proc.kill()
            sc_proc.wait(timeout=5)

        logger.info("Hushing Tidal...")
        tidal.hush()
        logger.info("Shutting down Tidal...")
        tidal.stop()

    finally:
        drain_stop.set()
        tmp_scd.unlink(missing_ok=True)
        try:
            flag.unlink(missing_ok=True)
            flag_dir.rmdir()
        except OSError:
            pass

    if out_path.exists():
        size = out_path.stat().st_size
        logger.info("Output: %s (%.1f KB)", out_path, size / 1024)
        _check_audio_level(out_path)
        if not no_normalize:
            try:
                normed = normalize_to_dbfs(out_path, target=-6.0)
                logger.info("Normalized: %s", normed)
            except Exception as exc:
                logger.warning("Normalization skipped: %s", exc)
    else:
        raise RuntimeError(f"Output file not found: {out_path}")


def _make_record_scd(
    out_path: Path,
    duration: float,
    flag: Path,
    flag_poll_max: float = 600.0,
) -> str:
    """Generate an sclang script that starts recording on a filesystem flag."""
    return (
        f"(\n"
        f"s.waitForBoot {{\n"
        f'    s.recHeaderFormat = "WAV";\n'
        f'    s.recSampleFormat = "int24";\n'
        f"    s.recChannels = 2;\n"
        f"    fork {{\n"
        f'        var flagPath = "{flag}";\n'
        f"        var maxWait = {int(flag_poll_max)};\n"
        f"        var waited  = 0;\n"
        f"        while {{ (File.exists(flagPath).not) and: {{ waited < maxWait }} }} {{\n"
        f"            0.25.wait;\n"
        f"            waited = waited + 0.25;\n"
        f"        }};\n"
        f"        if (File.exists(flagPath).not) {{\n"
        f'            "ERROR: Record trigger flag never set; aborting.".postln;\n'
        f"            0.exit;\n"
        f"        }};\n"
        f'        ("Trigger received; recording {duration}s to {out_path}").postln;\n'
        f'        s.record(path: "{out_path}".standardizePath, duration: {duration});\n'
        f"        ({duration} + 2).wait;\n"
        f'        "Recording complete.".postln;\n'
        f"        0.5.wait;\n"
        f"        0.exit;\n"
        f"    }};\n"
        f"}};\n"
        f")\n"
    )


def _check_audio_level(wav_path: Path) -> None:
    """Run ffmpeg volumedetect and warn on silent output."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(wav_path), "-af", "volumedetect", "-f", "null", "/dev/null"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    mean_db: float | None = None
    for line in result.stderr.split("\n"):
        if "mean_volume" in line:
            with contextlib.suppress(ValueError, IndexError):
                mean_db = float(line.split("mean_volume:")[1].split("dB")[0].strip())
    if mean_db is not None and mean_db < -70:
        logger.warning(
            "Mean volume %.1f dBFS — likely silent. "
            "Check SuperDirt port, Tidal pattern, or OSC routing.",
            mean_db,
        )
