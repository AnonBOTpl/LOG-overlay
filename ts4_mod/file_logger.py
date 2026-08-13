"""Independent JSONL file logger with simple size-based rotation."""

from __future__ import absolute_import

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
    ):
        self._enabled = bool(enabled)
        self._directory = directory
        self._session_id = session_id
        self._max_bytes = max(1, int(max_file_size_mb)) * 1024 * 1024
        self._flush_on_error = bool(flush_on_error)
        self._handle = None
        self._path = None
        self._failed = False

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

    def _rotate_if_needed(self):
        if self._handle is None or self._path is None:
            return
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
            if self._flush_on_error and event.get("level") == "ERROR":
                self._handle.flush()
            self._rotate_if_needed()
            return True
        except Exception:
            self._failed = True
            self.close()
            return False

    def close(self):
        if self._handle is not None:
            try:
                self._handle.flush()
                self._handle.close()
            except Exception:
                pass
            self._handle = None
