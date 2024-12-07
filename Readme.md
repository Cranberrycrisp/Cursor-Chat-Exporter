# Cursor Chat Exporter

一个简单的工具，用于导出 Cursor AI 的聊天记录到 Markdown 和 JSON 文件。(
可用于0.43以前的版本，旧版本覆盖安装不会删除聊天数据)

0.42.5版本：[0.42.5 Build Links - Cursor - Community Forum](https://forum.cursor.com/t/0-42-5-build-links/30521)

版本查看：`Help > About Cursor`

关闭自动更新：`文件 > 首选项 > 设置` 搜索框输入 update，`应用程序 > 更新` 关闭自动更新相关设置

程序会根据操作系统自动检测 Cursor 工作区存储位置：

- Windows: `%APPDATA%\Cursor\User\workspaceStorage`
- WSL2: `/mnt/c/Users/<USERNAME>/AppData/Roaming/Cursor/User/workspaceStorage`
- macOS: `~/Library/Application Support/Cursor/User/workspaceStorage`
- Linux: `~/.config/Cursor/User/workspaceStorage`

如果自动检测失败，可以在左上角 ⚙️ 中手动配置路径。

![Main Interface](https://raw.githubusercontent.com/Cranberrycrisp/Cursor-Chat-Exporter/refs/heads/main/main%20interface.png)

## 功能特点

- 导出所有 Cursor AI 聊天记录到 Markdown 文件
- 可选择同时导出 JSON 格式
- 文件名添加创建时间前缀（默认）。考虑到文件名重复会被覆盖，且聊天记录过多时可以根据文件名排序，可手动取消。
- 保留代码块和格式
- 简洁的图形界面
- 实时导出进度显示

## 下载使用

### 方式一：直接下载

windows 从 [Releases](https://github.com/Cranberrycrisp/Cursor-Chat-Exporter/releases/) 页面下载最新版本的`exe`可执行文件。

### 方式二：python脚本运行

安装依赖

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

```

```
# 命令行版本
python export_cursor_chat.py

# GUI版本
python export_cursor_chat_gui.py
```

### 方式三：自行打包

1. 克隆仓库

```bash
git clone https://github.com/Cranberrycrisp/Cursor-Chat-Exporter.git
cd cursor-chat-exporter
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. 安装依赖

```bash
pip install PyQt6 pyinstaller
```

4. 打包程序

```bash
pyinstaller cursor-chat-exporter-gui.spec

# 打包命令行版本
# pyinstaller cursor-chat-exporter.spec
```

打包后的程序位于 `dist` 目录下。

## 使用说明

1. 运行程序
2. 选择是否同时导出 JSON 文件
3. 点击"开始导出"
4. 等待导出完成
5. 导出的文件将保存在程序所在目录的 `cursor_chats` 文件夹中

## 其他

- `state.vscdb`文件可以 pip 安装 datasette，`pip install datasette` 运行 `datasette state.vscdb`，在浏览器 `http://localhost:8001/state?` 查看

## 开发环境

- Python 3.11.10 (3.8+)
- PyQt6
- Windows 10/11

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](https://github.com/thomas-pedersen/cursor-chat-browser/blob/main/LICENSE)
