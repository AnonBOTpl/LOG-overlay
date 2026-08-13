# AGENTS.md: Real-Time Sims 4 Log Streamer & Overlay Architecture

## 1. Project Goal

The objective of this project is to build a two-part system that captures live execution logs from The Sims 4 during loading screens and gameplay, normalizes and filters those logs, saves them to local files, and displays them in a customizable, color-coded desktop overlay.

The system MUST be designed primarily as a diagnostic tool for Sims 4 players and mod developers.

The architecture MUST keep the Sims 4 mod lightweight and must NEVER allow the overlay application or IPC communication to block or destabilize the game.

---

## 2. System Architecture

The system consists of two primary components:

### 2.1 TS4 Log Extractor Mod (`.ts4script`)

Python-based script injected into The Sims 4.

Responsibilities:

* Capture relevant log events from the Sims 4 runtime.
* Hook or integrate with the appropriate Sims 4 logging/error mechanisms.
* Capture Python exceptions where technically possible.
* Normalize raw log messages into a consistent event structure.
* Apply lightweight filtering and rate limiting.
* Write normalized logs to a local log file.
* Send normalized log events to the desktop overlay through IPC.
* Never wait indefinitely for the overlay application.
* Continue functioning if the overlay is closed or unavailable.

### 2.2 Desktop Overlay Application (`Overlay.exe`)

Standalone Windows application.

Responsibilities:

* Receive normalized log events from the TS4 mod.
* Display logs in real time.
* Provide filtering by severity and logger/category.
* Provide text search.
* Visually distinguish INFO, WARNING, ERROR and DEBUG events.
* Collapse repeated identical events.
* Display occurrence counts for repeated events.
* Provide configurable appearance and position.
* Remain independent from the Sims 4 process.
* Never interfere with normal game input unless explicitly configured to do so.

---

# 3. Log Pipeline

The complete log pipeline MUST follow this conceptual architecture:

```text
                    THE SIMS 4
                        │
                        ▼
                ┌───────────────┐
                │  Log Capture  │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │  Normalizer   │
                └───────┬───────┘
                        │
                        ▼
          ┌───────────────────────────┐
          │ Filter / Deduplicate /    │
          │ Rate Limit / Buffer       │
          └─────────────┬─────────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        Local Log File          IPC
                                  │
                                  ▼
                         ┌────────────────┐
                         │    Overlay     │
                         ├────────────────┤
                         │ UI Filtering   │
                         │ Search         │
                         │ Dedup Display  │
                         │ Color Coding   │
                         └────────────────┘
```

The local file logging path MUST NOT depend on the overlay being active.

If `Overlay.exe` is closed, logs MUST still be written to disk.

---

# 4. Log Capture

The capture layer is responsible only for obtaining raw log/error information from Sims 4.

Possible sources include:

* `sims4.log`
* `sims4.log` internal logging facilities
* Sims 4 Python logging modules
* Python exception handling
* `sys.excepthook`
* Other verified internal logging mechanisms

The implementation MUST NOT assume that undocumented Sims 4 internals are stable.

Before implementation, the current Sims 4 Python environment and logging implementation MUST be researched and verified.

The capture layer SHOULD remain isolated from the rest of the system so that changes to Sims 4 logging internals do not require rewriting the normalization, IPC or overlay layers.

---

# 5. Log Normalization

Raw Sims 4 log messages MUST be converted into a normalized internal event format before being sent to the overlay.

The overlay MUST NOT need to understand the internal format of Sims 4 logging.

A normalized event SHOULD contain fields similar to:

```json
{
  "timestamp": 1723580000.123,
  "level": "ERROR",
  "logger": "sims4.tuning",
  "message": "Failed to load tuning",
  "source": "ts4",
  "session_id": "abc123",
  "exception": {
    "type": "KeyError",
    "message": "missing_key"
  }
}
```

## 5.1 Required Fields

Every normalized event MUST contain:

* `timestamp`
* `level`
* `message`
* `source`

The following SHOULD also be present whenever available:

* `logger`
* `session_id`
* `exception`
* `exception_type`
* `stack_trace`
* `source_file`
* `source_line`

Missing optional information MUST NOT cause the event to be discarded.

---

# 6. Severity Levels

