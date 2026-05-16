import os
import typer
import questionary
import logging
import sys
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from dotenv import set_key, load_dotenv, unset_key

# os.path.dirname 表示获取当前文件的目录路径
ENTRY_DIR = os.path.dirname(os.path.abspath(__file__)) # entry目录
PROJECT_ROOT = os.path.dirname(ENTRY_DIR) # 项目根目录

os.chdir(PROJECT_ROOT) # 切换到项目根目录cyberclaw-main

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cybercode.core.provider import get_provider
from cybercode.core.theme import get_theme
from langchain_core.messages import HumanMessage

app = typer.Typer(help="Cyber Code - 极客专属的赛博智能终端")
console = Console()
theme = get_theme()

cyber_style = questionary.Style([
    ('qmark', f'fg:{theme.primary} bold'),
    ('question', f'fg:{theme.info} bold'),
    ('answer', f'fg:{theme.primary} bold'),
    ('pointer', f'fg:{theme.info} bold'),
    ('highlighted', f'fg:{theme.info} bold'),
    ('selected', f'fg:{theme.info}'),
    ('instruction', f'fg:{theme.muted} dim'),
])


# config env配置：
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

@app.command("config")
def config_wizard():
    console.clear()
    console.print(Panel(
        f"👾 Welcome to [bold {theme.primary}]Cyber Code[/bold {theme.primary}]...\n\n☁️[dim] 请完成模型配置，我们将把密钥安全固化在本地。[/dim]",
        title="[bold white]✦  Cyber Code Config[/bold white]", 
        border_style=theme.primary
    ))
    provider_raw = questionary.select(
        "选择你的模型提供商 (Provider):",
        choices=["openai", "anthropic", "aliyun (openai compatible)","tencent (openai compatible)", "z.ai (openai compatible)", "other (openai compatible)", "ollama"],
        style=cyber_style,
        instruction="(按上下键选择，回车确认)"
    ).ask() # 让用户选择模型提供商

    if not provider_raw:
        console.print(f"[dim {theme.primary}]✦   录入中断，Cyber Code 配置已取消。[/dim {theme.primary}]")
        return

    provider = provider_raw.split(" ")[0].strip()
    is_openai_compatible = "openai" in provider_raw.lower()

    model_name = questionary.text(
        "输入指定的模型型号 (如 gpt-4o-mini, qwen-max, glm-4 等):",
        style=cyber_style
    ).ask() # 让用户输入模型型号 ask是交互式输入

    if model_name is None:
        console.print(f"[dim {theme.primary}]✦   录入中断，Cyber Code 配置已取消。[/dim {theme.primary}]")
        return

    api_key = ""
    env_key = ""
    if provider != "ollama":
        if is_openai_compatible:
            env_key = "OPENAI_API_KEY"
        elif provider == "anthropic":
            env_key = "ANTHROPIC_API_KEY"

        api_key = questionary.password(
            f"输入你的 {env_key} (对应 {provider_raw}):",
            style=cyber_style
        ).ask()

        if api_key is None:
            console.print(f"[dim {theme.primary}]✦   录入中断，Cyber Code 配置已取消。[/dim {theme.primary}]")
            return

    base_url = ""
    if provider in ["openai", "anthropic"]:
        base_url = questionary.text(
            f"输入 {provider} 代理 Base URL (直连请直接回车跳过):",
            style=cyber_style
        ).ask()
    elif provider == "ollama":
        base_url = questionary.text(
            "输入 Ollama Base URL (默认 http://localhost:11434，直接回车跳过):",
            style=cyber_style
        ).ask()
    else:
        base_url = questionary.text(
            "输入兼容 Base URL (不填直接回车将使用官方默认地址):",
            style=cyber_style
        ).ask()

    if base_url is None:
        console.print(f"[dim {theme.primary}]✦   录入中断，Cyber Code 配置已取消。[/dim {theme.primary}]")
        return

    console.print("\n[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]")

    with Status(f"[bold {theme.primary}]正在连接 {provider.upper()} 引擎并发送探测包...[/bold {theme.primary}]", spinner="dots", spinner_style=theme.info):
        try:
            if env_key and api_key:
                os.environ[env_key] = api_key
            if base_url:
                if is_openai_compatible:
                    os.environ["OPENAI_API_BASE"] = base_url
                else:
                    os.environ[f"{provider.upper()}_BASE_URL"] = base_url

            llm = get_provider(provider_name=provider, model_name=model_name)
            response = llm.invoke([HumanMessage(content="回复我'收到'。")])

            console.print(f" [bold {theme.success}][ 配置成功!][/bold {theme.success}]")
            
        except Exception as e:

            console.print(f" [bold {theme.error}][ 配置失败!][/bold {theme.error}]  无法连接到模型，请检查 Key、Base URL、模型型号 或 网络！\n[dim]错误信息: {str(e)}[/dim]")
            return


    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, 'w').close()

    logging.getLogger("dotenv.main").setLevel(logging.ERROR)

    unset_key(ENV_PATH, "OPENAI_API_BASE")
    unset_key(ENV_PATH, "ANTHROPIC_BASE_URL")
    unset_key(ENV_PATH, "OLLAMA_BASE_URL")

    if env_key and api_key:
        set_key(ENV_PATH, env_key, api_key)
        
    if base_url:
        if is_openai_compatible:
            set_key(ENV_PATH, "OPENAI_API_BASE", base_url)
        else:
            set_key(ENV_PATH, f"{provider.upper()}_BASE_URL", base_url)
    
    set_key(ENV_PATH, "DEFAULT_PROVIDER", provider)
    set_key(ENV_PATH, "DEFAULT_MODEL", model_name)

    console.print(Panel(
        f"配置已保存至 [{theme.primary}]{ENV_PATH}[/{theme.primary}]\n"
        f"当前默认提供商: [{theme.primary}]{provider}[/{theme.primary}] | 模型: [{theme.primary}]{model_name}[/{theme.primary}]\n\n"
        f"👉 输入 [bold {theme.info}]cybercode run[/bold {theme.info}] 即可启动系统！",
        border_style=theme.info
    ))

