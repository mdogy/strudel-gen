"""Tidal Cycles lifecycle — spawn ghci, evaluate .tidal patterns, hush."""

import logging
import os
import select
import subprocess
import threading
import time
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)

TIDAL_DIR = Path(__file__).resolve().parent.parent / "tidal"


class TidalError(RuntimeError):
    """Raised when ghci fails to start or Tidal does not become ready."""


class TidalManager:
    """Context manager that starts ghci with BootTidal.hs and evaluates patterns.

    Args:
        boot_file: Path to BootTidal.hs. Defaults to src/tidal/BootTidal.hs.
        tidal_dir: Path to the tidal project dir (contains stack.yaml).
        timeout: Seconds to wait for ghci to become ready.
    """

    def __init__(
        self,
        boot_file: Path | None = None,
        tidal_dir: Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        if tidal_dir is None:
            tidal_dir = TIDAL_DIR
        if boot_file is None:
            boot_file = tidal_dir / "BootTidal.hs"
        if not boot_file.exists():
            raise TidalError(f"Boot file not found: {boot_file}")
        self._boot_file = boot_file
        self._tidal_dir = tidal_dir
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._ready = threading.Event()

    def _reader(self) -> None:
        """Read ghci stdout byte-by-byte to handle prompt without newline."""
        assert self._process is not None
        assert self._process.stdout is not None
        fd = self._process.stdout.fileno()
        buf = ""
        while True:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if not ready:
                continue
            try:
                chunk = os.read(fd, 4096).decode("utf-8", errors="replace")
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            # Process complete lines; check each for prompts
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.rstrip("\r")
                logger.debug("[ghci] %s", line)
                if "tidal> " in line or "ghci> " in line:
                    logger.debug("[ghci] DETECTED in line: %s", line)
                    self._ready.set()
            # Remaining buf (no newline — could be a prompt)
            if buf:
                for prompt in ("tidal> ", "ghci> "):
                    if prompt in buf:
                        logger.debug("[ghci] DETECTED in buf: %s", repr(buf))
                        buf = ""
                        self._ready.set()

    def start(self) -> None:
        """Start ghci with --no-load, then :script BootTidal.hs."""
        logger.info(
            "Starting Tidal ghci (%s) in %s", self._boot_file, self._tidal_dir
        )
        self._process = subprocess.Popen(
            ["stack", "ghci", "--no-load"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered
            cwd=str(self._tidal_dir),
        )
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        if not self._ready.wait(timeout=self._timeout):
            self.stop()
            raise TidalError(
                f"GHCi did not become ready within {self._timeout}s"
            )
        logger.debug("GHCi ready, loading BootTidal.hs")
        self._ready.clear()
        assert self._process.stdin is not None
        self._process.stdin.write(f':script "{self._boot_file}"\n')
        self._process.stdin.flush()
        # GHCi block-buffers stdout when piped; send a no-op to flush
        # the prompt that :script sets (tidal>) into the pipe.
        time.sleep(0.5)
        self._process.stdin.write("1+1\n")
        self._process.stdin.flush()
        if not self._ready.wait(timeout=self._timeout):
            self.stop()
            raise TidalError(
                f"BootTidal.hs did not load within {self._timeout}s"
            )
        logger.info("Tidal ghci is ready")

    def eval(self, code: str) -> None:
        """Evaluate Tidal pattern code by writing to ghci stdin."""
        assert self._process is not None
        assert self._process.stdin is not None
        logger.debug("Eval: %s", code.strip())
        self._process.stdin.write(code + "\n")
        self._process.stdin.flush()

    def hush(self) -> None:
        """Silence all Tidal orbits."""
        self.eval("hush")

    def _kill_process_tree(self) -> None:
        """Kill all descendant processes (ghc grandchild etc.) of the ghci process.

        ``stack ghci`` spawns a ``ghc`` grandchild that survives as an orphan
        if the parent is SIGKILL'd without walking the child tree.
        """
        assert self._process is not None
        pid = self._process.pid
        if pid is None:
            return
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            if not children:
                return
            logger.info("Killing %d child process(es) of pid=%d", len(children), pid)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _gone, alive = psutil.wait_procs(children, timeout=5)
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass

    def stop(self) -> None:
        """Terminate the ghci process and all its descendants."""
        if self._process is not None:
            pid = self._process.pid
            logger.info("Stopping ghci (pid=%d)", pid)
            try:
                if self._process.stdin:
                    self._process.stdin.write(":quit\n")
                    self._process.stdin.flush()
                self._process.wait(timeout=10)
            except (BrokenPipeError, OSError):
                pass
            except subprocess.TimeoutExpired:
                logger.warning("ghci did not exit gracefully, killing")
            # Walk and kill the child tree — catches grandchildren (ghc)
            # that survive the parent termination.
            self._kill_process_tree()
            if self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("ghci did not respond to SIGTERM, sending SIGKILL")
                    self._process.kill()
                    self._process.wait(timeout=5)
            self._process = None

    def __enter__(self) -> "TidalManager":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tx: object,
    ) -> None:
        self.hush()
        self.stop()
