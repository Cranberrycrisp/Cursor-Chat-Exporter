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
                             QTextEdit, QProgressBar, QMessageBox, QFileDialog,
                             QFrame, QDialog, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import sys
import platform


def sanitize_filename(filename):
    """清理文件名，移除非法字符，限制长度"""
    # 移除换行符和多余空格
    filename = ' '.join(filename.split())
    
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*\n\r]', '', filename)
    
    # 限制文件名长度(不包括扩展名)为50个字符
    filename = filename[:50]
    
    # 确保文件名不为空
    return filename.strip() or 'untitled'


def format_timestamp(timestamp):
    """将时间戳转换为易读的日期时间格式"""
    try:
        dt = datetime.fromtimestamp(timestamp / 1000)
        # return dt.strftime('%Y-%m-%d_%H-%M-%S')
        return dt.strftime('%Y-%m-%d_%H-%M')
    except Exception:
        return 'unknown_time'


class PathConfigDialog(QDialog):
    """路径配置对话框"""

    def __init__(self, current_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle('工作区路径配置 ⚙️')
        self.setFixedSize(500, 150)

        layout = QVBoxLayout()

        # 说明文字
        desc = QLabel('请选择 Cursor 工作区存储路径:')
        layout.addWidget(desc)

        # 路径输入框和浏览按钮
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(current_path)
        path_layout.addWidget(self.path_edit)

        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # 确定取消按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def browse_path(self):
        """浏览文件夹"""
        path = QFileDialog.getExistingDirectory(self, '选择工作区目录')
        if path:
            self.path_edit.setText(path)

    def get_path(self):
        """获取选择的路径"""
        return self.path_edit.text()


class ExportWorker(QThread):
    """后台导出线程"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(bool, str)  # 完成信号：(是否成功, 消息)

    def __init__(self, workspace_path, export_json=False, include_timestamp=True):
        super().__init__()
        self.workspace_path = workspace_path
        self.export_json = export_json
        self.include_timestamp = include_timestamp

    def run(self):
        try:
            if not os.path.exists(self.workspace_path):
                self.finished.emit(False, "工作区路径不存在")
                return

            chats = []
            workspace_path = self.workspace_path

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
        self.workspace_path = self.get_default_workspace_path()
        self.initUI()

    def get_default_workspace_path(self):
        """获取默认工作区路径"""
        system = platform.system()
        home = str(Path.home())

        # 检测操作系统类型
        if system == 'Windows':
            path = os.path.join(os.getenv('APPDATA'), 'Cursor', 'User', 'workspaceStorage')
        elif system == 'Darwin':  # macOS
            path = os.path.join(home, 'Library', 'Application Support', 'Cursor', 'User', 'workspaceStorage')
        elif system == 'Linux':
            # 检查是否是 WSL
            if 'microsoft' in platform.uname().release.lower():
                # WSL2 路径
                windows_home = os.path.join('/mnt/c/Users', os.getenv('USER'))
                path = os.path.join(windows_home, 'AppData/Roaming/Cursor/User/workspaceStorage')
            else:
                # 普通 Linux 路径
                path = os.path.join(home, '.config', 'Cursor', 'User', 'workspaceStorage')
        else:
            path = ''

        return path if os.path.exists(path) else ''

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
        self.timestamp_checkbox = QCheckBox('文件名添加创建时间 🕒')
        self.timestamp_checkbox.setChecked(True)  # 默认选中
        options_layout.addWidget(self.timestamp_checkbox)

        layout.addLayout(options_layout)

        # 添加菜单栏
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('设置 ⚙️')

        # 添加路径配置选项
        path_action = settings_menu.addAction('配置工作区路径')
        path_action.triggered.connect(self.configure_path)

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

        # 在底部添加作者信息
        author_layout = QHBoxLayout()

        # 使用 QLabel 的 HTML 功能添加带链接的文本
        author_label = QLabel('Made by <a href="https://github.com/Cranberrycrisp">Cranberrycrisp</a> 🚀')
        author_label.setOpenExternalLinks(True)  # 允许打开外部链接
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 设置样式
        author_label.setStyleSheet("""
                    QLabel {
                        color: #666;
                        padding: 5px;
                        margin-top: 10px;
                    }
                    QLabel a {
                        color: #0366d6;
                        text-decoration: none;
                    }
                    QLabel a:hover {
                        text-decoration: underline;
                    }
                """)

        author_layout.addWidget(author_label)
        layout.addLayout(author_layout)  # 添加到主布局

        # 添加一条分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #ddd;")
        layout.addWidget(separator)

        # 添加版本信息
        version_label = QLabel('v1.0.0')
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(version_label)

    def log(self, message):
        """添加日志"""
        self.log_text.append(message)

    def configure_path(self):
        """配置工作区路径"""
        dialog = PathConfigDialog(self.workspace_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_path = dialog.get_path()
            if os.path.exists(new_path):
                self.workspace_path = new_path
                self.log(f"✅ 工作区路径已更新: {new_path}")
            else:
                QMessageBox.warning(self, "错误", "所选路径不存在！")

    def start_export(self):
        """开始导出"""
        if not self.workspace_path:
            QMessageBox.warning(self, "错误", "请先配置工作区路径！")
            self.configure_path()
            return

        if not os.path.exists(self.workspace_path):
            QMessageBox.warning(self, "错误", "工作区路径不存在！")
            self.configure_path()
            return

        self.export_button.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.log("🚀 开始导出...")

        # 传递工作区路径给导出线程
        self.worker = ExportWorker(
            workspace_path=self.workspace_path,
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
