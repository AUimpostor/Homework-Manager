# Homework Manager v1.6 Beta 2
适用于信息化教学的简单作业显示工具 / 
A simple homework display tool for digital teaching

# Language - 简体中文
## 详细
打开 `Homework Manager.exe`（`main.py`）会启动此程序并将本程序加入系统托盘，此后请右键单击系统托盘上的此程序访问右键选单。

在仪表盘中可启动推送管理器，推送管理器可以通过电子邮箱将作业推送到订阅账户。

完成首次启动配置后，程序会在 `./data/` 下保存多项数据。若在首次启动配置时直接退出，则不会创建这些数据文件。

保存首次启动配置后，程序会注册当前用户的开始菜单快捷方式和 Windows 通知应用标识，用于通知中心显示应用标徽。

请通过 `uninstall.py` 或打包好的 `Uninstall.exe` 卸载程序，而不要擅自移除文件，否则可能会有注册表残留。

## 运行和构建
- 安装 Python 3.10 或更新版本，并确保支持 Tcl/Tk
- 使用 `python -m pip install -r requirements.txt` 安装 `requirements.txt` 中列出的依赖项
- 用 `python main.py` 启动应用
- 在 Windows 上运行 `.build.ps1` 以在 `./release/` 中创建可执行程序

## 许可证
本项目采用 GNU 通用公共许可证第 3 版授权，或（由你选择）任何后续版本。详情见 `LICENSE.md`。源文件也带有 SPDX 许可证标识。第三方组件保留各自的许可；详情见 `THIRD_PARTY_NOTICES.md`。

版权归 AUimpostor <auimpostor@outlook.com> 所有

# Language - English
## Details
Opening `Homework Manager.exe` (`main.py`) starts this program and adds it to the system tray. After that, please right-click the program in the system tray to access the context menu.

The Subscription Manager can be started from the dashboard. The Subscription Manager can send homework to subscribed accounts by email.

After first-launch setup is completed, the program saves multiple data items under `./data/`. If you quit directly during first-launch setup, these data files will not be created.

After saving first-launch setup, the program registers a Start menu shortcut and Windows notification app identity for the current user, for displaying the app badge in the notification center.

Please uninstall the program via `uninstall.py` or the packaged `Uninstall.exe`, and do not remove files on your own; otherwise, registry residue may remain.

## Run and build
- Install Python 3.10 or newer, and ensure Tcl/Tk support
- Install the dependencies listed in `requirements.txt` with `python -m pip install -r requirements.txt`
- Start the application with `python main.py`
- On Windows, run `.build.ps1` to create an executable in `./release/`

## License
This project is licensed under the GNU General Public License, version 3, or (at your option) any later version. See `LICENSE.md` for details. The source files also carry SPDX license identifiers. Third-party components retain their own licenses; see `THIRD_PARTY_NOTICES.md` for details.

Copyright is attributed to AUimpostor <auimpostor@outlook.com>
