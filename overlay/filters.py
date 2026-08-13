"""Overlay-side filtering (independent from mod-side filters)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OverlayFilters:
    debug: bool = True
    info: bool = True
    warning: bool = True
    error: bool = True
    text_query: str = ""
    logger_query: str = ""
    enabled_levels: set[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.refresh_levels()

    def refresh_levels(self) -> None:
        enabled: set[str] = set()
        if self.debug:
            enabled.add("DEBUG")
        if self.info:
            enabled.add("INFO")
        if self.warning:
            enabled.add("WARNING")
        if self.error:
            enabled.add("ERROR")
        self.enabled_levels = enabled

    def accepts(self, event: dict[str, Any]) -> bool:
        level = str(event.get("level", "")).upper()
        if level not in self.enabled_levels:
            return False
        if self.text_query:
            needle = self.text_query.lower()
            hay = str(event.get("message", "")).lower()
            if needle not in hay:
                return False
        if self.logger_query:
            needle = self.logger_query.lower()
            hay = str(event.get("logger", "")).lower()
            if needle not in hay:
                return False
        return True
