"""Always-on diagnostic logger for the mod itself (load / errors).

Writes under Documents/.../The Sims 4/mod_logs regardless of IPC filters.
Python 3.7 safe. Must never raise to callers.
"""

from __future__ import absolute_import

import os
import time
import traceback


_HANDLE = None
_PATH = None
_FAILED = False


def mod_logs_dir():
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    candidates = [
        os.path.join(profile, "Documents", "Electronic Arts", "The Sims 4", "mod_logs"),
        os.path.join(profile, "OneDrive", "Documents", "Electronic Arts", "The Sims 4", "mod_logs"),
        os.path.join(profile, "Dokumenty", "Electronic Arts", "The Sims 4", "mod_logs"),
    ]
    for path in candidates:
        parent = os.path.dirname(path)
        if os.path.isdir(parent):
            return path
    return candidates[0]


def self_log_path():
    return os.path.join(mod_logs_dir(), "LogOverlay_self.log")


def _ensure_handle():
    global _HANDLE, _PATH, _FAILED
    if _FAILED:
        return None
    if _HANDLE is not None:
        return _HANDLE
    try:
        directory = mod_logs_dir()
        if not os.path.isdir(directory):
            os.makedirs(directory)
        _PATH = self_log_path()
        _HANDLE = open(_PATH, "a", encoding="utf-8")
        return _HANDLE
    except Exception:
        _FAILED = True
        _HANDLE = None
        return None


def write(message, level="INFO"):
    """Append one diagnostic line. Never raises."""
    try:
        handle = _ensure_handle()
        if handle is None:
            return False
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{0}] [{1}] {2}\n".format(stamp, level, message)
        handle.write(line)
        handle.flush()
        return True
    except Exception:
        return False


def write_exception(message, exc=None):
    try:
        if exc is None:
            write(message, level="ERROR")
            return
        detail = "{0}: {1}".format(type(exc).__name__, exc)
        write("{0} | {1}".format(message, detail), level="ERROR")
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            write(tb.rstrip("\n"), level="ERROR")
    except Exception:
        pass


def close():
    global _HANDLE
    if _HANDLE is not None:
        try:
            _HANDLE.flush()
            _HANDLE.close()
        except Exception:
            pass
        _HANDLE = None
