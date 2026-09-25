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
import sys
import threading
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from HWMRuntime import (
    close_config_reload_event,
    close_shutdown_event,
    configure_tk_scaling,
    create_config_reload_event,
    create_shutdown_event,
    enable_high_dpi,
    enable_touch_keyboard,
    notify_config_saved,
    set_window_size_percent,
    wait_for_config_reload,
    wait_for_shutdown,
    set_window_icon,
)
from HWMConfig import load_config, load_homework_data, save_homework_data


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = APPLICATION_DIR
CONFIG_FILE = RESOURCE_DIR / "config.json"
HOMEWORK_FILE = RESOURCE_DIR / "homework.json"
SUBJECT_NAMES = {
    "chinese": "语文",
    "maths": "数学",
    "english": "英语",
    "history": "历史",
    "politics": "政治",
    "physics": "物理",
    "chemistry": "化学",
    "biology": "生物",
    "geography": "地理",
    "it": "信息技术",
    "pe": "体育",
    "art": "美术",
    "other": "其他",
}






def load_homework():
    homework = {}
    config = load_config(CONFIG_FILE)
    data = load_homework_data(HOMEWORK_FILE, CONFIG_FILE)

    def current_time():
        return datetime.now().isoformat(timespec="seconds")

    for subject_work in data:
        if not isinstance(subject_work, dict):
            raise ValueError("每个科目必须是 JSON 对象")
        for subject, assignments in subject_work.items():
            if not isinstance(subject, str) or not subject.strip():
                raise ValueError("科目名称必须是非空字符串")
            if not isinstance(assignments, list):
                raise ValueError("科目项目必须是 JSON 数组")
            valid_assignments = []
            for assignment in assignments:
                if isinstance(assignment, str) and assignment.strip():
                    valid_assignments.append(
                        {
                            "project": assignment.strip(),
                            "hide": False,
                            "date_modified": current_time(),
                        }
                    )
                elif isinstance(assignment, dict):
                    project_text = assignment.get("project", assignment.get("subject"))
                    if (
                        isinstance(project_text, str)
                        and project_text.strip()
                        and isinstance(assignment.get("hide", False), bool)
                    ):
                        valid_assignments.append(
                            {
                                "project": project_text.strip(),
                                "hide": assignment.get("hide", False),
                                "date_modified": assignment.get(
                                    "date_modified", current_time()
                                ),
                            }
                        )
                    else:
                        raise ValueError("项目项必须是非空字符串")
                else:
                    raise ValueError("项目项必须是非空字符串")
            homework[subject] = valid_assignments

    return homework, config


def save_homework(homework):
    save_homework_data(HOMEWORK_FILE, [{subject: assignments} for subject, assignments in homework.items()])


