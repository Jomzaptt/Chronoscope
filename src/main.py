"""Chronoscope — 主入口"""

import sys
import os
import logging

# 确保 src 包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.constants import APP_MUTEX, DATA_DIR
from src.config import ConfigManager
from src.storage import StorageManager
from src.monitor import WindowMonitor
from src.tray import TrayManager
from src.idle_detector import IdleDetector

log = logging.getLogger("Chronoscope")


def _ensure_single_instance():
    """使用 Windows Named Mutex 保证单实例运行"""
    try:
        import win32event
        import win32api
        import winerror

        mutex = win32event.CreateMutex(None, False, APP_MUTEX)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            log.warning("Another instance is already running. Exiting.")
            sys.exit(0)
        return mutex  # 必须保持引用防止 GC 释放
    except ImportError:
        log.warning("pywin32 not available, skipping single-instance check")
        return None


def _setup_logging():
    os.makedirs(DATA_DIR, exist_ok=True)
    log_path = os.path.join(DATA_DIR, "app.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main():
    _setup_logging()
    log.info("Starting Chronoscope")

    mutex = _ensure_single_instance()

    # 初始化模块
    config = ConfigManager()
    config.save()  # 确保配置文件存在

    storage = StorageManager()
    storage.cleanup_old_data(config.data_retention_days)

    monitor = WindowMonitor(storage, config)

    # 初始化空闲检测器
    idle_detector = IdleDetector(
        threshold_seconds=config.idle_threshold,
        on_idle_start=lambda: monitor.pause(),
        on_idle_end=lambda secs: monitor.resume(),
        poll_interval=5.0
    )

    monitor.start()
    idle_detector.start()

    tray = TrayManager(monitor, storage, config, idle_detector)

    log.info("All modules initialized, entering main loop")
    try:
        tray.run()  # 阻塞主线程
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt received")
    finally:
        idle_detector.stop()
        monitor.stop()
        monitor.join(timeout=3)
        storage.flush_daily_summary()
        storage.close()
        log.info("Chronoscope stopped")


if __name__ == "__main__":
    main()
