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

import ctypes
import importlib
import os
import subprocess
import sys
import threading
import time
import traceback
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw

from config import data_directory, default_document, initialize_data_directory, load_config, save_config, load_assignment_data, save_assignment_data
from runtime import (
    close_main_control_events,
    configure_tk_scaling,
    create_main_control_events,
    enable_high_dpi,
    enable_touch_keyboard,
    request_shutdown,
    SHUTDOWN_EVENTS,
    set_window_icon,
    set_window_size_percent,
    place_window_bottom_right,
    wait_for_main_action,
    show_windows_notification,
)
from subscriptionService import maybe_send_scheduled
from appIdentity import register_app
from editor import refresh_scheduled_assignments


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = APPLICATION_DIR
DATA_DIR = data_directory(RESOURCE_DIR)
CONFIG_FILE = DATA_DIR / "config.json"
TRAY_ICON_FILE = (
    Path(getattr(sys, "_MEIPASS", APPLICATION_DIR)) / "icon.ico"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR / "icon.ico"
)
DISPLAY_MUTEX_NAME = "Local\\displaySingleInstance"
MAIN_MUTEX_NAME = "Local\\HomeworkManagerMainInstance"
STORAGE_FILE = DATA_DIR / "storage.json"
STORAGE_WRITE_INTERVAL_SECONDS = 15 * 60


