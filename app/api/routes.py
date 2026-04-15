"""
智知因 - FastAPI生产级后端接口
包含完整的API路由、错误处理、输入验证、SSE流式响应
"""
import uuid
import time
import json
import re
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from loguru import logger

from app.config import settings
from app.models.schemas import (
    UserCreate, UserLogin, StudentProfileUpdate,
    StudyStartRequest, ResourceGenerateRequest, EvaluationSubmitRequest,
    StudySessionResponse, EvaluationResult
)
from app.db.database import db_manager
from app.agents.system_state import agent_controller
from app.rag import rag_pipeline
from app.api.monitoring import monitoring
from app.api.middleware import (
    RequestIDMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
    ErrorHandlerMiddleware
)


# ========== 生命周期管理 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("应用启动中...")

    # 初始化数据库
    try:
        db_manager
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

    yield

    logger.info("应用关闭中...")


# ========== FastAPI应用 ==========

app = FastAPI(
    title="智知因 - 多智能体个性化学习系统",
    version="1.0.0",
    description="基于大模型的多智能体个性化资源生成与学习系统API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 请求/响应模型 ==========

class ApiResponse(BaseModel):
    """统一API响应"""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    request_id: Optional[str] = None


class MetricsResponse(BaseModel):
    """指标响应"""
    uptime_seconds: float
    requests: Dict
    sessions: Dict
    system: Dict
    endpoints: Dict


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    checks: Dict
    version: str


# ========== 中间件：请求追踪 ==========

@app.middleware("http")
async def track_request(request: Request, call_next):
    """追踪所有请求"""
    start_time = time.time()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    response = await call_next(request)

    latency = time.time() - start_time

    # 记录指标
    monitoring.record_request(
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        latency=latency
    )

    return response


# ========== 健康检查与指标 ==========

@app.get("/", include_in_schema=False)
async def root():
    """根路径"""
    return {"message": "欢迎使用智知因API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    health = monitoring.get_health_status()
    return HealthResponse(
        status=health["status"],
        checks=health["checks"],
        version=settings.APP_VERSION
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["系统"])
async def get_metrics():
    """获取系统指标"""
    return monitoring.get_metrics()


# ========== 用户管理 ==========

@app.post(
    "/api/v1/users/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["用户"]
)
async def register(user: UserCreate):
    """用户注册"""
    # 检查学号是否已存在
    existing = db_manager.get_user_by_student_id(user.student_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号已注册"
        )

    # 创建用户
    user_id = str(uuid.uuid4())
    success = db_manager.create_user(
        user_id=user_id,
        student_id=user.student_id,
        name=user.name,
        major=user.major,
        grade=user.grade
    )

    if success:
        return ApiResponse(
            success=True,
            message="注册成功",
            data={"user_id": user_id}
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="注册失败"
    )


@app.post("/api/v1/users/login", tags=["用户"])
async def login(user: UserLogin, request: Request):
    """用户登录"""
    existing_user = db_manager.get_user_by_student_id(user.student_id)

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if existing_user['name'] != user.name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="姓名与学号不匹配"
        )

    profile = db_manager.get_profile(existing_user['user_id'])

    return ApiResponse(
        success=True,
        message="登录成功",
        data={
            "user_id": existing_user['user_id'],
            "student_id": existing_user['student_id'],
            "name": existing_user['name'],
            "profile": profile or {}
        }
    )


@app.get("/api/v1/users/{user_id}", tags=["用户"])
async def get_user(user_id: str):
    """获取用户信息"""
    user = db_manager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    profile = db_manager.get_profile(user_id)

    return ApiResponse(
        success=True,
        data={**user, "profile": profile or {}}
    )


@app.put("/api/v1/users/{user_id}/profile", tags=["用户"])
async def update_profile(user_id: str, update: StudentProfileUpdate):
    """更新学生档案"""
    user = db_manager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    update_data = update.model_dump(exclude_none=True)
    if update_data:
        db_manager.update_profile(user_id, **update_data)

    profile = db_manager.get_profile(user_id)

    return ApiResponse(
        success=True,
        message="更新成功",
        data={"profile": profile}
    )


# ========== 学习会话 ==========

@app.post("/api/v1/study/start", response_model=StudySessionResponse, tags=["学习"])
async def start_study(request: StudyStartRequest, background_tasks: BackgroundTasks):
    """开始学习会话"""
    # 验证用户
    user = db_manager.get_user(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 创建会话
    session_id = f"S_{uuid.uuid4().hex[:12]}"

    success = db_manager.create_session(
        session_id=session_id,
        user_id=request.user_id,
        topic=request.topic
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="会话创建失败"
        )

    # 更新活跃会话数
    monitoring.set_active_sessions(
        monitoring.get_metrics()["sessions"]["active"] + 1
    )

    # 后台运行Agent工作流
    # 注意：完整诊断将在generate时触发

    return StudySessionResponse(
        session_id=session_id,
        topic=request.topic,
        knowledge_gaps=[],
        suggested_level="初级",
        message="学习会话已创建，请选择资源类型开始学习"
    )


@app.post("/api/v1/study/generate", tags=["学习"])
async def generate_resource(request: ResourceGenerateRequest):
    """生成学习资源 - SSE流式返回"""
    session = db_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    user_id = session['user_id']
    topic = session['topic']

    async def event_generator():
        try:
            # 阶段1: 诊断
            yield {"event": "status", "data": json.dumps({
                "phase": "diagnose",
                "message": "正在分析学习需求..."
            })}

            # 获取学生档案
            profile = db_manager.get_profile(user_id) or {}

            # 执行完整工作流
            state = await agent_controller.arun_workflow(
                user_id=user_id,
                session_id=request.session_id,
                topic=topic
            )

            # 获取生成的资源
            resource_content = state.get('resources', {}).get(
                request.mode,
                state.get('resources', {}).get('lecture', '')
            )

            # 阶段2: 生成完成
            yield {"event": "status", "data": json.dumps({
                "phase": "generated",
                "message": "资源生成完成"
            })}

            yield {"event": "resource", "data": json.dumps({
                "type": request.mode,
                "content": resource_content,
                "difficulty": state.get('suggested_level', '初级'),
                "knowledge_gaps": state.get('knowledge_gaps', []),
                "evaluation_score": state.get('evaluation_score', 0)
            })}

            # 阶段3: 更新会话
            db_manager.update_session_state(request.session_id, {
                "knowledge_gaps": state.get('knowledge_gaps', []),
                "suggested_level": state.get('suggested_level', '初级'),
                "resources": state.get('resources', {}),
                "status": "resource_ready"
            })

            yield {"event": "done", "data": ""}

        except Exception as e:
            logger.error(f"资源生成失败: {e}")
            yield {"event": "error", "data": json.dumps({
                "message": str(e)
            })}

    return EventSourceResponse(event_generator())


@app.post("/api/v1/study/evaluate", response_model=EvaluationResult, tags=["学习"])
async def evaluate_answer(request: EvaluationSubmitRequest):
    """评测学生答案"""
    session = db_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 获取会话状态
    import json
    session_state = {}
    if session.get('current_state'):
        try:
            session_state = json.loads(session['current_state'])
        except:
            pass

    # 使用LLM进行评测
    from app.agents.llm_client import llm_client

    eval_prompt = f"""请评测学生对以下问题的回答：

问题知识点：{session['topic']}
学生答案：
{request.student_answer}

评测维度：
1. 答案是否正确
2. 理解深度如何
3. 是否有知识缺口
4. 改进建议

请以JSON格式返回：
{{
    "is_correct": true/false,
    "score": 0.0-1.0,
    "feedback": "具体反馈",
    "knowledge_gaps": ["缺口1", "缺口2"],
    "next_steps": "下一步建议"
}}"""

    response = llm_client.generate([
        {"role": "user", "content": eval_prompt}
    ])

    # 解析响应
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {
                "is_correct": False,
                "score": 0.5,
                "feedback": "无法解析评测结果",
                "knowledge_gaps": [],
                "next_steps": "请重试"
            }
    except Exception as e:
        logger.error(f"评测解析失败: {e}")
        result = {
            "is_correct": False,
            "score": 0.5,
            "feedback": "评测处理异常",
            "knowledge_gaps": [],
            "next_steps": "请稍后重试"
        }

    # 记录学习结果
    db_manager.add_learning_record(
        user_id=session['user_id'],
        topic=session['topic'],
        score=result.get('score', 0.5),
        knowledge_gaps=result.get('knowledge_gaps', []),
        resources_used=[request.session_id],
        session_id=request.session_id
    )

    # 更新学生档案
    if result.get('score', 0) >= 0.9:
        profile = db_manager.get_profile(session['user_id'])
        if profile:
            mastered = profile.get('mastered_nodes', [])
            if session['topic'] not in mastered:
                mastered.append(session['topic'])
                db_manager.update_profile(
                    session['user_id'],
                    mastered_nodes=mastered
                )

    return EvaluationResult(**result)


# ========== 学习历史 ==========

@app.get("/api/v1/history/{user_id}", tags=["学习"])
async def get_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=100)
):
    """获取学习历史"""
    user = db_manager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    history = db_manager.get_learning_history(user_id, limit)

    return ApiResponse(
        success=True,
        data={"history": history}
    )


