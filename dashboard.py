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
import ctypes
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tkinter as tk
import threading
import webbrowser
import winreg
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import colorchooser, messagebox, ttk
from runtime import (
    close_config_reload_event,
    close_shutdown_event,
    configure_tk_scaling,
    create_config_reload_event,
    request_main_action,
    create_shutdown_event,
    enable_high_dpi,
    enable_touch_keyboard,
    place_window_bottom_right,
    set_window_size_percent,
    notify_config_saved,
    show_windows_notification,
    wait_for_config_reload,
    wait_for_shutdown,
    set_window_icon,
)
from config import (
    DEFAULT_CONFIG,
    DISPLAY_ANIMATION_REGISTRY,
    BACKUP_EXTENSIONS,
    backup_directory,
    data_directory,
    ensure_backup_layout,
    load_config,
    load_assignment_data,
    next_backup_path,
    save_config,
    validate_backup_name,
    load_display_animation_params,
    save_display_animation_params,
    load_title_theme_params,
    save_title_theme_params,
)


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = APPLICATION_DIR
DATA_DIR = data_directory(RESOURCE_DIR)
CONFIG_BACKUP_DIR = backup_directory(RESOURCE_DIR, "config")
CUSTOM_BACKUP_DIR = backup_directory(RESOURCE_DIR, "custom")
ASSIGNMENT_BACKUP_DIR = backup_directory(RESOURCE_DIR, "assignment")
CUSTOM_DIR = DATA_DIR / "custom"
CONFIG_FILE = DATA_DIR / "config.json"
ASSIGNMENT_FILE = DATA_DIR / "assignment.json"
LICENSE_BUNDLE_DIR = (
    Path(getattr(sys, "_MEIPASS", APPLICATION_DIR)) / "distribution-licenses"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR
)
EDITOR_FILE = (
    APPLICATION_DIR / "Homework Manager.exe"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR / "editor.py"
)
INTEGER_FIELDS = (
    "title_width_permill", "title_length_permill", "title_font_size", "assignment_font_size", "secondary_assignment_font_size",
    "editor_width_percent", "editor_height_percent",
    "display_range_left_percent", "display_range_right_percent", "display_range_top_percent",
    "display_range_bottom_percent", "content_padding_x_permill", "content_padding_y_permill",
    "section_spacing_permill",
)
FLOAT_FIELDS = ("window_alpha",)
BOOLEAN_FIELDS = ("auto_start_display",)
TRAY_CLICK_OPTIONS = {
    "dashboard": "仪表盘",
    "assignment_editor": "作业编辑器",
    "menu": "右键菜单",
}
SELECT_FIELDS = ("tray_click_action", "open_action", "title_theme", "title_alignment", "assignment_alignment", "display_animation")
TITLE_THEMES = {
    "basic_color_block": "基础色块（默认）",
}
DISPLAY_ANIMATIONS = {
    name: spec["label"]
    for name, spec in DISPLAY_ANIMATION_REGISTRY.items()
}
OPEN_ACTION_OPTIONS = {
    "dashboard": "仪表盘",
    "assignment_editor": "作业编辑器",
}
SELECT_OPTIONS = {
    "tray_click_action": TRAY_CLICK_OPTIONS,
    "open_action": OPEN_ACTION_OPTIONS,
    "title_theme": TITLE_THEMES,
    "title_alignment": {"靠左": "靠左", "靠右": "靠右"},
    "assignment_alignment": {"靠左": "靠左", "靠右": "靠右"},
    "display_animation": DISPLAY_ANIMATIONS,
}
COLOR_FIELDS = (
    "assignment_font_color", "secondary_assignment_font_color",
)
FIELD_LABELS = {
    "title_width_permill": "标题宽度（‰）",
    "title_length_permill": "标题高度（‰）",
    "title_font_size": "标题字号（size）",
    "assignment_font_size": "作业字号（size）",
    "secondary_assignment_font_size": "次要作业字号（size）",
    "assignment_font_color": "作业字体颜色",
    "secondary_assignment_font_color": "次要作业字体颜色",
    "title_theme": "标题主题",
    "title_alignment": "标题排版",
    "assignment_alignment": "作业排版",
    "auto_start_display": "随 Windows 启动",
    "tray_click_action": "点击系统托盘图标时",
    "open_action": "打开 Homework Manager 时",
    "school": "学校",
    "class": "班级",
    "assignment_prefix": "作业前缀",
    "assignment_suffix": "作业后缀",
    "editor_width_percent": "作业编辑器宽度（%）",
    "editor_height_percent": "作业编辑器高度（%）",
    "display_range_left_percent": "显示区域：左（%）",
    "display_range_right_percent": "显示区域：右（%）",
    "display_range_top_percent": "显示区域：上（%）",
    "display_range_bottom_percent": "显示区域：下（%）",
    "window_alpha": "窗口透明度（0.1~1）",
    "content_padding_x_permill": "内容水平边距（‰）",
    "content_padding_y_permill": "内容垂直边距（‰）",
    "section_spacing_permill": "科目间距（‰）",
    "display_animation": "显示动画",
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
ANIMATION_PARAM_FIELDS = {
    name: spec["parameters"]
    for name, spec in DISPLAY_ANIMATION_REGISTRY.items()
}
TITLE_THEME_PARAM_FIELDS = {
    "basic_color_block": (
        ("title_font_color", "标题字体颜色", "color"),
        ("title_primary_color", "标题主要颜色", "color"),
        ("title_secondary_color", "标题次要颜色", "color"),
        ("title_outline_opacity", "描边透明度（%）", "percent"),
        ("title_guide_line_width_permill", "标题引导线粗（‰）", "permill"),
    ),
}
CONFIG_GROUPS = (
    (
        "首选项",
        (
            ("", ("auto_start_display", "open_action", "tray_click_action")),
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
                ),
            ),
            (
                "作业",
                (
                    "assignment_alignment",
                    "assignment_font_size",
                    "assignment_font_color",
                    "assignment_prefix",
                    "assignment_suffix",
                ),
            ),
            (
                "次要作业",
                (
                    "secondary_assignment_font_size",
                    "secondary_assignment_font_color",
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
                    "display_animation",
                ),
            ),
        ),
    ),
)
STARTUP_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "main"







