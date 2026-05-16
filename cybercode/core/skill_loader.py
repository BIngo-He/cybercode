"""
=====================================================================
skill_loader.py - 动态技能加载器
=====================================================================
主要功能：
1. 扫描 workspace/office/skills/ 目录
2. 解析 SKILL.md 文件获取技能元数据
3. 动态注册为 LangChain StructuredTool
4. 实现两阶段执行：help(阅读说明书) -> run(执行命令)
5. 支持懒加载、元数据缓存和热更新
=====================================================================
"""

import os
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .config import SKILLS_DIR
from .tools.sandbox_tools import execute_office_shell


class DynamicSkillInput(BaseModel):
    mode: str = Field(
        description="必须是 'help' 或 'run'。第一次使用时强烈建议先传入 'help' 阅读说明书。"
    )
    command: Optional[str] = Field(
        default="",
        description="仅在 mode='run' 时需要。你要执行的完整命令，保留 {baseDir} 占位符。",
    )


class LazySkillLoader:
    """
    渐进式技能加载器 + 缓存机制

    特性：
    1. 启动时只扫描元数据（name, description），不加载完整内容
    2. 首次调用技能时才加载完整内容并缓存
    3. 支持通过强制重扫刷新技能元数据
    4. LRU 缓存策略，自动清理不常用的技能正文
    """

    def __init__(self, cache_size: int = 50, scan_interval: int = 60):
        self._skill_registry: Optional[List[Dict[str, Any]]] = None
        self._cache_size = cache_size
        self._last_scan_time = 0.0
        self._scan_interval = scan_interval
        self._load_skill_content = lru_cache(maxsize=cache_size)(self._read_skill_content)

    @staticmethod
    def _read_skill_content(md_path: str, mtime: float) -> str:
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

    def _scan_skills(self, force_rescan: bool = False) -> List[Dict[str, Any]]:
        current_time = time.time()
        if (
            not force_rescan
            and self._skill_registry is not None
            and current_time - self._last_scan_time < self._scan_interval
        ):
            return self._skill_registry

        skills = []
        if not os.path.exists(SKILLS_DIR):
            self._skill_registry = []
            self._last_scan_time = current_time
            return []

        for item in os.listdir(SKILLS_DIR):
            folder_path = os.path.join(SKILLS_DIR, item)
            if not os.path.isdir(folder_path):
                continue

            md_path = os.path.join(folder_path, "SKILL.md")
            if not os.path.exists(md_path):
                md_path = os.path.join(folder_path, "README.md")
            if not os.path.exists(md_path):
                continue

            try:
                metadata = self._extract_metadata(md_path)
                if metadata:
                    skills.append(
                        {
                            "folder": item,
                            "md_path": md_path,
                            "mtime": os.path.getmtime(md_path),
                            **metadata,
                        }
                    )
            except Exception as e:
                print(f" [警告] 扫描技能 {item} 失败: {e}")

        self._skill_registry = skills
        self._last_scan_time = current_time
        if skills:
            print(f" [OK] 扫描到 {len(skills)} 个技能（懒加载模式）")
        return skills

    @staticmethod
    def _extract_metadata(md_path: str) -> Optional[Dict[str, str]]:
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                lines = []
                for index, line in enumerate(f):
                    if index >= 50:
                        break
                    lines.append(line)
            content = "".join(lines)

            name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
            desc_match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
            raw_name = name_match.group(1).strip() if name_match else os.path.basename(os.path.dirname(md_path))
            tool_name = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_name)

            raw_desc = desc_match.group(1).strip() if desc_match else f"提供 {raw_name} 相关功能"
            if (
                raw_desc.startswith('"')
                and raw_desc.endswith('"')
                or raw_desc.startswith("'")
                and raw_desc.endswith("'")
            ):
                raw_desc = raw_desc[1:-1]

            return {
                "raw_name": raw_name,
                "name": tool_name,
                "description": raw_desc,
            }
        except Exception as e:
            print(f" [警告] 提取元数据失败 {md_path}: {e}")
            return None

    def _create_lazy_tool(self, skill_info: Dict[str, Any]) -> StructuredTool:
        def lazy_runner(mode: str, command: str = "") -> str:
            if mode == "help":
                skill_content = self._load_skill_content(
                    skill_info["md_path"],
                    skill_info["mtime"],
                )
                return (
                    f"========== 【{skill_info['raw_name']} 完整说明书】 ==========\n"
                    f"{skill_content[:3000]}\n"
                    f"====================================\n"
                    f"提示：请根据以上说明，如果觉得能解决问题，就将 mode 设为 'run'，"
                    f"并将拼装好的执行命令填入 command 重新调用。"
                )
            if mode == "run":
                if not command:
                    return "错误：在 'run' 模式下，必须提供 command 参数！"
                actual_cmd = command.replace("{baseDir}", f"skills/{skill_info['folder']}")
                return execute_office_shell.invoke({"command": actual_cmd})
            return "错误：mode 参数只能是 'help' 或 'run'。"

        mini_description = (
            f"{skill_info['description']}\n\n"
            "注意：这是一个外部扩展技能。首次使用请务必先传入 `mode='help'` 来阅读完整说明书，"
            "之后再使用 `mode='run'` 配合 `command` 执行底层脚本。"
        )

        return StructuredTool.from_function(
            func=lazy_runner,
            name=skill_info["name"],
            description=mini_description,
            args_schema=DynamicSkillInput,
        )

    def get_all_tools(self, force_rescan: bool = False) -> List[StructuredTool]:
        return [self._create_lazy_tool(skill) for skill in self._scan_skills(force_rescan=force_rescan)]

    def get_tool_count(self) -> int:
        return len(self._scan_skills())

    def clear_cache(self) -> None:
        self._load_skill_content.cache_clear()
        self._skill_registry = None
        print(" [OK] 技能缓存已清除")


_lazy_loader = LazySkillLoader(cache_size=50)


def load_dynamic_skills(force_rescan: bool = False) -> List[StructuredTool]:
    return _lazy_loader.get_all_tools(force_rescan=force_rescan)


def reload_skills() -> List[StructuredTool]:
    _lazy_loader.clear_cache()
    return _lazy_loader.get_all_tools(force_rescan=True)


def get_skill_count() -> int:
    return _lazy_loader.get_tool_count()


def clear_skill_cache() -> None:
    _lazy_loader.clear_cache()
