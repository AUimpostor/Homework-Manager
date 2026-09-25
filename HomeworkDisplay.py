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
import tkinter as tk
import tkinter.font as tkfont
import ctypes
import threading
from pathlib import Path
from HWMRuntime import (
    close_config_reload_event,
    close_shutdown_event,
    configure_tk_scaling,
    create_config_reload_event,
    create_shutdown_event,
    enable_high_dpi,
	wait_for_config_reload,
	wait_for_shutdown,
	set_window_icon,
)
from HWMConfig import DEFAULT_CONFIG, load_config, load_homework_data


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




def acquire_single_instance():
	if sys.platform != "win32":
		return True

	kernel32 = ctypes.windll.kernel32
	kernel32.CreateMutexW.restype = ctypes.c_void_p
	kernel32.GetLastError.restype = ctypes.c_ulong
	kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

	mutex = kernel32.CreateMutexW(None, False, "Local\\HomeworkDisplaySingleInstance")
	if not mutex:
		return True
	if kernel32.GetLastError() == 183:
		kernel32.CloseHandle(mutex)
		return False

	return mutex


def format_homework(work_list):
	sections = []
	for subject_work in work_list:
		if not isinstance(subject_work, dict):
			raise ValueError("homework.json 中的每个科目必须是 JSON 对象")

		for subject, homework in subject_work.items():
			if not isinstance(homework, list):
				raise ValueError("科目作业必须是 JSON 数组")

			assignments = []
			for assignment in homework:
				if isinstance(assignment, str) and assignment.strip():
					assignments.append(assignment.strip())
				elif isinstance(assignment, dict):
					text = assignment.get("project", assignment.get("subject"))
					if (
						isinstance(text, str)
						and text.strip()
						and assignment.get("hide", False) is not True
					):
						assignments.append(text.strip())
			if assignments:
				subject_name = SUBJECT_NAMES.get(subject, subject)
				sections.append((subject_name, assignments))

	return sections


def load_document():
	config = load_config(CONFIG_FILE)
	data = load_homework_data(HOMEWORK_FILE, CONFIG_FILE)

	for key in (
		"title_width", "title_length", "title_font_size", "project_font_size",
		"title_guide_line_width",
		"display_range_left", "display_range_right", "display_range_top",
		"display_range_bottom", "content_padding_x", "content_padding_y",
		"section_spacing", "scroll_start_delay", "scroll_step_interval",
		"scroll_end_pause", "restart_pause", "fade_interval",
	):
		try:
			config[key] = max(1, int(config[key]))
		except (TypeError, ValueError, KeyError):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("scroll_step_size", "fade_step"):
		try:
			config[key] = float(config[key])
		except (TypeError, ValueError, KeyError):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("display_range_left", "display_range_right", "display_range_top", "display_range_bottom"):
		config[key] = min(100, config[key])
	if config["display_range_right"] <= config["display_range_left"]:
		config["display_range_left"] = DEFAULT_CONFIG["display_range_left"]
		config["display_range_right"] = DEFAULT_CONFIG["display_range_right"]
	if config["display_range_bottom"] <= config["display_range_top"]:
		config["display_range_top"] = DEFAULT_CONFIG["display_range_top"]
		config["display_range_bottom"] = DEFAULT_CONFIG["display_range_bottom"]
	config["window_alpha"] = min(1.0, max(0.1, float(config.get("window_alpha", DEFAULT_CONFIG["window_alpha"]))))
	config["scroll_step_size"] = min(1.0, max(0.0001, config["scroll_step_size"]))
	config["fade_step"] = min(1.0, max(0.01, config["fade_step"]))
	for key in ("project_prefix", "project_suffix"):
		if not isinstance(config.get(key), str):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("title_alignment", "project_alignment"):
		if config.get(key) not in ("靠左", "靠右"):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("title_font_color", "project_font_color", "title_primary_color", "title_secondary_color"):
		if not isinstance(config.get(key), str) or not config[key].strip():
			config[key] = DEFAULT_CONFIG[key]

	return config, format_homework(data)


