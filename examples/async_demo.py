"""
async_demo.py - 演示 create_task vs await 的区别

这个文件展示了两种不同的协程启动方式的执行顺序。

运行方式：
    python examples/async_demo.py
"""

import asyncio
import time


# =============================================================================
# 模拟协程函数
# =============================================================================

async def agent_worker():
    """模拟 Agent 工作协程"""
    print("  [Agent] 开始工作，等待任务...")
    await asyncio.sleep(3)  # 模拟处理任务
    print("  [Agent] 任务处理完成")


async def pacemaker_loop():
    """模拟 心跳协程"""
    print("  [Heartbeat] 开始心跳检查")
    await asyncio.sleep(2)  # 模拟检查
    print("  [Heartbeat] 心跳检查完成")


async def user_input_loop():
    """模拟 用户输入协程"""
    print("  [Input] 等待用户输入...")
    await asyncio.sleep(5)  # 模拟用户打字
    print("  [Input] 用户输入完成: 'hello'")
    return "hello"


# =============================================================================
# 方式1: 全部 await（顺序执行）
# =============================================================================
async def method1_all_await():
    print("\n" + "="*50)
    print("方式1: 全部用 await（顺序执行）")
    print("="*50)
    
    start = time.time()
    
    await agent_worker()
    await pacemaker_loop()
    await user_input_loop()
    
    elapsed = time.time() - start
    print(f"\n总耗时: {elapsed:.2f}秒（顺序执行）")


# =============================================================================
# 方式2: create_task + await（并发执行）
# =============================================================================
async def method2_create_task():
    print("\n" + "="*50)
    print("方式2: create_task + await（并发执行）")
    print("="*50)
    
    start = time.time()
    
    # 启动后台协程（不阻塞，立即返回）
    worker = asyncio.create_task(agent_worker())
    heartbeat = asyncio.create_task(pacemaker_loop())
    
    # 等待用户输入（阻塞）
    result = await user_input_loop()
    
    # 等待后台任务完成
    await worker
    await heartbeat
    
    elapsed = time.time() - start
    print(f"\n总耗时: {elapsed:.2f}秒（并发执行）")


# =============================================================================
# 主函数
# =============================================================================
async def main():
    # 运行方式1
    await method1_all_await()
    
    # 运行方式2
    await method2_create_task()
    
    print("\n" + "="*50)
    print("对比总结：")
    print("  方式1: await + await + await = 顺序执行")
    print("  方式2: create_task + create_task + await = 并发执行")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())