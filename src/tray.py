"""系统托盘管理"""

import os
import threading
import logging
from datetime import datetime
from typing import Optional
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageFont
import pystray

from src.monitor import WindowMonitor
from src.storage import StorageManager
from src.config import ConfigManager
from src.analytics import AnalyticsEngine
from src.stats_window import StatsWindow
from src.settings_window import SettingsWindow
from src.notifier import send_notification, NotificationType
from src.idle_detector import IdleDetector
from src.utils import format_seconds
from src.date_range_dialog import ask_date_range

log = logging.getLogger(__name__)


def _create_icon_image(text: str = "ST") -> "Image.Image":
    """生成简单的托盘图标图像"""
    size = 64
    img = Image.new("RGBA", (size, size), (52, 120, 246, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - 2
    draw.text((x, y), text, fill="white", font=font)
    return img


class TrayManager:
    def __init__(
        self,
        monitor: WindowMonitor,
        storage: StorageManager,
        config: ConfigManager,
        idle_detector: IdleDetector,
    ):
        self._monitor = monitor
        self._storage = storage
        self._config = config
        self._idle_detector = idle_detector

        # 初始化统计和设置窗口
        self._analytics = AnalyticsEngine(storage)
        self._stats_window = StatsWindow(self._analytics)
        self._settings_window = SettingsWindow(config, on_save=self._on_settings_saved)

        self._icon: Optional[pystray.Icon] = None
        self._tooltip = "屏幕时间追踪器"

    def update_tooltip(self, app_name: str, today_total: int):
        text = f"今日: {format_seconds(today_total)} | 当前: {app_name}"
        self._tooltip = text
        if self._icon:
            self._icon.title = text

    def run(self):
        self._icon = pystray.Icon(
            name="ScreenTimeTracker",
            icon=_create_icon_image(),
            title=self._tooltip,
            menu=self._build_menu(),
        )
        # 注册监控回调
        self._monitor.set_change_callback(self.update_tooltip)
        self._icon.run()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("今日统计", self._on_stats_click),
            pystray.MenuItem("本周统计", self._on_weekly_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("导出今日数据", self._on_export_today),
            pystray.MenuItem("导出本周数据", self._on_export_weekly),
            pystray.MenuItem("自定义范围导出", self._on_export_range),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "暂停监控",
                self._on_toggle_pause,
                checked=lambda item: self._monitor.is_paused,
            ),
            pystray.MenuItem("设置", self._on_settings_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def _on_stats_click(self, icon, item):
        self._stats_window.show()

    def _on_weekly_click(self, icon, item):
        """显示本周统计"""
        self._stats_window.show(tab="week")

    def _on_export_today(self, icon, item):
        """导出今日数据为 CSV"""
        def do_export():
            try:
                default_name = f"screen_time_today_{datetime.now().strftime('%Y%m%d')}.csv"
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV 文件", "*.csv")],
                    initialfile=default_name,
                    title="导出今日数据",
                )
                if filepath:
                    self._analytics.export_today_csv(filepath)
                    send_notification(
                        "导出成功",
                        f"今日数据已导出到 {os.path.basename(filepath)}",
                        NotificationType.SUCCESS,
                    )
                    log.info("Today data exported to %s", filepath)
            except Exception as e:
                log.error("Failed to export today data: %s", e)
                messagebox.showerror("导出失败", f"导出失败: {e}")

        threading.Thread(target=do_export, daemon=True).start()

    def _on_export_weekly(self, icon, item):
        """导出本周数据为 CSV"""
        def do_export():
            try:
                default_name = f"screen_time_weekly_{datetime.now().strftime('%Y%m%d')}.csv"
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV 文件", "*.csv")],
                    initialfile=default_name,
                    title="导出本周数据",
                )
                if filepath:
                    self._analytics.export_weekly_csv(filepath)
                    send_notification(
                        "导出成功",
                        f"本周数据已导出到 {os.path.basename(filepath)}",
                        NotificationType.SUCCESS,
                    )
                    log.info("Weekly data exported to %s", filepath)
            except Exception as e:
                log.error("Failed to export weekly data: %s", e)
                messagebox.showerror("导出失败", f"导出失败: {e}")

        threading.Thread(target=do_export, daemon=True).start()

    def _on_export_range(self, icon, item):
        """自定义日期范围导出"""
        def do_export():
            try:
                result = ask_date_range()
                if result is None:
                    return
                start_date, end_date = result

                default_name = f"screen_time_{start_date}_{end_date}.csv"
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV 文件", "*.csv")],
                    initialfile=default_name,
                    title="导出自定义范围数据",
                )
                if filepath:
                    self._analytics.export_range_csv(filepath, start_date, end_date)
                    send_notification(
                        "导出成功",
                        f"数据已导出到 {os.path.basename(filepath)}",
                        NotificationType.SUCCESS,
                    )
                    log.info("Range data exported to %s", filepath)
            except Exception as e:
                log.error("Failed to export range data: %s", e)
                messagebox.showerror("导出失败", f"导出失败: {e}")

        threading.Thread(target=do_export, daemon=True).start()

    def _on_settings_click(self, icon, item):
        self._settings_window.show()

    def _on_settings_saved(self):
        """设置保存后的回调"""
        log.info("Settings updated, applying changes...")
        # 更新空闲检测阈值
        self._idle_detector.threshold = self._config.idle_threshold
        # 通知用户设置已生效
        send_notification("设置已更新", "新设置已生效", NotificationType.SUCCESS)

    def _on_toggle_pause(self, icon, item):
        if self._monitor.is_paused:
            self._monitor.resume()
            icon.icon = _create_icon_image("ST")
        else:
            self._monitor.pause()
            icon.icon = _create_icon_image("||")

    def _on_quit(self, icon, item):
        log.info("User requested quit")
        self._monitor.stop()
        self._storage.flush_daily_summary()
        self._storage.close()
        icon.stop()