def create_assignment_backup(assignment_file, backup_dir):
    """创建作业文件备份。若作业文件缺失，则先通知再新建默认文件。

    返回 True 表示原文件缺失（已新建，未生成历史备份）；False 表示已生成备份。
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    if assignment_file.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H")
        backup_file = backup_dir / "assignment_{}.json.bak".format(timestamp)
        suffix = 1
        while backup_file.exists():
            backup_file = backup_dir / "assignment_{}_{}.json.bak".format(timestamp, suffix)
            suffix += 1
        shutil.copy2(assignment_file, backup_file)
        return False
    show_windows_notification("活跃的作业文件意外丢失\n已将作业文件重置为空", "备份时出现错误")
    save_assignment_data(assignment_file, default_document()[1]["data"])
    return True


def reset_assignment_if_new_day():
    today = datetime.now().date()
    try:
        stored = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
        previous = datetime.fromisoformat(stored.get("last_run_date", "")).date()
    except (OSError, ValueError, TypeError, AttributeError):
        previous = None

    if previous is not None and previous < today:
        assignment_file = DATA_DIR / "assignment.json"
        assignment_missing = create_assignment_backup(assignment_file, DATA_DIR / "backup")

        assignment = load_assignment_data(assignment_file, CONFIG_FILE)
        for subject in assignment:
            if not isinstance(subject, dict):
                continue
            for assignments in subject.values():
                if isinstance(assignments, list):
                    for index, entry in enumerate(assignments):
                        if isinstance(entry, dict):
                            entry["hide"] = True
                        elif isinstance(entry, str):
                            assignments[index] = {"assignment": entry, "hide": True}
        save_assignment_data(assignment_file, assignment)
        normalized = {}
        for subject in assignment:
            if isinstance(subject, dict):
                for name, assignments in subject.items():
                    normalized[name] = assignments
        refresh_scheduled_assignments(normalized)
        save_assignment_data(assignment_file, [{subject: assignments} for subject, assignments in normalized.items()])
        if not assignment_missing:
            show_windows_notification("已重置所有科目的所有作业", "重置完成")


def write_storage_timestamp():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STORAGE_FILE.with_suffix(".json.{}.tmp".format(uuid.uuid4().hex))
    temporary.write_text(json.dumps({"last_run_date": datetime.now().date().isoformat()}, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    temporary.replace(STORAGE_FILE)


def acquire_mutex(name):
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.GetLastError.restype = ctypes.c_ulong
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    mutex = kernel32.CreateMutexW(None, False, name)
    if not mutex:
        return True
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        return False
    return mutex


def is_display_running():
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    mutex = kernel32.OpenMutexW(0x00100000, False, DISPLAY_MUTEX_NAME)
    if not mutex:
        return False
    kernel32.CloseHandle(mutex)
    return True


def python_executable():
    executable = Path(sys.executable).with_name("pythonw.exe")
    return str(executable if executable.exists() else sys.executable)


def launch_component(component):
    if getattr(sys, "frozen", False):
        command = [sys.executable] if component == "main" else [
            sys.executable, "--component", component
        ]
    else:
        names = {
            "display": "display.py",
            "dashboard": "dashboard.py",
            "assignment_editor": "editor.py",
            "subscription_manager": "subscriptionManager.py",
            "assignment_preview": "preview.py",
            "main": "main.py",
        }
        target = APPLICATION_DIR / names[component]
        command = [python_executable(), str(target)]

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(command, cwd=str(APPLICATION_DIR), creationflags=creation_flags)


def wait_for_process_exit(process_id):
    if sys.platform != "win32":
        while True:
            try:
                os.kill(process_id, 0)
            except OSError:
                return
            time.sleep(0.1)

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    process = kernel32.OpenProcess(0x00100000, False, process_id)  # SYNCHRONIZE
    if not process:
        # ERROR_INVALID_PARAMETER means the old process has already exited.
        if ctypes.windll.kernel32.GetLastError() == 87:
            return
        raise ctypes.WinError()
    try:
        kernel32.WaitForSingleObject(process, 0xFFFFFFFF)
    finally:
        kernel32.CloseHandle(process)


def wait_for_components_exit():
    if sys.platform != "win32":
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.OpenEventW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    while True:
        running_components = []
        for component, event_name in SHUTDOWN_EVENTS.items():
            event = kernel32.OpenEventW(0x00100000, False, event_name)  # SYNCHRONIZE
            if event:
                running_components.append(component)
                kernel32.CloseHandle(event)
        if not running_components:
            return
        time.sleep(0.1)


def start_restart_helper():
    process_id = os.getpid()
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--restart-after", str(process_id)]
    else:
        command = [
            python_executable(), str(Path(__file__).resolve()),
            "--restart-after", str(process_id),
        ]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(command, cwd=str(APPLICATION_DIR), creationflags=creation_flags)


def ensure_display_running():
    if not is_display_running():
        launch_component("display")


def load_tray_click_action():
    config = load_config(CONFIG_FILE)
    action = config.get("tray_click_action", "dashboard")
    return action if action in ("dashboard", "assignment_editor", "menu") else "dashboard"


def load_open_action():
    config = load_config(CONFIG_FILE)
    action = config.get("open_action", "dashboard")
    return action if action in ("dashboard", "assignment_editor") else "dashboard"


def show_school_class_prompt():
    config_file = CONFIG_FILE if CONFIG_FILE.is_file() else RESOURCE_DIR / "config.json"
    config = load_config(config_file)
    if str(config.get("school", "")).strip() and str(config.get("class", "")).strip():
        return True, False

    root = tk.Tk()
    enable_touch_keyboard(root)
    set_window_icon(root, __file__)
    root.title("欢迎")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    configure_tk_scaling(root)
    set_window_size_percent(root, 32, 51)
    completed = {"value": False}
    school_var = tk.StringVar(value=str(config.get("school", "")))
    class_var = tk.StringVar(value=str(config.get("class", "")))
    outer = ttk.Frame(root, padding=20)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(1, weight=1)
    ttk.Label(
        outer,
        text="欢迎使用 Homework Manager",
        font=("Microsoft YaHei UI", 15, "bold"),
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
    ttk.Label(
        outer,
        text=" “坐下来，轻松一下，对屏幕上的选项做一个短暂的浏览。”\n\n 首次启动 Homework Manager 需要填写学校和班级，\n      之后可以在仪表盘中修改这两项。\n\n 本程序数据保存在程序目录，不会上传到服务器。\n\n 推送管理器中的 SMTP 密码使用 Windows DPAPI 加密。\n\n 当您点击“保存并继续”后，即授权本程序：\n      - 提供程序的服务；\n      - 在自身目录的 data 文件夹中创建若干文件用于存储数据；\n      - 注册开始菜单快捷方式及通知应用标识。",
        foreground="#000000",
        font=("Microsoft YaHei UI", 9),
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))
    ttk.Label(outer, text="学校").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=7)
    school_entry = ttk.Entry(outer, textvariable=school_var, font=("Microsoft YaHei UI", 10))
    school_entry.grid(row=2, column=1, sticky="ew", pady=7)
    ttk.Label(outer, text="班级").grid(row=3, column=0, sticky="w", padx=(0, 14), pady=7)
    ttk.Entry(outer, textvariable=class_var, font=("Microsoft YaHei UI", 10)).grid(
        row=3, column=1, sticky="ew", pady=7
    )

    def save_and_continue():
        school = school_var.get().strip()
        class_name = class_var.get().strip()
        if not school or not class_name:
            messagebox.showwarning("信息不完整", "学校和班级均必填项。", parent=root)
            return
        config["school"] = school
        config["class"] = class_name
        try:
            save_config(CONFIG_FILE, config)
            assignment_file = DATA_DIR / "assignment.json"
            if not assignment_file.is_file():
                save_assignment_data(assignment_file, default_document()[1]["data"])
            register_app()
        except OSError as error:
            messagebox.showerror("保存或应用注册失败", str(error), parent=root)
            return
        completed["value"] = True
        root.destroy()

    buttons = ttk.Frame(outer)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(20, 0))
    ttk.Button(buttons, text="退出", command=root.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="保存并继续", command=save_and_continue).pack(side="right")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    place_window_bottom_right(root)
    root.after_idle(lambda: (root.lift(), root.focus_force(), school_entry.focus_set()))
    root.mainloop()
    return completed["value"], completed["value"]


def create_tray_image():
    if TRAY_ICON_FILE.is_file():
        try:
            return Image.open(TRAY_ICON_FILE).convert("RGBA")
        except (OSError, ValueError):
            pass

    image = Image.new("RGB", (64, 64), "#315E7D")
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 56), outline="#8ABBD2", width=3)
    draw.text((22, 14), "H", fill="#FFFFFF")
    return image


def shutdown_components():
    for component in (
        "config_editor", "assignment_editor", "subscription_manager", "assignment_preview", "display"
    ):
        request_shutdown(component)


def main():
    enable_high_dpi()
    pystray = importlib.import_module("pystray")
    main_mutex = acquire_mutex(MAIN_MUTEX_NAME)
    if main_mutex is False:
        return

    prompt_succeeded, first_run_completed = show_school_class_prompt()
    if not prompt_succeeded:
        return
    initialize_data_directory(RESOURCE_DIR)
    if not first_run_completed:
        register_app()
    reset_assignment_if_new_day()
    write_storage_timestamp()
    ensure_display_running()
    tray_click_action = load_tray_click_action()
    main_control_events = create_main_control_events()

    def schedule_loop():
        last_storage_write = time.monotonic()
        while True:
            try:
                maybe_send_scheduled(RESOURCE_DIR)
            except Exception as error:
                try:
                    with (RESOURCE_DIR / "push.log").open("a", encoding="utf-8") as log:
                        log.write("{} scheduled push failed: {}\n".format(
                            datetime.now().isoformat(timespec="seconds"), error
                        ))
                except OSError:
                    pass
            current = datetime.now()
            if time.monotonic() - last_storage_write >= STORAGE_WRITE_INTERVAL_SECONDS:
                try:
                    write_storage_timestamp()
                    last_storage_write = time.monotonic()
                except OSError:
                    pass
            time.sleep(max(0.01, 1.0 - current.microsecond / 1_000_000))

    threading.Thread(target=schedule_loop, daemon=True).start()

    def open_dashboard(_icon=None, _item=None):
        launch_component("dashboard")

    def open_assignment_editor(_icon=None, _item=None):
        launch_component("assignment_editor")

    def open_assignment_preview(_icon=None, _item=None):
        launch_component("assignment_preview")

    def stop_hwm(icon, restart=False):
        if restart:
            start_restart_helper()
        shutdown_components()
        try:
            write_storage_timestamp()
        except OSError:
            pass
        icon.stop()

    def exit_hwm(icon, _item=None):
        stop_hwm(icon)

    def restart_hwm(icon, _item=None):
        stop_hwm(icon, restart=True)

    def wait_for_control_action():
        action = wait_for_main_action(main_control_events)
        if action == "exit":
            exit_hwm(icon)
        elif action == "restart":
            restart_hwm(icon)

    def on_icon_stop(_icon):
        close_main_control_events(main_control_events)

    default_dashboard = tray_click_action == "dashboard"
    default_editor = tray_click_action == "assignment_editor"
    menu = pystray.Menu(
        pystray.MenuItem("仪表盘", open_dashboard, default=default_dashboard),
        pystray.MenuItem(
            "作业编辑器",
            open_assignment_editor,
            default=default_editor,
        ),
        pystray.MenuItem("预览作业", open_assignment_preview),
        pystray.MenuItem("重启程序", restart_hwm),
        pystray.MenuItem("退出", exit_hwm),
    )
    icon = pystray.Icon("HomeworkManager", create_tray_image(), "Homework Manager", menu)

    if tray_click_action == "menu":
        try:
            from pystray._util import win32 as _pystray_win32
            original_notify = icon._message_handlers[_pystray_win32.WM_NOTIFY]

            def notify_showing_menu(wparam, lparam):
                if lparam == _pystray_win32.WM_LBUTTONUP:
                    lparam = _pystray_win32.WM_RBUTTONUP
                return original_notify(wparam, lparam)

            icon._message_handlers[_pystray_win32.WM_NOTIFY] = notify_showing_menu
        except (AttributeError, ImportError, KeyError):
            pass

    threading.Thread(target=wait_for_control_action, daemon=True).start()
    if "--autostart" not in sys.argv:
        open_action = load_open_action()
        if open_action == "dashboard":
            open_dashboard()
        elif open_action == "assignment_editor":
            open_assignment_editor()
    icon.run()
    on_icon_stop(icon)


def run_entry_point():
    if "--restart-after" in sys.argv:
        index = sys.argv.index("--restart-after")
        if index + 1 >= len(sys.argv):
            raise ValueError("缺少需要等待退出的进程编号")
        wait_for_process_exit(int(sys.argv[index + 1]))
        wait_for_components_exit()
        launch_component("main")
        return

    if getattr(sys, "frozen", False) and "--component" in sys.argv:
        component_index = sys.argv.index("--component")
        if component_index + 1 >= len(sys.argv):
            raise ValueError("缺少组件名称")
        component = sys.argv[component_index + 1]
        component_modules = {
            "display": "display",
            "dashboard": "dashboard",
            "assignment_editor": "editor",
            "subscription_manager": "subscriptionManager",
            "assignment_preview": "preview",
        }
        if component not in component_modules:
            raise ValueError("未知组件: {}".format(component))
        importlib.import_module(component_modules[component]).main()
    else:
        main()


if __name__ == "__main__":
    try:
        run_entry_point()
    except Exception:
        crash_log = RESOURCE_DIR / "crash.log"
        try:
            crash_log.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        raise
