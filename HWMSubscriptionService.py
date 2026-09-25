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

"""SMTP delivery, subscription persistence, and scheduled-push services."""
import base64
import ctypes
import html
import json
import re
import smtplib
import ssl
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from HWMConfig import load_config, load_homework_data


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

SETTINGS_NAME = "subscriptions.json"

SUBJECT_NAMES = {
    "chinese": "语文", "maths": "数学", "english": "英语", "history": "历史",
    "politics": "政治", "physics": "物理", "chemistry": "化学", "biology": "生物",
    "geography": "地理", "it": "信息技术", "pe": "体育", "art": "美术", "other": "其他",
}

DEFAULTS = {
    "source": {"host": "", "port": 465, "security": "SSL", "email": "", "username": "", "password": ""},
    "subscribers": [], "schedule_enabled": False, "schedule_time": "18:00:00",
    "title_template": "%date% 作业",
    "body_template": "<b>%n% %t%，您好。这是今天的作业：</b>\n<hr style='height:1px;border-width:0;color:gray;background-color:gray'><blockquote style='border-left: 3px solid #318CE7; padding-left: 12px; margin-left: 0;'>%hw%</blockquote>\n<div style='text-align: right;'><b>%s% %c%</b></div><hr style='height:2px;border-width:0;color:gray;background-color:gray'><div style='text-align: center;'><small>此邮件由 <a href='https://github.com/AUimpostor/Homework-Manager'>Homework Manager</a> 推送管理器自动发送，请不要回复。\n%date% %time%</small></div>",
}

_schedule_lock = threading.Lock()


def normalize_schedule_time(value):
    """Return strict 24-hour HH:MM:SS; accept legacy HH:MM as :00."""
    text = str(value).strip()
    if re.fullmatch(r"\d{2}:\d{2}", text):
        text += ":00"
    if not re.fullmatch(r"\d{2}:\d{2}:\d{2}", text):
        raise ValueError("定时推送时间请使用 HH:MM:SS 格式（例如 18:30:00）。")
    try:
        return datetime.strptime(text, "%H:%M:%S").strftime("%H:%M:%S")
    except ValueError as error:
        raise ValueError("定时推送时间无效，请输入有效的 24 小时时间。") from error

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

def _protect(value):
    if not value:
        return ""
    if sys.platform != "win32":
        return base64.b64encode(value.encode("utf-8")).decode("ascii")
    raw = value.encode("utf-8")
    source = _Blob(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(_Blob), ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_Blob)]
    crypt32.CryptProtectData.restype = ctypes.c_bool
    if not crypt32.CryptProtectData(ctypes.byref(source), "HWM SMTP password", None, None, None, 1, ctypes.byref(result)):
        raise OSError("Windows 凭据加密失败")
    try:
        return "dpapi:" + base64.b64encode(ctypes.string_at(result.pbData, result.cbData)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)

def _unprotect(value):
    if not value:
        return ""
    if not value.startswith("dpapi:"):
        try:
            return base64.b64decode(value).decode("utf-8")
        except Exception:
            return value
    raw = base64.b64decode(value[6:])
    source = _Blob(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_Blob)]
    crypt32.CryptUnprotectData.restype = ctypes.c_bool
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise OSError("无法解密 SMTP 密码；请在设置中重新输入")
    try:
        return ctypes.string_at(result.pbData, result.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)

def load_settings(directory=APP_DIR):
    path = Path(directory) / SETTINGS_NAME
    try:
        with path.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        result = dict(DEFAULTS)
        result.update(loaded)
        result["source"] = dict(DEFAULTS["source"], **loaded.get("source", {}))
        result["source"]["password"] = _unprotect(result["source"].get("password", ""))
        result["subscribers"] = loaded.get("subscribers", [])
        # Discard the legacy daily-send marker; schedules now fire only on exact time matches.
        result.pop("last_sent_date", None)
        try:
            result["schedule_time"] = normalize_schedule_time(result.get("schedule_time", DEFAULTS["schedule_time"]))
        except ValueError:
            pass
        return result
    except FileNotFoundError:
        return dict(DEFAULTS, source=dict(DEFAULTS["source"]), subscribers=[])

def save_settings(settings, directory=APP_DIR):
    path = Path(directory) / SETTINGS_NAME
    value = dict(settings)
    value.pop("last_sent_date", None)
    value["source"] = dict(settings["source"])
    value["source"]["password"] = _protect(value["source"].get("password", ""))
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)

