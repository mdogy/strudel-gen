"""Tests for recorder.py — SC Routine script generation."""

from pathlib import Path

from strudel_gen.recorder import RecorderScript


class TestRecorderScript:
    def test_generate_basic(self):
        rec = RecorderScript(
            output_path=Path("/tmp/test.wav"),
            duration=30.0,
        )
        script = rec.generate()
        assert 's.recHeaderFormat = "WAV"' in script
        assert 's.recSampleFormat = "int24"' in script
        assert "s.recChannels = 2" in script
        assert "test.wav" in script
        assert "duration: 30.0" in script

    def test_generate_custom_channels(self):
        rec = RecorderScript(
            output_path=Path("/tmp/stems.wav"),
            duration=60.0,
            num_channels=6,
            header_format="AIFF",
            sample_format="int16",
        )
        script = rec.generate()
        assert 's.recHeaderFormat = "AIFF"' in script
        assert 's.recSampleFormat = "int16"' in script
        assert "s.recChannels = 6" in script
        assert "duration: 60.0" in script

    def test_generate_expands_user_path(self):
        rec = RecorderScript(
            output_path=Path("~/Desktop/output.wav"),
            duration=10.0,
        )
        script = rec.generate()
        # Should resolve ~ to home directory
        assert "Desktop" in script
        assert "output.wav" in script

    def test_to_temp_file_creates_scd(self, tmp_path):
        rec = RecorderScript(
            output_path=Path("/tmp/test.wav"),
            duration=5.0,
        )
        scd_path = rec.to_temp_file(directory=tmp_path)
        assert scd_path.exists()
        assert scd_path.suffix == ".scd"
        content = scd_path.read_text()
        assert 's.recHeaderFormat = "WAV"' in content