# cybercode run 启动时检查配置是否完整
def _show_boot_error():
    console.print(Panel(
        f"[bold {theme.info}]Cyber Code未完成配置![/bold {theme.info}]\n\n"
        f"[{theme.primary}]检测到 API Key、模型或Baseurl。请重新执行以下命令完成配置：[/{theme.primary}]\n"
        f"[bold {theme.info}]cybercode config[/bold {theme.info}]",
        title=f"[bold {theme.primary}]⚠️ Boot Sequence Failed[/bold {theme.primary}]",
        border_style=theme.primary
    ))


@app.command("run")
def run_agent():
    load_dotenv(ENV_PATH)
    provider = os.getenv("DEFAULT_PROVIDER")
    model = os.getenv("DEFAULT_MODEL")
    if not provider or not model:
        _show_boot_error()
        raise typer.Exit()
    if provider != "ollama":
        if provider in ["openai", "aliyun", "z.ai", "tencent", "other"]: 
            if not os.getenv("OPENAI_API_KEY"):
                _show_boot_error()
                raise typer.Exit()
                
        elif provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                _show_boot_error()
                raise typer.Exit()
        
    import entry.main as cyberclaw_main
    cyberclaw_main.main()

@app.command("monitor")
def run_monitor():    
        
    try:
        import entry.monitor as cyberclaw_monitor
        cyberclaw_monitor.main()
    except ImportError as e:
        console.print(f"[bold red]启动失败：找不到监视器模块！[/bold red]\n[dim]请确保 monitor.py 和 cli.py 在同一目录下。\n报错信息: {e}[/dim]")

def main():
    app()

if __name__ == "__main__":
    main()
