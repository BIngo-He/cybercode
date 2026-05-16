"""
=====================================================================
provider.py - 多模型适配器工厂
=====================================================================
主要功能：
1. 统一接口创建不同提供商的 LLM 实例
2. 支持：OpenAI, 阿里云, Anthropic, Ollama, 腾讯混元等
3. 自动从环境变量读取 API Key 和 Base URL
4. 兼容 OpenAI API 格式的模型都能接入
=====================================================================
"""

# ==================== 导入部分 ====================
import os
from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from dotenv import load_dotenv
from pydantic import SecretStr

# 加载环境变量
load_dotenv()

# =====================================================================
# COMPATIBLE_BASE_URLS - 各提供商的默认 API 地址
# =====================================================================
# 当用户未配置 BASE_URL 时，使用这些默认地址
COMPATIBLE_BASE_URLS = {
    "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "z.ai": "https://open.bigmodel.cn/api/paas/v4",
    "tencent": "https://api.hunyuan.cloud.tencent.com/v1"
}


# =====================================================================
# get_provider() - 模型提供商工厂函数
# =====================================================================
# 参数：
#   - provider_name: 提供商名称（openai/aliyun/anthropic/ollama/tencent）
#   - model_name: 模型名称
#   - temperature: 温度参数（默认0.0）
#   - base_url: API 地址（可选，默认使用 COMPATIBLE_BASE_URLS）
#   - api_key: API Key（可选，默认从环境变量读取）
# 返回：LangChain ChatModel 实例
def get_provider(
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.0,
    base_url: Optional[str] = None,  # 允许外部传入
    api_key: Optional[str | None] = None,   # 允许外部传入
    **kwargs: Any
) -> BaseChatModel:
    """
    模型适配器工厂
    """
    provider_name = provider_name.lower()
    
    if provider_name in ["openai", "aliyun", "dashscope", "z.ai", "tencent", "other"]:
        from langchain_openai import ChatOpenAI
        
        current_api_key: str | None = api_key or os.environ.get("OPENAI_API_KEY", None)
          
        
        if not current_api_key:
            raise ValueError(f"未找到 API Key！请确保 .env 中配置了 OPENAI_API_KEY")
            
        final_base_url = base_url or os.environ.get("OPENAI_API_BASE")
        if not final_base_url:
            final_base_url = COMPATIBLE_BASE_URLS.get(provider_name) 

        return ChatOpenAI(
            model=model_name, 
            temperature=temperature,
            api_key=current_api_key, # type: ignore
            base_url=final_base_url,
            **kwargs
        )

    elif provider_name == "anthropic":
        from langchain_anthropic import ChatAnthropic
        
        current_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not current_api_key:
            raise ValueError("未找到 ANTHROPIC_API_KEY 环境变量！")
            
        final_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")

        return ChatAnthropic(
            model_name=model_name, 
            temperature=temperature, 
            anthropic_api_key=current_api_key, #type: ignore
            base_url=final_base_url,
            **kwargs
        )
        
    elif provider_name == "ollama":
        from langchain_ollama import ChatOllama 
        
        final_base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        
        return ChatOllama(
            model=model_name, 
            temperature=temperature, 
            base_url=final_base_url,
            **kwargs
        )
        
    else:
        raise ValueError(f"不支持的模型提供商: {provider_name}")

# 测试模型调用    
# LLM = get_provider(provider_name='aliyun', model_name='glm-5')
# res = LLM.invoke('你是谁')
# print(type(res))
# print(res)


