"""
智知因 - 评估 Agent
评估学生学习效果，更新学生画像
"""
from typing import Dict, List, Optional
from datetime import datetime
from .base import BaseAgent, AgentState, AgentResponse


class EvaluationAgent(BaseAgent):
    """评估 Agent - 评估学习效果"""

    EVALUATION_PROMPT = """
# 角色：学习效果评估专家

你是一个专业的学习效果评估专家，负责：
1. 分析学生的答题表现
2. 评估学生对知识点的掌握程度
3. 生成个性化的学习建议

## 学生画像

{student_profile}

## 学习内容

{content_summary}

## 学生答题记录

{answers}

## 输出要求

```json
{{
    "performance_summary": {{
        "total_questions": 10,
        "correct": 8,
        "incorrect": 2,
        "accuracy_rate": 0.8
    }},
    "knowledge_mastery": [
        {{
            "topic": "知识点名称",
            "mastery_level": "掌握/基本掌握/未掌握",
            "correct_rate": 0-1,
            "improvement_suggestion": "提升建议"
        }}
    ],
    "strengths": ["学生做得好的方面"],
    "weaknesses": ["学生需要加强的方面"],
    "next_steps": [
        {{
            "action": "下一步行动",
            "priority": 1-5,
            "reason": "原因说明"
        }}
    ],
    "estimated_mastery_change": "+5%",
    "study_time_efficiency": "优秀/良好/一般/需改进"
}}
```
"""

    def __init__(self, llm_client):
        super().__init__("EvaluationAgent", llm_client)

    async def execute(self, state: AgentState, answers: Optional[List[Dict]] = None) -> AgentResponse:
        """执行评估逻辑"""
        self._log("info", f"开始评估学生 {state.user_id} 的学习效果")

        try:
            # 如果没有提供答题记录，生成模拟评估
            if not answers:
                answers = state.metadata.get("answers", [])

            # 构建评估提示
            prompt = self._format_prompt(
                self.EVALUATION_PROMPT,
                student_profile=json.dumps(state.student_profile, ensure_ascii=False),
                content_summary=json.dumps({
                    "lecture": state.generated_content.get("lecture", {}),
                    "exercise_count": len(state.generated_content.get("exercises", []))
                }, ensure_ascii=False),
                answers=json.dumps(answers, ensure_ascii=False),
            )

            # 调用 LLM 进行评估
            result_text = await self._call_llm(prompt)

            # 解析评估结果
            evaluation_result = self._parse_evaluation(result_text)

            # 更新学生画像
            updated_profile = self._update_profile(state, evaluation_result)

            # 更新状态
            state.update(
                current_step="evaluation_completed",
                evaluation_result=evaluation_result,
                student_profile=updated_profile,
            )

            self._log("info", f"评估完成，准确率: {evaluation_result.get('performance_summary', {}).get('accuracy_rate', 0) * 100:.0f}%")

            return AgentResponse(
                success=True,
                message="学习效果评估完成",
                data=evaluation_result,
                state=state,
            )

        except Exception as e:
            self._log("error", f"评估失败: {e}")
            return AgentResponse(
                success=False,
                message="评估失败",
                error=str(e),
                state=state,
            )

    def _parse_evaluation(self, text: str) -> Dict:
        """解析评估结果"""
        import re
        import json

        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        try:
            return json.loads(text)
        except:
            return {"raw_text": text}

    def _update_profile(self, state: AgentState, evaluation: Dict) -> Dict:
        """更新学生画像"""
        profile = state.student_profile.copy() if state.student_profile else {}

        # 初始化或更新知识掌握度
        if "knowledge_mastery" not in profile:
            profile["knowledge_mastery"] = {}

        mastery = evaluation.get("knowledge_mastery", [])
        for km in mastery:
            topic = km.get("topic")
            if topic:
                profile["knowledge_mastery"][topic] = {
                    "level": km.get("mastery_level", "未知"),
                    "correct_rate": km.get("correct_rate", 0),
                    "last_tested": datetime.now().isoformat(),
                }

        # 更新学习历史
        if "learning_history" not in profile:
            profile["learning_history"] = []

        profile["learning_history"].append({
            "timestamp": datetime.now().isoformat(),
            "session_id": state.session_id,
            "difficulty": state.content_difficulty,
            "topics_covered": state.knowledge_gaps,
            "performance": evaluation.get("performance_summary", {}),
        })

        # 计算整体水平
        profile["overall_level"] = self._calculate_level(evaluation)

        return profile

    def _calculate_level(self, evaluation: Dict) -> str:
        """根据表现计算学生水平"""
        accuracy = evaluation.get("performance_summary", {}).get("accuracy_rate", 0)

        if accuracy >= 0.9:
            return "优秀"
        elif accuracy >= 0.7:
            return "良好"
        elif accuracy >= 0.5:
            return "一般"
        else:
            return "需努力"


import json
