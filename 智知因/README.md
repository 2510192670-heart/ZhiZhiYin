# 智知因 - 基于大模型的多智能体个性化学习系统

> 🎓 基于大模型的多 Agent 协作 + RAG 知识库的个性化学习平台

## 📖 项目简介

智知因是一款智能个性化学习系统，通过多 Agent 协作框架，为每个学生提供精准诊断、个性化学材生成和自适应评估的闭环学习体验。

### 核心特性

- 🔬 **多 Agent 协作** - 诊断→生成→反思→评估的完整闭环
- 📚 **RAG 知识库** - 支持教材 PDF 挂载，确保内容权威准确
- 🎯 **难度自适应** - 基于学生画像动态调整内容深浅
- 🛡️ **质量保障** - 自动校验生成内容，触发回滚重做机制

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户界面层                        │
│              (Streamlit Web 界面)                    │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                    API 网关                          │
│                 (FastAPI 接口)                      │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                 多 Agent 协作层                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐ │
│  │诊断 Agent │→│生成 Agent │→│反思 Agent │→│评估 │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────┘ │
└─────────────────────────────────────────────────────┘
                         ↓
┌────────────────────┐       ┌────────────────────┐
│     SQLite         │       │     ChromaDB       │
│   (用户画像)        │       │    (RAG 知识库)     │
└────────────────────┘       └────────────────────┘
```

## 🚀 快速开始

### 方式一：一键部署（推荐）

**Windows 用户：**
```bash
.\deploy.bat
```

**Linux/Mac 用户：**
```bash
chmod +x deploy.sh
./deploy.sh
```

### 方式二：手动部署

#### 1. 克隆项目
```bash
git clone https://github.com/2510192670-heart/ZhiZhiYin.git
cd ZhiZhiYin
```

#### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

#### 5. 启动服务

**仅后端 API：**
```bash
uvicorn api.routes:app --reload --port 8000
```

**仅前端界面：**
```bash
streamlit run streamlit_app.py --server.port 8501
```

**同时启动：**
```bash
# 终端1
uvicorn api.routes:app --reload --port 8000

# 终端2
streamlit run streamlit_app.py --server.port 8501
```

### 方式三：Docker 部署

```bash
# 设置环境变量
export DEEPSEEK_API_KEY=your_api_key

# 构建并启动
docker-compose up -d --build
```

## 📚 访问地址

| 服务 | 地址 |
|------|------|
| API 文档 | http://localhost:8000/docs |
| 前端界面 | http://localhost:8501 |
| WebSocket | ws://localhost:8000/ws/{client_id} |

## 🧪 开发指南

### 项目结构
```
智知因/
├── agent/                 # Agent 核心模块
│   ├── __init__.py
│   ├── base.py           # Agent 基类
│   ├── diagnosis_agent.py # 诊断 Agent
│   ├── generation_agent.py# 生成 Agent
│   ├── reflection_agent.py# 反思 Agent
│   ├── evaluation_agent.py# 评估 Agent
│   └── coordinator.py    # Agent 协调器
├── api/                   # FastAPI 接口
│   ├── __init__.py
│   ├── routes.py         # API 路由
│   ├── models.py         # 数据模型
│   └── llm_client.py     # LLM 客户端
├── db/                    # 数据库层
│   ├── __init__.py
│   ├── database.py       # SQLite 管理
│   └── vector_store.py   # ChromaDB 管理
├── knowledge_base/        # 知识库（存放教材 PDF）
├── data/                  # 数据存储
├── logs/                  # 日志目录
├── config.py              # 配置文件
├── streamlit_app.py       # 前端界面
├── requirements.txt       # 依赖清单
├── Dockerfile             # Docker 容器化
├── docker-compose.yml     # Docker 编排
└── deploy.sh / deploy.bat # 一键部署脚本
```

### API 接口

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/users` | 创建用户 |
| GET | `/api/users/{user_id}/profile` | 获取学生画像 |
| POST | `/api/diagnosis` | 诊断知识缺口 |
| POST | `/api/generate` | 生成学习内容 |
| POST | `/api/evaluate` | 评估答题结果 |
| POST | `/api/knowledge` | 添加知识到 RAG |
| WS | `/ws/{client_id}` | WebSocket 实时交互 |

### 配置说明

在 `.env` 文件中配置 LLM：

```env
# DeepSeek（推荐）
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 通义千问（备选）
# DASHSCOPE_API_KEY=sk-xxxxxxxx
```

## 🎓 使用流程

1. **输入学习主题** - 选择想要学习的内容
2. **智能诊断** - Agent 分析你的知识缺口
3. **生成讲义** - 基于 RAG 知识库生成个性化讲义
4. **完成练习** - 巩固知识点
5. **评估反馈** - 获得学习效果报告

## 📝 文档清单

- [x] SRS 需求规格说明书
- [x] 概要设计说明书
- [x] 详细设计说明书
- [x] 测试计划与用例
- [x] 用户操作手册

## 👥 团队成员

- **徐颖** - 多智能体核心逻辑
- **姚畅** - 前端界面
- **廖宏伟** - 测试与文档

**指导教师：** 满国晶

## 📄 许可证

本项目仅供学习交流使用。

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代 Python Web 框架
- [Streamlit](https://github.com/streamlit/streamlit) - 数据科学 Web 框架

---

<p align="center">
  <strong>第十五届"中国软件杯"大学生软件设计大赛 A3 赛题</strong>
  <br>
  Team IKUN 🎓
</p>
