"""UDP receiver for normalized log events."""

from __future__ import annotations

import json
import socket
from typing import Any

REQUIRED = ("timestamp", "level", "message", "source")
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def validate_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    for key in REQUIRED:
        if key not in payload:
            return None
    level = str(payload.get("level", "")).upper()
    if level == "WARN":
        level = "WARNING"
    if level not in VALID_LEVELS:
        return None
    event = dict(payload)
    event["level"] = level
    event["message"] = str(event.get("message", ""))
    event["source"] = str(event.get("source", "unknown"))
    try:
        event["timestamp"] = float(event["timestamp"])
    except Exception:
        return None
    return event


class UdpIpcReceiver:
    def __init__(self, host: str = "127.0.0.1", port: int = 37241, bufsize: int = 65535):
        self._addr = (host, int(port))
        self._bufsize = bufsize
        self._sock: socket.socket | None = None

    def bind(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self._addr)
        sock.setblocking(False)
        self._sock = sock

    def poll(self, max_messages: int = 64) -> list[dict[str, Any]]:
        if self._sock is None:
            return []
        events: list[dict[str, Any]] = []
        for _ in range(max_messages):
            try:
                data, _addr = self._sock.recvfrom(self._bufsize)
            except BlockingIOError:
                break
            except OSError:
                break
            try:
                payload = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            event = validate_event(payload)
            if event is not None:
                events.append(event)
        return events

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
