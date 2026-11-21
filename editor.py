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
import copy
import shutil
import subprocess
from datetime import datetime, time, timedelta
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from runtime import (
    close_config_reload_event,
    close_shutdown_event,
    configure_tk_scaling,
    create_config_reload_event,
    create_shutdown_event,
    enable_high_dpi,
    enable_touch_keyboard,
    notify_config_saved,
    show_windows_notification,
    place_window_bottom_right,
    set_window_size_percent,
    wait_for_config_reload,
    wait_for_shutdown,
    set_window_icon,
)
from config import data_directory, load_config, load_assignment_data, save_config, save_assignment_data


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = APPLICATION_DIR
DATA_DIR = data_directory(RESOURCE_DIR)
CONFIG_FILE = DATA_DIR / "config.json"
ASSIGNMENT_FILE = DATA_DIR / "assignment.json"
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
    "it": "信息",
    "pe": "体育",
    "art": "美术",
    "other": "其他",
}
SCHEDULE_VISIBLE_COLOR = "#69C8D0"
SCHEDULE_HIDDEN_COLOR = "#315E7D"


def parse_datetime(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d")
        except ValueError:
            return None


def parse_time(value):
    if not isinstance(value, str) or not value.strip():
        return None
    if value.strip() in ("24:00", "24:00:00"):
        return None
    try:
        return time.fromisoformat(value.strip())
    except ValueError:
        return None


QUICK_PLAN_CHOICES = (
    "本周一",
    "本周二",
    "本周三",
    "本周四",
    "本周五",
    "本周六",
    "本周日",
    "下周一",
)


def quick_plan_until(choice, now=None):
    now = now or datetime.now()
    if choice not in QUICK_PLAN_CHOICES:
        raise ValueError("不支持的快速计划目标")
    weekday = 1 if choice == "下周一" else QUICK_PLAN_CHOICES.index(choice) + 1
    if choice == "下周一":
        monday = now.date() - timedelta(days=now.isoweekday() - 1)
        target_date = monday + timedelta(days=7)
    else:
        monday = now.date() - timedelta(days=now.isoweekday() - 1)
        target_date = monday + timedelta(days=weekday - 1)
    target = datetime.combine(target_date, time.min)
    return {
        "enabled": True,
        "root": {
            "type": "interval",
            "start": now.strftime("%Y-%m-%d %H:%M:%S"),
            "end": target.strftime("%Y-%m-%d %H:%M:%S"),
            "children": [],
        },
    }


def migrate_legacy_schedule_rules(rules):
    """Convert old persisted rules to the nested schedule-tree format."""
    children = []
    for rule in rules or []:
        if not isinstance(rule, dict):
            continue
        if rule.get("cycle") in ("daily", "每天"):
            children.append({"type": "calendar", "unit": "day", "selectors": {}, "children": []})
        elif rule.get("cycle") in ("weekly", "每周"):
            children.append({
                "type": "calendar",
                "unit": "week",
                "selectors": {"weekdays": [rule.get("weekday")]},
                "children": [],
            })
        elif rule.get("cycle") in ("monthly", "每月"):
            selectors = {}
            if rule.get("kind") in ("day", "某日"):
                selectors["month_days"] = [rule.get("day")]
            else:
                selectors["week_of_month"] = [rule.get("week")]
                if rule.get("weekday") is not None:
                    selectors["weekdays"] = [rule.get("weekday")]
            children.append({"type": "calendar", "unit": "month", "selectors": selectors, "children": []})
    if not children:
        return None
    return {"enabled": True, "root": {"type": "any", "children": children}}


def normalize_schedule(schedule, legacy_rules=None):
    if isinstance(schedule, dict):
        root = schedule.get("root")
        if isinstance(root, dict):
            root = copy.deepcopy(root)

            def remove_unsupported_calendar_nodes(node):
                if not isinstance(node, dict):
                    return None
                if node.get("type") == "calendar" and node.get("unit") not in ("day", "week", "month"):
                    return None
                children = node.get("children")
                if isinstance(children, list):
                    node["children"] = [
                        cleaned
                        for child in children
                        if (cleaned := remove_unsupported_calendar_nodes(child)) is not None
                    ]
                return node

            root = remove_unsupported_calendar_nodes(root)
            if root is None:
                root = {"type": "all", "children": []}
            return {"enabled": schedule.get("enabled", True) is True, "root": root}
    return migrate_legacy_schedule_rules(legacy_rules)


def is_calendar_match(node, moment):
    unit = node.get("unit")
    if unit == "day":
        pass
    elif unit == "week":
        pass
    elif unit == "month":
        pass
    else:
        return False

    selectors = node.get("selectors", {})
    if not isinstance(selectors, dict):
        selectors = {}

    weekdays = selectors.get("weekdays")
    if weekdays:
        if moment.isoweekday() not in weekdays:
            return False

    month_days = selectors.get("month_days")
    if month_days:
        matched = False
        for value in month_days:
            if value == "last":
                next_month = moment.replace(day=28) + timedelta(days=4)
                last_day = (next_month - timedelta(days=next_month.day)).day
                matched = moment.day == last_day
            elif isinstance(value, int) and moment.day == value:
                matched = True
            if matched:
                break
        if not matched:
            return False

    months = selectors.get("months")
    if months and moment.month not in months:
        return False

    week_of_month = selectors.get("week_of_month")
    if week_of_month:
        current_week = (moment.day - 1) // 7 + 1
        matched = False
        for value in week_of_month:
            if value == "last":
                next_week = moment + timedelta(days=7)
                matched = next_week.month != moment.month
            elif isinstance(value, int) and current_week == value:
                matched = True
            if matched:
                break
        if not matched:
            return False
    return True


def schedule_matches_node(node, moment):
    if not isinstance(node, dict):
        return False
    node_type = node.get("type")

    if node_type == "interval":
        start = parse_datetime(node.get("start"))
        end = parse_datetime(node.get("end"))
        if start is not None and moment < start:
            return False
        if end is not None and moment >= end:
            return False
    elif node_type == "calendar":
        if not is_calendar_match(node, moment):
            return False
    elif node_type == "time_window":
        start = parse_time(node.get("start"))
        end = parse_time(node.get("end"))
        if start is not None and moment.time().replace(tzinfo=None) < start:
            return False
        if end is not None and moment.time().replace(tzinfo=None) >= end:
            return False
    elif node_type == "any":
        return any(schedule_matches_node(child, moment) for child in node.get("children", []))
    elif node_type == "all":
        children = node.get("children", [])
        return bool(children) and all(schedule_matches_node(child, moment) for child in children)

    children = node.get("children", [])
    if not children:
        return True
    if node_type in ("interval", "calendar", "time_window"):
        return all(schedule_matches_node(child, moment) for child in children)
    return False


def schedule_matches(schedule, moment=None):
    moment = moment or datetime.now()
    if not isinstance(schedule, dict) or schedule.get("enabled", True) is not True:
        return False
    root = schedule.get("root")
    return isinstance(root, dict) and schedule_matches_node(root, moment)


def refresh_scheduled_assignments(entries):
    for assignments in entries.values():
        for assignment in assignments:
            schedule = assignment.get("schedule")
            if isinstance(schedule, dict) and schedule.get("enabled", True):
                assignment["hide"] = not schedule_matches(schedule)


def schedule_summary(schedule):
    if not isinstance(schedule, dict) or not schedule.get("root"):
        return ""
    enabled = "启用" if schedule.get("enabled", True) else "停用"
    return "计划规则（{}）".format(enabled)

def load_assignment():
    entries = {}
    config = load_config(CONFIG_FILE)
    data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)

    def current_time():
        return datetime.now().isoformat(timespec="seconds")

    for subject_work in data:
        if not isinstance(subject_work, dict):
            raise ValueError("每个科目必须是 JSON 对象")
        for subject, assignments in subject_work.items():
            if not isinstance(subject, str) or not subject.strip():
                raise ValueError("科目名称必须是非空字符串")
            if not isinstance(assignments, list):
                raise ValueError("科目作业必须是 JSON 数组")
            valid_assignments = []
            for assignment in assignments:
                if isinstance(assignment, str) and assignment.strip():
                    valid_assignments.append(
                        {
                            "assignment": assignment.strip(),
                            "hide": False,
                            "date_modified": current_time(),
                        }
                    )
                elif isinstance(assignment, dict):
                    assignment_text = assignment.get("assignment")
                    if (
                        isinstance(assignment_text, str)
                        and assignment_text.strip()
                        and isinstance(assignment.get("hide", False), bool)
                    ):
                        legacy_rules = assignment.get("schedule_rules", [])
                        schedule = normalize_schedule(
                            assignment.get("schedule"),
                            legacy_rules if isinstance(legacy_rules, list) else [],
                        )
                        valid_assignments.append(
                            {
                            "assignment": assignment_text.strip(),
                            "hide": assignment.get("hide", False),
                            "ignore_prefix": assignment.get("ignore_prefix", False) is True,
                            "ignore_suffix": assignment.get("ignore_suffix", False) is True,
                            "secondary": assignment.get("secondary", False) is True,
                            "schedule": schedule,
                                "date_modified": assignment.get(
                                    "date_modified", current_time()
                                ),
                            }
                        )
                    else:
                        raise ValueError("作业项必须是非空字符串")
                else:
                    raise ValueError("作业项必须是非空字符串")
            entries[subject] = valid_assignments

    refresh_scheduled_assignments(entries)
    return entries, config


