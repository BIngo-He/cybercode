import os
import sys
import time
import asyncio
import random
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.styles import Style
from prompt_toolkit.application import get_app

from cybercode.core.agent import create_agent_app
from cybercode.core.config import DB_PATH
from cybercode.core.bus import task_queue
from cybercode.core.heartbeat import pacemaker_loop
from cybercode.core.commands import process_command, CommandRegistry, SlashCommandCompleter
from cybercode.core.theme import get_theme

def clear_screen():
    """ 清除屏幕  nt 是 windows NT 内核 
        os.system('cls') 是 windows 下的清除屏幕命令
        os.system('clear') 是 linux 下的清除屏幕命令
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def type_line(text: str, delay: float = 0.008):
    """ 打印文本时，每个字符之间有 delay 秒的间隔
    """
    for ch in text:
        print(ch, end='', flush=True)
        time.sleep(delay)
    print()

def print_banner():
    """
    打印欢迎 banner
    """
    clear_screen()

    theme = get_theme()
    CYAN = theme.ansi_info
    PURPLE = theme.ansi_primary
    SILVER = theme.ansi_muted
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    WHITE = '\033[37m'

    logo = f"""{CYAN}{BOLD}
        ██████╗██╗   ██╗██████╗ ███████╗██████╗      ██████╗ ██████╗ ██████╗ ███████╗
        ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
        ██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝    ██║     ██║   ██║██║  ██║█████╗  
        ██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗    ██║     ██║   ██║██║  ██║██╔══╝  
        ╚██████╗   ██║   ██████╔╝███████╗██║  ██║    ╚██████╗╚██████╔╝██████╔╝███████╗
        ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
        {RESET}                                                                       
        """

    sub_title = f"{WHITE}{BOLD} [*] Welcome to the {PURPLE}{BOLD}Cyber Code{RESET}{WHITE}{BOLD} !  {RESET}"

    quotes = [
        "It works on my machine.",
        "It compiles! Ship it.",
        "Git commit, push, pray.",
        "There's no place like 127.0.0.1.",
        "sudo make me a sandwich.",
        "Works fine in dev.",
        "May the source be with you.",
        "Ctrl+C, Ctrl+V, Deploy.",
        "Hello, World."
    ]
    quote = random.choice(quotes)
    meta = f" {SILVER}*{RESET} {CYAN}{quote}{RESET}"

    tip = (
        f"{PURPLE} * {RESET}"
        f"{SILVER}{PURPLE}{BOLD}Cyber Code{RESET} 已完成启动。输入命令开始，输入 {PURPLE}/exit{RESET}{SILVER} 退出。{RESET}\n"
    )

    print(logo)
    # type_line(logo, delay=0.04)
    print(sub_title)
    print() 
    time.sleep(0.12)
    # print(meta)
    type_line(meta, delay=0.008)

    print() 
    type_line(tip, delay=0.008)


def cprint(text="", end="\n"):
    
    print_formatted_text(ANSI(str(text)), end=end)


async def async_main():
    # 1. 打印启动 banner（ASCII 艺术字 logo）
    print_banner()
    
    # 2. 加载 .env 配置文件
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)
    
    # 3. 从环境变量读取模型配置（支持自定义 Provider 和 Model）
    current_provider = os.getenv("DEFAULT_PROVIDER", "aliyun")
    current_model = os.getenv("DEFAULT_MODEL", "glm-5")

    # 4. 创建 SQLite 记忆库（用于持久化对话状态，实现跨会话记忆）
    #    - DB_PATH = workspace/state.sqlite3
    #    - AsyncSqliteSaver 是 LangGraph 的检查点保存器
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:

        # 5. 创建 Agent 应用（LangGraph 工作流），并挂载 checkpointer
        #    - 每次对话会自动保存到 SQLite
        #    - 下次启动会自动恢复历史对话
        app = create_agent_app(provider_name=current_provider, model_name=current_model, checkpointer=memory)
        
        # 6. 定义会话配置（thread_id 决定对话线程的唯一性）
        #    - 相同 thread_id 会共享历史记录
        current_thread = os.getenv("CURRENT_THREAD_ID", "local_geek_master")
        config = {"configurable": {"thread_id": current_thread}}

        # ========== Spinner 状态类：控制底部动画 ==========
        class SpinnerState:
            action_words = [  # Agent思考时显示的随机提示词
                "Thinking...",              
                "Working...",               
                "Beep boop...",             
                "Eating bugs...",           
                "Charging battery...",      
                "Brewing coffee...",        
                "Blinking lights...",       
                "Polishing pixels...",      
                "Scanning matrix...",       
                "Warming up circuits...",   
                "Syncing data...",          
                "Pinging server..."         
            ]
            current_words = []    # 当前随机打乱后的提示词列表
            is_spinning = False   # 是否正在思考（显示动画）
            start_time = 0        # 思考开始时间（用于计算耗时）
            frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']  # 旋转动画帧
            is_tool_calling = False   # 是否正在调用工具
            tool_msg = ""             # 当前正在调用的工具名

        spinner = SpinnerState()


        # ========== 底部工具栏生成器：显示动画和状态 ==========
        def get_bottom_toolbar():
            if not spinner.is_spinning:
                return ANSI("") 
            
            elapsed = time.time() - spinner.start_time
            if spinner.is_tool_calling:
                display_msg = spinner.tool_msg
            else:
                idx_word = int(elapsed) % len(spinner.current_words)
                display_msg = f"* {spinner.current_words[idx_word]}"

            idx_frame = int(elapsed * 12) % len(spinner.frames)
            frame = spinner.frames[idx_frame]
            
            # 返回带颜色的状态栏文本
            live_theme = get_theme()
            return ANSI(
                f"  {live_theme.ansi_info}{frame}\033[0m "
                f"{live_theme.ansi_muted}{display_msg}\033[0m "
                f"{live_theme.ansi_accent}[{elapsed:.1f}s]\033[0m"
            )

        placeholder_text = ANSI("\033[3m\033[38;5;242minput...\033[0m")  # 占位符 "input..."

        # ========== Agent 工作协程：从队列获取任务并执行 ==========
        async def agent_worker():
            while True:
                # 7. 从任务队列获取用户输入（阻塞等待）
                user_input = await task_queue.get()  
                if user_input.lower() in ["/exit", "/quit"]:
                    task_queue.task_done()
                    break
                
                # 8. 准备状态：打乱提示词、记录开始时间
                spinner.current_words = spinner.action_words.copy()
                random.shuffle(spinner.current_words)
                
                spinner.start_time: int | float = time.time()
                spinner.is_spinning = True
                spinner.is_tool_calling = False
                
                # 9. 构建输入：只发送当前用户的新消息
                #    注意：历史消息由 checkpointer 自动注入，无需手动处理
                inputs = {"messages": [HumanMessage(content=user_input)]}
                try:
                    # 10. 流式执行 Agent 工作流
                    #     - app.astream() 会自动从 SQLite 读取历史并注入到状态
                    #     - config 参数指定 thread_id，用于关联历史记录
                    async for event in app.astream(inputs, config=config, stream_mode="updates"):
                        for node_name, node_data in event.items():
                            if node_name == "agent":
                                last_msg = node_data["messages"][-1]
                                
                                # 11. 如果 Agent 决定调用工具
                                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                    for tc in last_msg.tool_calls:
                                        spinner.is_tool_calling = True
                                        spinner.tool_msg = f"唤醒内置工具 : {tc['name']}..."
                                        cprint(f"  *{get_theme().ansi_info} Tool Call: \033[0m{tc['name']}")
                                        cprint('')
                                        
                                # 12. 如果 Agent 返回文本回答
                                elif last_msg.content:
                                    spinner.is_spinning = False
                                    
                                    lines = last_msg.content.strip().split('\n')
                                    if lines:
                                        live_theme = get_theme()
                                        formatted_out = f"  {live_theme.ansi_primary}>\033[0m {live_theme.ansi_text}{lines[0]}"
                                        for line in lines[1:]:
                                            formatted_out += f"\n    {line}"
                                        formatted_out += "\033[0m" 
                                        cprint(formatted_out)
                                    
                            elif node_name != "agent": 
                                spinner.is_tool_calling = False 
                                
                except Exception as e:
                    spinner.is_spinning = False
                    cprint(f"  \033[31m[ ⚠️ 引擎异常 : {e} ]\033[0m")

                spinner.is_spinning = False
                cprint()  # 空行
                task_queue.task_done()

        # ========== 用户输入协程：读取命令行输入并放入队列 ==========
        async def user_input_loop():
            custom_style = Style.from_dict({
                'bottom-toolbar': 'bg:default fg:default noreverse',
            })

            completer = SlashCommandCompleter(CommandRegistry.get_command_names())

            session = PromptSession(
                bottom_toolbar=get_bottom_toolbar,
                style=custom_style,
                erase_when_done=True,
                reserve_space_for_menu=0,
                completer=completer,
            )
            
            # 定时刷新任务栏动画
            async def redraw_timer():
                while True:
                    if spinner.is_spinning:
                        try:
                            get_app().invalidate()
                        except Exception:
                            pass
                    await asyncio.sleep(0.08)
                    
            redraw_task = asyncio.create_task(redraw_timer())
            
            while True:
                try:
                    prompt_message = ANSI(f"  {get_theme().ansi_info}>\033[0m ")
                    user_input = await session.prompt_async(prompt_message, placeholder=placeholder_text)

                    user_input = user_input.strip()
                    if not user_input:
                        continue

                    padded_bubble = f"  > {user_input}    "
                    cprint(f"\033[48;2;38;38;38m\033[38;5;255m{padded_bubble}\033[0m\n")

                    if user_input.startswith("/"):
                        cmd_result = process_command(user_input)
                        if cmd_result == "exit":
                            cprint(f"  {get_theme().ansi_primary}* 记忆已固化，Cyber Code 进入休眠。\033[0m")
                            await task_queue.put("/exit")
                            break 
                        if cmd_result:
                            cprint(f"{get_theme().ansi_primary}{cmd_result}\033[0m\n")
                        continue

                    await task_queue.put(user_input)
                    if user_input.lower() in ["/exit", "/quit"]:
                        cprint(f"  {get_theme().ansi_primary}* 记忆已固化，Cyber Code 进入休眠。\033[0m")
                        break
                        
                except (KeyboardInterrupt, EOFError):
                    cprint(f"\n  {get_theme().ansi_primary}* 强制中断，Cyber Code 进入休眠。\033[0m")
                    await task_queue.put("/exit")
                    break

            redraw_task.cancel() 

        # ========== 启动所有协程 ==========
        with patch_stdout():  # 上下文管理器，解决 多协程输出冲突问题，让界面不会打印乱
            # 15. 启动三个并发任务
            worker = asyncio.create_task(agent_worker())              # Agent 工作协程  等待task队列中 input 的输入
            heartbeat_worker = asyncio.create_task(pacemaker_loop(check_interval=10))  # 心跳任务（定时任务）  
            await user_input_loop()   # 用户输入协程（主协程，会阻塞直到退出）
            
            # 16. 等待任务队列处理完毕  阻塞 直到队列为空 然后进入下面的代码
            await task_queue.join()  
            
            # 17. 取消所有后台任务
            worker.cancel()
            heartbeat_worker.cancel()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
