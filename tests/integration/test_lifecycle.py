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
        """sclang --version should produce output containing 'sclang' or 'SuperCollider'."""
        import subprocess

        from strudel_gen.detect import _find_sclang

        sclang_bin = _find_sclang() or "sclang"
        result = subprocess.run(
            [sclang_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0
        assert "sclang" in combined.lower() or "supercollider" in combined.lower()


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
