"""Mod-side severity filtering and simple token-bucket rate limiting."""

from __future__ import absolute_import

import time

_LEVEL_ENABLED_KEYS = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warning",
    "ERROR": "error",
}

_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
}


class EventFilter(object):
    def __init__(self, logging_cfg):
        self._logging_cfg = logging_cfg or {}
        self._max_per_second = max(
            1, int(self._logging_cfg.get("max_events_per_second", 500))
        )
        self._window_start = time.time()
        self._window_count = 0
        # Reserve headroom so DEBUG spam cannot starve ERROR.
        self._low_priority_budget = max(1, int(self._max_per_second * 0.7))

    def level_allowed(self, level):
        key = _LEVEL_ENABLED_KEYS.get(level)
        if key is None:
            return True
        return bool(self._logging_cfg.get(key, True))

    def allow(self, event):
        level = event.get("level", "INFO")
        if not self.level_allowed(level):
            return False

        now = time.time()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._window_count = 0
            self._low_priority_budget = max(1, int(self._max_per_second * 0.7))

        if self._window_count >= self._max_per_second:
            # Prefer ERROR/WARNING when the global budget is exhausted.
            return _PRIORITY.get(level, 0) >= _PRIORITY["WARNING"]

        if _PRIORITY.get(level, 0) < _PRIORITY["WARNING"]:
            if self._low_priority_budget <= 0:
                return False
            self._low_priority_budget -= 1

        self._window_count += 1
        return True
