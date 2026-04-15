# 智知因 - 基于大模型的多智能体个性化学习系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![竞赛](https://img.shields.io/badge/竞赛-中国软件杯-A3赛题-orange.svg)

**基于大模型多智能体（Multi-Agent）技术的个性化辅助学习系统**

</div>

---

## 项目简介

"智知因"是一款基于大模型多智能体技术的个性化学习平台，通过对话诊断学习者知识盲区，结合权威教材（RAG技术）生成专属讲义、习题与学习报告。

### 核心功能

- 🎯 **智能诊断**：分析学习者知识缺口，识别前置知识掌握情况
- 📚 **个性化生成**：基于RAG技术生成匹配学习者能力的讲义与习题
- 🔄 **反思审核**：多Agent协作校验内容准确性，自动回滚重做
- 📊 **学习报告**：雷达图可视化知识掌握情况

### 核心技术

| 技术 | 用途 |
|------|------|
| LangGraph | 多Agent工作流编排 |
| FastAPI | RESTful API服务 |
| Streamlit | 前端交互界面 |
| SQLite + ChromaDB | 数据持久化与向量检索 |
| DeepSeek / 通义千问 | 大语言模型 |

## 系统架构

```
用户交互层 (Streamlit)
         ↓
┌────────────────────────────────────────────────┐
│         多Agent协作引擎 (LangGraph)              │
│  诊断Agent → 生成Agent → 反思审核Agent → 评估Agent │
└────────────────────────────────────────────────┘
         ↓
数据层 (SQLite + ChromaDB RAG)
```

## 团队成员

| 角色 | 姓名 | 职责 |
|------|------|------|
| 后端开发 | 徐颖 | 多智能体核心逻辑 |
| 前端开发 | 姚畅 | Streamlit界面 |
| 测试 | 廖宏伟 | 测试与文档 |

指导教师：满国晶

## 参赛信息

- **赛事**：第十五届"中国软件杯"大学生软件设计大赛
- **赛题**：A3 - 基于大模型的多智能体个性化学习系统
- **团队**：IKUN

## 文档

- 📄 [软件需求规格说明书](./docs/SRS.md)
- 📄 [概要设计说明书](./docs/概要设计说明书.md)
- 📄 [详细设计说明书](./docs/详细设计说明书.md)
- 📄 [测试计划与用例](./docs/测试计划与用例.md)
- 📄 [用户操作手册](./docs/用户操作手册.md)

## 快速开始

### 环境要求

- Python 3.10+
- API Key (DeepSeek / 通义千问)

### 安装

```bash
# 克隆仓库
git clone https://github.com/2510192670-heart/ZhiZhiYin.git
cd ZhiZhiYin

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动应用
streamlit run app.py
```

## License

MIT License