The normalized system MUST support at least:

* `DEBUG`
* `INFO`
* `WARNING`
* `ERROR`

If Sims 4 exposes additional severity levels, they SHOULD be mapped to the closest normalized level.

The normalization layer MUST preserve the original severity information where possible.

---

# 7. Log Filtering

Filtering MUST exist at two different levels.

## 7.1 Mod-Side Filtering

The TS4 mod SHOULD be able to prevent unnecessary events from being transmitted through IPC.

Examples:

* Disable DEBUG transmission.
* Disable INFO transmission.
* Enable only WARNING and ERROR.
* Filter specific logger/category names.
* Ignore known noisy patterns.

Mod-side filtering exists primarily to reduce:

* CPU usage.
* IPC traffic.
* Memory usage.
* Unnecessary processing.

Mod-side filtering MUST NOT prevent important ERROR events from being written to the local log file unless explicitly configured by the user.

## 7.2 Overlay-Side Filtering

The overlay MUST provide independent filtering.

Example:

```text
☑ ERROR
☑ WARNING
☐ INFO
☐ DEBUG
```

Changing overlay filters MUST NOT affect what the TS4 mod writes to disk.

The overlay SHOULD support:

* Severity filtering.
* Logger/category filtering.
* Text filtering.
* Include patterns.
* Exclude patterns.

---

# 8. Deduplication

The system SHOULD detect repeated identical or effectively identical log events.

Example:

```text
ERROR Failed to load tuning
ERROR Failed to load tuning
ERROR Failed to load tuning
...
```

The overlay SHOULD be able to display this as:

```text
[ERROR] Failed to load tuning    × 47
```

Repeated events SHOULD contain or internally generate a stable message hash.

Deduplication MUST NOT permanently discard information from the local log file unless the user explicitly enables aggressive deduplication.

The preferred behavior is:

* Preserve full events in the log file.
* Collapse repeated events visually in the overlay.

---

# 9. Rate Limiting

The system MUST protect the game and overlay from excessive log spam.

A configurable maximum event rate SHOULD be supported.

Example:

```text
max_events_per_second = 500
```

Rate limiting SHOULD be applied separately by severity where practical.

ERROR and WARNING events SHOULD receive higher priority than DEBUG and INFO events.

The implementation MUST prevent a DEBUG spam source from starving ERROR events.

Rate limiting MUST NOT cause the Sims 4 process to block while waiting for the overlay.

---

# 10. Buffering and Backpressure

The TS4 mod MUST use a non-blocking or effectively non-blocking buffering strategy.

The overlay MUST NOT be able to block the Sims 4 main execution path.

If the overlay becomes unavailable:

1. The mod MUST continue operating.
2. File logging MUST continue.
3. IPC failures MUST be handled gracefully.
4. The mod SHOULD periodically retry the connection/transmission.
5. The mod MUST NOT continuously generate connection errors inside the Sims 4 log.

The IPC layer MUST have bounded memory usage.

The system MUST define what happens when the IPC buffer becomes full.

Preferred priority:

```text
ERROR
WARNING
INFO
DEBUG
```

Lower-priority events MAY be dropped before higher-priority events.

---

# 11. Local File Logging

Normalized logs MUST also be written to a local file.

File logging MUST operate independently from the overlay.

The expected behavior is:

```text
TS4
 │
 ├──► Local log file
 │
 └──► Overlay IPC
```

Closing `Overlay.exe` MUST NOT stop file logging.

The log file SHOULD use a machine-readable format such as JSON Lines (`.jsonl`) or another format selected during implementation.

Example:

```json
{"timestamp":1723580000.123,"level":"INFO","message":"Game started"}
{"timestamp":1723580001.241,"level":"WARNING","message":"Example warning"}
{"timestamp":1723580002.552,"level":"ERROR","message":"Failed to load tuning"}
```

The implementation SHOULD support:

* Automatic log file creation.
* UTF-8 encoding.
* Safe flushing.
* Reasonable file rotation or size limits.
* Crash-safe writing where practical.
* Configurable log directory.

The file logger MUST NOT significantly increase Sims 4 loading times or gameplay overhead.

---

# 12. Session Identification

Each Sims 4 launch SHOULD receive a unique `session_id`.

