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
import sys
import threading
import tkinter as tk
from pathlib import Path

from HWMConfig import load_config, load_homework_data
from HWMRuntime import (
    close_shutdown_event,
    configure_tk_scaling,
    create_shutdown_event,
    enable_high_dpi,
    place_window_bottom_right,
    set_window_icon,
    set_window_size_percent,
    wait_for_shutdown,
)


APPLICATION_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
CONFIG_FILE = APPLICATION_DIR / "config.json"
HOMEWORK_FILE = APPLICATION_DIR / "homework.json"
SUBJECT_NAMES = {
    "chinese": "语文", "maths": "数学", "english": "英语", "history": "历史",
    "politics": "政治", "physics": "物理", "chemistry": "化学", "biology": "生物",
    "geography": "地理", "it": "信息", "pe": "体育", "art": "美术", "other": "其他",
}


def visible_sections():
    data = load_homework_data(HOMEWORK_FILE, CONFIG_FILE)
    sections = []
    for item in data:
        if not isinstance(item, dict):
            continue
        for subject, assignments in item.items():
            visible = []
            for assignment in assignments if isinstance(assignments, list) else []:
                if isinstance(assignment, str) and assignment.strip():
                    visible.append({"project": assignment.strip()})
                elif isinstance(assignment, dict) and not assignment.get("hide", False):
                    text = assignment.get("project", "")
                    if isinstance(text, str) and text.strip():
                        visible.append({
                            "project": text.strip(),
                            "ignore_prefix": assignment.get("ignore_prefix", False) is True,
                            "ignore_suffix": assignment.get("ignore_suffix", False) is True,
                            "secondary": assignment.get("secondary", False) is True,
                        })
            if visible:
                sections.append((SUBJECT_NAMES.get(subject, subject), visible))
    return sections


