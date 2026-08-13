"""Overlay entrypoint."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from overlay.config import load_config
from overlay.ui import OverlayWindow


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    config_path = None
    if len(argv) > 1:
        config_path = argv[1]

    app = QApplication(argv)
    app.setApplicationName("TS4 Log Overlay")
    cfg = load_config(config_path)
    window = OverlayWindow(cfg)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
