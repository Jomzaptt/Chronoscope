# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Screen Time Tracker is a Windows desktop application that monitors and records user's application usage time. It runs in the system tray with background window monitoring and SQLite storage.

## Dependencies

Required Python packages:
- `pywin32` (win32gui, win32process, win32api, win32con) - Window monitoring
- `psutil` - Process information
- `Pillow` (PIL) - Tray icon generation
- `pystray` - System tray management
- `tkinter` - GUI (standard library)

Install dependencies:
```bash
pip install pywin32 psutil Pillow pystray
```

## Running the Application

```bash
# Run from project root
python src/main.py

# Or run as module
python -m src.main
```

The application creates a system tray icon. Right-click the tray icon to access:
- Today's statistics
- Weekly statistics
- Export data to CSV
- Settings
- Pause/resume monitoring

## Architecture

### Core Data Flow

```
WindowMonitor (background thread)
    ↓ polls foreground window every 1s
    ↓ creates/updates sessions
StorageManager (SQLite with WAL mode)
    ↓ aggregates to daily_summary
AnalyticsEngine
    ↓ queries for reports
UI Windows (tkinter)
    ↓ displays statistics
```

### Threading Model

**Main Thread**:
- Runs tkinter mainloop for UI windows
- Runs pystray event loop for system tray

**WindowMonitor Thread** (daemon):
- Polls foreground window every 1 second
- Writes to SQLite via thread-safe StorageManager
- Detects system sleep/wake (gap > 30s between polls)
- Ends current session on pause/stop

**Notification Threads**:
- ThreadPoolExecutor with max_workers=2
- Spawns PowerShell processes for Windows Toast notifications
- Non-blocking, handles failures gracefully

**File Dialog Threads**:
- Spawned for CSV export dialogs
- Prevents tray icon freezing

### Database Schema (SQLite)

**apps table**:
- `exe_path` (UNIQUE): Full executable path
- `exe_name`: Executable filename
- `display_name`: User-friendly name (can be customized)
- `category`: Application category
- `is_hidden`: Whether to hide from statistics

**sessions table**:
- Records individual usage sessions
- Each session = one continuous app usage
- Linked to `apps` via `app_id`
- Includes `window_title` (optional, configurable)
- `is_idle` flag for idle sessions

**daily_summary table**:
- Pre-aggregated daily totals per app
- Updated every 60s by StorageManager
- Primary key: `(date, app_id)`

### Key Design Patterns

**Single Instance**: Uses Windows Named Mutex (`Global\\ScreenTimeTrackerMutex`) to prevent multiple instances.

**Thread-Safe Storage**: StorageManager uses `threading.Lock()` for all SQLite operations. SQLite is configured with WAL mode for better concurrency.

**Callback Pattern**: 
- WindowMonitor accepts `on_change` callback
- IdleDetector accepts `on_idle_start` and `on_idle_end` callbacks
- Decouples monitoring logic from UI updates

**Encapsulation**: 
- Private attributes prefixed with `_`
- Public methods for external access (e.g., `set_change_callback()`)
- Property decorators for read-only state

### Configuration

Config stored in JSON at `%LOCALAPPDATA%\ScreenTimeTracker\config.json`:
- `idle_threshold`: Seconds before considering user idle (default: 300)
- `data_retention_days`: Days to keep data (default: 90)
- `record_window_title`: Whether to store window titles (privacy concern)
- `autostart`: Windows auto-start on login
- `notify_hourly`: Send hourly usage notifications
- `daily_limit_minutes`: Daily usage limit (0 = unlimited)

### Data Storage Location

All data stored in `%LOCALAPPDATA%\ScreenTimeTracker\`:
- `screentime.db` - SQLite database
- `config.json` - User configuration
- `app.log` - Application logs
- `icons/` - Cached application icons (future use)

### Window Monitoring Logic

1. **Foreground Detection**: Uses `win32gui.GetForegroundWindow()` to get active window HWND
2. **Process Info**: Gets PID via `win32process.GetWindowThreadProcessId()`
3. **Special Cases**:
   - No foreground window → "Desktop"
   - Lock screen → "LockScreen"
   - Unknown process → "Unknown"
4. **Session Management**:
   - App switch ends current session, starts new one
   - Sleep detection (gap > 30s) ends session
   - Pause monitoring ends session
   - App exit ends session

### Idle Detection

`IdleDetector` class uses Windows `GetLastInputInfo()` API to detect keyboard/mouse inactivity:
- Polls every 5 seconds by default
- Calls `on_idle_start` when idle exceeds threshold
- Calls `on_idle_end(idle_duration)` when activity resumes
- Thread-safe state transitions with lock

**Note**: IdleDetector is implemented but not yet integrated into main application flow.

### CSV Export Format

**Today's export**: `screen_time_today_YYYYMMDD.csv`
```
应用名称,使用时长（秒）,占比（%）
Chrome,3600,40.5
VSCode,2700,30.3
...

总计,8900,100.0
```

**Weekly export**: `screen_time_weekly_YYYYMMDD.csv`
```
日期,使用时长（秒）
2024-01-10,7200
2024-01-11,8900
...

日均,8050,
```

Uses `utf-8-sig` encoding for Excel compatibility.

### Security Considerations

**PowerShell Injection Prevention**: Notification system escapes XML special characters before interpolating into PowerShell script.

**Path Validation**: File dialogs handle path selection; no arbitrary path acceptance.

**Credential Safety**: No credentials stored. Config contains only user preferences.

**Privacy**: `record_window_title` disabled by default to avoid storing potentially sensitive window titles.

## Known Limitations

1. **Windows Only**: Uses Windows-specific APIs (win32gui, GetLastInputInfo, registry for autostart)
2. **No Tests**: Test directory exists but empty. Unit tests need to be written.
3. **IdleDetector Not Integrated**: Module exists but not connected to main flow
4. **No Custom Date Range**: CSV export only supports today/week, not arbitrary ranges
5. **Single-User**: No multi-user support (single database)

## Development Workflow

### Adding New Features

1. **Storage changes**: Modify `StorageManager.init_db()` and add migration logic if needed
2. **Config additions**: Add to `_DEFAULTS` in `ConfigManager` and update properties
3. **UI windows**: Create new tkinter window class, integrate via `TrayManager`
4. **Background tasks**: Use threading with daemon=True, coordinate via callbacks

### Code Style

- Type annotations on all function signatures
- Private attributes prefixed with `_`
- Thread-safe operations use locks
- Logging via `logging.getLogger(__name__)`
- Error handling at boundaries (file I/O, external APIs)
- Early returns over deep nesting

### Debugging

Logs written to `%LOCALAPPDATA%\ScreenTimeTracker\app.log`:
```
2024-01-10 10:15:30 [INFO] WindowMonitor started
2024-01-10 10:15:31 [DEBUG] App changed: Chrome → VSCode
2024-01-10 10:20:45 [INFO] Monitoring paused
```

Set logging level to DEBUG for verbose output:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Future Improvements

From COMPLETION_REPORT.md:
1. Add unit tests (target 80%+ coverage)
2. Integrate IdleDetector into main application
3. Add daily limit warning notifications
4. Add more visualization (pie charts, trend lines)
5. Add internationalization support
