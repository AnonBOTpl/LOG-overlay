"""Win32 helpers for topmost / click-through overlays."""

from __future__ import annotations

import sys

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040


def _user32():
    if sys.platform != "win32":
        return None
    import ctypes

    return ctypes.windll.user32


def apply_overlay_styles(
    hwnd: int,
    *,
    always_on_top: bool = True,
    click_through: bool = False,
) -> None:
    """
    Apply topmost / click-through styles.

    Opacity is intentionally NOT set here — use Qt setWindowOpacity().
    Mixing SetLayeredWindowAttributes(LWA_ALPHA) with Qt often breaks mouse hit-testing.
    """
    user32 = _user32()
    if user32 is None or not hwnd:
        return

    import ctypes

    # Prefer LongPtr on 64-bit Windows.
    get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

    ex_style = int(get_long(ctypes.c_void_p(hwnd), GWL_EXSTYLE))
    ex_style |= WS_EX_TOOLWINDOW
    if click_through:
        # Transparent hit-testing requires layered on Win32.
        ex_style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT
        # Leave layered alone if Qt already set it for opacity.

    if always_on_top:
        ex_style |= WS_EX_TOPMOST
    else:
        ex_style &= ~WS_EX_TOPMOST

    set_long(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex_style)

    insert_after = HWND_TOPMOST if always_on_top else HWND_NOTOPMOST
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
    user32.SetWindowPos(
        ctypes.c_void_p(hwnd),
        insert_after,
        0,
        0,
        0,
        0,
        flags,
    )


def is_click_through(hwnd: int) -> bool:
    user32 = _user32()
    if user32 is None or not hwnd:
        return False
    import ctypes

    get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    ex_style = int(get_long(ctypes.c_void_p(hwnd), GWL_EXSTYLE))
    return bool(ex_style & WS_EX_TRANSPARENT)
