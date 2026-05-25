"""OSC bridge lifecycle — start/stop the Strudel → SuperDirt OSC bridge."""

import logging
import re
import subprocess
import time
from pathlib import Path

from strudel_gen.detect import detect

logger = logging.getLogger(__name__)

BRIDGE_READY_RE = re.compile(r"(listening on|bridge ready|osc bridge started)", re.IGNORECASE)


class BridgeError(RuntimeError):
    """Raised when the OSC bridge fails to start or unexpectedly stops."""


class BridgeManager:
    """Context manager that starts the Strudel OSC bridge and keeps it alive.

    Args:
        strudel_dir: Path to the Strudel clone directory. If None, auto-detect.
        timeout: Seconds to wait for the bridge ready message.
    """

    def __init__(
        self,
        strudel_dir: Path | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._strudel_dir = strudel_dir or self._resolve_strudel_dir()
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._log_file: Path | None = None

    @staticmethod
    def _resolve_strudel_dir() -> Path:
        det = detect()
        if det.strudel_dir is None:
            raise BridgeError(
                "Strudel clone not found. Set STRUDEL_DIR env var or clone to ~/devel/strudel"
            )
        return det.strudel_dir

    def start(self) -> None:
        """Start the OSC bridge and wait for the ready signal."""
        bridge_dir = self._strudel_dir
        logger.info("Starting OSC bridge in %s", bridge_dir)
        self._process = subprocess.Popen(
            ["pnpm", "run", "osc"],
            cwd=str(bridge_dir),
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
            logger.debug("[bridge] %s", line)
            if BRIDGE_READY_RE.search(line):
                logger.info("OSC bridge is ready")
                return

        # Timeout or premature exit
        self.stop()
        raise BridgeError(f"Bridge did not emit ready signal within {self._timeout}s")

    def stop(self) -> None:
        """Terminate the bridge process."""
        if self._process is not None:
            logger.info("Stopping OSC bridge (pid=%d)", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bridge did not exit gracefully, killing")
                self._process.kill()
                self._process.wait(timeout=3)
            self._process = None

    def __enter__(self) -> "BridgeManager":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.stop()
