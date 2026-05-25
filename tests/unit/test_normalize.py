"""Tests for normalize.py — ffmpeg loudnorm wrapper."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from strudel_gen.normalize import (
    NormalizationError,
    _ffmpeg_available,
    _parse_loudnorm_json,
    normalize_to_dbfs,
)


class TestFFmpegAvailable:
    def test_returns_true_when_ffmpeg_found(self):
        assert _ffmpeg_available()


class TestParseLoudnormJson:
    def test_parses_valid_json(self):
        stderr = (
            "some ffmpeg output\n"
            '{\n'
            '    "input_i" : "-23.0",\n'
            '    "input_tp" : "-1.5",\n'
            '    "input_lra" : "7.0",\n'
            '    "input_thresh" : "-35.0"\n'
            '}\n'
        )
        result = _parse_loudnorm_json(stderr)
        assert result is not None
        assert result["input_i"] == "-23.0"
        assert result["input_tp"] == "-1.5"

    def test_returns_none_on_no_json(self):
        assert _parse_loudnorm_json("just some text") is None

    def test_returns_none_on_malformed(self):
        assert _parse_loudnorm_json("{broken") is None


class TestNormalizeToDbfs:
    def test_raises_when_ffmpeg_missing(self):
        with patch("strudel_gen.normalize._ffmpeg_available", return_value=False):
            with pytest.raises(NormalizationError, match="ffmpeg not found"):
                normalize_to_dbfs(Path("/tmp/test.wav"))

    def test_returns_input_when_nothing_to_do(self, tmp_path):
        wav = tmp_path / "silent.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run") as mock_run,
            patch("strudel_gen.normalize._parse_loudnorm_json", return_value=None),
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = normalize_to_dbfs(wav, sidecar=False)
            assert result == wav
