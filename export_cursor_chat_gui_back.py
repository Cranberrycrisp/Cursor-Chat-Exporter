# -*- coding: utf-8 -*-
# @Time    : 2024/12/7 09:42
# @Author  : flyrr
# @File    : /export_cursor_chat_gui.py
# @IDE     : pycharm
import os
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QCheckBox,
                             QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


def sanitize_filename(filename):
    """清理文件名，移除非法字符，只保留字母、数字、中文和基本标点"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename.strip() or 'untitled'


def format_timestamp(timestamp):
    """将时间戳转换为易读的日期时间格式"""
    try:
        dt = datetime.fromtimestamp(timestamp / 1000)
        # return dt.strftime('%Y-%m-%d_%H-%M-%S')
        return dt.strftime('%Y-%m-%d_%H-%M')
    except Exception:
        return 'unknown_time'


class ExportWorker(QThread):
    """后台导出线程"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(bool, str)  # 完成信号：(是否成功, 消息)

    def __init__(self, export_json=False, include_timestamp=True):
        super().__init__()
        self.export_json = export_json
        self.include_timestamp = include_timestamp

    def run(self):
        try:
            # 获取用户主目录
            home = str(Path.home())

            possible_paths = [
                os.path.join(home, 'AppData/Roaming/Cursor/User/workspaceStorage'),
                os.path.join(home, 'Library/Application Support/Cursor/User/workspaceStorage'),
                os.path.join(home, '.config/Cursor/User/workspaceStorage'),
            ]

            # 找到工作区目录
            workspace_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    workspace_path = path
                    break

            if not workspace_path:
                self.finished.emit(False, "找不到Cursor工作区目录")
                return

            chats = []

            # 遍历所有工作区文件夹
            for workspace in os.listdir(workspace_path):
                db_path = os.path.join(workspace_path, workspace, 'state.vscdb')

                if not os.path.exists(db_path):
                    continue

                # 连接数据库
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 获取所有需要的数据
                cursor.execute("""
                    SELECT [key], value 
                    FROM ItemTable 
                    WHERE [key] IN (
                        'workbench.panel.aichat.view.aichat.chatdata',
                        'composer.composerData'
                    )
                """)

                for row in cursor.fetchall():
                    key, value = row
                    try:
                        data = json.loads(value)
                        chats.append({
                            'workspace': workspace,
                            'type': key,
                            'data': data
                        })
                    except Exception as e:
                        continue

                conn.close()

            if not chats:
                self.finished.emit(False, "没有找到任何聊天记录")
                return

            self.progress.emit("🔍 开始导出...")

            # 创建输出目录
            md_output_dir = 'cursor_chats'
            os.makedirs(md_output_dir, exist_ok=True)

            if self.export_json:
                json_output_dir = 'cursor_chats_json'
                os.makedirs(json_output_dir, exist_ok=True)

            # 记录统计信息
            total_chats = len(chats)
            total_tabs = 0
            md_count = 0
            json_count = 0
            # 遍历并导出每个对话
            for chat in chats:
                if chat['type'] == 'workbench.panel.aichat.view.aichat.chatdata':
                    data = chat['data']
                    if 'tabs' in data:
                        total_tabs += len(data['tabs'])
                        for tab in data['tabs']:
                            # 获取对话标题和时间戳
                            title = tab.get('chatTitle', '')
                            timestamp = tab.get('lastSendTime', 0)
                            time_str = format_timestamp(timestamp)

                            if not title:
                                title = f"Chat_{time_str}"

                            # 清理文件名
                            safe_title = sanitize_filename(title)

                            # 获取时间戳字符串
                            time_str = format_timestamp(timestamp) if self.include_timestamp else ""

                            # 处理 Markdown 文件名
                            md_filename = (f"{time_str}_{safe_title}.md" if time_str
                                           else f"{safe_title}.md")
                            md_path = os.path.join(md_output_dir, md_filename)

                            # 导出 Markdown 文件
                            with open(md_path, 'w', encoding='utf-8') as f:
                                # 写入标题
                                f.write(f"# {title}\n\n")

                                # 写入工作区信息
                                f.write(f"Workspace: `{chat['workspace']}`\n\n")

                                # 写入时间信息
                                if timestamp:
                                    f.write(f"Last Updated: {timestamp}\n\n")

                                # 写入对话内容
                                if 'bubbles' in tab:
                                    for bubble in tab['bubbles']:
                                        # 用户消息
                                        if bubble.get('type') == 'user':
                                            if 'text' in bubble:
                                                f.write(f"## User\n\n{bubble['text']}\n\n")

                                            # 添加代码选择
                                            if bubble.get('selections'):
                                                f.write("Selected code:\n")
                                                for selection in bubble['selections']:
                                                    f.write(f"```{selection.get('uri', {}).get('path', '')}\n")
                                                    f.write(f"{selection.get('text', '')}\n```\n\n")

                                        # AI消息
                                        elif bubble.get('type') == 'ai':
                                            if 'text' in bubble:
                                                f.write(f"## Assistant\n\n{bubble['text']}\n\n")

                                            # 添加代码块
                                            if bubble.get('codeBlocks'):
                                                for code_block in bubble['codeBlocks']:
                                                    f.write(f"```{code_block.get('language', '')}\n")
                                                    f.write(f"{code_block.get('code', '')}\n```\n\n")

                            # 可选：导出 JSON 文件
                            if self.export_json:
                                json_filename = (f"{time_str}_{safe_title}.json" if time_str
                                                 else f"{safe_title}.json")
                                json_path = os.path.join(json_output_dir, json_filename)

                                chat_data = {
                                    'workspace': chat['workspace'],
                                    'title': title,
                                    'lastSendTime': timestamp,
                                    'bubbles': tab.get('bubbles', [])
                                }

                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(chat_data, f, ensure_ascii=False, indent=2)
                                json_count += 1

                            md_count += 1
                            self.progress.emit(f"📝 已导出: {md_count} 个文件...")

            success_msg = f"✨ 导出完成!\n📊 共导出 {md_count} 个 Markdown 文件\n📂 位置: {os.path.abspath(md_output_dir)}"
            if self.export_json:
                success_msg += f"\n📊 同时导出 {json_count} 个 JSON 文件\n📂 位置: {os.path.abspath(json_output_dir)}"

            self.finished.emit(True, success_msg)

        except Exception as e:
            self.finished.emit(False, f"⚠️ 发生错误: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """初始化UI"""
        self.setWindowTitle('Cursor Chat Exporter 📤')
        self.setFixedSize(600, 400)

        # 设置字体，确保支持 emoji
        emoji_font = QFont()
        emoji_font.setFamilies(['Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', 'Segoe UI Symbol', 'Arial'])
        QApplication.setFont(emoji_font)

        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 标题
        title = QLabel('Cursor Chat Exporter 📤')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # 说明文字
        desc = QLabel('导出您的 Cursor AI 聊天记录到MD/JSON文件 💾')
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # 选项区域
        options_layout = QVBoxLayout()

        # JSON导出选项
        self.json_checkbox = QCheckBox('同时导出JSON文件 📄')
        options_layout.addWidget(self.json_checkbox)

        # 时间戳选项
        self.timestamp_checkbox = QCheckBox('文件名包含时间戳 🕒')
        self.timestamp_checkbox.setChecked(True)  # 默认选中
        options_layout.addWidget(self.timestamp_checkbox)

        layout.addLayout(options_layout)

        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.export_button = QPushButton('开始导出 📥')
        self.export_button.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_button)

        self.close_button = QPushButton('关闭 ❌')
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def log(self, message):
        """添加日志"""
        self.log_text.append(message)

    def start_export(self):
        """开始导出"""
        self.export_button.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.log("🚀 开始导出...")

        # 创建并启动工作线程，传递两个选项
        self.worker = ExportWorker(
            export_json=self.json_checkbox.isChecked(),
            include_timestamp=self.timestamp_checkbox.isChecked()
        )
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.export_finished)
        self.worker.start()

    def export_finished(self, success, message):
        """导出完成的处理"""
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.export_button.setEnabled(True)

        if success:
            self.log(message)
            QMessageBox.information(self, "成功 ✨", message)
        else:
            self.log(message)
            QMessageBox.warning(self, "错误 ⚠️", message)


def main():
    app = QApplication([])

    # 设置应用程序样式
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    app.exec()


if __name__ == '__main__':
    main()
    # 打包
    # pyinstaller cursor-chat-exporter-gui.spec
