# Homework Manager v1.6 Beta
适用于信息化教学的简单作业显示工具
/
A simple homework display tool for digital teaching

## 详细 / Details
打开 `Homework Manager.exe`（`main.py`）会启动此程序并将本程序加入系统托盘，此后请右键单击系统托盘上的此程序访问右键选单

在仪表盘中可启动推送管理器，推送管理器可以通过电子邮箱将作业推送到订阅账户

完成首次启动配置后，程序会在程序所在目录的 `data` 文件夹保存 `config.json`（程序设置）、`homework.json`（作业内容）和 `subscriptions.json`（订阅账户）。若在首次启动配置时直接退出，则不会创建这些数据文件。修改配置前会在 `data/backup` 中创建可见的 `config_时间戳.json.bak` 备份。旧版程序目录中的这些数据文件和配置备份会在首次运行时迁移到新目录。

/
Opening `Homework Manager.exe`\(`main.py`\), will start this program and add it to the system tray. After that, please right-click the program in the system tray to access the context menu

You can start the Subscription Manager from the dashboard, and the Subscription Manager emails homeworks to subscribed accounts

After first-launch setup, the program stores `config.json` (settings), `homework.json` (homework), and `subscriptions.json` (subscriptions) in the `data` folder beside the program. Quitting during setup creates none of these data files. Before changing settings, it creates a visible `config_timestamp.json.bak` backup in `data/backup`. Existing root-level data files and config backups are moved to the new folders on first run.

保存首次启动配置后，程序会注册当前用户的开始菜单快捷方式和 Windows 通知应用标识，用于通知中心显示应用标徽。仪表盘的“卸载”按钮提供“卸载程序”（删除程序目录、数据及通知注册）和“调试性卸载”（保留程序文件，仅删除数据及通知注册）。源码运行时会保留源码文件。

After saving first-launch settings, the app registers a Start menu shortcut and Windows notification identity so Toasts can use its app badge. The dashboard's Uninstall button offers a full uninstall or a debugging uninstall that keeps program files. Source files are retained when running from source.

## 运行和构建 / Run and build
- 安装 Python 3.10 或更新版本，并确保支持 Tcl/Tk
- 使用 `python -m pip install -r requirements.txt` 安装 `requirements.txt` 中列出的依赖项
- 用 `python main.py` 启动应用
- 在 Windows 上运行 `.build.ps1` 以在 `release/` 中创建可执行程序

/
- Install Python 3.10 or newer with Tcl/Tk support
- Install the dependencies listed in `requirements.txt` with `python -m pip install -r requirements.txt`
- Start the application with `python main.py`
- On Windows, run `.build.ps1` to create an executable in `release/`

## 许可证 / License
本项目采用 GNU 通用公共许可证第 3 版授权，或（由你选择）任何后续版本。详情见 `LICENSE.md`。源文件也带有 SPDX 许可证标识。第三方组件保留各自的许可；详情见 `THIRD_PARTY_NOTICES.md`

版权归 AUimpostor <auimpostor@outlook.com> 所有

/
This project is licensed under the GNU General Public License, version 3 or (at your option) any later version. See `LICENSE.md`. The source files also carry SPDX license identifiers. Third-party components retain their own licenses; see `THIRD_PARTY_NOTICES.md`

Copyright is attributed to AUimpostor <auimpostor@outlook.com>
