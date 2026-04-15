"""
智知因 - 完整测试套件
包含单元测试、集成测试、API测试
"""
import pytest
import sys
import os
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ========== 测试配置 ==========

@pytest.fixture
def mock_settings():
    """模拟设置"""
    with patch('app.config.settings') as mock:
        mock.APP_NAME = "智知因测试"
        mock.APP_VERSION = "1.0.0"
        mock.LLM_PROVIDER = "deepseek"
        mock.DEEPSEEK_API_KEY = "test_key"
        mock.SQLITE_DB_PATH = "/tmp/test_zhiyin.db"
        mock.CHROMA_DB_PATH = "/tmp/test_chroma"
        yield mock


@pytest.fixture
def sample_state() -> Dict:
    """示例状态"""
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "student_profile": {
            "level": 2,
            "learning_style": "文本",
            "mastered_nodes": ["Python基础", "函数定义"],
            "weaknesses": ["装饰器", "闭包"]
        },
        "current_topic": "Python装饰器",
        "knowledge_gaps": [],
        "rag_context": "装饰器是Python的一种高级特性...",
        "resources": {},
        "review_feedback": "",
        "evaluation_score": 0.0,
        "conversation_history": [],
        "suggested_level": "中级",
        "current_phase": "diagnose",
        "error_message": None,
        "execution_metadata": {}
    }


# ========== 单元测试 ==========

class TestDatabaseManager:
    """数据库管理器测试"""

    def test_database_initialization(self):
        """测试数据库初始化"""
        from app.db.database import DatabaseManager

        db = DatabaseManager()
        assert db.sqlite_path.exists() or db.sqlite_path.parent.exists()
        assert db.chroma_client is not None

    def test_user_creation(self, tmp_path):
        """测试用户创建"""
        with patch('app.config.settings') as mock_settings:
            mock_settings.SQLITE_DB_PATH = tmp_path / "test.db"
            mock_settings.CHROMA_DB_PATH = tmp_path / "chroma"

            from app.db.database import DatabaseManager
            db = DatabaseManager()

            result = db.create_user(
                user_id="test_001",
                student_id="S001",
                name="测试用户",
                major="计算机科学",
                grade="大一"
            )
            assert result is True

            user = db.get_user("test_001")
            assert user is not None
            assert user["name"] == "测试用户"

    def test_profile_update(self, tmp_path):
        """测试档案更新"""
        with patch('app.config.settings') as mock_settings:
            mock_settings.SQLITE_DB_PATH = tmp_path / "test.db"
            mock_settings.CHROMA_DB_PATH = tmp_path / "chroma"

            from app.db.database import DatabaseManager
            db = DatabaseManager()

            # 创建用户
            db.create_user(
                user_id="test_002",
                student_id="S002",
                name="测试用户2",
                major="软件工程",
                grade="大二"
            )

            # 更新档案
            result = db.update_profile(
                "test_002",
                level=3,
                mastered_nodes=["Python基础"]
            )
            assert result is True

            # 验证更新
            profile = db.get_profile("test_002")
            assert profile["level"] == 3
            assert "Python基础" in profile["mastered_nodes"]

    def test_vector_search(self):
        """测试向量搜索"""
        from app.db.database import db_manager

        # 添加测试知识
        db_manager.add_knowledge(
            course="测试课程",
            chapter=1,
            content="这是关于装饰器的知识内容。装饰器用于修改函数行为。",
            source="测试文档",
            doc_type="concept",
            importance="核心"
        )

        # 搜索
        results = db_manager.vector_search("装饰器", course="测试课程", top_k=3)
        assert isinstance(results, list)

        # 清理
        db_manager.delete_course_knowledge("测试课程")


