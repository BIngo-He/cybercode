"""
=====================================================================
context.py - Agent 状态定义与上下文管理
=====================================================================
主要功能：
1. 定义 AgentState 类型（TypedDict）
2. 实现上下文消息裁剪算法（trim_context_messages）
=====================================================================
"""

# ==================== 导入部分 ====================
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph.message import add_messages


# =====================================================================
# AgentState - Agent 状态类型定义
# =====================================================================
# LangGraph 使用 TypedDict 来定义状态的类型结构
# 两个字段：
#   - messages: 对话历史列表（带 add_messages 注解，自动合并新消息）
#   - summary: 上下文摘要（用于长对话压缩）
class AgentState(TypedDict):
    # 存储对话历史。
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 摘要压缩
    summary: str

# =====================================================================
# trim_context_messages() - 上下文消息裁剪函数
# =====================================================================
# 作用：防止对话上下文无限增长导致 token 溢出
# 原理：按"回合"（用户提问 + AI回答 + 工具调用）来裁剪
# 参数：
#   - messages: 完整消息列表
#   - trigger_turns: 触发裁剪的回合数（默认40轮）
#   - keep_turns: 裁剪后保留的最近回合数（默认10轮）
# 返回：(保留的消息列表, 丢弃的消息列表)
def trim_context_messages(messages: list[BaseMessage], trigger_turns: int = 40, keep_turns: int = 10) -> tuple[list[BaseMessage], list[BaseMessage]]:
    # 按照完整用户回合来裁剪上下文：即 一个会从从HumanMessage开始，直到下一个HumanMessage结束，会把AIMessage、tool_calls、ToolMessage一并保留
    first_system = next((m for m in messages if isinstance(m, SystemMessage)), None)
    non_system_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    if not non_system_msgs:
        return ([first_system] if first_system else []), []
    
    turns: list[list[BaseMessage]] = []
    current_turn: list[BaseMessage] = []

    # 遍历非系统信息，按回合进行分组
    for msg in non_system_msgs:
        if isinstance(msg, HumanMessage):
            if current_turn:
                turns.append(current_turn)
            current_turn = [msg]
        else:
            if current_turn:
                current_turn.append(msg)
    
    # 保存最后一个回合
    if current_turn:
        turns.append(current_turn)

    total_turns = len(turns)

    if total_turns < trigger_turns:
        final_messages = ([first_system] if first_system else []) + non_system_msgs
        return final_messages, []
    
    recent_turns = turns[-keep_turns:]
    discarded_turns = turns[:-keep_turns]

    final_messages: list[BaseMessage] = []
    if first_system:
        final_messages.append(first_system)
    for turn in recent_turns:
        final_messages.extend(turn)

    discarded_messages: list[BaseMessage] = []
    for turn in discarded_turns:
        discarded_messages.extend(turn)

    return final_messages, discarded_messages

    
