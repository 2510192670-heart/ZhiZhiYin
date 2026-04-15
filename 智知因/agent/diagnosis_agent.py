"""
智知因 - 诊断 Agent
分析学生学习记录，诊断知识缺口和学习难点
"""
from typing import Dict, List
from .base import BaseAgent, AgentState, AgentResponse


class DiagnosisAgent(BaseAgent):
    """诊断 Agent - 分析学生知识缺口"""

    DIAGNOSIS_PROMPT = """
# 角色：学习诊断专家

你是一个专业的学习诊断专家，负责分析学生的学习记录和历史数据，
准确识别学生的知识缺口和学习薄弱点。

## 诊断维度

1. **知识点掌握度**：基于答题记录分析各知识点的掌握情况
2. **薄弱环节**：识别错误率较高的知识点
3. **学习进度**：分析学习历史，判断学习节奏
4. **潜在风险**：预测可能遇到困难的内容

## 输入信息

学生画像：
{student_profile}

学习历史记录：
{learning_records}

教材章节信息：
{chapter_info}

## 输出要求

请生成一份详细的诊断报告，包括：

1. **知识缺口列表**：列出学生尚未掌握或掌握不牢的知识点
2. **薄弱原因分析**：分析每个薄弱点的形成原因
3. **学习优先级排序**：按重要程度和紧急程度排序
4. **建议学习路径**：基于诊断结果推荐学习顺序

请以 JSON 格式输出诊断结果：
```json
{{
    "knowledge_gaps": [
        {{
            "topic": "知识点名称",
            "gap_level": "完全未掌握/部分掌握/理解偏差",
            "priority": 1-5,
            "related_concepts": ["相关知识点"],
            "suggested_approach": "建议学习方式"
        }}
    ],
    "weak_points_analysis": "薄弱原因分析",
    "learning_path": ["学习顺序建议"],
    "estimated_time": "预计学习时长"
}}
```
"""

    def __init__(self, llm_client):
        super().__init__("DiagnosisAgent", llm_client)

    async def execute(self, state: AgentState) -> AgentResponse:
        """执行诊断逻辑"""
        self._log("info", f"开始诊断学生 {state.user_id} 的学习情况")

        try:
            # 构建诊断输入
            prompt = self._format_prompt(
                self.DIAGNOSIS_PROMPT,
                student_profile=json.dumps(state.student_profile, ensure_ascii=False),
                learning_records=json.dumps(state.metadata.get("learning_records", []), ensure_ascii=False),
                chapter_info=json.dumps(state.metadata.get("chapter_info", []), ensure_ascii=False),
            )

            # 调用 LLM 进行诊断
            result_text = await self._call_llm(prompt)

            # 解析诊断结果
            diagnosis_result = self._parse_diagnosis(result_text)

            # 更新状态
            state.update(
                current_step="diagnosis_completed",
                diagnosis_result=diagnosis_result,
                knowledge_gaps=[gap["topic"] for gap in diagnosis_result.get("knowledge_gaps", [])],
            )

            self._log("info", f"诊断完成，发现 {len(state.knowledge_gaps)} 个知识缺口")

            return AgentResponse(
                success=True,
                message="诊断完成",
                data=diagnosis_result,
                state=state,
            )

        except Exception as e:
            self._log("error", f"诊断失败: {e}")
            return AgentResponse(
                success=False,
                message="诊断失败",
                error=str(e),
                state=state,
            )

    def _parse_diagnosis(self, text: str) -> Dict:
        """解析诊断结果"""
        import re

        # 提取 JSON 部分
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group(1))

        # 如果没有 JSON 标记，尝试直接解析
        try:
            import json
            return json.loads(text)
        except:
            return {"raw_text": text}


# 需要添加 json 导入
import json
