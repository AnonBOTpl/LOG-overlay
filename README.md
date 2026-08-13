# TS4 Log Overlay

Real-time **Sims 4 log capture** (script mod) paired with a **Windows desktop overlay** that displays normalized log events live — color-coded by severity, filterable, and configurable — without ever blocking or destabilizing the game.

> A diagnostic tool for Sims 4 players and mod developers. It hooks the game's built-in `sims4.log` facility and Python exception handler, normalizes the events, writes them to a local file, and streams them over localhost UDP to a transparent overlay.

---

## Features

- **Live capture** of `sims4.log` events (INFO / WARNING / ERROR / DEBUG) plus Python exceptions via `sys.excepthook`.
- **Normalization** into a consistent structured event schema (`timestamp`, `level`, `message`, `source`, `logger`, `session_id`, `exception`, `stack_trace`, …).
- **Independent file logging** (JSON Lines) that keeps working even when the overlay is closed.
- **Non-blocking localhost UDP** transport — a missing overlay never blocks the game, and connection failures are handled gracefully.
- **Severity filtering** on both the mod side and the overlay side.
- **Token-bucket rate limiting** with ERROR/WARNING priority over INFO/DEBUG (spam can't starve errors).
- **Bounded buffers** and automatic log-file rotation — no unbounded memory growth.
- **Overlay UI**: severity colors, text + logger search, severity checkboxes, auto-scroll toggle, pause, clear, collapse repeated events with occurrence counts, expandable exception/stack trace, copy event, drag-to-move, bottom-right resize, click-through mode.
- **Configurable** appearance and behavior via `config.json` — no recompile needed.

---

## Architecture

```text
                    THE SIMS 4
                        │
                        ▼
                ┌───────────────┐
                │  Log Capture  │   sims4.log hook + excepthook
                └───────┬───────┘
                        ▼
                ┌───────────────┐
                │  Normalizer   │
                └───────┬───────┘
                        ▼
          ┌───────────────────────────┐
          │ Filter / Deduplicate /    │
          │ Rate Limit / Buffer       │
          └─────────────┬─────────────┘
              ┌─────────┴─────────┐
              ▼                   ▼
        Local Log File          UDP (127.0.0.1)
                                  │
                                  ▼
                         ┌────────────────┐
                         │    Overlay     │
                         └────────────────┘
```

The two components are deliberately independent:

- **`ts4_mod/`** — game-side pipeline (Python 3.7, packaged as `.ts4script`).
- **`overlay/`** — Windows desktop overlay (PySide6), runs as a separate process, optionally packaged as `Overlay.exe` (Nuitka).

---

## Repository layout

```text
ts4_mod/                 # game-side pipeline (Python 3.7)
  capture.py             #   sims4.log + excepthook capture
  normalize.py           #   raw -> normalized event
  filter.py              #   severity + noisy-pattern filters
  buffer.py              #   bounded, priority-aware buffer
  ipc.py                 #   non-blocking UDP sender (valid-JSON truncation)
  file_logger.py         #   JSONL file logger with rotation
  pipeline.py            #   wires capture -> normalize -> filter -> file + IPC
  config.py              #   load/validate config, safe defaults
overlay/                 # desktop overlay (PySide6)
  main.py                #   entry point (DPI-aware)
  ui.py                  #   frameless chrome + body, filters, search, resize
  ipc.py                 #   UDP receiver
  log_model.py           #   event model with dedup/counts
  filters.py             #   overlay-side filtering
  config.py              #   overlay config (auto-created next to exe)
  win32_styles.py        #   topmost / layered / click-through styles
config/config.json       # shared config (mod + overlay)
shared/schema.py         # shared event schema constants
tools/
  package_mod.py         # build .ts4script (Python 3.7 .pyc)
  build_overlay.py       # build Overlay.exe (Nuitka standalone)
  demo_sender.py         # synthetic UDP demo traffic
```

---

## Requirements

- **Sims 4** with **Script Mods Allowed** enabled (tested on **1.124** / embedded **Python 3.7**).
- **Windows** for the overlay (Win32 styles used).
- The overlay needs **Python 3.12 + PySide6** when run from source, or the bundled **Overlay.exe**.

---

## Quick start (overlay from source)

From the repo root:

```text
run_overlay.bat
```

In a second terminal (synthetic traffic, no game needed):

```text
run_demo_sender.bat
```

Or manually (no venv activation required):

```powershell
.\.venv\Scripts\python.exe -m overlay.main
.\.venv\Scripts\python.exe -m tools.demo_sender
```

If `.venv` is missing:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-overlay.txt
```

---

## Install the mod into Sims 4

> The Sims 4 **ignores `.ts4script` archives that contain only `.py` files** — scripts must be compiled to **Python 3.7 `.pyc`** (same as Lot51 / S4CL / Better Exceptions).

```text
install_mod.bat
```

This compiles with `tools\python37`, builds `dist\LogOverlay.ts4script`, and copies it into `Mods`.

Dev fallback (loads raw `.py` via the special `Scripts` folder — **do not** use together with the `.ts4script`):

```text
install_mod_dev.bat
```

Then:

1. **Game Options → Other → Script Mods Allowed = ON**.
2. Start the overlay (`run_overlay.bat` or `Overlay.exe`).
3. Launch Sims 4 in **windowed / borderless** (the main menu is enough).
4. Check `Documents\Electronic Arts\The Sims 4\mod_logs\LogOverlay_self.log` for the mod's own self-diagnostics.

---

## Using the overlay exe

If you downloaded the release package (`LogOverlay.zip`):

1. Unzip anywhere.
2. Run **`Overlay.exe`**.
3. On first run it **auto-creates `config\config.json`** next to the exe — edit it and restart to change port, position, size, opacity, etc.
4. Keep the **whole folder** together (the exe needs its DLLs).

---

## Config

Edit `config/config.json`:

```jsonc
{
  "ipc": { "host": "127.0.0.1", "port": 37241, "max_datagram_bytes": 8192 },
  "overlay": {
    "opacity": 0.85,
    "x": 20, "y": 20,
    "width": 1300, "height": 400,
    "click_through": false,
    "always_on_top": true,
    "max_displayed_events": 500,
    "auto_scroll": true
  },
  "logging": { "debug": false, "info": true, "warning": true, "error": true, "max_events_per_second": 5000 },
  "file_logging": { "enabled": true, "directory": "mod_logs", "max_file_size_mb": 50, "flush_on_error": true },
  "mod": { "session_id_prefix": "ts4", "ipc_enabled": true, "capture_exceptions": true }
}
```

Invalid values fall back to safe defaults. Overlay-side filters never affect what the mod writes to disk.

---

## Building

- **Mod** (`.ts4script`): `python -m tools.package_mod` (needs `tools/python37`).
- **Overlay exe**: `python -m tools.build_overlay` (needs Nuitka + Visual Studio Build Tools; outputs to `dist/Overlay`).

---

## Notes

- Use Sims 4 in **windowed / borderless** so the overlay can appear above the game.
- Do not run **Sims Log Enabler** at the same time until coexistence is tested — both hook `sims4.log.Logger`.
- The overlay is designed to never block the game: UDP drops a datagram rather than stall the game thread.

---

## License

This project is provided as-is for personal and diagnostic use. Third-party mods and their licenses are the responsibility of their respective authors.
