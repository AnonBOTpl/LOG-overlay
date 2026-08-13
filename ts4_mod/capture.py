"""
Capture layer: hook Sims 4 logging / exceptions.

Isolated so EA logging changes do not force rewrites of normalize/IPC/overlay.
"""

from __future__ import absolute_import

import sys
import traceback


class LogCapture(object):
    def __init__(self, emit_callback, capture_exceptions=True):
        """
        emit_callback(level, message, logger=None, exception=None, stack_trace=None)
        """
        self._emit = emit_callback
        self._capture_exceptions = bool(capture_exceptions)
        self._installed = False
        self._originals = {}
        self._previous_excepthook = None

    def install(self):
        if self._installed:
            return True
        hooked = self._hook_sims4_logger()
        if self._capture_exceptions:
            self._hook_excepthook()
        self._installed = True
        # Emit a bootstrap event even outside the game so desktop tests work.
        if not hooked:
            self._emit(
                "INFO",
                "LogCapture installed (sims4.log unavailable — desktop/dev mode)",
                logger="log_overlay.capture",
            )
        else:
            self._emit(
                "INFO",
                "LogCapture installed (sims4.log hooks active)",
                logger="log_overlay.capture",
            )
        return hooked

    def uninstall(self):
        if not self._installed:
            return
        try:
            import sims4.log as sims4_log  # type: ignore
        except Exception:
            sims4_log = None

        if sims4_log is not None:
            logger_cls = getattr(sims4_log, "Logger", None)
            for name, original in self._originals.items():
                if logger_cls is not None and hasattr(logger_cls, name):
                    setattr(logger_cls, name, original)

        if self._previous_excepthook is not None:
            sys.excepthook = self._previous_excepthook
            self._previous_excepthook = None

        self._originals = {}
        self._installed = False

    def _hook_sims4_logger(self):
        try:
            import sims4.log as sims4_log  # type: ignore
        except Exception:
            return False

        logger_cls = getattr(sims4_log, "Logger", None)
        if logger_cls is None:
            return False

        capture = self

        def _wrap(level_name, original):
            def hooked(self_logger, message, *args, **kwargs):
                try:
                    text = capture._format_message(message, args, kwargs)
                    group = getattr(self_logger, "group", None) or getattr(
                        self_logger, "default_owner", None
                    )
                    capture._emit(level_name, text, logger=group)
                except Exception:
                    pass
                if original is not None:
                    return original(self_logger, message, *args, **kwargs)
                return None

            return hooked

        for level_name in ("debug", "info", "warn", "error"):
            original = getattr(logger_cls, level_name, None)
            self._originals[level_name] = original
            mapped = "WARNING" if level_name == "warn" else level_name.upper()
            setattr(logger_cls, level_name, _wrap(mapped, original))

        # exception(message, ...) often carries exc info
        original_exc = getattr(logger_cls, "exception", None)
        self._originals["exception"] = original_exc

        def hooked_exception(self_logger, message, *args, **kwargs):
            try:
                text = capture._format_message(message, args, kwargs)
                group = getattr(self_logger, "group", None)
                exc = kwargs.get("exc") or kwargs.get("exception")
                stack = None
                exc_payload = None
                if exc is not None:
                    exc_payload = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                    stack = "".join(
                        traceback.format_exception(type(exc), exc, getattr(exc, "__traceback__", None))
                    )
                capture._emit(
                    "ERROR",
                    text,
                    logger=group,
                    exception=exc_payload,
                    stack_trace=stack,
                )
            except Exception:
                pass
            if original_exc is not None:
                return original_exc(self_logger, message, *args, **kwargs)
            return None

        setattr(logger_cls, "exception", hooked_exception)
        return True

    def _hook_excepthook(self):
        self._previous_excepthook = sys.excepthook
        capture = self

        def _hook(exc_type, exc_value, exc_tb):
            try:
                stack = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                capture._emit(
                    "ERROR",
                    str(exc_value),
                    logger="excepthook",
                    exception={
                        "type": getattr(exc_type, "__name__", str(exc_type)),
                        "message": str(exc_value),
                    },
                    stack_trace=stack,
                )
            except Exception:
                pass
            if capture._previous_excepthook is not None:
                return capture._previous_excepthook(exc_type, exc_value, exc_tb)
            return sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = _hook

    @staticmethod
    def _format_message(message, args, kwargs):
        text = message
        try:
            if args:
                # EA loggers often use .format-style braces.
                text = message.format(*args)
        except Exception:
            try:
                text = str(message) + " " + " ".join(str(a) for a in args)
            except Exception:
                text = str(message)
        owner = kwargs.get("owner")
        if owner:
            text = "[{0}] {1}".format(owner, text)
        return text
