# Research Notes — LOG-overlay MVP (2026-08-13)

Verified against local install unless noted otherwise.

## Local environment

| Item | Value |
|------|--------|
| Install path | `D:\Games\The Sims 4 Royalty and Legacy` |
| Game version | **1.124.55.1030** (`Documents\...\GameVersion.txt`) |
| Embedded Python | **3.7.0** (`Game\Bin\python37_x64.dll`) |
| Script archives | `Data\Simulation\Gameplay\{base,core,simulation}.zip` |
| Logging module | `core.zip` → `sims4/log.pyc` (compiled ~2024-07-17) |
| User folder | `C:\Users\Admin\Documents\Electronic Arts\The Sims 4` |

Relevant installed diagnostic mods (context only; do not depend on them):

- `Tmex-BetterExceptions.ts4script`
- `sims4communitylib.ts4script`
- `lot51_core.ts4script`

---

## 1. TS4 log capture

### How EA logging works

`sims4.log` (from `core.zip`) exposes:

- Levels: `LEVEL_DEBUG`, `LEVEL_INFO`, `LEVEL_WARN`, `LEVEL_ERROR`, `LEVEL_FATAL`, `LEVEL_EXCEPTION`
- Module helpers: `debug`, `info`, `warn`, `error`, `log`, `exception`, `callstack`
- Classes: `Logger`, `LoggerClass`, `ProductionLogger`, `CheatLogger`, `_BaseLogger`
- Sink: internal `_trace.trace(...)` (native/C side)
- Utilities: `OverrideTrace` (swap `_trace.trace`), `callback_on_error_or_exception`

By default, many `Logger.debug/info/warn/error` paths are effectively no-ops / macro stubs until enabled. That is why **Sims Log Enabler** (Scumbumbo / Turbodriver) works by reassigning:

```python
sims4.log.Logger.info = info
sims4.log.Logger.debug = debug
sims4.log.Logger.warn = warn
sims4.log.Logger.error = error
```

### Recommended capture strategy (isolated layer)

Primary (proven community pattern):

1. Wrap / replace `sims4.log.Logger.{debug,info,warn,error,exception}` (and preferably module-level twins).
2. In the wrapper: format message → emit normalized event → call original.
3. Optionally register `callback_on_error_or_exception` for ERROR/exception paths.
4. Optionally wrap `sys.excepthook` for uncaught Python exceptions (secondary source).

Do **not** rely on reading EA text log files as the primary live path.

### Constraints (mod side)

- Target bytecode / syntax: **Python 3.7** only.
- Prefer shipping `.py` inside `.ts4script` (zip) or compile with 3.7 — never 3.12+.
- No blocking I/O on the game thread: bounded queue + non-blocking UDP `sendto`.
- Avoid spamming EA logs with our own connection failures.
- Capture must stay in `capture.py`; normalization/IPC/file stay independent.

### Volume warning

EA emits a large volume of logs (especially startup/tuning). MVP should:

- Default IPC transmission to WARNING+ERROR (DEBUG/INFO optional).
- Always allow ERROR → local file unless user disables file logging.
- Rate-limit + drop DEBUG first under backpressure.

---

## 2. Windows overlay

### Required Win32 behavior

| Need | Mechanism |
|------|-----------|
| Always on top | `WS_EX_TOPMOST` / `HWND_TOPMOST` |
| Opacity | `WS_EX_LAYERED` + `SetLayeredWindowAttributes` (MVP) |
| Click-through | `WS_EX_TRANSPARENT` **together with** `WS_EX_LAYERED` |
| Interactive mode | Remove `WS_EX_TRANSPARENT` when user needs filters/search |
| Frameless | `WS_POPUP` / no chrome |
| Hide from Alt-Tab (optional) | `WS_EX_TOOLWINDOW` |

Notes:

- `WS_EX_TRANSPARENT` alone is insufficient / misleading; pair with layered.
- Full click-through disables all hit-testing — toggle for settings UI.
- Prefer Per-Monitor DPI awareness (v2) for multi-monitor position/size.

### Display mode compatibility

