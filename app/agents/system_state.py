"""
智知因 - LangGraph多智能体系统 (生产级)
基于状态图的Multi-Agent协同架构，包含CoT、反思机制、完整的工作流编排
"""
import json
import re
import asyncio
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from loguru import logger

from app.agents.llm_client import llm_client
from app.agents.prompts import (
    DIAGNOSE_AGENT_PROMPT,
    GENERATOR_AGENT_PROMPT,
    REVIEW_AGENT_PROMPT,
    NAVIGATOR_AGENT_PROMPT,
    REFLECTION_AGENT_PROMPT,
    EVALUATION_AGENT_PROMPT
)
from app.agents.resilience import (
    execution_engine,
    RetryConfig,
    CircuitBreakerConfig,
    CircuitBreaker
)
from app.db.database import db_manager
from app.rag import rag_pipeline


class SystemState(TypedDict):
    """系统状态定义 - LangGraph状态图的核心数据结构"""
    user_id: str
    session_id: str
    student_profile: Dict
    current_topic: str
    knowledge_gaps: List[str]
    rag_context: str
    resources: Dict[str, str]
    review_feedback: str
    evaluation_score: float
    conversation_history: List[Dict]
    suggested_level: str
    current_phase: str
    error_message: Optional[str]
    execution_metadata: Dict


class BaseAgent:
    """Agent基类 - 包含通用功能"""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60
            )
        )
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            strategy="exponential"
        )

    def build_messages(self, state: SystemState, user_message: str = "") -> List[Dict]:
        """构建消息列表"""
        # 添加对话历史
        history_context = ""
        if state.get('conversation_history'):
            history_context = "\n\n## 对话历史\n"
            for msg in state['conversation_history'][-5:]:
                history_context += f"- {msg.get('role', 'user')}: {msg.get('content', '')[:200]}...\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""{user_message}

{history_context}

## 当前状态
- 用户ID: {state.get('user_id', '未知')}
- 会话ID: {state.get('session_id', '未知')}
- 当前课题: {state.get('current_topic', '未指定')}
- 当前阶段: {state.get('current_phase', '未知')}
- 学生档案: {json.dumps(state.get('student_profile', {}), ensure_ascii=False)}
- 知识缺口: {state.get('knowledge_gaps', [])}
- 建议难度: {state.get('suggested_level', '初级')}
- RAG上下文: {state.get('rag_context', '无RAG上下文')[:500] if state.get('rag_context') else '无'}
            """}
        ]
        return messages

    async def ainvoke(
        self,
        state: SystemState,
        user_message: str = "",
        use_cot: bool = True
    ) -> Dict:
        """异步调用Agent"""
        try:
            messages = self.build_messages(state, user_message)

            # 添加思维链提示
            if use_cot:
                messages[1]["content"] += "\n\n## 思维链要求\n请先展示你的思考过程(CoT)，再给出最终答案。"

            # 使用执行引擎（带重试和熔断）
            response = await execution_engine.execute_with_retry(
                lambda: self.llm.agenerate(messages),
                self.retry_config,
                self.name
            )

            return {
                "agent_name": self.name,
                "response": response,
                "success": True
            }

        except Exception as e:
            logger.error(f"{self.name} 调用失败: {e}")
            return {
                "agent_name": self.name,
                "response": "",
                "success": False,
                "error": str(e)
            }

    def invoke(self, state: SystemState, user_message: str = "", use_cot: bool = True) -> Dict:
        """同步调用Agent"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.ainvoke(state, user_message, use_cot))
        finally:
            loop.close()