The session ID allows events from different game launches to be distinguished.

Example:

```text
session_id = "2026-08-13T20-41-01-a81f"
```

The session ID SHOULD be included in normalized events and local log files.

The system does NOT need session replay or historical replay functionality.

---

# 13. IPC

The MVP MUST use localhost IPC.

Preferred transport:

```text
UDP 127.0.0.1
```

UDP SHOULD be preferred for the initial implementation because:

* It is lightweight.
* It does not require a persistent connection.
* A missing overlay does not need to block the sender.
* Localhost latency should be extremely low.
* Losing an individual DEBUG event is generally acceptable.

Alternative mechanisms such as:

* Named Pipes
* Shared Memory
* File Polling
* WebSockets

MAY be researched but MUST NOT be implemented in the MVP unless research identifies a concrete technical blocker with localhost UDP.

---

# 14. IPC Event Format

IPC MUST transmit normalized events rather than raw Sims 4 log strings.

The serialization format SHOULD be:

* JSON for initial development and debugging.

The protocol SHOULD be designed so that a more compact format can be introduced later without changing the internal log model.

The overlay MUST validate incoming events before rendering them.

Malformed IPC messages MUST be ignored safely.

---

# 15. Overlay Rendering

The overlay MUST be:

* Frameless.
* Transparent.
* Always-on-top.
* Configurable.
* Lightweight.
* Suitable for use over The Sims 4.

Windows APIs/styles that MUST be researched include:

* `WS_EX_TRANSPARENT`
* `WS_EX_LAYERED`
* `WS_EX_TOPMOST`

The overlay SHOULD support click-through behavior.

The implementation MUST consider the difference between:

* Windowed mode.
* Borderless windowed mode.
* Fullscreen mode.

Compatibility with exclusive fullscreen MUST be researched rather than assumed.

---

# 16. Overlay Features

The MVP overlay SHOULD provide:

### Required

* Real-time log display.
* Severity colors.
* Auto-scroll.
* Pause scrolling.
* Clear display.
* Severity filters.
* Basic search.
* Configurable transparency.
* Configurable position.
* Configurable size.

### Strongly Recommended

* Collapsing repeated events.
* Occurrence counters.
* Logger/category filtering.
* Copy event/message.
* Expandable exception details.
* Expandable stack traces.
* Maximum number of displayed events.
* Automatic removal of old UI entries.

The overlay MUST avoid keeping unlimited log entries in memory.

---

# 17. Configuration

Configuration MUST be external to the executable.

Preferred format:

```text
config.json
```

Configuration SHOULD support:

```json
{
  "overlay": {
    "opacity": 0.85,
    "x": 20,
    "y": 20,
    "width": 800,
    "height": 400,
    "click_through": true
  },
  "logging": {
    "debug": true,
    "info": true,
    "warning": true,
    "error": true,
    "max_events_per_second": 500
  },
  "file_logging": {
    "enabled": true,
    "directory": "logs",
    "max_file_size_mb": 50
  }
}
```

Configuration MUST be validated.

Invalid configuration values MUST fall back to safe defaults instead of crashing the overlay or TS4 mod.

---

# 18. Error Handling

The system MUST fail gracefully.

### If the overlay crashes:

* Sims 4 MUST continue running.
* File logging MUST continue.
* The TS4 mod MUST continue operating.

### If the overlay is not running:

* Sims 4 MUST continue running.
* File logging MUST continue.
* IPC transmission MAY be skipped.

### If the log file cannot be written:

* The mod SHOULD continue running.
* The failure SHOULD be reported safely.
* The mod MUST NOT enter an infinite retry loop.

### If Sims 4 logging internals change:

* Capture logic SHOULD be isolated.
* Normalization and overlay code SHOULD remain reusable.

---

# 19. Performance Requirements

Performance is a core requirement.

The TS4 mod MUST:

* Avoid blocking the game thread.
* Avoid expensive processing for every log event where possible.
* Avoid unbounded queues.
* Avoid excessive disk flushing.
* Avoid excessive socket operations.
* Avoid creating unnecessary Python objects.
* Avoid generating large amounts of additional Sims 4 logging.

The overlay MUST:

* Avoid rendering unlimited log entries.
* Avoid excessive UI updates.
* Batch or throttle rendering when necessary.
* Remain responsive during large log bursts.

