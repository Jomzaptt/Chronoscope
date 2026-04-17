"""JSON 配置管理"""

import json
import os
from src.constants import CONFIG_PATH, DEFAULT_IDLE_THRESHOLD, DEFAULT_DATA_RETENTION_DAYS

_DEFAULTS = {
    "idle_threshold": DEFAULT_IDLE_THRESHOLD,
    "data_retention_days": DEFAULT_DATA_RETENTION_DAYS,
    "record_window_title": False,
    "autostart": False,
    "notify_hourly": True,
    "daily_limit_minutes": 0,  # 0 = 不限制
}


class ConfigManager:
    def __init__(self, path: str = CONFIG_PATH):
        self._path = path
        self._data: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        # 补全缺失的默认值
        for k, v in _DEFAULTS.items():
            if k not in self._data:
                self._data[k] = v

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    @property
    def idle_threshold(self) -> int:
        return self._data["idle_threshold"]

    @property
    def data_retention_days(self) -> int:
        return self._data["data_retention_days"]

    @property
    def record_window_title(self) -> bool:
        return self._data["record_window_title"]

    @property
    def autostart(self) -> bool:
        return self._data["autostart"]

    @property
    def notify_hourly(self) -> bool:
        return self._data["notify_hourly"]

    @property
    def daily_limit_minutes(self) -> int:
        return self._data["daily_limit_minutes"]
