"""File logger with human-readable combined + per-level logs and optional JSONL.

Rotates files on size (checked on a throttle, not every event).
"""

from __future__ import absolute_import

import glob
import json
import os
import time

_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class FileLogger(object):
    def __init__(
        self,
        directory,
        session_id,
        max_file_size_mb=50,
        flush_on_error=True,
        enabled=True,
        human_readable=True,
        split_by_level=True,
        write_json=False,
        size_check_every=128,
        size_check_interval=5.0,
    ):
        self._enabled = bool(enabled)
        self._directory = directory
        self._session_id = session_id
        self._max_bytes = max(1, int(max_file_size_mb)) * 1024 * 1024
        self._flush_on_error = bool(flush_on_error)
        self._human_readable = bool(human_readable)
        self._split_by_level = bool(split_by_level) and self._human_readable
        self._write_json = bool(write_json)
        self._failed = False
        self._size_check_every = max(1, int(size_check_every))
        self._size_check_interval = max(0.5, float(size_check_interval))
        self._write_count = 0
        self._last_check_write = 0
        self._last_check_time = 0.0
        # name -> (path, handle); names: jsonl, log, debug, info, warning, error
        self._files = {}

    @property
    def path(self):
        for name in ("log", "jsonl"):
            entry = self._files.get(name)
            if entry is not None:
                return entry[0]
        return None

    @property
    def json_path(self):
        entry = self._files.get("jsonl")
        if entry is not None:
            return entry[0]
        return None

    def _open(self):
        if not self._enabled or self._failed:
            return False
        try:
            if not os.path.isdir(self._directory):
                os.makedirs(self._directory)
            base = "ts4-log-{0}-{1}".format(
                time.strftime("%Y%m%d-%H%M%S"), self._session_id
            )
            if self._write_json:
                self._add_file("jsonl", base + ".jsonl")
            if self._human_readable:
                self._add_file("log", base + ".log")
                if self._split_by_level:
                    for level in _LEVELS:
                        self._add_file(level.lower(), base + "." + level + ".log")
            return True
        except Exception:
            self._failed = True
            self.close()
            return False

    def _add_file(self, name, filename):
        path = os.path.join(self._directory, filename)
        handle = open(path, "a", encoding="utf-8")
        self._files[name] = (path, handle)

    def _reopen(self, name):
        """Rotate one file to a fresh timestamped name."""
        base = "ts4-log-{0}-{1}".format(
            time.strftime("%Y%m%d-%H%M%S"), self._session_id
        )
        if name == "jsonl":
            self._add_file(name, base + ".jsonl")
        elif name == "log":
            self._add_file(name, base + ".log")
        else:
            self._add_file(name, base + "." + name.upper() + ".log")

    def _should_check_size(self):
        if self._write_count - self._last_check_write >= self._size_check_every:
            return True
        if time.time() - self._last_check_time >= self._size_check_interval:
            return True
        return False

    def _rotate_if_needed(self):
        self._last_check_write = self._write_count
        self._last_check_time = time.time()
        if not self._files:
            return
        try:
            for name, (path, handle) in list(self._files.items()):
                handle.flush()
                if os.path.getsize(path) < self._max_bytes:
                    continue
                handle.close()
                del self._files[name]
                self._reopen(name)
        except Exception:
            self._failed = True
            self.close()

    def _format_human(self, event):
        ts = event.get("timestamp", 0)
        try:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
        except Exception:
            stamp = "?"
        level = event.get("level", "INFO")
        logger = event.get("logger") or "-"
        message = str(event.get("message", ""))
        lines = ["{0} | {1} | {2} | {3}".format(stamp, level, logger, message)]
        exc = event.get("exception")
        if isinstance(exc, dict):
            lines.append(
                "  exception: {0}: {1}".format(
                    exc.get("type", "?"), exc.get("message", "")
                )
            )
        stack = event.get("stack_trace")
        if stack:
            for line in str(stack).rstrip("\n").split("\n"):
                lines.append("  " + line)
        return "\n".join(lines)

    def write(self, event):
        if not self._enabled or self._failed:
            return False
        if not self._files and not self._open():
            return False
        if not self._files:
            return True
        try:
            level = event.get("level", "INFO")
            if self._write_json:
                entry = self._files.get("jsonl")
                if entry is not None:
                    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                    entry[1].write(line + "\n")
            if self._human_readable:
                text = self._format_human(event)
                entry = self._files.get("log")
                if entry is not None:
                    entry[1].write(text + "\n")
                key = level.lower()
                entry = self._files.get(key)
                if entry is not None:
                    entry[1].write(text + "\n")
            self._write_count += 1
            if self._flush_on_error and level == "ERROR":
                for name in ("jsonl", "log", "error"):
                    entry = self._files.get(name)
                    if entry is not None:
                        try:
                            entry[1].flush()
                        except Exception:
                            pass
            if self._should_check_size():
                self._rotate_if_needed()
            return True
        except Exception:
            self._failed = True
            self.close()
            return False

    def discard_json(self):
        """Close and delete this session's JSONL file (if any)."""
        entry = self._files.pop("jsonl", None)
        if entry is None:
            return
        path = entry[0]
        try:
            entry[1].close()
        except Exception:
            pass
        try:
            os.remove(path)
        except Exception:
            pass

    def prune_old_json(self):
        """Delete leftover JSONL files from earlier sessions (best-effort)."""
        try:
            for path in glob.glob(os.path.join(self._directory, "ts4-log-*.jsonl")):
                try:
                    os.remove(path)
                except Exception:
                    continue
        except Exception:
            pass

    def prune_old_logs(self, days=7):
        """Delete ts4-log-* files older than `days` days (best-effort)."""
        if days is None or int(days) <= 0:
            return
        try:
            cutoff = time.time() - int(days) * 86400
            for path in glob.glob(os.path.join(self._directory, "ts4-log-*")):
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                except Exception:
                    continue
        except Exception:
            pass

    def close(self):
        for entry in self._files.values():
            try:
                entry[1].flush()
                entry[1].close()
            except Exception:
                pass
        self._files = {}