class DiagnoseAgent(BaseAgent):
    """诊断Agent - 分析学生学习情况，识别知识缺口"""

    def __init__(self):
        super().__init__("DiagnoseAgent", DIAGNOSE_AGENT_PROMPT)

    async def ainvoke(self, state: SystemState) -> SystemState:
        """执行诊断"""
        topic = state.get('current_topic', '')
        profile = state.get('student_profile', {})

        user_message = f"""请分析学习者在学习"{topic}"时的知识缺口。

学生档案信息：
- 当前水平等级: {profile.get('level', 1)}
- 学习风格: {profile.get('learning_style', '文本')}
- 已掌握节点: {profile.get('mastered_nodes', [])}
- 薄弱环节: {profile.get('weaknesses', [])}"""

        result = await super().ainvoke(state, user_message)

        # 解析JSON响应
        try:
            response = result.get('response', '')
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                state['knowledge_gaps'] = data.get('knowledge_gaps', [])
                state['suggested_level'] = data.get('suggested_level', '初级')
                state['conversation_history'].append({
                    "role": "assistant",
                    "content": f"诊断完成: 识别到{len(state['knowledge_gaps'])}个知识缺口",
                    "agent": self.name
                })
                logger.info(f"诊断完成: {state['knowledge_gaps']}")
        except Exception as e:
            logger.error(f"诊断解析失败: {e}")
            state['knowledge_gaps'] = ["诊断解析失败，请重试"]

        state['execution_metadata'] = {
            **state.get('execution_metadata', {}),
            f"{self.name}_attempts": result.get('attempts', 1)
        }

        return state


class GeneratorAgent(BaseAgent):
    """资源生成Agent - 根据知识缺口生成个性化学习资源"""

    def __init__(self):
        super().__init__("GeneratorAgent", GENERATOR_AGENT_PROMPT)

    async def ainvoke(
        self,
        state: SystemState,
        resource_type: str = "lecture"
    ) -> SystemState:
        """生成学习资源"""
        topic = state.get('current_topic', '')
        difficulty = state.get('suggested_level', '初级')
        gaps = state.get('knowledge_gaps', [])
        profile = state.get('student_profile', {})
        rag_context = state.get('rag_context', '')

        user_message = f"""请为学生生成{resource_type}类型的学习资源。

## 课题信息
- 课题: {topic}
- 目标难度: {difficulty}
- 学习风格: {profile.get('learning_style', '文本')}

## 知识缺口 (必须覆盖)
{json.dumps(gaps, ensure_ascii=False)}

## RAG权威教材内容
{rag_context[:2000] if rag_context else '无RAG上下文'}

请生成对应的学习资源，确保：
1. 内容准确，与RAG权威教材一致
2. 覆盖所有识别出的知识缺口
3. 难度适合目标学生水平"""

        result = await super().ainvoke(state, user_message)

        if result.get('success'):
            content = result.get('response', '')

            # 提取JSON元数据（如果存在）
            try:
                json_match = re.search(r'\{\s*"resource_type"', content, re.DOTALL)
                if json_match:
                    end_match = re.search(r'\}[\s]*["\']?content["\']?[\s]*:',
                                         content[json_match.start():])
                    if end_match:
                        json_part = content[json_match.start():json_match.start() + end_match.end() + 500]
                        data = json.loads(json_part)
                        content = data.get('content', content)
            except:
                pass

            resources = state.get('resources', {})
            resources[resource_type] = content
            state['resources'] = resources

            state['conversation_history'].append({
                "role": "assistant",
                "content": f"生成{resource_type}类型资源，长度{len(content)}字符",
                "agent": self.name
            })

            logger.info(f"资源生成完成: {resource_type}, {len(content)}字符")
        else:
            state['error_message'] = f"资源生成失败: {result.get('error', '未知错误')}"

        return state


