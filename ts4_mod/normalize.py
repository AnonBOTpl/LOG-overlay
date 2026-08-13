"""Normalize raw capture payloads into the shared event schema."""

from __future__ import absolute_import

import time

_LEVEL_MAP = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "FATAL": "ERROR",
    "EXCEPTION": "ERROR",
    "LEVEL_DEBUG": "DEBUG",
    "LEVEL_INFO": "INFO",
    "LEVEL_WARN": "WARNING",
    "LEVEL_ERROR": "ERROR",
    "LEVEL_FATAL": "ERROR",
    "LEVEL_EXCEPTION": "ERROR",
}


def map_level(raw_level):
    if raw_level is None:
        return "INFO"
    key = str(raw_level).strip().upper()
    return _LEVEL_MAP.get(key, "INFO")


def normalize_event(
    message,
    level="INFO",
    logger=None,
    source="ts4",
    session_id=None,
    exception=None,
    stack_trace=None,
    source_file=None,
    source_line=None,
    timestamp=None,
    extra=None,
):
    """Build a normalized event dict. Missing optional fields are omitted."""
    event = {
        "timestamp": float(timestamp if timestamp is not None else time.time()),
        "level": map_level(level),
        "message": "" if message is None else str(message),
        "source": source or "ts4",
    }

    if logger:
        event["logger"] = str(logger)
    if session_id:
        event["session_id"] = str(session_id)
    if exception:
        event["exception"] = exception
    if stack_trace:
        event["stack_trace"] = str(stack_trace)
    if source_file:
        event["source_file"] = str(source_file)
    if source_line is not None:
        try:
            event["source_line"] = int(source_line)
        except (TypeError, ValueError):
            pass
    if extra and isinstance(extra, dict):
        for key, value in extra.items():
            if key not in event:
                event[key] = value
    return event
