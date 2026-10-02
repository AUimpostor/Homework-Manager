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
import os
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path


CONFIG_RELOAD_EVENTS = {
    "display": "Local\\HomeworkDisplayConfigReload",
    "config_editor": "Local\\HomeworkConfigEditorReload",
    "homework_editor": "Local\\HomeworkProjectEditorReload",
}
SHUTDOWN_EVENTS = {
    "display": "Local\\HomeworkDisplayShutdown",
    "config_editor": "Local\\HomeworkConfigEditorShutdown",
    "homework_editor": "Local\\HomeworkProjectEditorShutdown",
    "subscription_manager": "Local\\HomeworkSubscriptionManagerShutdown",
}
MAIN_CONTROL_EVENTS = {
    "exit": "Local\\HomeworkManagerExit",
}


def enable_high_dpi():
    """Enable Windows DPI awareness before creating a Tk root window."""
    if sys.platform != "win32":
        return True
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                return False
    return True


def configure_tk_scaling(window):
    """Set Tk's point scaling from the current display DPI."""
    try:
        scaling = window.winfo_fpixels("1i") / 72.0
        window.tk.call("tk", "scaling", scaling)
        return scaling
    except (AttributeError, tk.TclError):
        return 1.0


def set_window_size_percent(window, width_percent, height_percent, lock_minimum=False):
    width = round(window.winfo_screenwidth() * width_percent / 100)
    height = round(window.winfo_screenheight() * height_percent / 100)
    window.geometry("{}x{}".format(width, height))
    if lock_minimum:
        window.minsize(width, height)


def set_window_icon(window, module_file, default_only=True):
    if getattr(sys, "frozen", False):
        icon_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)) / "hwm.ico"
    else:
        icon_path = Path(module_file).resolve().parent / "hwm.ico"
    try:
        if icon_path.is_file():
            if default_only:
                window.iconbitmap(default=str(icon_path))
            else:
                window.iconbitmap(str(icon_path))
    except (OSError, RuntimeError):
        pass


def enable_touch_keyboard(window):
    if sys.platform != "win32" or getattr(window, "_hwm_touch_keyboard_bound", False):
        return

    user32 = ctypes.windll.user32
    digitizer = user32.GetSystemMetrics(94)
    if not (digitizer & 0x80 and digitizer & 0x03):
        return

    get_extra_info = user32.GetMessageExtraInfo
    get_extra_info.restype = ctypes.c_size_t
    find_window = user32.FindWindowW
    find_window.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    find_window.restype = ctypes.c_void_p
    is_window_visible = user32.IsWindowVisible
    is_window_visible.argtypes = [ctypes.c_void_p]
    is_window_visible.restype = ctypes.c_bool
    common_files = os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files")
    tabtip = Path(common_files) / "Microsoft Shared" / "ink" / "TabTip.exe"
    if not tabtip.is_file():
        return

    last_launch = {"time": 0.0}

    def on_pointer_press(event):
        info = int(get_extra_info())
        if (info & 0xFFFFFF00) != 0xFF515700 or not (info & 0x80):
            return
        if event.widget.winfo_class() not in {
            "Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox"
        }:
            return

        now = time.monotonic()
        if now - last_launch["time"] < 1.0:
            return
        last_launch["time"] = now
        keyboard = find_window("IPTip_Main_Window", None)
        if keyboard and is_window_visible(keyboard):
            return
        try:
            subprocess.Popen([str(tabtip)], close_fds=True)
        except OSError:
            pass

    window.bind_all("<ButtonPress-1>", on_pointer_press, add="+")
    window._hwm_touch_keyboard_bound = True


def notify_config_saved():
    if sys.platform != "win32":
        return

    kernel32 = ctypes.windll.kernel32
    for event_name in CONFIG_RELOAD_EVENTS.values():
        event = kernel32.OpenEventW(0x0002, False, event_name)
        if event:
            kernel32.SetEvent(event)
            kernel32.CloseHandle(event)


def create_config_reload_event(component="display"):
    if sys.platform != "win32":
        return None

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
    event_name = CONFIG_RELOAD_EVENTS.get(component, component)
    return kernel32.CreateEventW(None, False, False, event_name)


def wait_for_config_reload(event):
    if event is None:
        return False

    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    return kernel32.WaitForSingleObject(event, 0xFFFFFFFF) == 0


def close_config_reload_event(event):
    if event is not None and sys.platform == "win32":
        ctypes.windll.kernel32.CloseHandle(event)


def create_shutdown_event(component):
    if sys.platform != "win32":
        return None

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = [
        ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p
    ]
    kernel32.ResetEvent.argtypes = [ctypes.c_void_p]
    event_name = SHUTDOWN_EVENTS[component]
    event = kernel32.CreateEventW(None, True, False, event_name)
    if event:
        kernel32.ResetEvent(event)
    return event


def wait_for_shutdown(event):
    if event is None:
        return False

    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    return kernel32.WaitForSingleObject(event, 0xFFFFFFFF) == 0


def request_shutdown(component):
    if sys.platform != "win32":
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.restype = ctypes.c_void_p
    kernel32.OpenEventW.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.SetEvent.argtypes = [ctypes.c_void_p]
    event = kernel32.OpenEventW(0x0002, False, SHUTDOWN_EVENTS[component])
    if event:
        kernel32.SetEvent(event)
        kernel32.CloseHandle(event)


def close_shutdown_event(event):
    if event is not None and sys.platform == "win32":
        ctypes.windll.kernel32.CloseHandle(event)


def request_main_action(action):
    if sys.platform != "win32":
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.restype = ctypes.c_void_p
    kernel32.OpenEventW.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.SetEvent.argtypes = [ctypes.c_void_p]
    event = kernel32.OpenEventW(0x0002, False, MAIN_CONTROL_EVENTS[action])
    if event:
        kernel32.SetEvent(event)
        kernel32.CloseHandle(event)


def create_main_control_events():
    if sys.platform != "win32":
        return {}

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = [
        ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p
    ]
    events = {}
    for action, event_name in MAIN_CONTROL_EVENTS.items():
        events[action] = kernel32.CreateEventW(None, False, False, event_name)
    return events


def wait_for_main_action(events):
    if not events:
        return False

    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    while True:
        for action, event in events.items():
            if event and kernel32.WaitForSingleObject(event, 100) == 0:
                return action


def close_main_control_events(events):
    if sys.platform == "win32":
        for event in events.values():
            if event:
                ctypes.windll.kernel32.CloseHandle(event)


