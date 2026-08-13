# TS4 Log Overlay

Real-time Sims 4 log capture (script mod) + Windows desktop overlay.

## Status

Scaffold / MVP skeleton. Capture hooks target TS4 **1.124** / embedded **Python 3.7**. Overlay runs as a separate process.

## Layout

```text
ts4_mod/          # game-side pipeline (Python 3.7)
overlay/          # desktop overlay (PySide6)
config/config.json
shared/schema.py
tools/demo_sender.py
logs/
RESEARCH.md
AGENTS.md
```

## Quick test (without the game)

Double-click or run from repo root:

```text
run_overlay.bat
```

In a second terminal / double-click:

```text
run_demo_sender.bat
```

Or manually with the venv interpreter (no Activate needed):

```powershell
cd C:\Users\Admin\Desktop\LOG-overlay
.\.venv\Scripts\python.exe -m overlay.main
.\.venv\Scripts\python.exe -m tools.demo_sender
```

If `.venv` is missing:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-overlay.txt
```

## Config

Edit `config/config.json` for IPC port, overlay geometry/opacity, severity gates, and file logging.

## Install mod into Sims 4

Important: The Sims 4 **ignores `.ts4script` archives that contain only `.py` files**.
Scripts must be compiled to **Python 3.7 `.pyc`** (same as Lot51 / S4CL / Better Exceptions).

```text
install_mod.bat
```

This compiles with `tools\python37`, builds `dist\LogOverlay.ts4script`, and copies it into `Mods`.

Dev fallback (loads raw `.py` via the special `Scripts` folder — do not use together with the `.ts4script`):

```text
install_mod_dev.bat
```

Then:

1. **Game Options → Other → Script Mods Allowed = ON**
2. Start `run_overlay.bat`
3. Launch Sims 4 in **windowed / borderless** (menu is enough)
4. Check `Documents\Electronic Arts\The Sims 4\mod_logs\LogOverlay_self.log`

## Notes

- Use Sims 4 **windowed / borderless** so the overlay can appear above the game.
- Building a single `Overlay.exe` comes later; for now use `run_overlay.bat`.
- Do not run Sims Log Enabler at the same time until coexistence is tested — both hook `sims4.log.Logger`.
