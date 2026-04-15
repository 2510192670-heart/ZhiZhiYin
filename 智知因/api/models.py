"""
智知因 - Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 请求模型 ============

class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=2, max_length=50)
    subject: Optional[str] = None


class DiagnosisRequest(BaseModel):
    """诊断请求"""
    user_id: str
    topic: Optional[str] = None  # 指定诊断主题


class GenerateRequest(BaseModel):
    """生成内容请求"""
    user_id: str
    topic: str
    difficulty: str = "基础"
    knowledge_gaps: Optional[List[str]] = None


class AnswerSubmit(BaseModel):
    """提交答题答案"""
    session_id: str
    user_id: str
    answers: List[Dict[str, Any]]


class KnowledgeAdd(BaseModel):
    """添加知识请求"""
    source: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


# ============ 响应模型 ============

class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    created_at: str


class ProfileResponse(BaseModel):
    """学生画像响应"""
    user_id: str
    subject: Optional[str]
    knowledge_mastery: Dict[str, Any]
    overall_level: str
    learning_history: List[Dict]


class DiagnosisResponse(BaseModel):
    """诊断结果响应"""
    user_id: str
    knowledge_gaps: List[Dict]
    weak_points_analysis: str
    learning_path: List[str]
    estimated_time: str


class GenerateResponse(BaseModel):
    """内容生成响应"""
    session_id: str
    lecture: Dict
    exercises: List[Dict]
    summary: str


class EvaluationResponse(BaseModel):
    """评估结果响应"""
    performance_summary: Dict
    knowledge_mastery: List[Dict]
    next_steps: List[Dict]


# ============ WebSocket 消息模型 ============

class WSMessage(BaseModel):
    """WebSocket 消息"""
    type: str  # diagnosis, generation, evaluation, heartbeat
    data: Dict
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class WSResponse(BaseModel):
    """WebSocket 响应"""
    type: str
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
