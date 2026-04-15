"""
智知因 - Agent执行引擎
包含重试策略、错误处理、熔断器等生产级特性
"""
import asyncio
import time
from typing import Callable, Any, Optional, TypeVar, Dict
from functools import wraps
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

T = TypeVar('T')


class RetryStrategy(Enum):
    """重试策略"""
    IMMEDIATE = "immediate"           # 立即重试
    EXPONENTIAL = "exponential"       # 指数退避
    LINEAR = "linear"                 # 线性退避
    FIBONACCI = "fibonacci"           # 斐波那契退避


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"     # 正常
    OPEN = "open"         # 熔断
    HALF_OPEN = "half_open"  # 半开


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retry_on_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5       # 失败次数阈值
    recovery_timeout: int = 60      # 恢复超时(秒)
    half_open_max_calls: int = 3    # 半开状态最大调用数


class CircuitBreaker:
    """熔断器实现"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

    def record_success(self):
        """记录成功调用"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        """检查是否可以尝试调用"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls

        return False

    def __call__(self, func: Callable) -> Callable:
        """装饰器实现"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.can_attempt():
                raise CircuitBreakerOpenError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.can_attempt():
                raise CircuitBreakerOpenError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass


class AgentExecutionEngine:
    """Agent执行引擎 - 包含重试、熔断、缓存等生产级特性"""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.execution_cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        self.cache_ttl = 300  # 缓存TTL 5分钟
        self.execution_history: list = []

    def _get_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """计算重试延迟"""
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (2 ** attempt)
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.FIBONACCI:
            delay = config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = config.base_delay

        return min(delay, config.max_delay)

    def _fibonacci(self, n: int) -> int:
        """斐波那契数列"""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    def _generate_cache_key(self, agent_name: str, state_snapshot: Dict) -> str:
        """生成缓存键"""
        content = json.dumps(state_snapshot, sort_keys=True, default=str)
        return hashlib.sha256(f"{agent_name}:{content}".encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self.execution_cache:
            return False
        result, timestamp = self.execution_cache[key]
        return (datetime.now() - timestamp).total_seconds() < self.cache_ttl

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        config: RetryConfig,
        agent_name: str = "unknown",
        **kwargs
    ) -> Any:
        """带重试的执行"""
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                # 检查缓存
                if hasattr(func, '__name__'):
                    cache_key = self._generate_cache_key(
                        agent_name,
                        {"func": func.__name__, "kwargs": kwargs}
                    )
                    if self._is_cache_valid(cache_key):
                        logger.debug(f"Cache hit for {agent_name}")
                        return self.execution_cache[cache_key][0]

                # 执行
                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)

                # 记录执行历史
                self.execution_history.append({
                    "agent": agent_name,
                    "attempt": attempt + 1,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })

                # 缓存结果
                if hasattr(func, '__name__'):
                    self.execution_cache[cache_key] = (result, datetime.now())

                return result

            except config.retry_on_exceptions as e:
                last_exception = e
                logger.warning(
                    f"Agent {agent_name} attempt {attempt + 1} failed: {str(e)}"
                )

                if attempt < config.max_attempts - 1:
                    delay = self._get_retry_delay(attempt, config)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)

        # 所有重试都失败
        self.execution_history.append({
            "agent": agent_name,
            "attempt": config.max_attempts,
            "status": "failed",
            "error": str(last_exception),
            "timestamp": datetime.now().isoformat()
        })

        raise last_exception

    def get_execution_stats(self) -> Dict:
        """获取执行统计"""
        total = len(self.execution_history)
        if total == 0:
            return {"total": 0, "success_rate": 1.0}

        success = sum(1 for h in self.execution_history if h["status"] == "success")
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": success / total
        }

    def clear_cache(self):
        """清空缓存"""
        self.execution_cache.clear()


# 全局执行引擎
execution_engine = AgentExecutionEngine()


def with_retry(config: RetryConfig = None, agent_name: str = "unknown"):
    """重试装饰器"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await execution_engine.execute_with_retry(
                func, config, agent_name, **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本使用事件循环
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    execution_engine.execute_with_retry(
                        func, config, agent_name, **kwargs
                    )
                )
            finally:
                loop.close()

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def with_circuit_breaker(breaker_name: str, config: CircuitBreakerConfig = None):
    """熔断器装饰器"""
    if config is None:
        config = CircuitBreakerConfig()

    def decorator(func: Callable) -> Callable:
        if breaker_name not in execution_engine.circuit_breakers:
            execution_engine.circuit_breakers[breaker_name] = CircuitBreaker(config)

        breaker = execution_engine.circuit_breakers[breaker_name]

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker(func)(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker(func)(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