def main():
	instance_mutex = acquire_single_instance()
	if instance_mutex is False:
		return

	enable_high_dpi()
	config, _ = load_document()
	root = tk.Tk()
	set_window_icon(root, __file__)
	configure_tk_scaling(root)
	root.title("今日作业")
	root.overrideredirect(True)
	transparent_color = "#010203"
	root.configure(background=transparent_color)
	root.attributes("-transparentcolor", transparent_color)
	max_alpha = config["window_alpha"]
	root.attributes("-alpha", max_alpha)

	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	window_left = int(screen_width * config["display_range_left"] / 100)
	window_right = int(screen_width * config["display_range_right"] / 100)
	left = window_left
	window_width = window_right - window_left
	top = int(screen_height * config["display_range_top"] / 100)
	window_bottom = int(screen_height * config["display_range_bottom"] / 100)
	window_height = window_bottom - top
	root.geometry("{}x{}+{}+{}".format(window_width, window_height, left, top))

	scroll_canvas = tk.Canvas(
		root,
		highlightthickness=0,
		background=transparent_color,
	)
	scroll_canvas.pack(
		fill="both", expand=True,
		padx=config["content_padding_x"], pady=config["content_padding_y"],
	)

	content = tk.Frame(scroll_canvas, background=transparent_color)
	content_window = scroll_canvas.create_window(
		(0, 0),
		window=content,
		anchor="nw",
	)
	scroll_canvas.tag_raise(content_window)

	def update_content_width(event):
		scroll_canvas.itemconfigure(content_window, width=event.width)

	def update_scroll_region(_event=None):
		scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

	scroll_canvas.bind("<Configure>", update_content_width)
	content.bind("<Configure>", update_scroll_region)

	def apply_window_config():
		nonlocal max_alpha
		max_alpha = config["window_alpha"]
		root.attributes("-alpha", max_alpha)
		window_left = int(screen_width * config["display_range_left"] / 100)
		window_right = int(screen_width * config["display_range_right"] / 100)
		top = int(screen_height * config["display_range_top"] / 100)
		window_bottom = int(screen_height * config["display_range_bottom"] / 100)
		root.geometry("{}x{}+{}+{}".format(
			window_right - window_left,
			window_bottom - top,
			window_left,
			top,
		))
		scroll_canvas.pack_configure(
			padx=config["content_padding_x"],
			pady=config["content_padding_y"],
		)

	def render_homework():
		nonlocal config
		config, sections = load_document()
		apply_window_config()
		for child in content.winfo_children():
			child.destroy()

		for subject_name, assignments in sections:
			section = tk.Frame(content, background=transparent_color)
			section.pack(fill="x", anchor="e", pady=(0, config["section_spacing"]))

			header_font = tkfont.Font(
				family="Microsoft YaHei UI", size=config["title_font_size"], weight="bold"
			)
			header_text = "{}".format(subject_name)
			header_height = max(1, config["title_length"])
			main_width = max(1, config["title_width"])
			theme = config.get("title_theme", "默认")
			secondary_width = max(1, config.get("title_guide_line_width", 10)) if theme == "默认" else 0
			canvas_width = main_width + secondary_width if theme == "默认" else main_width
			header = tk.Canvas(
				section,
				width=canvas_width + 5,
				height=header_height + 4,
				highlightthickness=0,
				background=transparent_color,
			)
			primary = config["title_primary_color"]
			secondary = config["title_secondary_color"]
			opacity = max(0, min(100, int(config.get("title_outline_opacity", 25)))) / 100.0
			def outline_color(color):
				if opacity <= 0:
					return transparent_color
				try:
					foreground = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
					background = tuple(int(transparent_color[index:index + 2], 16) for index in (1, 3, 5))
					return "#" + "".join(
						"{:02X}".format(round(bg + (fg - bg) * opacity))
						for fg, bg in zip(foreground, background)
					)
				except (ValueError, TypeError, IndexError):
					return color
			primary_outline = outline_color(primary)
			secondary_outline = outline_color(secondary)
			if theme == "默认":
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_rectangle(main_width, 0, main_width + secondary_width, header_height, fill=secondary, outline=secondary_outline)
			elif theme == "圆角标签":
				radius = min(12, header_height // 3, main_width // 8)
				header.create_polygon(
					radius, 0, main_width-radius, 0, main_width, radius,
					main_width, header_height-radius, main_width-radius, header_height,
					radius, header_height, 0, header_height-radius, 0, radius,
					fill=primary, outline=primary_outline, smooth=True, splinesteps=12,
				)
				dot = max(4, min(12, header_height // 4))
				header.create_oval(10, (header_height-dot)//2, 10+dot, (header_height+dot)//2, fill=secondary, outline=secondary_outline)
			elif theme == "左侧标记":
				mark = max(1, min(header_height, config.get("title_guide_line_width", 10)))
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_rectangle(0, 0, mark, header_height, fill=secondary, outline=secondary_outline)
			elif theme == "底边强调":
				bar = max(1, min(header_height, config.get("title_guide_line_width", 10)))
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_rectangle(0, header_height-bar, main_width, header_height, fill=secondary, outline=secondary_outline)
			elif theme == "顶面强调":
				bar = max(1, min(header_height, config.get("title_guide_line_width", 10)))
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_rectangle(0, 0, main_width, bar, fill=secondary, outline=secondary_outline)
			elif theme == "角标标题":
				cut = min(18, header_height // 3, main_width // 6)
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_polygon(main_width-cut, 0, main_width, 0, main_width, cut, fill=secondary, outline=secondary_outline)
			else:
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
			title_is_left = config["title_alignment"] == "靠左"
			project_is_left = config["project_alignment"] == "靠左"
			header.create_text(
				10 if title_is_left else main_width - 10,
				header_height // 2,
				text=header_text,
				anchor="w" if title_is_left else "e",
				font=header_font,
				fill=config["title_font_color"],
			)
			header.pack(anchor="w" if title_is_left else "e")

			homework = tk.Label(
				section,
				text="\n".join(
					"{}{}{}".format(
						config["project_prefix"], assignment, config["project_suffix"]
					)
					for assignment in assignments
				),
				anchor="w" if project_is_left else "e",
				justify="left" if project_is_left else "right",
				font=("Microsoft YaHei UI", config["project_font_size"]),
				foreground=config["project_font_color"],
				background=transparent_color,
			)
			homework.pack(anchor="w" if project_is_left else "e", pady=(4, 0))

	render_homework()
	animation_generation = 0
	animation_after_ids = []

	def schedule_animation(delay_ms, callback, *args):
		after_id = root.after(max(0, int(delay_ms)), callback, *args)
		animation_after_ids.append(after_id)
		return after_id

	def cancel_animation_jobs():
		for after_id in list(animation_after_ids):
			try:
				root.after_cancel(after_id)
			except Exception:
				pass
		animation_after_ids.clear()

	def reload_homework():
		nonlocal animation_generation
		try:
			cancel_animation_jobs()
			render_homework()
			animation_generation += 1
			root.attributes("-alpha", max_alpha)
			scroll_canvas.yview_moveto(0)
			schedule_animation(100, auto_scroll)
		except (OSError, json.JSONDecodeError, ValueError) as error:
			print("刷新作业列表失败：{}".format(error))

	reload_event = create_config_reload_event()
	shutdown_event = create_shutdown_event("display")

	def wait_for_reload():
		if wait_for_config_reload(reload_event):
			root.after(0, reload_homework)
			threading.Thread(target=wait_for_reload, daemon=True).start()

	if reload_event is not None:
		threading.Thread(target=wait_for_reload, daemon=True).start()

	def wait_for_shutdown_signal():
		if wait_for_shutdown(shutdown_event):
			root.after(0, close_display)

	if shutdown_event is not None:
		threading.Thread(target=wait_for_shutdown_signal, daemon=True).start()

	def auto_scroll():
		nonlocal animation_generation
		animation_generation += 1
		generation = animation_generation

		bounds = scroll_canvas.bbox("all")
		if not bounds:
			return

		content_height = bounds[3] - bounds[1]
		viewport_height = scroll_canvas.winfo_height()
		if viewport_height <= 1:
			schedule_animation(100, auto_scroll)
			return
		if content_height <= viewport_height:
			return

		scroll_canvas.yview_moveto(0)

		def scroll_step():
			if generation != animation_generation:
				return
			first, last = scroll_canvas.yview()
			if last >= 1:
				schedule_animation(config["scroll_end_pause"], scroll_to_top)
				return

			scroll_canvas.yview_moveto(min(first + config["scroll_step_size"], 1))
			schedule_animation(config["scroll_step_interval"], scroll_step)

		def scroll_to_top():
			fade_out()

		def fade_out(alpha=max_alpha):
			if generation != animation_generation:
				return
			alpha -= config["fade_step"]
			if alpha <= 0:
				root.attributes("-alpha", 0)
				scroll_canvas.yview_moveto(0)
				schedule_animation(config["restart_pause"], fade_in)
				return

			root.attributes("-alpha", alpha)
			schedule_animation(config["fade_interval"], fade_out, alpha)

		def fade_in(alpha=0):
			if generation != animation_generation:
				return
			alpha += config["fade_step"]
			if alpha >= max_alpha:
				root.attributes("-alpha", max_alpha)
				schedule_animation(config["scroll_start_delay"], scroll_step)
				return

			root.attributes("-alpha", alpha)
			schedule_animation(config["fade_interval"], fade_in, alpha)

		schedule_animation(config["scroll_start_delay"], scroll_step)

	schedule_animation(100, auto_scroll)
	def close_display():
		cancel_animation_jobs()
		close_config_reload_event(reload_event)
		close_shutdown_event(shutdown_event)
		root.destroy()

	root.bind("<Escape>", lambda _event: close_display())
	root.mainloop()


if __name__ == "__main__":
	main()


