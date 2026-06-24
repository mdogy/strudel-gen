"""Tests for normalize.py — ffmpeg loudnorm wrapper."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from strudel_gen.normalize import (
    NormalizationError,
    _ffmpeg_available,
    _parse_loudnorm_json,
    normalize_to_dbfs,
    to_mp3,
)


class TestFFmpegAvailable:
    def test_returns_true_when_ffmpeg_found(self) -> None:
        with patch("strudel_gen.normalize.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            assert _ffmpeg_available() is True

    def test_returns_false_when_ffmpeg_times_out(self) -> None:
        with patch(
            "strudel_gen.normalize.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10),
        ):
            assert _ffmpeg_available() is False


class TestParseLoudnormJson:
    def test_parses_valid_json(self) -> None:
        stderr = (
            "some ffmpeg output\n"
            "{\n"
            '    "input_i" : "-23.0",\n'
            '    "input_tp" : "-1.5",\n'
            '    "input_lra" : "7.0",\n'
            '    "input_thresh" : "-35.0"\n'
            "}\n"
        )
        result = _parse_loudnorm_json(stderr)
        assert result is not None
        assert result["input_i"] == "-23.0"
        assert result["input_tp"] == "-1.5"

    def test_returns_none_on_no_json(self) -> None:
        assert _parse_loudnorm_json("just some text") is None

    def test_returns_none_on_malformed(self) -> None:
        assert _parse_loudnorm_json("{broken") is None

    def test_parses_key_value_summary_format(self) -> None:
        stderr = (
            "input_i: -26.58\n"
            "input_tp: -14.62\n"
            "input_lra: 12.3\n"
            "input_thresh: -37.82\n"
        )
        result = _parse_loudnorm_json(stderr)
        assert result is not None
        assert result["input_i"] == "-26.58"
        assert result["input_tp"] == "-14.62"
        assert result["input_lra"] == "12.3"

    def test_returns_none_on_empty_or_noise(self) -> None:
        assert _parse_loudnorm_json("") is None
        assert _parse_loudnorm_json("[Parsed_loudnorm_0 @ 0x123]") is None


class TestToMp3:
    def test_raises_when_ffmpeg_missing(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=False),
            pytest.raises(NormalizationError, match="ffmpeg not found"),
        ):
            to_mp3(wav)

    def test_produces_mp3_path_on_success(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        mp3 = tmp_path / "take.mp3"
        mp3.write_bytes(b"\xff\xfb" + b"\x00" * 100)

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0, stdout="", stderr=""
            )
            result = to_mp3(wav, bitrate=128)

        assert result == mp3
        cmd = mock_run.call_args[0][0]
        assert "-codec:a" in cmd
        assert "libmp3lame" in cmd
        assert "-b:a" in cmd
        assert "128k" in cmd
        assert cmd[-1] == str(mp3)

    def test_raises_on_ffmpeg_failure(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch(
                "strudel_gen.normalize.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, ["ffmpeg"], stderr="codec error"),
            ),
            pytest.raises(NormalizationError, match="MP3 encoding failed"),
        ):
            to_mp3(wav)

    def test_raises_on_missing_binary(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(NormalizationError, match="ffmpeg not found"),
        ):
            to_mp3(wav)


class TestNormalizeToDbfs:
    def test_raises_when_ffmpeg_missing(self) -> None:
        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=False),
            pytest.raises(NormalizationError, match="ffmpeg not found"),
        ):
            normalize_to_dbfs(Path("/tmp/test.wav"))

    def test_returns_input_when_nothing_to_do(self, tmp_path: Path) -> None:
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

    def test_normalizes_in_place_and_writes_sidecar(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        normalized = tmp_path / "take.normalized.wav"
        normalized.write_bytes(b"RIFF" + b"\x01" * 100)
        stderr = (
            "metadata\n"
            "{\n"
            '  "input_i": "-23.0",\n'
            '  "input_tp": "-1.5",\n'
            '  "input_lra": "7.0",\n'
            '  "input_thresh": "-35.0"\n'
            "}\n"
        )

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["ffmpeg"], returncode=0, stdout="", stderr=stderr
                ),
                subprocess.CompletedProcess(
                    args=["ffmpeg"], returncode=0, stdout="", stderr="done"
                ),
            ]
            result = normalize_to_dbfs(wav)

        assert result == wav
        sidecar = tmp_path / "take.normalized.loudness.json"
        assert sidecar.exists()
        payload = json.loads(sidecar.read_text())
        assert payload["target_dbfs"] == -6.0
        assert payload["measured"]["input_i"] == "-23.0"
        assert wav.exists()
        assert not normalized.exists()
        assert mock_run.call_args_list[0].args[0][0:2] == ["ffmpeg", "-i"]
        assert "print_format=json" in mock_run.call_args_list[0].args[0][4]
        assert "measured_I=-23.0" in mock_run.call_args_list[1].args[0][4]

    def test_normalizes_to_separate_output_path(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        output = tmp_path / "final.wav"
        output.write_bytes(b"RIFF" + b"\x01" * 100)
        stderr = (
            "{\n"
            '  "input_i": "-20.0",\n'
            '  "input_tp": "-1.0",\n'
            '  "input_lra": "6.0",\n'
            '  "input_thresh": "-30.0"\n'
            "}\n"
        )

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["ffmpeg"], returncode=0, stdout="", stderr=stderr
                ),
                subprocess.CompletedProcess(
                    args=["ffmpeg"], returncode=0, stdout="", stderr="done"
                ),
            ]
            result = normalize_to_dbfs(wav, output_path=output, sidecar=False)

        assert result == output
        assert output.exists()
        assert wav.exists()
        assert mock_run.call_args_list[1].args[0][-1] == str(output)

    def test_raises_when_measurement_binary_missing(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(NormalizationError, match="ffmpeg not found"),
        ):
            normalize_to_dbfs(wav)

    def test_raises_when_normalization_fails(self, tmp_path: Path) -> None:
        wav = tmp_path / "take.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        stderr = (
            "{\n"
            '  "input_i": "-20.0",\n'
            '  "input_tp": "-1.0",\n'
            '  "input_lra": "6.0",\n'
            '  "input_thresh": "-30.0"\n'
            "}\n"
        )

        with (
            patch("strudel_gen.normalize._ffmpeg_available", return_value=True),
            patch("strudel_gen.normalize.subprocess.run") as mock_run,
        ):
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["ffmpeg"], returncode=0, stdout="", stderr=stderr
                ),
                subprocess.CalledProcessError(1, ["ffmpeg"], stderr="bad filter"),
            ]
            with pytest.raises(NormalizationError, match="Normalization failed"):
                normalize_to_dbfs(wav)
