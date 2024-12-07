# -*- coding: utf-8 -*-
# @Time    : 2024/12/7 09:42
# @Author  : flyrr
# @File    : /export_cursor_chat.py
# @IDE     : pycharm
import os
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime
import sys
import locale


def supports_emoji():
    """检查终端是否支持emoji"""
    return sys.stdout.encoding.lower() in ('utf-8', 'utf8')


class Icons:
    """定义图标，根据终端支持情况使用emoji或ASCII字符"""

    def __init__(self):
        self.use_emoji = supports_emoji()

        # 定义图标映射
        self.icons = {
            'success': '✅' if self.use_emoji else '[OK]',
            'error': '❌' if self.use_emoji else '[ERROR]',
            'folder': '📁' if self.use_emoji else '[DIR]',
            'loading': '⏳' if self.use_emoji else '[...]',
            'wave': '👋' if self.use_emoji else '[BYE]',
            'info': 'ℹ️' if self.use_emoji else '[INFO]'
        }

    def get(self, name):
        """获取图标"""
        return self.icons.get(name, '')


# 创建全局图标对象
icons = Icons()


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


def print_banner():
    """打印欢迎信息"""
    banner = f"""
╔══════════════════════════════════════════╗
║         Cursor Chat Exporter v1.0        ║
║                                          ║
║  导出您的 Cursor AI 聊天记录到MD/JSON文件  ║
╚══════════════════════════════════════════╝

{icons.get('info')} 支持导出格式：Markdown 和 JSON
"""
    print(banner)


def get_user_choice():
    """获取用户选择"""
    while True:
        print("\n请选择导出格式:")
        print("1. 仅导出 Markdown 文件 (默认)")
        print("2. 同时导出 Markdown 和 JSON 文件")
        print("3. 退出程序")

        choice = input("\n请输入选项 (1-3) [默认:1]: ").strip() or "1"

        if choice in ["1", "2", "3"]:
            return choice
        else:
            print(f"\n{icons.get('error')} 无效的选项，请重新选择")


def export_cursor_chat(export_json=False):
    """
    导出 Cursor 聊天记录
    Args:
        export_json: 是否同时导出 JSON 文件，默认为 False
    """
    try:
        # 获取用户主目录
        home = str(Path.home())

        possible_paths = [
            os.path.join(home, 'AppData/Roaming/Cursor/User/workspaceStorage'),  # Windows路径
            os.path.join(home, '.config/Cursor/User/workspaceStorage'),  # Linux路径
            os.path.join(home, 'Library/Application Support/Cursor/User/workspaceStorage'),
        ]

        # 找到第一个存在的路径
        workspace_path = None
        for path in possible_paths:
            if os.path.exists(path):
                workspace_path = path
                break

        if not workspace_path:
            print("找不到Cursor工作区目录")
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
            print("没有找到任何聊天记录")
            return

        # 创建输出目录
        md_output_dir = 'cursor_chats'
        os.makedirs(md_output_dir, exist_ok=True)

        if export_json:
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
                        if not title:
                            title = f"{format_timestamp(timestamp)}_Untitled_Chat" if timestamp else "Untitled_Chat"

                        # 清理文件名
                        safe_title = sanitize_filename(title)
                        time_str = format_timestamp(timestamp)

                        # 导出 Markdown 文件
                        md_filename = f"{time_str}_{safe_title}.md"
                        md_path = os.path.join(md_output_dir, md_filename)

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
                        if export_json:
                            json_filename = f"{time_str}_{safe_title}.json"
                            json_path = os.path.join(json_output_dir, json_filename)

                            # 创建单个对话的 JSON 数据
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

        # 关闭数据库连接
        conn.close()

        # 输出统计信息
        print(f"\n{icons.get('success')} 导出完成!")
        print(f"- 找到 {total_chats} 个聊天记录")
        print(f"- 包含 {total_tabs} 个对话标签页")
        print(f"{icons.get('folder')} Markdown文件位置: {os.path.abspath(md_output_dir)} ({md_count} 个)")
        if export_json:
            print(f"{icons.get('folder')} JSON文件位置: {os.path.abspath(json_output_dir)} ({json_count} 个)")

    except Exception as e:
        print(f"\n{icons.get('error')} 发生错误: {e}")
        return False
    return True


def main():
    """主函数"""
    print_banner()

    while True:
        choice = get_user_choice()

        if choice == "3":
            print(f"\n{icons.get('wave')} 感谢使用，再见！")
            break

        export_json = (choice == "2")

        print(f"\n{icons.get('loading')} 正在导出聊天记录...")
        success = export_cursor_chat(export_json)

        if success:
            print("\n是否继续导出? (y/n) [默认:n]: ", end="")
            if input().lower() != 'y':
                print(f"\n{icons.get('wave')} 感谢使用，再见！")
                break
        else:
            print("\n是否重试? (y/n) [默认:y]: ", end="")
            if input().lower() == 'n':
                print(f"\n{icons.get('wave')} 感谢使用，再见！")
                break

    # 添加暂停，让用户看到最后的消息
    print("\n按任意键退出...", end="")
    input()


if __name__ == "__main__":
    # 默认只导出 Markdown 文件
    # export_cursor_chat()

    # 如果需要同时导出 JSON，可以这样调用：
    # export_cursor_chat(export_json=True)

    # 交互式使用
    main()
    # 打包命令行版本
    # pip install pyinstaller
    # pyinstaller cursor-chat-exporter.spec
