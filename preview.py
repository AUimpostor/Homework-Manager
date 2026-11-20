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

import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from config import data_directory, load_config, load_assignment_data
from runtime import (
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
DATA_DIR = data_directory(APPLICATION_DIR)
CONFIG_FILE = DATA_DIR / "config.json"
ASSIGNMENT_FILE = DATA_DIR / "assignment.json"
SUBJECT_NAMES = {
    "chinese": "语文", "maths": "数学", "english": "英语", "history": "历史",
    "politics": "政治", "physics": "物理", "chemistry": "化学", "biology": "生物",
    "geography": "地理", "it": "信息", "pe": "体育", "art": "美术", "other": "其他",
}


def visible_sections():
    data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)
    sections = []
    for item in data:
        if not isinstance(item, dict):
            continue
        for subject, assignments in item.items():
            visible = []
            for assignment in assignments if isinstance(assignments, list) else []:
                if isinstance(assignment, str) and assignment.strip():
                    visible.append({"assignment": assignment.strip()})
                elif isinstance(assignment, dict) and not assignment.get("hide", False):
                    text = assignment.get("assignment", "")
                    if isinstance(text, str) and text.strip():
                        visible.append({
                            "assignment": text.strip(),
                            "ignore_prefix": assignment.get("ignore_prefix", False) is True,
                            "ignore_suffix": assignment.get("ignore_suffix", False) is True,
                            "secondary": assignment.get("secondary", False) is True,
                        })
            if visible:
                sections.append((SUBJECT_NAMES.get(subject, subject), visible))
    return sections


class Assignmentpreview:
    def __init__(self, root):
        self.root = root
        self.config = load_config(CONFIG_FILE)
        self.sections = visible_sections()
        self.shutdown_event = create_shutdown_event("assignment_preview")
        set_window_icon(root, __file__)
        root.title("预览作业")
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
        style = ttk.Style(self.root)
        if style.theme_use() == "classic":
            themes = style.theme_names()
            preferred_theme = "vista" if sys.platform == "win32" else "clam"
            if preferred_theme in themes:
                style.theme_use(preferred_theme)
        alignment = "w" if self.config.get("assignment_alignment") == "靠左" else "e"
        justify = "left" if alignment == "w" else "right"
        padx = max(1, round(float(self.config.get("content_padding_x_permill", 18)) / 1000 * self.root.winfo_screenwidth()))
        pady = max(1, round(float(self.config.get("content_padding_y_permill", 12)) / 1000 * self.root.winfo_screenheight()))
        base_size = max(1, int(self.config.get("assignment_font_size", 17)))
        content_frame = tk.Frame(self.root, background=background)
        preview = tk.Text(
            content_frame,
            wrap="none",
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
            takefocus=False,
        )
        self.base_sizes = {
            "subject": base_size,
            "assignment": base_size,
            "secondary": max(1, int(self.config.get("secondary_assignment_font_size", 14))),
            "empty": base_size,
        }
        self.preview_tags = {"subject": ("bold",), "assignment": (), "secondary": (), "empty": ()}
        self.preview = preview
        self.justify = justify
        self.zoom_percent = 100

        toolbar = ttk.Frame(self.root, padding=(8, 6))
        toolbar.pack(side="bottom", fill="x")
        ttk.Label(toolbar, text="缩放").pack(side="left", padx=(0, 6))
        ttk.Label(toolbar, text="10%").pack(side="left", padx=(0, 4))
        self.zoom_scale = ttk.Scale(
            toolbar,
            from_=10,
            to=500,
            orient="horizontal",
            command=self.set_zoom,
        )
        self.zoom_scale.pack(side="left", fill="x", expand=True)
        ttk.Label(toolbar, text="500%").pack(side="left", padx=(4, 8))
        self.zoom_label = ttk.Label(toolbar, text="100%", width=5, anchor="e")
        self.zoom_label.pack(side="right")
        self.zoom_scale.set(self.zoom_percent)
        content_frame.pack(fill="both", expand=True)

        if not self.sections:
            preview.insert("end", "（今天没有作业）", "empty")
        else:
            for section_index, (name, assignments) in enumerate(self.sections):
                preview.insert("end", name + "\n", "subject")
                for assignment in assignments:
                    prefix = "" if assignment.get("ignore_prefix", False) else self.config.get("assignment_prefix", "")
                    suffix = "" if assignment.get("ignore_suffix", False) else self.config.get("assignment_suffix", "")
                    text = "{}{}{}\n".format(prefix, assignment["assignment"], suffix)
                    tag = "secondary" if assignment.get("secondary", False) else "assignment"
                    preview.insert("end", text, tag)
                if section_index < len(self.sections) - 1:
                    preview.insert("end", "\n")

        # Keep the preview read-only.
        preview.bind("<KeyPress>", lambda event: "break")
        preview.bind("<<Paste>>", lambda event: "break")
        preview.bind("<<Cut>>", lambda event: "break")
        preview.bind("<<Clear>>", lambda event: "break")
        preview.bind("<<Undo>>", lambda event: "break")
        preview.bind("<<Redo>>", lambda event: "break")

        for tag, size in self.base_sizes.items():
            preview.tag_configure(
                tag,
                font=("Microsoft YaHei UI", size, *self.preview_tags[tag]),
                justify=self.justify,
            )

        # Connect both scroll directions so long assignments remain reachable at
        # high zoom levels.
        vertical_scrollbar = ttk.Scrollbar(
            content_frame, orient="vertical", command=preview.yview
        )
        horizontal_scrollbar = ttk.Scrollbar(
            content_frame, orient="horizontal", command=preview.xview
        )
        preview.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        preview.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

    def set_zoom(self, value):
        zoom_percent = max(10, min(500, int(round(float(value)))))
        self.zoom_percent = zoom_percent
        self.zoom_label.configure(text="{}%".format(zoom_percent))
        for tag, base_size in self.base_sizes.items():
            size = max(1, int(base_size * zoom_percent / 100 + 0.5))
            self.preview.tag_configure(
                tag,
                font=("Microsoft YaHei UI", size, *self.preview_tags[tag]),
            )


def main():
    enable_high_dpi()
    root = tk.Tk()
    Assignmentpreview(root)
    root.mainloop()


if __name__ == "__main__":
    main()
