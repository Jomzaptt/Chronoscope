"""常量定义"""

import os

APP_NAME = "ScreenTimeTracker"
APP_MUTEX = "Global\\ScreenTimeTrackerMutex"

# 数据目录
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), APP_NAME)
DB_PATH = os.path.join(DATA_DIR, "screentime.db")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
ICON_CACHE_DIR = os.path.join(DATA_DIR, "icons")

# 监控默认值
DEFAULT_POLL_INTERVAL = 1.0  # 秒
DEFAULT_IDLE_THRESHOLD = 300  # 5 分钟
DEFAULT_DATA_RETENTION_DAYS = 90
SLEEP_DETECTION_THRESHOLD = 30  # 秒，超过此值判定为休眠

# 汇总刷新间隔
SUMMARY_FLUSH_INTERVAL = 60  # 秒

# 特殊应用名
DESKTOP_APP_NAME = "Desktop"
LOCK_SCREEN_APP_NAME = "LockScreen"
SYSTEM_APP_NAME = "System"
UNKNOWN_APP_NAME = "Unknown"
PROGRAM_MANAGER_TITLE = "Program Manager"

# 注册表
AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