class TestRAGPipeline:
    """RAG管道测试"""

    def test_text_splitter(self):
        """测试文本分割"""
        from app.rag.pipeline import TextSplitter

        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)

        text = "这是第一段文本。\n\n这是第二段文本，包含更多内容。\n\n第三段文本。"
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) <= 150 for c in chunks)  # 有一些重叠

    def test_document_creation(self):
        """测试文档创建"""
        from app.rag.pipeline import Document

        doc = Document(
            id="test_doc_1",
            content="测试内容",
            metadata={"source": "测试"}
        )

        assert doc.id == "test_doc_1"
        assert doc.content == "测试内容"
        assert doc.metadata["source"] == "测试"

    def test_chunk_creation(self):
        """测试块创建"""
        from app.rag.pipeline import Chunk

        chunk = Chunk(
            id="test_chunk_1",
            content="测试块内容",
            metadata={"index": 0}
        )

        assert chunk.id == "test_chunk_1"
        assert chunk.content == "测试块内容"
        assert chunk.embedding is None


class TestAgentPrompts:
    """Agent提示词测试"""

    def test_diagnose_prompt_structure(self):
        """测试诊断提示词结构"""
        from app.agents.prompts import DIAGNOSE_AGENT_PROMPT

        assert "诊断Agent" in DIAGNOSE_AGENT_PROMPT
        assert "knowledge_gaps" in DIAGNOSE_AGENT_PROMPT
        assert "JSON格式" in DIAGNOSE_AGENT_PROMPT

    def test_generator_prompt_structure(self):
        """测试生成提示词结构"""
        from app.agents.prompts import GENERATOR_AGENT_PROMPT

        assert "Generator Agent" in GENERATOR_AGENT_PROMPT
        assert "lecture" in GENERATOR_AGENT_PROMPT
        assert "Markdown" in GENERATOR_AGENT_PROMPT

    def test_review_prompt_structure(self):
        """测试审查提示词结构"""
        from app.agents.prompts import REVIEW_AGENT_PROMPT

        assert "Review Agent" in REVIEW_AGENT_PROMPT
        assert "准确性审查" in REVIEW_AGENT_PROMPT
        assert "evaluation_score" in REVIEW_AGENT_PROMPT


class TestResilience:
    """弹性机制测试"""

    def test_retry_config(self):
        """测试重试配置"""
        from app.agents.resilience import RetryConfig, RetryStrategy

        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL
        )

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.strategy == RetryStrategy.EXPONENTIAL

    def test_circuit_breaker_config(self):
        """测试熔断器配置"""
        from app.agents.resilience import CircuitBreakerConfig, CircuitBreaker, CircuitState

        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60
        )

        breaker = CircuitBreaker(config)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_open(self):
        """测试熔断器开启"""
        from app.agents.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState

        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        # 记录失败
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # 检查熔断状态
        assert not breaker.can_attempt()

    def test_circuit_breaker_recovery(self):
        """测试熔断器恢复"""
        from app.agents.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState
        import time

        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1)
        breaker = CircuitBreaker(config)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # 等待恢复
        time.sleep(1.1)
        assert breaker.can_attempt()
        assert breaker.state == CircuitState.HALF_OPEN


class TestMonitoring:
    """监控服务测试"""

    def test_monitoring_service_init(self):
        """测试监控服务初始化"""
        from app.api.monitoring import MonitoringService, Metrics

        service = MonitoringService()
        metrics = service.get_metrics()

        assert "uptime_seconds" in metrics
        assert "requests" in metrics
        assert "system" in metrics
        assert metrics["requests"]["total"] == 0

    def test_record_request(self):
        """测试请求记录"""
        from app.api.monitoring import MonitoringService

        service = MonitoringService()

        service.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            latency=0.1
        )

        metrics = service.get_metrics()
        assert metrics["requests"]["total"] == 1
        assert metrics["requests"]["success"] == 1

    def test_health_status(self):
        """测试健康状态"""
        from app.api.monitoring import MonitoringService

        service = MonitoringService()
        health = service.get_health_status()

        assert "status" in health
        assert "checks" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]


# ========== API测试 ==========

