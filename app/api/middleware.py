"""
智知因 - 生产级中间件
包含限流、请求追踪、日志、监控等生产级特性
"""
import time
import uuid
import asyncio
from typing import Callable
from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger
import json


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID追踪中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始
        logger.info(
            f"Request started | "
            f"id={request_id} | "
            f"method={request.method} | "
            f"path={request.url.path} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"

            # 记录请求完成
            logger.info(
                f"Request completed | "
                f"id={request_id} | "
                f"status={response.status_code} | "
                f"duration={process_time:.3f}s"
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed | "
                f"id={request_id} | "
                f"error={str(e)} | "
                f"duration={process_time:.3f}s"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单限流中间件 - 基于内存存储"""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict = {}
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable):
        # 定期清理过期记录
        now = time.time()
        if now - self.last_cleanup > 60:
            self._cleanup_old_entries()
            self.last_cleanup = now

        # 获取客户端标识
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}"

        # 检查限流
        if not self._check_rate_limit(key):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "请求过于频繁，请稍后再试",
                    "retry_after": 60
                }
            )

        response = await call_next(request)
        return response

    def _check_rate_limit(self, key: str) -> bool:
        """检查限流"""
        now = time.time()

        if key not in self.request_counts:
            self.request_counts[key] = []

        # 清理超过1分钟的请求
        self.request_counts[key] = [
            t for t in self.request_counts[key]
            if now - t < 60
        ]

        if len(self.request_counts[key]) >= self.requests_per_minute:
            return False

        self.request_counts[key].append(now)
        return True

    def _cleanup_old_entries(self):
        """清理过期记录"""
        now = time.time()
        expired_keys = [
            k for k, times in self.request_counts.items()
            if all(now - t >= 60 for t in times)
        ]
        for k in expired_keys:
            del self.request_counts[k]


class LoggingMiddleware(BaseHTTPMiddleware):
    """详细日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        # 记录请求体大小
        content_length = request.headers.get("content-length", "unknown")

        logger.debug(
            f"Request details | "
            f"method={request.method} | "
            f"path={request.url.path} | "
            f"query_params={dict(request.query_params)} | "
            f"content_length={content_length}"
        )

        response = await call_next(request)

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.error(
                f"Unhandled exception | "
                f"request_id={request_id} | "
                f"error={str(e)} | "
                f"path={request.url.path}"
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "服务器内部错误",
                    "request_id": request_id,
                    "message": str(e) if logger.level_name == "DEBUG" else None
                }
            )
