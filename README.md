# TS4 Log Overlay

Real-time **Sims 4 log capture** (script mod) paired with a **Windows desktop overlay** that displays normalized log events live — color-coded by severity, filterable, and configurable — without ever blocking or destabilizing the game.

> A diagnostic tool for Sims 4 players and mod developers. It hooks the game's built-in `sims4.log` facility and Python exception handler, normalizes the events, writes them to a local file, and streams them over localhost UDP to a transparent overlay.

---

## Features

- **Live capture** of `sims4.log` events (INFO / WARNING / ERROR / DEBUG) plus Python exceptions via `sys.excepthook`.
- **Normalization** into a consistent structured event schema (`timestamp`, `level`, `message`, `source`, `logger`, `session_id`, `exception`, `stack_trace`, …).
- **Independent file logging** that keeps working even when the overlay is closed.
- **Non-blocking localhost UDP** transport — a missing overlay never blocks the game, and connection failures are handled gracefully.
- **Severity filtering** on both the mod side and the overlay side.
- **Token-bucket rate limiting** with ERROR/WARNING priority over INFO/DEBUG (spam can't starve errors).
- **Bounded buffers** and automatic log-file rotation — no unbounded memory growth.
- **Overlay UI**: severity colors, text + logger search, severity checkboxes, auto-scroll toggle, pause, clear, collapse repeated events with occurrence counts, expandable exception/stack trace, copy event, drag-to-move, bottom-right resize, click-through mode.
- **Configurable** appearance and behavior via `config.json` — no recompile needed.

---

## Requirements

- **Sims 4** with **Script Mods Allowed** enabled (tested on **1.124** / embedded **Python 3.7**).
- **Windows** for the overlay (Win32 styles used).
- **Windowed or borderless** game mode (see below).

### Important: game display mode

The overlay only appears correctly when the game runs in **windowed** or **borderless (windowed-fullscreen)** mode.

Add this to `Documents\Electronic Arts\The Sims 4\Options.ini`:

```ini
fullscreen = 0
windowedfullscreen = 1
```

Or simply run the game in normal windowed mode. **Exclusive fullscreen is not supported** — the overlay cannot stay on top of it.

---

## Quick start

The packaged release (`LogOverlay.zip`) contains:

```text
Overlay/                Windows overlay (Overlay.exe + DLLs)
LogOverlay.ts4script    the game-side script mod
README.txt              full instructions
```

1. **Install the mod**: copy `LogOverlay.ts4script` into `Documents\Electronic Arts\The Sims 4\Mods`, then enable **Game Options → Other → Script Mods Allowed = ON** and restart the game.
2. **Run the overlay**: run `Overlay\Overlay.exe`. On first run it auto-creates `Overlay\config\config.json` next to the exe — edit it and restart to change settings. Keep the whole `Overlay` folder together (the exe needs its DLLs).
3. Make sure the game is **windowed / borderless** (`windowedfullscreen = 1`).
4. Check the mod's self-diagnostics at `Documents\Electronic Arts\The Sims 4\mod_logs\LogOverlay_self.log`.

---

## Repository layout

```text
modfile/                 # ready-to-install LogOverlay.ts4script
ts4_mod/                 # game-side pipeline (Python 3.7)
  capture.py             #   sims4.log + excepthook capture
  normalize.py           #   raw -> normalized event
  filter.py              #   severity + rate limiting
  ipc.py                 #   non-blocking UDP sender (valid-JSON truncation)
  file_logger.py         #   human-readable combined + per-level logs (optional JSONL), rotation
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
publish/                 # mod-site descriptions, SignPath checklist, CurseForge zip
.github/workflows/       # CI: builds Overlay.exe (SignPath requirement)
```

---

## Running the overlay from source (development)

```powershell
.\.venv\Scripts\python.exe -m overlay.main
```

Synthetic traffic without the game:

```powershell
.\.venv\Scripts\python.exe -m tools.demo_sender
```

If `.venv` is missing:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-overlay.txt
```

---

## Config

Edit `config/config.json` (or `Overlay\config\config.json` next to the exe):

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
  "file_logging": { "enabled": true, "directory": "mod_logs", "max_file_size_mb": 50, "flush_on_error": true, "max_log_age_days": 7, "human_readable": true, "split_by_level": true, "write_json": false },
  "mod": { "session_id_prefix": "ts4", "ipc_enabled": true, "capture_exceptions": true }
}
```

`file_logging.write_json: true` writes a raw JSONL dump for diagnostics; it is
temporary and removed when the game closes. With the default `false`, only the
human-readable logs are written. Old log files older than `max_log_age_days`
are removed automatically at startup.

Invalid values fall back to safe defaults. Overlay-side filters never affect what the mod writes to disk.

---

## Logs

Captured events are written to `Documents\Electronic Arts\The Sims 4\mod_logs\`
while the game runs (even when the overlay is closed):

```text
ts4-log-20260814-121152-session.log          all events, one file
ts4-log-20260814-121152-session.ERROR.log    errors only
ts4-log-20260814-121152-session.WARNING.log  warnings only
ts4-log-20260814-121152-session.INFO.log     info only
ts4-log-20260814-121152-session.DEBUG.log    debug only
```

Lines look like `2026-08-14 12:11:52 | ERROR | logger | message`, with
exceptions and stack traces indented below. Files older than `max_log_age_days`
(7 by default) are cleaned automatically at startup.

If `file_logging.write_json` is `true`, a raw `ts4-log-*.jsonl` dump is also
written for debugging and removed when the game closes. The mod's own
diagnostics are in `LogOverlay_self.log` in the same folder.

---

## Building

- **Mod** (`.ts4script`): `python -m tools.package_mod` (needs `tools/python37`).
- **Overlay exe**: `python -m tools.build_overlay` (needs Nuitka + Visual Studio Build Tools; outputs to `dist/Overlay`).

---

## Notes

- The overlay is designed to never block the game: UDP drops a datagram rather than stall the game thread.
- Do not run **Sims Log Enabler** at the same time until coexistence is tested — both hook `sims4.log.Logger`.

---

## Code signing policy

Windows binaries (`Overlay.exe`) published in GitHub Releases are built from this
repository by **GitHub Actions** (`.github/workflows/build-overlay.yml`) and are
eligible for signing under the SignPath Foundation program.

- Only artifacts produced by CI (built from source in this repository) are signed.
- Every release is reviewed and approved manually before signing.
- No binaries are built or signed outside this repository.
- The private key never leaves SignPath's hardware security module.

Free code signing provided by [SignPath.io](https://signpath.io), certificate by
SignPath Foundation. Build trust: verify the VirusTotal link in the release notes
before running any binary.

## License

MIT License — see [`LICENSE`](LICENSE). Copyright (c) 2026 AnonBOTpl.
The Sims is a trademark of Electronic Arts; this project is an unofficial,
fan-made diagnostic tool, not affiliated with EA.
