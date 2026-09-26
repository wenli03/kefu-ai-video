"""
API 弹性与降级模块

提供：
1. 指数退避重试（支持 OpenAI 429 错误）
2. 模型降级（GPT-4o → GPT-4o-mini）
3. 服务降级管理（STT/TTS/数字人）
4. 预设话术库（LLM 不可用时）
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .logging import SessionLogger

_log = SessionLogger("resilience")


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 8.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class ServiceState:
    """服务状态"""
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_check: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    consecutive_failures: int = 0


class CircuitBreaker:
    """
    断路器模式

    状态转换：
    CLOSED (正常) → OPEN (故障) → HALF_OPEN (试探) → CLOSED (恢复)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = "closed"
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_calls = 0
        return self._state

    @property
    def allow_request(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "half_open":
            return self._half_open_calls < self.half_open_max_calls
        return False

    def record_success(self):
        if self.state == "half_open":
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._reset()
        else:
            self._reset()

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            _log.warning(
                "circuit_breaker_opened",
                failure_count=self._failure_count,
            )

    def _reset(self):
        self._failure_count = 0
        self._state = "closed"


class ModelFallbackChain:
    """
    模型降级链

    当主模型不可用时，自动降级到备用模型
    """

    def __init__(self, models: list[dict]):
        """
        models: [{"model": "gpt-4o", "provider": "openai"}, {"model": "gpt-4o-mini", ...}]
        """
        self.models = models
        self._current_index = 0
        self._breakers: dict[str, CircuitBreaker] = {
            m["model"]: CircuitBreaker() for m in models
        }

    @property
    def current_model(self) -> dict:
        return self.models[self._current_index]

    def mark_failure(self, model: str):
        breaker = self._breakers.get(model)
        if breaker:
            breaker.record_failure()
            if not breaker.allow_request:
                self._fallback()

    def mark_success(self, model: str):
        breaker = self._breakers.get(model)
        if breaker:
            breaker.record_success()

    def _fallback(self):
        if self._current_index < len(self.models) - 1:
            old = self.models[self._current_index]["model"]
            self._current_index += 1
            new = self.models[self._current_index]["model"]
            _log.warning("model_fallback", from_model=old, to_model=new)

    def reset(self):
        self._current_index = 0
        for breaker in self._breakers.values():
            breaker._reset()


class PresetResponses:
    """
    预设话术库

    当 LLM 完全不可用时，使用预设话术响应用户
    """

    PRODUCT_SEARCH = [
        "您好，系统暂时繁忙。您可以直接在搜索栏输入关键词查找商品，或稍后再试。",
        "抱歉，AI 助手暂时无法响应。您可以浏览推荐商品列表，或稍后再咨询。",
    ]

    ORDER_QUERY = [
        "您好，订单查询系统暂时繁忙。请稍后再试，或联系客服邮箱获取帮助。",
        "抱歉，暂时无法查询订单。您可以稍后再试，或拨打客服热线。",
    ]

    RETURN_REQUEST = [
        "您好，退换货系统暂时繁忙。请记录您的订单号，稍后我们会优先处理。",
        "抱歉，退换货申请暂时无法处理。请保留好商品，我们会尽快恢复服务。",
    ]

    GENERAL = [
        "您好，AI 客服系统正在维护中，请稍后再试。感谢您的耐心！",
        "系统暂时繁忙，建议您稍后再咨询。如有紧急问题，请拨打客服热线。",
        "您好，当前咨询量大，AI 助手响应较慢。您可以先浏览帮助中心。",
    ]

    @classmethod
    def get_response(cls, intent: str = "general") -> str:
        import random
        responses = getattr(cls, intent.upper(), cls.GENERAL)
        return random.choice(responses)


class ServiceDegradationManager:
    """
    服务降级管理器

    管理各服务的降级状态和降级策略
    """

    def __init__(self):
        self._services: dict[str, ServiceState] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    def register_service(self, name: str):
        if name not in self._services:
            self._services[name] = ServiceState()

    def get_status(self, name: str) -> ServiceStatus:
        state = self._services.get(name)
        return state.status if state else ServiceStatus.UNAVAILABLE

    def mark_healthy(self, name: str):
        self.register_service(name)
        state = self._services[name]
        if state.status != ServiceStatus.HEALTHY:
            state.status = ServiceStatus.HEALTHY
            state.consecutive_failures = 0
            state.last_check = time.time()
            _log.info("service_recovered", service=name)
            self._notify(name, "recovered")

    def mark_degraded(self, name: str, reason: str = ""):
        self.register_service(name)
        state = self._services[name]
        state.status = ServiceStatus.DEGRADED
        state.consecutive_failures += 1
        state.last_error = reason
        state.last_check = time.time()
        _log.warning("service_degraded", service=name, reason=reason)
        self._notify(name, "degraded")

    def mark_unavailable(self, name: str, reason: str = ""):
        self.register_service(name)
        state = self._services[name]
        state.status = ServiceStatus.UNAVAILABLE
        state.consecutive_failures += 1
        state.last_error = reason
        state.last_check = time.time()
        _log.error("service_unavailable", service=name, reason=reason)
        self._notify(name, "unavailable")

    def on_status_change(self, service: str, callback: Callable):
        if service not in self._callbacks:
            self._callbacks[service] = []
        self._callbacks[service].append(callback)

    def _notify(self, service: str, event: str):
        for cb in self._callbacks.get(service, []):
            try:
                cb(service, event)
            except Exception:
                pass

    def get_all_status(self) -> dict[str, ServiceStatus]:
        return {name: s.status for name, s in self._services.items()}


async def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
) -> Any:
    """
    指数退避重试

    Args:
        func: 要执行的异步函数
        config: 重试配置
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试时的回调
    """
    cfg = config or RetryConfig()
    last_exception = None

    for attempt in range(cfg.max_attempts):
        try:
            return await func()
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt >= cfg.max_attempts - 1:
                raise

            delay = min(
                cfg.base_delay * (cfg.exponential_base ** attempt),
                cfg.max_delay,
            )
            if cfg.jitter:
                import random
                delay *= 0.5 + random.random()

            _log.warning(
                "retry_attempt",
                attempt=attempt + 1,
                max_attempts=cfg.max_attempts,
                delay=round(delay, 2),
                error=str(exc),
            )

            if on_retry:
                on_retry(attempt + 1, exc)

            await asyncio.sleep(delay)

    raise last_exception


# 全局实例
degradation_manager = ServiceDegradationManager()

llm_fallback_chain = ModelFallbackChain([
    {"model": "gpt-4o", "provider": "openai"},
    {"model": "gpt-4o-mini", "provider": "openai"},
    {"model": "qwen2:7b", "provider": "ollama"},
])
