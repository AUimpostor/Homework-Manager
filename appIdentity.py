"""Register and remove the Windows identity used by Homework Manager Toasts."""
import os
import sys
import winreg
from pathlib import Path

APP_ID = "AUimpostor.HomeworkManager"
APP_NAME = "Homework Manager"
REGISTRY_PATH = "Software\\Classes\\AppUserModelId\\" + APP_ID


def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def set_shortcut_app_id(shortcut):
    """Write the AppUserModelID required by Windows Toast into a shortcut."""
    import ctypes
    import uuid
    from ctypes import wintypes

    class Guid(ctypes.Structure):
        _fields_ = [("data", ctypes.c_ubyte * 16)]

    class PropertyKey(ctypes.Structure):
        _fields_ = [("fmtid", Guid), ("pid", wintypes.DWORD)]

    class PropVariantValue(ctypes.Union):
        _fields_ = [("pointer", ctypes.c_void_p), ("padding", ctypes.c_ubyte * 16)]

    class PropVariant(ctypes.Structure):
        _fields_ = [
            ("vt", ctypes.c_ushort),
            ("reserved1", ctypes.c_ushort),
            ("reserved2", ctypes.c_ushort),
            ("reserved3", ctypes.c_ushort),
            ("value", PropVariantValue),
        ]

    def com_method(instance, index, result_type, *argument_types):
        vtable = ctypes.cast(instance, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(result_type, ctypes.c_void_p, *argument_types)(vtable[index])

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(Guid), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(Guid), ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = ctypes.c_long
    initialized = ole32.CoInitialize(None)
    if initialized not in (0, 1):
        raise OSError(initialized, "无法初始化通知快捷方式")

    link = ctypes.c_void_p()
    store = ctypes.c_void_p()
    persist = ctypes.c_void_p()
    try:
        clsid = Guid.from_buffer_copy(uuid.UUID("00021401-0000-0000-C000-000000000046").bytes_le)
        iid_link = Guid.from_buffer_copy(uuid.UUID("000214F9-0000-0000-C000-000000000046").bytes_le)
        result = ole32.CoCreateInstance(
            ctypes.byref(clsid), None, 1, ctypes.byref(iid_link), ctypes.byref(link)
        )
        if result < 0:
            raise OSError(result, "无法打开通知快捷方式")

        query = com_method(
            link, 0, ctypes.c_long, ctypes.POINTER(Guid), ctypes.POINTER(ctypes.c_void_p)
        )
        iid_persist = Guid.from_buffer_copy(uuid.UUID("0000010B-0000-0000-C000-000000000046").bytes_le)
        result = query(link, ctypes.byref(iid_persist), ctypes.byref(persist))
        if result < 0:
            raise OSError(result, "无法读取通知快捷方式")
        load = com_method(persist, 5, ctypes.c_long, wintypes.LPCWSTR, wintypes.DWORD)
        result = load(persist, str(shortcut), 2)
        if result < 0:
            raise OSError(result, "无法加载通知快捷方式")

        iid_store = Guid.from_buffer_copy(uuid.UUID("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99").bytes_le)
        result = query(link, ctypes.byref(iid_store), ctypes.byref(store))
        if result < 0:
            raise OSError(result, "无法打开通知快捷方式属性")
        set_value = com_method(
            store, 6, ctypes.c_long, ctypes.POINTER(PropertyKey), ctypes.POINTER(PropVariant)
        )
        key = PropertyKey(
            Guid.from_buffer_copy(uuid.UUID("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3").bytes_le), 5
        )
        app_id = ctypes.create_unicode_buffer(APP_ID)
        value = PropVariant(vt=31)
        value.value.pointer = ctypes.cast(app_id, ctypes.c_void_p)
        result = set_value(store, ctypes.byref(key), ctypes.byref(value))
        if result < 0:
            raise OSError(result, "无法写入通知应用标识")
        commit = com_method(store, 7, ctypes.c_long)
        result = commit(store)
        if result < 0:
            raise OSError(result, "无法保存通知应用标识")
        save = com_method(persist, 6, ctypes.c_long, wintypes.LPCWSTR, wintypes.BOOL)
        result = save(persist, str(shortcut), True)
        if result < 0:
            raise OSError(result, "无法保存通知快捷方式")
    finally:
        for instance in (store, persist, link):
            if instance:
                com_method(instance, 2, wintypes.ULONG)(instance)
        ole32.CoUninitialize()


def register_app():
    from winotify._registry import Registry, P
    directory = application_dir()
    resources = Path(getattr(sys, "_MEIPASS", directory))
    icon = resources / "icon.ico"
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs"
    shortcut = start_menu / (APP_NAME + ".lnk")
    target = Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(sys.executable).resolve().with_name("pythonw.exe")
    args = "" if getattr(sys, "frozen", False) else str(directory / "main.py")
    powershell = ('$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\'{0}\');'
                  '$s.TargetPath=\'{1}\';$s.Arguments=\'{2}\';$s.IconLocation=\'{3}\';$s.Save()').format(shortcut, target, args, icon)
    import subprocess
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", powershell], capture_output=True)
    if result.returncode or not shortcut.is_file():
        raise OSError("无法创建开始菜单快捷方式")
    set_shortcut_app_id(shortcut)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
        winreg.SetValueEx(key, "displayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon))
    Registry(APP_ID, executable=P(str(target), str(target)), script_path=args, force_override=True)


