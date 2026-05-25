"""Tests for detect.py — mocked environment probes."""

from pathlib import Path
from typing import Any

from strudel_gen.detect import (
    DetectionResult,
    _find_strudel_dir,
    _is_wsl,
    detect,
    platform_install_hints,
)


class TestDetect:
    """detect() returns sane defaults even when nothing is installed."""

    def test_detect_returns_result_object(self) -> None:
        result = detect()
        assert isinstance(result, DetectionResult)
        assert result.os_name in ("Darwin", "Linux", "Windows", "Java")

    def test_is_wsl_returns_false_on_non_linux(self) -> None:
        # On non-Linux, _is_wsl should always be False
        result = detect()
        if result.os_name != "Linux":
            assert not result.is_wsl

    def test_is_wsl_detects_microsoft_kernel(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(Path, "read_text", lambda *_args: "Linux version microsoft")
        assert _is_wsl() is True

    def test_is_wsl_returns_false_when_proc_unavailable(self, monkeypatch: Any) -> None:
        def raise_os_error(*_args: Any) -> str:
            raise OSError("no proc")

        monkeypatch.setattr(Path, "read_text", raise_os_error)
        assert _is_wsl() is False

    def test_find_strudel_dir_prefers_env_override(self, tmp_path: Path, monkeypatch: Any) -> None:
        strudel_dir = tmp_path / "custom-strudel"
        strudel_dir.mkdir()
        (strudel_dir / "package.json").write_text("{}")
        monkeypatch.setenv("STRUDEL_DIR", str(strudel_dir))

        assert _find_strudel_dir() == strudel_dir.resolve()

    def test_find_strudel_dir_falls_back_to_home_candidates(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        home = tmp_path / "home"
        candidate = home / "code" / "strudel"
        candidate.mkdir(parents=True)
        (candidate / "package.json").write_text("{}")
        monkeypatch.delenv("STRUDEL_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: home)

        assert _find_strudel_dir() == candidate.resolve()

    def test_detect_includes_mocked_tool_paths(self, monkeypatch: Any) -> None:
        values = {
            "sclang": "/usr/local/bin/sclang",
            "node": "/usr/local/bin/node",
            "pnpm": "/usr/local/bin/pnpm",
        }

        monkeypatch.setattr("strudel_gen.detect.shutil.which", lambda name: values.get(name))
        monkeypatch.setattr("strudel_gen.detect._find_strudel_dir", lambda: Path("/tmp/strudel"))
        monkeypatch.setattr("strudel_gen.detect.platform.system", lambda: "Linux")
        monkeypatch.setattr("strudel_gen.detect._is_wsl", lambda: True)

        result = detect()

        assert result.sclang == values["sclang"]
        assert result.node == values["node"]
        assert result.pnpm == values["pnpm"]
        assert result.strudel_dir == Path("/tmp/strudel")
        assert result.is_wsl is True


class TestPlatformInstallHints:
    """platform_install_hints returns actionable strings for missing deps."""

    def test_hints_for_missing_everything(self) -> None:
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

    def test_hints_empty_when_everything_present(self) -> None:
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

    def test_macos_hint_for_sclang(self) -> None:
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

    def test_windows_hint_for_sclang(self) -> None:
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

    def test_linux_hint_for_sclang(self) -> None:
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
