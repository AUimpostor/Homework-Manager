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
import shutil
import uuid
from pathlib import Path


BACKUP_TYPES = ("config", "custom", "assignment")
BACKUP_EXTENSIONS = {
    "config": ".json.bak",
    "custom": ".tar",
    "assignment": ".json.bak",
}


def backup_directory(application_dir, backup_type):
    if backup_type not in BACKUP_TYPES:
        raise ValueError("未知备份类型: {}".format(backup_type))
    return data_directory(application_dir) / "backup" / backup_type


def next_backup_path(directory, extension, name=None, automatic=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if automatic:
        index = 0
        while True:
            path = directory / "auto_{}{}".format(index, extension)
            if not path.exists():
                return path
            index += 1

    name = validate_backup_name(name)
    path = directory / "{}{}".format(name, extension)
    index = 1
    while path.exists():
        path = directory / "{}_{}{}".format(name, index, extension)
        index += 1
    return path


def validate_backup_name(name):
    name = name.strip() if isinstance(name, str) else ""
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
    }
    reserved_names.update("COM{}".format(index) for index in range(1, 10))
    reserved_names.update("LPT{}".format(index) for index in range(1, 10))
    if (
        not name
        or name.lower().startswith("auto_")
        or name in (".", "..")
        or name.endswith((".", " "))
        or any(ord(char) < 32 or char in '<>:"/\\|?*' for char in name)
        or name.split(".", 1)[0].upper() in reserved_names
    ):
        raise ValueError("备份名称不能为空或包含无效字符")
    return name


def ensure_backup_layout(application_dir):
    backup_root = data_directory(application_dir) / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    for backup_type in BACKUP_TYPES:
        backup_directory(application_dir, backup_type).mkdir(parents=True, exist_ok=True)

    legacy_state = backup_root / ".custom_backup_state.json"
    custom_state = backup_directory(application_dir, "custom") / legacy_state.name
    if legacy_state.is_file():
        if custom_state.exists():
            legacy_state.unlink()
        else:
            legacy_state.replace(custom_state)

    prefixes = {
        "config": "config_",
        "custom": "custom_",
        "assignment": "assignment_",
    }
    for source in sorted(
        (path for path in backup_root.iterdir() if path.is_file()),
        key=lambda path: (path.stat().st_ctime, path.name),
    ):
        if source.name == legacy_state.name:
            continue
        backup_type = next(
            (
                item for item in BACKUP_TYPES
                if source.name.startswith(prefixes[item])
                and source.name.endswith(BACKUP_EXTENSIONS[item])
            ),
            None,
        )
        if backup_type is None:
            continue
        destination = next_backup_path(
            backup_directory(application_dir, backup_type),
            BACKUP_EXTENSIONS[backup_type],
            automatic=True,
        )
        source.replace(destination)


