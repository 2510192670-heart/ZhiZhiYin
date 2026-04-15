"""
智知因 - FastAPI 路由
"""
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from api.models import (
    UserCreate, DiagnosisRequest, GenerateRequest,
    AnswerSubmit, KnowledgeAdd,
    UserResponse, ProfileResponse, DiagnosisResponse,
    GenerateResponse, EvaluationResponse
)
from api.llm_client import get_llm_client
from db import DatabaseManager, get_db, init_database
from db.vector_store import get_rag_retriever
from agent import AgentCoordinator

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于大模型的多智能体个性化学习系统 API"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局管理器
db: DatabaseManager = None
coordinator: AgentCoordinator = None


@app.on_event("startup")
async def startup():
    """应用启动初始化"""
    global db, coordinator

    # 初始化数据库
    db = get_db()
    init_database()
    logger.info("数据库初始化完成")

    # 初始化 LLM 客户端
    llm_client = get_llm_client()
    logger.info(f"LLM 客户端初始化完成，使用模型: {llm_client.get_model_name()}")

    # 初始化 Agent 协调器
    rag_retriever = get_rag_retriever()
    coordinator = AgentCoordinator(llm_client, rag_retriever)
    logger.info("Agent 协调器初始化完成")


# ============ 用户管理 ============

@app.post("/api/users", response_model=UserResponse)
async def create_user(data: UserCreate):
    """创建用户"""
    user_id = str(uuid.uuid4())

    success = db.create_user(user_id, data.username)
    if not success:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = db.get_user(user_id)

    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        created_at=user["created_at"]
    )


@app.get("/api/users/{user_id}/profile", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """获取学生画像"""
    profile = db.get_student_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")

    return ProfileResponse(
        user_id=profile["user_id"],
        subject=profile.get("subject"),
        knowledge_mastery=profile.get("knowledge_mastery", {}),
        overall_level=profile.get("overall_level", "一般"),
        learning_history=profile.get("learning_history", [])
    )


# ============ 学习流程 ============

@app.post("/api/diagnosis", response_model=DiagnosisResponse)
async def diagnose(data: DiagnosisRequest):
    """诊断知识缺口"""
    # 获取用户画像
    profile = db.get_student_profile(data.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取学习历史
    history = db.get_learning_history(data.user_id)

    # 执行诊断
    state = await coordinator.diagnose_only(data.user_id, profile, history, data.topic)

    return DiagnosisResponse(
        user_id=data.user_id,
        knowledge_gaps=state.diagnosis_result.get("knowledge_gaps", []),
        weak_points_analysis=state.diagnosis_result.get("weak_points_analysis", ""),
        learning_path=state.diagnosis_result.get("learning_path", []),
        estimated_time=state.diagnosis_result.get("estimated_time", "")
    )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_content(data: GenerateRequest):
    """生成学习内容"""
    # 获取用户画像
    profile = db.get_student_profile(data.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 创建会话
    session_id = str(uuid.uuid4())
    db.create_session(session_id, data.user_id)

    # 执行内容生成流程
    state = await coordinator.run_learning_pipeline(
        user_id=data.user_id,
        session_id=session_id,
        student_profile=profile,
        knowledge_gaps=data.knowledge_gaps,
        difficulty=data.difficulty,
    )

    return GenerateResponse(
        session_id=session_id,
        lecture=state.generated_content.get("lecture", {}),
        exercises=state.generated_content.get("exercises", []),
        summary=state.generated_content.get("summary", "")
    )


@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_answers(data: AnswerSubmit):
    """评估答题结果"""
    # 获取用户画像
    profile = db.get_student_profile(data.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 执行评估
    state = await coordinator.evaluate_only(data.user_id, profile, data.answers)

    # 保存学习记录
    db.save_learning_record({
        "user_id": data.user_id,
        "session_id": data.session_id,
        "topic": "综合学习",
        "difficulty": state.content_difficulty,
        "accuracy_rate": state.evaluation_result.get("performance_summary", {}).get("accuracy_rate"),
    })

    # 更新会话
    db.update_session(data.session_id, "completed")

    return EvaluationResponse(
        performance_summary=state.evaluation_result.get("performance_summary", {}),
        knowledge_mastery=state.evaluation_result.get("knowledge_mastery", []),
        next_steps=state.evaluation_result.get("next_steps", [])
    )


# ============ 知识库管理 ============

@app.post("/api/knowledge")
async def add_knowledge(data: KnowledgeAdd):
    """添加知识到 RAG 知识库"""
    try:
        rag = get_rag_retriever()
        rag.add_text_knowledge(data.content, data.source, data.metadata)
        return {"message": "知识添加成功", "source": data.source}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ WebSocket 实时通信 ============

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 实时交互"""
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            payload = data.get("data", {})

            if msg_type == "heartbeat":
                await manager.send_message({
                    "type": "heartbeat",
                    "success": True,
                    "timestamp": data.get("timestamp")
                }, client_id)

            elif msg_type == "generate":
                # 实时生成内容
                profile = db.get_student_profile(payload["user_id"])
                if not profile:
                    await manager.send_message({
                        "type": "error",
                        "error": "用户不存在"
                    }, client_id)
                    continue

                session_id = str(uuid.uuid4())

                # 分步发送进度
                await manager.send_message({
                    "type": "progress",
                    "step": "诊断",
                    "message": "正在分析学习情况..."
                }, client_id)

                state = await coordinator.run_learning_pipeline(
                    user_id=payload["user_id"],
                    session_id=session_id,
                    student_profile=profile,
                    difficulty=payload.get("difficulty", "基础"),
                )

                await manager.send_message({
                    "type": "progress",
                    "step": "完成",
                    "message": "学习内容生成完成"
                }, client_id)

                await manager.send_message({
                    "type": "result",
                    "success": True,
                    "data": {
                        "session_id": session_id,
                        "lecture": state.generated_content.get("lecture", {}),
                        "exercises": state.generated_content.get("exercises", []),
                        "summary": state.generated_content.get("summary", ""),
                    }
                }, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"客户端断开连接: {client_id}")


# ============ 健康检查 ============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
