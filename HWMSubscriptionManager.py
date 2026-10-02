# Homework Manager
# Copyright (C) 2026 AUimpostor <auimpostor@outlook.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import json
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from HWMRuntime import (
    close_shutdown_event,
    configure_tk_scaling,
    create_shutdown_event,
    enable_high_dpi,
    enable_touch_keyboard,
    set_window_icon,
    wait_for_shutdown,
)
from HWMSubscriptionService import (
    DEFAULTS,
    check_smtp_connection,
    load_settings,
    save_settings,
    send_push,
)


class SubscriptionManager:
    def __init__(self, root):
        self.root = root
        enable_touch_keyboard(root)
        set_window_icon(root, __file__)
        self.root.title("Homework Manager 推送管理器")
        self.root.geometry("1060x760")
        self.root.minsize(880, 620)
        self.settings = load_settings()
        self.status = tk.StringVar(value="就绪")
        self.smtp_status = tk.StringVar(value="正在检测 SMTP 连接…")
        self._smtp_check_generation = 0
        self.vars = {}
        self._build()
        self._populate()
        self.shutdown_event = create_shutdown_event("subscription_manager")
        if self.shutdown_event is not None:
            threading.Thread(target=self._wait_for_shutdown, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(150, self._check_smtp_connection)



    def _close(self):
        close_shutdown_event(self.shutdown_event)
        self.root.destroy()

    def _wait_for_shutdown(self):
        if wait_for_shutdown(self.shutdown_event):
            self.root.after(0, self._close)

    def _build(self):
        configure_tk_scaling(self.root)
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=3, uniform="cols")
        frame.columnconfigure(1, weight=2, uniform="cols")
        frame.rowconfigure(2, weight=1)
        smtp = ttk.LabelFrame(frame, text="推送源（SMTP）", padding=10)
        smtp.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for column in range(3):
            smtp.columnconfigure(column, weight=1, uniform="smtp-fields")
        fields = (("host", "SMTP 服务器"), ("port", "端口"), ("email", "发件邮箱"), ("username", "SMTP 用户名"), ("password", "SMTP 密码 / 授权码"))
        for i, (key, label) in enumerate(fields):
            col = i % 3
            row = (i // 3) * 2
            ttk.Label(smtp, text=label).grid(row=row, column=col, sticky="w", padx=(0, 10), pady=(0, 2))
            var = tk.StringVar(); self.vars[key] = var
            ttk.Entry(smtp, textvariable=var, show="•" if key == "password" else "").grid(row=row+1, column=col, sticky="ew", padx=(0, 10), pady=(0, 7))
        self.security = tk.StringVar(value="SSL")
        ttk.Label(smtp, text="加密方式").grid(row=2, column=2, sticky="w", padx=(0, 10), pady=(0, 2))
        ttk.Combobox(smtp, textvariable=self.security, state="readonly", values=("SSL", "STARTTLS", "无加密")).grid(row=3, column=2, sticky="ew", padx=(0, 10), pady=(0, 7))
        self.smtp_status_label = ttk.Label(smtp, textvariable=self.smtp_status, foreground="#777777")
        self.smtp_status_label.grid(row=4, column=0, sticky="w", pady=(2, 0))
        ttk.Button(smtp, text="刷新 SMTP 状态", command=self._check_smtp_connection).grid(row=4, column=1, sticky="e", padx=8, pady=(2, 0))
        ttk.Button(smtp, text="保存 SMTP 设置", command=self._save_smtp).grid(row=4, column=2, sticky="e", pady=(2, 0))

        accounts = ttk.LabelFrame(frame, text="订阅账户", padding=10)
        accounts.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        accounts.columnconfigure(0, weight=1); accounts.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(accounts, height=10, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        scrollbar = ttk.Scrollbar(accounts, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=(0, 8))
        self.listbox.configure(yscrollcommand=scrollbar.set)
        actions = ttk.Frame(accounts); actions.grid(row=1, column=0, sticky="ew")
        ttk.Button(actions, text="添加账户...", command=self._add_account).pack(side="left")
        ttk.Button(actions, text="编辑...", command=self._edit_account).pack(side="left", padx=8)
        ttk.Button(actions, text="删除", command=self._delete).pack(side="left")

        right = ttk.Frame(frame); right.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right.columnconfigure(0, weight=1); right.rowconfigure(1, weight=1)
        fmt = ttk.LabelFrame(right, text="推送格式", padding=10)
        fmt.grid(row=1, column=0, sticky="nsew")
        fmt.columnconfigure(1, weight=1); fmt.rowconfigure(2, weight=1)
        ttk.Label(fmt, text="标题").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.title_text = tk.Text(fmt, height=2, wrap="word"); self.title_text.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(fmt, text="正文").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.body_text = tk.Text(fmt, height=10, wrap="word"); self.body_text.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=4)
        ttk.Label(fmt, text="%date% 当前日期；%time% 当前时间\n%n% 昵称；%t% 称呼\n%s% 学校；%c% 班级\n%hw% 作业内容\n正文支持 HTML 和换行", justify="left", wraplength=300).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))
        ttk.Button(fmt, text="保存推送格式", command=self._save_format).grid(row=4, column=1, sticky="e", pady=(8, 0))

        schedule = ttk.LabelFrame(right, text="定时推送", padding=10)
        schedule.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.enabled = tk.BooleanVar()
        ttk.Checkbutton(schedule, text="每日推送（仅 HWM 运行时）", variable=self.enabled).grid(row=0, column=0, columnspan=3, sticky="w")
        self.time_var = tk.StringVar(value="18:00")
        ttk.Label(schedule, text="时间（24 小时制）").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(schedule, textvariable=self.time_var, width=10).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Button(schedule, text="保存定时设置", command=self._save_schedule).grid(row=1, column=2, padx=(8, 0))
        bottom = ttk.Frame(frame)
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        ttk.Button(bottom, text="推送所有订阅账户...", command=self._push).pack(side="right")

    def _populate(self):
        s = self.settings["source"]
        for key, var in self.vars.items(): var.set(str(s.get(key, "")))
        self.security.set(s.get("security", "SSL"))
        self.enabled.set(bool(self.settings.get("schedule_enabled")))
        self.time_var.set(self.settings.get("schedule_time", "18:00"))
        self.title_text.delete("1.0", tk.END)
        self.title_text.insert("1.0", self.settings.get("title_template", DEFAULTS["title_template"]))
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert("1.0", self.settings.get("body_template", DEFAULTS["body_template"]))
        self.listbox.delete(0, tk.END)
        for p in self.settings.get("subscribers", []):
            self.listbox.insert(tk.END, "{}  |  {}  |  {}".format(p.get("nickname", ""), p.get("salutation", ""), p.get("email", "")))

    def _edit_account(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showinfo("编辑订阅账户", "请先选中列表中的账户。", parent=self.root)
            return
        self._open_account_dialog(selected[0])

    def _add_account(self):
        self._open_account_dialog()

    def _open_account_dialog(self, account_index=None):
        editing = account_index is not None
        original = dict(self.settings["subscribers"][account_index]) if editing else None
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("编辑订阅账户" if editing else "添加订阅账户")
        dialog.transient(self.root); dialog.grab_set(); dialog.resizable(False, False)
        configure_tk_scaling(dialog); dialog.geometry("430x280")
        form = ttk.Frame(dialog, padding=16); form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        nickname = tk.StringVar(value=original.get("nickname", "") if original else "")
        salutation = original.get("salutation", "") if original else ""
        email = tk.StringVar(value=original.get("email", "") if original else "")
        custom = tk.StringVar(value="")
        presets = ("无", "同学", "妈妈", "爸爸", "爷爷", "奶奶", "家长", "老师")
        preset = tk.StringVar(value=("无" if not salutation else salutation) if (not editing or salutation in presets or not salutation) else "自定义（填写）")
        if editing and salutation not in presets and salutation:
            custom.set(salutation)
        ttk.Label(form, text="昵称").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=7)
        ttk.Entry(form, textvariable=nickname).grid(row=0, column=1, sticky="ew", pady=7)
        ttk.Label(form, text="称呼").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=7)
        ttk.Combobox(form, textvariable=preset, state="readonly", values=("无", "同学", "妈妈", "爸爸", "爷爷", "奶奶", "家长", "老师", "自定义（填写）")).grid(row=1, column=1, sticky="ew", pady=7)
        ttk.Label(form, text="自定义称呼").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=7)
        custom_entry = ttk.Entry(form, textvariable=custom, state="disabled")
        custom_entry.grid(row=2, column=1, sticky="ew", pady=7)
        ttk.Label(form, text="电子邮箱").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=7)
        ttk.Entry(form, textvariable=email).grid(row=3, column=1, sticky="ew", pady=7)
        preset.trace_add("write", lambda *_: custom_entry.configure(state="normal" if preset.get() == "自定义（填写）" else "disabled"))
        custom_entry.configure(state="normal" if preset.get() == "自定义（填写）" else "disabled")
        def save_account():
            name, address = nickname.get().strip(), email.get().strip()
            greeting = custom.get().strip() if preset.get() == "自定义（填写）" else ("" if preset.get() == "无" else preset.get())
            if not name or (preset.get() == "自定义（填写）" and not greeting) or "@" not in address:
                messagebox.showwarning("信息不完整", "请填写昵称、称呼和有效的电子邮箱地址。", parent=dialog); return
            person = {"nickname": name, "salutation": greeting, "email": address}
            if editing:
                self.settings["subscribers"][account_index] = person
            else:
                self.settings["subscribers"].append(person)
            try: save_settings(self.settings)
            except (OSError, ValueError) as error:
                if editing:
                    self.settings["subscribers"][account_index] = original
                else:
                    self.settings["subscribers"].pop()
                messagebox.showerror("保存失败", str(error), parent=dialog); return
            self._populate()
            dialog.destroy()
        ttk.Button(form, text="确定", command=save_account).grid(row=4, column=1, sticky="e", pady=(12, 0))

    def _delete(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showinfo("删除订阅账户", "请先选中列表中的账户。", parent=self.root); return
        person = self.settings["subscribers"][selected[0]]
        if messagebox.askyesno("确认删除", "确定删除订阅账户“{}”吗？".format(person.get("nickname", "")), parent=self.root):
            removed = self.settings["subscribers"].pop(selected[0])
            try:
                save_settings(self.settings)
            except (OSError, ValueError) as error:
                self.settings["subscribers"].insert(selected[0], removed)
                messagebox.showerror("删除失败", str(error), parent=self.root)
                return
            self._populate()

    def _read(self):
        settings = self.settings
        settings["source"] = {key: self.vars[key].get().strip() for key in self.vars}
        settings["source"]["port"] = int(settings["source"]["port"] or 465)
        settings["source"]["security"] = self.security.get()
        return settings

    def _save_smtp(self):
        try:
            settings = self._read()
            save_settings({**self.settings, "source": settings["source"]})
            self.settings["source"] = settings["source"]
            self.status.set("SMTP 推送源已保存")
            self._check_smtp_connection()
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror("保存失败", str(error), parent=self.root)

    def _check_smtp_connection(self):
        self._smtp_check_generation += 1
        generation = self._smtp_check_generation
        source = dict(self.settings.get("source", {}))
        # Include unsaved values in the form so the status always tests what is currently visible.
        if self.vars:
            source = {key: variable.get().strip() for key, variable in self.vars.items()}
            try: source["port"] = int(source.get("port") or 465)
            except ValueError: source["port"] = ""
            source["security"] = self.security.get()
        self.smtp_status.set("正在检测 SMTP 连接…")
        self.smtp_status_label.configure(foreground="#777777")
        def worker():
            connected = check_smtp_connection(source)
            def update():
                if generation != self._smtp_check_generation:
                    return
                if connected:
                    self.smtp_status.set("已连接到 SMTP 服务器")
                    self.smtp_status_label.configure(foreground="#187A3D")
                else:
                    self.smtp_status.set("无法连接到 SMTP 服务器")
                    self.smtp_status_label.configure(foreground="#B3261E")
            try: self.root.after(0, update)
            except tk.TclError: pass
        threading.Thread(target=worker, daemon=True).start()

    def _save_format(self):
        try:
            self.settings["title_template"] = self.title_text.get("1.0", "end-1c")
            self.settings["body_template"] = self.body_text.get("1.0", "end-1c")
            save_settings(self.settings); self.status.set("推送格式已保存")
        except OSError as error: messagebox.showerror("保存失败", str(error), parent=self.root)

    def _save_schedule(self):
        try:
            schedule_time = self.time_var.get().strip()
            datetime.strptime(schedule_time, "%H:%M")
            enabled = self.enabled.get()
            if enabled and (not self.settings.get("schedule_enabled") or self.settings.get("schedule_time") != schedule_time):
                if not messagebox.askyesno("确认定时推送", "确认每天 {} 向所有订阅账户发送推送邮件？\n仅当 HWM 正在运行时执行。".format(schedule_time), parent=self.root): return
            self.settings["schedule_enabled"] = enabled
            self.settings["schedule_time"] = schedule_time
            save_settings(self.settings); self.status.set("定时推送设置已保存")
        except (OSError, ValueError) as error: messagebox.showerror("保存失败", str(error), parent=self.root)

    def _push(self):
        try:
            settings = self._read()
            settings["title_template"] = self.title_text.get("1.0", "end-1c")
            settings["body_template"] = self.body_text.get("1.0", "end-1c")
            if not settings["subscribers"]: raise ValueError("请先添加订阅账户。")
            if not messagebox.askyesno("确认发出推送", "将立即向 {} 个订阅账户推送作业\n确认发送？".format(len(settings["subscribers"])), parent=self.root): return
            save_settings(settings)
            self.status.set("正在发送...")
            threading.Thread(target=self._send_worker, args=(settings,), daemon=True).start()
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror("无法发送", str(error), parent=self.root)

    def _send_worker(self, settings):
        try:
            count = send_push(settings)
            self.root.after(0, lambda: self.status.set("已发送到 {} 个订阅账户".format(count)))
        except Exception as error:
            self.root.after(0, lambda e=str(error): messagebox.showerror("推送失败", e, parent=self.root))
            self.root.after(0, lambda: self.status.set("推送失败"))


def main():
    enable_high_dpi()
    root = tk.Tk()
    try:
        SubscriptionManager(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        messagebox.showerror("加载失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()


