"""
Desktop demo: simulate the TS4 mod IPC path without launching the game.

Sends a curated, realistic Sims 4 log session (game load + failing third-party
mods + diagnostics) so the overlay can be screenshotted. Deterministic content:
all four severity levels, repeated errors (shown as xN by the overlay) and one
exception with a stack trace.

Usage (from repo root):
  python -m tools.demo_sender [--interval 0.35]
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_port() -> tuple[str, int]:
    cfg_path = ROOT / "config" / "config.json"
    host, port = "127.0.0.1", 37241
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        host = raw.get("ipc", {}).get("host", host)
        port = int(raw.get("ipc", {}).get("port", port))
    except Exception:
        pass
    return host, port


STACK_MODULE = (
    'Traceback (most recent call last):\n'
    '  File "sims4/core_services.py", line 812, in _load_module\n'
    '    return _import(module_name)\n'
    '  File "sims4/core_services.py", line 120, in _import\n'
    '    module = __import__(name, globals(), locals(), [], 0)\n'
)

STACK_TUNING = (
    'Traceback (most recent call last):\n'
    '  File "sims4/tuning/tuning_manager.py", line 445, in get_instance\n'
    '    return self._tuned_classes[class_id]\n'
    '  File "sims4/tuning/serialization.py", line 93, in _load_tuning\n'
    '    key = raw_tuning["key"]\n'
)

# (level, logger, message, exception, stack_trace)
SCENARIO = [
    ("INFO", "sims4.core", "Script mod loaded: LogOverlay v1.0.0"),
    ("INFO", "sims4.core", "sims4.log hook installed (12 logger methods patched)"),
    ("DEBUG", "LogOverlay", "Session ts4-20260814-171500 started, IPC 127.0.0.1:37241"),
    ("INFO", "zone", "Zone load: Willow Creek (Residential)"),
    ("DEBUG", "LogOverlay", "IPC datagram 512 B, rate 15 evt/s, 0 dropped"),
    ("WARNING", "sims4.tuning", "Failed to load tuning for 'cas_parts' (WickedWhims): missing resource"),
    (
        "ERROR",
        "sims4.core",
        "ModuleNotFoundError: No module named 'llamalogic'",
        {"type": "ModuleNotFoundError", "message": "No module named 'llamalogic'"},
        STACK_MODULE,
    ),
    (
        "ERROR",
        "sims4.core",
        "ModuleNotFoundError: No module named 'andirz_corescript'",
        {"type": "ModuleNotFoundError", "message": "No module named 'andirz_corescript'"},
        STACK_MODULE,
    ),
    ("INFO", "services", "Services registered: AreaServer, Status, Time"),
    ("WARNING", "AffordanceInjection", "Duplicate affordance 'Social_Introduce' injected"),
    (
        "ERROR",
        "sims4.tuning",
        "KeyError: 'missing_key' in tuning lookup",
        {"type": "KeyError", "message": "missing_key"},
        STACK_TUNING,
    ),
    ("INFO", "zone", "Household loaded: The Smiths (4 sims) in 14.2s"),
    ("DEBUG", "LogOverlay", "Rotation check: 128 writes, file 1.2 MB"),
    ("WARNING", "simulation", "Simulation clock drift detected (+120 ms)"),
    ("INFO", "services", "Heartbeat: pipeline healthy, 0 events dropped"),
    (
        "ERROR",
        "sims4.core",
        "ModuleNotFoundError: No module named 'andirz_corescript'",
        {"type": "ModuleNotFoundError", "message": "No module named 'andirz_corescript'"},
        STACK_MODULE,
    ),
    (
        "ERROR",
        "sims4.core",
        "ModuleNotFoundError: No module named 'andirz_corescript'",
        {"type": "ModuleNotFoundError", "message": "No module named 'andirz_corescript'"},
        STACK_MODULE,
    ),
    (
        "ERROR",
        "sims4.core",
        "ModuleNotFoundError: No module named 'andirz_corescript'",
        {"type": "ModuleNotFoundError", "message": "No module named 'andirz_corescript'"},
        STACK_MODULE,
    ),
    ("INFO", "zone", "Zone save complete (28.5 KB)"),
    ("WARNING", "sims4.tuning", "Obsolete tuning ignored: 'household_dirty_lingerie'"),
    ("DEBUG", "LogOverlay", "prune_old_logs: removed 3 files older than 7 days"),
    ("INFO", "sims4.core", "LogOverlay self-check OK (hooked=True, 0 errors)"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Send demo log events over UDP")
    parser.add_argument("--interval", type=float, default=0.35)
    args = parser.parse_args()

    host, port = load_port()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Sending {len(SCENARIO)} events to udp://{host}:{port}")
    for index, item in enumerate(SCENARIO):
        level, logger, message = item[0], item[1], item[2]
        exception = item[3] if len(item) > 3 else None
        stack_trace = item[4] if len(item) > 4 else None
        event = {
            "timestamp": time.time(),
            "level": level,
            "logger": logger,
            "message": message,
            "source": "demo",
            "session_id": "demo-session",
        }
        if exception:
            event["exception"] = exception
        if stack_trace:
            event["stack_trace"] = stack_trace
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        sock.sendto(payload, (host, port))
        print(f"  -> {level}: {message}")
        time.sleep(args.interval)

    sock.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())