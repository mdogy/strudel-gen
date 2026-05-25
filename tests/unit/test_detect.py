"""Tests for detect.py — mocked environment probes."""

from pathlib import Path

from strudel_gen.detect import DetectionResult, _is_wsl, detect, platform_install_hints


class TestDetect:
    """detect() returns sane defaults even when nothing is installed."""

    def test_detect_returns_result_object(self):
        result = detect()
        assert isinstance(result, DetectionResult)
        assert result.os_name in ("Darwin", "Linux", "Windows", "Java")

    def test_is_wsl_returns_false_on_non_linux(self):
        # On non-Linux, _is_wsl should always be False
        result = detect()
        if result.os_name != "Linux":
            assert not result.is_wsl


class TestPlatformInstallHints:
    """platform_install_hints returns actionable strings for missing deps."""

    def test_hints_for_missing_everything(self):
        empty = DetectionResult(
            sclang=None,
            node=None,
            pnpm=None,
            strudel_dir=None,
            os_name="Linux",
            is_wsl=False,
        )
        hints = platform_install_hints(empty)
        assert "sclang" in hints
        assert "node" in hints
        assert "pnpm" in hints
        assert "strudel_dir" in hints

    def test_hints_empty_when_everything_present(self):
        full = DetectionResult(
            sclang="/usr/bin/sclang",
            node="/usr/bin/node",
            pnpm="/usr/bin/pnpm",
            strudel_dir=Path("/home/user/devel/strudel"),
            os_name="Linux",
            is_wsl=False,
        )
        hints = platform_install_hints(full)
        assert hints == {}

    def test_macos_hint_for_sclang(self):
        mac = DetectionResult(
            sclang=None,
            node="/usr/bin/node",
            pnpm="/usr/bin/pnpm",
            strudel_dir=Path("/some/strudel"),
            os_name="Darwin",
            is_wsl=False,
        )
        hints = platform_install_hints(mac)
        assert "brew install" in hints["sclang"]

    def test_windows_hint_for_sclang(self):
        win = DetectionResult(
            sclang=None,
            node="/usr/bin/node",
            pnpm="/usr/bin/pnpm",
            strudel_dir=Path("/some/strudel"),
            os_name="Windows",
            is_wsl=False,
        )
        hints = platform_install_hints(win)
        assert "Windows installer" in hints["sclang"]

    def test_linux_hint_for_sclang(self):
        linux = DetectionResult(
            sclang=None,
            node="/usr/bin/node",
            pnpm="/usr/bin/pnpm",
            strudel_dir=Path("/some/strudel"),
            os_name="Linux",
            is_wsl=False,
        )
        hints = platform_install_hints(linux)
        assert "apt install" in hints["sclang"]
