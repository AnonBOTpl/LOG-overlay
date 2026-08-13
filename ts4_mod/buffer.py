"""Bounded in-memory buffer with severity-aware drop policy."""

from __future__ import absolute_import

from collections import deque

_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
}


class EventBuffer(object):
    def __init__(self, maxsize=256):
        self._maxsize = max(8, int(maxsize))
        self._queue = deque()

    def __len__(self):
        return len(self._queue)

    def push(self, event):
        """Push event. May drop lower-priority items when full. Never blocks."""
        if len(self._queue) < self._maxsize:
            self._queue.append(event)
            return True

        incoming_priority = _PRIORITY.get(event.get("level"), 0)
        # Drop the oldest event with priority strictly below incoming.
        for index, existing in enumerate(self._queue):
            if _PRIORITY.get(existing.get("level"), 0) < incoming_priority:
                del self._queue[index]
                self._queue.append(event)
                return True

        # Buffer full of equal/higher priority: drop incoming if lower/equal DEBUG/INFO,
        # otherwise drop oldest.
        if incoming_priority >= _PRIORITY["WARNING"]:
            self._queue.popleft()
            self._queue.append(event)
            return True
        return False

    def pop_many(self, limit=32):
        items = []
        while self._queue and len(items) < limit:
            items.append(self._queue.popleft())
        return items

    def clear(self):
        self._queue.clear()