class TestAPIEndpoints:
    """API端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.api.routes import app
        return TestClient(app)

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        assert "欢迎" in response.json()["message"]

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "requests" in data

    def test_register_endpoint(self, client):
        """测试注册端点"""
        import uuid
        student_id = f"TEST_{uuid.uuid4().hex[:8]}"

        response = client.post("/api/v1/users/register", json={
            "student_id": student_id,
            "name": "测试用户",
            "major": "计算机科学",
            "grade": "大一"
        })

        assert response.status_code in [200, 201, 400]  # 成功或学号已存在

    def test_login_endpoint_not_found(self, client):
        """测试登录端点 - 用户不存在"""
        response = client.post("/api/v1/users/login", json={
            "student_id": "NONEXISTENT",
            "name": "不存在"
        })
        assert response.status_code == 404

    def test_get_user_not_found(self, client):
        """测试获取用户 - 用户不存在"""
        response = client.get("/api/v1/users/nonexistent")
        assert response.status_code == 404

    def test_study_start_invalid_user(self, client):
        """测试开始学习 - 用户不存在"""
        response = client.post("/api/v1/study/start", json={
            "user_id": "nonexistent",
            "topic": "Python装饰器"
        })
        assert response.status_code == 404


# ========== Agent集成测试 ==========

class TestAgentWorkflow:
    """Agent工作流测试"""

    @pytest.mark.asyncio
    async def test_diagnose_agent_invoke(self, sample_state):
        """测试诊断Agent调用"""
        with patch('app.agents.llm_client.llm_client') as mock_llm:
            mock_llm.agenerate = AsyncMock(return_value=json.dumps({
                "knowledge_gaps": ["装饰器基础", "闭包概念"],
                "suggested_level": "中级",
                "prerequisites": ["Python函数"],
                "common_misconceptions": ["装饰器会修改原函数"]
            }))

            from app.agents.system_state import DiagnoseAgent
            agent = DiagnoseAgent()

            result_state = await agent.ainvoke(sample_state)

            assert "knowledge_gaps" in result_state
            assert "suggested_level" in result_state

    @pytest.mark.asyncio
    async def test_generator_agent_invoke(self, sample_state):
        """测试生成Agent调用"""
        sample_state['knowledge_gaps'] = ["装饰器基础"]
        sample_state['rag_context'] = "装饰器是Python的重要特性..."

        with patch('app.agents.llm_client.llm_client') as mock_llm:
            mock_llm.agenerate = AsyncMock(return_value="""# Python装饰器

## 什么是装饰器

装饰器是一种高级Python特性...

## 示例代码

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```
""")

            from app.agents.system_state import GeneratorAgent
            agent = GeneratorAgent()

            result_state = await agent.ainvoke(sample_state, "lecture")

            assert "resources" in result_state
            assert "lecture" in result_state["resources"]

    @pytest.mark.asyncio
    async def test_review_agent_invoke(self, sample_state):
        """测试审查Agent调用"""
        sample_state['resources'] = {
            'lecture': '# 装饰器讲义\n\n这是内容...'
        }
        sample_state['rag_context'] = "装饰器权威内容..."

        with patch('app.agents.llm_client.llm_client') as mock_llm:
            mock_llm.agenerate = AsyncMock(return_value=json.dumps({
                "is_approved": True,
                "evaluation_score": 0.88,
                "review_notes": "内容准确，难度适中",
                "review_details": {
                    "accuracy": {"score": 0.9, "issues": []},
                    "difficulty_match": {"score": 0.85, "issues": []}
                }
            }))

            from app.agents.system_state import ReviewAgent
            agent = ReviewAgent()

            result_state = await agent.ainvoke(sample_state, "lecture")

            assert "evaluation_score" in result_state
            assert result_state["evaluation_score"] > 0


# ========== 性能测试标记 ==========

@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    def test_concurrent_requests(self):
        """测试并发请求"""
        # 这个测试需要实际运行的服务
        pass

    def test_response_time(self):
        """测试响应时间"""
        # 这个测试需要实际运行的服务
        pass


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