def homework_text(directory=APP_DIR):
    data = load_homework_data(Path(directory) / "homework.json", Path(directory) / "config.json")
    sections = []
    for item in data:
        if not isinstance(item, dict):
            continue
        for subject, assignments in item.items():
            visible = []
            for assignment in assignments if isinstance(assignments, list) else []:
                if isinstance(assignment, str) and assignment.strip():
                    visible.append(assignment.strip())
                elif isinstance(assignment, dict) and not assignment.get("hide", False):
                    text = assignment.get("project", assignment.get("subject", ""))
                    if isinstance(text, str) and text.strip():
                        visible.append(text.strip())
            if visible:
                sections.append((SUBJECT_NAMES.get(subject, subject), visible))
    return sections

def send_push(settings, directory=APP_DIR, recipients=None):
    source = settings["source"]
    required = ("host", "port", "email", "username", "password")
    if any(not str(source.get(key, "")).strip() for key in required):
        raise ValueError("请先完整填写推送源 SMTP 配置。")
    targets = recipients if recipients is not None else settings.get("subscribers", [])
    if not targets:
        raise ValueError("没有可发送的订阅账户。")
    sections = homework_text(directory)
    app_config = load_config(Path(directory) / "config.json")
    lines = []
    html_sections = []
    for name, assignments in sections:
        lines.append(name + "：")
        lines.extend("  • " + assignment for assignment in assignments)
        lines.append("")
        html_sections.append("<strong>{}：</strong><br>{}<br><br>".format(
            html.escape(name), "<br>".join("• " + html.escape(assignment) for assignment in assignments)
        ))
    for person in targets:
        msg = EmailMessage()
        now = datetime.now()
        replacements = {"%date%": now.strftime("%Y-%m-%d"), "%time%": now.strftime("%H:%M"),
                        "%n%": str(person.get("nickname", "")), "%t%": str(person.get("salutation", "")),
                        "%s%": str(app_config.get("school", "")), "%c%": str(app_config.get("class", "")),
                        "%hw%": "\n".join(lines) if lines else "（今天没有作业）"}
        title = str(settings.get("title_template", DEFAULTS["title_template"]))
        body_template = str(settings.get("body_template", DEFAULTS["body_template"]))
        if not person.get("salutation"):
            body_template = body_template.replace("%n% %t%，您好", "%n%，您好")
        body = body_template
        safe_body = body_template
        for token, value in replacements.items():
            title = title.replace(token, value)
            body = body.replace(token, value)
            if token != "%hw%":
                safe_body = safe_body.replace(token, html.escape(str(value)))
        hw_html = "".join(html_sections) if html_sections else "（今天没有作业）"
        safe_body = safe_body.replace("%hw%", hw_html).replace("\n", "<br>")
        msg["Subject"] = title.replace("\r", " ").replace("\n", " ")
        msg["From"] = source["email"]
        msg["To"] = person["email"]
        msg.set_content(body)
        msg.add_alternative("<div style=\"font-family:Arial,'Microsoft YaHei',sans-serif;line-height:1.65\">{}</div>".format(safe_body), subtype="html")
        with _smtp_session(source, timeout=30) as server:
            server.send_message(msg)
    return len(targets)


@contextmanager
def _smtp_session(source, timeout):
    server = None
    try:
        context = ssl.create_default_context()
        port = int(source["port"])
        if source.get("security", "SSL") == "SSL":
            server = smtplib.SMTP_SSL(source["host"], port, context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(source["host"], port, timeout=timeout)
            server.ehlo()
            if source.get("security") == "STARTTLS":
                server.starttls(context=context)
                server.ehlo()
        server.login(source["username"], source["password"])
        yield server
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


def check_smtp_connection(source, timeout=8):
    required = ("host", "port", "email", "username", "password")
    if any(not str(source.get(key, "")).strip() for key in required):
        return False
    try:
        with _smtp_session(source, timeout):
            pass
        return True
    except Exception:
        return False

def maybe_send_scheduled(directory=APP_DIR, now=None):
    now = now or datetime.now()
    if not _schedule_lock.acquire(False):
        return
    try:
        settings = load_settings(directory)
        if not settings.get("schedule_enabled"):
            return
        try:
            scheduled_time = datetime.strptime(
                normalize_schedule_time(settings.get("schedule_time", DEFAULTS["schedule_time"])),
                "%H:%M:%S",
            ).time()
        except (ValueError, TypeError):
            return
        if (now.hour, now.minute, now.second) != (
            scheduled_time.hour, scheduled_time.minute, scheduled_time.second
        ):
            return
        send_push(settings, directory)
        with (Path(directory) / "push.log").open("a", encoding="utf-8") as log:
            log.write("{} scheduled push sent to {} subscribers\n".format(now.isoformat(timespec="seconds"), len(settings.get("subscribers", []))))
    finally:
        _schedule_lock.release()