class ProjectPreview:
    def __init__(self, root):
        self.root = root
        self.config = load_config(CONFIG_FILE)
        self.sections = visible_sections()
        self.shutdown_event = create_shutdown_event("project_preview")
        self.zoom = 1.0
        self.minimum_zoom = 0.5
        self.maximum_zoom = 3.0
        self._touch_gesture_proc = None
        set_window_icon(root, __file__)
        root.title("预览项目")
        configure_tk_scaling(root)
        set_window_size_percent(root, 20, 50)
        # Keep the native title bar's maximize/restore and close controls,
        # while hiding minimize (WS_MINIMIZEBOX).
        root.resizable(True, True)
        root.update_idletasks()
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -16)
                style &= ~0x00020000
                ctypes.windll.user32.SetWindowLongW(hwnd, -16, style)
            except (AttributeError, OSError):
                pass
        place_window_bottom_right(root)
        self.build_preview()
        if self.shutdown_event is not None:
            threading.Thread(target=self.wait_for_shutdown_signal, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        close_shutdown_event(self.shutdown_event)
        self.root.destroy()

    def wait_for_shutdown_signal(self):
        if wait_for_shutdown(self.shutdown_event):
            self.root.after(0, self.close)

    def build_preview(self):
        background = "#FFFFFF"
        self.root.configure(background=background)
        alignment = "w" if self.config.get("project_alignment") == "靠左" else "e"
        justify = "left" if alignment == "w" else "right"
        padx = max(1, round(float(self.config.get("content_padding_x_permill", 18)) / 1000 * self.root.winfo_screenwidth()))
        pady = max(1, round(float(self.config.get("content_padding_y_permill", 12)) / 1000 * self.root.winfo_screenheight()))
        base_size = max(1, int(self.config.get("project_font_size", 17)))
        preview = tk.Text(
            self.root,
            wrap="word",
            undo=False,
            bg=background,
            fg="#000000",
            insertbackground="#000000",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            insertwidth=0,
            insertofftime=0,
            insertontime=0,
            padx=padx,
            pady=pady,
            font=("Microsoft YaHei UI", base_size),
            cursor="arrow",
            takefocus=True,
        )
        preview.pack(fill="both", expand=True)
        self.base_sizes = {
            "subject": base_size,
            "project": base_size,
            "secondary": max(1, int(self.config.get("secondary_project_font_size", 14))),
            "empty": base_size,
        }
        self.preview_tags = {"subject": ("bold",), "project": (), "secondary": (), "empty": ()}
        self.preview = preview
        self.justify = justify
        self.apply_zoom()

        if not self.sections:
            preview.insert("end", "（今天没有作业）", "empty")
        else:
            for section_index, (name, assignments) in enumerate(self.sections):
                preview.insert("end", name + "\n", "subject")
                for assignment in assignments:
                    prefix = "" if assignment.get("ignore_prefix", False) else self.config.get("project_prefix", "")
                    suffix = "" if assignment.get("ignore_suffix", False) else self.config.get("project_suffix", "")
                    text = "{}{}{}\n".format(prefix, assignment["project"], suffix)
                    tag = "secondary" if assignment.get("secondary", False) else "project"
                    preview.insert("end", text, tag)
                if section_index < len(self.sections) - 1:
                    preview.insert("end", "\n")

        # A disabled Text widget cannot be selected/copied, so block edits at
        # the key-event layer while leaving normal selection and Ctrl+C intact.
        preview.bind("<KeyPress>", lambda event: "break")
        preview.bind("<<Paste>>", lambda event: "break")
        preview.bind("<<Cut>>", lambda event: "break")
        preview.bind("<<Clear>>", lambda event: "break")
        preview.bind("<<Undo>>", lambda event: "break")
        preview.bind("<<Redo>>", lambda event: "break")
        preview.bind("<Button-1>", lambda _event: preview.focus_set(), add="+")
        preview.bind("<MouseWheel>", self.on_mousewheel, add="+")
        preview.bind("<Control-MouseWheel>", self.on_mousewheel, add="+")
        preview.bind("<Button-4>", lambda event: self.change_zoom(0.1), add="+")
        preview.bind("<Button-5>", lambda event: self.change_zoom(-0.1), add="+")
        if sys.platform == "win32":
            self.enable_windows_touch_zoom()

    def apply_zoom(self):
        for tag, size in self.base_sizes.items():
            self.preview.tag_configure(
                tag,
                font=("Microsoft YaHei UI", max(1, round(size * self.zoom)), *self.preview_tags[tag]),
                justify=self.justify,
            )

    def change_zoom(self, amount):
        self.zoom = min(self.maximum_zoom, max(self.minimum_zoom, self.zoom + amount))
        self.apply_zoom()
        return "break"

    def on_mousewheel(self, event):
        delta = getattr(event, "delta", 0)
        if not delta:
            return "break"
        self.change_zoom(0.1 if delta > 0 else -0.1)
        return "break"

    def enable_windows_touch_zoom(self):
        """Handle Windows WM_GESTURE pinch events for native touchscreens."""
        try:
            from ctypes import wintypes

            class GESTUREINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.UINT),
                    ("dwFlags", wintypes.DWORD),
                    ("dwID", wintypes.DWORD),
                    ("hwndTarget", wintypes.HWND),
                    ("ptsLocation", wintypes.POINT),
                    ("dwInstanceID", wintypes.DWORD),
                    ("dwSequenceID", wintypes.DWORD),
                    ("ullArguments", ctypes.c_uint64),
                    ("cbExtraArgs", wintypes.UINT),
                ]
            user32 = ctypes.windll.user32
            get_gesture_info = user32.GetGestureInfo
            get_gesture_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(GESTUREINFO)]
            get_gesture_info.restype = wintypes.BOOL
            close_gesture_info = user32.CloseGestureInfoHandle
            close_gesture_info.argtypes = [wintypes.HANDLE]
            close_gesture_info.restype = wintypes.BOOL
            self.root.update_idletasks()
            hwnd = user32.GetParent(self.root.winfo_id())
            get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_window_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            pointer_type = ctypes.c_ssize_t if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
            get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
            get_window_long.restype = pointer_type
            set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, pointer_type]
            set_window_long.restype = pointer_type
            user32.CallWindowProcW.argtypes = [
                pointer_type, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
            ]
            user32.CallWindowProcW.restype = ctypes.c_ssize_t
            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
            )
            previous = get_window_long(hwnd, -4)
            gesture_state = {"last_distance": None}

            def window_proc(window, message, wparam, lparam):
                if message == 0x0119:  # WM_GESTURE
                    info = GESTUREINFO()
                    info.cbSize = ctypes.sizeof(GESTUREINFO)
                    if get_gesture_info(wintypes.HANDLE(lparam), ctypes.byref(info)):
                        try:
                            if info.dwID == 4:  # GID_ZOOM
                                distance = info.ullArguments
                                if info.dwFlags & 1:  # GF_BEGIN
                                    gesture_state["last_distance"] = distance
                                else:
                                    last = gesture_state.get("last_distance")
                                    if last:
                                        change = 0.1 if distance > last else -0.1
                                        self.change_zoom(change)
                                    gesture_state["last_distance"] = distance
                                if info.dwFlags & 2:  # GF_END
                                    gesture_state["last_distance"] = None
                        finally:
                            close_gesture_info(wintypes.HANDLE(lparam))
                    return 0
                return user32.CallWindowProcW(previous, window, message, wparam, lparam)

            self._touch_gesture_proc = callback_type(window_proc)
            callback_address = ctypes.cast(self._touch_gesture_proc, ctypes.c_void_p).value
            set_window_long(hwnd, -4, pointer_type(callback_address))
        except (AttributeError, OSError, TypeError, ValueError):
            self._touch_gesture_proc = None


def main():
    enable_high_dpi()
    root = tk.Tk()
    ProjectPreview(root)
    root.mainloop()


if __name__ == "__main__":
    main()
