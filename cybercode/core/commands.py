"""
=====================================================================
commands.py - 斜杠命令系统
=====================================================================
主要功能：
1. 定义斜杠命令 (Slash Commands)
2. 实现命令自动补全
3. 统一命令处理入口

命令列表：
- /help   : 显示所有可用命令
- /status : 显示当前系统状态
- /skills : 列出已加载的技能
- /model  : 查看/切换当前模型信息
- /session: 查看/切换会话
=====================================================================
"""

import os
import subprocess
import asyncio
import sqlite3
from typing import List, Callable, Optional, Any
from dataclasses import dataclass, field
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .config import DB_PATH, SKILLS_DIR, TASKS_FILE, MEMORY_DIR, PROJECT_ROOT
from .skill_loader import load_dynamic_skills
from .tools.builtins import get_system_model_info
from .theme import get_theme, list_themes, set_theme


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[[List[str]], Any]
    usage: str = ""


class CommandRegistry:
    _commands: dict = {}
    _initialized: bool = False

    @classmethod
    def register(cls, name: str, description: str, handler: Callable, usage: str = ""):
        if not name.startswith("/"):
            name = "/" + name
        cls._commands[name] = Command(
            name=name,
            description=description,
            handler=handler,
            usage=usage
        )

    @classmethod
    def get_commands(cls) -> dict:
        return cls._commands

    @classmethod
    def get_command_names(cls) -> List[str]:
        return list(cls._commands.keys())

    @classmethod
    def get_command(cls, name: str) -> Optional[Command]:
        if not name.startswith("/"):
            name = "/" + name
        return cls._commands.get(name)

    @classmethod
    def get_all_descriptions(cls) -> List[tuple]:
        return [(cmd.name, cmd.description) for cmd in cls._commands.values()]


class SlashCommandCompleter(Completer):
    def __init__(self, commands: List[str]):
        self.commands = commands

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()
        if len(parts) == 0:
            return

        if parts[0] == "/session" and len(parts) > 1:
            current = parts[-1]
            sessions = self._get_sessions()
            for session in sessions:
                if current.lower() in session.lower():
                    yield Completion(session, start_position=-len(current))
            return

        if parts[0] == "/theme" and len(parts) > 1:
            current = parts[-1]
            theme_options = [theme.name for theme in list_themes()] + ["preview"]
            for theme_name in theme_options:
                if current.lower() in theme_name.lower():
                    yield Completion(theme_name, start_position=-len(current))
            return

        current = text[1:]
        for cmd in self.commands:
            if cmd.startswith("/"):
                cmd = cmd[1:]
            if current.lower() in cmd.lower():
                yield Completion(cmd, start_position=-len(current))

    def _get_sessions(self) -> List[str]:
        sessions = []
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
                sessions = [row[0] for row in cursor.fetchall()]
                conn.close()
            except:
                pass
        return sessions


def handle_help(args: List[str]) -> str:
    registry = CommandRegistry.get_commands()
    if not args:
        lines = [" 可用斜杠命令:", ""]
        for cmd in registry.values():
            lines.append(f"  {cmd.name:<12} - {cmd.description}")
        lines.append("")
        lines.append("  输入 /help <命令> 查看具体用法")
        return "\n".join(lines)
    if args:
        cmd = CommandRegistry.get_command(args[0])
        if cmd:
            if cmd.usage:
                return f"  用法: {cmd.usage}\n\n  {cmd.description}"
            return f"  {cmd.description}"
        return f"  未知命令: /{args[0]}"


def handle_status(args: List[str]) -> str:
    lines = ["  系统状态:", ""]
    provider = os.getenv("DEFAULT_PROVIDER", "未设置")
    model = os.getenv("DEFAULT_MODEL", "未设置")
    lines.append(f"  模型: {provider} / {model}")

    if os.path.exists(SKILLS_DIR):
        skill_count = len([d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d))])
    else:
        skill_count = 0
    lines.append(f"  技能数: {skill_count}")

    if os.path.exists(TASKS_FILE):
        import json
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            lines.append(f"  定时任务: {len(tasks)} 个")
        except:
            lines.append("  定时任务: 0 个")
    else:
        lines.append("  定时任务: 0 个")

    return "\n".join(lines)


