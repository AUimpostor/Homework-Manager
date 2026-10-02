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
import os
import subprocess
import sys
import tkinter as tk
import threading
import webbrowser
import winreg
from pathlib import Path
from tkinter import colorchooser, messagebox, ttk
from HWMRuntime import (
    close_config_reload_event,
    close_shutdown_event,
    configure_tk_scaling,
    create_config_reload_event,
    request_main_action,
    create_shutdown_event,
    enable_high_dpi,
    enable_touch_keyboard,
    set_window_size_percent,
    notify_config_saved,
    wait_for_config_reload,
    wait_for_shutdown,
    set_window_icon,
)
from HWMConfig import DEFAULT_CONFIG, load_config, load_homework_data, save_config


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = APPLICATION_DIR
CONFIG_FILE = RESOURCE_DIR / "config.json"
HOMEWORK_FILE = RESOURCE_DIR / "homework.json"
LICENSE_BUNDLE_DIR = (
    Path(getattr(sys, "_MEIPASS", APPLICATION_DIR)) / "distribution-licenses"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR
)
EDITOR_FILE = (
    APPLICATION_DIR / "Homework Manager.exe"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR / "HomeworkEditor.py"
)
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
INTEGER_FIELDS = (
    "title_width_permill", "title_length_permill", "title_font_size", "project_font_size", "secondary_project_font_size",
    "title_guide_line_width_permill",
    "title_outline_opacity",
    "editor_width_percent", "editor_height_percent",
    "display_range_left_percent", "display_range_right_percent", "display_range_top_percent",
    "display_range_bottom_percent", "content_padding_x_permill", "content_padding_y_permill",
    "section_spacing_permill", "scroll_start_delay", "scroll_step_interval",
    "scroll_end_pause", "restart_pause", "fade_interval",
)
FLOAT_FIELDS = ("window_alpha", "scroll_step_size", "fade_step")
BOOLEAN_FIELDS = ("auto_start_display",)
TRAY_CLICK_OPTIONS = {
    "dashboard": "仪表盘",
    "homework_editor": "项目编辑器",
    "menu": "右键菜单",
}
SELECT_FIELDS = ("tray_click_action", "title_theme", "title_alignment", "project_alignment")
TITLE_THEMES = {
    "默认": "默认",
    "圆角标签": "圆角标签",
    "左侧标记": "左侧标记",
    "底边强调": "底边强调",
    "顶面强调": "顶面强调",
    "角标标题": "角标标题",
}
SELECT_OPTIONS = {
    "tray_click_action": TRAY_CLICK_OPTIONS,
    "title_theme": {name: name for name in TITLE_THEMES},
    "title_alignment": {"靠左": "靠左", "靠右": "靠右"},
    "project_alignment": {"靠左": "靠左", "靠右": "靠右"},
}
COLOR_FIELDS = (
    "title_font_color", "project_font_color", "secondary_project_font_color", "title_primary_color",
    "title_secondary_color",
)
FIELD_LABELS = {
    "title_width_permill": "标题宽度（‰）",
    "title_length_permill": "标题高度（‰）",
    "title_font_size": "标题字号（size）",
    "project_font_size": "项目字号（size）",
    "secondary_project_font_size": "次要项目字号（size）",
    "title_font_color": "标题字体颜色",
    "project_font_color": "项目字体颜色",
    "secondary_project_font_color": "次要项目字体颜色",
    "title_theme": "标题主题",
    "title_alignment": "标题排版",
    "project_alignment": "项目排版",
    "title_primary_color": "标题主要颜色",
    "title_secondary_color": "标题次要颜色",
    "title_outline_opacity": "描边透明度（%）",
    "title_guide_line_width_permill": "标题引导线粗（‰）",
    "auto_start_display": "开机时自动启动显示器",
    "tray_click_action": "点击系统托盘图标时",
    "school": "学校",
    "class": "班级",
    "project_prefix": "项目前缀",
    "project_suffix": "项目后缀",
    "editor_width_percent": "项目编辑器宽度（%）",
    "editor_height_percent": "项目编辑器高度（%）",
    "display_range_left_percent": "显示区域：左（%）",
    "display_range_right_percent": "显示区域：右（%）",
    "display_range_top_percent": "显示区域：上（%）",
    "display_range_bottom_percent": "显示区域：下（%）",
    "window_alpha": "窗口透明度（0.1~1）",
    "content_padding_x_permill": "内容水平边距（‰）",
    "content_padding_y_permill": "内容垂直边距（‰）",
    "section_spacing_permill": "科目间距（‰）",
    "scroll_start_delay": "首次滚动前停顿（ms）",
    "scroll_step_interval": "滚动间隔（ms）",
    "scroll_step_size": "每次滚动幅度",
    "scroll_end_pause": "滚动到末尾停留（ms）",
    "restart_pause": "回到顶部后停留（ms）",
    "fade_interval": "淡入淡出间隔（ms）",
    "fade_step": "淡入淡出步长",
}
COLOR_PRESETS = (
    ("浅灰", "#F5F5F5"),
    ("灰色", "#808080"),
    ("深灰色", "#A9A9A9"),
    ("白色", "#FFFFFF"),
    ("深蓝", "#315E7D"),
    ("水蓝", "#4C8DB4"),
    ("浅蓝", "#CFE8FF"),
    ("浅黄", "#FFF2A8"),
    ("浅绿", "#C8F7C5"),
    ("浅粉", "#FFD6E7"),
)
CONFIG_GROUPS = (
    (
        "首选项",
        (
            ("", ("auto_start_display", "tray_click_action")),
            ("信息", ("school", "class")),
        ),
    ),
    (
        "显示器格式",
        (
            (
                "标题",
                (
                    "title_width_permill",
                    "title_length_permill",
                    "title_font_size",
                    "title_alignment",
                    "title_theme",
                    "title_font_color",
                    "title_primary_color",
                    "title_secondary_color",
                    "title_outline_opacity",
                    "title_guide_line_width_permill",
                ),
            ),
            (
                "项目",
                (
                    "project_alignment",
                    "project_font_size",
                    "project_font_color",
                    "project_prefix",
                    "project_suffix",
                ),
            ),
            (
                "次要项目",
                (
                    "secondary_project_font_size",
                    "secondary_project_font_color",
                ),
            ),
        ),
    ),
    (
        "显示",
        (
            (
                "窗口",
                (
                    "editor_width_percent",
                    "editor_height_percent",
                ),
            ),
            (
                "显示器",
                (
                    "display_range_left_percent",
                    "display_range_right_percent",
                    "display_range_top_percent",
                    "display_range_bottom_percent",
                    "window_alpha",
                    "content_padding_x_permill",
                    "content_padding_y_permill",
                    "section_spacing_permill",
                ),
            ),
            (
                "动画",
                (
                    "scroll_start_delay",
                    "scroll_step_interval",
                    "scroll_step_size",
                    "scroll_end_pause",
                    "restart_pause",
                    "fade_interval",
                    "fade_step",
                ),
            ),
        ),
    ),
)
STARTUP_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "main"