Performance testing MUST include artificial log spam.

---

# 20. Research & Discovery Phase — MANDATORY

Before generating or refactoring implementation code, the agent MUST research current information relevant to the target Sims 4 build and Windows environment. today is year 2026 13 sierpnia

## 20.1 TS4 Python Modding

Research:

* Current Sims 4 Python version. My game version is 1.124
* Current `sims4.log` implementation.
* Current `sims4.log.Logger` behavior.
* Safe ways to intercept or observe log events.
* `sys.excepthook` behavior.
* Existing Sims 4 modding examples.
* Threading limitations.
* Socket limitations.
* File I/O limitations.
* Safe ways to perform non-blocking operations.

The agent MUST NOT assume that undocumented internal APIs remain stable.

## 20.2 Windows Overlay

Research:

* Transparent windows.
* Layered windows.
* Topmost windows.
* Click-through behavior.
* Borderless overlays.
* DPI scaling.
* Multi-monitor behavior.
* Windowed/borderless Sims 4 compatibility.
* DirectX compatibility.

Relevant Win32 styles/APIs MUST be verified rather than copied from outdated examples.

## 20.3 IPC

Research and compare:

* UDP localhost.
* Named Pipes.
* Shared Memory.
* File Polling.

The MVP should remain with UDP unless research identifies a concrete blocker.

## 20.4 File Logging

Research:

* Safe file flushing.
* File rotation.
* JSON Lines performance.
* Encoding.
* File locking.
* Behavior when Sims 4 terminates unexpectedly.

---

# 21. Implementation Rules

The agent MUST follow these rules:

1. Do not implement undocumented Sims 4 behavior based solely on assumptions.
2. Do not introduce unnecessary dependencies.
3. Keep TS4 mod code independent from overlay UI code.
4. Keep the normalized log event schema independent from the transport layer.
5. Keep file logging independent from IPC.
6. Keep overlay filtering independent from mod-side filtering.
7. Never allow the overlay to block Sims 4.
8. Never allow IPC failure to crash Sims 4.
9. Never allow unbounded memory growth.
10. Prefer simple, testable components over premature abstraction.
11. MVP MUST use localhost UDP unless research proves it unsuitable.
12. MVP MUST include local file logging.
13. MVP MUST include normalized log events.
14. MVP MUST include severity filtering.
15. MVP SHOULD include deduplication and rate limiting.
16. Do not implement Recorder, Replay or session playback functionality.

---

# 22. Recommended Project Structure

```text
/
├── ts4_mod/
│   ├── __init__.py
│   ├── capture.py
│   ├── normalize.py
│   ├── filter.py
│   ├── buffer.py
│   ├── ipc.py
│   ├── file_logger.py
│   └── config.py
│
├── overlay/
│   ├── main
│   ├── ipc
│   ├── log_model
│   ├── filters
│   ├── renderer
│   ├── config
│   └── ui
│
├── config/
│   └── config.json
│
├── logs/
│
└── AGENTS.md
```

The exact language/framework for the overlay MUST be selected after evaluating the project's performance and Windows integration requirements.

---

# 23. MVP Definition

The first working version MUST demonstrate:

1. Sims 4 log capture.
2. Normalization into structured events.
3. Local file logging.
4. Localhost UDP transmission.
5. Overlay reception.
6. Real-time display.
7. INFO/WARNING/ERROR/DEBUG categorization.
8. Severity filtering.
9. Basic configuration.
10. Graceful behavior when the overlay is closed.
11. No blocking of Sims 4 due to IPC.
12. Bounded memory usage.

Features such as advanced search, sophisticated deduplication, stack-trace UI and advanced filtering MAY be implemented after the basic pipeline is stable.

---

# 24. Definition of Success

The project is successful when:

* Sims 4 can run normally with the mod installed.
* Relevant log events appear in the overlay with minimal latency.
* Events are normalized into a consistent structure.
* Logs are written to a local file even when the overlay is closed.
* Repeated log spam does not freeze or overwhelm the overlay.
* IPC failure does not destabilize Sims 4.
* The overlay can be configured without recompiling.
* The architecture can survive reasonable Sims 4 updates with changes isolated primarily to the capture layer.
