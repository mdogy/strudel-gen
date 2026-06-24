"""Tests for sc.py — SuperCollider lifecycle."""

import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from strudel_gen.sc import SCError, SCManager


class TestSCManagerInit:
    def test_init_default_startup_file(self) -> None:
        manager = SCManager()
        assert manager._startup_file.name == "startup.scd"
        assert manager._startup_file.exists()

    def test_init_raises_on_missing_startup(self) -> None:
        with pytest.raises(SCError, match="Startup file not found"):
            SCManager(startup_file=Path("/nonexistent/startup.scd"))


class TestSCManagerStart:
    def _make_mock_proc(self, output: str) -> MagicMock:
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 54321
        mock_proc.stdout = io.StringIO(output)
        return mock_proc

    def test_start_superdirt_ready_detected(self) -> None:
        mock_proc = self._make_mock_proc("compiling...\nSuperDirt: listening on port 57120\n")

        with patch("subprocess.Popen", return_value=mock_proc):
            manager = SCManager(timeout=5)
            manager.start()
            assert manager._process is not None

    def test_start_timeout_raises(self) -> None:
        mock_proc = self._make_mock_proc("compiling...\nstill booting...\nSC not ready yet\n")

        with patch("subprocess.Popen", return_value=mock_proc):
            manager = SCManager(timeout=0.1)
            with pytest.raises(SCError, match="did not become ready"):
                manager.start()


class TestSCManagerContextManager:
    def test_context_manager_starts_and_stops(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 54321
        mock_proc.stdout = io.StringIO("SuperDirt: listening on port 57120\n")

        with patch("subprocess.Popen", return_value=mock_proc):
            with SCManager(timeout=5) as mgr:
                assert mgr._process is not None
            mock_proc.terminate.assert_called_once()

    def test_stop_kills_process_after_timeout(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 54321
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="sclang", timeout=10), None]

        manager = SCManager(timeout=5)
        manager._process = mock_proc
        manager.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()