class ReviewAgent(BaseAgent):
    """审查Agent - 验证生成内容的准确性、难度、格式规范"""

    def __init__(self):
        super().__init__("ReviewAgent", REVIEW_AGENT_PROMPT)

    async def ainvoke(
        self,
        state: SystemState,
        resource_type: str = "lecture"
    ) -> SystemState:
        """审查资源"""
        resource_content = state.get('resources', {}).get(resource_type, '')
        rag_context = state.get('rag_context', '')
        target_level = state.get('suggested_level', '初级')
        gaps = state.get('knowledge_gaps', [])

        if not resource_content:
            state['error_message'] = f"没有找到{resource_type}类型资源可审查"
            return state

        user_message = f"""请审查以下{resource_type}类型的学习资源。

## 待审查内容
{resource_content[:3000]}

## 审查标准
- RAG权威参考: {rag_context[:1000] if rag_context else '无'}
- 目标难度: {target_level}
- 必须覆盖的知识缺口: {json.dumps(gaps, ensure_ascii=False)}

请进行严格审查并给出评分。"""

        result = await super().ainvoke(state, user_message)

        if result.get('success'):
            try:
                response = result.get('response', '')
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    state['evaluation_score'] = data.get('evaluation_score', 0.5)
                    state['review_feedback'] = data.get('review_notes', '')

                    if not data.get('is_approved', False):
                        state['review_feedback'] += "\n修改建议: " + \
                            "; ".join(data.get('revision_required', []))

                    logger.info(f"审查完成: 评分{state['evaluation_score']:.2f}")
            except Exception as e:
                logger.error(f"审查解析失败: {e}")
                state['evaluation_score'] = 0.5
                state['review_feedback'] = '审查解析失败'

        return state


class NavigatorAgent(BaseAgent):
    """路径规划Agent - 规划学习路径，决定工作流走向"""

    def __init__(self):
        super().__init__("NavigatorAgent", NAVIGATOR_AGENT_PROMPT)

    async def ainvoke(self, state: SystemState) -> SystemState:
        """决定下一步行动"""
        current_phase = state.get('current_phase', 'generate')
        evaluation_score = state.get('evaluation_score', 0)
        review_feedback = state.get('review_feedback', '')
        profile = state.get('student_profile', {})
        mastered = profile.get('mastered_nodes', [])
        topic = state.get('current_topic', '')

        user_message = f"""请决定下一步行动。

## 当前状态
- 当前阶段: {current_phase}
- 资源评分: {evaluation_score:.2f}
- 审查反馈: {review_feedback[:200] if review_feedback else '无'}
- 当前课题: {topic}
- 已掌握节点: {json.dumps(mastered, ensure_ascii=False)}

## 决策规则
1. 如果评分 >= 0.85: 资源合格，进入下一阶段
2. 如果评分 0.70-0.85: 需要微调，返回生成阶段
3. 如果评分 < 0.70: 需要重新生成

请做出决策。"""

        result = await super().ainvoke(state, user_message)

        next_phase = current_phase
        decision = "proceed"

        if result.get('success'):
            try:
                response = result.get('response', '')
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    decision = data.get('decision', 'proceed')
                    logger.info(f"导航决策: {decision}")
            except:
                pass

        # 根据决策更新阶段
        if decision == "proceed" or evaluation_score >= 0.85:
            if current_phase == "diagnose":
                next_phase = "generate"
            elif current_phase == "generate":
                next_phase = "review"
            elif current_phase == "review":
                next_phase = "evaluate"
            elif current_phase == "evaluate":
                next_phase = "complete"
            else:
                next_phase = "complete"
        elif decision in ["revise", "regenerate"]:
            # 返回生成阶段重新生成
            next_phase = "generate" if current_phase in ["generate", "review"] else current_phase
        else:
            next_phase = current_phase

        state['current_phase'] = next_phase
        logger.info(f"阶段转换: {current_phase} -> {next_phase}")

        return state


class ReflectionAgent(BaseAgent):
    """反思Agent - 引导学生深度反思"""

    def __init__(self):
        super().__init__("ReflectionAgent", REFLECTION_AGENT_PROMPT)

    async def ainvoke(self, state: SystemState, learning_result: str = "") -> SystemState:
        """执行反思"""
        topic = state.get('current_topic', '')
        evaluation_score = state.get('evaluation_score', 0)
        gaps = state.get('knowledge_gaps', [])
        history = state.get('conversation_history', [])

        user_message = f"""请引导学生进行深度反思。

## 学习情况
- 课题: {topic}
- 学习结果: {learning_result or '学习完成'}
- 评测得分: {evaluation_score:.0%}
- 知识缺口: {json.dumps(gaps, ensure_ascii=False)}

请提供反思指导和下一步建议。"""

        result = await super().ainvoke(state, user_message)

        if result.get('success'):
            state['conversation_history'].append({
                "role": "assistant",
                "content": f"反思指导: {result['response'][:300]}...",
                "agent": self.name
            })

        return state