def handle_skills(args: List[str]) -> str:
    skills = load_dynamic_skills()
    if not skills:
        return "  当前无已加载的技能。"

    lines = ["  已加载的技能:", ""]
    for skill in skills:
        desc = skill.description.split("\n")[0][:50]
        lines.append(f"  - {skill.name:<20} {desc}")
    return "\n".join(lines)


def handle_model(args: List[str]) -> str:
    from dotenv import set_key
    from .config import PROJECT_ROOT

    ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

    if not args:
        from .tools.builtins import get_system_model_info
        return get_system_model_info.invoke({})

    new_model = args[0]

    supported_providers = ["openai", "anthropic", "aliyun", "tencent", "z.ai", "ollama", "other"]

    if "/" in new_model:
        parts = new_model.split("/", 1)
        provider = parts[0].lower()
        model = parts[1]

        if provider not in supported_providers:
            return f"  不支持的提供商: {provider}\n  支持: {', '.join(supported_providers)}"

        try:
            set_key(ENV_PATH, "DEFAULT_PROVIDER", provider)
            set_key(ENV_PATH, "DEFAULT_MODEL", model)
            os.environ["DEFAULT_PROVIDER"] = provider
            os.environ["DEFAULT_MODEL"] = model
            return f"  已切换模型: {provider} / {model}"
        except Exception as e:
            return f"  切换失败: {str(e)}"

    current_provider = os.getenv("DEFAULT_PROVIDER", "")
    if not current_provider:
        return "  请使用 /model provider/model 格式指定"

    try:
        set_key(ENV_PATH, "DEFAULT_MODEL", new_model)
        os.environ["DEFAULT_MODEL"] = new_model
        return f"  已切换模型: {current_provider} / {new_model}"
    except Exception as e:
        return f" 切换失败: {str(e)}"


def handle_session(args: List[str]) -> str:
    from dotenv import set_key
    from .config import PROJECT_ROOT

    ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

    if not args:
        current = os.getenv("CURRENT_THREAD_ID", "local_geek_master")
        lines = [f"  当前会话: {current}", ""]
        # lines.append("  用法: /session <会话名>  或  /session delete <会话名>")

        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
                threads = cursor.fetchall()
                conn.close()

                if threads:
                    lines.append("")
                    lines.append("  可用会话:")
                    for (tid,) in threads:
                        marker = " ← 当前" if tid == current else ""
                        lines.append(f"    - {tid}{marker}")
                else:
                    lines.append("  无历史会话")
            except Exception as e:
                lines.append(f"  查询会话失败: {str(e)}")
        else:
            lines.append("  无会话记录")

        return "\n".join(lines)

    if args[0] in ["delete", "rm", "del"]:
        if len(args) < 2:
            return "  请指定要删除的会话名: /session delete <会话名>"

        session_to_delete = args[1]

        current = os.getenv("CURRENT_THREAD_ID", "local_geek_master")
        if session_to_delete == current:
            return "  无法删除当前会话，请先切换到其他会话"

        if not os.path.exists(DB_PATH):
            return "  无会话记录"

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
            threads = [row[0] for row in cursor.fetchall()]

            if session_to_delete not in threads:
                return f"  会话不存在: {session_to_delete}"

            cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (session_to_delete,))
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (session_to_delete,))
            conn.commit()
            conn.close()

            log_file = os.path.join(PROJECT_ROOT, "logs", f"{session_to_delete}.jsonl")
            if os.path.exists(log_file):
                os.remove(log_file)

            return f"  已删除会话: {session_to_delete}"
        except Exception as e:
            return f"  删除失败: {str(e)}"

    new_session = args[0]
    try:
        set_key(ENV_PATH, "CURRENT_THREAD_ID", new_session)
        os.environ["CURRENT_THREAD_ID"] = new_session
        return f"  已切换到会话: {new_session}"
    except Exception as e:
        return f"  切换失败: {str(e)}"


