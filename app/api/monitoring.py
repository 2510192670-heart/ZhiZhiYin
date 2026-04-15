"""
智知因 - 监控和指标模块
提供系统健康监控、性能指标等功能
"""
import time
import psutil
import os
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock


@dataclass
class Metrics:
    """系统指标"""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    total_latency: float = 0.0
    active_sessions: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0


@dataclass
class RequestMetrics:
    """请求指标"""
    endpoint: str
    method: str
    status_code: int
    latency: float
    timestamp: datetime


class MonitoringService:
    """监控服务"""

    def __init__(self):
        self._metrics = Metrics()
        self._request_history: list = []
        self._max_history_size = 1000
        self._lock = Lock()
        self._start_time = time.time()
        self._endpoint_stats: Dict[str, Dict] = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "failed": 0,
            "total_latency": 0.0,
            "max_latency": 0.0,
            "min_latency": float("inf")
        })

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency: float
    ):
        """记录请求"""
        with self._lock:
            self._metrics.requests_total += 1
            self._metrics.total_latency += latency

            if 200 <= status_code < 300:
                self._metrics.requests_success += 1
            else:
                self._metrics.requests_failed += 1

            # 端点统计
            stats = self._endpoint_stats[endpoint]
            stats["count"] += 1
            if 200 <= status_code < 300:
                stats["success"] += 1
            else:
                stats["failed"] += 1
            stats["total_latency"] += latency
            stats["max_latency"] = max(stats["max_latency"], latency)
            stats["min_latency"] = min(stats["min_latency"], latency)

            # 请求历史
            self._request_history.append(RequestMetrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                latency=latency,
                timestamp=datetime.now()
            ))

            # 限制历史大小
            if len(self._request_history) > self._max_history_size:
                self._request_history = self._request_history[-self._max_history_size:]

    def set_active_sessions(self, count: int):
        """设置活跃会话数"""
        with self._lock:
            self._metrics.active_sessions = count

    def update_system_metrics(self):
        """更新系统指标"""
        try:
            self._metrics.cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self._metrics.memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            self._metrics.disk_usage = disk.percent
        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")

    def get_metrics(self) -> Dict:
        """获取完整指标"""
        self.update_system_metrics()

        uptime = time.time() - self._start_time
        avg_latency = (
            self._metrics.total_latency / self._metrics.requests_total
            if self._metrics.requests_total > 0
            else 0
        )

        return {
            "uptime_seconds": uptime,
            "requests": {
                "total": self._metrics.requests_total,
                "success": self._metrics.requests_success,
                "failed": self._metrics.requests_failed,
                "success_rate": (
                    self._metrics.requests_success / self._metrics.requests_total
                    if self._metrics.requests_total > 0
                    else 1.0
                ),
                "avg_latency_ms": avg_latency * 1000
            },
            "sessions": {
                "active": self._metrics.active_sessions
            },
            "system": {
                "cpu_percent": self._metrics.cpu_usage,
                "memory_percent": self._metrics.memory_usage,
                "disk_percent": self._metrics.disk_usage
            },
            "endpoints": {
                endpoint: {
                    "count": stats["count"],
                    "success_rate": (
                        stats["success"] / stats["count"]
                        if stats["count"] > 0
                        else 1.0
                    ),
                    "avg_latency_ms": (
                        stats["total_latency"] / stats["count"] * 1000
                        if stats["count"] > 0
                        else 0
                    ),
                    "max_latency_ms": stats["max_latency"] * 1000,
                    "min_latency_ms": (
                        stats["min_latency"] * 1000
                        if stats["min_latency"] != float("inf")
                        else 0
                    )
                }
                for endpoint, stats in self._endpoint_stats.items()
            }
        }

    def get_health_status(self) -> Dict:
        """获取健康状态"""
        self.update_system_metrics()

        health = {
            "status": "healthy",
            "checks": {}
        }

        # 检查CPU
        if self._metrics.cpu_usage > 90:
            health["status"] = "degraded"
            health["checks"]["cpu"] = "high_usage"
        else:
            health["checks"]["cpu"] = "ok"

        # 检查内存
        if self._metrics.memory_usage > 90:
            health["status"] = "degraded"
            health["checks"]["memory"] = "high_usage"
        else:
            health["checks"]["memory"] = "ok"

        # 检查错误率
        if self._metrics.requests_total > 10:
            error_rate = (
                self._metrics.requests_failed / self._metrics.requests_total
            )
            if error_rate > 0.1:
                health["status"] = "degraded"
                health["checks"]["error_rate"] = "high_error_rate"
            else:
                health["checks"]["error_rate"] = "ok"
        else:
            health["checks"]["error_rate"] = "ok"

        return health


# 全局监控服务
monitoring = MonitoringService()
