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
    "title_width": 70,
    "title_length": 30,
    "title_font_size": 15,
    "project_font_size": 14,
    "title_font_color": "#F5F5F5",
    "project_font_color": "#F5F5F5",
    "title_alignment": "靠右",
    "project_alignment": "靠右",
    "title_theme": "默认",
    "title_primary_color": "#315E7D",
    "title_secondary_color": "#4C8DB4",
    "title_outline_opacity": 80,
    "title_guide_line_width": 10,
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
    "display_range_left": 55,
    "display_range_right": 100,
    "display_range_top": 2,
    "display_range_bottom": 70,
    "window_alpha": 0.9,
    "content_padding_x": 18,
    "content_padding_y": 12,
    "section_spacing": 14,
    "scroll_start_delay": 1200,
    "scroll_step_interval": 120,
    "scroll_step_size": 0.001,
    "scroll_end_pause": 1200,
    "restart_pause": 1200,
    "fade_interval": 30,
    "fade_step": 0.03,
}
DEFAULT_SUBJECTS = (
    "chinese", "maths", "english", "history", "politics", "physics",
    "chemistry", "biology", "geography", "it", "pe", "art", "other",
)
LEGACY_COLOR_THEMES = {"海洋青", "森林绿", "日落橙", "紫藤", "玫瑰", "石墨", "黑板绿"}


def default_document():
    return [
        {"config": DEFAULT_CONFIG.copy()},
        {"data": [{subject: []} for subject in DEFAULT_SUBJECTS]},
    ]


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
                if config.get("title_theme") in LEGACY_COLOR_THEMES:
                    config["title_theme"] = "默认"
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
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        document = default_document()
        with Path(config_file).open("w", encoding="utf-8") as target:
            json.dump({"config": document[0]["config"]}, target, ensure_ascii=False, indent=4)
            target.write("\n")
        return DEFAULT_CONFIG.copy(), document[1]["data"]


def load_config(config_file):
    config, _legacy_data = load_config_document(config_file)
    return config


def save_config(config_file, config):
    path = Path(config_file)
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


