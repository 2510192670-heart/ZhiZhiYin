"""
智知因 - LLM客户端
支持多种大模型：DeepSeek、通义千问、Kimi、OpenAI
"""
import os
from typing import Optional, List, Dict, Any
from loguru import logger

from app.config import settings


class LLMClient:
    """大模型客户端"""

    def __init__(self, provider: str = None):
        self.provider = provider or settings.LLM_PROVIDER
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化客户端"""
        if self.provider == "deepseek":
            self._init_deepseek()
        elif self.provider == "qwen":
            self._init_qwen()
        elif self.provider == "kimi":
            self._init_kimi()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "minimax":
            self._init_minimax()
        else:
            logger.warning(f"未配置的大模型提供商: {self.provider}, 使用DeepSeek作为默认")
            self._init_deepseek()

    def _init_deepseek(self):
        """初始化DeepSeek客户端"""
        try:
            from langchain_deepseek import ChatDeepSeek
            self._client = ChatDeepSeek(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.7,
                streaming=True
            )
            logger.info("DeepSeek客户端初始化成功")
        except ImportError:
            logger.error("请安装 langchain-deepseek: pip install langchain-deepseek")
            self._client = None

    def _init_qwen(self):
        """初始化通义千问客户端"""
        try:
            from langchain_openai import ChatOpenAI
            self._client = ChatOpenAI(
                model=settings.QWEN_MODEL,
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
                temperature=0.7,
                streaming=True
            )
            logger.info("通义千问客户端初始化成功")
        except ImportError:
            logger.error("请安装 langchain-openai: pip install langchain-openai")
            self._client = None

    def _init_kimi(self):
        """初始化Kimi客户端"""
        try:
            from langchain_openai import ChatOpenAI
            self._client = ChatOpenAI(
                model=settings.KIMI_MODEL,
                api_key=settings.KIMI_API_KEY,
                base_url=settings.KIMI_BASE_URL,
                temperature=0.7,
                streaming=True
            )
            logger.info("Kimi客户端初始化成功")
        except ImportError:
            logger.error("Kimi客户端初始化失败")
            self._client = None

    def _init_openai(self):
        """初始化OpenAI客户端"""
        try:
            from langchain_openai import ChatOpenAI
            self._client = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                streaming=True
            )
            logger.info("OpenAI客户端初始化成功")
        except ImportError:
            logger.error("OpenAI客户端初始化失败")
            self._client = None

    def _init_minimax(self):
        """初始化MiniMax客户端"""
        try:
            from langchain_openai import ChatOpenAI
            self._client = ChatOpenAI(
                model=settings.MINIMAX_MODEL,
                api_key=settings.MINIMAX_API_KEY,
                base_url=settings.MINIMAX_BASE_URL,
                temperature=0.7,
                streaming=True
            )
            logger.info("MiniMax客户端初始化成功")
        except ImportError:
            logger.error("请安装 langchain-openai: pip install langchain-openai")
            self._client = None
        except Exception as e:
            logger.error(f"MiniMax客户端初始化失败: {e}")
            self._client = None

    def generate(self, messages: List[Dict], **kwargs) -> str:
        """生成回复"""
        if not self._client:
            return "大模型客户端未初始化，请检查API配置"

        try:
            response = self._client.invoke(messages, **kwargs)
            return response.content
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return f"生成失败: {str(e)}"

    async def agenerate(self, messages: List[Dict], **kwargs) -> str:
        """异步生成回复"""
        if not self._client:
            return "大模型客户端未初始化，请检查API配置"

        try:
            from langchain_core.messages import HumanMessage, AIMessage
            langchain_messages = []
            for msg in messages:
                if msg['role'] == 'user':
                    langchain_messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    langchain_messages.append(AIMessage(content=msg['content']))

            response = await self._client.ainvoke(langchain_messages, **kwargs)
            return response.content
        except Exception as e:
            logger.error(f"异步生成失败: {e}")
            return f"生成失败: {str(e)}"

    def get_model_name(self) -> str:
        """获取当前模型名称"""
        if self.provider == "deepseek":
            return settings.DEEPSEEK_MODEL
        elif self.provider == "qwen":
            return settings.QWEN_MODEL
        elif self.provider == "kimi":
            return settings.KIMI_MODEL
        elif self.provider == "openai":
            return settings.OPENAI_MODEL
        elif self.provider == "minimax":
            return settings.MINIMAX_MODEL
        return "unknown"


# 全局LLM客户端
llm_client = LLMClient()
