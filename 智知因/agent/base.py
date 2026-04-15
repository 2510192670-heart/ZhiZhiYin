"""
智知因 - Agent 基类
定义所有 Agent 的通用接口和状态管理
"""
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger


class AgentState(BaseModel):
    """Agent 状态管理"""
    user_id: str
    session_id: str
    current_step: str = "init"
    diagnosis_result: Optional[Dict] = None
    generated_content: Optional[Dict] = None
    reflection_result: Optional[Dict] = None
    evaluation_result: Optional[Dict] = None
    student_profile: Optional[Dict] = None
    knowledge_gaps: List[str] = Field(default_factory=list)
    content_difficulty: str = "基础"
    reflection_rounds: int = 0
    max_reflection_rounds: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict:
        return self.model_dump()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class AgentResponse(BaseModel):
    """Agent 响应模型"""
    success: bool
    message: str
    data: Optional[Dict] = None
    state: Optional[AgentState] = None
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, name: str, llm_client: Any):
        self.name = name
        self.llm_client = llm_client
        self.logger = logger

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentResponse:
        """执行 Agent 逻辑"""
        pass

    def _format_prompt(self, template: str, **kwargs) -> str:
        """格式化提示模板"""
        return template.format(**kwargs)

    async def _call_llm(self, prompt: str, **kwargs) -> str:
        """调用 LLM"""
        try:
            response = await self.llm_client.agenerate([prompt])
            return response.generations[0][0].text
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise

    def _log(self, level: str, message: str):
        """日志记录"""
        getattr(self.logger, level)(f"[{self.name}] {message}")
