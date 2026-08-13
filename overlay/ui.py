"""Main overlay window: interactive chrome strip + optional click-through body."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from overlay.filters import OverlayFilters
from overlay.ipc import UdpIpcReceiver
from overlay.log_model import DisplayEvent, LogModel
from overlay.win32_styles import apply_overlay_styles

LEVEL_COLORS = {
    "DEBUG": QColor("#9AA0A6"),
    "INFO": QColor("#E8EAED"),
    "WARNING": QColor("#FDD663"),
    "ERROR": QColor("#F28B82"),
}

CHROME_HEIGHT = 36
ROOT_STYLE = """
QWidget#root {
    background: rgba(20, 22, 28, 240);
    border: 1px solid rgba(255, 255, 255, 40);
}
QLabel#dragHandle {
    color: #E8EAED;
    font-weight: 600;
    padding: 4px 6px;
}
QLabel, QCheckBox {
    color: #E8EAED;
}
QLineEdit {
    background: rgba(0, 0, 0, 120);
    color: #E8EAED;
    border: 1px solid rgba(255, 255, 255, 30);
    padding: 4px;
}
QPushButton {
    background: rgba(255, 255, 255, 24);
    color: #E8EAED;
    border: 1px solid rgba(255, 255, 255, 30);
    padding: 4px 10px;
}
QPushButton:checked {
    background: rgba(242, 139, 130, 110);
}
QTextEdit {
    background: rgba(0, 0, 0, 90);
    color: #E8EAED;
    border: none;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 12px;
}
"""


def _frameless_flags() -> Qt.WindowType:
    return (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )


class DragHandle(QLabel):
    def __init__(self, on_drag, text: str = "TS4 Log Overlay") -> None:
        super().__init__(text)
        self._on_drag = on_drag
        self._drag_offset: QPoint | None = None
        self.setObjectName("dragHandle")
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_offset
            self._drag_offset = event.globalPosition().toPoint()
            self._on_drag(delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class ResizeGrip(QLabel):
    """Bottom-right drag handle to resize the overlay window."""

    def __init__(self, on_resize) -> None:
        super().__init__("⤡")
        self._on_resize = on_resize
        self._last_pos: QPoint | None = None
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip("Drag to resize")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._last_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            delta = pos - self._last_pos
            self._last_pos = pos
            # Convert device pixels to logical pixels so the window grows 1:1
            # with the cursor even on scaled (DPI) monitors.
            dpr = self.window().devicePixelRatioF() or 1.0
            self._on_resize(round(delta.x() / dpr), round(delta.y() / dpr))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._last_pos = None
        super().mouseReleaseEvent(event)


class ChromeWindow(QWidget):
    """Always-interactive title strip (never click-through)."""

    def __init__(self, controller: "OverlayController") -> None:
        super().__init__()
        self._controller = controller
        self.setWindowFlags(_frameless_flags())
        self.setWindowTitle("TS4 Log Overlay Chrome")

        root = QWidget(self)
        root.setObjectName("root")
        root.setStyleSheet(ROOT_STYLE)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self._drag = DragHandle(controller.move_by, "TS4 Log Overlay  —  drag here")
        layout.addWidget(self._drag, stretch=1)

        self._btn_click = QPushButton("Click-through")
        self._btn_click.setCheckable(True)
        self._btn_click.setToolTip("Body ignores mouse; this bar stays clickable")
        self._btn_click.clicked.connect(controller.toggle_click_through_from_button)
        layout.addWidget(self._btn_click)

        self._btn_close = QPushButton("✕")
        self._btn_close.setFixedWidth(32)
        self._btn_close.clicked.connect(controller.close)
        layout.addWidget(self._btn_close)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

    def set_click_through_checked(self, enabled: bool) -> None:
        self._btn_click.blockSignals(True)
        self._btn_click.setChecked(enabled)
        self._btn_click.blockSignals(False)


class BodyWindow(QMainWindow):
    """Log body; may be click-through while chrome stays interactive."""

    def __init__(self, controller: "OverlayController", config: dict[str, Any]) -> None:
        super().__init__()
        self._controller = controller
        overlay_cfg = config.get("overlay", {})
        logging_cfg = config.get("logging", {})

        self.setWindowTitle("TS4 Log Overlay Body")
        self.setWindowFlags(_frameless_flags())

        self._filters = OverlayFilters(
            debug=bool(logging_cfg.get("debug", True)),
            info=bool(logging_cfg.get("info", True)),
            warning=bool(logging_cfg.get("warning", True)),
            error=bool(logging_cfg.get("error", True)),
        )
        self._model = LogModel(
            max_events=int(overlay_cfg.get("max_displayed_events", 500)),
            collapse_repeats=True,
        )
        self._paused = False
        self._auto_scroll = bool(overlay_cfg.get("auto_scroll", True))
        self._last_by_line: dict[str, "DisplayEvent"] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("root")
        root.setStyleSheet(ROOT_STYLE)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self._chk_error = QCheckBox("ERROR")
        self._chk_warn = QCheckBox("WARNING")
        self._chk_info = QCheckBox("INFO")
        self._chk_debug = QCheckBox("DEBUG")
        self._chk_error.setChecked(self._filters.error)
        self._chk_warn.setChecked(self._filters.warning)
        self._chk_info.setChecked(self._filters.info)
        self._chk_debug.setChecked(self._filters.debug)
        for chk in (
            self._chk_error,
            self._chk_warn,
            self._chk_info,
            self._chk_debug,
        ):
            chk.stateChanged.connect(self._on_filter_changed)
            toolbar.addWidget(chk)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search message…")
        self._search.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._search, stretch=1)

        self._logger_search = QLineEdit()
        self._logger_search.setPlaceholderText("Filter logger…")
        self._logger_search.setFixedWidth(150)
        self._logger_search.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._logger_search)

        self._btn_pause = QPushButton("Pause")
        self._btn_pause.clicked.connect(self._toggle_pause)
        self._btn_clear = QPushButton("Clear")
        self._btn_clear.clicked.connect(self._clear)
        self._btn_auto = QPushButton("Auto-scroll")
        self._btn_auto.setCheckable(True)
        self._btn_auto.setChecked(self._auto_scroll)
        self._btn_auto.setToolTip("Follow new events; uncheck to inspect older lines")
        self._btn_auto.clicked.connect(self._toggle_auto_scroll)
        self._btn_copy = QPushButton("Copy")
        self._btn_copy.setToolTip("Copy the full event under the cursor (JSON)")
        self._btn_copy.clicked.connect(self._copy_at_cursor)
        toolbar.addWidget(self._btn_pause)
        toolbar.addWidget(self._btn_auto)
        toolbar.addWidget(self._btn_copy)
        toolbar.addWidget(self._btn_clear)
        layout.addLayout(toolbar)

        self._status = QLabel("Listening…")
        layout.addWidget(self._status)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        self._view.setFont(QFont("Consolas", 10))
        layout.addWidget(self._view, stretch=1)

        self._grip = ResizeGrip(self._controller.resize_by)
        self._grip.setFixedSize(18, 18)
        self._grip.setStyleSheet(
            "color: #E8EAED; background: rgba(255,255,255,24);"
            "border: 1px solid rgba(255,255,255,40);"
        )
        layout.addWidget(self._grip, alignment=Qt.AlignmentFlag.AlignRight)
        self.setCentralWidget(root)

    def _on_filter_changed(self) -> None:
        self._filters.error = self._chk_error.isChecked()
        self._filters.warning = self._chk_warn.isChecked()
        self._filters.info = self._chk_info.isChecked()
        self._filters.debug = self._chk_debug.isChecked()
        self._filters.text_query = self._search.text().strip()
        self._filters.logger_query = self._logger_search.text().strip()
        self._filters.refresh_levels()
        self.render_all()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._btn_pause.setText("Resume" if self._paused else "Pause")
        self._status.setText("Paused" if self._paused else "Listening…")

    @property
    def paused(self) -> bool:
        return self._paused

    def _toggle_auto_scroll(self) -> None:
        self._auto_scroll = self._btn_auto.isChecked()
        if self._auto_scroll:
            self._view.moveCursor(QTextCursor.MoveOperation.End)

    def _clear(self) -> None:
        self._model.clear()
        self._view.clear()
        self._last_by_line.clear()

    def _copy_at_cursor(self) -> None:
        """Copy the full JSON of the event whose line holds the text cursor."""
        block = self._view.textCursor().block()
        if block is None:
            return
        text = block.text()
        item = self._last_by_line.get(text)
        event = item.event if item is not None else None
        if event is None:
            self._status.setText("No event on cursor line")
            return
        try:
            import json as _json

            payload = _json.dumps(event, ensure_ascii=False, indent=2)
        except Exception:
            payload = str(event)
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(payload)
        self._status.setText("Copied event (cursor line)")


    def add_events(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            self._model.add(event)
        self.render_all()
        mode = "ON" if self._controller.click_through else "OFF"
        self._status.setText(
            f"Events: {len(self._model.items)}  body click-through={mode}"
        )

    def render_all(self) -> None:
        self._view.clear()
        cursor = self._view.textCursor()
        for item in self._model.items:
            event = item.event
            if not self._filters.accepts(event):
                continue
            level = event.get("level", "INFO")
            ts = datetime.fromtimestamp(float(event.get("timestamp", 0))).strftime(
                "%H:%M:%S"
            )
            logger = event.get("logger") or "-"
            suffix = f" ×{item.count}" if item.count > 1 else ""
            line = f"[{ts}] [{level}] [{logger}] {event.get('message', '')}{suffix}\n"
            fmt = QTextCharFormat()
            fmt.setForeground(LEVEL_COLORS.get(level, QColor("#E8EAED")))
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(line, fmt)
            exc = event.get("exception")
            if isinstance(exc, dict):
                detail = "  exception: {0}: {1}".format(
                    exc.get("type", "?"), exc.get("message", "")
                )
                detail_fmt = QTextCharFormat()
                detail_fmt.setForeground(QColor("#F28B82"))
                detail_fmt.setFontItalic(True)
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(detail + "\n", detail_fmt)
            stack = event.get("stack_trace")
            if stack:
                stack_fmt = QTextCharFormat()
                stack_fmt.setForeground(QColor("#C58AF9"))
                stack_fmt.setFontItalic(True)
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(str(stack).rstrip("\n") + "\n", stack_fmt)
            self._last_by_line[line] = item
        if self._auto_scroll:
            self._view.moveCursor(QTextCursor.MoveOperation.End)


class OverlayController:
    """Owns chrome + body windows and keeps them synced."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        overlay_cfg = config.get("overlay", {})
        self._click_through = bool(overlay_cfg.get("click_through", False))
        self._opacity = max(0.15, min(1.0, float(overlay_cfg.get("opacity", 0.85))))
        self._always_on_top = bool(overlay_cfg.get("always_on_top", True))

        self._x = int(overlay_cfg.get("x", 20))
        self._y = int(overlay_cfg.get("y", 20))
        self._width = int(overlay_cfg.get("width", 800))
        self._height = int(overlay_cfg.get("height", 400))

        self.chrome = ChromeWindow(self)
        self.body = BodyWindow(self, config)
        self.chrome.set_click_through_checked(self._click_through)

        self._receiver = UdpIpcReceiver(
            host=config.get("ipc", {}).get("host", "127.0.0.1"),
            port=int(config.get("ipc", {}).get("port", 37241)),
        )
        self._receiver.bind()

        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll_ipc)
        self._timer.start()

        # Hotkey backup (needs focus on chrome/body).
        self._shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self.chrome)
        self._shortcut.activated.connect(self.toggle_click_through_from_hotkey)

    @property
    def click_through(self) -> bool:
        return self._click_through

    def show(self) -> None:
        self._layout_windows()
        self.chrome.setWindowOpacity(self._opacity)
        self.body.setWindowOpacity(self._opacity)
        self.chrome.show()
        self.body.show()
        QTimer.singleShot(0, self._apply_native_styles)

    def _layout_windows(self) -> None:
        body_h = max(120, self._height - CHROME_HEIGHT)
        self.chrome.setGeometry(self._x, self._y, self._width, CHROME_HEIGHT)
        self.body.setGeometry(self._x, self._y + CHROME_HEIGHT, self._width, body_h)

    def move_by(self, delta: QPoint) -> None:
        self._x += delta.x()
        self._y += delta.y()
        self._layout_windows()

    def resize_by(self, dx: int, dy: int) -> None:
        self._width = max(200, self._width + dx)
        self._height = max(160, self._height + dy)
        self._layout_windows()

    def _apply_native_styles(self) -> None:
        # Chrome is NEVER click-through.
        apply_overlay_styles(
            int(self.chrome.winId()),
            always_on_top=self._always_on_top,
            click_through=False,
        )
        apply_overlay_styles(
            int(self.body.winId()),
            always_on_top=self._always_on_top,
            click_through=self._click_through,
        )
        self.chrome.setWindowOpacity(self._opacity)
        self.body.setWindowOpacity(self._opacity)
        # Keep chrome above body.
        self.chrome.raise_()

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = bool(enabled)
        self.chrome.set_click_through_checked(self._click_through)
        self._apply_native_styles()
        mode = "ON" if self._click_through else "OFF"
        self.body._status.setText(
            f"Events: {len(self.body._model.items)}  body click-through={mode}"
        )

    def toggle_click_through_from_button(self) -> None:
        self.set_click_through(self.chrome._btn_click.isChecked())

    def toggle_click_through_from_hotkey(self) -> None:
        self.set_click_through(not self._click_through)

    def _poll_ipc(self) -> None:
        events = self._receiver.poll()
        if not events or self.body.paused:
            return
        self.body.add_events(events)

    def close(self) -> None:
        self._timer.stop()
        self._receiver.close()
        self.body.close()
        self.chrome.close()


# Backwards-compatible name used by main.py
class OverlayWindow:
    def __init__(self, config: dict[str, Any]) -> None:
        self._controller = OverlayController(config)

    def show(self) -> None:
        self._controller.show()