| TS4 mode | Overlay expected |
|----------|------------------|
| Windowed | Works |
| Borderless windowed | Works (recommended) |
| Exclusive fullscreen | Overlay usually **invisible** (bypasses DWM) |

MVP docs must tell users to use **borderless / windowed**. Exclusive fullscreen is unsupported without invasive graphics hooks (out of scope).

### Overlay stack recommendation

**MVP: Python 3.12 + PySide6 (Qt)** for the overlay process (separate from the game).

Why:

- Mature layered / frameless / topmost support on Windows
- Easy UDP listener + UI filters
- Packagable to `Overlay.exe` via PyInstaller later
- Avoids DearPyGui transparency/click-through gaps

Alternatives rejected for MVP:

- DearPyGui — fast, but transparency/click-through need fragile Win32 hacks
- C#/WPF — excellent Win32 integration, but adds a second language early

Game mod remains Python 3.7 and never imports Qt.

---

## 3. IPC

### Decision: UDP localhost for MVP — **confirmed**

| Transport | Verdict |
|-----------|---------|
| **UDP 127.0.0.1** | Prefer — connectionless, non-blocking, overlay optional |
| Named pipes | Better reliability, but connection lifecycle + blocking risk |
| Shared memory | Faster, more complex (sync, layout, cleanup) |
| File polling | High latency / disk churn — reject for live path |

### Protocol sketch

- Endpoint: `127.0.0.1:<configurable port>` (default e.g. `37241`)
- Payload: UTF-8 JSON (one event per datagram)
- Soft size target: **&lt; 8 KiB** per packet (avoid fragmentation pain); truncate long stack traces for IPC, keep full text in file log
- Sender: `SOCK_DGRAM`, `setblocking(False)`; swallow `BlockingIOError` / `OSError`
- Receiver: validate schema; ignore malformed packets
- No ACK in MVP (DEBUG loss acceptable; ERROR still on disk)

---

## 4. File logging

- Format: **JSON Lines** (`.jsonl`), UTF-8
- Directory: configurable; default under project/`logs` or Documents Sims 4 subfolder
- Independent of overlay lifetime
- Rotate by size (`max_file_size_mb`)
- Buffered writes + periodic flush; optional `flush_on_error=True`
- Include `session_id` on every line
- Never block forever on disk failure; disable file logger after repeated failures

---

## 5. MVP architecture confirmation

```text
TS4 (Py 3.7 mod)
  capture (hook Logger + excepthook)
    → normalize
      → filter / rate-limit / bounded buffer
        ├─→ file .jsonl
        └─→ UDP 127.0.0.1 (non-blocking)

Overlay.exe (separate process, PySide6)
  UDP recv → validate → UI (colors, severity filter, scroll)
```

### MVP feature cut

Must ship:

1. Logger hook capture  
2. Normalized events  
3. Local `.jsonl`  
4. UDP send/recv  
5. Real-time overlay display  
6. DEBUG/INFO/WARNING/ERROR colors + severity filters  
7. `config.json` with safe defaults  
8. Graceful overlay-down behavior  
9. Bounded memory  

Defer after pipeline is stable:

- Advanced search / include-exclude patterns  
- Rich stack UI  
- Sophisticated visual dedup  
- Named pipes / shared memory  

---

## 6. Open verification items (before/during first in-game test)

1. Confirm Logger monkey-patch still fires for EA groups on 1.124.55 (expect yes; API present in `core.zip`).
2. Measure startup log rate with WARNING+ERROR only vs all levels.
3. Confirm TS4 graphics mode (windowed vs exclusive) on this machine.
4. Install Python **3.7.x** on the host for packaging/compiling the `.ts4script` (overlay can stay on 3.12).

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Capture breaks after EA patch | Isolate in `capture.py` only |
| Log spam freezes game | Rate limit, severity priority, bounded queue |
| Overlay invisible | Require borderless/windowed |
| UDP drop under spam | File log is source of truth; drop DEBUG first |
| Conflict with Sims Log Enabler | Document mutual exclusion / load-order note |
| Conflict with Better Exceptions | Only wrap excepthook chain; call previous hook |
