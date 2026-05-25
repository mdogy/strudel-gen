"""Detect prerequisites: sclang, node, pnpm, Strudel clone, OS platform + WSL."""

import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectionResult:
    sclang: str | None
    node: str | None
    pnpm: str | None
    strudel_dir: Path | None
    os_name: str
    is_wsl: bool


def _is_wsl() -> bool:
    """Detect WSL by checking /proc/version for 'microsoft'."""
    try:
        proc_version = Path("/proc/version").read_text().lower()
        return "microsoft" in proc_version or "wsl" in proc_version
    except (FileNotFoundError, OSError):
        return False


def _find_strudel_dir() -> Path | None:
    """Locate the Strudel clone directory.

    Checks STRUDEL_DIR env var first, then common defaults.
    """
    env_dir = Path(__file__).resolve().parent.parent.parent.parent / "strudel"
    candidates: list[Path] = [
        Path(p)
        for p in [
            env_dir,
            Path.home() / "devel" / "strudel",
            Path.home() / "code" / "strudel",
            Path.home() / "src" / "strudel",
        ]
    ]
    for candidate in candidates:
        if (candidate / "package.json").exists():
            return candidate.resolve()
    return None


def detect() -> DetectionResult:
    """Probe the environment for all prerequisites."""
    sclang = shutil.which("sclang")
    node = shutil.which("node")
    pnpm = shutil.which("pnpm")
    strudel_dir = _find_strudel_dir()
    os_name = platform.system()
    is_wsl = _is_wsl() if os_name == "Linux" else False

    return DetectionResult(
        sclang=sclang,
        node=node,
        pnpm=pnpm,
        strudel_dir=strudel_dir,
        os_name=os_name,
        is_wsl=is_wsl,
    )


def platform_install_hints(detection: DetectionResult) -> dict[str, str]:
    """Return actionable install hints for missing prerequisites."""
    hints: dict[str, str] = {}
    os_name = detection.os_name

    if not detection.sclang:
        if os_name == "Darwin":
            hints["sclang"] = (
                "Install SuperCollider from https://supercollider.github.io/download "
                "or via `brew install supercollider`"
            )
        elif os_name == "Windows":
            hints["sclang"] = (
                "Install SuperCollider from https://supercollider.github.io/download "
                "(use the Windows installer)"
            )
        else:
            hints["sclang"] = (
                "Install SuperCollider via apt: "
                "`sudo apt install supercollider supercollider-sc3-plugins`"
            )

    if not detection.node:
        hints["node"] = "Install Node.js via nvm: `nvm install lts/iron` or from https://nodejs.org"

    if not detection.pnpm:
        hints["pnpm"] = "Install pnpm via `npm install -g pnpm`"

    if not detection.strudel_dir:
        hints["strudel_dir"] = (
            "Clone Strudel: `git clone https://github.com/tidalcycles/strudel.git ~/devel/strudel` "
            "and pin to commit 8a8ae9ac9659509ad7e1ed356093905a54cf8b2b"
        )

    return hints
