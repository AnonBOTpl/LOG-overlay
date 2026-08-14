"""Overlay configuration loader with safe defaults."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _ROOT / "config" / "config.json"

_DEFAULTS: dict[str, Any] = {
    "ipc": {"host": "127.0.0.1", "port": 37241, "max_datagram_bytes": 8192},
    "overlay": {
        "opacity": 0.85,
        "x": 20,
        "y": 20,
        "width": 1300,
        "height": 400,
        "click_through": False,
        "always_on_top": True,
        "max_displayed_events": 500,
        "auto_scroll": True,
    },
    "logging": {
        "debug": True,
        "info": True,
        "warning": True,
        "error": True,
    },
}


def _executable_dir() -> Path:
    """Directory of the running executable (frozen exe or source interpreter)."""
    return Path(sys.executable).resolve().parent


def _discover_default_path() -> Path:
    """Pick a config location, preferring one next to the executable."""
    base = _executable_dir()
    for candidate in (base / "config" / "config.json", base / "config.json"):
        if candidate.is_file():
            return candidate
    if _DEFAULT_PATH.is_file():
        return _DEFAULT_PATH
    return base / "config" / "config.json"


def ensure_config_file(path: str | Path | None = None) -> Path:
    """Create a config.json from defaults if it does not exist yet."""
    config_path = Path(path) if path else _discover_default_path()
    if config_path.is_file():
        return config_path
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(_DEFAULTS, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    return config_path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = deepcopy(_DEFAULTS)
    config_path = Path(path) if path else _discover_default_path()
    if config_path.is_file():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg = _deep_merge(cfg, raw)
        except Exception:
            pass
    else:
        ensure_config_file(config_path)

    try:
        port = int(cfg["ipc"].get("port", 37241))
        if not 1 <= port <= 65535:
            port = 37241
        cfg["ipc"]["port"] = port
    except Exception:
        cfg["ipc"]["port"] = 37241

    overlay = cfg["overlay"]
    try:
        overlay["opacity"] = min(1.0, max(0.15, float(overlay.get("opacity", 0.85))))
    except Exception:
        overlay["opacity"] = 0.85
    for key, default in (("x", 20), ("y", 20), ("width", 800), ("height", 400)):
        try:
            overlay[key] = int(overlay.get(key, default))
        except Exception:
            overlay[key] = default
    try:
        overlay["max_displayed_events"] = max(
            50, int(overlay.get("max_displayed_events", 500))
        )
    except Exception:
        overlay["max_displayed_events"] = 500

    return cfg
