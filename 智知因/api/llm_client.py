"""
智知因 - LLM 客户端封装
支持 DeepSeek / 通义千问 / 讯飞星火 多模型切换
"""
from typing import Optional, Dict, Any
from loguru import logger
import os

from config import settings


class LLMClient:
    """LLM 客户端 - 统一接口"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化客户端"""
        if self.provider == "deepseek":
            self._init_deepseek()
        elif self.provider == "qwen":
            self._init_qwen()
        elif self.provider == "xunfei":
            self._init_xunfei()
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    def _init_deepseek(self):
        """初始化 DeepSeek 客户端"""
        try:
            from langchain_openai import ChatOpenAI

            self._client = ChatOpenAI(
                api_key=settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY"),
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
                temperature=0.7,
                streaming=True,
            )
            logger.info("DeepSeek LLM 客户端初始化成功")
        except Exception as e:
            logger.error(f"DeepSeek 客户端初始化失败: {e}")
            raise

    def _init_qwen(self):
        """初始化通义千问客户端"""
        try:
            from langchain_openai import ChatOpenAI

            self._client = ChatOpenAI(
                api_key=settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model=settings.DASHSCOPE_MODEL,
                temperature=0.7,
                streaming=True,
            )
            logger.info("通义千问 LLM 客户端初始化成功")
        except Exception as e:
            logger.error(f"通义千问客户端初始化失败: {e}")
            raise

    def _init_xunfei(self):
        """初始化讯飞星火客户端"""
        # 讯飞需要特殊的认证方式
        try:
            from langchain_community.chat_models import ChatSparkLLM

            self._client = ChatSparkLLM(
                app_id=settings.XUNFEI_APP_ID or os.getenv("XUNFEI_APP_ID"),
                api_key=settings.XUNFEI_API_KEY or os.getenv("XUNFEI_API_KEY"),
                api_secret=settings.XUNFEI_API_SECRET or os.getenv("XUNFEI_API_SECRET"),
                model=settings.XUNFEI_MODEL,
                temperature=0.7,
            )
            logger.info("讯飞星火 LLM 客户端初始化成功")
        except Exception as e:
            logger.error(f"讯飞星火客户端初始化失败: {e}")
            raise

    @property
    def client(self):
        """获取客户端实例"""
        return self._client

    async def agenerate(self, prompts: list) -> Any:
        """异步生成"""
        try:
            # LangChain 的异步调用
            from langchain_core.outputs import ChatGeneration

            # 使用同步调用的异步版本
            response = await self._client.agenerate(prompts)

            # 转换为标准格式
            return ChatResultWrapper(response)
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            raise

    def generate(self, prompt: str) -> str:
        """同步生成"""
        try:
            response = self._client.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            raise

    def get_model_name(self) -> str:
        """获取当前模型名称"""
        if self.provider == "deepseek":
            return settings.DEEPSEEK_MODEL
        elif self.provider == "qwen":
            return settings.DASHSCOPE_MODEL
        elif self.provider == "xunfei":
            return settings.XUNFEI_MODEL
        return "unknown"


class ChatResultWrapper:
    """Chat 结果包装器 - 统一不同模型的返回格式"""

    def __init__(self, response):
        self.response = response

    @property
    def generations(self):
        """返回 generations 列表"""
        return [[ChatGenerationWrapper(gen)] for gen in self.response.generations]


class ChatGenerationWrapper:
    """ChatGeneration 包装器"""

    def __init__(self, generation):
        self.generation = generation

    @property
    def text(self) -> str:
        """返回文本内容"""
        if hasattr(self.generation, "text"):
            return self.generation.text
        elif hasattr(self.generation, "message"):
            return self.generation.message.content
        elif hasattr(self.generation, "content"):
            return self.generation.content
        return str(self.generation)


# 全局 LLM 客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(provider)
    return _llm_client
