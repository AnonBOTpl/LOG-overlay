"""
TS4 Log Extractor mod package.

Loaded by The Sims 4 as a script mod. Keep this package free of overlay UI code.
Target runtime: Python 3.7 (embedded in TS4 1.124).
"""

from ts4_mod.self_log import write as self_write
from ts4_mod.self_log import write_exception as self_write_exception

__all__ = ["start_pipeline", "stop_pipeline"]


def _maybe_autoload():
    """Auto-start only inside The Sims 4 (sims4 module present)."""
    self_write("ts4_mod package import starting", level="INFO")
    try:
        import sims4  # type: ignore  # noqa: F401
    except Exception as exc:
        self_write(
            "sims4 not importable — desktop/dev mode, pipeline not auto-started ({0})".format(
                type(exc).__name__
            ),
            level="INFO",
        )
        return

    self_write("sims4 detected — starting pipeline", level="INFO")
    try:
        from ts4_mod.pipeline import start_pipeline, stop_pipeline

        globals()["start_pipeline"] = start_pipeline
        globals()["stop_pipeline"] = stop_pipeline
        state = start_pipeline()
        session = None
        if isinstance(state, dict):
            session = state.get("session_id")
        self_write(
            "pipeline started ok session_id={0}".format(session),
            level="INFO",
        )
    except Exception as exc:
        self_write_exception("pipeline failed to start", exc)


# Export stubs for import-time; replaced when pipeline import succeeds in-game.
def start_pipeline(config_path=None):
    from ts4_mod.pipeline import start_pipeline as _start

    return _start(config_path)


def stop_pipeline():
    from ts4_mod.pipeline import stop_pipeline as _stop

    return _stop()


def __on_teardown():
    """Called by the game when the mod is unloaded (game exit / reload)."""
    try:
        stop_pipeline()
    except Exception:
        pass


_maybe_autoload()
