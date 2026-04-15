# 智知因 - 基于大模型的多智能体个性化学习系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.0.35-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-red.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30.0-FF4B4B.svg)

**第十五届中国软件杯大赛 A组赛题作品**

基于大模型的多智能体个性化资源生成与学习系统

[English](./README_EN.md) | 中文

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

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Streamlit 前端                         │
│              (用户界面 / Markdown渲染 / SSE)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/SSE
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI 后端                          │
│     ┌─────────────┬──────────────┬────────────────────┐     │
│     │ Rate Limit  │ Request ID    │ Error Handler      │     │
│     └─────────────┴──────────────┴────────────────────┘     │
│     ┌───────────────────────────────────────────────────┐     │
│     │              AgentController (LangGraph)           │     │
│     │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐  │     │
│     │  │Diagnose │→│Generate │→│ Review  │→│Navigate│  │     │
│     │  │ Agent   │ │ Agent   │ │ Agent   │ │ Agent  │  │     │
│     │  └─────────┘ └─────────┘ └─────────┘ └────────┘  │     │
│     └───────────────────────────────────────────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │  SQLite  │    │ ChromaDB │    │   LLM    │
   │ (业务)   │    │ (向量)   │    │ (DeepSeek│
   └──────────┘    └──────────┘    │ /Qwen)   │
                                   └──────────┘
```

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
| 大模型 | DeepSeek/Qwen/Kimi | 支持多种LLM后端 |
| PDF处理 | pypdf | 教材解析 |

---

## 快速开始

### 环境要求

- Python 3.10+
- API密钥 (DeepSeek/通义千问/Kimi三选一)

### 方式一：本地开发

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/zhiyin.git
cd zhiyin

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置API密钥
cp .env.example .env
# 编辑.env填入你的API密钥

# 5. 初始化数据
python -m app.db

# 6. 启动API服务 (终端1)
uvicorn app.api.routes:app --reload --port 8000

# 7. 启动前端 (终端2)
streamlit run app/__init__.py --port 8501
```

### 方式二：Docker部署

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/zhiyin.git
cd zhiyin

# 2. 配置环境变量
cp .env.example .env
# 编辑.env填入你的API密钥

# 3. 一键启动
docker-compose up -d

# 访问服务
# 前端: http://localhost:8501
# API:  http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式三：Kubernetes部署

```bash
# 1. 配置Secret
kubectl create secret generic zhiyin-secrets \
  --from-literal=deepseek-api-key=YOUR_KEY

# 2. 应用部署
kubectl apply -f deploy/kubernetes/

# 3. 查看服务
kubectl get pods -l app=zhiyin
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

## API文档

启动服务后访问: http://localhost:8000/docs

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /health` | 健康检查 | 系统健康状态 |
| `GET /metrics` | 指标 | 请求量、延迟、系统资源 |
| `POST /api/v1/users/register` | 注册 | 创建新用户 |
| `POST /api/v1/users/login` | 登录 | 用户认证 |
| `POST /api/v1/study/start` | 开始学习 | 创建学习会话 |
| `POST /api/v1/study/generate` | 生成资源 | SSE流式生成讲义/练习 |
| `POST /api/v1/study/evaluate` | 评测答案 | AI自动评分 |
| `POST /api/v1/knowledge/upload` | 上传PDF | 添加教材到知识库 |
| `GET /api/v1/knowledge/search` | 搜索知识 | RAG向量检索 |

---

## Multi-Agent工作流程

```
┌──────────────────────────────────────────────────────────────┐
│                     LangGraph状态图                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐ │
│  │ Diagnose │───→│ Generate │───→│  Review  │───→│Navigate│ │
│  │  Agent   │    │  Agent   │    │  Agent   │    │ Agent │ │
│  └──────────┘    └──────────┘    └──────────┘    └───┬───┘ │
│       ↑              ↑              ↑                │      │
│       │              │              │                ▼      │
│       │              │              │    ┌────────────────┐ │
│       └──────────────┴──────────────┴────│  Decision Loop │ │
│                                          │ score<0.85?    │ │
│                                          └───────┬────────┘ │
│                                                  │          │
│                              ┌───────────────────┴───┐      │
│                              │                       │      │
│                              ▼                       ▼      │
│                      ┌──────────────┐          ┌─────────┐  │
│                      │   Continue   │          │ Complete│  │
│                      │  (regenerate)│          │         │  │
│                      └──────────────┘          └─────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 配置说明

### 环境变量 (.env)

```bash
# LLM配置 (必填)
DEEPSEEK_API_KEY=your_api_key     # DeepSeek API密钥
LLM_PROVIDER=deepseek             # 提供商: deepseek/qwen/kimi/openai

# 可选配置
QWEN_API_KEY=your_qwen_key
KIMI_API_KEY=your_kimi_key
DEBUG=false                        # 生产环境设为false
```

### Agent参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_MAX_RETRIES` | 3 | 最大重试次数 |
| `AGENT_REVIEW_THRESHOLD` | 0.85 | 审查通过阈值 |
| `RAG_TOP_K` | 5 | 检索返回数量 |
| `RAG_SCORE_THRESHOLD` | 0.7 | 向量相似度阈值 |

---

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行带覆盖率
pytest tests/ --cov=app --cov-report=html

# 运行特定测试类
pytest tests/test_agents.py::TestAgentWorkflow -v
```

---

## 演示账号

| 学号 | 姓名 |
|------|------|
| 2024001 | 张三 |
| 2024002 | 李四 |
| 2024003 | 王五 |

---

## 性能基准

| 指标 | 数值 |
|------|------|
| API响应时间(P50) | < 100ms |
| API响应时间(P99) | < 500ms |
| 并发用户支持 | 100+ |
| 知识库检索延迟 | < 50ms |

---

## 竞赛信息

- **赛题**: 第十五届中国软件杯大赛 A组 A3
- **题目**: 基于大模型的个性化资源生成与学习多智能体系统开发
- **团队**: IKUN

---

## License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

- [LangChain/LangGraph](https://github.com/langchain-ai/langgraph) - Agent编排框架
- [DeepSeek](https://platform.deepseek.com) - 大模型服务
- [通义千问](https://dashscope.console.aliyun.com) - 大模型服务
- [Streamlit](https://streamlit.io) - 前端框架
