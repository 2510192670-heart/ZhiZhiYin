# 智知因 - 基于大模型的多智能体个性化学习系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.0.35-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-red.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30.0-FF4B4B.svg)

**第十五届中国软件杯大赛 A组赛题作品**

基于大模型的多智能体个性化资源生成与学习系统

</div>

---

## 项目简介

智知因是一个基于大语言模型(LLM)和Multi-Agent架构的个性化学习平台。系统通过多个智能体的协同工作，为学习者提供量身定制的学习资源、练习题和知识图谱。

### 核心特性

- **Multi-Agent协作**：使用LangGraph实现DiagnoseAgent、GeneratorAgent、ReviewAgent、NavigatorAgent的智能协同
- **RAG增强**：基于ChromaDB的课程知识库，支持PDF教材向量化检索
- **CoT思维链**：内置Chain of Thought推理，提升Agent决策质量
- **流式输出**：SSE实时流式返回，良好用户体验
- **生产级架构**：限流、熔断、监控、重试等企业级特性

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit 1.30 | 数据科学友好Web框架 |
| 后端 | FastAPI 0.109 | 现代高效的Python Web框架 |
| 多智能体 | LangGraph 0.0.35 | 基于状态图的Agent编排 |
| 业务数据库 | SQLite | 轻量级关系数据库 |
| 向量数据库 | ChromaDB | AI原生向量存储 |
| Embedding | HuggingFace/Sentence-Transformers | 文本向量化 |
| 大模型 | MiniMax/DeepSeek/Qwen/Kimi | 支持多种LLM后端 |
| PDF处理 | pypdf | 教材解析 |

---

## 快速开始

### 环境要求

- Python 3.10+
- API密钥 (MiniMax/DeepSeek/通义千问/Kimi四选一)

### 方式一：本地开发

```bash
# 1. 克隆项目
git clone https://github.com/2510192670-heart/ZhiZhiYin.git
cd ZhiZhiYin

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置API密钥
cp .env.example .env
# 编辑.env填入你的API密钥

# 4. 启动服务
./start.sh  # Linux/Mac
# 或 start.bat  # Windows
```

### 方式二：Docker部署

```bash
# 1. 克隆项目
git clone https://github.com/2510192670-heart/ZhiZhiYin.git
cd ZhiZhiYin

# 2. 配置环境变量
cp .env.example .env
# 编辑.env填入你的API密钥

# 3. 一键启动
docker-compose up -d

# 访问服务
# 前端: http://localhost:8501
# API:  http://localhost:8003
# API文档: http://localhost:8003/docs
```

---

## 项目结构

```
智知因/
├── app/
│   ├── __init__.py          # Streamlit应用入口
│   ├── config.py             # 配置管理
│   ├── api/
│   │   ├── routes.py        # FastAPI路由
│   │   ├── middleware.py     # 中间件(限流/日志)
│   │   └── monitoring.py     # 监控指标
│   ├── agents/
│   │   ├── llm_client.py    # LLM客户端
│   │   ├── prompts.py        # 提示词模板
│   │   ├── system_state.py   # LangGraph状态图
│   │   └── resilience.py      # 重试/熔断器
│   ├── rag/
│   │   └── pipeline.py       # RAG处理流程
│   ├── db/
│   │   ├── database.py       # 数据库管理
│   │   └── __init__.py       # 数据初始化
│   └── models/
│       └── schemas.py         # Pydantic模型
├── tests/                    # 测试文件
├── deploy/
│   ├── kubernetes/           # K8s配置
│   └── nginx/               # Nginx配置
├── .github/workflows/        # CI/CD
├── data/                    # 数据存储
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 演示账号

| 学号 | 姓名 |
|------|------|
| 2024001 | 张三 |
| 2024002 | 李四 |
| 2024003 | 王五 |

---

## 竞赛信息

- **赛题**: 第十五届中国软件杯大赛 A组 A3
- **题目**: 基于大模型的个性化资源生成与学习多智能体系统开发

---

## License

MIT License - 详见 [LICENSE](LICENSE) 文件
