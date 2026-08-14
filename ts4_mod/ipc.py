"""Non-blocking localhost UDP sender for normalized events."""

from __future__ import absolute_import

import json
import socket


class UdpIpcSender(object):
    def __init__(self, host="127.0.0.1", port=37241, max_datagram_bytes=8192):
        self._addr = (host, int(port))
        self._max_bytes = max(512, int(max_datagram_bytes))
        self._sock = None

    def _ensure_socket(self):
        if self._sock is not None:
            return self._sock
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        self._sock = sock
        return sock

    @staticmethod
    def _fit_event(event, max_bytes):
        """
        Return (trimmed_event, encoded_bytes) that fit under max_bytes.
        Truncates large fields instead of cutting raw bytes, so the payload
        is always valid JSON and the overlay never drops the whole event.
        """
        trimmed = dict(event)
        trimmed["truncated"] = True

        def _head(value, fraction):
            text = str(value)
            keep = max(16, int(len(text) * fraction))
            return text[:keep] + "…" if len(text) > keep else text

        # Pre-shrink the two heavy text fields (keep the useful head).
        for key in ("stack_trace", "message"):
            value = trimmed.get(key)
            if isinstance(value, str) and len(value) > max_bytes // 4:
                trimmed[key] = _head(value, 0.25)

        exc = trimmed.get("exception")
        if isinstance(exc, dict):
            exc = dict(exc)
            exc["message"] = str(exc.get("message", ""))[:1024]
            trimmed["exception"] = exc

        # Iteratively halve the longest remaining text field until it fits.
        # No ellipsis here so the length strictly decreases (terminates).
        for _ in range(64):
            data = json.dumps(
                trimmed, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if len(data) <= max_bytes:
                return trimmed, data
            message = str(trimmed.get("message", ""))
            stack = str(trimmed.get("stack_trace", ""))
            if len(stack) > len(message) and len(stack) > 8:
                trimmed["stack_trace"] = stack[: max(1, len(stack) // 2)]
            elif len(message) > 8:
                trimmed["message"] = message[: max(1, len(message) // 2)]
            else:
                break

        # Nothing left to shrink: fall back to essential fields only.
        minimal = {
            "timestamp": trimmed.get("timestamp"),
            "level": trimmed.get("level", "INFO"),
            "message": _head(message, 0.5),
            "source": trimmed.get("source", "ts4"),
            "truncated": True,
        }
        if trimmed.get("logger"):
            minimal["logger"] = str(trimmed["logger"])[:128]
        if trimmed.get("session_id"):
            minimal["session_id"] = str(trimmed["session_id"])[:128]
        data = json.dumps(
            minimal, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return minimal, data

    def send_event(self, event):
        """Best-effort send. Never raises to callers. Never blocks."""
        try:
            payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
            data = payload.encode("utf-8")
            if len(data) > self._max_bytes:
                trimmed, data = self._fit_event(event, self._max_bytes)
            sock = self._ensure_socket()
            sock.sendto(data, self._addr)
            return True
        except (socket.error, OSError, ValueError, TypeError):
            return False

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
