"""Tests for bridge.py — OSC bridge lifecycle."""

import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from strudel_gen.bridge import BridgeError, BridgeManager


class TestBridgeManagerInit:
    def test_init_with_explicit_dir(self):
        manager = BridgeManager(strudel_dir=Path("/custom/strudel"))
        assert manager._strudel_dir == Path("/custom/strudel")

    def test_init_resolves_strudel_dir_when_none(self):
        with patch("strudel_gen.bridge.detect") as mock_detect:
            mock_detect.return_value.strudel_dir = Path("/detected/strudel")
            manager = BridgeManager()
            assert manager._strudel_dir == Path("/detected/strudel")

    def test_init_raises_when_no_strudel_dir(self):
        with patch("strudel_gen.bridge.detect") as mock_detect:
            mock_detect.return_value.strudel_dir = None
            with pytest.raises(BridgeError, match="Strudel clone not found"):
                BridgeManager()


class TestBridgeManagerStart:
    def _make_mock_proc(self, output: str) -> MagicMock:
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdout = io.StringIO(output)
        return mock_proc

    def test_start_ready_line_detected(self):
        mock_proc = self._make_mock_proc("loading...\nlistening on port 57120\n")

        with (
            patch("subprocess.Popen", return_value=mock_proc),
            patch("strudel_gen.bridge.detect") as mock_detect,
        ):
            mock_detect.return_value.strudel_dir = Path("/fake/strudel")
            manager = BridgeManager(timeout=5)
            manager.start()
            assert manager._process is not None

    def test_start_timeout_raises(self):
        mock_proc = self._make_mock_proc(
            "some output\nstill loading\nmore logs\nno ready signal\n"
        )

        with (
            patch("subprocess.Popen", return_value=mock_proc),
            patch("strudel_gen.bridge.detect") as mock_detect,
        ):
            mock_detect.return_value.strudel_dir = Path("/fake/strudel")
            manager = BridgeManager(timeout=0.1)
            with pytest.raises(BridgeError, match="did not emit ready signal"):
                manager.start()


class TestBridgeManagerContextManager:
    def test_context_manager_starts_and_stops(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        mock_proc.stdout = io.StringIO("listening on port 57120\n")

        with (
            patch("subprocess.Popen", return_value=mock_proc),
            patch("strudel_gen.bridge.detect") as mock_detect,
        ):
            mock_detect.return_value.strudel_dir = Path("/fake/strudel")
            with BridgeManager(timeout=5) as mgr:
                assert mgr._process is not None
            mock_proc.terminate.assert_called_once()
