"""tkinter 统计窗口 — 条形图、饼图、趋势线展示应用使用时长"""

import math
import tkinter as tk
from tkinter import ttk

from src.analytics import AnalyticsEngine
from src.utils import format_seconds


# 调色板
_COLORS = [
    "#3478F6", "#FF6B35", "#2ECC71", "#E74C3C", "#9B59B6",
    "#1ABC9C", "#F39C12", "#E91E63", "#00BCD4", "#8BC34A",
]


class StatsWindow:
    def __init__(self, analytics: AnalyticsEngine):
        self._analytics = analytics
        self._root: tk.Tk | None = None

    def show(self, tab: str = "today"):
        if self._root and self._root.winfo_exists():
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
            self._tab_var.set(tab)
            self._refresh()
            return

        self._root = tk.Tk()
        self._root.title("屏幕时间统计")
        self._root.geometry("700x600")
        self._root.configure(bg="#1E1E2E")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_styles()
        self._build_ui()
        self._tab_var.set(tab)
        self._refresh()
        self._root.mainloop()

    def _setup_styles(self):
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"),
                         foreground="#CDD6F4", background="#1E1E2E")
        style.configure("Total.TLabel", font=("Segoe UI", 14),
                         foreground="#A6ADC8", background="#1E1E2E")
        style.configure("App.TLabel", font=("Segoe UI", 11),
                         foreground="#CDD6F4", background="#1E1E2E")
        style.configure("Time.TLabel", font=("Segoe UI", 10),
                         foreground="#A6ADC8", background="#1E1E2E")
        style.configure("Tab.TFrame", background="#1E1E2E")

    def _build_ui(self):
        # 标题
        header = tk.Frame(self._root, bg="#1E1E2E")
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="屏幕时间统计", style="Title.TLabel").pack(
            side="left"
        )

        # 标签切换
        tab_frame = tk.Frame(self._root, bg="#1E1E2E")
        tab_frame.pack(fill="x", padx=20, pady=(0, 5))

        self._tab_var = tk.StringVar(value="today")
        for text, val in [("今日", "today"), ("本周", "week")]:
            rb = tk.Radiobutton(
                tab_frame, text=text, variable=self._tab_var, value=val,
                font=("Segoe UI", 10), fg="#CDD6F4", bg="#1E1E2E",
                selectcolor="#313244", activebackground="#1E1E2E",
                activeforeground="#CDD6F4", indicatoron=0,
                padx=12, pady=4, relief="flat", bd=0,
                command=self._refresh,
            )
            rb.pack(side="left", padx=(0, 5))

        # 总计
        self._total_label = ttk.Label(
            self._root, text="总计: 0m", style="Total.TLabel"
        )
        self._total_label.pack(padx=20, anchor="w")

        # 条形图区域（可滚动）
        container = tk.Frame(self._root, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=20, pady=10)

        self._canvas = tk.Canvas(
            container, bg="#1E1E2E", highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self._canvas.yview
        )
        self._scroll_frame = tk.Frame(self._canvas, bg="#1E1E2E")

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")
            ),
        )
        self._canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮
        self._canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-e.delta // 120, "units"),
        )

    def _refresh(self):
        # 清除旧内容
        for w in self._scroll_frame.winfo_children():
            w.destroy()

        tab = self._tab_var.get()
        if tab == "today":
            report = self._analytics.today_usage()
            self._total_label.configure(
                text=f"总计: {format_seconds(report.total_seconds)}"
            )
            self._draw_pie(report.app_breakdown)
            self._draw_bars(report.app_breakdown)
        else:
            weekly = self._analytics.weekly_trend()
            self._total_label.configure(
                text=f"日均: {format_seconds(weekly.avg_daily)}"
            )
            self._draw_weekly(weekly.daily_totals)
            self._draw_trend_line(weekly.daily_totals)

    def _draw_pie(self, breakdown: list):
        """绘制饼图：[(name, seconds, pct), ...]"""
        if not breakdown or breakdown[0][1] == 0:
            return

        total = sum(s for _, s, _ in breakdown)
        top = breakdown[:6]
        other_secs = sum(s for _, s, _ in breakdown[6:])
        if other_secs > 0:
            top.append(("其他", other_secs, other_secs / total * 100))

        size = 180
        cx, cy = size // 2, size // 2
        radius = 70

        chart = tk.Canvas(
            self._scroll_frame, width=size, height=size, bg="#1E1E2E",
            highlightthickness=0,
        )
        chart.pack(pady=(10, 5))

        start_angle = 90
        for i, (name, secs, pct) in enumerate(top):
            extent = pct / 100 * 360
            color = _COLORS[i % len(_COLORS)]
            chart.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=start_angle, extent=extent,
                fill=color, outline="#1E1E2E", width=2,
            )
            # 标签
            mid_angle = math.radians(start_angle + extent / 2)
            lx = cx + (radius + 18) * math.cos(mid_angle)
            ly = cy - (radius + 18) * math.sin(mid_angle)
            if pct >= 5:
                chart.create_text(
                    lx, ly, text=f"{name}\n{pct:.0f}%",
                    fill="#CDD6F4", font=("Segoe UI", 8),
                )
            start_angle += extent

    def _draw_bars(self, breakdown: list):
        """绘制水平条形图：[(name, seconds, pct), ...]"""
        if not breakdown:
            ttk.Label(
                self._scroll_frame, text="暂无数据", style="Time.TLabel"
            ).pack(pady=20)
            return

        max_secs = breakdown[0][1] if breakdown else 1
        bar_width = 420

        for i, (name, secs, pct) in enumerate(breakdown[:15]):
            row = tk.Frame(self._scroll_frame, bg="#1E1E2E")
            row.pack(fill="x", pady=3)

            # 应用名
            name_label = tk.Label(
                row, text=name, font=("Segoe UI", 10), fg="#CDD6F4",
                bg="#1E1E2E", width=16, anchor="w",
            )
            name_label.pack(side="left")

            # 条形
            color = _COLORS[i % len(_COLORS)]
            ratio = secs / max_secs if max_secs > 0 else 0
            w = max(int(bar_width * ratio), 4)

            bar_canvas = tk.Canvas(
                row, width=bar_width, height=20, bg="#1E1E2E",
                highlightthickness=0,
            )
            bar_canvas.pack(side="left", padx=(5, 5))
            bar_canvas.create_rectangle(
                0, 2, w, 18, fill=color, outline="", width=0
            )

            # 时长
            time_label = tk.Label(
                row, text=f"{format_seconds(secs)}  {pct:.0f}%",
                font=("Segoe UI", 9), fg="#A6ADC8", bg="#1E1E2E",
                anchor="w",
            )
            time_label.pack(side="left")

    def _draw_weekly(self, daily_totals: list):
        """绘制每日柱状图：[(date_str, seconds), ...]"""
        if not daily_totals:
            ttk.Label(
                self._scroll_frame, text="暂无数据", style="Time.TLabel"
            ).pack(pady=20)
            return

        max_secs = max(s for _, s in daily_totals) or 1
        bar_height = 180

        chart = tk.Canvas(
            self._scroll_frame, width=640, height=250, bg="#1E1E2E",
            highlightthickness=0,
        )
        chart.pack(pady=10)

        bar_w = 50
        gap = 30
        x_start = 40

        for i, (date_str, secs) in enumerate(daily_totals):
            x = x_start + i * (bar_w + gap)
            ratio = secs / max_secs if max_secs > 0 else 0
            h = max(int(bar_height * ratio), 2)
            y_top = 200 - h

            color = _COLORS[i % len(_COLORS)]
            chart.create_rectangle(
                x, y_top, x + bar_w, 200, fill=color, outline=""
            )

            # 日期标签 (MM-DD)
            short_date = date_str[5:]  # "YYYY-MM-DD" → "MM-DD"
            chart.create_text(
                x + bar_w // 2, 215, text=short_date,
                fill="#A6ADC8", font=("Segoe UI", 9),
            )

            # 时长标签
            if secs > 0:
                chart.create_text(
                    x + bar_w // 2, y_top - 10,
                    text=format_seconds(secs),
                    fill="#CDD6F4", font=("Segoe UI", 8),
                )

    def _draw_trend_line(self, daily_totals: list):
        """绘制周趋势线：[(date_str, seconds), ...]"""
        if not daily_totals:
            return

        vals = [s for _, s in daily_totals]
        max_val = max(vals) or 1

        chart = tk.Canvas(
            self._scroll_frame, width=640, height=150, bg="#1E1E2E",
            highlightthickness=0,
        )
        chart.pack(pady=(0, 10))

        margin_x, margin_top, margin_bottom = 40, 20, 30
        plot_w = 640 - 2 * margin_x
        plot_h = 150 - margin_top - margin_bottom

        # Y 轴参考线
        for i in range(5):
            y = margin_top + int(plot_h * i / 4)
            chart.create_line(
                margin_x, y, 640 - margin_x, y,
                fill="#313244", dash=(2, 4),
            )
            val = int(max_val * (1 - i / 4))
            chart.create_text(
                margin_x - 5, y, text=format_seconds(val),
                fill="#585B70", font=("Segoe UI", 7), anchor="e",
            )

        # 数据点
        points = []
        for i, secs in enumerate(vals):
            x = margin_x + int(plot_w * i / max(len(vals) - 1, 1))
            ratio = secs / max_val if max_val > 0 else 0
            y = margin_top + plot_h - int(plot_h * ratio)
            points.append((x, y))

        # 填充区域
        fill_coords = [margin_x, margin_top + plot_h]
        fill_coords.extend([coord for pt in points for coord in pt])
        fill_coords.extend([points[-1][0], margin_top + plot_h])
        chart.create_polygon(fill_coords, fill="#3478F6", outline="", stipple="gray25")

        # 趋势线
        line_coords = [coord for pt in points for coord in pt]
        if len(line_coords) >= 4:
            chart.create_line(line_coords, fill="#3478F6", width=2, smooth=True)

        # 数据点标记
        for i, (x, y) in enumerate(points):
            chart.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#3478F6", outline="white", width=1)

    def _on_close(self):
        if self._root:
            self._root.destroy()
            self._root = None
