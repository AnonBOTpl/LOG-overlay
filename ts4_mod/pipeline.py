"""Wire capture → normalize → filter → file + IPC."""

from __future__ import absolute_import

from ts4_mod.capture import LogCapture
from ts4_mod.config import load_config
from ts4_mod.file_logger import FileLogger
from ts4_mod.filter import EventFilter
from ts4_mod.ipc import UdpIpcSender
from ts4_mod.normalize import normalize_event
from ts4_mod.self_log import close as self_close
from ts4_mod.self_log import write as self_write
from ts4_mod.self_log import write_exception as self_write_exception
from ts4_mod.session import make_session_id

_STATE = {
    "started": False,
    "session_id": None,
    "capture": None,
    "file_logger": None,
    "ipc": None,
    "filter": None,
    "config": None,
}


def start_pipeline(config_path=None):
    if _STATE["started"]:
        self_write("start_pipeline called but already started", level="WARNING")
        return _STATE

    self_write("start_pipeline begin", level="INFO")
    cfg = load_config(config_path)
    meta = cfg.get("_meta") or {}
    self_write(
        "config loaded in_ts4={0} config_path={1} file_dir={2}".format(
            meta.get("in_ts4"),
            meta.get("config_path"),
            cfg.get("file_logging", {}).get("directory"),
        ),
        level="INFO",
    )

    session_id = make_session_id(cfg.get("mod", {}).get("session_id_prefix", "ts4"))
    self_write("session_id={0}".format(session_id), level="INFO")

    event_filter = EventFilter(cfg.get("logging", {}))

    # Always prefer Sims 4 mod_logs for captured event files when in-game,
    # unless user set an absolute directory in config.
    file_dir = cfg["file_logging"]["directory"]
    file_logger = FileLogger(
        directory=file_dir,
        session_id=session_id,
        max_file_size_mb=cfg["file_logging"].get("max_file_size_mb", 50),
        flush_on_error=cfg["file_logging"].get("flush_on_error", True),
        enabled=cfg["file_logging"].get("enabled", True),
    )
    file_logger.prune_old_logs(cfg["file_logging"].get("max_log_age_days", 7))

    ipc = None
    if cfg.get("mod", {}).get("ipc_enabled", True):
        ipc = UdpIpcSender(
            host=cfg["ipc"].get("host", "127.0.0.1"),
            port=cfg["ipc"].get("port", 37241),
            max_datagram_bytes=cfg["ipc"].get("max_datagram_bytes", 8192),
        )
        self_write(
            "ipc enabled udp://{0}:{1}".format(
                cfg["ipc"].get("host", "127.0.0.1"),
                cfg["ipc"].get("port", 37241),
            ),
            level="INFO",
        )
    else:
        self_write("ipc disabled by config", level="WARNING")

    def emit(level, message, logger=None, exception=None, stack_trace=None):
        event = normalize_event(
            message=message,
            level=level,
            logger=logger,
            source="ts4",
            session_id=session_id,
            exception=exception,
            stack_trace=stack_trace,
        )

        # Always mirror our own logger traffic into the self log.
        if str(logger or "").startswith("log_overlay"):
            self_write(
                "[{0}] {1}".format(event.get("level"), event.get("message")),
                level=event.get("level", "INFO"),
            )

        # File logging: keep ERROR always; other levels follow mod filter.
        if event_filter.level_allowed(event["level"]) or event["level"] == "ERROR":
            file_logger.write(event)

        if not event_filter.allow(event):
            return

        if ipc is not None:
            ipc.send_event(event)

    try:
        capture = LogCapture(
            emit_callback=emit,
            capture_exceptions=cfg.get("mod", {}).get("capture_exceptions", True),
        )
        hooked = capture.install()
        self_write("LogCapture.install returned hooked={0}".format(hooked), level="INFO")
    except Exception as exc:
        self_write_exception("LogCapture.install failed", exc)
        raise

    # Force a visible pipeline heartbeat (WARNING so default filters keep it).
    emit(
        "WARNING",
        "LogOverlay pipeline online (menu is enough; household not required)",
        logger="log_overlay.pipeline",
    )

    _STATE.update(
        {
            "started": True,
            "session_id": session_id,
            "capture": capture,
            "file_logger": file_logger,
            "ipc": ipc,
            "filter": event_filter,
            "config": cfg,
        }
    )
    self_write(
        "start_pipeline complete file_log={0}".format(file_logger.path),
        level="INFO",
    )
    return _STATE


def stop_pipeline():
    if not _STATE["started"]:
        return
    self_write("stop_pipeline begin", level="INFO")
    capture = _STATE.get("capture")
    if capture is not None:
        try:
            capture.uninstall()
        except Exception as exc:
            self_write_exception("capture.uninstall failed", exc)
    ipc = _STATE.get("ipc")
    if ipc is not None:
        try:
            ipc.close()
        except Exception as exc:
            self_write_exception("ipc.close failed", exc)
    file_logger = _STATE.get("file_logger")
    if file_logger is not None:
        try:
            file_logger.close()
        except Exception as exc:
            self_write_exception("file_logger.close failed", exc)
    _STATE.update(
        {
            "started": False,
            "session_id": None,
            "capture": None,
            "file_logger": None,
            "ipc": None,
            "filter": None,
            "config": None,
        }
    )
    self_write("stop_pipeline complete", level="INFO")
    self_close()


def get_state():
    return dict(_STATE)
