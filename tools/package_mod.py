"""Build LogOverlay.ts4script with Python 3.7 .pyc (required by Sims 4)."""

from __future__ import annotations

import py_compile
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "ts4script_staging"
OUT = DIST / "LogOverlay.ts4script"
PYTHON37 = ROOT / "tools" / "python37" / "python.exe"

PACKAGE_DIR = ROOT / "ts4_mod"
ENTRY_PY = ROOT / "ts4_mod_entry.py"
DEFAULT_CFG = ROOT / "config" / "config.json"


def _require_python37() -> Path:
    if not PYTHON37.is_file():
        raise SystemExit(
            f"Missing Python 3.7 embeddable at {PYTHON37}. "
            "Download python-3.7.9-embed-amd64.zip into tools/python37/"
        )
    return PYTHON37


def _compile_with_37(src: Path, dest_pyc: Path) -> None:
    """Compile a single .py to 3.7 .pyc at dest_pyc."""
    py37 = _require_python37()
    dest_pyc.parent.mkdir(parents=True, exist_ok=True)
    # py_compile via 3.7 interpreter so magic number matches the game.
    cmd = [
        str(py37),
        "-c",
        (
            "import py_compile, sys; "
            "py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)"
        ),
        str(src),
        str(dest_pyc),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Failed compiling {src}:\n{proc.stdout}\n{proc.stderr}"
        )


def stage() -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)

    # Compile package modules
    for src in PACKAGE_DIR.rglob("*.py"):
        rel = src.relative_to(ROOT)
        dest = BUILD / rel.with_suffix(".pyc")
        _compile_with_37(src, dest)

    # Compile entry module at archive root
    _compile_with_37(ENTRY_PY, BUILD / "ts4_mod_entry.pyc")

    # Seed config (optional readable file; not executed)
    if DEFAULT_CFG.is_file():
        shutil.copy2(DEFAULT_CFG, BUILD / "default_config.json")

    return BUILD


def build() -> Path:
    staged = stage()
    DIST.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in staged.rglob("*"):
            if not path.is_file():
                continue
            arcname = path.relative_to(staged).as_posix()
            zf.write(path, arcname=arcname)
    return OUT


def install_dev_scripts() -> Path:
    """
    Dev install: Mods/LogOverlay/Scripts with .py sources.
    Sims 4 loads .py from the special Scripts folder.
    """
    docs = Path.home() / "Documents" / "Electronic Arts" / "The Sims 4" / "Mods"
    if not docs.is_dir():
        onedrive = (
            Path.home()
            / "OneDrive"
            / "Documents"
            / "Electronic Arts"
            / "The Sims 4"
            / "Mods"
        )
        docs = onedrive
    target = docs / "LogOverlay" / "Scripts"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    shutil.copytree(PACKAGE_DIR, target / "ts4_mod")
    shutil.copy2(ENTRY_PY, target / "ts4_mod_entry.py")
    return target


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    mode = argv[0] if argv else "package"

    if mode in ("package", "all"):
        out = build()
        with zipfile.ZipFile(out, "r") as zf:
            names = sorted(zf.namelist())
        print(f"Built: {out}")
        print(f"Files: {len(names)}")
        for name in names:
            print(f"  {name}")
        # quick magic check on one pyc
        sample = next(n for n in names if n.endswith(".pyc"))
        data = zipfile.ZipFile(out).read(sample)
        print(f"Sample magic {sample}: {data[:4].hex()} (expect 420d0d0a for 3.7)")

    if mode in ("dev", "all"):
        target = install_dev_scripts()
        print(f"Dev Scripts installed: {target}")

    if mode not in ("package", "dev", "all"):
        print("Usage: python -m tools.package_mod [package|dev|all]")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