def load_document():
    ensure_config_file_visible()
    config = load_config(CONFIG_FILE)
    data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)
    return config, data


def save_document(config):
    create_config_backup()
    save_config(CONFIG_FILE, config)


def create_config_backup(extension=".json.bak"):
    if not CONFIG_FILE.is_file():
        return None
    ensure_backup_layout(RESOURCE_DIR)
    backup = next_backup_path(
        CONFIG_BACKUP_DIR, extension, automatic=True
    )
    shutil.copy2(CONFIG_FILE, backup)
    return backup


def backup_display_name(path):
    for extension in (".json.bak", ".tar"):
        if path.name.endswith(extension):
            return path.name[:-len(extension)]
    return path.name


def backup_creation_time(path):
    stat = path.stat()
    created = getattr(stat, "st_birthtime", stat.st_ctime)
    return datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")


def backup_storage_type(path):
    return "自动" if path.name.startswith("auto_") else "手动"


def ensure_config_file_visible():
    """Keep the active config.json discoverable."""
    if sys.platform != "win32" or not CONFIG_FILE.is_file():
        return
    kernel32 = ctypes.windll.kernel32
    attributes = kernel32.GetFileAttributesW(str(CONFIG_FILE))
    if attributes == -1:
        raise ctypes.WinError()
    if attributes & 0x2 and not kernel32.SetFileAttributesW(str(CONFIG_FILE), attributes & ~0x2):
        raise ctypes.WinError()


def list_config_backups():
    ensure_backup_layout(RESOURCE_DIR)
    return sorted(
        (path for path in CONFIG_BACKUP_DIR.glob("*.json.bak") if path.is_file()),
        key=lambda path: path.stat().st_ctime,
        reverse=True,
    )


