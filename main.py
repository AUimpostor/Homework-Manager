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
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw

from HWMConfig import load_config, save_config
from HWMRuntime import (
    close_main_control_events,
    configure_tk_scaling,
    create_main_control_events,
    enable_high_dpi,
    enable_touch_keyboard,
    request_shutdown,
    set_window_icon,
    wait_for_main_action,
)
from HWMSubscriptionService import maybe_send_scheduled


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = (
    APPLICATION_DIR
    if (APPLICATION_DIR / "config.json").exists() or (APPLICATION_DIR / "homework.json").exists()
    else APPLICATION_DIR.parent
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR
)
CONFIG_FILE = RESOURCE_DIR / "config.json"
TRAY_ICON_FILE = (
    Path(getattr(sys, "_MEIPASS", APPLICATION_DIR)) / "hwm.ico"
    if getattr(sys, "frozen", False)
    else APPLICATION_DIR / "hwm.ico"
)
DISPLAY_MUTEX_NAME = "Local\\HomeworkDisplaySingleInstance"
MAIN_MUTEX_NAME = "Local\\HomeworkManagerMainInstance"


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


def launch_component(component, preview=False):
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--component", component]
        if preview:
            command.append("--preview")
    else:
        names = {
            "display": "HomeworkDisplay.py",
            "dashboard": "HWMConfigEditor.py",
            "homework_editor": "HomeworkEditor.py",
            "subscription_manager": "HWMSubscriptionManager.py",
            "main": "main.py",
        }
        target = APPLICATION_DIR / names[component]
        command = [python_executable(), str(target)]
        if preview:
            command.append("--preview")

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(command, cwd=str(APPLICATION_DIR), creationflags=creation_flags)


def ensure_display_running():
    if not is_display_running():
        launch_component("display")


def load_tray_click_action():
    config = load_config(CONFIG_FILE)
    action = config.get("tray_click_action", "dashboard")
    return action if action in ("dashboard", "homework_editor") else "dashboard"


def show_school_class_prompt():
    config = load_config(CONFIG_FILE)
    if str(config.get("school", "")).strip() and str(config.get("class", "")).strip():
        return True

    root = tk.Tk()
    enable_touch_keyboard(root)
    set_window_icon(root, __file__)
    root.title("填写学校和班级")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.geometry("500x320")
    configure_tk_scaling(root)
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
        text="首次启动请填写学校和班级，之后可在仪表盘中修改。",
        foreground="#666666",
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
            messagebox.showwarning("信息不完整", "学校和班级都必须填写。", parent=root)
            return
        config["school"] = school
        config["class"] = class_name
        try:
            save_config(CONFIG_FILE, config)
        except OSError as error:
            messagebox.showerror("保存失败", str(error), parent=root)
            return
        completed["value"] = True
        root.destroy()

    buttons = ttk.Frame(outer)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(20, 0))
    ttk.Button(buttons, text="退出 HWM", command=root.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="保存并继续", command=save_and_continue).pack(side="right")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.after_idle(lambda: (root.lift(), root.focus_force(), school_entry.focus_set()))
    root.mainloop()
    return completed["value"]


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
    for component in ("config_editor", "homework_editor", "subscription_manager", "display"):
        request_shutdown(component)


def main():
    enable_high_dpi()
    pystray = importlib.import_module("pystray")
    main_mutex = acquire_mutex(MAIN_MUTEX_NAME)
    if main_mutex is False:
        return

    if not show_school_class_prompt():
        return
    ensure_display_running()
    tray_click_action = load_tray_click_action()
    main_control_events = create_main_control_events()

    def schedule_loop():
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
            # Check at wall-clock second boundaries so HH:MM:SS schedules do not wait
            # for the old 20-second polling interval to elapse.
            current = datetime.now()
            time.sleep(max(0.01, 1.0 - current.microsecond / 1_000_000))

    threading.Thread(target=schedule_loop, daemon=True).start()

    def open_dashboard(_icon=None, _item=None):
        launch_component("dashboard")

    def open_homework_editor(_icon=None, _item=None):
        launch_component("homework_editor")

    def preview_homework(_icon=None, _item=None):
        launch_component("dashboard", preview=True)

    def exit_hwm(icon, _item=None):
        shutdown_components()
        icon.stop()

    def wait_for_control_action():
        action = wait_for_main_action(main_control_events)
        if action == "exit":
            exit_hwm(icon)

    def on_icon_stop(_icon):
        close_main_control_events(main_control_events)

    click_action = open_dashboard if tray_click_action == "dashboard" else open_homework_editor
    menu = pystray.Menu(
        pystray.MenuItem("仪表盘", open_dashboard, default=click_action is open_dashboard),
        pystray.MenuItem(
            "项目编辑器",
            open_homework_editor,
            default=click_action is open_homework_editor,
        ),
        pystray.MenuItem("预览项目", preview_homework),
        pystray.MenuItem("退出 HWM", exit_hwm),
    )
    icon = pystray.Icon("HomeworkManager", create_tray_image(), "Homework Manager", menu)
    threading.Thread(target=wait_for_control_action, daemon=True).start()
    icon.run()
    on_icon_stop(icon)


def run_entry_point():
    if getattr(sys, "frozen", False) and "--component" in sys.argv:
        component_index = sys.argv.index("--component")
        if component_index + 1 >= len(sys.argv):
            raise ValueError("缺少组件名称")
        component = sys.argv[component_index + 1]
        component_modules = {
            "display": "HomeworkDisplay",
            "dashboard": "HWMConfigEditor",
            "homework_editor": "HomeworkEditor",
            "subscription_manager": "HWMSubscriptionManager",
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
        crash_log = RESOURCE_DIR / "hwm_crash.log"
        try:
            crash_log.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        raise