# ========== 知识库管理 ==========

@app.post("/api/v1/knowledge/add", tags=["知识库"])
async def add_knowledge(
    course: str = Query(..., description="课程名称"),
    chapter: int = Query(..., ge=1, description="章节编号"),
    content: str = Query(..., description="知识内容"),
    source: str = Query(default="教材", description="来源"),
    doc_type: str = Query(default="concept", description="文档类型"),
    importance: str = Query(default="核心", description="重要性")
):
    """添加知识到向量库"""
    result = db_manager.add_knowledge(
        course=course,
        chapter=chapter,
        content=content,
        source=source,
        doc_type=doc_type,
        importance=importance
    )

    return ApiResponse(
        success=True,
        message=result,
        data={"course": course, "chapter": chapter}
    )


@app.post("/api/v1/knowledge/upload", tags=["知识库"])
async def upload_knowledge(
    course: str = Query(..., description="课程名称"),
    chapter: int = Query(..., ge=1, description="章节编号"),
    source: str = Query(default="教材", description="来源"),
    doc_type: str = Query(default="concept", description="文档类型"),
    importance: str = Query(default="核心", description="重要性"),
    request: Request = None
):
    """上传PDF文件到知识库"""
    try:
        # 获取上传的文件
        form = await request.form()
        file = form.get("file")

        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未上传文件"
            )

        # 保存临时文件
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 处理PDF
            result = rag_pipeline.process_and_store(
                file_path=tmp_path,
                course=course,
                chapter=chapter,
                source=source,
                doc_type=doc_type,
                importance=importance
            )

            return ApiResponse(
                success=True,
                message=f"成功处理{result.get('chunks', 0)}个知识片段",
                data=result
            )
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"知识上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/knowledge/search", tags=["知识库"])
async def search_knowledge(
    query: str = Query(..., description="搜索关键词"),
    course: Optional[str] = Query(default=None, description="课程筛选"),
    top_k: int = Query(default=5, ge=1, le=20, description="返回数量")
):
    """搜索知识"""
    results = rag_pipeline.retrieve(
        query=query,
        course=course,
        top_k=top_k
    )

    return ApiResponse(
        success=True,
        data={
            "results": [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "score": r.score
                }
                for r in results
            ]
        }
    )


@app.get("/api/v1/knowledge/chapters/{course}", tags=["知识库"])
async def get_chapters(course: str):
    """获取课程章节"""
    chapters = db_manager.get_course_chapters(course)

    return ApiResponse(
        success=True,
        data={"course": course, "chapters": chapters}
    )


# ========== 会话管理 ==========

@app.get("/api/v1/sessions/{session_id}", tags=["会话"])
async def get_session(session_id: str):
    """获取会话详情"""
    session = db_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    return ApiResponse(
        success=True,
        data=session
    )


@app.delete("/api/v1/sessions/{session_id}", tags=["会话"])
async def close_session(session_id: str):
    """关闭会话"""
    session = db_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 更新会话状态
    db_manager.update_session_state(session_id, {"status": "closed"})

    # 减少活跃会话数
    current = monitoring.get_metrics()["sessions"]["active"]
    monitoring.set_active_sessions(max(0, current - 1))

    return ApiResponse(
        success=True,
        message="会话已关闭"
    )


# ========== 错误处理 ==========

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理异常: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "服务器内部错误",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# ========== 主应用入口 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