def save_assignment(assignment):
    save_assignment_data(ASSIGNMENT_FILE, [{subject: assignments} for subject, assignments in assignment.items()])


class editor:
    def __init__(self, root):
        self.root = root
        enable_touch_keyboard(root)
        set_window_icon(root, __file__)
        self.root.title("Homework Manager 作业编辑器")
        self.assignment, self.config = load_assignment()
        configure_tk_scaling(root)
        set_window_size_percent(
            root,
            self.config.get("editor_width_percent", 50),
            self.config.get("editor_height_percent", 50),
        )
        self.selected_subject = tk.StringVar()
        self.status_text = tk.StringVar(value="就绪")
        self.undo_stack = []
        self.redo_stack = []
        self._dirty = False
        self.management_action_buttons = {}

        self.create_widgets()
        self._update_save_button()
        self.refresh_subjects()
        self.reload_event = create_config_reload_event("assignment_editor")
        self.shutdown_event = create_shutdown_event("assignment_editor")
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
            _, self.config = load_assignment()
            self._dirty = False
            self._update_save_button()
            self._context_status("已从文件刷新配置")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self._context_status("刷新配置失败（{}）".format(error))

    @staticmethod
    def _make_mousewheel_handler(listbox):
        def on_mousewheel(event):
            if getattr(event, "delta", 0):
                listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                listbox.yview_scroll(-1, "units")
            elif event.num == 5:
                listbox.yview_scroll(1, "units")
            return "break"
        return on_mousewheel

    def _bind_mousewheel(self, listbox):
        handler = self._make_mousewheel_handler(listbox)
        listbox.bind("<MouseWheel>", handler)
        listbox.bind("<Button-4>", handler)
        listbox.bind("<Button-5>", handler)

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        self.main = main
        main.rowconfigure(1, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="科目").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(main, text="作业").grid(row=0, column=1, sticky="w")

        subject_frame = ttk.Frame(main)
        subject_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        subject_frame.rowconfigure(0, weight=1)
        subject_frame.columnconfigure(0, weight=1)

        self.subject_list = tk.Listbox(
            subject_frame,
            width=5,
            exportselection=False,
        )
        self.subject_list.grid(row=0, column=0, sticky="nsew")
        self.subject_list.bind("<<ListboxSelect>>", self.on_subject_selected)
        self._bind_mousewheel(self.subject_list)

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
            font=("Microsoft YaHei UI", 10),
        )
        self.assignment_list.grid(row=0, column=0, sticky="nsew")
        self.assignment_list.bind("<<ListboxSelect>>", self.on_assignment_selected)
        self._bind_mousewheel(self.assignment_list)

        scrollbar = ttk.Scrollbar(
            assignment_frame,
            orient="vertical",
            command=self.assignment_list.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.assignment_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(assignment_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        button_group = ttk.Frame(buttons)
        button_group.grid(row=0, column=0, sticky="w")
        self.action_specs = [
            ("add", "添加...", self.add_assignment), ("edit", "编辑...", self.edit_assignment),
            ("toggle", "显示/隐藏", self.toggle_assignment), ("delete", "删除", self.delete_assignment),
            ("copy", "复制", self.copy_assignment), ("move_subject", "移动到...", self.move_assignment_subject),
            ("up", "上置", self.move_up_assignment), ("down", "下置", self.move_down_assignment),
            ("toggle_all", "隐藏所有", self.toggle_all_assignments),
            ("delete_all", "删除所有", self.delete_all_assignments),
        ]
        self.action_buttons = {}
        order = self.config.get("editor_action_order", [key for key, _, _ in self.action_specs])
        ordered_specs = sorted(self.action_specs, key=lambda item: order.index(item[0]) if item[0] in order else len(order))
        for position, (key, label, command) in enumerate(ordered_specs):
            button = ttk.Button(button_group, text=label, command=command)
            button.pack(side="left", padx=(0, 4))
            self.action_buttons[key] = button
        self.add_button = self.action_buttons["add"]
        self.edit_button = self.action_buttons["edit"]
        self.toggle_button = self.action_buttons["toggle"]
        self.delete_button = self.action_buttons["delete"]
        self.copy_button = self.action_buttons["copy"]
        self.move_subject_button = self.action_buttons["move_subject"]
        self.move_up_button = self.action_buttons["up"]
        self.move_down_button = self.action_buttons["down"]
        self.toggle_all_button = self.action_buttons["toggle_all"]
        visible_actions = set(self.config.get("editor_visible_actions", []))
        for action_key, action_button in self.action_buttons.items():
            if action_key not in visible_actions:
                action_button.pack_forget()
        self.all_actions_button = ttk.Button(
            buttons, text="...", command=self.open_all_actions, width=2
        )
        self.all_actions_button.grid(row=0, column=1, sticky="e", padx=(8, 0))

        bottom = ttk.Frame(main)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status_text).grid(row=0, column=0, sticky="w")
        self.undo_button = ttk.Button(bottom, text="撤销", command=self.undo, state="disabled")
        self.undo_button.grid(row=0, column=1, sticky="e", padx=(0, 4))
        self.redo_button = ttk.Button(bottom, text="恢复", command=self.redo, state="disabled")
        self.redo_button.grid(row=0, column=2, sticky="e", padx=(0, 4))
        self.save_button = ttk.Button(bottom, text="保存作业", command=self.save)
        self.dashboard_button = ttk.Button(
            bottom, text="仪表盘...", command=self.open_dashboard
        )
        self.management_toolbar_buttons = {
            "undo": self.undo_button,
            "redo": self.redo_button,
            "save": self.save_button,
            "dashboard": self.dashboard_button,
        }
        self.all_management_button = ttk.Button(
            bottom, text="...", command=self.open_all_management, width=2
        )
        self.all_management_button.grid(row=0, column=4, sticky="e")
        self._apply_management_action_visibility()

    @staticmethod
    def _subject_name(subject):
        return SUBJECT_NAMES.get(subject, subject or "未选择科目")

    def open_all_actions(self):
        subject = self.selected_subject.get()
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("所有作业操作")
        dialog.transient(self.root)
        dialog.grab_set()
        self.all_actions_dialog = dialog
        dialog.minsize(260, 120)
        configure_tk_scaling(dialog)
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)
        selection = self.assignment_list.curselection()
        assignments = self.assignment.get(subject, []) if subject else []
        assignment = assignments[selection[0]]["assignment"] if selection and selection[0] < len(assignments) else "全部作业"
        assignment = assignment.replace("\r\n", "\n").replace("\r", "\n")
        assignment = assignment.split("\n", 1)[0].strip()
        assignment = " ".join(assignment.split())
        if len(assignment) > 24:
            assignment = assignment[:23] + "..."
        ttk.Label(
            frame,
            text="对 {} 或其中的\n {} 进行……".format(self._subject_name(subject), assignment),
        ).pack(anchor="w", pady=(0, 10))
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        self.all_action_rows = {}
        visible = set(self.config.get("editor_visible_actions", [key for key, _, _ in self.action_specs]))
        order = self.config.get("editor_action_order", [key for key, _, _ in self.action_specs])
        ordered_specs = sorted(self.action_specs, key=lambda item: order.index(item[0]) if item[0] in order else len(order))
        for key, label, command in ordered_specs:
            row = ttk.Frame(actions)
            row.pack(fill="x", pady=2)
            self.all_action_rows[key] = row
            button = ttk.Button(row, text=self.toggle_all_button.cget("text") if key == "toggle_all" else label,
                                command=command, state=self.action_buttons[key].cget("state"))
            button.pack(side="left", fill="x", expand=True)
            selected = tk.BooleanVar(value=key in visible)
            ttk.Checkbutton(row, variable=selected, command=lambda k=key, v=selected: self.set_action_visible(k, v.get())).pack(side="right", padx=(8, 0))
            ttk.Button(row, text="↓", width=1.2, command=lambda k=key: self.move_action_order(k, 1)).pack(side="right", padx=(2, 0))
            ttk.Button(row, text="↑", width=1.2, command=lambda k=key: self.move_action_order(k, -1)).pack(side="right", padx=(2, 0))
        def close_dialog():
            if getattr(self, "all_actions_dialog", None) is dialog:
                self.all_actions_dialog = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        place_window_bottom_right(dialog)

    def open_all_management(self):
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("所有管理操作")
        self.all_management_dialog = dialog
        dialog.transient(self.root)
        dialog.grab_set()
        configure_tk_scaling(dialog)
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)
        actions = [
            ("undo", "撤销", self.undo, self.undo_button),
            ("redo", "恢复", self.redo, self.redo_button),
            ("save", "保存作业", self.save, self.save_button),
            ("dashboard", "仪表盘...", self.open_dashboard, None),
        ]
        self.management_action_buttons = {}
        visible = set(self.config.get("editor_visible_management_actions", [key for key, *_ in actions]))
        order = self.config.get("editor_management_action_order", [key for key, *_ in actions])
        ordered = sorted(actions, key=lambda item: order.index(item[0]) if item[0] in order else len(order))
        for key, label, command, state_source in ordered:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            button = ttk.Button(row, text=label, command=command,
                                state=state_source.cget("state") if state_source else "normal")
            button.pack(side="left", fill="x", expand=True)
            self.management_action_buttons[key] = button
            selected = tk.BooleanVar(value=key in visible)
            ttk.Checkbutton(row, variable=selected, command=lambda k=key, v=selected: self.set_management_action_visible(k, v.get())).pack(side="right", padx=(8, 0))
            ttk.Button(row, text="↓", width=1.2, command=lambda k=key: self.move_management_action_order(k, 1)).pack(side="right", padx=(2, 0))
            ttk.Button(row, text="↑", width=1.2, command=lambda k=key: self.move_management_action_order(k, -1)).pack(side="right", padx=(2, 0))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        place_window_bottom_right(dialog)

    def _management_action_specs(self):
        return [("undo", "撤销", self.undo, self.undo_button), ("redo", "恢复", self.redo, self.redo_button),
                ("save", "保存作业", self.save, self.save_button),
                ("dashboard", "仪表盘...", self.open_dashboard, None)]

    def open_dashboard(self):
        if getattr(sys, "frozen", False):
            command = [sys.executable, "--component", "dashboard"]
        else:
            executable = Path(sys.executable).with_name("pythonw.exe")
            command = [str(executable if executable.exists() else sys.executable),
                       str(APPLICATION_DIR / "dashboard.py")]
        subprocess.Popen(command, cwd=str(APPLICATION_DIR),
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def move_management_action_order(self, key, direction):
        keys = [item[0] for item in self._management_action_specs()]
        order = self.config.get("editor_management_action_order", keys.copy())
        order = [item for item in order if item in keys]
        order.extend(item for item in keys if item not in order)
        target = order.index(key) + direction
        if target < 0 or target >= len(order):
            return
        order[order.index(key)], order[target] = order[target], order[order.index(key)]
        self.config["editor_management_action_order"] = order
        save_config(CONFIG_FILE, self.config)
        dialog = getattr(self, "all_management_dialog", None)
        if dialog and dialog.winfo_exists():
            dialog.destroy()
            self.open_all_management()

    def set_management_action_visible(self, key, visible):
        keys = [item[0] for item in self._management_action_specs()]
        actions = set(self.config.get("editor_visible_management_actions", keys))
        (actions.add if visible else actions.discard)(key)
        self.config["editor_visible_management_actions"] = [item for item in keys if item in actions]
        save_config(CONFIG_FILE, self.config)
        self._apply_management_action_visibility()
        dialog = getattr(self, "all_management_dialog", None)
        if dialog and dialog.winfo_exists():
            dialog.destroy()
            self.open_all_management()

    def _apply_management_action_visibility(self):
        visible = set(self.config.get("editor_visible_management_actions", ["undo", "redo", "save"]))
        keys = [item[0] for item in self._management_action_specs()]
        order = self.config.get("editor_management_action_order", keys)
        ordered = [key for key in order if key in keys]
        ordered.extend(key for key in keys if key not in ordered)
        column = 1
        for key in ordered:
            widget = self.management_toolbar_buttons[key]
            if key in visible:
                widget.grid(row=0, column=column, sticky="e", padx=(0, 4))
                column += 1
            else:
                widget.grid_remove()
        self.all_management_button.grid(row=0, column=column, sticky="e")

    def move_action_order(self, key, direction):
        keys = [item[0] for item in self.action_specs]
        order = self.config.get("editor_action_order", keys.copy())
        order = [item for item in order if item in keys]
        order.extend(item for item in keys if item not in order)
        position = order.index(key)
        target = position + direction
        if target < 0 or target >= len(order):
            return
        order[position], order[target] = order[target], order[position]
        self.config["editor_action_order"] = order
        save_config(CONFIG_FILE, self.config)
        visible = set(self.config.get("editor_visible_actions", keys))
        for action_key in order:
            button = self.action_buttons[action_key]
            button.pack_forget()
            if action_key in visible:
                button.pack(side="left", padx=(0, 4))
        dialog = getattr(self, "all_actions_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            for action_key in order:
                row = getattr(self, "all_action_rows", {}).get(action_key)
                if row is not None and row.winfo_exists():
                    row.pack_forget()
                    row.pack(fill="x", pady=2)

    def set_action_visible(self, key, visible):
        actions = set(self.config.get("editor_visible_actions", [item[0] for item in self.action_specs]))
        if visible:
            actions.add(key)
        else:
            actions.discard(key)
        self.config["editor_visible_actions"] = [item[0] for item in self.action_specs if item[0] in actions]
        save_config(CONFIG_FILE, self.config)
        for action_key, _, _ in self.action_specs:
            button = self.action_buttons[action_key]
            if action_key in actions:
                button.pack(side="left", padx=(0, 4))
            else:
                button.pack_forget()

    def _context_status(self, action, subject=None, assignment=None):
        subject = subject if subject is not None else self.selected_subject.get()
        if assignment is None and subject:
            selection = self.assignment_list.curselection()
            assignments = self.assignment.get(subject, [])
            if selection and selection[0] < len(assignments):
                assignment = assignments[selection[0]]["assignment"]
        assignment = assignment or "全部作业"
        self.status_text.set(
            "{}：{}（{}）".format(
                action, assignment, self._subject_name(subject)
            )
        )

    def _record_undo(self):
        self.undo_stack.append(copy.deepcopy(self.assignment))
        self.redo_stack.clear()
        self._update_history_buttons()
        self._set_dirty(True)

    def _set_dirty(self, dirty):
        self._dirty = dirty
        self._update_save_button()

    def _update_save_button(self):
        state = "normal" if self._dirty else "disabled"
        self.save_button.configure(state=state)
        dialog = getattr(self, "all_management_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            button = self.management_action_buttons.get("save")
            if button is not None:
                button.configure(state=state)

    def _update_history_buttons(self):
        self.undo_button.configure(state="normal" if self.undo_stack else "disabled")
        self.redo_button.configure(state="normal" if self.redo_stack else "disabled")

    def undo(self):
        if not self.undo_stack:
            return
        subject = self.selected_subject.get()
        selection = self.assignment_list.curselection()
        index = selection[0] if selection else None
        self.redo_stack.append(copy.deepcopy(self.assignment))
        self.assignment = self.undo_stack.pop()
        self.refresh_subjects(subject)
        if subject in self.assignment and index is not None and self.assignment[subject]:
            self.refresh_assignments(index)
        self._update_history_buttons()
        self._set_dirty(True)
        self._context_status("已撤销")

    def redo(self):
        if not self.redo_stack:
            return
        subject = self.selected_subject.get()
        selection = self.assignment_list.curselection()
        index = selection[0] if selection else None
        self.undo_stack.append(copy.deepcopy(self.assignment))
        self.assignment = self.redo_stack.pop()
        self.refresh_subjects(subject)
        if subject in self.assignment and index is not None and self.assignment[subject]:
            self.refresh_assignments(index)
        self._update_history_buttons()
        self._set_dirty(True)
        self._context_status("已恢复")

    def refresh_subjects(self, subject_to_select=None):
        subjects = list(self.assignment)
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
            self._update_buttons_state()

    def refresh_assignments(self, assignment_index=None):
        self.assignment_list.delete(0, tk.END)
        assignments = self.assignment.get(self.selected_subject.get(), [])
        for assignment in assignments:
            index = self.assignment_list.size()
            display_text = assignment["assignment"]
            if assignment["hide"]:
                display_text = "• " + display_text
            self.assignment_list.insert(tk.END, display_text)
            if assignment.get("schedule"):
                self.assignment_list.itemconfig(index, foreground=SCHEDULE_VISIBLE_COLOR if assignment["hide"] else SCHEDULE_HIDDEN_COLOR)
            elif assignment["hide"]:
                self.assignment_list.itemconfig(index, foreground="#aaaaaa")
        if assignments:
            index = 0 if assignment_index is None else min(
                assignment_index, len(assignments) - 1
            )
            self.assignment_list.selection_set(index)
            self.assignment_list.activate(index)
            self.assignment_list.see(index)
        self._update_buttons_state()

    def on_subject_selected(self, _event=None):
        selection = self.subject_list.curselection()
        if not selection:
            return
        subject = list(self.assignment)[selection[0]]
        self.selected_subject.set(subject)
        self.refresh_assignments()

    def on_assignment_selected(self, _event=None):
        self._update_buttons_state()

    def _update_buttons_state(self, _event=None):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        total = len(self.assignment.get(subject, [])) if subject else 0
        has_subject = bool(subject)
        has_selection = bool(selection and subject)
        assignments = self.assignment.get(subject, []) if subject else []
        has_hidden = any(assignment["hide"] for assignment in assignments)
        self.add_button.configure(state="normal" if has_subject else "disabled")
        self.toggle_all_button.configure(
            text="显示所有" if has_hidden else "隐藏所有",
            state="normal" if assignments else "disabled",
        )
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.copy_button.configure(state="normal" if has_selection else "disabled")
        self.move_subject_button.configure(state="normal" if has_selection else "disabled")
        if has_selection:
            index = selection[0]
            selected_assignment = self.assignment[subject][index]
            schedule = selected_assignment.get("schedule")
            scheduled = bool(schedule and schedule.get("enabled", True))
            hidden = selected_assignment["hide"]
            self.toggle_button.configure(
                text="由计划控制" if scheduled else ("显示" if hidden else "隐藏"),
                state="disabled" if scheduled else "normal"
            )
            self.move_up_button.configure(state="normal" if index > 0 else "disabled")
            self.move_down_button.configure(state="normal" if index < total - 1 else "disabled")
        else:
            self.toggle_button.configure(text="显示/隐藏", state="disabled")
            self.move_up_button.configure(state="disabled")
            self.move_down_button.configure(state="disabled")

    def _open_assignment_dialog(self, assignment_index=None):
        editing = assignment_index is not None
        subject = self.selected_subject.get()
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("编辑作业" if editing else "添加作业")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(500, 300)
        configure_tk_scaling(dialog)
        set_window_size_percent(dialog, 35, 35)

        form = ttk.Frame(dialog, padding=14)
        form.pack(fill="both", expand=True)
        form.rowconfigure(1, weight=1)
        form.columnconfigure(0, weight=1)
        ttk.Label(form, text="作业内容").grid(
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
            current_assignment = self.assignment[subject][assignment_index]
            editor.insert("1.0", current_assignment["assignment"])
        else:
            current_assignment = {}

        ignore_prefix_var = tk.BooleanVar(value=current_assignment.get("ignore_prefix", False))
        ignore_suffix_var = tk.BooleanVar(value=current_assignment.get("ignore_suffix", False))
        secondary_var = tk.BooleanVar(value=current_assignment.get("secondary", False))
        schedule_configured = [isinstance(current_assignment.get("schedule"), dict)]
        schedule_enabled_var = tk.BooleanVar(
            value=(
                schedule_configured[0]
                and current_assignment.get("schedule", {}).get("enabled", True)
            )
        )
        schedule = copy.deepcopy(current_assignment.get("schedule")) or {
            "enabled": True,
            "root": {"type": "all", "children": []},
        }
        property_row = ttk.Frame(form)
        property_row.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(property_row, text="忽略前缀", variable=ignore_prefix_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(property_row, text="忽略后缀", variable=ignore_suffix_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(property_row, text="次要作业", variable=secondary_var).pack(side="left")

        schedule_row = ttk.Frame(form)
        schedule_row.grid(row=3, column=0, sticky="w", pady=(6, 0))
        pending_quick_plan = [None]

        def finish_schedule_config():
            schedule_configured[0] = True
            pending_quick_plan[0] = None

        def open_schedule():
            self._schedule_rules_dialog(
                dialog,
                schedule,
                on_confirm=finish_schedule_config,
            )

        ttk.Checkbutton(schedule_row, variable=schedule_enabled_var).pack(side="left", padx=(0, 6))
        ttk.Button(schedule_row, text="计划任务", command=open_schedule).pack(side="left")
        ttk.Label(schedule_row, text="快速计划").pack(side="left", padx=(12, 6))
        quick_plan_var = tk.StringVar(value="")
        quick_plan_selector = ttk.Combobox(
            schedule_row,
            textvariable=quick_plan_var,
            values=["直到" + choice for choice in QUICK_PLAN_CHOICES],
            state="readonly",
            width=12,
        )
        quick_plan_selector.pack(side="left")

        def apply_quick_plan(_event=None):
            choice_text = quick_plan_var.get()
            if not choice_text.startswith("直到"):
                return
            choice = choice_text[len("直到"):]
            try:
                planned = quick_plan_until(choice)
            except ValueError:
                return
            pending_quick_plan[0] = choice
            schedule.clear()
            schedule.update(planned)
            schedule_configured[0] = True
            schedule_enabled_var.set(True)

        quick_plan_selector.bind("<<ComboboxSelected>>", apply_quick_plan)

        def save_assignment():
            value = editor.get("1.0", "end-1c").strip()
            if not value:
                messagebox.showwarning("输入无效", "作业内容不能为空。", parent=dialog)
                editor.focus_set()
                return
            current_now = datetime.now()
            now = current_now.isoformat(timespec="seconds")
            if pending_quick_plan[0] is not None:
                planned = quick_plan_until(pending_quick_plan[0], current_now)
                schedule.clear()
                schedule.update(planned)
            if editing:
                self._record_undo()
                self.assignment[subject][assignment_index]["assignment"] = value
                self.assignment[subject][assignment_index]["ignore_prefix"] = ignore_prefix_var.get()
                self.assignment[subject][assignment_index]["ignore_suffix"] = ignore_suffix_var.get()
                self.assignment[subject][assignment_index]["secondary"] = secondary_var.get()
                schedule["enabled"] = schedule_enabled_var.get()
                if schedule_configured[0] and schedule.get("root"):
                    self.assignment[subject][assignment_index]["schedule"] = schedule
                else:
                    self.assignment[subject][assignment_index].pop("schedule", None)
                self.assignment[subject][assignment_index]["date_modified"] = now
                selected_index = assignment_index
                self._context_status("已编辑", subject, value)
            else:
                self._record_undo()
                self.assignment[subject].append({
                    "assignment": value,
                    "hide": False,
                    "ignore_prefix": ignore_prefix_var.get(),
                    "ignore_suffix": ignore_suffix_var.get(),
                    "secondary": secondary_var.get(),
                    "date_modified": now,
                })
                schedule["enabled"] = schedule_enabled_var.get()
                if schedule_configured[0] and schedule.get("root"):
                    self.assignment[subject][-1]["schedule"] = schedule
                selected_index = len(self.assignment[subject]) - 1
                self._context_status("已添加", subject, value)
            refresh_scheduled_assignments(self.assignment)
            self.refresh_assignments(selected_index)
            dialog.destroy()

        buttons = ttk.Frame(form)
        buttons.grid(row=4, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(buttons, text="确定", command=save_assignment).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.after_idle(editor.focus_set)
        place_window_bottom_right(dialog)

    def _schedule_rules_dialog(self, parent, schedule, on_confirm=None):
        schedule_target = schedule if isinstance(schedule, dict) else None
        if isinstance(schedule, dict) and isinstance(schedule.get("root"), dict):
            schedule = copy.deepcopy(schedule)
        else:
            schedule = {"enabled": True, "root": {"type": "all", "children": []}}

        window = tk.Toplevel(parent)
        window.title("配置计划")
        window.transient(parent)
        window.grab_set()
        configure_tk_scaling(window)

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, show="tree", height=14)
        tree.pack(fill="both", expand=True)

        def node_label(node):
            node_type = node.get("type")
            if node_type == "interval":
                start = node.get("start") or "无限开始"
                end = node.get("end") or "无限结束"
                return "时限区间：{} 至 {}".format(start, end)
            if node_type == "calendar":
                names = {"day": "日", "week": "周", "month": "月"}
                unit = names.get(node.get("unit"), str(node.get("unit")))
                parts = []
                selectors = node.get("selectors", {})
                if selectors.get("weekdays"):
                    parts.append("星期{}".format(",".join(str(v) for v in selectors["weekdays"])))
                if selectors.get("month_days"):
                    parts.append("日期{}".format(",".join(str(v) for v in selectors["month_days"])))
                if selectors.get("months"):
                    parts.append("月份{}".format(",".join(str(v) for v in selectors["months"])))
                if selectors.get("week_of_month"):
                    parts.append("第{}周".format(",".join(str(v) for v in selectors["week_of_month"])))
                return "日历周期：{}".format(unit + ("；" + "、".join(parts) if parts else ""))
            if node_type == "time_window":
                return "时间窗口：{} 至 {}".format(node.get("start") or "00:00:00", node.get("end") or "24:00:00")
            if node_type == "any":
                return "∃ 满足任何"
            if node_type == "all":
                return "∀ 满足所有"
            return str(node_type)

        def get_node(path):
            node = schedule["root"]
            if path == "0":
                return node
            for index_text in path.split(".")[1:]:
                node = node.setdefault("children", [])[int(index_text)]
            return node

        def get_parent(path):
            if path == "0":
                return None
            parts = path.split(".")
            parent_path = ".".join(parts[:-1])
            node = get_node(parent_path)
            return node, int(parts[-1])

        def redraw():
            tree.delete(*tree.get_children())
            def add_branch(node, parent, iid):
                tree.insert(parent, "end", iid=iid, text=node_label(node), open=True)
                children = node.get("children", [])
                if isinstance(children, list):
                    for index, child in enumerate(children):
                        add_branch(child, iid, "{}.{}".format(iid, index))
            add_branch(schedule["root"], "", "0")
            tree.update_idletasks()

        def edit_node(existing=None, create=False, on_changed=None):
            d = tk.Toplevel(window)
            d.title("编辑规则节点" if existing is not None else "添加规则节点")
            d.transient(window)
            d.grab_set()
            configure_tk_scaling(d)
            f = ttk.Frame(d, padding=12)
            f.pack(fill="both", expand=True)
            existing = existing or {"type": "interval", "children": []}

            type_var = tk.StringVar(value=existing.get("type", "interval"))
            ttk.Label(f, text="节点类型").grid(row=0, column=0, sticky="w", pady=3)
            type_box = ttk.Combobox(
                f,
                textvariable=type_var,
                values=("时限区间", "日历循环", "时间窗口", "∃ 满足任何", "∀ 满足所有"),
                state="readonly",
                width=18,
            )
            type_box.grid(row=0, column=1, sticky="w", pady=3)
            type_names = {
                "时限区间": "interval",
                "日历循环": "calendar",
                "时间窗口": "time_window",
                "∃ 满足任何": "any",
                "∀ 满足所有": "all",
            }

            fields = ttk.Frame(f)
            fields.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 6))
            start_var = tk.StringVar(value=existing.get("start", ""))
            end_var = tk.StringVar(value=existing.get("end", ""))
            unit_var = tk.StringVar(value=existing.get("unit", "week"))
            weekday_vars = {day: tk.BooleanVar(value=False) for day in range(1, 8)}
            month_day_vars = {day: tk.BooleanVar(value=False) for day in range(1, 32)}
            week_vars = {week: tk.BooleanVar(value=False) for week in range(1, 6)}
            selectors = existing.get("selectors", {})
            if isinstance(selectors, dict):
                for day in selectors.get("weekdays", []):
                    if day in weekday_vars:
                        weekday_vars[day].set(True)
                for day in selectors.get("month_days", []):
                    if day in month_day_vars:
                        month_day_vars[day].set(True)
                for week in selectors.get("week_of_month", []):
                    if week in week_vars:
                        week_vars[week].set(True)

                weekday_widgets = {}

                def sync_month_week_selection(*_):
                    enabled = any(var.get() for var in week_vars.values())
                    if enabled:
                        for var in month_day_vars.values():
                            var.set(False)
                    else:
                        for var in weekday_vars.values():
                            var.set(False)
                    for widget in weekday_widgets.values():
                        widget.configure(state="normal" if enabled else "disabled")

            def clear_month_week_selection(*_):
                if any(var.get() for var in month_day_vars.values()):
                    for var in week_vars.values():
                        var.set(False)
                        for var in weekday_vars.values():
                            var.set(False)

            def rebuild(*_):
                for child in fields.winfo_children():
                    child.destroy()
                node_type = type_names.get(type_var.get(), existing.get("type", "interval"))
                if node_type == "interval":
                    ttk.Label(fields, text="开始（YYYY-MM-DD HH:MM:SS，留空不限）").grid(row=0, column=0, sticky="w")
                    ttk.Entry(fields, textvariable=start_var, width=28).grid(row=1, column=0, sticky="w", pady=3)
                    ttk.Label(fields, text="结束（左闭右开，留空不限）").grid(row=2, column=0, sticky="w")
                    ttk.Entry(fields, textvariable=end_var, width=28).grid(row=3, column=0, sticky="w", pady=3)
                elif node_type == "calendar":
                    ttk.Label(fields, text="周期").grid(row=0, column=0, sticky="w")
                    ttk.Combobox(fields, textvariable=unit_var, values=("day", "week", "month"), state="readonly", width=12).grid(row=0, column=1, sticky="w")

                    weekday_names = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
                    if unit_var.get() == "week":
                        ttk.Label(fields, text="星期").grid(row=1, column=0, sticky="w", pady=(6, 2))
                        weekday_row = ttk.Frame(fields)
                        weekday_row.grid(row=2, column=0, columnspan=2, sticky="w")
                        for day, name in enumerate(weekday_names, start=1):
                            ttk.Checkbutton(weekday_row, text=name, variable=weekday_vars[day]).pack(side="left", padx=(0, 8))

                    if unit_var.get() == "month":
                        ttk.Label(fields, text="第几周").grid(row=3, column=0, sticky="w", pady=(8, 2))
                        week_row = ttk.Frame(fields)
                        week_row.grid(row=4, column=0, columnspan=2, sticky="w")
                        for week in range(1, 6):
                            var = week_vars[week]
                            var.trace_add("write", sync_month_week_selection)
                            ttk.Checkbutton(week_row, text="第{}周".format(week), variable=var).pack(side="left", padx=(0, 8))

                        ttk.Label(fields, text="周几").grid(row=5, column=0, sticky="w", pady=(8, 2))
                        weekday_row = ttk.Frame(fields)
                        weekday_row.grid(row=6, column=0, columnspan=2, sticky="w")
                        weekday_widgets.clear()
                        for day, name in enumerate(weekday_names, start=1):
                            widget = ttk.Checkbutton(
                                weekday_row,
                                text=name,
                                variable=weekday_vars[day],
                            )
                            widget.pack(side="left", padx=(0, 8))
                            weekday_widgets[day] = widget

                        ttk.Label(fields, text="几号").grid(row=7, column=0, sticky="w", pady=(8, 2))
                        day_row = ttk.Frame(fields)
                        day_row.grid(row=8, column=0, columnspan=2, sticky="w")
                        for day in range(1, 32):
                            var = month_day_vars[day]
                            var.trace_add("write", clear_month_week_selection)
                            ttk.Checkbutton(day_row, text=str(day), variable=var).grid(
                                row=(day - 1) // 8,
                                column=(day - 1) % 8,
                                sticky="w",
                                padx=(0, 8),
                                pady=1,
                            )
                        sync_month_week_selection()
                elif node_type == "time_window":
                    ttk.Label(fields, text="开始时刻（HH:MM:SS）").grid(row=0, column=0, sticky="w")
                    ttk.Entry(fields, textvariable=start_var, width=28).grid(row=1, column=0, sticky="w")
                    ttk.Label(fields, text="结束时刻（左闭右开）").grid(row=2, column=0, sticky="w")
                    ttk.Entry(fields, textvariable=end_var, width=28).grid(row=3, column=0, sticky="w")
                else:
                    ttk.Label(fields, text="此节点用于组合子节点；∃ 满足任何表示满足其一，∀ 满足所有表示全部生效。").grid(row=0, column=0, sticky="w")

            reverse_types = {value: key for key, value in type_names.items()}
            type_var.set(reverse_types.get(existing.get("type", "interval"), "时限区间"))
            type_var.trace_add("write", rebuild)
            unit_var.trace_add("write", rebuild)
            rebuild()

            def accept():
                node_type = type_names.get(type_var.get(), "interval")
                children = copy.deepcopy(existing.get("children", []))
                node = {"type": node_type, "children": children}
                if node_type == "interval":
                    node["start"] = start_var.get().strip() or None
                    node["end"] = end_var.get().strip() or None
                    if node["start"] is not None and parse_datetime(node["start"]) is None:
                        messagebox.showwarning("输入无效", "开始时刻格式应为 YYYY-MM-DD HH:MM:SS", parent=d)
                        return
                    if node["end"] is not None and parse_datetime(node["end"]) is None:
                        messagebox.showwarning("输入无效", "结束时刻格式应为 YYYY-MM-DD HH:MM:SS", parent=d)
                        return
                elif node_type == "calendar":
                    node.update(unit=unit_var.get())
                    selectors = {}
                    weekdays = [day for day, var in weekday_vars.items() if var.get()]
                    month_days = [day for day, var in month_day_vars.items() if var.get()]
                    weeks = [week for week, var in week_vars.items() if var.get()]
                    if unit_var.get() == "month" and not weeks:
                        weekdays = []
                    if weekdays:
                        selectors["weekdays"] = weekdays
                    if month_days:
                        selectors["month_days"] = month_days
                    if weeks:
                        selectors["week_of_month"] = weeks
                    node["selectors"] = selectors
                elif node_type == "time_window":
                    node["start"] = start_var.get().strip() or "00:00:00"
                    node["end"] = end_var.get().strip() or "24:00:00"
                    if node["start"] != "24:00:00" and parse_time(node["start"]) is None:
                        messagebox.showwarning("输入无效", "开始时刻格式应为 HH:MM:SS", parent=d)
                        return
                    if node["end"] != "24:00:00" and parse_time(node["end"]) is None:
                        messagebox.showwarning("输入无效", "结束时刻格式应为 HH:MM:SS", parent=d)
                        return
                    if node["start"] != "24:00:00" and node["end"] != "24:00:00":
                        if parse_time(node["end"]) <= parse_time(node["start"]):
                            messagebox.showwarning("输入无效", "结束时刻必须晚于开始时刻", parent=d)
                            return
                d.destroy()
                existing.clear()
                existing.update(node)
                if on_changed is not None:
                    on_changed()

            ttk.Button(f, text="确定", command=accept).grid(row=2, column=1, sticky="e", pady=(10, 0))
            ttk.Button(f, text="取消", command=d.destroy).grid(row=2, column=0, sticky="w", pady=(10, 0))
            set_window_size_percent(d, 32, 55)
            place_window_bottom_right(d)

        def selected_node():
            selection = tree.selection()
            if not selection:
                return None, None
            path = selection[0]
            return path, get_node(path)

        def add_child():
            path, parent = selected_node()
            if parent is None:
                return
            node = {"type": "interval", "start": None, "end": None, "children": []}
            def changed():
                parent.setdefault("children", []).append(node)
                redraw()
            edit_node(node, create=True, on_changed=changed)

        def edit_selected():
            path, node = selected_node()
            if node is not None:
                edit_node(node, on_changed=redraw)

        def delete_selected():
            path, node = selected_node()
            if path is None or path == "0":
                messagebox.showwarning("无法删除", "根节点不能删除，可以编辑根节点类型。", parent=window)
                return
            parent, index = get_parent(path)
            del parent["children"][index]
            redraw()

        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(bar, text="编辑节点", command=edit_selected).pack(side="left")
        ttk.Button(bar, text="添加子节点", command=add_child).pack(side="left", padx=6)
        ttk.Button(bar, text="删除节点", command=delete_selected).pack(side="left")

        def confirm():
            if schedule_target is not None:
                schedule_target.clear()
                schedule_target.update(copy.deepcopy(schedule))
            if on_confirm is not None:
                on_confirm()
            window.destroy()

        ttk.Button(bar, text="确定", command=confirm).pack(side="right")
        redraw()
        set_window_size_percent(window, 38, 55)
        place_window_bottom_right(window)

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
            messagebox.showwarning("未选择作业", "请先选择要编辑的作业项。", parent=self.root)
            return
        self._open_assignment_dialog(selection[0])

    def _selected_assignment(self):
        subject = self.selected_subject.get()
        selection = self.assignment_list.curselection()
        if not subject or not selection:
            messagebox.showwarning("未选择作业", "请先选择要操作的作业。", parent=self.root)
            return None, None, None
        index = selection[0]
        return subject, index, self.assignment[subject][index]

    def copy_assignment(self):
        subject, index, assignment = self._selected_assignment()
        if assignment is None:
            return
        self._record_undo()
        duplicate = copy.deepcopy(assignment)
        duplicate["date_modified"] = datetime.now().isoformat(timespec="seconds")
        self.assignment[subject].insert(index + 1, duplicate)
        self.refresh_assignments(index + 1)
        self._context_status("已复制", subject, duplicate.get("assignment"))

    def move_assignment_subject(self):
        source, index, assignment = self._selected_assignment()
        if assignment is None:
            return
        subjects = list(self.assignment)
        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("移动作业")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="移动到科目：").pack(anchor="w", pady=(0, 6))
        choices = [SUBJECT_NAMES.get(subject, subject) for subject in subjects]
        target_var = tk.StringVar(value=SUBJECT_NAMES.get(source, source))
        selector = ttk.Combobox(frame, state="readonly", values=choices, textvariable=target_var)
        selector.pack(fill="x")
        def confirm():
            target = subjects[choices.index(target_var.get())]
            dialog.destroy()
            if target == source:
                return
            self._record_undo()
            moved = self.assignment[source].pop(index)
            moved["date_modified"] = datetime.now().isoformat(timespec="seconds")
            self.assignment.setdefault(target, []).append(moved)
            self.refresh_subjects(target)
            self.refresh_assignments(len(self.assignment[target]) - 1)
            self._context_status("已移动", target, moved.get("assignment"))
        buttons = ttk.Frame(frame); buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="确定", command=confirm).pack(side="right")
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right", padx=(0, 6))
        configure_tk_scaling(dialog); place_window_bottom_right(dialog)

    def toggle_assignment(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not selection or not subject:
            messagebox.showwarning("未选择作业", "请先选择要切换显示状态的作业项。", parent=self.root)
            return
        index = selection[0]
        assignment = self.assignment[subject][index]
        schedule = assignment.get("schedule")
        if isinstance(schedule, dict) and schedule.get("enabled", True):
            return
        self._record_undo()
        assignment["hide"] = not assignment["hide"]
        assignment["date_modified"] = datetime.now().isoformat(timespec="seconds")
        self.refresh_assignments(index)
        state = "已隐藏" if assignment["hide"] else "已显示"
        self._context_status(state, subject, assignment["assignment"])

    def toggle_all_assignments(self):
        subject = self.selected_subject.get()
        assignments = self.assignment.get(subject, []) if subject else []
        if not assignments:
            return
        show_all = any(assignment["hide"] for assignment in assignments)
        self._record_undo()
        now = datetime.now().isoformat(timespec="seconds")
        for assignment in assignments:
            schedule = assignment.get("schedule")
            if isinstance(schedule, dict) and schedule.get("enabled", True):
                continue
            if assignment["hide"] != (not show_all):
                assignment["hide"] = not show_all
                assignment["date_modified"] = now
        self.refresh_assignments()
        self._context_status(
            "已显示" if show_all else "已隐藏", subject, "全部作业"
        )

    def delete_assignment(self):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not subject or not selection:
            messagebox.showwarning("未选择作业", "请先选择要删除的作业项。", parent=self.root)
            return
        if not messagebox.askyesno("确认删除", "确定删除选中的作业项吗？", parent=self.root):
            return
        index = selection[0]
        assignment = self.assignment[subject][index]["assignment"]
        self._record_undo()
        del self.assignment[subject][index]
        self.refresh_assignments(index)
        self._context_status("已删除", subject, assignment)
        dialog = getattr(self, "all_actions_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
            self.all_actions_dialog = None

    def delete_all_assignments(self):
        subject = self.selected_subject.get()
        assignments = self.assignment.get(subject, []) if subject else []
        if not assignments:
            return
        if not messagebox.askyesno("确认删除", "确定删除 {} 中的所有作业吗？此操作可撤销。".format(self._subject_name(subject)), parent=self.root):
            return
        self._record_undo()
        self.assignment[subject] = []
        self.refresh_assignments()
        self._context_status("已删除全部作业", subject, "全部作业")
        dialog = getattr(self, "all_actions_dialog", None)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
            self.all_actions_dialog = None

    def _move_assignment(self, direction):
        selection = self.assignment_list.curselection()
        subject = self.selected_subject.get()
        if not selection or not subject:
            return
        index = selection[0]
        assignments = self.assignment[subject]
        new_index = index + direction
        if new_index < 0 or new_index >= len(assignments):
            return
        assignment = assignments[index]["assignment"]
        self._record_undo()
        assignments[index], assignments[new_index] = assignments[new_index], assignments[index]
        now = datetime.now().isoformat(timespec="seconds")
        assignments[index]["date_modified"] = now
        assignments[new_index]["date_modified"] = now
        self.refresh_assignments(new_index)
        state = "已上置" if direction < 0 else "已下置"
        self._context_status(state, subject, assignment)

    def move_up_assignment(self):
        self._move_assignment(-1)

    def move_down_assignment(self):
        self._move_assignment(1)

    def save(self):
        if not self._dirty:
            return
        try:
            refresh_scheduled_assignments(self.assignment)
            save_assignment(self.assignment)
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("保存失败", str(error), parent=self.root)
            return
        self._dirty = False
        self._update_save_button()
        self._context_status("已保存到 assignment.json")
        self.refresh_assignments()
        notify_config_saved()
        show_windows_notification("已保存各科所有作业", "保存完成")


def main():
    enable_high_dpi()
    from runtime import acquire_single_instance
    if not acquire_single_instance("assignment_editor"):
        return
    root = tk.Tk()
    try:
        editor(root)
        place_window_bottom_right(root)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("加载失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
