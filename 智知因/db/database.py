"""
智知因 - SQLite 数据库管理模块
用户画像、学习记录等结构化数据存储
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from config import settings

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    profiles = relationship("StudentProfile", back_populates="user", cascade="all, delete-orphan")
    learning_records = relationship("LearningRecord", back_populates="user", cascade="all, delete-orphan")


class StudentProfile(Base):
    """学生画像表 - 存储学生能力评估和偏好"""
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 知识掌握情况 (JSON 格式存储)
    knowledge_status = Column(Text, default="{}")  # {"算法": {"掌握度": 0.8, "熟练度": "熟练"}}

    # 学习偏好
    preferred_difficulty = Column(String(20), default="基础")  # 基础/进阶/拓展
    preferred_style = Column(String(50), default="详细讲解")  # 详细讲解/简洁概括/实战导向

    # 能力评分
    overall_score = Column(Float, default=0.0)  # 0-100
    learning_speed = Column(Float, default=0.5)  # 0-1
    memory_retention = Column(Float, default=0.5)  # 0-1

    # 统计信息
    total_learning_time = Column(Integer, default=0)  # 分钟
    total_exercises = Column(Integer, default=0)
    correct_rate = Column(Float, default=0.0)  # 0-1

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="profiles")


class LearningRecord(Base):
    """学习记录表 - 存储每次学习活动的详情"""
    __tablename__ = "learning_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 学习内容
    topic = Column(String(200), nullable=False)  # 学习主题
    difficulty = Column(String(20), nullable=False)  # 难度等级

    # 生成的内容摘要
    content_type = Column(String(50))  # lecture/exercise/quiz
    content_summary = Column(Text)  # 内容摘要 JSON

    # 学习结果
    score = Column(Float, nullable=True)  # 评估得分 0-100
    feedback = Column(Text, nullable=True)  # AI 反馈

    # 元数据
    duration = Column(Integer, nullable=True)  # 学习时长(秒)
    agent_workflow = Column(Text)  # Agent 工作流记录 JSON

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User", back_populates="learning_records")


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url: Optional[str] = None):
        if db_url is None:
            db_url = settings.DATABASE_URL

        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    @contextmanager
    def get_db(self):
        """上下文管理器获取数据库会话"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db():
    """FastAPI 依赖注入"""
    yield next(db_manager.get_db())


def init_database():
    """初始化数据库"""
    db_manager.create_tables()
    print("✅ 数据库初始化完成")


# 辅助函数
def create_user(username: str, email: Optional[str] = None) -> User:
    """创建新用户"""
    with db_manager.get_db() as db:
        user = User(username=username, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

        # 同时创建默认学生画像
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()

        return user


def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    with db_manager.get_db() as db:
        return db.query(User).filter(User.username == username).first()


def update_student_profile(user_id: int, **kwargs) -> StudentProfile:
    """更新学生画像"""
    with db_manager.get_db() as db:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        if profile:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            db.commit()
            db.refresh(profile)
        return profile


def add_learning_record(user_id: int, topic: str, difficulty: str,
                        content_type: str = "lecture",
                        content_summary: str = None,
                        score: float = None,
                        feedback: str = None) -> LearningRecord:
    """添加学习记录"""
    with db_manager.get_db() as db:
        record = LearningRecord(
            user_id=user_id,
            topic=topic,
            difficulty=difficulty,
            content_type=content_type,
            content_summary=content_summary,
            score=score,
            feedback=feedback,
            completed_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
