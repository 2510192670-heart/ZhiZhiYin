"""
智知因 - 基于大模型的多智能体个性化学习系统
配置文件
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Literal

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """系统配置"""

    # 应用配置
    APP_NAME: str = "智知因 - 多智能体个性化学习系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    SQLITE_DB_PATH: Path = BASE_DIR / "data" / "zhiyin.db"
    CHROMA_DB_PATH: Path = BASE_DIR / "data" / "chroma_db"

    # LLM配置 - 支持多种大模型
    LLM_PROVIDER: Literal["deepseek", "qwen", "kimi", "openai", "minimax"] = "deepseek"

    # DeepSeek配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # 通义千问配置
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL: str = "qwen-max"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Kimi配置
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
    KIMI_MODEL: str = "moonshot-v1-128k"
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"

    # MiniMax配置
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_MODEL: str = "MiniMax-Text-01"
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"

    # OpenAI配置 (备选)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # 讯飞星火配置 (用于TTS/ASR等)
    XFYUN_APP_ID: str = os.getenv("XFYUN_APP_ID", "13614c79")
    XFYUN_API_KEY: str = os.getenv("XFYUN_API_KEY", "")
    XFYUN_API_SECRET: str = os.getenv("XFYUN_API_SECRET", "")

    # RAG配置
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.7

    # 学习难度等级
    DIFFICULTY_LEVELS: list = ["入门", "初级", "中级", "高级", "专家"]

    # 多Agent配置
    AGENT_MAX_RETRIES: int = 3
    AGENT_REVIEW_THRESHOLD: float = 0.8

    # 并发配置
    MAX_CONCURRENT_SESSIONS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# 确保数据目录存在
settings.SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
