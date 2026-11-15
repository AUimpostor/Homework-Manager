"""Register and remove the Windows identity used by Homework Manager Toasts."""
import os
import shutil
import sys
import winreg
from pathlib import Path

APP_ID = "AUimpostor.HomeworkManager"
APP_NAME = "Homework Manager"
REGISTRY_PATH = "Software\\Classes\\AppUserModelId\\" + APP_ID


def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def register_app():
    from winotify._registry import Registry, P
    directory = application_dir()
    icon = Path(getattr(sys, "_MEIPASS", directory)) / "hwm.ico"
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs"
    shortcut = start_menu / (APP_NAME + ".lnk")
    target = Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(sys.executable).resolve().with_name("pythonw.exe")
    args = "" if getattr(sys, "frozen", False) else str(directory / "main.py")
    powershell = ('"$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\'{0}\');'
                  '$s.TargetPath=\'{1}\';$s.Arguments=\'{2}\';$s.IconLocation=\'{3}\';$s.Save()"').format(shortcut, target, args, icon)
    import subprocess
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", powershell], capture_output=True)
    if result.returncode:
        raise OSError("无法创建开始菜单快捷方式")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon))
    Registry(APP_ID, executable=P(str(target), str(target)), script_path=args, force_override=True)


def uninstall(remove_program=False):
    directory = application_dir()
    shortcut = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs" / (APP_NAME + ".lnk")
    shortcut.unlink(missing_ok=True)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
    except FileNotFoundError:
        pass
    shutil.rmtree(directory / "data", ignore_errors=True)
    if remove_program and getattr(sys, "frozen", False):
        import subprocess
        script = 'Start-Sleep -Seconds 2; Remove-Item -LiteralPath "{}" -Recurse -Force'.format(directory)
        subprocess.Popen(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script], creationflags=0x08000000)
