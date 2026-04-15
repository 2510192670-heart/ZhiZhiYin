"""
智知因 - Agent 协调器
管理多 Agent 协作流程
"""
from typing import Dict, Optional
from loguru import logger

from .base import AgentState, AgentResponse
from .diagnosis_agent import DiagnosisAgent
from .generation_agent import GenerationAgent
from .reflection_agent import ReflectionAgent
from .evaluation_agent import EvaluationAgent
from config import settings


class AgentCoordinator:
    """多 Agent 协作协调器"""

    def __init__(self, llm_client, rag_retriever=None):
        self.logger = logger
        self.llm_client = llm_client

        # 初始化各 Agent
        self.diagnosis_agent = DiagnosisAgent(llm_client)
        self.generation_agent = GenerationAgent(llm_client, rag_retriever)
        self.reflection_agent = ReflectionAgent(llm_client)
        self.evaluation_agent = EvaluationAgent(llm_client)

        self.max_reflection_rounds = settings.MAX_REFLECTION_ROUNDS

    async def run_learning_pipeline(
        self,
        user_id: str,
        session_id: str,
        student_profile: Dict,
        knowledge_gaps: Optional[list] = None,
        difficulty: str = "基础",
        answers: Optional[list] = None,
    ) -> AgentState:
        """
        执行完整的学习流程管道

        流程: 诊断 → 生成 → 反思审核 → (评估) → 推荐
        """
        self.logger.info(f"开始学习流程 [用户: {user_id}, 会话: {session_id}]")

        # 初始化状态
        state = AgentState(
            user_id=user_id,
            session_id=session_id,
            student_profile=student_profile,
            knowledge_gaps=knowledge_gaps or [],
            content_difficulty=difficulty,
            max_reflection_rounds=self.max_reflection_rounds,
        )

        # Step 1: 诊断 (如果需要)
        if not knowledge_gaps:
            self.logger.info("Step 1: 执行诊断")
            diag_response = await self.diagnosis_agent.execute(state)
            if not diag_response.success:
                raise Exception(f"诊断失败: {diag_response.error}")
            state = diag_response.state

        # Step 2: 生成学习内容
        self.logger.info("Step 2: 生成学习内容")
        gen_response = await self.generation_agent.execute(state)
        if not gen_response.success:
            raise Exception(f"内容生成失败: {gen_response.error}")
        state = gen_response.state

        # Step 3: 反思审核循环
        self.logger.info("Step 3: 反思审核")
        reflection_passed = False
        while not reflection_passed and state.reflection_rounds < state.max_reflection_rounds:
            refl_response = await self.reflection_agent.execute(state)

            if refl_response.state.current_step == "reflection_passed":
                reflection_passed = True
                break
            elif refl_response.state.current_step == "needs_regeneration":
                self.logger.warning(f"需要重新生成内容 (第 {state.reflection_rounds} 轮)")
                # 重新生成
                gen_response = await self.generation_agent.execute(state)
                if not gen_response.success:
                    raise Exception(f"重新生成失败: {gen_response.error}")
                state = gen_response.state
            else:
                break

        if not reflection_passed and state.reflection_rounds >= state.max_reflection_rounds:
            self.logger.warning("达到最大反思轮次，继续流程")

        # Step 4: 评估 (如果有答题记录)
        if answers:
            self.logger.info("Step 4: 评估学习效果")
            eval_response = await self.evaluation_agent.execute(state, answers)
            if not eval_response.success:
                self.logger.warning(f"评估失败: {eval_response.error}")
            else:
                state = eval_response.state

        # Step 5: 生成推荐
        self.logger.info("Step 5: 生成学习推荐")
        state.update(current_step="completed")

        self.logger.info(f"学习流程完成 [用户: {user_id}]")
        return state

    async def diagnose_only(self, state: AgentState) -> AgentResponse:
        """仅执行诊断"""
        return await self.diagnosis_agent.execute(state)

    async def generate_only(self, state: AgentState) -> AgentResponse:
        """仅生成内容"""
        return await self.generation_agent.execute(state)

    async def reflect_only(self, state: AgentState) -> AgentResponse:
        """仅执行反思"""
        return await self.reflection_agent.execute(state)

    async def evaluate_only(self, state: AgentState, answers: list) -> AgentResponse:
        """仅执行评估"""
        return await self.evaluation_agent.execute(state, answers)
