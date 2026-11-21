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
from runtime import (
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
from config import (
    DEFAULT_CONFIG,
    DISPLAY_ANIMATION_DEFAULTS,
    DISPLAY_ANIMATION_REGISTRY,
    TITLE_THEME_DEFAULTS,
    data_directory,
    load_config,
    load_assignment_data,
    load_display_animation_params,
    load_title_theme_params,
)


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




def acquire_single_instance():
	if sys.platform != "win32":
		return True

	kernel32 = ctypes.windll.kernel32
	kernel32.CreateMutexW.restype = ctypes.c_void_p
	kernel32.GetLastError.restype = ctypes.c_ulong
	kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

	mutex = kernel32.CreateMutexW(None, False, "Local\\displaySingleInstance")
	if not mutex:
		return True
	if kernel32.GetLastError() == 183:
		kernel32.CloseHandle(mutex)
		return False

	return mutex


def format_assignment(work_list):
	sections = []
	for subject_work in work_list:
		if not isinstance(subject_work, dict):
			raise ValueError("assignment.json 中的每个科目必须是 JSON 对象")

		for subject, entries in subject_work.items():
			if not isinstance(entries, list):
				raise ValueError("科目作业必须是 JSON 数组")

			assignments = []
			for assignment in entries:
				if isinstance(assignment, str) and assignment.strip():
					assignments.append({"assignment": assignment.strip()})
				elif isinstance(assignment, dict):
					text = assignment.get("assignment")
					if (
						isinstance(text, str)
						and text.strip()
						and assignment.get("hide", False) is not True
					):
						assignments.append({
							"assignment": text.strip(),
							"ignore_prefix": assignment.get("ignore_prefix", False) is True,
							"ignore_suffix": assignment.get("ignore_suffix", False) is True,
							"secondary": assignment.get("secondary", False) is True,
						})
			if assignments:
				subject_name = SUBJECT_NAMES.get(subject, subject)
				sections.append((subject_name, assignments))

	return sections


def load_document():
	config = load_config(CONFIG_FILE)
	data = load_assignment_data(ASSIGNMENT_FILE, CONFIG_FILE)
	animation_name = config.get("display_animation", DEFAULT_CONFIG["display_animation"])
	animation_defaults = DISPLAY_ANIMATION_DEFAULTS.get(
		animation_name
	) or next(iter(DISPLAY_ANIMATION_DEFAULTS.values()))
	config.update(load_display_animation_params(APPLICATION_DIR, animation_name))
	theme_name = config.get("title_theme", DEFAULT_CONFIG["title_theme"])
	theme_defaults = TITLE_THEME_DEFAULTS.get(
		theme_name
	) or next(iter(TITLE_THEME_DEFAULTS.values()))
	config.update(load_title_theme_params(APPLICATION_DIR, theme_name))
	defaults = dict(DEFAULT_CONFIG)
	defaults.update(animation_defaults)
	defaults.update(theme_defaults)
	for spec in DISPLAY_ANIMATION_REGISTRY.values():
		defaults.update(spec["defaults"])

	for key in (
		"title_width_permill", "title_length_permill", "title_font_size", "assignment_font_size", "secondary_assignment_font_size",
		"title_guide_line_width_permill",
		"display_range_left_percent", "display_range_right_percent", "display_range_top_percent",
		"display_range_bottom_percent", "content_padding_x_permill", "content_padding_y_permill",
		"section_spacing_permill", "scroll_start_delay", "scroll_step_interval",
		"scroll_end_pause", "restart_pause", "fade_interval",
		"seamless_start_delay", "seamless_step_interval",
		"seamless_step_size",
	):
		try:
			config[key] = max(1, int(config[key]))
		except (TypeError, ValueError, KeyError):
			config[key] = defaults[key]
	try:
		config["seamless_loop_pause"] = max(0, int(config["seamless_loop_pause"]))
	except (TypeError, ValueError, KeyError):
		config["seamless_loop_pause"] = defaults["seamless_loop_pause"]
	try:
		config["seamless_loop_gap_permill"] = min(
			1000,
			max(0, int(config["seamless_loop_gap_permill"])),
		)
	except (TypeError, ValueError, KeyError):
		config["seamless_loop_gap_permill"] = defaults["seamless_loop_gap_permill"]
	try:
		scroll_step_size = float(config["scroll_step_size"])
		if 0 < scroll_step_size < 1:
			scroll_step_size *= 1000
		config["scroll_step_size"] = min(1000, max(1, int(round(scroll_step_size))))
	except (TypeError, ValueError, KeyError):
		config["scroll_step_size"] = defaults["scroll_step_size"]
	try:
		fade_step = float(config["fade_step"])
		if 0 < fade_step < 1:
			fade_step *= 100
		config["fade_step"] = min(100, max(1, int(round(fade_step))))
	except (TypeError, ValueError, KeyError):
		config["fade_step"] = defaults["fade_step"]
	for key in ("display_range_left_percent", "display_range_right_percent", "display_range_top_percent", "display_range_bottom_percent"):
		config[key] = min(100, config[key])
	for key in (
		"title_width_permill", "title_length_permill", "title_guide_line_width_permill",
		"content_padding_x_permill", "content_padding_y_permill", "section_spacing_permill",
	):
		try:
			config[key] = max(1, min(1000, int(config[key])))
		except (TypeError, ValueError, KeyError):
			config[key] = defaults[key]
	if config["display_range_right_percent"] <= config["display_range_left_percent"]:
		config["display_range_left_percent"] = DEFAULT_CONFIG["display_range_left_percent"]
		config["display_range_right_percent"] = DEFAULT_CONFIG["display_range_right_percent"]
	if config["display_range_bottom_percent"] <= config["display_range_top_percent"]:
		config["display_range_top_percent"] = DEFAULT_CONFIG["display_range_top_percent"]
		config["display_range_bottom_percent"] = DEFAULT_CONFIG["display_range_bottom_percent"]
	config["window_alpha"] = min(1.0, max(0.1, float(config.get("window_alpha", DEFAULT_CONFIG["window_alpha"]))))
	for key in ("assignment_prefix", "assignment_suffix"):
		if not isinstance(config.get(key), str):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("title_alignment", "assignment_alignment"):
		if config.get(key) not in ("靠左", "靠右"):
			config[key] = DEFAULT_CONFIG[key]
	for key in ("title_font_color", "assignment_font_color", "secondary_assignment_font_color", "title_primary_color", "title_secondary_color"):
		if not isinstance(config.get(key), str) or not config[key].strip():
			config[key] = defaults[key]

	return config, format_assignment(data)


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
	def permill_x(value):
		return max(1, round(screen_width * value / 1000))
	def permill_y(value):
		return max(1, round(screen_height * value / 1000))

	window_left = int(screen_width * config["display_range_left_percent"] / 100)
	window_right = int(screen_width * config["display_range_right_percent"] / 100)
	left = window_left
	window_width = window_right - window_left
	top = int(screen_height * config["display_range_top_percent"] / 100)
	window_bottom = int(screen_height * config["display_range_bottom_percent"] / 100)
	window_height = window_bottom - top
	root.geometry("{}x{}+{}+{}".format(window_width, window_height, left, top))

	scroll_canvas = tk.Canvas(
		root,
		highlightthickness=0,
		background=transparent_color,
	)
	scroll_canvas.pack(
		fill="both", expand=True,
		padx=permill_x(config["content_padding_x_permill"]),
		pady=permill_y(config["content_padding_y_permill"]),
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
		window_left = int(screen_width * config["display_range_left_percent"] / 100)
		window_right = int(screen_width * config["display_range_right_percent"] / 100)
		top = int(screen_height * config["display_range_top_percent"] / 100)
		window_bottom = int(screen_height * config["display_range_bottom_percent"] / 100)
		root.geometry("{}x{}+{}+{}".format(
			window_right - window_left,
			window_bottom - top,
			window_left,
			top,
		))
		scroll_canvas.pack_configure(
			padx=permill_x(config["content_padding_x_permill"]),
			pady=permill_y(config["content_padding_y_permill"]),
		)

	original_content = None
	duplicate_content = None

	def render_assignment():
		nonlocal config, original_content, duplicate_content
		config, sections = load_document()
		apply_window_config()
		for child in content.winfo_children():
			child.destroy()
		original_content = None
		duplicate_content = None

		def render_sections(target):
			for subject_name, assignments in sections:
				section = tk.Frame(target, background=transparent_color)
				section.pack(fill="x", anchor="e", pady=(0, permill_y(config["section_spacing_permill"])))

				header_font = tkfont.Font(
					family="Microsoft YaHei UI", size=config["title_font_size"], weight="bold"
				)
				header_text = "{}".format(subject_name)
				header_height = permill_y(config["title_length_permill"])
				main_width = permill_x(config["title_width_permill"])
				guide_line_width = permill_x(config.get("title_guide_line_width_permill", 10))
				secondary_width = guide_line_width
				canvas_width = main_width + secondary_width
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
				header.create_rectangle(0, 0, main_width, header_height, fill=primary, outline=primary_outline)
				header.create_rectangle(main_width, 0, main_width + secondary_width, header_height, fill=secondary, outline=secondary_outline)
				title_is_left = config["title_alignment"] == "靠左"
				assignment_is_left = config["assignment_alignment"] == "靠左"
				header.create_text(
					10 if title_is_left else main_width - 10,
					header_height // 2,
					text=header_text,
					anchor="w" if title_is_left else "e",
					font=header_font,
					fill=config["title_font_color"],
				)
				header.pack(anchor="w" if title_is_left else "e")

				for assignment in assignments:
					is_secondary = assignment.get("secondary", False)
					label = tk.Label(
						section,
						text="{}{}{}".format(
							"" if assignment.get("ignore_prefix", False) else config["assignment_prefix"],
							assignment["assignment"],
							"" if assignment.get("ignore_suffix", False) else config["assignment_suffix"],
						),
						anchor="w" if assignment_is_left else "e",
						justify="left" if assignment_is_left else "right",
						font=("Microsoft YaHei UI", config["secondary_assignment_font_size"] if is_secondary else config["assignment_font_size"]),
						foreground=config["secondary_assignment_font_color"] if is_secondary else config["assignment_font_color"],
						background=transparent_color,
					)
					label.pack(anchor="w" if assignment_is_left else "e", pady=(4, 0))

		animation_name = config.get("display_animation", DEFAULT_CONFIG["display_animation"])
		if animation_name == "seamless_scroll":
			original_content = tk.Frame(content, background=transparent_color)
			original_content.pack(fill="x", anchor="n")
			render_sections(original_content)
			duplicate_content = tk.Frame(content, background=transparent_color)
			loop_gap_height = permill_y(config["seamless_loop_gap_permill"])
			duplicate_content.pack(fill="x", anchor="n", pady=(loop_gap_height, 0))
			render_sections(duplicate_content)
		else:
			original_content = tk.Frame(content, background=transparent_color)
			original_content.pack(fill="x", anchor="n")
			render_sections(original_content)

		scroll_canvas.update_idletasks()
		scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

	render_assignment()
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

	def get_animation_start_delay():
		if config.get("display_animation", DEFAULT_CONFIG["display_animation"]) == "seamless_scroll":
			return config["seamless_start_delay"]
		return config["scroll_start_delay"]

	def manual_scroll(event):
		"""Allow wheel and arrow-key scrolling while the pointer is over the display."""
		nonlocal animation_generation
		if event.type == tk.EventType.MouseWheel:
			steps = -3 if event.delta > 0 else 3
		elif getattr(event, "num", None) == 4:
			steps = -3
		elif getattr(event, "num", None) == 5:
			steps = 3
		elif event.keysym == "Up":
			steps = -3
		elif event.keysym == "Down":
			steps = 3
		else:
			return
		pointer_x = event.x_root if hasattr(event, "x_root") else root.winfo_pointerx()
		pointer_y = event.y_root if hasattr(event, "y_root") else root.winfo_pointery()
		widget = root.winfo_containing(pointer_x, pointer_y)
		if widget is None or not str(widget).startswith(str(root)):
			return
		cancel_animation_jobs()
		animation_generation += 1
		scroll_canvas.yview_scroll(steps, "units")
		schedule_animation(get_animation_start_delay(), auto_scroll)
		return "break"

	touch_drag_y = None
	touch_drag_start_y = None
	touch_dragged = False

	def touch_drag_start(event):
		nonlocal touch_drag_y, touch_drag_start_y, touch_dragged, animation_generation
		touch_drag_y = event.y_root
		touch_drag_start_y = event.y_root
		touch_dragged = False
		cancel_animation_jobs()
		animation_generation += 1

	def touch_drag_motion(event):
		nonlocal touch_drag_y, touch_dragged
		if touch_drag_y is None:
			return
		delta_y = event.y_root - touch_drag_y
		touch_drag_y = event.y_root
		if abs(event.y_root - touch_drag_start_y) >= 2:
			touch_dragged = True
		if not touch_dragged:
			return
		bounds = scroll_canvas.bbox("all")
		if not bounds:
			return "break"
		content_height = bounds[3] - bounds[1]
		viewport_height = scroll_canvas.winfo_height()
		if content_height > viewport_height:
			first, _last = scroll_canvas.yview()
			scroll_canvas.yview_moveto(
				first - delta_y / content_height
			)
		return "break"

	def touch_drag_end(_event):
		nonlocal touch_drag_y, touch_drag_start_y
		was_dragged = touch_dragged
		touch_drag_y = None
		touch_drag_start_y = None
		if was_dragged:
			schedule_animation(get_animation_start_delay(), auto_scroll)

	root.bind_all("<ButtonPress-1>", touch_drag_start, add="+")
	root.bind_all("<B1-Motion>", touch_drag_motion, add="+")
	root.bind_all("<ButtonRelease-1>", touch_drag_end, add="+")

	root.bind_all("<MouseWheel>", manual_scroll, add="+")
	root.bind_all("<Button-4>", manual_scroll, add="+")
	root.bind_all("<Button-5>", manual_scroll, add="+")
	root.bind_all("<KeyPress-Up>", manual_scroll, add="+")
	root.bind_all("<KeyPress-Down>", manual_scroll, add="+")

	def reload_assignment():
		nonlocal animation_generation
		try:
			cancel_animation_jobs()
			render_assignment()
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
			root.after(0, reload_assignment)
			threading.Thread(target=wait_for_reload, daemon=True).start()

	if reload_event is not None:
		threading.Thread(target=wait_for_reload, daemon=True).start()

	def wait_for_shutdown_signal():
		if wait_for_shutdown(shutdown_event):
			root.after(0, close_display)

	if shutdown_event is not None:
		threading.Thread(target=wait_for_shutdown_signal, daemon=True).start()

	def run_fade_out(generation):
		nonlocal animation_generation
		bounds = scroll_canvas.bbox("all")
		if not bounds:
			return

		content_height = bounds[3] - bounds[1]
		viewport_height = scroll_canvas.winfo_height()
		scroll_step_pixels = max(
			1,
			round(screen_height * config["scroll_step_size"] / 1000),
		)
		fade_step = config["fade_step"] / 100.0
		if viewport_height <= 1:
			schedule_animation(100, auto_scroll)
			return
		if content_height <= viewport_height:
			return

		def scroll_step():
			if generation != animation_generation:
				return
			first, last = scroll_canvas.yview()
			if last >= 1:
				schedule_animation(config["scroll_end_pause"], scroll_to_top)
				return

			scroll_canvas.yview_moveto(
				min(first + scroll_step_pixels / max(1, content_height), 1)
			)
			schedule_animation(config["scroll_step_interval"], scroll_step)

		def scroll_to_top():
			fade_out()

		def fade_out(alpha=max_alpha):
			if generation != animation_generation:
				return
			alpha -= fade_step
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
			alpha += fade_step
			if alpha >= max_alpha:
				root.attributes("-alpha", max_alpha)
				schedule_animation(config["scroll_start_delay"], scroll_step)
				return

			root.attributes("-alpha", alpha)
			schedule_animation(config["fade_interval"], fade_in, alpha)

		schedule_animation(config["scroll_start_delay"], scroll_step)

	def run_seamless_scroll(generation):
		scroll_canvas.update_idletasks()
		bounds = scroll_canvas.bbox("all")
		if not bounds:
			return

		viewport_height = scroll_canvas.winfo_height()
		if viewport_height <= 1:
			schedule_animation(100, auto_scroll)
			return
		if original_content is None:
			return

		loop_height = original_content.winfo_height()
		total_height = bounds[3] - bounds[1]
		if loop_height <= 0 or loop_height <= viewport_height:
			return
		if total_height <= loop_height:
			return
		if duplicate_content is None:
			return

		loop_start = duplicate_content.winfo_y()
		step_size = max(1, int(config["seamless_step_size"]))
		first, _last = scroll_canvas.yview()
		position = max(0, min(loop_start, round(first * total_height)))

		def scroll_step():
			nonlocal position
			if generation != animation_generation:
				return
			next_position = position + step_size
			if next_position >= loop_start:
				if config["seamless_loop_pause"] > 0:
					schedule_animation(
						config["seamless_loop_pause"],
						reset_to_start,
					)
				else:
					reset_to_start()
				return

			position = next_position
			scroll_canvas.yview_moveto(min(1.0, position / total_height))
			schedule_animation(
				config["seamless_step_interval"],
				scroll_step,
			)

		def reset_to_start():
			nonlocal position
			if generation != animation_generation:
				return
			position = 0
			scroll_canvas.yview_moveto(0)
			schedule_animation(
				config["seamless_step_interval"],
				scroll_step,
			)

		schedule_animation(
			config["seamless_start_delay"],
			scroll_step,
		)

	ANIMATION_RUNNERS = {
		"fade-out": run_fade_out,
		"seamless_scroll": run_seamless_scroll,
	}

	def auto_scroll():
		nonlocal animation_generation
		animation_generation += 1
		generation = animation_generation
		root.attributes("-alpha", max_alpha)

		animation_name = config.get(
			"display_animation",
			DEFAULT_CONFIG["display_animation"],
		)
		runner = ANIMATION_RUNNERS.get(animation_name)
		if runner is None:
			runner = run_fade_out
		runner(generation)

	schedule_animation(100, auto_scroll)
	def close_display():
		cancel_animation_jobs()
		close_config_reload_event(reload_event)
		close_shutdown_event(shutdown_event)
		if hasattr(root, "_hwm_old_window_proc"):
			try:
				ctypes.windll.user32.SetWindowLongPtrW(
					root._hwm_window_handle,
					-4,
					root._hwm_old_window_proc,
				)
			except (AttributeError, OSError):
				pass
		root.destroy()

	root.bind("<Escape>", lambda _event: close_display())
	root.mainloop()


if __name__ == "__main__":
	main()


