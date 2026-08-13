"""
Shared conceptual schema for normalized log events.

The TS4 mod (Python 3.7) and the overlay (modern Python) both follow this
shape. Keep transport concerns out of this module.
"""

REQUIRED_FIELDS = ("timestamp", "level", "message", "source")

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

LEVEL_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
}

# Example normalized event (documentation only):
EXAMPLE_EVENT = {
    "timestamp": 1723580000.123,
    "level": "ERROR",
    "logger": "sims4.tuning",
    "message": "Failed to load tuning",
    "source": "ts4",
    "session_id": "2026-08-13T20-41-01-a81f",
    "exception": {
        "type": "KeyError",
        "message": "missing_key",
    },
}
