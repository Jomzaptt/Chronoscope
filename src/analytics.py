"""统计分析引擎"""

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.storage import StorageManager

log = logging.getLogger(__name__)


@dataclass
class DailyReport:
    total_seconds: int = 0
    app_breakdown: list = field(default_factory=list)  # [(name, seconds, pct)]
    most_used_app: str = ""


@dataclass
class WeeklyReport:
    daily_totals: list = field(default_factory=list)  # [(date_str, seconds)]
    avg_daily: int = 0


class AnalyticsEngine:
    def __init__(self, storage: StorageManager):
        self._storage = storage

    def today_usage(self) -> DailyReport:
        rows = self._storage.get_today_summary()
        total = sum(r["total_seconds"] for r in rows)
        breakdown = []
        for r in rows:
            secs = r["total_seconds"]
            pct = (secs / total * 100) if total > 0 else 0
            name = r["display_name"] or r["exe_name"]
            breakdown.append((name, secs, pct))

        most_used = breakdown[0][0] if breakdown else ""
        return DailyReport(
            total_seconds=total,
            app_breakdown=breakdown,
            most_used_app=most_used,
        )

    def weekly_trend(self) -> WeeklyReport:
        today = datetime.now()
        start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        rows = self._storage.get_range_summary(start, end)

        daily_map: dict[str, int] = {}
        for r in rows:
            d = r["date"]
            daily_map[d] = daily_map.get(d, 0) + r["total_seconds"]

        daily_totals = []
        for i in range(7):
            d = (today - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            daily_totals.append((d, daily_map.get(d, 0)))

        vals = [s for _, s in daily_totals]
        avg = sum(vals) // max(len(vals), 1)
        return WeeklyReport(daily_totals=daily_totals, avg_daily=avg)

    def export_today_csv(self, filepath: str) -> None:
        """导出今日使用数据为 CSV 文件

        Raises:
            IOError: 文件写入失败
            PermissionError: 无写入权限
        """
        report = self.today_usage()

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["应用名称", "使用时长（秒）", "占比（%）"])

                for name, secs, pct in report.app_breakdown:
                    writer.writerow([name, secs, f"{pct:.1f}"])

                writer.writerow([])
                writer.writerow(["总计", report.total_seconds, "100.0"])
        except (IOError, PermissionError) as e:
            log.error("Failed to export CSV to %s: %s", filepath, e)
            raise

    def export_weekly_csv(self, filepath: str) -> None:
        """导出本周使用数据为 CSV 文件

        Raises:
            IOError: 文件写入失败
            PermissionError: 无写入权限
        """
        report = self.weekly_trend()

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "使用时长（秒）"])

                for date_str, secs in report.daily_totals:
                    writer.writerow([date_str, secs])

                writer.writerow([])
                writer.writerow(["日均", report.avg_daily, ""])
        except (IOError, PermissionError) as e:
            log.error("Failed to export CSV to %s: %s", filepath, e)
            raise

    def export_range_csv(self, filepath: str, start_date: str, end_date: str) -> None:
        """导出自定义日期范围的使用数据为 CSV 文件

        Args:
            filepath: 输出文件路径
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Raises:
            ValueError: 日期格式无效或 start_date > end_date
            IOError: 文件写入失败
            PermissionError: 无写入权限
        """
        self._validate_date(start_date)
        self._validate_date(end_date)
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        rows = self._storage.get_range_summary(start_date, end_date)

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "应用名称", "使用时长（秒）"])

                total = 0
                for r in rows:
                    secs = r["total_seconds"]
                    total += secs
                    name = r["display_name"] or r["exe_name"]
                    writer.writerow([r["date"], name, secs])

                writer.writerow([])
                writer.writerow(["总计", "", total])
        except (IOError, PermissionError) as e:
            log.error("Failed to export CSV to %s: %s", filepath, e)
            raise

    @staticmethod
    def _validate_date(date_str: str) -> None:
        """验证日期字符串格式为 YYYY-MM-DD"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}, expected YYYY-MM-DD")
