"""日期范围选择对话框"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import Optional


def ask_date_range() -> Optional[tuple[str, str]]:
    """弹出日期范围选择对话框。

    Returns:
        (start_date, end_date) 元组，格式为 YYYY-MM-DD；
        用户取消时返回 None。
    """
    result: Optional[tuple[str, str]] = None

    root = tk.Tk()
    root.title("选择日期范围")
    root.geometry("320x200")
    root.resizable(False, False)
    root.configure(bg="#1E1E2E")
    root.grab_set()

    today_str = datetime.now().strftime("%Y-%m-%d")
    week_ago_str = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Dialog.TLabel", font=("Segoe UI", 11),
                     foreground="#CDD6F4", background="#1E1E2E")
    style.configure("Dialog.TButton", font=("Segoe UI", 10))

    ttk.Label(root, text="开始日期:", style="Dialog.TLabel").place(
        x=30, y=25, width=80, height=25
    )
    start_var = tk.StringVar(value=week_ago_str)
    start_entry = ttk.Entry(root, textvariable=start_var, width=14)
    start_entry.place(x=120, y=25, width=160, height=25)

    ttk.Label(root, text="结束日期:", style="Dialog.TLabel").place(
        x=30, y=65, width=80, height=25
    )
    end_var = tk.StringVar(value=today_str)
    end_entry = ttk.Entry(root, textvariable=end_var, width=14)
    end_entry.place(x=120, y=65, width=160, height=25)

    ttk.Label(
        root, text="格式: YYYY-MM-DD", style="Dialog.TLabel"
    ).place(x=120, y=95, width=160, height=20)

    def on_ok():
        nonlocal result
        s = start_var.get().strip()
        e = end_var.get().strip()
        try:
            datetime.strptime(s, "%Y-%m-%d")
            datetime.strptime(e, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("格式错误", "请输入正确的日期格式: YYYY-MM-DD", parent=root)
            return
        if s > e:
            messagebox.showerror("日期错误", "开始日期不能晚于结束日期", parent=root)
            return
        result = (s, e)
        root.destroy()

    def on_cancel():
        root.destroy()

    btn_frame = tk.Frame(root, bg="#1E1E2E")
    btn_frame.place(x=60, y=140, width=200, height=35)
    ttk.Button(btn_frame, text="确定", command=on_ok).pack(side="left", padx=10)
    ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side="left", padx=10)

    root.mainloop()
    return result
