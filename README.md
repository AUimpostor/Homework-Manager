# Homework Manager v1.5.1
适用于信息化教学的简单作业显示工具
/
A simple homework display tool for digital teaching

## 详细 / Details
打开 `Homework Manager.exe`（`main.py`）会启动此程序并将本程序加入系统托盘，此后请右键单击系统托盘上的此程序访问右键选单

在仪表盘中可启动推送管理器，推送管理器可以通过电子邮箱将作业推送到订阅账户

此程序在完成首次启动配置后，才会在程序所在目录创建 JSON 文件用作存储数据；若在首次启动配置时直接退出，则不会创建 JSON 文件

/
Opening `Homework Manager.exe`\(`main.py`\), will start this program and add it to the system tray. After that, please right-click the program in the system tray to access the context menu

You can start the Subscription Manager from the dashboard, and the Subscription Manager emails homeworks to subscribed accounts

After the first-launch setup is completed, this program creates JSON files in the program directory for data storage. Quitting during that setup creates no JSON files

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