DEFAULT_CONFIG = {
    "title_width_permill": 45,
    "title_length_permill": 45,
    "title_font_size": 18,
    "assignment_font_size": 17,
    "secondary_assignment_font_size": 14,
    "assignment_font_color": "#F5F5F5",
    "secondary_assignment_font_color": "#A9A9A9",
    "title_alignment": "靠右",
    "assignment_alignment": "靠右",
    "title_theme": "basic_color_block",
    "auto_start_display": False,
    "tray_click_action": "dashboard",
    "open_action": "dashboard",
    "school": "",
    "class": "",
    "assignment_prefix": "",
    "assignment_suffix": " -",
    "dashboard_width_percent": 40,
    "dashboard_height_percent": 40,
    "editor_width_percent": 50,
    "editor_height_percent": 50,
    "editor_visible_actions": ["add", "edit", "toggle", "delete", "up", "down"],
    "editor_visible_management_actions": ["undo", "redo", "save"],
    "editor_management_action_order": ["undo", "redo", "save"],
    "display_range_left_percent": 55,
    "display_range_right_percent": 100,
    "display_range_top_percent": 2,
    "display_range_bottom_percent": 45,
    "window_alpha": 0.9,
    "content_padding_x_permill": 18,
    "content_padding_y_permill": 12,
    "section_spacing_permill": 12,
    "display_animation": "fade-out",
}
COLOR_PRESETS = (
    ("浅灰色", "#F5F5F5"),
    ("灰色", "#808080"),
    ("深灰色", "#A9A9A9"),
    ("白色", "#FFFFFF"),
    ("深蓝色", "#315E7D"),
    ("水蓝色", "#69C8D0"),
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
DISPLAY_ANIMATION_REGISTRY = {
    "fade-out": {
        "label": "淡出循环（默认）",
        "defaults": {
            "scroll_start_delay": 1200,
            "scroll_step_interval": 30,
            "scroll_step_size": 1,
            "scroll_end_pause": 1200,
            "restart_pause": 800,
            "fade_interval": 15,
            "fade_step": 3,
        },
        "parameters": (
            ("scroll_start_delay", "首次滚动前停顿（ms）", "int"),
            ("scroll_step_interval", "滚动间隔（ms）", "int"),
            ("scroll_step_size", "每次滚动幅度（‰）", "permill"),
            ("scroll_end_pause", "滚动到末尾停留（ms）", "int"),
            ("restart_pause", "回到顶部后停留（ms）", "int"),
            ("fade_interval", "淡入淡出间隔（ms）", "int"),
            ("fade_step", "淡入淡出步长（%）", "percent"),
        ),
    },
    "seamless_scroll": {
        "label": "无缝滚动",
        "defaults": {
            "seamless_start_delay": 1200,
            "seamless_step_interval": 16,
            "seamless_step_size": 1,
            "seamless_loop_pause": 0,
            "seamless_loop_gap_permill": 40,
        },
        "parameters": (
            ("seamless_start_delay", "首次滚动前停顿（ms）", "int"),
            ("seamless_step_interval", "滚动间隔（ms）", "int"),
            ("seamless_step_size", "每次滚动幅度（px）", "positive_int"),
            ("seamless_loop_pause", "循环重置停顿（ms）", "nonnegative_int"),
            ("seamless_loop_gap_permill", "循环间留空（‰）", "permill"),
        ),
    },
}

DISPLAY_ANIMATION_DEFAULTS = {
    name: dict(spec["defaults"])
    for name, spec in DISPLAY_ANIMATION_REGISTRY.items()
}
TITLE_THEME_DEFAULTS = {
    "basic_color_block": {
        "title_font_color": "#F5F5F5",
        "title_primary_color": "#315E7D",
        "title_secondary_color": "#4C8DB4",
        "title_outline_opacity": 80,
        "title_guide_line_width_permill": 10,
    },
}


def data_directory(application_dir):
    """Return the data directory without creating files or directories."""
    return Path(application_dir) / "data"


def custom_directory(application_dir):
    """Return the custom data directory without creating it."""
    return data_directory(application_dir) / "custom"


def load_custom_params(application_dir, directory, defaults_table, name, label):
    """Load a named preset's parameters from its custom data file."""
    defaults = defaults_table.get(name) or next(iter(defaults_table.values()))
    path = custom_directory(application_dir) / directory / "{}.json".format(name)
    if not path.is_file():
        save_custom_params(application_dir, directory, defaults_table, name, defaults)
        from runtime import show_windows_notification
        show_windows_notification(
            "活跃的{}自定义数据文件意外丢失\n已将{}重置为默认值".format(label, label),
            "加载{}自定义数据时出现错误".format(label),
        )

    with path.open("r", encoding="utf-8") as source:
        loaded = json.load(source)
    if not isinstance(loaded, dict):
        raise ValueError("{}自定义数据文件必须是 JSON 对象".format(label))
    if any(key not in loaded for key in defaults):
        save_custom_params(
            application_dir,
            directory,
            defaults_table,
            name,
            {key: loaded.get(key, value) for key, value in defaults.items()},
        )
        with path.open("r", encoding="utf-8") as source:
            loaded = json.load(source)
    return {key: loaded[key] for key in defaults}


def initialize_custom_params(application_dir):
    """Create missing preset files before the first post-welcome parameter read."""
    for directory, defaults_table in (
        ("display_animation", DISPLAY_ANIMATION_DEFAULTS),
        ("title_theme", TITLE_THEME_DEFAULTS),
    ):
        for name, defaults in defaults_table.items():
            path = custom_directory(application_dir) / directory / "{}.json".format(name)
            if not path.is_file():
                save_custom_params(application_dir, directory, defaults_table, name, defaults)


def save_custom_params(application_dir, directory, defaults_table, name, params):
    """Persist a preset's parameters under the custom data directory."""
    defaults = defaults_table.get(name) or next(iter(defaults_table.values()))
    normalized = {}
    for key in defaults:
        normalized[key] = params.get(key, defaults[key])
    target_dir = custom_directory(application_dir) / directory
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "{}.json".format(name)
    temporary = path.with_suffix(path.suffix + ".{}.tmp".format(uuid.uuid4().hex))
    with temporary.open("w", encoding="utf-8") as target:
        json.dump(normalized, target, ensure_ascii=False, indent=4)
        target.write("\n")
    temporary.replace(path)


def load_display_animation_params(application_dir, name):
    return load_custom_params(
        application_dir, "display_animation", DISPLAY_ANIMATION_DEFAULTS, name, "显示动画"
    )


def save_display_animation_params(application_dir, name, params):
    save_custom_params(
        application_dir, "display_animation", DISPLAY_ANIMATION_DEFAULTS, name, params
    )


def load_title_theme_params(application_dir, name):
    return load_custom_params(
        application_dir, "title_theme", TITLE_THEME_DEFAULTS, name, "标题主题"
    )


def save_title_theme_params(application_dir, name, params):
    save_custom_params(application_dir, "title_theme", TITLE_THEME_DEFAULTS, name, params)


def initialize_data_directory(application_dir):
    """Create the data directories and move existing root-level user files once."""
    application_dir = Path(application_dir)
    data_dir = data_directory(application_dir)
    backup_dir = data_dir / "backup"
    data_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "assignment.json", "subscriptions.json"):
        source = application_dir / name
        destination = data_dir / name
        if source.is_file() and not destination.exists():
            shutil.move(str(source), str(destination))
    for source in application_dir.glob("config_*.json.bak"):
        destination = backup_dir / source.name
        if not source.is_file():
            continue
        index = 1
        while destination.exists():
            stem = source.name[:-len(".json.bak")]
            destination = backup_dir / "{}_{}.json.bak".format(stem, index)
            index += 1
        shutil.move(str(source), str(destination))
    ensure_backup_layout(application_dir)
    return data_dir


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
            json.dump(document[0]["config"], target, ensure_ascii=False, indent=4)
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
        has_assignment_font_color = False
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
                    ("content_padding_x", "content_padding_x_permill"),
                    ("content_padding_y", "content_padding_y_permill"),
                    ("section_spacing", "section_spacing_permill"),
                    ("display_range_left", "display_range_left_percent"),
                    ("display_range_right", "display_range_right_percent"),
                    ("display_range_top", "display_range_top_percent"),
                    ("display_range_bottom", "display_range_bottom_percent"),
                ):
                    if new_key not in config_item and old_key in config_item:
                        config[new_key] = config_item[old_key]
                    config.pop(old_key, None)
                for obsolete_key in (
                    "dashboard_width", "dashboard_height", "editor_width",
                    "editor_height", "editor_subject_width",
                    "subject_list_width_percent",
                    "scroll_start_delay", "scroll_step_interval", "scroll_step_size",
                    "scroll_end_pause", "restart_pause", "fade_interval", "fade_step",
                    "title_font_color", "title_primary_color", "title_secondary_color",
                    "title_outline_opacity", "title_guide_line_width",
                    "title_guide_line_width_permill",
                    "title_background_color", "title_guide_line_color",
                ):
                    config.pop(obsolete_key, None)
                legacy_font_color = config_item.get("font_color", legacy_font_color)
                has_assignment_font_color |= "assignment_font_color" in config_item
            if isinstance(item.get("data"), list):
                data.extend(item["data"])
        if legacy_font_color is not None:
            if not has_assignment_font_color:
                config["assignment_font_color"] = legacy_font_color
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
        json.dump(config, target, ensure_ascii=False, indent=4)
        target.write("\n")
    temporary.replace(path)


def load_assignment_data(assignment_file, legacy_config_file=None):
    assignment_path = Path(assignment_file)
    try:
        with assignment_path.open("r", encoding="utf-8") as source:
            data = json.load(source)
        if isinstance(data, dict):
            return [{subject: assignments} for subject, assignments in data.items()]
        if isinstance(data, list):
            return data
        raise ValueError("assignment.json 必须是 JSON 对象")
    except FileNotFoundError:
        try:
            from runtime import show_windows_notification
            show_windows_notification(
                "活跃的作业文件意外丢失\n已将作业文件重置为空", "加载作业时出现错误"
            )
        except Exception:
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
    save_assignment_data(assignment_path, data)
    if migrated_legacy_data:
        save_config(legacy_config_file, load_config(legacy_config_file))
    return data


def save_assignment_data(assignment_file, data):
    path = Path(assignment_file)
    path.parent.mkdir(parents=True, exist_ok=True)
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


