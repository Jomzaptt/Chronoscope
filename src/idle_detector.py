"""用户空闲检测 — 通过 GetLastInputInfo 检测键盘/鼠标空闲"""

import ctypes
import ctypes.wintypes
import logging
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]


def get_idle_seconds() -> float:
    """返回用户空闲秒数（距最后一次键盘/鼠标输入）"""
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return 0.0
        tick_count = ctypes.windll.kernel32.GetTickCount()
        elapsed_ms = tick_count - lii.dwTime
        return max(elapsed_ms / 1000.0, 0.0)
    except Exception as e:
        log.debug("Failed to get idle time: %s", e)
        return 0.0


class IdleDetector:
    """空闲检测器 — 定期检查用户空闲状态并触发回调"""

    def __init__(
        self,
        threshold_seconds: int = 300,
        on_idle_start: Callable[[], None] | None = None,
        on_idle_end: Callable[[int], None] | None = None,
        poll_interval: float = 5.0,
    ):
        """
        Args:
            threshold_seconds: 空闲阈值（秒）
            on_idle_start: 空闲开始回调
            on_idle_end: 空闲结束回调，参数为空闲持续秒数
            poll_interval: 轮询间隔（秒）

        Raises:
            ValueError: threshold_seconds 不是正整数
        """
        if not isinstance(threshold_seconds, int) or threshold_seconds <= 0:
            raise ValueError(f"threshold_seconds must be a positive integer, got {threshold_seconds}")

        self._threshold = threshold_seconds
        self._on_idle_start = on_idle_start
        self._on_idle_end = on_idle_end
        self._poll_interval = poll_interval

        self._is_idle = False
        self._idle_start_time: float | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    @property
    def threshold(self) -> int:
        return self._threshold

    @threshold.setter
    def threshold(self, value: int):
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"threshold must be a positive integer, got {value}")
        if value > 86400:  # 24 hours
            log.warning("Threshold exceeds 24 hours (%ds), this may not be intended", value)
        self._threshold = value

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    def start(self):
        """启动空闲检测"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        log.info("IdleDetector started (threshold=%ds)", self._threshold)

    def stop(self):
        """停止空闲检测"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        log.info("IdleDetector stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            idle_secs = get_idle_seconds()

            with self._lock:
                if idle_secs >= self._threshold and not self._is_idle:
                    # 进入空闲状态
                    self._is_idle = True
                    self._idle_start_time = time.time()
                    log.debug("User idle started")
                    if self._on_idle_start:
                        try:
                            self._on_idle_start()
                        except Exception as e:
                            log.error("on_idle_start callback failed: %s", e)

                elif idle_secs < self._threshold and self._is_idle:
                    # 从空闲状态恢复
                    self._is_idle = False
                    idle_duration = int(time.time() - self._idle_start_time) if self._idle_start_time else 0
                    log.debug("User idle ended (duration=%ds)", idle_duration)
                    if self._on_idle_end:
                        try:
                            self._on_idle_end(idle_duration)
                        except Exception as e:
                            log.error("on_idle_end callback failed: %s", e)
                    self._idle_start_time = None

            time.sleep(self._poll_interval)
