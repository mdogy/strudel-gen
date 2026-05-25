"""SuperCollider lifecycle — spawn sclang, evaluate startup, detect SuperDirt ready."""

import logging
import re
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SUPERDIRT_READY_RE = re.compile(r"SuperDirt:\s+listening\s+on\s+port\s+57120", re.IGNORECASE)


class SCError(RuntimeError):
    """Raised when SuperCollider fails to start or SuperDirt does not become ready."""


class SCManager:
    """Context manager that starts SuperCollider and waits for SuperDirt.

    Args:
        startup_file: Path to the SC startup .scd file.
        sclang: Absolute path to sclang binary. Auto-detected if None.
        timeout: Seconds to wait for the SuperDirt ready message.
    """

    def __init__(
        self,
        startup_file: Path | None = None,
        sclang: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        if startup_file is None:
            startup_file = Path(__file__).resolve().parent.parent / "supercollider" / "startup.scd"
        if not startup_file.exists():
            raise SCError(f"Startup file not found: {startup_file}")
        if sclang is None:
            from strudel_gen.detect import _find_sclang

            sclang = _find_sclang()
        if sclang is None:
            raise SCError(
                "sclang not found. Install SuperCollider and ensure sclang is on PATH, "
                "or symlink: ln -s /Applications/SuperCollider.app/Contents/MacOS/sclang "
                "~/.local/bin/sclang"
            )
        self._sclang = sclang
        self._startup_file = startup_file
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        """Start sclang and wait for SuperDirt to announce it is listening."""
        logger.info("Starting sclang (%s) with startup file %s", self._sclang, self._startup_file)
        self._process = subprocess.Popen(
            [self._sclang, str(self._startup_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            assert self._process.stdout is not None
            line = self._process.stdout.readline()
            if not line:
                break
            line = line.strip()
            logger.debug("[sclang] %s", line)
            if SUPERDIRT_READY_RE.search(line):
                logger.info("SuperDirt is listening on port 57120")
                return

        self.stop()
        raise SCError(f"SuperDirt did not become ready within {self._timeout}s")

    def stop(self) -> None:
        """Terminate the sclang process."""
        if self._process is not None:
            logger.info("Stopping sclang (pid=%d)", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("sclang did not exit gracefully, killing")
                self._process.kill()
                self._process.wait(timeout=5)
            self._process = None

    def __enter__(self) -> "SCManager":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.stop()
