"""
智知因 - 反思审核 Agent
自动校验生成内容的准确性、完整性和难度适配性
"""
from typing import Dict, List
from .base import BaseAgent, AgentState, AgentResponse


class ReflectionAgent(BaseAgent):
    """反思 Agent - 审核生成内容"""

    REFLECTION_PROMPT = """
# 角色：学习内容质量审核专家

你是一个严格的学习内容质量审核专家，负责检验生成内容的：
1. 准确性 - 知识点是否正确无误
2. 完整性 - 内容是否涵盖所有关键点
3. 难度适配性 - 难度是否与目标学生匹配
4. 术语一致性 - 专业术语是否规范准确

## 学生画像

{student_profile}

## 目标难度

{difficulty}

## 待审核内容

{generated_content}

## 审核维度与标准

### 准确性检查
- 核心概念定义是否正确
- 原理说明是否准确
- 术语使用是否规范

### 完整性检查
- 是否覆盖所有知识缺口
- 讲解是否循序渐进
- 练习是否有针对性

### 难度适配检查
- 内容深度是否适中
- 术语密度是否匹配
- 例子是否恰当

## 输出要求

请进行严格审核，返回以下结论之一：
- **通过**：内容质量合格，可以发布
- **需要修改**：存在小问题，需要调整
- **回滚重做**：存在严重问题，需要重新生成

```json
{{
    "verdict": "通过/需要修改/回滚重做",
    "scores": {{
        "accuracy": 0-100,
        "completeness": 0-100,
        "difficulty_match": 0-100,
        "overall": 0-100
    }},
    "issues": [
        {{
            "type": "准确性/完整性/难度适配",
            "severity": "严重/中等/轻微",
            "location": "问题位置",
            "description": "问题描述",
            "suggestion": "修改建议"
        }}
    ],
    "strengths": ["内容优点列表"],
    "summary": "审核总结"
}}
```
"""

    def __init__(self, llm_client):
        super().__init__("ReflectionAgent", llm_client)

    async def execute(self, state: AgentState) -> AgentResponse:
        """执行反思审核逻辑"""
        self._log("info", f"开始审核内容，反思轮次: {state.reflection_rounds + 1}/{state.max_reflection_rounds}")

        try:
            # 构建审核提示
            prompt = self._format_prompt(
                self.REFLECTION_PROMPT,
                student_profile=json.dumps(state.student_profile, ensure_ascii=False),
                difficulty=state.content_difficulty,
                generated_content=json.dumps(state.generated_content, ensure_ascii=False, indent=2),
            )

            # 调用 LLM 进行审核
            result_text = await self._call_llm(prompt)

            # 解析审核结果
            reflection_result = self._parse_reflection(result_text)

            # 更新反思轮次
            state.update(
                reflection_rounds=state.reflection_rounds + 1,
                reflection_result=reflection_result,
            )

            # 判断是否需要回滚
            verdict = reflection_result.get("verdict", "通过")

            if verdict == "回滚重做":
                self._log("warning", "内容审核不通过，需要重新生成")
                state.update(
                    current_step="needs_regeneration",
                    generated_content=None,  # 清空之前的内容
                )
            elif verdict == "需要修改":
                self._log("info", "内容需要小幅调整")
                state.update(current_step="needs_adjustment")
            else:
                self._log("info", "内容审核通过")
                state.update(current_step="reflection_passed")

            return AgentResponse(
                success=True,
                message=f"审核结果: {verdict}",
                data=reflection_result,
                state=state,
            )

        except Exception as e:
            self._log("error", f"审核失败: {e}")
            return AgentResponse(
                success=False,
                message="审核失败",
                error=str(e),
                state=state,
            )

    def _parse_reflection(self, text: str) -> Dict:
        """解析审核结果"""
        import re
        import json

        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        try:
            return json.loads(text)
        except:
            return {"raw_text": text, "verdict": "通过"}


import json
