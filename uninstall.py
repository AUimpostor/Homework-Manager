"""External cleanup utility for Homework Manager (Windows)."""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

APP_ID = "AUimpostor.HomeworkManager"
APP_NAME = "Homework Manager"
REGISTRY_PATH = "Software\\Classes\\AppUserModelId\\" + APP_ID


def exe_dir():
    """Directory containing the running executable (frozen) or this script (source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_install_dir():
    """In a frozen release, Uninstall.exe sits inside the app directory."""
    here = exe_dir()
    candidates = (here / APP_NAME, here)
    for path in candidates:
        if (path / (APP_NAME + ".exe")).is_file() and (path / "_internal").exists():
            return path
        if (path / (APP_NAME + ".exe")).is_file() and (path / "icon.ico").is_file():
            return path
    return None


def remove_registration():
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
    except FileNotFoundError:
        pass
    link = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs" / (APP_NAME + ".lnk")
    link.unlink(missing_ok=True)


def main():
    if sys.platform != "win32":
        raise RuntimeError("此卸载程序仅支持 Windows。")
    root = tk.Tk()
    root.withdraw()
    install_dir = find_install_dir()
    if install_dir is None:
        message = "未找到可确认的 PyInstaller 发布目录。将清理注册信息及源码目录旁的 data 数据目录。"
    else:
        message = "将删除以下项目及其中全部数据：\n\n{}\n\n并清理通知注册信息和开始菜单快捷方式。此操作不可撤销。".format(install_dir)
    if not messagebox.askyesno("确定要卸载 Homework Manager 吗？", message, parent=root):
        root.destroy()
        return
    remove_registration()
    if install_dir:
        # Run a detached helper because Windows cannot delete the running script's directory.
        script = "Start-Sleep -Seconds 2; Remove-Item -LiteralPath '{}' -Recurse -Force".format(str(install_dir).replace("'", "''"))
        subprocess.Popen(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script], creationflags=0x08000000)
    else:
        data_dir = exe_dir() / "data"
        data_dir.exists() and shutil.rmtree(data_dir)
    root.destroy()


if __name__ == "__main__":
    main()
