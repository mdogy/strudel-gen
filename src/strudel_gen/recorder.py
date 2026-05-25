"""SC Routine generator — produce sclang code for timed recording."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RecorderScript:
    """Generates SuperCollider Routine code for timed WAV recording.

    The generated script is piped to sclang while the SuperCollider
    server is already running (booted via SCManager).

    Args:
        output_path: Absolute path for the WAV file.
        duration: Recording duration in seconds.
        num_channels: Number of channels (2 for stereo, 6 for stems).
        header_format: "WAV", "AIFF", etc.
        sample_format: "int24", "int16", "float".
    """

    def __init__(
        self,
        output_path: Path,
        duration: float,
        num_channels: int = 2,
        header_format: str = "WAV",
        sample_format: str = "int24",
    ) -> None:
        self.output_path = output_path
        self.duration = duration
        self.num_channels = num_channels
        self.header_format = header_format
        self.sample_format = sample_format

    def generate(self) -> str:
        """Generate the SC Routine script as a string."""
        path_str = str(self.output_path.expanduser().resolve()).replace("\\", "/")
        return f"""(
s.recHeaderFormat = "{self.header_format}";
s.recSampleFormat = "{self.sample_format}";
s.recChannels = {self.num_channels};
Routine({{
    0.5.wait;
    s.record(
        path: "{path_str}".standardizePath,
        duration: {self.duration}
    );
}}).play;
)
"""

    def to_temp_file(self, directory: Path | None = None) -> Path:
        """Write the generated script to a temporary .scd file."""
        import tempfile

        if directory:
            directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".scd",
            delete=False,
            dir=str(directory) if directory else None,
        ) as tmp:
            tmp.write(self.generate())
            path = Path(tmp.name)
        logger.debug("Wrote recording script to %s", path)
        return path
