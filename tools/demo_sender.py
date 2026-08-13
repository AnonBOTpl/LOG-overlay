"""
Desktop demo: simulate the TS4 mod IPC path without launching the game.

Usage (from repo root):
  python -m tools.demo_sender
"""

from __future__ import annotations

import argparse
import json
import random
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Send demo log events over UDP")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--interval", type=float, default=0.15)
    args = parser.parse_args()

    host, port = load_port()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    messages = [
        "Game systems initialized",
        "Failed to load tuning",
        "Interaction queue overflow",
        "Script hook installed",
        "Zone load complete",
        "Missing key in catalog",
    ]

    print(f"Sending {args.count} events to udp://{host}:{port}")
    for index in range(args.count):
        level = random.choices(levels, weights=[2, 3, 2, 2], k=1)[0]
        event = {
            "timestamp": time.time(),
            "level": level,
            "logger": random.choice(["sims4.tuning", "services", "interactions", "demo"]),
            "message": f"{random.choice(messages)} #{index}",
            "source": "demo",
            "session_id": "demo-session",
        }
        if level == "ERROR" and index % 5 == 0:
            event["exception"] = {"type": "KeyError", "message": "missing_key"}
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        sock.sendto(payload, (host, port))
        print(f"  -> {level}: {event['message']}")
        time.sleep(args.interval)

    sock.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
