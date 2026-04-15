"""
智知因 - 生成 Agent
基于诊断结果，调用 RAG 知识库生成个性化学习内容
"""
from typing import Dict, List, Optional
from .base import BaseAgent, AgentState, AgentResponse


class GenerationAgent(BaseAgent):
    """生成 Agent - 生成个性化学习材料"""

    CONTENT_GENERATION_PROMPT = """
# 角色：个性化学习内容生成专家

你是一个专业的学习内容生成专家，根据学生的知识缺口和学习画像，
生成针对性的学习材料。

## 生成原则

1. **难度适配**：内容难度必须与学生当前水平匹配
2. **知识连贯**：确保内容逻辑清晰，循序渐进
3. **实用导向**：注重实际应用，避免纯理论堆砌
4. **RAG 增强**：优先使用知识库中的权威内容

## 学生画像

{student_profile}

## 知识缺口

{knowledge_gaps}

## 内容难度要求

{difficulty_requirement}

## 输出要求

请生成以下类型的学习材料：

### 1. 讲义内容
- 核心概念讲解
- 关键术语解释
- 原理说明
- 重点标注

### 2. 练习题目
- 选择题（检测概念理解）
- 判断题（检测辨析能力）
- 简答题（检测综合运用）
- 至少包含 5 道各类题目

### 3. 答案解析
- 每道题目的详细解析
- 易错点提醒
- 知识点关联

请以 JSON 格式输出：
```json
{{
    "lecture": {{
        "title": "讲义标题",
        "sections": [
            {{
                "heading": "章节标题",
                "content": "章节内容（Markdown格式）",
                "key_points": ["重点列表"]
            }}
        ]
    }},
    "exercises": [
        {{
            "type": "选择题/判断题/简答题",
            "question": "题目内容",
            "options": ["A选项", "B选项", "C选项", "D选项"],
            "answer": "正确答案",
            "explanation": "详细解析",
            "difficulty": "难度等级"
        }}
    ],
    "summary": "本节内容总结"
}}
```
"""

    def __init__(self, llm_client, rag_retriever=None):
        super().__init__("GenerationAgent", llm_client)
        self.rag_retriever = rag_retriever

    async def execute(self, state: AgentState) -> AgentResponse:
        """执行内容生成逻辑"""
        self._log("info", f"开始为学生 {state.user_id} 生成学习内容")

        try:
            # 获取 RAG 知识
            rag_context = await self._get_rag_context(state.knowledge_gaps)

            # 获取难度配置
            difficulty_req = self._get_difficulty_requirement(state.content_difficulty)

            # 构建生成提示
            prompt = self._format_prompt(
                self.CONTENT_GENERATION_PROMPT,
                student_profile=json.dumps(state.student_profile, ensure_ascii=False),
                knowledge_gaps=", ".join(state.knowledge_gaps),
                difficulty_requirement=json.dumps(difficulty_req, ensure_ascii=False),
            )

            # 调用 LLM 生成内容
            result_text = await self._call_llm(prompt)

            # 解析生成结果
            generated_content = self._parse_generation(result_text)

            # 添加 RAG 上下文引用
            generated_content["rag_references"] = rag_context

            # 更新状态
            state.update(
                current_step="generation_completed",
                generated_content=generated_content,
            )

            self._log("info", "内容生成完成")

            return AgentResponse(
                success=True,
                message="学习内容生成完成",
                data=generated_content,
                state=state,
            )

        except Exception as e:
            self._log("error", f"内容生成失败: {e}")
            return AgentResponse(
                success=False,
                message="内容生成失败",
                error=str(e),
                state=state,
            )

    async def _get_rag_context(self, topics: List[str]) -> List[Dict]:
        """从 RAG 知识库获取相关内容"""
        if not self.rag_retriever:
            return []

        context = []
        for topic in topics[:3]:  # 限制检索数量
            try:
                docs = await self.rag_retriever.similarity_search(topic, k=3)
                context.extend(docs)
            except Exception as e:
                self._log("warning", f"RAG 检索失败 [{topic}]: {e}")

        return context

    def _get_difficulty_requirement(self, difficulty: str) -> Dict:
        """获取难度配置"""
        from config import settings
        return settings.DIFFICULTY_CONTENT_MAP.get(difficulty, settings.DIFFICULTY_CONTENT_MAP["基础"])

    def _parse_generation(self, text: str) -> Dict:
        """解析生成结果"""
        import re
        import json

        # 提取 JSON 部分
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        try:
            return json.loads(text)
        except:
            return {"raw_text": text, "lecture": {}, "exercises": []}


import json
