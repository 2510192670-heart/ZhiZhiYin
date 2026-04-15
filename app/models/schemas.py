"""
智知因 - 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class UserCreate(BaseModel):
    """用户注册"""
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    major: str = Field(default="计算机科学", description="专业")
    grade: str = Field(default="大一", description="年级")


class UserLogin(BaseModel):
    """用户登录"""
    student_id: str
    name: str


class StudentProfileUpdate(BaseModel):
    """学生档案更新"""
    level: Optional[int] = Field(None, ge=1, le=5, description="知识等级 1-5")
    learning_style: Optional[Literal["视觉", "文本", "实践"]] = None
    mastered_nodes: Optional[list] = []
    weaknesses: Optional[list] = []


class StudyStartRequest(BaseModel):
    """开始学习请求"""
    user_id: str
    topic: str


class ResourceGenerateRequest(BaseModel):
    """资源生成请求"""
    session_id: str
    mode: Literal["lecture", "practice", "mindmap", "quiz"] = "lecture"


class EvaluationSubmitRequest(BaseModel):
    """评测提交"""
    session_id: str
    student_answer: str


class StudySessionResponse(BaseModel):
    """学习会话响应"""
    session_id: str
    topic: str
    knowledge_gaps: list
    suggested_level: str
    message: str = ""


class GeneratedResource(BaseModel):
    """生成的学习资源"""
    type: str  # lecture, practice, mindmap, quiz
    content: str  # Markdown格式
    difficulty: str
    key_points: list
    review_notes: Optional[str] = None


class EvaluationResult(BaseModel):
    """评测结果"""
    is_correct: bool
    score: float
    feedback: str
    knowledge_gaps: list
    next_steps: str