class EvaluationAgent(BaseAgent):
    """评测Agent - 评估学生学习效果"""

    def __init__(self):
        super().__init__("EvaluationAgent", EVALUATION_AGENT_PROMPT)

    async def ainvoke(
        self,
        state: SystemState,
        student_answer: str,
        evaluation_mode: str = "auto"
    ) -> SystemState:
        """评测学生答案"""
        topic = state.get('current_topic', '')
        rag_context = state.get('rag_context', '')

        user_message = f"""请评测学生对"{topic}"相关问题的回答。

## 学生答案
{student_answer}

## 评测标准
RAG权威内容参考: {rag_context[:1000] if rag_context else '无'}

请给出评分和详细反馈。"""

        result = await super().ainvoke(state, user_message)

        if result.get('success'):
            try:
                response = result.get('response', '')
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    state['evaluation_score'] = data.get('score', 0.5)

                    # 更新学习记录
                    db_manager.add_learning_record(
                        user_id=state['user_id'],
                        topic=topic,
                        score=state['evaluation_score'],
                        knowledge_gaps=data.get('knowledge_gaps_detected', []),
                        resources_used=list(state.get('resources', {}).keys()),
                        session_id=state.get('session_id', '')
                    )

                    # 如果高分，更新掌握节点
                    if state['evaluation_score'] >= 0.85:
                        profile = db_manager.get_profile(state['user_id'])
                        if profile:
                            mastered = profile.get('mastered_nodes', [])
                            if topic not in mastered:
                                mastered.append(topic)
                                db_manager.update_profile(
                                    state['user_id'],
                                    mastered_nodes=mastered
                                )

                    logger.info(f"评测完成: 得分{state['evaluation_score']:.2f}")

            except Exception as e:
                logger.error(f"评测解析失败: {e}")

        return state


