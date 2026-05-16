import unittest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestConfig(unittest.TestCase):

    def test_config_import(self):
        """测试配置模块导入"""
        from cybercode.core.config import WORKSPACE_DIR, MEMORY_DIR, PERSONAS_DIR, SCRIPTS_DIR, OFFICE_DIR, SKILLS_DIR, DB_PATH, TASKS_FILE

        # 验证配置项存在
        self.assertIsInstance(WORKSPACE_DIR, str)
        self.assertIsInstance(MEMORY_DIR, str)
        self.assertIsInstance(PERSONAS_DIR, str)
        self.assertIsInstance(SCRIPTS_DIR, str)
        self.assertIsInstance(OFFICE_DIR, str)
        self.assertIsInstance(SKILLS_DIR, str)
        self.assertIsInstance(DB_PATH, str)
        self.assertIsInstance(TASKS_FILE, str)


class TestSkillLoader(unittest.TestCase):

    def test_skill_loader_import(self):
        """测试技能加载器模块导入"""
        try:
            from cybercode.core.skill_loader import load_dynamic_skills
            # 确保函数存在
            self.assertTrue(callable(load_dynamic_skills))
        except ImportError as e:
            # 如果导入失败，可能是因为依赖问题，但仍需确认模块结构
            self.fail(f"无法导入技能加载器: {e}")

    @patch('os.path.exists', return_value=False)
    @patch('os.listdir', side_effect=FileNotFoundError())
    def test_load_dynamic_skills_no_directory(self, mock_listdir, mock_exists):
        """测试技能加载器 - 不存在的目录"""
        from cybercode.core.skill_loader import load_dynamic_skills

        skills = load_dynamic_skills()
        self.assertEqual(skills, [])

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=[])
    def test_load_dynamic_skills_empty_directory(self, mock_listdir, mock_exists):
        """测试技能加载器 - 空目录"""
        from cybercode.core.skill_loader import load_dynamic_skills

        skills = load_dynamic_skills()
        self.assertEqual(skills, [])

    def test_lazy_loader_reads_full_content_only_on_help(self):
        from cybercode.core.skill_loader import LazySkillLoader

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "demo"
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo\ndescription: demo skill\n---\n\n# Demo\nfull instructions",
                encoding="utf-8",
            )

            loader = LazySkillLoader()
            with patch("cybercode.core.skill_loader.SKILLS_DIR", temp_dir):
                tools = loader.get_all_tools()
                self.assertEqual(len(tools), 1)
                result = tools[0].invoke({"mode": "help", "command": ""})

        self.assertIn("full instructions", result)

    def test_reload_skills_refreshes_changed_metadata(self):
        from cybercode.core.skill_loader import LazySkillLoader

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "demo"
            skill_dir.mkdir()
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo\ndescription: before\n---\n",
                encoding="utf-8",
            )

            loader = LazySkillLoader(scan_interval=3600)
            with patch("cybercode.core.skill_loader.SKILLS_DIR", temp_dir):
                first = loader.get_all_tools()
                skill_file.write_text(
                    "---\nname: demo\ndescription: after\n---\n",
                    encoding="utf-8",
                )
                second = loader.get_all_tools(force_rescan=True)

        self.assertIn("before", first[0].description)
        self.assertIn("after", second[0].description)


if __name__ == '__main__':
    unittest.main()
