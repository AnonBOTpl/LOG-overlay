"""Load and validate mod-side configuration (Python 3.7 safe)."""

from __future__ import absolute_import, print_function

import json
import os
import sys


_DEFAULTS = {
    "ipc": {
        "host": "127.0.0.1",
        "port": 37241,
        "max_datagram_bytes": 8192,
    },
    "logging": {
        "debug": True,
        "info": True,
        "warning": True,
        "error": True,
        "max_events_per_second": 5000,
    },
    "file_logging": {
        "enabled": True,
        "directory": "mod_logs",
        "max_file_size_mb": 50,
        "flush_on_error": True,
    },
    "mod": {
        "session_id_prefix": "ts4",
        "ipc_enabled": True,
        "capture_exceptions": True,
    },
}

_APP_DIR_NAME = "LogOverlay"


def running_in_ts4():
    return "sims4" in sys.modules


def _repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, os.pardir))


def _userprofile():
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def sims4_documents_dir():
    """Best-effort The Sims 4 user folder."""
    profile = _userprofile()
    candidates = [
        os.path.join(profile, "Documents", "Electronic Arts", "The Sims 4"),
        os.path.join(profile, "OneDrive", "Documents", "Electronic Arts", "The Sims 4"),
        os.path.join(profile, "Dokumenty", "Electronic Arts", "The Sims 4"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    # Fallback even if folder does not exist yet.
    return candidates[0]


def runtime_data_dir():
    """
    Writable config/log location.

    In-game: Documents/.../The Sims 4/LogOverlay
    Desktop: repo root (dev mode)
    """
    if running_in_ts4():
        return os.path.join(sims4_documents_dir(), _APP_DIR_NAME)
    return _repo_root()


def default_config_path():
    if running_in_ts4():
        return os.path.join(runtime_data_dir(), "config.json")
    repo_cfg = os.path.join(_repo_root(), "config", "config.json")
    if os.path.isfile(repo_cfg):
        return repo_cfg
    return os.path.join(runtime_data_dir(), "config.json")


def _deep_merge(base, override):
    result = dict(base)
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _clamp_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 37241
    if port < 1 or port > 65535:
        return 37241
    return port


def _bundled_seed_config():
    """Load packaged default config if present next to the mod package."""
    seeded = _deep_merge(_DEFAULTS, {})
    candidates = [
        os.path.join(_repo_root(), "config", "config.json"),
        os.path.join(_repo_root(), "default_config.json"),
        os.path.join(os.path.dirname(__file__), "default_config.json"),
    ]
    for candidate in candidates:
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, "r") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                return _deep_merge(seeded, raw)
        except Exception:
            continue
    return seeded


def ensure_runtime_config(path=None):
    """Create runtime config.json from defaults if missing (in-game)."""
    config_path = path or default_config_path()
    folder = os.path.dirname(config_path)
    try:
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
    except Exception:
        return config_path

    if os.path.isfile(config_path):
        return config_path

    seeded = _bundled_seed_config()
    try:
        with open(config_path, "w") as handle:
            json.dump(seeded, handle, indent=2, sort_keys=False)
            handle.write("\n")
    except Exception:
        pass
    return config_path


def load_config(path=None):
    """Load config.json and fall back to safe defaults on any error."""
    cfg = _deep_merge(_DEFAULTS, {})
    config_path = path or ensure_runtime_config()
    try:
        with open(config_path, "r") as handle:
            raw = json.load(handle)
        if isinstance(raw, dict):
            cfg = _deep_merge(cfg, raw)
    except Exception:
        pass

    cfg["ipc"]["port"] = _clamp_port(cfg.get("ipc", {}).get("port"))
    try:
        cfg["ipc"]["max_datagram_bytes"] = max(
            512, int(cfg["ipc"].get("max_datagram_bytes", 8192))
        )
    except (TypeError, ValueError):
        cfg["ipc"]["max_datagram_bytes"] = 8192

    try:
        cfg["logging"]["max_events_per_second"] = max(
            1, int(cfg["logging"].get("max_events_per_second", 500))
        )
    except (TypeError, ValueError):
        cfg["logging"]["max_events_per_second"] = 500

    directory = cfg.get("file_logging", {}).get("directory") or "mod_logs"
    if not os.path.isabs(directory):
        # Prefer The Sims 4\mod_logs for captured events (in-game and by default name).
        if directory in ("logs", "mod_logs") or running_in_ts4():
            directory = os.path.join(sims4_documents_dir(), "mod_logs")
        else:
            directory = os.path.join(runtime_data_dir(), directory)
    cfg["file_logging"]["directory"] = directory
    cfg["_meta"] = {
        "config_path": config_path,
        "runtime_data_dir": runtime_data_dir(),
        "in_ts4": running_in_ts4(),
    }
    return cfg
