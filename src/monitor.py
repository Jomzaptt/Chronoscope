"""窗口监控模块 — 后台线程，检测前台活跃窗口"""

import threading
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

import psutil

try:
    import win32gui
    import win32process
    import win32api
    import win32con
except ImportError:
    raise SystemExit("pywin32 is required. Install with: pip install pywin32")

from src.constants import (
    DEFAULT_POLL_INTERVAL,
    SLEEP_DETECTION_THRESHOLD,
    DESKTOP_APP_NAME,
    SYSTEM_APP_NAME,
    UNKNOWN_APP_NAME,
    PROGRAM_MANAGER_TITLE,
    SUMMARY_FLUSH_INTERVAL,
)
from src.storage import StorageManager
from src.config import ConfigManager
from src.notifier import send_notification, NotificationType

log = logging.getLogger(__name__)


@dataclass
class AppInfo:
    exe_path: str
    exe_name: str
    window_title: str
    pid: int


class WindowMonitor(threading.Thread):
    def __init__(
        self,
        storage: StorageManager,
        config: ConfigManager,
        on_change: Optional[Callable[[str, int], None]] = None,
    ):
        super().__init__(daemon=True)
        self._storage = storage
        self._config = config
        self._on_change = on_change

        self._running = False
        self._paused = False
        self._poll_interval = DEFAULT_POLL_INTERVAL

        self._current_app_id: Optional[int] = None
        self._current_session_id: Optional[int] = None
        self._current_exe_name: Optional[str] = None
        self._last_poll_time: Optional[datetime] = None
        self._last_flush_time: float = time.monotonic()
        self._last_limit_notify_time: Optional[datetime] = None

    # ── 公共方法 ──

    def set_change_callback(self, callback: Optional[Callable[[str, int], None]]) -> None:
        """设置应用变更回调函数"""
        self._on_change = callback

    def run(self):
        self._running = True
        log.info("WindowMonitor started")
        while self._running:
            if not self._paused:
                self._tick()
            time.sleep(self._poll_interval)
        self._end_current_session()
        log.info("WindowMonitor stopped")

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True
        self._end_current_session()
        log.info("Monitoring paused")

    def resume(self):
        self._paused = False
        log.info("Monitoring resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_app_name(self) -> Optional[str]:
        return self._current_exe_name

    @property
    def current_session_id(self) -> Optional[int]:
        return self._current_session_id

    # ── 内部方法 ──

    def _tick(self):
        now = datetime.now()

        # 检测休眠唤醒
        if self._last_poll_time:
            gap = (now - self._last_poll_time).total_seconds()
            if gap > SLEEP_DETECTION_THRESHOLD:
                log.info("Sleep detected (gap=%.1fs), ending session", gap)
                self._end_current_session()
        self._last_poll_time = now

        # 获取前台应用
        app_info = self._get_foreground_app()
        if app_info is None:
            return

        app_id = self._storage.get_or_create_app(
            app_info.exe_path, app_info.exe_name
        )

        # 应用未变化
        if app_id == self._current_app_id:
            self._maybe_flush_summary()
            return

        # 应用切换
        self._end_current_session()

        title = (
            app_info.window_title if self._config.record_window_title else None
        )
        self._current_session_id = self._storage.start_session(app_id, title)
        self._current_app_id = app_id
        self._current_exe_name = app_info.exe_name

        if self._on_change:
            today_total = self._storage.get_today_total_seconds()
            self._on_change(app_info.exe_name, today_total)

        self._maybe_flush_summary()
        self._check_daily_limit()

    def _get_foreground_app(self) -> Optional[AppInfo]:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)

            # 桌面
            if not title or title == PROGRAM_MANAGER_TITLE:
                return AppInfo(
                    exe_path=DESKTOP_APP_NAME,
                    exe_name=DESKTOP_APP_NAME,
                    window_title=title or "",
                    pid=0,
                )

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None

            proc = psutil.Process(pid)
            return AppInfo(
                exe_path=proc.exe(),
                exe_name=proc.name(),
                window_title=title,
                pid=pid,
            )

        except psutil.NoSuchProcess:
            return None
        except psutil.AccessDenied:
            return AppInfo(
                exe_path=SYSTEM_APP_NAME,
                exe_name=SYSTEM_APP_NAME,
                window_title="",
                pid=0,
            )
        except Exception as e:
            log.debug("Failed to get foreground app: %s", e)
            return None

    def _end_current_session(self):
        if self._current_session_id is not None:
            self._storage.end_session(self._current_session_id)
            self._current_session_id = None
            self._current_app_id = None
            self._current_exe_name = None

    def _maybe_flush_summary(self):
        elapsed = time.monotonic() - self._last_flush_time
        if elapsed >= SUMMARY_FLUSH_INTERVAL:
            self._storage.flush_daily_summary()
            self._last_flush_time = time.monotonic()

    def _check_daily_limit(self):
        """检查是否达到每日使用时间限制"""
        limit_minutes = self._config.daily_limit_minutes
        if limit_minutes <= 0:
            return

        today_total = self._storage.get_today_total_seconds()
        limit_seconds = limit_minutes * 60

        if today_total < limit_seconds:
            return

        # 避免频繁通知：每小时最多通知一次
        now = datetime.now()
        if (
            self._last_limit_notify_time
            and (now - self._last_limit_notify_time).total_seconds() < 3600
        ):
            return

        self._last_limit_notify_time = now
        exceeded = today_total - limit_seconds
        h, m = divmod(int(exceeded), 3600)
        m, _ = divmod(m, 60)
        msg = f"今日已使用超过限制 {limit_minutes} 分钟（超 {h}h {m}m）"
        log.info(msg)
        send_notification("每日使用时间提醒", msg, NotificationType.WARNING)