def custom_directory_hash():
    """Return a content hash of the custom directory, or None when empty."""
    if not CUSTOM_DIR.is_dir():
        return None
    files = sorted(path for path in CUSTOM_DIR.rglob("*") if path.is_file())
    if not files:
        return None
    hasher = hashlib.sha256()
    for path in files:
        hasher.update(str(path.relative_to(CUSTOM_DIR)).encode("utf-8", "replace"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def create_custom_backup():
    """Pack the custom directory into a tar, only when its content changed."""
    ensure_backup_layout(RESOURCE_DIR)
    current_hash = custom_directory_hash()
    if current_hash is None:
        return None
    state_file = CUSTOM_BACKUP_DIR / ".custom_backup_state.json"
    last_hash = None
    try:
        last_hash = json.loads(state_file.read_text(encoding="utf-8")).get("hash")
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    if current_hash == last_hash:
        return None
    backup = next_backup_path(CUSTOM_BACKUP_DIR, ".tar", automatic=True)
    with tarfile.open(backup, "w") as tar:
        for path in sorted(p for p in CUSTOM_DIR.rglob("*") if p.is_file()):
            tar.add(path, arcname=str(path.relative_to(CUSTOM_DIR)))
    state_file.write_text(
        json.dumps({"hash": current_hash}, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return backup


def list_custom_backups():
    ensure_backup_layout(RESOURCE_DIR)
    return sorted(
        (path for path in CUSTOM_BACKUP_DIR.glob("*.tar") if path.is_file()),
        key=lambda path: path.stat().st_ctime,
        reverse=True,
    )


def list_assignment_backups():
    ensure_backup_layout(RESOURCE_DIR)
    return sorted(
        (path for path in ASSIGNMENT_BACKUP_DIR.glob("*.json.bak") if path.is_file()),
        key=lambda path: path.stat().st_ctime,
        reverse=True,
    )


def create_manual_backup(backup_type, name):
    if backup_type not in BACKUP_EXTENSIONS:
        raise ValueError("未知备份类型: {}".format(backup_type))
    name = validate_backup_name(name)
    ensure_backup_layout(RESOURCE_DIR)
    extension = BACKUP_EXTENSIONS[backup_type]
    directory = backup_directory(RESOURCE_DIR, backup_type)
    backup = next_backup_path(directory, extension, name=name)
    if backup_type == "config":
        source = CONFIG_FILE
        if not source.is_file():
            raise FileNotFoundError(str(source))
        shutil.copy2(source, backup)
    elif backup_type == "assignment":
        source = ASSIGNMENT_FILE
        if not source.is_file():
            raise FileNotFoundError(str(source))
        shutil.copy2(source, backup)
    elif backup_type == "custom":
        with tarfile.open(backup, "w") as tar:
            if CUSTOM_DIR.is_dir():
                for path in sorted(item for item in CUSTOM_DIR.rglob("*") if item.is_file()):
                    tar.add(path, arcname=str(path.relative_to(CUSTOM_DIR)))
    else:
        raise ValueError("未知备份类型: {}".format(backup_type))
    return backup


def restore_custom_backup(path):
    """Extract a custom backup tar back into the custom directory."""
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    root_resolved = CUSTOM_DIR.resolve()
    with tarfile.open(path, "r") as tar:
        for member in tar.getmembers():
            target = (CUSTOM_DIR / member.name).resolve()
            if target != root_resolved and root_resolved not in target.parents:
                raise ValueError("备份包含非法路径，已取消恢复")
        tar.extractall(CUSTOM_DIR)


def get_display_startup_command():
    if getattr(sys, "frozen", False):
        main_file = APPLICATION_DIR / "Homework Manager.exe"
        return subprocess.list2cmdline([str(main_file), "--autostart"])
    main_file = APPLICATION_DIR / "main.py"
    python_executable = Path(sys.executable).with_name("pythonw.exe")
    if not python_executable.exists():
        python_executable = Path(sys.executable)
    return subprocess.list2cmdline([str(python_executable), str(main_file), "--autostart"])


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


class configeditor:
    def __init__(self, root, initial_backup_type=None):
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
        self.preview_menu = tk.Menu(self.root, tearoff=False)
        self.preview_menu.add_command(label="预览作业", command=self.open_assignment_preview)
        self.color_previews = {}
        self.color_selectors = {}
        self.animation_params = {}
        self.title_theme_params = {}
        self.backup_manager_dialog = None
        self.create_backup_dialog = None
        self.status = tk.StringVar(value="就绪")
        self._dirty = False
        self._loading = False
        self.save_button = None
        self.create_widgets()
        self.load_values()
        self.reload_event = create_config_reload_event("config_editor")
        self.shutdown_event = create_shutdown_event("config_editor")
        if self.reload_event is not None:
            threading.Thread(target=self.wait_for_reload, daemon=True).start()
        if self.shutdown_event is not None:
            threading.Thread(target=self.wait_for_shutdown_signal, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        if initial_backup_type:
            self.root.after_idle(lambda: self.rollback_config(initial_backup_type))

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

        # The dashboard has no assignment list; expose the assignment preview from
        # its right-click menu while keeping the existing preview button.
        self.root.bind("<Button-3>", self.show_preview_menu)
        self.root.bind("<Button-2>", self.show_preview_menu)

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
                    variable.trace_add("write", lambda *_args: self._mark_dirty())
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
                        if key in ("display_animation", "title_theme"):
                            selector_frame = ttk.Frame(main)
                            selector_frame.grid(row=row, column=1, sticky="ew", pady=5)
                            selector_frame.columnconfigure(0, weight=1)
                            selector = ttk.Combobox(
                                selector_frame,
                                state="readonly",
                                textvariable=variable,
                                values=list(SELECT_OPTIONS[key].values()),
                            )
                            selector.grid(row=0, column=0, sticky="ew")
                            ttk.Button(
                                selector_frame,
                                text="动画参数" if key == "display_animation" else "主题参数",
                                command=(
                                    self.open_animation_params
                                    if key == "display_animation"
                                    else self.open_title_theme_params
                                ),
                            ).grid(row=0, column=1, padx=(6, 0))
                        else:
                            selector = ttk.Combobox(
                                main,
                                state="readonly",
                                textvariable=variable,
                                values=list(SELECT_OPTIONS[key].values()),
                            )
                            selector.grid(row=row, column=1, sticky="ew", pady=5)
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
        icon_path = Path(getattr(sys, "_MEIPASS", RESOURCE_DIR)) / "icon.ico"
        with Image.open(icon_path) as icon_file:
            icon_file.seek(0)
            icon_image = icon_file.convert("RGBA")
            icon_image.thumbnail((64, 64), Image.Resampling.LANCZOS)
            self.about_icon = ImageTk.PhotoImage(icon_image, master=about_title)
        ttk.Label(about_title, image=self.about_icon).pack(side="left", padx=(0, 6))
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
        ttk.Label(about_title, text=" v1.6 Beta 3").pack(side="left")
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
        row += 1
        recovery_buttons = ttk.Frame(main)
        recovery_buttons.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ttk.Button(
            recovery_buttons,
            text="恢复默认配置",
            command=self.restore_default_config,
        ).pack(side="left", padx=4)
        ttk.Button(
            recovery_buttons,
            text="备份管理",
            command=self.rollback_config,
        ).pack(side="left", padx=4)

        bottom = ttk.Frame(outer)
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(0, weight=1)

        ttk.Label(bottom, textvariable=self.status).grid(
            row=0, column=0, sticky="w"
        )

        buttons = ttk.Frame(bottom)
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(
            buttons,
            text="保存配置",
            command=self.save,
        ).pack(side="left", padx=4)
        self.save_button = buttons.winfo_children()[0]
        self.save_button.configure(state="disabled")
        ttk.Button(
            buttons,
            text="推送管理器...",
            command=self.open_subscription_manager,
        ).pack(side="left", padx=4)
        ttk.Button(
            buttons,
            text="预览作业",
            command=self.open_assignment_preview,
        ).pack(side="left", padx=4)
        ttk.Button(
            buttons,
            text="作业编辑器...",
            command=self.open_assignment_editor,
        ).pack(side="left", padx=4)

        control_buttons = ttk.Frame(outer)
        control_buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(
            control_buttons,
            text="重启程序",
            command=self.restart_hwm,
        ).pack(side="left", padx=4)
        ttk.Button(
            control_buttons,
            text="退出",
            command=self.exit_hwm,
        ).pack(side="left", padx=4)

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

    def restart_hwm(self):
        request_main_action("restart")

    def load_values(self):
        self._loading = True
        try:
            for key in DEFAULT_CONFIG:
                if key not in self.variables:
                    continue
                value = self.config.get(key, DEFAULT_CONFIG[key])
                if key in SELECT_FIELDS:
                    value = SELECT_OPTIONS[key].get(value, SELECT_OPTIONS[key][DEFAULT_CONFIG[key]])
                self.variables[key].set(str(value))
            for key in COLOR_FIELDS:
                self.update_color_preview(key)
        finally:
            self._loading = False
        self._dirty = False
        if self.save_button is not None:
            self.save_button.configure(state="disabled")

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

    def open_animation_params(self):
        label = self.variables["display_animation"].get()
        name = next(
            (value for value, display in DISPLAY_ANIMATIONS.items() if display == label),
            DEFAULT_CONFIG["display_animation"],
        )
        fields = ANIMATION_PARAM_FIELDS.get(name)
        if not fields:
            messagebox.showinfo("动画参数", "该动画没有可调整的参数。", parent=self.root)
            return
        if name in self.animation_params:
            params = dict(self.animation_params[name])
        else:
            params = load_display_animation_params(APPLICATION_DIR, name)

        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("动画参数 - {}".format(DISPLAY_ANIMATIONS.get(name, name)))
        dialog.transient(self.root)
        dialog.grab_set()
        configure_tk_scaling(dialog)
        dialog.columnconfigure(1, weight=1)

        labels = {key: field_label for key, field_label, _kind in fields}
        entries = {}
        for row, (key, field_label, kind) in enumerate(fields):
            ttk.Label(dialog, text=field_label).grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            variable = tk.StringVar(value=str(params.get(key, "")))
            entries[key] = (variable, kind)
            ttk.Entry(dialog, textvariable=variable).grid(
                row=row, column=1, sticky="ew", padx=(0, 10), pady=5
            )

        buttons = ttk.Frame(dialog)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", padx=10, pady=(10, 10))

        def commit():
            new_params = {}
            for key, (variable, kind) in entries.items():
                text = variable.get().strip()
                try:
                    if kind in ("int", "positive_int", "nonnegative_int"):
                        value = int(text)
                        if kind in ("int", "positive_int") and value < 1:
                            raise ValueError("{} 必须大于 0".format(labels[key]))
                        if kind == "nonnegative_int" and value < 0:
                            raise ValueError("{} 必须大于或等于 0".format(labels[key]))
                    elif kind == "permill":
                        value = int(text)
                        if not 0 <= value <= 1000:
                            raise ValueError("{} 必须在 0 到 1000 之间".format(labels[key]))
                    elif kind == "percent":
                        value = int(text)
                        if not 1 <= value <= 100:
                            raise ValueError("{} 必须在 1 到 100 之间".format(labels[key]))
                    else:
                        value = float(text)
                        if not 0 < value <= 1:
                            raise ValueError("{} 必须大于 0 且不超过 1".format(labels[key]))
                except ValueError as error:
                    messagebox.showerror("参数无效", str(error), parent=dialog)
                    return
                new_params[key] = value
            self.animation_params[name] = new_params
            self._mark_dirty()
            dialog.destroy()

        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="确定", command=commit).pack(side="right", padx=(0, 8))
        place_window_bottom_right(dialog)

    def open_title_theme_params(self):
        label = self.variables["title_theme"].get()
        name = next(
            (value for value, display in TITLE_THEMES.items() if display == label),
            DEFAULT_CONFIG["title_theme"],
        )
        fields = TITLE_THEME_PARAM_FIELDS.get(name)
        if not fields:
            messagebox.showinfo("主题参数", "该主题没有可调整的参数。", parent=self.root)
            return
        if name in self.title_theme_params:
            params = dict(self.title_theme_params[name])
        else:
            params = load_title_theme_params(APPLICATION_DIR, name)

        dialog = tk.Toplevel(self.root)
        set_window_icon(dialog, __file__)
        dialog.title("主题参数 - {}".format(TITLE_THEMES.get(name, name)))
        dialog.transient(self.root)
        dialog.grab_set()
        configure_tk_scaling(dialog)
        dialog.columnconfigure(1, weight=1)

        labels = {key: field_label for key, field_label, _kind in fields}
        entries = {}
        for row, (key, field_label, kind) in enumerate(fields):
            ttk.Label(dialog, text=field_label).grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            variable = tk.StringVar(value=str(params.get(key, "")))
            entries[key] = (variable, kind)
            if kind != "color":
                ttk.Entry(dialog, textvariable=variable).grid(
                    row=row, column=1, sticky="ew", padx=(0, 10), pady=5
                )
                continue
            color_frame = ttk.Frame(dialog)
            color_frame.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=5)
            color_frame.columnconfigure(1, weight=1)
            color_preview = tk.Label(color_frame, width=3, relief="sunken")
            color_preview.grid(row=0, column=0, padx=(0, 6))
            color_selector = ttk.Combobox(
                color_frame,
                state="readonly",
                values=[preset for preset, _color in COLOR_PRESETS],
            )
            color_selector.grid(row=0, column=1, sticky="ew")

            def sync_preview(
                *_args, preview=color_preview, selector=color_selector, source=variable
            ):
                color = source.get()
                try:
                    preview.configure(background=color)
                except tk.TclError:
                    preview.configure(background="#FFFFFF")
                for index, (_preset, preset_color) in enumerate(COLOR_PRESETS):
                    if color.upper() == preset_color.upper():
                        selector.current(index)
                        return
                selector.set("自定义颜色")

            def select_preset(_event, selector=color_selector, source=variable):
                index = selector.current()
                if 0 <= index < len(COLOR_PRESETS):
                    source.set(COLOR_PRESETS[index][1])

            def choose_color(source=variable):
                color = colorchooser.askcolor(
                    color=source.get(),
                    parent=dialog,
                    title="选择颜色",
                )[1]
                if color:
                    source.set(color.upper())

            color_selector.bind("<<ComboboxSelected>>", select_preset)
            ttk.Button(
                color_frame, text="自定义颜色...", command=choose_color
            ).grid(row=0, column=2, padx=(6, 0))
            variable.trace_add("write", sync_preview)
            sync_preview()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", padx=10, pady=(10, 10))

        def commit():
            new_params = {}
            for key, (variable, kind) in entries.items():
                text = variable.get().strip()
                if kind == "color":
                    try:
                        dialog.winfo_rgb(text)
                    except tk.TclError:
                        messagebox.showerror(
                            "参数无效",
                            "{}不是有效的颜色值".format(labels[key]),
                            parent=dialog,
                        )
                        return
                    new_params[key] = text
                    continue
                try:
                    value = int(text)
                except ValueError:
                    messagebox.showerror(
                        "参数无效",
                        "{} 必须是整数".format(labels[key]),
                        parent=dialog,
                    )
                    return
                if kind == "percent" and not 0 <= value <= 100:
                    messagebox.showerror(
                        "参数无效",
                        "{} 必须在 0 到 100 之间".format(labels[key]),
                        parent=dialog,
                    )
                    return
                if kind == "permill" and not 1 <= value <= 1000:
                    messagebox.showerror(
                        "参数无效",
                        "{} 必须在 1 到 1000 之间".format(labels[key]),
                        parent=dialog,
                    )
                    return
                new_params[key] = value
            self.title_theme_params[name] = new_params
            self._mark_dirty()
            dialog.destroy()

        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="确定", command=commit).pack(side="right", padx=(0, 8))
        place_window_bottom_right(dialog)

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
            if value < 1:
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
            "title_width_permill", "title_length_permill",
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
        for key in ("assignment_prefix", "assignment_suffix", "school", "class"):
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

    def _mark_dirty(self):
        if self._loading:
            return
        if self._dirty:
            return
        self._dirty = True
        if self.save_button is not None:
            self.save_button.configure(state="normal")

    def save(self):
        if not self._dirty:
            return
        try:
            config = self.read_config()
            create_config_backup()
            create_custom_backup()
            for name, params in self.animation_params.items():
                save_display_animation_params(APPLICATION_DIR, name, params)
            for name, params in self.title_theme_params.items():
                save_title_theme_params(APPLICATION_DIR, name, params)
            save_config(CONFIG_FILE, config)
            update_display_startup(config["auto_start_display"])
        except (OSError, TypeError, ValueError, winreg.error) as error:
            messagebox.showerror("保存失败", str(error), parent=self.root)
            return
        self.config = config
        self.animation_params = {}
        self.title_theme_params = {}
        self._dirty = False
        if self.save_button is not None:
            self.save_button.configure(state="disabled")
        self.status.set("已保存到 config.json")
        notify_config_saved()
        show_windows_notification("已保存 Homework Manager 配置", "保存完成")
        self.root.after_idle(self.reload_from_disk)

    def restore_default_config(self):
        if not messagebox.askyesno(
            "恢复默认配置",
            "这会覆盖当前所有的仪表盘配置，包含：\n首选项、显示器格式、显示\n你确定吗？",
            parent=self.root,
        ):
            return
        config = DEFAULT_CONFIG.copy()
        # School and class identify the user's context, so preserve them when
        # resetting presentation and preference settings.
        current_config = load_config(CONFIG_FILE)
        for key in ("school", "class"):
            config[key] = current_config.get(key, config[key])
        try:
            save_document(config)
            update_display_startup(config["auto_start_display"])
        except (OSError, TypeError, ValueError, winreg.error) as error:
            messagebox.showerror("恢复失败", str(error), parent=self.root)
            return
        self.config = config
        self.load_values()
        self.status.set("已恢复默认配置并保存到 config.json")
        notify_config_saved()

    def rollback_config(self, initial_mode="config"):
        existing_dialog = self.backup_manager_dialog
        if existing_dialog is not None and existing_dialog.winfo_exists():
            if initial_mode in ("config", "custom", "assignment"):
                existing_dialog.set_backup_mode(initial_mode)
            existing_dialog.lift()
            existing_dialog.focus_force()
            return

        try:
            ensure_backup_layout(RESOURCE_DIR)
        except OSError as error:
            messagebox.showerror("备份管理失败", str(error), parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        self.backup_manager_dialog = dialog
        set_window_icon(dialog, __file__)
        dialog.transient(self.root)
        dialog.grab_set()
        configure_tk_scaling(dialog)
        set_window_size_percent(dialog, 35, 35)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        type_names = {
            "config": "配置",
            "custom": "自定义数据",
            "assignment": "作业",
        }
        backup_lists = {
            "config": list_config_backups,
            "custom": list_custom_backups,
            "assignment": list_assignment_backups,
        }
        state = {
            "mode": initial_mode if initial_mode in type_names else "config",
        }
        mode_var = tk.StringVar(value=type_names[state["mode"]])
        heading = ttk.Label(dialog, text="")
        heading.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 6))

        backup_list = ttk.Treeview(
            dialog,
            columns=("name", "time", "storage_type"),
            show="headings",
            selectmode="browse",
        )
        backup_list.heading("name", text="名称")
        backup_list.heading("time", text="时间")
        backup_list.heading("storage_type", text="存储类型")
        backup_list.column("name", width=250, anchor="w")
        backup_list.column("time", width=150, anchor="center")
        backup_list.column("storage_type", width=90, anchor="center")
        backup_list.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 8))
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=backup_list.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 8))
        backup_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(dialog)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        navigation = ttk.Frame(buttons)
        navigation.pack(side="left")

        def current_backups():
            return backup_lists[state["mode"]]()

        def refresh():
            backups = current_backups()
            for item in backup_list.get_children():
                backup_list.delete(item)
            for index, backup in enumerate(backups):
                backup_list.insert(
                    "", tk.END, iid=str(index),
                    values=(
                        backup_display_name(backup),
                        backup_creation_time(backup),
                        backup_storage_type(backup),
                    ),
                )
            if backups:
                backup_list.selection_set("0")
                backup_list.focus("0")
            else:
                backup_list.insert(
                    "", tk.END,
                    values=("没有可用的{}备份".format(type_names[state["mode"]]), "", ""),
                )
            dialog.title("备份管理 - {}".format(type_names[state["mode"]]))
            heading.configure(text="选择要操作的{}备份：".format(type_names[state["mode"]]))
            mode_var.set(type_names[state["mode"]])
            restore_button.configure(state="normal" if backups else "disabled")
            delete_button.configure(state="normal" if backups else "disabled")
            return backups

        def restore_selected():
            backups = current_backups()
            selection = backup_list.selection()
            if not selection or not backups:
                return
            backup = backups[int(selection[0])]
            try:
                if state["mode"] == "custom":
                    restore_custom_backup(backup)
                elif state["mode"] == "assignment":
                    automatic_backup = next_backup_path(
                        ASSIGNMENT_BACKUP_DIR, ".json.bak", automatic=True
                    )
                    shutil.copy2(ASSIGNMENT_FILE, automatic_backup)
                    shutil.copy2(backup, ASSIGNMENT_FILE)
                    self.data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)
                else:
                    restored_config = load_config(backup)
                    create_config_backup()
                    shutil.copy2(backup, CONFIG_FILE)
                    self.config = restored_config
                    self.data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)
                    self.load_values()
                    update_display_startup(self.config["auto_start_display"])
            except (
                OSError, TypeError, ValueError, json.JSONDecodeError,
                tarfile.TarError, winreg.error,
            ) as error:
                messagebox.showerror("恢复失败", str(error), parent=dialog)
                return
            self.status.set(
                "已恢复{}备份：{}".format(
                    type_names[state["mode"]], backup_display_name(backup)
                )
            )
            notify_config_saved()
            close_manager()

        def delete_selected():
            backups = current_backups()
            selection = backup_list.selection()
            if not selection or not backups:
                return
            if not messagebox.askyesno(
                "确认删除",
                "你确定要删除此备份吗？\n此操作不可恢复！",
                parent=dialog,
            ):
                return
            backup = backups[int(selection[0])]
            try:
                backup.unlink()
            except OSError as error:
                messagebox.showerror("删除失败", str(error), parent=dialog)
                return
            refresh()

        def set_mode(backup_type=None):
            if backup_type not in type_names:
                backup_type = next(
                    key for key, label in type_names.items()
                    if label == mode_var.get()
                )
            state["mode"] = backup_type
            refresh()

        def close_manager():
            if self.create_backup_dialog is not None:
                if self.create_backup_dialog.winfo_exists():
                    self.create_backup_dialog.destroy()
                self.create_backup_dialog = None
            self.backup_manager_dialog = None
            dialog.destroy()

        def open_create_dialog():
            existing_dialog = self.create_backup_dialog
            if existing_dialog is not None and existing_dialog.winfo_exists():
                existing_dialog.lift()
                existing_dialog.focus_force()
                return
            self.create_backup_dialog = None

            create_dialog = tk.Toplevel(dialog)
            self.create_backup_dialog = create_dialog
            backup_type = state["mode"]
            set_window_icon(create_dialog, __file__)
            create_dialog.title("创建备份 - {}".format(type_names[backup_type]))
            create_dialog.transient(dialog)
            create_dialog.grab_set()
            configure_tk_scaling(create_dialog)
            create_dialog.columnconfigure(1, weight=1)

            name_var = tk.StringVar()
            ttk.Label(create_dialog, text="备份名称").grid(
                row=0, column=0, sticky="w", padx=(12, 8), pady=(12, 6)
            )
            name_entry = ttk.Entry(create_dialog, textvariable=name_var, width=30)
            name_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 6))

            def close_create_dialog():
                self.create_backup_dialog = None
                create_dialog.destroy()

            def create():
                try:
                    backup = create_manual_backup(backup_type, name_var.get())
                except (OSError, ValueError, tarfile.TarError) as error:
                    messagebox.showerror("创建备份失败", str(error), parent=create_dialog)
                    return
                state["mode"] = backup_type
                close_create_dialog()
                refresh()
                self.status.set(
                    "已创建{}备份：{}".format(
                        type_names[backup_type], backup_display_name(backup)
                    )
                )

            create_buttons = ttk.Frame(create_dialog)
            create_buttons.grid(row=1, column=0, columnspan=2, sticky="e", padx=12, pady=(8, 12))
            ttk.Button(create_buttons, text="取消", command=close_create_dialog).pack(
                side="right"
            )
            ttk.Button(create_buttons, text="创建", command=create).pack(
                side="right", padx=(0, 8)
            )
            create_dialog.bind("<Return>", lambda _event: create())
            create_dialog.protocol("WM_DELETE_WINDOW", close_create_dialog)
            place_window_bottom_right(create_dialog)
            name_entry.focus_set()

        ttk.Button(navigation, text="+", width=2, command=open_create_dialog).pack(
            side="left", padx=(0, 4)
        )
        ttk.Label(navigation, text="备份类型").pack(side="left", padx=(0, 4))
        mode_choice = ttk.Combobox(
            navigation,
            textvariable=mode_var,
            values=tuple(type_names.values()),
            state="readonly",
            width=12,
        )
        mode_choice.pack(side="left")
        mode_choice.bind("<<ComboboxSelected>>", lambda _event: set_mode())

        ttk.Button(buttons, text="取消", command=close_manager).pack(side="right")
        restore_button = ttk.Button(buttons, text="恢复", command=restore_selected)
        restore_button.pack(side="right", padx=(0, 8))
        delete_button = ttk.Button(buttons, text="删除", command=delete_selected)
        delete_button.pack(side="right", padx=(0, 8))

        backup_list.bind("<Double-Button-1>", lambda _event: restore_selected())
        dialog.set_backup_mode = set_mode
        dialog.protocol("WM_DELETE_WINDOW", close_manager)
        refresh()
        place_window_bottom_right(dialog)

    def open_assignment_editor(self):
        try:
            if EDITOR_FILE.suffix == ".py":
                subprocess.Popen([sys.executable, str(EDITOR_FILE)])
            else:
                subprocess.Popen([str(EDITOR_FILE), "--component", "assignment_editor"])
        except OSError as error:
            messagebox.showerror("启动失败", str(error), parent=self.root)

    def open_subscription_manager(self):
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([str(EDITOR_FILE), "--component", "subscription_manager"])
            else:
                subprocess.Popen([sys.executable, str(APPLICATION_DIR / "subscriptionManager.py")])
        except OSError as error:
            messagebox.showerror("启动失败", str(error), parent=self.root)

    def open_assignment_preview(self):
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([str(EDITOR_FILE), "--component", "assignment_preview"])
            else:
                subprocess.Popen([sys.executable, str(APPLICATION_DIR / "preview.py")])
        except OSError as error:
            messagebox.showerror("启动失败", str(error), parent=self.root)

    def show_preview_menu(self, event):
        widget = event.widget
        if isinstance(widget, (tk.Scrollbar,)):
            return
        try:
            self.preview_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.preview_menu.grab_release()
        return "break"


def main(initial_backup_type=None):
    enable_high_dpi()
    from runtime import acquire_single_instance
    if not acquire_single_instance("dashboard"):
        return
    if initial_backup_type is None and "--backup-type" in sys.argv:
        index = sys.argv.index("--backup-type")
        if index + 1 < len(sys.argv):
            initial_backup_type = sys.argv[index + 1]
    root = tk.Tk()
    try:
        configeditor(root, initial_backup_type)
        place_window_bottom_right(root)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("加载失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
