import unittest
import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cybercode.core.commands import (
    process_command,
    CommandRegistry,
    handle_session,
    handle_model,
    handle_status,
    handle_help
)


class TestCommands(unittest.TestCase):

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["DEFAULT_PROVIDER"] = "aliyun"
        os.environ["DEFAULT_MODEL"] = "glm-5"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_handle_help_without_args(self):
        """测试 /help 命令 - 无参数"""
        result = handle_help([])
        self.assertIn("可用斜杠命令", result)
        self.assertIn("/help", result)
        self.assertIn("/model", result)
        self.assertIn("/session", result)
        self.assertIn("/status", result)
        self.assertIn("/skills", result)

    def test_handle_help_with_args(self):
        """测试 /help 命令 - 带参数"""
        result = handle_help(["model"])
        self.assertIn("用法", result)
        self.assertIn("model", result.lower())

    def test_handle_status(self):
        """测试 /status 命令"""
        result = handle_status([])
        self.assertIn("系统状态", result)
        self.assertIn("aliyun", result)
        self.assertIn("glm-5", result)

    def test_process_command_help(self):
        """测试 process_command 处理 /help"""
        result = process_command("/help")
        self.assertIsNotNone(result)
        self.assertIn("可用斜杠命令", result)

    def test_process_command_unknown(self):
        """测试 process_command 处理未知命令"""
        result = process_command("/unknown")
        self.assertIsNotNone(result)
        self.assertIn("未知命令", result)

    def test_process_command_non_slash(self):
        """测试 process_command 处理非斜杠命令"""
        result = process_command("hello")
        self.assertIsNone(result)

    def test_command_registry_initialized(self):
        """测试命令注册表已初始化"""
        commands = CommandRegistry.get_commands()
        self.assertIn("/help", commands)
        self.assertIn("/model", commands)
        self.assertIn("/session", commands)
        self.assertIn("/status", commands)
        self.assertIn("/skills", commands)


class TestSessionCommand(unittest.TestCase):

    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_handle_session_list(self):
        """测试 /session 命令 - 列出会话"""
        os.environ["CURRENT_THREAD_ID"] = "test_session"
        result = handle_session([])
        self.assertIn("当前会话", result)
        self.assertIn("test_session", result)

    def test_handle_session_switch(self):
        """测试 /session 命令 - 切换会话"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("")
            temp_env = f.name

        try:
            os.environ["CURRENT_THREAD_ID"] = "original_session"
            result = handle_session(["new_session"])
            self.assertIn("new_session", result)
        finally:
            if os.path.exists(temp_env):
                os.remove(temp_env)

    def test_handle_session_switch_updates_env(self):
        """测试 /session 命令 - 切换后环境变量更新"""
        os.environ["CURRENT_THREAD_ID"] = "old_session"
        handle_session(["switched_session"])
        self.assertEqual(os.environ.get("CURRENT_THREAD_ID"), "switched_session")


class TestModelCommand(unittest.TestCase):

    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_handle_model_without_args(self):
        """测试 /model 命令 - 无参数"""
        os.environ["DEFAULT_PROVIDER"] = "openai"
        os.environ["DEFAULT_MODEL"] = "gpt-4o"
        result = handle_model([])
        self.assertIn("openai", result)
        self.assertIn("gpt-4o", result)

    def test_handle_model_switch(self):
        """测试 /model 命令 - 切换模型"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("")
            temp_env = f.name

        try:
            os.environ["DEFAULT_PROVIDER"] = "aliyun"
            os.environ["DEFAULT_MODEL"] = "glm-5"
            result = handle_model(["anthropic/claude-3"])
            self.assertIn("anthropic", result)
            self.assertIn("claude-3", result)
        finally:
            if os.path.exists(temp_env):
                os.remove(temp_env)


if __name__ == "__main__":
    unittest.main()