class HomeworkEditor:
    def __init__(self, root):
        self.root = root
        enable_touch_keyboard(root)
        set_window_icon(root, __file__)
        self.root.title("Homework Manager 项目编辑器")
        self.homework, self.config = load_homework()
        configure_tk_scaling(root)
        set_window_size_percent(
            root,
            self.config.get("editor_width_percent", 50),
            self.config.get("editor_height_percent", 50),
        )
        self.selected_subject = tk.StringVar()
        self.status_text = tk.StringVar(value="就绪")

        self.create_widgets()
        self.refresh_subjects()
        self.reload_event = create_config_reload_event("homework_editor")
        self.shutdown_event = create_shutdown_event("homework_editor")
        if self.reload_event is not None:
            threading.Thread(target=self.wait_for_reload, daemon=True).start()
        if self.shutdown_event is not None:
            threading.Thread(target=self.wait_for_shutdown_signal, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        close_config_reload_event(self.reload_event)
        close_shutdown_event(self.shutdown_event)
        self.root.destroy()

    def wait_for_shutdown_signal(self):
        if wait_for_shutdown(self.shutdown_event):
            self.root.after(0, self.close)

    def wait_for_reload(self):
        if wait_for_config_reload(self.reload_event):
            self.root.after(0, self.reload_config)
            threading.Thread(target=self.wait_for_reload, daemon=True).start()

    def reload_config(self):
        try:
            _, self.config = load_homework()
            self.apply_subject_list_width()
            self.status_text.set("已从文件刷新项目和配置")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.status_text.set("刷新配置失败：{}".format(error))

    def apply_subject_list_width(self):
        subject_width_percent = max(
            0, min(100, int(self.config.get("subject_list_width_percent", 25)))
        )
        subject_width = round(
            self.root.winfo_screenwidth() * subject_width_percent / 100
        )
        self.main.columnconfigure(0, minsize=subject_width + 12, weight=0)
        self.main.columnconfigure(1, weight=1)

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        self.main = main
        self.apply_subject_list_width()
        main.rowconfigure(1, weight=1)

        ttk.Label(main, text="科目").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(main, text="项目").grid(row=0, column=1, sticky="w")

        subject_frame = ttk.Frame(main)
        subject_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        subject_frame.rowconfigure(0, weight=1)
        subject_frame.columnconfigure(0, weight=1)

        self.subject_list = tk.Listbox(
            subject_frame,
            width=3,
            exportselection=False,
        )
        self.subject_list.grid(row=0, column=0, sticky="nsew")
        self.subject_list.bind("<<ListboxSelect>>", self.on_subject_selected)

        subject_scrollbar = ttk.Scrollbar(
            subject_frame, orient="vertical", command=self.subject_list.yview
        )
        subject_scrollbar.grid(row=0, column=1, sticky="ns")
        self.subject_list.configure(yscrollcommand=subject_scrollbar.set)

        assignment_frame = ttk.Frame(main)
        assignment_frame.grid(row=1, column=1, sticky="nsew")
        assignment_frame.columnconfigure(0, weight=1)
        assignment_frame.rowconfigure(0, weight=1)

        self.assignment_list = tk.Listbox(
            assignment_frame,
            exportselection=False,
            selectmode=tk.SINGLE,
        )
        self.assignment_list.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.assignment_list.bind("<<ListboxSelect>>", self.on_assignment_selected)

        scrollbar = ttk.Scrollbar(
            assignment_frame,
            orient="vertical",
            command=self.assignment_list.yview,
        )
        scrollbar.grid(row=0, column=2, sticky="ns")
        self.assignment_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(assignment_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="添加", command=self.add_assignment).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(buttons, text="编辑选中项", command=self.edit_assignment).pack(
            side="left", padx=(0, 6)
        )
        self.toggle_button = ttk.Button(
            buttons, text="显示/隐藏", command=self.toggle_assignment
        )
        self.toggle_button.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="删除选中项", command=self.delete_assignment).pack(
            side="left", padx=(0, 6)
        )

        bottom = ttk.Frame(main)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status_text).grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="保存项目", command=self.save).grid(
            row=0, column=2, sticky="e"
        )

    def refresh_subjects(self, subject_to_select=None):
        subjects = list(self.homework)
        self.subject_list.delete(0, tk.END)
        for subject in subjects:
            self.subject_list.insert(tk.END, SUBJECT_NAMES.get(subject, subject))

        if subjects:
            selected = subject_to_select if subject_to_select in subjects else subjects[0]
            index = subjects.index(selected)
            self.subject_list.selection_set(index)
            self.subject_list.activate(index)
            self.subject_list.see(index)
            self.selected_subject.set(selected)
            self.refresh_assignments()
        else:
            self.selected_subject.set("")
            self.assignment_list.delete(0, tk.END)
            self._update_toggle_button()

    def refresh_assignments(self, assignment_index=None):
        self.assignment_list.delete(0, tk.END)
        assignments = self.homework.get(self.selected_subject.get(), [])
        for assignment in assignments:
            index = self.assignment_list.size()
            display_text = assignment["project"]
            if assignment["hide"]:
                display_text = "• " + display_text
            self.assignment_list.insert(tk.END, display_text)
            if assignment["hide"]:
                self.assignment_list.itemconfig(index, foreground="#aaaaaa")
        if assignments:
            index = 0 if assignment_index is None else min(
                assignment_index, len(assignments) - 1
            )
            self.assignment_list.selection_set(index)
            self.assignment_list.activate(index)
            self.assignment_list.see(index)
        self._update_toggle_button()

    def on_subject_selected(self, _event=None):
        selection = self.subject_list.curselection()
        if not selection:
            return
        subject = list(self.homework)[selection[0]]
        self.selected_subject.set(subject)
        self.refresh_assignments()

    def on_assignment_selected(self, _event=None):
        self._update_toggle_button()

    def _update_toggle_button(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if selection and subject:
            hidden = self.homework[subject][selection[0]]["hide"]
            self.toggle_button.configure(
                text="显示" if hidden else "隐藏", state="normal"
            )
        else:
            self.toggle_button.configure(text="显示/隐藏", state="disabled")

    def _open_assignment_dialog(self, assignment_index=None):
        editing = assignment_index is not None
        subject = self.selected_subject.get()
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("编辑项目" if editing else "添加项目")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(500, 300)
        configure_tk_scaling(dialog)
        dialog.geometry("640x380")

        form = ttk.Frame(dialog, padding=14)
        form.pack(fill="both", expand=True)
        form.rowconfigure(1, weight=1)
        form.columnconfigure(0, weight=1)
        ttk.Label(form, text="项目内容（支持多行）").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        text_frame = ttk.Frame(form)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        editor = tk.Text(
            text_frame, wrap="word", undo=True, font=("Microsoft YaHei UI", 11)
        )
        editor.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        editor.configure(yscrollcommand=scrollbar.set)
        if editing:
            editor.insert("1.0", self.homework[subject][assignment_index]["project"])

        def save_assignment():
            value = editor.get("1.0", "end-1c").strip()
            if not value:
                messagebox.showwarning("输入无效", "项目内容不能为空。", parent=dialog)
                editor.focus_set()
                return
            now = datetime.now().isoformat(timespec="seconds")
            if editing:
                self.homework[subject][assignment_index]["project"] = value
                self.homework[subject][assignment_index]["date_modified"] = now
                selected_index = assignment_index
                self.status_text.set("已编辑项目，请注意保存")
            else:
                self.homework[subject].append({
                    "project": value,
                    "hide": False,
                    "date_modified": now,
                })
                selected_index = len(self.homework[subject]) - 1
                self.status_text.set("已添加项目，请注意保存")
            self.refresh_assignments(selected_index)
            dialog.destroy()

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(buttons, text="确定", command=save_assignment).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.after_idle(editor.focus_set)

    def add_assignment(self):
        subject = self.selected_subject.get()
        if not subject:
            messagebox.showwarning("未选择科目", "请先选择科目。", parent=self.root)
            return
        self._open_assignment_dialog()

    def edit_assignment(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not subject or not selection:
            messagebox.showwarning("未选择项目", "请先选择要编辑的项目项。", parent=self.root)
            return
        self._open_assignment_dialog(selection[0])

    def toggle_assignment(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not selection or not subject:
            messagebox.showwarning("未选择项目", "请先选择要切换显示状态的项目项。", parent=self.root)
            return
        index = selection[0]
        assignment = self.homework[subject][index]
        assignment["hide"] = not assignment["hide"]
        assignment["date_modified"] = datetime.now().isoformat(timespec="seconds")
        self.refresh_assignments(index)
        state = "已隐藏" if assignment["hide"] else "已显示"
        self.status_text.set(
            "{}项目项，请点击保存写入文件".format(state)
        )

    def delete_assignment(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not selection or not subject:
            messagebox.showwarning("未选择项目", "请先选择要删除的项目项。", parent=self.root)
            return
        if not messagebox.askyesno("确认删除", "确定删除选中的项目项吗？", parent=self.root):
            return
        index = selection[0]
        del self.homework[subject][index]
        self.refresh_assignments(index)
        self.status_text.set("已删除项目项，请点击保存写入文件")

    def save(self):
        try:
            save_homework(self.homework)
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("保存失败", str(error), parent=self.root)
            return
        self.status_text.set("作业项目已保存到 homework.json")
        notify_config_saved()
        messagebox.showinfo("保存成功", "项目列表已保存到 homework.json。", parent=self.root)


def main():
    enable_high_dpi()
    root = tk.Tk()
    try:
        HomeworkEditor(root)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("加载失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()


