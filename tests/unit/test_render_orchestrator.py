"""Tests for render_orchestrator.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from strudel_gen.render_orchestrator import _check_audio_level, _make_record_scd, render_tidal


class TestMakeRecordScd:
    def test_generates_valid_scd_syntax(self) -> None:
        out_path = Path("/tmp/test.wav")
        flag = Path("/tmp/flag/start.flag")
        scd = _make_record_scd(out_path, duration=30.0, flag=flag, flag_poll_max=600.0)

        assert "s.waitForBoot" in scd
        assert "s.recHeaderFormat" in scd
        assert "s.recSampleFormat" in scd
        assert "test.wav" in scd
        assert "start.flag" in scd
        assert "maxWait = 600" in scd
        assert "duration: 30" in scd
        assert "0.exit" in scd


class TestCheckAudioLevel:
    def test_warns_on_silent_audio(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("WARNING")
        stderr = (
            "Parsed_volumedetect_0: mean_volume: -91.0 dB\n"
            "Parsed_volumedetect_0: max_volume: -70.0 dB\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stderr = stderr
            mock_run.return_value = mock_result
            _check_audio_level(Path("/tmp/test.wav"))

        assert "likely silent" in caplog.text

    def test_no_warning_on_normal_audio(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("WARNING")
        stderr = (
            "Parsed_volumedetect_0: mean_volume: -26.0 dB\n"
            "Parsed_volumedetect_0: max_volume: -14.6 dB\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stderr = stderr
            mock_run.return_value = mock_result
            _check_audio_level(Path("/tmp/test.wav"))

        assert "likely silent" not in caplog.text


class TestRenderTidal:
    def test_raises_when_superdirt_not_ready(self, tmp_path: Path) -> None:
        pattern = tmp_path / "test.tidal"
        pattern.write_text('d1 $ sound "bd"')
        out = tmp_path / "out.wav"
        flag_dir = tmp_path / "flag"
        flag_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.stdout.readline.side_effect = [
            "compiling...",
            "still loading samples...",
            "",
        ]

        with (
            patch("subprocess.Popen", return_value=mock_proc),
            patch("tempfile.mkdtemp", return_value=str(flag_dir)),
            patch("tempfile.NamedTemporaryFile") as mock_tmp,
        ):
            tmp_file = MagicMock()
            tmp_file.name = str(tmp_path / "render.scd")
            mock_tmp.return_value.__enter__.return_value = tmp_file

            with pytest.raises(RuntimeError, match="SuperDirt did not become ready"):
                render_tidal(pattern, out, duration=5.0)
