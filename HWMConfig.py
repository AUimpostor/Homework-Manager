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
import uuid
from pathlib import Path


DEFAULT_CONFIG = {
    "title_width_permill": 45,
    "title_length_permill": 45,
    "title_font_size": 18,
    "project_font_size": 17,
    "secondary_project_font_size": 14,
    "title_font_color": "#F5F5F5",
    "project_font_color": "#F5F5F5",
    "secondary_project_font_color": "#A9A9A9",
    "title_alignment": "靠右",
    "project_alignment": "靠右",
    "title_theme": "默认",
    "title_primary_color": "#315E7D",
    "title_secondary_color": "#4C8DB4",
    "title_outline_opacity": 80,
    "title_guide_line_width_permill": 10,
    "auto_start_display": False,
    "tray_click_action": "dashboard",
    "school": "",
    "class": "",
    "project_prefix": "",
    "project_suffix": " -",
    "dashboard_width_percent": 40,
    "dashboard_height_percent": 40,
    "editor_width_percent": 50,
    "editor_height_percent": 50,
    "subject_list_width_percent": 5,
    "display_range_left_percent": 55,
    "display_range_right_percent": 100,
    "display_range_top_percent": 2,
    "display_range_bottom_percent": 70,
    "window_alpha": 0.9,
    "content_padding_x_permill": 18,
    "content_padding_y_permill": 12,
    "section_spacing_permill": 12,
    "scroll_start_delay": 1200,
    "scroll_step_interval": 120,
    "scroll_step_size": 0.001,
    "scroll_end_pause": 1200,
    "restart_pause": 1200,
    "fade_interval": 30,
    "fade_step": 0.03,
}
COLOR_PRESETS = (
    ("浅灰色", "#F5F5F5"),
    ("灰色", "#808080"),
    ("深灰色", "#A9A9A9"),
    ("白色", "#FFFFFF"),
    ("深蓝色", "#315E7D"),
    ("蓝色", "#4C8DB4"),
    ("浅蓝色", "#CFE8FF"),
    ("浅黄色", "#FFF2A8"),
    ("浅绿色", "#C8F7C5"),
    ("浅粉色", "#FFD6E7"),
)
DEFAULT_SUBJECTS = (
    "chinese", "maths", "english", "history", "politics", "physics",
    "chemistry", "biology", "geography", "it", "pe", "art", "other",
)


def default_document():
    return [
        {"config": DEFAULT_CONFIG.copy()},
        {"data": [{subject: []} for subject in DEFAULT_SUBJECTS]},
    ]


def _write_default_config(config_file):
    """Write a fresh config file using the built-in defaults."""
    document = default_document()
    path = Path(config_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as target:
            json.dump({"config": document[0]["config"]}, target, ensure_ascii=False, indent=4)
            target.write("\n")
    except OSError:
        pass


def load_config_document(config_file):
    try:
        with Path(config_file).open("r", encoding="utf-8") as source:
            document = json.load(source)
        config = DEFAULT_CONFIG.copy()
        data = []
        legacy_font_color = None
        has_title_font_color = False
        has_project_font_color = False
        legacy_array = isinstance(document, list)
        items = document if legacy_array else [document]
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("config.json 必须是 JSON 对象")
            if legacy_array:
                config_item = item.get("config", {})
            else:
                config_item = item.get("config") if isinstance(item.get("config"), dict) else item
            if isinstance(config_item, dict):
                config.update(config_item)
                for old_key, new_key in (
                    ("title_width", "title_width_permill"),
                    ("title_length", "title_length_permill"),
                    ("title_guide_line_width", "title_guide_line_width_permill"),
                    ("content_padding_x", "content_padding_x_permill"),
                    ("content_padding_y", "content_padding_y_permill"),
                    ("section_spacing", "section_spacing_permill"),
                    ("subject_list_width_percent", "subject_list_width_percent"),
                    ("display_range_left", "display_range_left_percent"),
                    ("display_range_right", "display_range_right_percent"),
                    ("display_range_top", "display_range_top_percent"),
                    ("display_range_bottom", "display_range_bottom_percent"),
                ):
                    if new_key not in config_item and old_key in config_item:
                        config[new_key] = config_item[old_key]
                    config.pop(old_key, None)
                if "title_primary_color" not in config_item and "title_background_color" in config_item:
                    config["title_primary_color"] = config_item["title_background_color"]
                if "title_secondary_color" not in config_item and "title_guide_line_color" in config_item:
                    config["title_secondary_color"] = config_item["title_guide_line_color"]
                config.pop("title_background_color", None)
                config.pop("title_guide_line_color", None)
                for obsolete_key in (
                    "dashboard_width", "dashboard_height", "editor_width",
                    "editor_height", "editor_subject_width",
                ):
                    config.pop(obsolete_key, None)
                legacy_font_color = config_item.get("font_color", legacy_font_color)
                has_title_font_color |= "title_font_color" in config_item
                has_project_font_color |= "project_font_color" in config_item
            if isinstance(item.get("data"), list):
                data.extend(item["data"])
        if legacy_font_color is not None:
            if not has_title_font_color:
                config["title_font_color"] = legacy_font_color
            if not has_project_font_color:
                config["project_font_color"] = legacy_font_color
        return config, data
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy(), default_document()[1]["data"]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        _write_default_config(config_file)
        return DEFAULT_CONFIG.copy(), default_document()[1]["data"]


def load_config(config_file):
    config, _legacy_data = load_config_document(config_file)
    return config


def save_config(config_file, config):
    path = Path(config_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".{}.tmp".format(uuid.uuid4().hex))
    with temporary.open("w", encoding="utf-8") as target:
        json.dump({"config": config}, target, ensure_ascii=False, indent=4)
        target.write("\n")
    temporary.replace(path)


def load_homework_data(homework_file, legacy_config_file=None):
    homework_path = Path(homework_file)
    try:
        with homework_path.open("r", encoding="utf-8") as source:
            data = json.load(source)
        if isinstance(data, dict):
            return [{subject: assignments} for subject, assignments in data.items()]
        if isinstance(data, list):
            return data
        raise ValueError("homework.json 必须是 JSON 对象")
    except FileNotFoundError:
        pass

    data = None
    migrated_legacy_data = False
    if legacy_config_file is not None:
        try:
            with Path(legacy_config_file).open("r", encoding="utf-8") as source:
                legacy_document = json.load(source)
            if isinstance(legacy_document, list):
                data = []
                for item in legacy_document:
                    if isinstance(item, dict) and isinstance(item.get("data"), list):
                        data.extend(item["data"])
                        migrated_legacy_data = True
        except (OSError, json.JSONDecodeError, TypeError):
            data = None
    if data is None:
        data = default_document()[1]["data"]
    save_homework_data(homework_path, data)
    if migrated_legacy_data:
        save_config(legacy_config_file, load_config(legacy_config_file))
    return data


def save_homework_data(homework_file, data):
    path = Path(homework_file)
    temporary = path.with_suffix(path.suffix + ".{}.tmp".format(uuid.uuid4().hex))
    if isinstance(data, list):
        normalized = {}
        for item in data:
            if isinstance(item, dict):
                normalized.update(item)
    elif isinstance(data, dict):
        normalized = data
    else:
        raise ValueError("作业数据必须是 JSON 对象")
    with temporary.open("w", encoding="utf-8") as target:
        json.dump(normalized, target, ensure_ascii=False, indent=4)
        target.write("\n")
    temporary.replace(path)


