"""
智知因 - 全局配置管理
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 应用基础配置
    APP_NAME: str = "智知因"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/zhizhiyin.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    # LLM 配置（支持多模型切换）
    LLM_PROVIDER: str = "deepseek"  # deepseek / qwen / xunfei

    # DeepSeek 配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 阿里通义千问配置
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_MODEL: str = "qwen-turbo"

    # 讯飞星火配置
    XUNFEI_APP_ID: Optional[str] = None
    XUNFEI_API_KEY: Optional[str] = None
    XUNFEI_API_SECRET: Optional[str] = None
    XUNFEI_MODEL: str = "general"

    # RAG 知识库配置
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Agent 配置
    MAX_REFLECTION_ROUNDS: int = 3
    REFLECTION_THRESHOLD: float = 0.8
    DIFFICULTY_LEVELS: list = ["基础", "进阶", "拓展"]

    # 学习难度与内容的映射关系
    DIFFICULTY_CONTENT_MAP: dict = {
        "基础": {
            "术语密度": "低",
            "例题占比": "60%",
            "概念解释": "详细",
            "适用对象": "初学者/零基础"
        },
        "进阶": {
            "术语密度": "中",
            "例题占比": "40%",
            "概念解释": "适中",
            "适用对象": "有一定基础的学习者"
        },
        "拓展": {
            "术语密度": "高",
            "例题占比": "20%",
            "概念解释": "精炼",
            "适用对象": "深入研究者/竞赛备考"
        }
    }

    # 文件路径配置
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"
    KB_DIR: Path = BASE_DIR / "knowledge_base"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

# 确保必要目录存在
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
settings.KB_DIR.mkdir(parents=True, exist_ok=True)
