"""Integration tests — require real binaries (sclang, pnpm, node, Strudel clone).

All tests in this file are skipped if the required binaries are not present.
"""

import pytest

from strudel_gen.detect import detect


def _require_binary(name: str) -> bool:
    det = detect()
    return getattr(det, name, None) is not None


sclang_available = pytest.mark.skipif(
    not _require_binary("sclang"),
    reason="sclang not found on PATH",
)
strudel_available = pytest.mark.skipif(
    not _require_binary("strudel_dir"),
    reason="Strudel clone not found",
)
bridge_available = pytest.mark.skipif(
    not (_require_binary("pnpm") and _require_binary("strudel_dir")),
    reason="pnpm or Strudel clone not found",
)


@sclang_available
class TestSCIntegration:
    """Integration tests for sclang invocation (real binary, real startup)."""

    def test_sclang_version(self) -> None:
        """sclang --version should produce output."""
        import subprocess

        result = subprocess.run(
            ["sclang", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "SuperCollider" in result.stdout or "SuperCollider" in result.stderr


@bridge_available
class TestBridgeIntegration:
    """Integration tests for the OSC bridge (real pnpm + Strudel clone)."""

    def test_pnpm_run_osc_available(self) -> None:
        """The 'pnpm run osc' script should be defined in package.json."""
        import json

        from strudel_gen.detect import detect as _detect

        det = _detect()
        assert det.strudel_dir is not None
        pkg = json.loads((det.strudel_dir / "package.json").read_text())
        scripts = pkg.get("scripts", {})
        assert "osc" in scripts, f"'osc' script not found in {det.strudel_dir}/package.json"
