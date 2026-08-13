"""In-memory log model with bounded size and optional visual dedup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DisplayEvent:
    event: dict[str, Any]
    count: int = 1
    fingerprint: str = ""


def _fingerprint(event: dict[str, Any]) -> str:
    return "|".join(
        [
            str(event.get("level", "")),
            str(event.get("logger", "")),
            str(event.get("message", "")),
        ]
    )


@dataclass
class LogModel:
    max_events: int = 500
    collapse_repeats: bool = True
    items: list[DisplayEvent] = field(default_factory=list)

    def clear(self) -> None:
        self.items.clear()

    def add(self, event: dict[str, Any]) -> None:
        fp = _fingerprint(event)
        if self.collapse_repeats and self.items:
            last = self.items[-1]
            if last.fingerprint == fp:
                last.count += 1
                last.event = event
                return
        self.items.append(DisplayEvent(event=event, count=1, fingerprint=fp))
        overflow = len(self.items) - self.max_events
        if overflow > 0:
            del self.items[0:overflow]