def load_document():
    config = load_config(CONFIG_FILE)
    data = load_homework_data(HOMEWORK_FILE, CONFIG_FILE)
    return config, data


def save_document(config):
    save_config(CONFIG_FILE, config)


def get_display_startup_command():
    if getattr(sys, "frozen", False):
        main_file = APPLICATION_DIR / "Homework Manager.exe"
        return subprocess.list2cmdline([str(main_file)])
    main_file = APPLICATION_DIR / "main.py"
    python_executable = Path(sys.executable).with_name("pythonw.exe")
    if not python_executable.exists():
        python_executable = Path(sys.executable)
    return subprocess.list2cmdline([str(python_executable), str(main_file)])


def update_display_startup(enabled):
    if sys.platform != "win32":
        return
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        STARTUP_REGISTRY_PATH,
        0,
        winreg.KEY_SET_VALUE,
    ) as startup_key:
        if enabled:
            winreg.SetValueEx(
                startup_key,
                STARTUP_VALUE_NAME,
                0,
                winreg.REG_SZ,
                get_display_startup_command(),
            )
        else:
            try:
                winreg.DeleteValue(startup_key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass


class ConfigEditor:
    def __init__(self, root):
        self.root = root
        enable_touch_keyboard(root)
        set_window_icon(root, __file__)
        self.root.title("Homework Manager 仪表盘")
        self.config, self.data = load_document()
        configure_tk_scaling(root)
        set_window_size_percent(
            root,
            40,
            40,
            lock_minimum=True,
        )
        self.variables = {}
        self.color_previews = {}
        self.color_selectors = {}
        self.guide_width_widgets = []
        self.status = tk.StringVar(value="就绪")
        self.create_widgets()
        self.load_values()
        self.reload_event = create_config_reload_event("config_editor")
        self.shutdown_event = create_shutdown_event("config_editor")
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
            self.root.after(0, self.reload_from_disk)
            threading.Thread(target=self.wait_for_reload, daemon=True).start()

    def reload_from_disk(self):
        try:
            self.config, self.data = load_document()
            self.load_values()
            self.status.set("已从 config.json 刷新配置")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.status.set("刷新失败：{}".format(error))

    def create_widgets(self):
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        main = ttk.Frame(canvas, padding=10)
        canvas_window = canvas.create_window((0, 0), window=main, anchor="nw")
        main.columnconfigure(1, weight=1)

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_content_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        main.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_content_width)

        def on_mousewheel(event):
            widget = getattr(event, "widget", None)
            if widget is not None and widget.winfo_class() in ("TCombobox", "Listbox"):
                return
            if getattr(event, "delta", 0):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Button-4>", on_mousewheel)
        canvas.bind("<Button-5>", on_mousewheel)
        self.root.bind_all("<MouseWheel>", on_mousewheel)
        self.root.bind_all("<Button-4>", on_mousewheel)
        self.root.bind_all("<Button-5>", on_mousewheel)

        ttk.Label(main, text="配置 Homework Manager", font=("Microsoft YaHei UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )
        row = 1
        for group_name, keys in CONFIG_GROUPS:
            if group_name == "首选项":
                ttk.Label(
                    main,
                    text="一些选项可能需要重启程序才能生效",
                    foreground="#666666",
                    font=("Microsoft YaHei UI", 9),
                ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
                row += 1
            ttk.Label(
                main,
                text=group_name,
                font=("Microsoft YaHei UI", 14, "bold"),
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
            row += 1
            if keys and isinstance(keys[0], tuple) and len(keys[0]) == 2 and isinstance(keys[0][0], str):
                subgroups = keys
            else:
                subgroups = (("", keys),)
            for subgroup_name, subgroup_keys in subgroups:
                if subgroup_name:
                    ttk.Label(
                        main,
                        text=subgroup_name,
                        font=("Microsoft YaHei UI", 11, "bold"),
                    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 1))
                    row += 1
                for key in subgroup_keys:
                    ttk.Label(main, text=FIELD_LABELS[key]).grid(
                        row=row, column=0, sticky="w", padx=(0, 14), pady=5
                    )
                    variable = tk.StringVar()
                    self.variables[key] = variable
                    label_widget = None
                    if key in BOOLEAN_FIELDS:
                        ttk.Checkbutton(
                            main,
                            text="启用",
                            variable=variable,
                            onvalue="True",
                            offvalue="False",
                        ).grid(row=row, column=1, sticky="w", pady=5)
                    elif key in SELECT_FIELDS:
                        selector = ttk.Combobox(
                            main,
                            state="readonly",
                            textvariable=variable,
                            values=list(SELECT_OPTIONS[key].values()),
                        )
                        selector.grid(row=row, column=1, sticky="ew", pady=5)
                        if key == "title_theme":
                            selector.bind("<<ComboboxSelected>>", self.apply_title_theme)
                    elif key in COLOR_FIELDS:
                        color_frame = ttk.Frame(main)
                        color_frame.grid(row=row, column=1, sticky="ew", pady=5)
                        color_frame.columnconfigure(1, weight=1)
                        color_preview = tk.Label(color_frame, width=3, relief="sunken")
                        color_preview.grid(row=0, column=0, padx=(0, 6))
                        self.color_previews[key] = color_preview
                        color_selector = ttk.Combobox(
                            color_frame,
                            state="readonly",
                            values=[name for name, _color in COLOR_PRESETS],
                        )
                        color_selector.grid(row=0, column=1, sticky="ew")
                        self.color_selectors[key] = color_selector
                        color_selector.bind(
                            "<<ComboboxSelected>>",
                            lambda _event, color_key=key: self.select_preset_color(color_key),
                        )
                        ttk.Button(
                            color_frame,
                            text="自定义颜色...",
                            command=lambda color_key=key: self.choose_custom_color(color_key),
                        ).grid(row=0, column=2, padx=(6, 0))
                    else:
                        entry = ttk.Entry(main, textvariable=variable)
                        entry.grid(
                            row=row, column=1, sticky="ew", pady=5
                        )
                    if key == "title_guide_line_width_permill":
                        label_widget = main.grid_slaves(row=row, column=0)[0]
                        self.guide_width_widgets = [label_widget, entry]
                    row += 1

        ttk.Separator(main, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(12, 8)
        )
        row += 1
        ttk.Label(
            main,
            text="关于",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
        row += 1
        about_title = ttk.Frame(main)
        about_title.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        app_name_label = ttk.Label(
            about_title,
            text="Homework Manager",
            foreground="#1769AA",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "underline"),
        )
        app_name_label.pack(side="left")
        app_name_label.bind(
            "<Button-1>",
            lambda _event: webbrowser.open("https://github.com/AUimpostor/Homework-Manager"),
        )
        ttk.Label(about_title, text=" v1.5").pack(side="left")
        row += 1
        ttk.Label(
            main,
            text="适用于信息化教学的简单作业显示工具\n\nCopyright (C) 2026 AUimpostor <auimpostor@outlook.com>",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 3))
        row += 1
        license_links = ttk.Frame(main)
        license_links.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        for label_text, filename in (
            ("GPL 许可证", "LICENSE.md"),
            ("第三方许可声明", "THIRD_PARTY_NOTICES.md"),
        ):
            link = ttk.Label(
                license_links,
                text=label_text,
                foreground="#1769AA",
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "underline"),
            )
            link.pack(side="left", padx=(0, 14))
            link.bind(
                "<Button-1>",
                lambda _event, name=filename: self.open_license_file(name),
            )
        row += 1
        details_link = ttk.Label(
            main,
            text="所有许可文件",
            foreground="#1769AA",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "underline"),
        )
        details_link.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        details_link.bind("<Button-1>", lambda _event: self.open_license_folder())

        bottom = ttk.Frame(outer)
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status).grid(
            row=0, column=0, sticky="w"
        )
        buttons = ttk.Frame(bottom)
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="保存配置", command=self.save).pack(side="left")
        ttk.Button(buttons, text="预览项目...", command=self.show_compact_homework).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="推送管理器...", command=self.open_subscription_manager).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="项目编辑器...", command=self.open_homework_editor).pack(
            side="right", padx=(8, 0)
        )
        control_buttons = ttk.Frame(outer)
        control_buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(
            control_buttons, text="退出", command=self.exit_hwm
        ).pack(side="left")

    def open_license_file(self, filename):
        path = LICENSE_BUNDLE_DIR / filename
        if not path.is_file():
            messagebox.showerror("无法打开", "找不到许可文件：{}".format(path), parent=self.root)
            return
        try:
            os.startfile(str(path))
        except OSError as error:
            messagebox.showerror("无法打开", str(error), parent=self.root)

    def open_license_folder(self):
        if not LICENSE_BUNDLE_DIR.is_dir():
            messagebox.showerror("无法打开", "找不到内嵌许可文件目录。", parent=self.root)
            return
        try:
            os.startfile(str(LICENSE_BUNDLE_DIR))
        except OSError as error:
            messagebox.showerror("无法打开", str(error), parent=self.root)

    def exit_hwm(self):
        request_main_action("exit")

    def show_compact_homework(self):
        compact_window = tk.Toplevel(self.root)
        set_window_icon(compact_window, __file__, default_only=False)
        compact_window.title("预览项目")
        screen_width = compact_window.winfo_screenwidth()
        screen_height = compact_window.winfo_screenheight()
        width = min(max(1, screen_width - 40), max(280, round(screen_width * 0.42)), 560)
        height = min(max(1, screen_height - 80), max(240, round(screen_height * 0.78)), 820)
        left = max(0, (screen_width - width) // 2)
        top = max(0, (screen_height - height) // 2)
        compact_window.geometry("{}x{}+{}+{}".format(width, height, left, top))
        compact_window.minsize(min(280, width), min(240, height))
        compact_window.transient(self.root)
        compact_window.attributes("-topmost", True)
        compact_window.lift()
        compact_window.focus_force()
        compact_window.rowconfigure(0, weight=1)
        compact_window.columnconfigure(0, weight=1)

        text_frame = ttk.Frame(compact_window)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_widget = tk.Text(
            text_frame, wrap=tk.WORD, padx=12, pady=12, state="disabled",
            font=("Microsoft YaHei UI", 14),
        )
        text_widget.grid(row=0, column=0, sticky="nsew")
        text_scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=text_widget.yview
        )
        text_scrollbar.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=text_scrollbar.set)

        def apply_font_size():
            try:
                current_config = self.read_config()
            except ValueError:
                current_config = self.config
            alignment = "left" if current_config.get("display_range_left_percent", 55) < 50 else "right"
            text_widget.configure(font=("Microsoft YaHei UI", 14))
            text_widget.tag_configure(
                "subject_heading",
                font=("Microsoft YaHei UI", 18, "bold"),
                justify=alignment,
            )
            text_widget.tag_configure("project", font=("Microsoft YaHei UI", 14), justify=alignment)
            text_widget.tag_configure("secondary_project", font=("Microsoft YaHei UI", 11), justify=alignment)
            text_widget.tag_configure("project_spacer", justify=alignment)

        try:
            preview_config = self.read_config()
        except ValueError:
            preview_config = self.config
        preview_sections = []
        for subject_work in self.data:
            for subject, assignments in subject_work.items():
                visible_assignments = [
                    item
                    for item in assignments
                    if not item.get("hide", False)
                ]
                if not visible_assignments:
                    continue
                preview_sections.append((SUBJECT_NAMES.get(subject, subject), visible_assignments))
        text_widget.configure(state="normal")
        if preview_sections:
            for subject_name, visible_assignments in preview_sections:
                text_widget.insert(tk.END, "{}\n".format(subject_name), "subject_heading")
                for item in visible_assignments:
                    prefix = "" if item.get("ignore_prefix", False) else preview_config.get("project_prefix", "")
                    suffix = "" if item.get("ignore_suffix", False) else preview_config.get("project_suffix", "")
                    project = "{}{}{}".format(prefix, item.get("project", ""), suffix)
                    tag = "secondary_project" if item.get("secondary", False) else "project"
                    text_widget.insert(tk.END, "  {}\n".format(project), tag)
                text_widget.insert(tk.END, "\n", "project_spacer")
        else:
            text_widget.insert("1.0", "（无可显示项目）")
        apply_font_size()
        text_widget.configure(state="disabled")

    def load_values(self):
        for key in DEFAULT_CONFIG:
            if key not in self.variables:
                continue
            value = self.config.get(key, DEFAULT_CONFIG[key])
            if key in SELECT_FIELDS:
                value = SELECT_OPTIONS[key].get(value, SELECT_OPTIONS[key][DEFAULT_CONFIG[key]])
            self.variables[key].set(str(value))
        for key in COLOR_FIELDS:
            self.update_color_preview(key)
        self.update_guide_width_visibility()

    def apply_title_theme(self, _event=None):
        self.update_guide_width_visibility()

    def update_guide_width_visibility(self):
        if not self.guide_width_widgets:
            return
        label, entry = self.guide_width_widgets
        if self.variables["title_theme"].get() in (
            "默认", "左侧标记", "底边强调", "顶面强调"
        ):
            label.grid()
            entry.grid()
        else:
            label.grid_remove()
            entry.grid_remove()

    def update_color_preview(self, key):
        color = self.variables[key].get()
        try:
            self.color_previews[key].configure(background=color)
        except tk.TclError:
            self.color_previews[key].configure(background=DEFAULT_CONFIG[key])
        for index, (_name, preset_color) in enumerate(COLOR_PRESETS):
            if color.upper() == preset_color.upper():
                self.color_selectors[key].current(index)
                return
        self.color_selectors[key].set("自定义颜色")

    def select_preset_color(self, key):
        index = self.color_selectors[key].current()
        if 0 <= index < len(COLOR_PRESETS):
            self.variables[key].set(COLOR_PRESETS[index][1])
            self.update_color_preview(key)

    def choose_custom_color(self, key):
        color = colorchooser.askcolor(
            color=self.variables[key].get(),
            parent=self.root,
            title="选择颜色",
        )[1]
        if color:
            self.variables[key].set(color.upper())
            self.update_color_preview(key)

    def read_config(self):
        config = self.config.copy()
        for key in BOOLEAN_FIELDS:
            config[key] = self.variables[key].get() == "True"
        for key in SELECT_FIELDS:
            selected_label = self.variables[key].get()
            selected_value = next(
                (value for value, label in SELECT_OPTIONS[key].items() if label == selected_label),
                DEFAULT_CONFIG[key],
            )
            config[key] = selected_value
        for key in INTEGER_FIELDS:
            try:
                value = int(self.variables[key].get().strip())
            except ValueError as error:
                raise ValueError("{} 必须是整数".format(FIELD_LABELS[key])) from error
            if key == "title_outline_opacity":
                if not 0 <= value <= 100:
                    raise ValueError("描边透明度必须在 0 到 100 之间")
            elif value < 1:
                raise ValueError("{} 必须大于 0".format(FIELD_LABELS[key]))
            config[key] = value
        for key in FLOAT_FIELDS:
            try:
                config[key] = float(self.variables[key].get().strip())
            except ValueError as error:
                raise ValueError("{} 必须是数字".format(FIELD_LABELS[key])) from error
        for key in (
            "editor_width_percent", "editor_height_percent",
        ):
            if not 10 <= config[key] <= 100:
                raise ValueError("{} 必须在 10 到 100 之间".format(FIELD_LABELS[key]))
        for key in (
            "display_range_left_percent", "display_range_right_percent", "display_range_top_percent", "display_range_bottom_percent",
        ):
            if not 0 <= config[key] <= 100:
                raise ValueError("{} 必须在 0 到 100 之间".format(FIELD_LABELS[key]))
        for key in (
            "title_width_permill", "title_length_permill", "title_guide_line_width_permill",
            "content_padding_x_permill", "content_padding_y_permill", "section_spacing_permill",
        ):
            if not 1 <= config[key] <= 1000:
                raise ValueError("{} 必须在 1 到 1000 之间".format(FIELD_LABELS[key]))
        if config["display_range_left_percent"] >= config["display_range_right_percent"]:
            raise ValueError("显示区域：左必须小于显示区域：右")
        if config["display_range_top_percent"] >= config["display_range_bottom_percent"]:
            raise ValueError("显示区域：上必须小于显示区域：下")
        if not 0.1 <= config["window_alpha"] <= 1:
            raise ValueError("窗口透明度必须在 0.1 到 1 之间")
        if not 0 < config["scroll_step_size"] <= 1:
            raise ValueError("每次滚动幅度必须大于 0 且不超过 1")
        if not 0 < config["fade_step"] <= 1:
            raise ValueError("淡入淡出步长必须大于 0 且不超过 1")
        for key in ("project_prefix", "project_suffix", "school", "class"):
            config[key] = self.variables[key].get()
        for key in COLOR_FIELDS:
            color = self.variables[key].get().strip()
            if not color:
                raise ValueError("{}不能为空".format(FIELD_LABELS[key]))
            try:
                self.root.winfo_rgb(color)
            except tk.TclError as error:
                raise ValueError("{}不是有效的颜色值".format(FIELD_LABELS[key])) from error
            config[key] = color
        return config

    def save(self):
        try:
            config = self.read_config()
            save_document(config)
            update_display_startup(config["auto_start_display"])
        except (OSError, TypeError, ValueError, winreg.error) as error:
            messagebox.showerror("保存失败", str(error), parent=self.root)
            return
        self.config = config
        self.status.set("已保存到 config.json")
        notify_config_saved()
        self.root.after_idle(self.reload_from_disk)

    def open_homework_editor(self):
        try:
            if EDITOR_FILE.suffix == ".py":
                subprocess.Popen([sys.executable, str(EDITOR_FILE)])
            else:
                subprocess.Popen([str(EDITOR_FILE), "--component", "homework_editor"])
        except OSError as error:
            messagebox.showerror("启动失败", str(error), parent=self.root)

    def open_subscription_manager(self):
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([str(EDITOR_FILE), "--component", "subscription_manager"])
            else:
                subprocess.Popen([sys.executable, str(APPLICATION_DIR / "HWMSubscriptionManager.py")])
        except OSError as error:
            messagebox.showerror("启动失败", str(error), parent=self.root)


def main():
    enable_high_dpi()
    root = tk.Tk()
    try:
        editor = ConfigEditor(root)
        if "--preview" in sys.argv:
            root.after(0, editor.show_compact_homework)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("加载失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()


