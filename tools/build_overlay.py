"""Build Overlay.exe (Nuitka standalone, onedir) from overlay/main.py.

Requires Nuitka + MSVC (Visual Studio Build Tools) and the bundled PySide6.
Output lands in dist/Overlay/ ready to copy as a folder.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "dist_overlay"
DIST_DIR = OUT_DIR / "main.dist"
FINAL = ROOT / "dist" / "Overlay"
ENTRY = ROOT / "overlay" / "main.py"


def build() -> Path:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        "--output-dir=" + str(OUT_DIR),
        "--output-filename=Overlay.exe",
        str(ENTRY),
    ]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise SystemExit(f"Nuitka failed with code {proc.returncode}")
    if not (DIST_DIR / "Overlay.exe").is_file():
        raise SystemExit("Build finished but Overlay.exe not found")
    if FINAL.exists():
        shutil.rmtree(FINAL)
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DIST_DIR, FINAL)
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    return FINAL


def main(argv: list[str] | None = None) -> int:
    final = build()
    size_mb = sum(p.stat().st_size for p in final.rglob("*") if p.is_file()) / 1e6
    print(f"Overlay built: {final}")
    print(f"Size: {size_mb:.1f} MB")
    print("Config.json is auto-created next to Overlay.exe on first run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
