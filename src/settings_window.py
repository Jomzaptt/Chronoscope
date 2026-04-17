"""tkinter 设置窗口 — 用户配置界面"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable

from src.config import ConfigManager
from src import autostart


class SettingsWindow:
    def __init__(self, config: ConfigManager, on_save: Callable | None = None):
        self._config = config
        self._on_save = on_save
        self._root: tk.Tk | None = None

    def show(self):
        if self._root and self._root.winfo_exists():
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
            return

        self._root = tk.Tk()
        self._root.title("设置")
        self._root.geometry("480x420")
        self._root.configure(bg="#1E1E2E")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_styles()
        self._build_ui()
        self._load_settings()
        self._root.mainloop()

    def _setup_styles(self):
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                       foreground="#CDD6F4", background="#1E1E2E")
        style.configure("Setting.TLabel", font=("Segoe UI", 11),
                       foreground="#CDD6F4", background="#1E1E2E")
        style.configure("Value.TLabel", font=("Segoe UI", 10),
                       foreground="#A6ADC8", background="#1E1E2E")
        style.configure("TCheckbutton", font=("Segoe UI", 11),
                       foreground="#CDD6F4", background="#1E1E2E")

    def _build_ui(self):
        # 标题
        header = tk.Frame(self._root, bg="#1E1E2E")
        header.pack(fill="x", padx=20, pady=(15, 10))
        ttk.Label(header, text="设置", style="Title.TLabel").pack(side="left")

        # 滚动区域
        canvas = tk.Canvas(self._root, bg="#1E1E2E", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._root, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#1E1E2E")

        scroll_frame.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")

        # 空闲阈值
        idle_frame = self._create_setting_row(scroll_frame, "空闲阈值（秒）")
        self._idle_var = tk.IntVar(value=300)
        self._idle_scale = ttk.Scale(
            idle_frame, from_=60, to=900, variable=self._idle_var,
            orient="horizontal", length=250, command=self._on_idle_change
        )
        self._idle_scale.pack(side="left", padx=(0, 10))
        self._idle_label = ttk.Label(idle_frame, text="300秒", style="Value.TLabel")
        self._idle_label.pack(side="left")

        # 数据保留天数
        retention_frame = self._create_setting_row(scroll_frame, "数据保留天数")
        self._retention_var = tk.IntVar(value=90)
        self._retention_scale = ttk.Scale(
            retention_frame, from_=7, to=365, variable=self._retention_var,
            orient="horizontal", length=250, command=self._on_retention_change
        )
        self._retention_scale.pack(side="left", padx=(0, 10))
        self._retention_label = ttk.Label(retention_frame, text="90天", style="Value.TLabel")
        self._retention_label.pack(side="left")

        # 每日时间限制
        limit_frame = self._create_setting_row(scroll_frame, "每日时间限制（分钟）")
        self._limit_var = tk.IntVar(value=0)
        self._limit_scale = ttk.Scale(
            limit_frame, from_=0, to=480, variable=self._limit_var,
            orient="horizontal", length=250, command=self._on_limit_change
        )
        self._limit_scale.pack(side="left", padx=(0, 10))
        self._limit_label = ttk.Label(limit_frame, text="不限制", style="Value.TLabel")
        self._limit_label.pack(side="left")

        # 记录窗口标题
        title_frame = self._create_setting_row(scroll_frame, "")
        self._record_title_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            title_frame, text="记录窗口标题（可能包含敏感信息）",
            variable=self._record_title_var, style="TCheckbutton"
        ).pack(side="left")

        # 开机自启
        autostart_frame = self._create_setting_row(scroll_frame, "")
        self._autostart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            autostart_frame, text="开机自启动",
            variable=self._autostart_var, style="TCheckbutton",
            command=self._on_autostart_change
        ).pack(side="left")

        # 每小时通知
        notify_frame = self._create_setting_row(scroll_frame, "")
        self._notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            notify_frame, text="每小时发送使用统计通知",
            variable=self._notify_var, style="TCheckbutton"
        ).pack(side="left")

        # 按钮
        button_frame = tk.Frame(self._root, bg="#1E1E2E")
        button_frame.pack(fill="x", padx=20, pady=(10, 15))

        ttk.Button(
            button_frame, text="保存", command=self._on_save_click
        ).pack(side="right", padx=(5, 0))

        ttk.Button(
            button_frame, text="取消", command=self._on_close
        ).pack(side="right")

    def _create_setting_row(self, parent: tk.Widget, label: str) -> tk.Frame:
        """创建设置行"""
        frame = tk.Frame(parent, bg="#1E1E2E")
        frame.pack(fill="x", pady=8)

        if label:
            ttk.Label(frame, text=label, style="Setting.TLabel").pack(anchor="w")

        control_frame = tk.Frame(frame, bg="#1E1E2E")
        control_frame.pack(fill="x", pady=(5, 0))

        return control_frame

    def _load_settings(self):
        """加载当前配置"""
        self._idle_var.set(self._config.idle_threshold)
        self._retention_var.set(self._config.data_retention_days)
        self._record_title_var.set(self._config.record_window_title)
        self._autostart_var.set(autostart.is_autostart_enabled())
        self._notify_var.set(self._config.notify_hourly)
        self._limit_var.set(self._config.daily_limit_minutes)

        self._on_idle_change(self._config.idle_threshold)
        self._on_retention_change(self._config.data_retention_days)
        self._on_limit_change(self._config.daily_limit_minutes)

    def _on_idle_change(self, value: str | float) -> None:
        secs = int(float(value))
        mins = secs // 60
        if mins > 0:
            self._idle_label.configure(text=f"{mins}分钟")
        else:
            self._idle_label.configure(text=f"{secs}秒")

    def _on_retention_change(self, value: str | float) -> None:
        days = int(float(value))
        self._retention_label.configure(text=f"{days}天")

    def _on_limit_change(self, value: str | float) -> None:
        mins = int(float(value))
        if mins == 0:
            self._limit_label.configure(text="不限制")
        else:
            hours = mins // 60
            remain_mins = mins % 60
            if hours > 0:
                self._limit_label.configure(text=f"{hours}小时{remain_mins}分钟")
            else:
                self._limit_label.configure(text=f"{mins}分钟")

    def _on_autostart_change(self):
        """开机自启变更时立即应用"""
        enabled = self._autostart_var.get()
        autostart.set_autostart(enabled)

    def _on_save_click(self):
        """保存设置"""
        try:
            self._config.set("idle_threshold", self._idle_var.get())
            self._config.set("data_retention_days", self._retention_var.get())
            self._config.set("record_window_title", self._record_title_var.get())
            self._config.set("autostart", self._autostart_var.get())
            self._config.set("notify_hourly", self._notify_var.get())
            self._config.set("daily_limit_minutes", self._limit_var.get())

            messagebox.showinfo("成功", "设置已保存", parent=self._root)

            if self._on_save:
                self._on_save()

            self._on_close()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}", parent=self._root)

    def _on_close(self):
        if self._root:
            self._root.destroy()
            self._root = None
