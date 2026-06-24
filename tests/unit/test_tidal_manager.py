"""Tests for tidal_manager.py — Tidal Cycles ghci lifecycle."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import psutil

from strudel_gen.tidal_manager import TidalError, TidalManager


class TestTidalManagerInit:
    def test_init_defaults(self) -> None:
        manager = TidalManager(timeout=5)
        assert manager._timeout == 5
        assert manager._boot_file.name == "BootTidal.hs"
        assert manager._boot_file.exists()

    def test_init_raises_on_missing_boot(self) -> None:
        with pytest.raises(TidalError, match="Boot file not found"):
            TidalManager(boot_file=Path("/nonexistent/BootTidal.hs"))


class TestTidalManagerStop:
    def test_stop_graceful_quit(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process") as mock_psutil_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = []
            mock_psutil_process.return_value = mock_parent

            manager.stop()

            mock_stdin.write.assert_called_once_with(":quit\n")
            mock_proc.wait.assert_called()

    def test_stop_kills_child_process_tree(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None

        mock_child_1 = MagicMock(spec=psutil.Process)
        mock_child_1.pid = 12346
        mock_child_2 = MagicMock(spec=psutil.Process)
        mock_child_2.pid = 12347

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process") as mock_psutil_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = [mock_child_1, mock_child_2]
            mock_psutil_process.return_value = mock_parent

            with patch("psutil.wait_procs", return_value=([], [])):
                manager.stop()

                mock_child_1.terminate.assert_called_once()
                mock_child_2.terminate.assert_called_once()

    def test_stop_no_orphan_when_process_already_gone(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = 0  # already exited

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process") as mock_psutil_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = []
            mock_psutil_process.return_value = mock_parent

            manager.stop()

            mock_proc.terminate.assert_not_called()

    def test_stop_force_kills_alive_children(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None

        mock_child = MagicMock(spec=psutil.Process)
        mock_child.pid = 12346

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process") as mock_psutil_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = [mock_child]
            mock_psutil_process.return_value = mock_parent

            with patch("psutil.wait_procs", return_value=([], [mock_child])):
                manager.stop()

                mock_child.terminate.assert_called_once()
                mock_child.kill.assert_called_once()

    def test_stop_handles_no_such_process(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)):
            manager.stop()

            mock_stdin.write.assert_called_once_with(":quit\n")

    def test_stop_twice_is_safe(self) -> None:
        mock_stdin = MagicMock()
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdin = mock_stdin
        mock_proc.poll.return_value = None

        manager = TidalManager(timeout=5)
        manager._process = mock_proc

        with patch("psutil.Process") as mock_psutil_process:
            mock_parent = MagicMock()
            mock_parent.children.return_value = []
            mock_psutil_process.return_value = mock_parent

            manager.stop()
            manager.stop()

            assert mock_stdin.write.call_count == 1