class AgentController:
    """Agent协调控制器 - 使用LangGraph编排多Agent工作流"""

    def __init__(self):
        self.diagnose_agent = DiagnoseAgent()
        self.generator_agent = GeneratorAgent()
        self.review_agent = ReviewAgent()
        self.navigator_agent = NavigatorAgent()
        self.reflection_agent = ReflectionAgent()
        self.evaluation_agent = EvaluationAgent()
        self._build_graph()

    def _build_graph(self):
        """构建LangGraph状态图"""
        workflow = StateGraph(SystemState)

        # 定义节点
        workflow.add_node("diagnose", self._wrap_diagnose)
        workflow.add_node("generate", self._wrap_generate)
        workflow.add_node("review", self._wrap_review)
        workflow.add_node("evaluate", self._wrap_evaluate)
        workflow.add_node("reflect", self._wrap_reflect)
        workflow.add_node("navigate", self._wrap_navigate)

        # 定义入口
        workflow.set_entry_point("diagnose")

        # 主流程边
        workflow.add_edge("diagnose", "generate")
        workflow.add_edge("generate", "review")
        workflow.add_edge("review", "navigate")

        # 条件边
        workflow.add_conditional_edges(
            "navigate",
            self._should_proceed,
            {
                "generate": "generate",      # 需要重新生成
                "evaluate": "evaluate",       # 审查通过，进入评测
                "reflect": "reflect",         # 需要反思
                "complete": END              # 完成
            }
        )

        # 评测后的反思
        workflow.add_edge("evaluate", "reflect")
        workflow.add_edge("reflect", END)

        self.graph = workflow.compile()

    def _should_proceed(self, state: SystemState) -> str:
        """判断是否继续"""
        phase = state.get('current_phase', 'generate')
        score = state.get('evaluation_score', 0)

        if phase == "complete":
            return "complete"

        if score >= 0.85 and phase in ["review", "evaluate"]:
            return "evaluate" if phase == "review" else "complete"

        if score < 0.70 and phase == "review":
            return "generate"

        if phase == "evaluate":
            return "complete"

        return "generate"

    async def _wrap_diagnose(self, state: SystemState) -> SystemState:
        """诊断节点包装"""
        state['current_phase'] = 'diagnose'
        return await self.diagnose_agent.ainvoke(state)

    async def _wrap_generate(self, state: SystemState) -> SystemState:
        """生成节点包装"""
        state['current_phase'] = 'generate'
        return await self.generator_agent.ainvoke(state, "lecture")

    async def _wrap_review(self, state: SystemState) -> SystemState:
        """审查节点包装"""
        state['current_phase'] = 'review'
        return await self.review_agent.ainvoke(state, "lecture")

    async def _wrap_navigate(self, state: SystemState) -> SystemState:
        """导航节点包装"""
        return await self.navigator_agent.ainvoke(state)

    async def _wrap_evaluate(self, state: SystemState) -> SystemState:
        """评测节点包装"""
        state['current_phase'] = 'evaluate'
        return state

    async def _wrap_reflect(self, state: SystemState) -> SystemState:
        """反思节点包装"""
        return await self.reflection_agent.ainvoke(state)

    async def arun_workflow(
        self,
        user_id: str,
        session_id: str,
        topic: str
    ) -> SystemState:
        """异步运行完整工作流"""
        # 初始化状态
        profile = db_manager.get_profile(user_id) or {}
        session = db_manager.get_session(session_id) or {}

        state: SystemState = {
            "user_id": user_id,
            "session_id": session_id,
            "student_profile": profile,
            "current_topic": topic,
            "knowledge_gaps": [],
            "rag_context": "",
            "resources": {},
            "review_feedback": "",
            "evaluation_score": 0.0,
            "conversation_history": [],
            "suggested_level": "初级",
            "current_phase": "diagnose",
            "error_message": None,
            "execution_metadata": {}
        }

        # 1. 执行诊断
        state = await self.diagnose_agent.ainvoke(state)

        # 2. RAG检索上下文
        try:
            rag_context = rag_pipeline.get_context_for_topic(
                topic=topic,
                knowledge_gaps=state.get('knowledge_gaps', []),
                course=None
            )
            state['rag_context'] = rag_context
        except Exception as e:
            logger.warning(f"RAG检索失败: {e}")
            state['rag_context'] = f"关于{topic}的核心知识要点"

        # 3. 执行生成-审查循环（最多3次）
        max_iterations = 3
        for i in range(max_iterations):
            state = await self.generator_agent.ainvoke(state, "lecture")
            state = await self.review_agent.ainvoke(state, "lecture")

            score = state.get('evaluation_score', 0)
            if score >= 0.85:
                logger.info(f"资源审查通过 (迭代{i+1})")
                break

            logger.info(f"迭代 {i+1}: 评分{score:.2f}，需要优化")

        state['current_phase'] = 'complete'

        # 4. 记录会话
        db_manager.update_session_state(session_id, {
            "knowledge_gaps": state.get('knowledge_gaps', []),
            "suggested_level": state.get('suggested_level', '初级'),
            "evaluation_score": state.get('evaluation_score', 0)
        })

        return state

    def run_workflow(
        self,
        user_id: str,
        session_id: str,
        topic: str
    ) -> SystemState:
        """同步运行完整工作流"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.arun_workflow(user_id, session_id, topic)
                    )
                    return future.result()
            else:
                return asyncio.run(self.arun_workflow(user_id, session_id, topic))
        except RuntimeError:
            return asyncio.run(self.arun_workflow(user_id, session_id, topic))


# 全局Agent控制器
agent_controller = AgentController()
