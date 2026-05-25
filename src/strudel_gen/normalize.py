"""WAV post-processing — normalize to −6 dBFS via ffmpeg loudnorm."""

import json
import logging
import subprocess
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)


class NormalizationError(RuntimeError):
    """Raised when ffmpeg normalization fails."""


def normalize_to_dbfs(
    input_path: Path,
    target: float = -6.0,
    output_path: Path | None = None,
    sidecar: bool = True,
) -> Path:
    """Normalize a WAV file to a target loudness level using ffmpeg loudnorm.

    Args:
        input_path: Path to the source WAV file.
        target: Target integrated loudness in dBFS (default −6.0).
        output_path: Path for the output WAV. If None, overwrites input.
        sidecar: If True, write a sidecar .json with loudness metrics.

    Returns:
        Path to the normalized WAV file.

    Raises:
        NormalizationError: If ffmpeg is not found or the command fails.
    """
    if not _ffmpeg_available():
        raise NormalizationError("ffmpeg not found on PATH. Install ffmpeg or skip normalization.")

    if output_path is None:
        output_path = input_path

    out = input_path.parent / f"{input_path.stem}.normalized{input_path.suffix}"

    # First pass: measure loudness
    measure_cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-af",
        f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    logger.info("Measuring loudness: %s", input_path)
    try:
        measure_result = subprocess.run(
            measure_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise NormalizationError(f"Loudness measurement failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise NormalizationError("ffmpeg not found") from exc

    # Parse the JSON loudness data from stderr
    loudness_data = _parse_loudnorm_json(measure_result.stderr)

    if loudness_data is None:
        logger.warning("Could not parse loudnorm output; skipping normalization")
        return input_path

    logger.debug("Loudness data: %s", loudness_data)

    # Second pass: apply normalization
    offset = float(loudness_data.get("input_i", "0")) - target
    normalize_cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-af",
        (
            f"loudnorm=I={target}:TP=-1.5:LRA=11:"
            f"measured_I={loudness_data['input_i']}:"
            f"measured_TP={loudness_data['input_tp']}:"
            f"measured_LRA={loudness_data['input_lra']}:"
            f"measured_thresh={loudness_data['input_thresh']}:"
            f"offset={offset}:"
            f"linear=true:print_format=summary"
        ),
        "-y",
        str(out),
    ]
    logger.info("Normalizing to %.1f dBFS: %s -> %s", target, input_path, out)
    try:
        subprocess.run(
            normalize_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise NormalizationError(f"Normalization failed: {exc.stderr[:500]}") from exc

    # Write sidecar JSON
    if sidecar:
        sidecar_path = out.with_suffix(".loudness.json")
        sidecar_data = {
            "input": str(input_path),
            "output": str(out),
            "target_dbfs": target,
            "measured": loudness_data,
        }
        sidecar_path.write_text(json.dumps(sidecar_data, indent=2))
        logger.info("Wrote loudness sidecar to %s", sidecar_path)

    # Replace original if no separate output path
    if output_path == input_path:
        input_path.unlink()
        out.rename(input_path)
        return input_path

    return out


def _ffmpeg_available() -> bool:
    """Check if ffmpeg is on PATH."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _parse_loudnorm_json(stderr: str) -> dict[str, str] | None:
    """Extract JSON loudness data from loudnorm stderr output."""
    try:
        lines = stderr.strip().split("\n")
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
        if json_start >= 0:
            json_str = "\n".join(lines[json_start:])
            data = cast(dict[str, str], json.loads(json_str))
            return data
    except (json.JSONDecodeError, IndexError, TypeError):
        pass
    return None
