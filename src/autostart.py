"""Windows 注册表开机自启管理"""

import sys
import os
import logging
import winreg

from src.constants import AUTOSTART_REG_KEY, APP_NAME

log = logging.getLogger(__name__)


def _get_exe_path() -> str:
    """获取当前可执行文件路径（兼容 PyInstaller 打包）"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def enable_autostart():
    exe = _get_exe_path()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        log.info("Autostart enabled: %s", exe)
    except OSError as e:
        log.error("Failed to enable autostart: %s", e)


def disable_autostart():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
            log.info("Autostart disabled")
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
    except OSError as e:
        log.error("Failed to disable autostart: %s", e)


def set_autostart(enabled: bool):
    if enabled:
        enable_autostart()
    else:
        disable_autostart()
