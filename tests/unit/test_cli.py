"""Tests for cli.py — Typer command coverage."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from strudel_gen.cli import app
from strudel_gen.detect import DetectionResult
from strudel_gen.normalize import NormalizationError

runner = CliRunner()


def _detection(
    *,
    sclang: str | None = "/usr/bin/sclang",
    node: str | None = "/usr/bin/node",
    pnpm: str | None = "/usr/bin/pnpm",
    strudel_dir: Path | None = Path("/tmp/strudel"),
) -> DetectionResult:
    return DetectionResult(
        sclang=sclang,
        node=node,
        pnpm=pnpm,
        strudel_dir=strudel_dir,
        os_name="Linux",
        is_wsl=False,
    )


class TestDoctorCommand:
    def test_doctor_verbose_success(self) -> None:
        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.platform_install_hints", return_value={"node": "install node"}),
        ):
            result = runner.invoke(app, ["doctor", "--verbose"])

        assert result.exit_code == 0
        assert "All prerequisites found" in result.output

    def test_doctor_missing_dependency_exits_one(self) -> None:
        with (
            patch("strudel_gen.cli.detect", return_value=_detection(sclang=None)),
            patch(
                "strudel_gen.cli.platform_install_hints",
                return_value={"sclang": "install supercollider"},
            ),
        ):
            result = runner.invoke(app, ["doctor", "--verbose"])

        assert result.exit_code == 1
        assert "Some prerequisites are missing" in result.output
        assert "install supercollider" in result.output


class TestRenderPatternCommand:
    def test_render_pattern_writes_output(self, tmp_path: Path) -> None:
        spec_path = tmp_path / "spec.json"
        out_path = tmp_path / "pattern.js"
        spec_path.write_text(
            '{"cpm":20,"layers":['
            '{"type":"drone","notes":"<c2 g2>","sound":"sawtooth","orbit":0,'
            '"slow_factor":8,"room":0.9,"gain":0.4},'
            '{"type":"pad","notes":"<c4 eb4>","sound":"sine","orbit":1,'
            '"slow_factor":4,"room":0.8,"gain":0.3}'
            "]}"
        )

        result = runner.invoke(
            app,
            ["render-pattern", "--spec", str(spec_path), "--out", str(out_path)],
        )

        assert result.exit_code == 0
        assert out_path.exists()
        assert "setcpm(20)" in out_path.read_text()


class TestSessionCommand:
    def test_session_requires_sclang(self) -> None:
        with patch("strudel_gen.cli.detect", return_value=_detection(sclang=None)):
            result = runner.invoke(app, ["session", "--dry-run"])

        assert result.exit_code == 1
        assert "sclang not found" in result.output

    def test_session_requires_strudel_clone(self) -> None:
        with patch("strudel_gen.cli.detect", return_value=_detection(strudel_dir=None)):
            result = runner.invoke(app, ["session", "--dry-run"])

        assert result.exit_code == 1
        assert "Strudel clone not found" in result.output

    def test_session_dry_run_starts_and_stops_services(self) -> None:
        mock_sc = MagicMock()
        mock_bridge = MagicMock()

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.SCManager", return_value=mock_sc),
            patch("strudel_gen.cli.BridgeManager", return_value=mock_bridge),
            patch("time.sleep"),
        ):
            result = runner.invoke(app, ["session", "--dry-run", "--duration", "1"])

        assert result.exit_code == 0
        mock_sc.start.assert_called_once()
        mock_bridge.start.assert_called_once()
        mock_bridge.stop.assert_called_once()
        mock_sc.stop.assert_called_once()
        assert "Session complete" in result.output


class TestRenderCommand:
    def test_render_requires_sclang(self) -> None:
        with patch("strudel_gen.cli.detect", return_value=_detection(sclang=None)):
            result = runner.invoke(app, ["render", "--duration", "1"])

        assert result.exit_code == 1
        assert "sclang not found" in result.output

    # --- Path A: self-contained .scd script ---

    def test_render_scd_runs_sclang_directly(self, tmp_path: Path) -> None:
        """scd render path: sclang called with positional args, no bridge/SCManager."""
        scd_path = tmp_path / "pattern.scd"
        scd_path.write_text("// sc script")
        out_path = tmp_path / "out.wav"
        out_path.write_bytes(b"RIFF" + b"\x00" * 32)

        completed = subprocess.CompletedProcess(
            args=["sclang", str(scd_path), str(out_path), "5"],
            returncode=0,
            stdout="Recording complete.",
            stderr="",
        )

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.normalize_to_dbfs", return_value=out_path),
            patch("strudel_gen.cli.subprocess.run", return_value=completed) as mock_run,
        ):
            result = runner.invoke(
                app,
                ["render", "--pattern", str(scd_path), "--duration", "5", "--out", str(out_path)],
            )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        # sclang may be a full path (e.g. from app bundle detection) or bare "sclang"
        assert str(call_args[0]).endswith("sclang") or str(call_args[0]).endswith("sclang.exe")
        assert call_args[1] == str(scd_path)
        assert call_args[2] == str(out_path)
        assert "Render complete" in result.output

    def test_render_scd_missing_file_exits_one(self, tmp_path: Path) -> None:
        scd_path = tmp_path / "missing.scd"
        out_path = tmp_path / "out.wav"

        with patch("strudel_gen.cli.detect", return_value=_detection()):
            result = runner.invoke(
                app,
                ["render", "--pattern", str(scd_path), "--duration", "1", "--out", str(out_path)],
            )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_render_scd_nonzero_exit_propagates(self, tmp_path: Path) -> None:
        scd_path = tmp_path / "bad.scd"
        scd_path.write_text("// broken")
        out_path = tmp_path / "out.wav"

        completed = subprocess.CompletedProcess(
            args=["sclang", str(scd_path)], returncode=1, stdout="", stderr="error"
        )

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.subprocess.run", return_value=completed),
        ):
            result = runner.invoke(
                app,
                ["render", "--pattern", str(scd_path), "--duration", "1", "--out", str(out_path)],
            )

        assert result.exit_code == 1

    # --- Path B: Strudel .js pattern via bridge ---

    def test_render_js_records_and_normalizes(self, tmp_path: Path) -> None:
        out_path = tmp_path / "soundscape.wav"
        pattern_path = tmp_path / "pattern.js"
        pattern_path.write_text("setcpm(20)")
        out_path.write_bytes(b"RIFF" + b"\x00" * 32)
        mock_sc = MagicMock()
        mock_bridge = MagicMock()
        normalized_path = tmp_path / "normalized.wav"

        completed = subprocess.CompletedProcess(
            args=["sclang", "-"], returncode=0, stdout="ok", stderr=""
        )

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.SCManager", return_value=mock_sc),
            patch("strudel_gen.cli.BridgeManager", return_value=mock_bridge),
            patch("strudel_gen.cli.subprocess.run", return_value=completed) as mock_run,
            patch(
                "strudel_gen.cli.normalize_to_dbfs", return_value=normalized_path
            ) as mock_normalize,
        ):
            result = runner.invoke(
                app,
                [
                    "render",
                    "--duration",
                    "1",
                    "--out",
                    str(out_path),
                    "--pattern",
                    str(pattern_path),
                ],
            )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        mock_normalize.assert_called_once_with(out_path, target=-6.0)
        mock_bridge.stop.assert_called_once()
        mock_sc.stop.assert_called_once()
        assert "Render complete" in result.output

    def test_render_js_skips_normalize_when_disabled(self, tmp_path: Path) -> None:
        out_path = tmp_path / "soundscape.wav"
        out_path.write_bytes(b"RIFF" + b"\x00" * 32)
        mock_sc = MagicMock()
        mock_bridge = MagicMock()
        completed = subprocess.CompletedProcess(
            args=["sclang", "-"], returncode=0, stdout="", stderr=""
        )

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.SCManager", return_value=mock_sc),
            patch("strudel_gen.cli.BridgeManager", return_value=mock_bridge),
            patch("strudel_gen.cli.subprocess.run", return_value=completed),
            patch("strudel_gen.cli.normalize_to_dbfs") as mock_normalize,
        ):
            result = runner.invoke(
                app,
                ["render", "--duration", "1", "--out", str(out_path), "--no-normalize"],
            )

        assert result.exit_code == 0
        mock_normalize.assert_not_called()

    def test_render_reports_normalization_warning(self, tmp_path: Path) -> None:
        out_path = tmp_path / "soundscape.wav"
        out_path.write_bytes(b"RIFF" + b"\x00" * 32)
        mock_sc = MagicMock()
        mock_bridge = MagicMock()
        completed = subprocess.CompletedProcess(
            args=["sclang", "-"], returncode=0, stdout="", stderr=""
        )

        with (
            patch("strudel_gen.cli.detect", return_value=_detection()),
            patch("strudel_gen.cli.SCManager", return_value=mock_sc),
            patch("strudel_gen.cli.BridgeManager", return_value=mock_bridge),
            patch("strudel_gen.cli.subprocess.run", return_value=completed),
            patch(
                "strudel_gen.cli.normalize_to_dbfs",
                side_effect=NormalizationError("ffmpeg missing"),
            ),
        ):
            result = runner.invoke(app, ["render", "--duration", "1", "--out", str(out_path)])

        assert result.exit_code == 0
        assert "Normalization warning" in result.output