def handle_theme(args: List[str]) -> str:
    from dotenv import set_key

    cwd_env_path = os.path.join(os.getcwd(), ".env")
    env_path = cwd_env_path if os.path.exists(cwd_env_path) else os.path.join(PROJECT_ROOT, ".env")
    current_theme = get_theme()

    if not args:
        lines = [f"  当前主题: {current_theme.name} ({current_theme.display_name})", ""]
        lines.append("  可用主题:")
        for theme in list_themes():
            marker = " ← 当前" if theme.name == current_theme.name else ""
            lines.append(f"    - {theme.name:<12} {theme.display_name}{marker}")
        lines.append("")
        lines.append("  输入 /theme preview 查看主题预览")
        return "\n".join(lines)

    requested_theme = args[0].strip().lower()
    if requested_theme == "preview":
        lines = ["  主题预览:", ""]
        for theme in list_themes():
            lines.append(
                f"  {theme.ansi_primary}■ primary\033[0m "
                f"{theme.ansi_accent}■ accent\033[0m "
                f"{theme.ansi_info}■ info\033[0m "
                f"{theme.ansi_success}■ success\033[0m "
                f"{theme.ansi_warning}■ warning\033[0m "
                f"{theme.ansi_error}■ error\033[0m "
                f"  {theme.name} ({theme.display_name})"
            )
        return "\n".join(lines)

    available_theme_names = [theme.name for theme in list_themes()]
    if requested_theme not in available_theme_names:
        return f"  未知主题: {requested_theme}\n  可用: {', '.join(available_theme_names)}"

    try:
        set_key(env_path, "CYBERCODE_THEME", requested_theme)
        os.environ["CYBERCODE_THEME"] = requested_theme
        theme = set_theme(requested_theme)
        return f"  已切换主题: {theme.name} ({theme.display_name})"
    except Exception as e:
        return f"  切换失败: {str(e)}"

def handle_exit(args: List[str]) -> str:
    return "exit"

def init_commands():
    if CommandRegistry._initialized:
        return

    CommandRegistry.register(
        "exit",
        "退出当前会话",
        handle_exit,
        "/exit"
    )
    CommandRegistry.register(
        "help",
        "显示所有可用命令",
        handle_help,
        "/help [命令名]"
    )
    CommandRegistry.register(
        "status",
        "显示当前系统状态",
        handle_status,
        "/status"
    )
    CommandRegistry.register(
        "skills",
        "列出已加载的技能",
        handle_skills,
        "/skills"
    )
    CommandRegistry.register(
        "model",
        "查看/切换当前模型 (例: /model aliyun/glm-4)",
        handle_model,
        "/model [provider/model]"
    )
    CommandRegistry.register(
        "session",
        "查看/切换/删除会话 (例: /session my_project, /session delete my_project)",
        handle_session,
        "/session [会话名]"
    )
    CommandRegistry.register(
        "theme",
        "查看/切换当前主题 (例: /theme acid-pulse)",
        handle_theme,
        "/theme [主题名]"
    )

    CommandRegistry._initialized = True


def process_command(input_text: str) -> Optional[str]:
    if not input_text.startswith("/"):
        return None

    parts = input_text.strip().split()
    if not parts:
        return None

    cmd_name = parts[0]
    args = parts[1:]

    cmd = CommandRegistry.get_command(cmd_name)
    if cmd:
        try:
            return cmd.handler(args)
        except Exception as e:
            return f"  命令执行出错: {str(e)}"

    return f"  未知命令: {cmd_name}，输入 /help 查看可用命令"


init_commands()
