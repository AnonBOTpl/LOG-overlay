"""Independent JSONL file logger with simple size-based rotation."""

from __future__ import absolute_import

import glob
import json
import os
import time


class FileLogger(object):
    def __init__(
        self,
        directory,
        session_id,
        max_file_size_mb=50,
        flush_on_error=True,
        enabled=True,
        size_check_every=128,
        size_check_interval=5.0,
    ):
        self._enabled = bool(enabled)
        self._directory = directory
        self._session_id = session_id
        self._max_bytes = max(1, int(max_file_size_mb)) * 1024 * 1024
        self._flush_on_error = bool(flush_on_error)
        self._handle = None
        self._path = None
        self._failed = False
        self._size_check_every = max(1, int(size_check_every))
        self._size_check_interval = max(0.5, float(size_check_interval))
        self._write_count = 0
        self._last_check_write = 0
        self._last_check_time = 0.0

    @property
    def path(self):
        return self._path

    def _open(self):
        if not self._enabled or self._failed:
            return False
        try:
            if not os.path.isdir(self._directory):
                os.makedirs(self._directory)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            filename = "ts4-log-{0}-{1}.jsonl".format(stamp, self._session_id)
            self._path = os.path.join(self._directory, filename)
            self._handle = open(self._path, "a", encoding="utf-8")
            return True
        except Exception:
            self._failed = True
            self._handle = None
            return False

    def _should_check_size(self):
        if self._write_count - self._last_check_write >= self._size_check_every:
            return True
        if time.time() - self._last_check_time >= self._size_check_interval:
            return True
        return False

    def _rotate_if_needed(self):
        if self._handle is None or self._path is None:
            return
        self._last_check_write = self._write_count
        self._last_check_time = time.time()
        try:
            self._handle.flush()
            if os.path.getsize(self._path) < self._max_bytes:
                return
            self._handle.close()
            self._handle = None
            self._open()
        except Exception:
            self._failed = True
            self.close()

    def write(self, event):
        if not self._enabled or self._failed:
            return False
        if self._handle is None and not self._open():
            return False
        try:
            line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            self._handle.write(line + "\n")
            self._write_count += 1
            if self._flush_on_error and event.get("level") == "ERROR":
                self._handle.flush()
            if self._should_check_size():
                self._rotate_if_needed()
            return True
        except Exception:
            self._failed = True
            self.close()
            return False

    def prune_old_logs(self, days=7):
        """Delete ts4-log-*.jsonl files older than `days` days (best-effort)."""
        if days is None or int(days) <= 0:
            return
        try:
            cutoff = time.time() - int(days) * 86400
            for path in glob.glob(os.path.join(self._directory, "ts4-log-*.jsonl")):
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                except Exception:
                    continue
        except Exception:
            pass

    def close(self):
        if self._handle is not None:
            try:
                self._handle.flush()
                self._handle.close()
            except Exception:
                pass
            self._handle = None
