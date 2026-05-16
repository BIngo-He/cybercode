"""
=====================================================================
config.py - 项目配置与目录初始化
=====================================================================
主要功能：
1. 定义项目各目录路径
2. 自动创建必要的目录结构
3. 加载环境变量
=====================================================================
"""

# ==================== 导入部分 ====================
import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# =====================================================================
# 路径定义 - 基于项目结构计算各目录路径
# =====================================================================

# 当前文件目录：D:/vscode/xhs1_pc_claw/cybercode-main/cybercode/core/
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# 包目录：D:/vscode/xhs1_pc_claw/cybercode-main/cybercode/
PACKAGE_DIR = os.path.dirname(CORE_DIR)
# 项目根目录：D:/vscode/xhs1_pc_claw/cybercode-main/
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

# 工作区根目录（支持自定义，默认在项目根目录下）
# 可通过环境变量 CYBERCLAW_WORKSPACE 指定
WORKSPACE_DIR = os.getenv("CYBERCLAW_WORKSPACE", os.path.join(PROJECT_ROOT, "workspace"))


# =====================================================================
# 各子目录路径定义
# =====================================================================
# state.sqlite3 - 对话状态持久化（短期记忆）
DB_PATH = os.path.join(WORKSPACE_DIR, "state.sqlite3")
# memory/ - 用户长期画像（Markdown格式）
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
# personas/ - 系统人设 Prompt
PERSONAS_DIR = os.path.join(WORKSPACE_DIR, "personas")
# scripts/ - 自动化脚本
SCRIPTS_DIR = os.path.join(WORKSPACE_DIR, "scripts")
# office/ - 沙盒工位（唯一的文件操作空间）
OFFICE_DIR = os.path.join(WORKSPACE_DIR, "office")
# office/skills/ - 动态技能目录
SKILLS_DIR = os.path.join(OFFICE_DIR, "skills")
# tasks.json - 定时任务配置
TASKS_FILE = os.path.join(WORKSPACE_DIR, "tasks.json")

# =====================================================================
# 目录初始化 - 启动时自动创建所有必要目录
# =====================================================================
for d in [WORKSPACE_DIR, MEMORY_DIR, PERSONAS_DIR, SCRIPTS_DIR, OFFICE_DIR, SKILLS_DIR]:
    os.makedirs(d, exist_ok=True)

print(f"[Config] Workspace path ready: {WORKSPACE_DIR}")