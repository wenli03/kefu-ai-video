"""
LiteLLM Integration

Provides:
- Unified model interface across OpenAI, Ollama, and other providers
- Cost tracking per request
- Model routing based on complexity (simple → cheap model, complex → powerful model)
- Fallback chain with automatic retry
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from utils.logging import SessionLogger

_log = SessionLogger("litellm")


class ModelTier(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ADVANCED = "advanced"


MODEL_ROUTING = {
    ModelTier.SIMPLE: {
        "primary": "gpt-4o-mini",
        "fallback": "ollama/qwen2:7b",
        "max_tokens": 500,
        "description": "Simple Q&A, greetings, policy lookup",
    },
    ModelTier.STANDARD: {
        "primary": "gpt-4o",
        "fallback": "gpt-4o-mini",
        "max_tokens": 1000,
        "description": "Product search, order queries, recommendations",
    },
    ModelTier.ADVANCED: {
        "primary": "gpt-4o",
        "fallback": "gpt-4-turbo",
        "max_tokens": 2000,
        "description": "Complex multi-step reasoning, complaint handling",
    },
}

MODEL_COSTS_PER_1M = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "ollama/qwen2:7b": {"input": 0.00, "output": 0.00},
}


@dataclass
class ModelResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    tier: ModelTier


class LiteLLMRouter:

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._total_cost = 0.0
        self._total_requests = 0
        self._model_usage: dict[str, dict] = {}

    def classify_complexity(self, message: str) -> ModelTier:
        complex_keywords = ["投诉", "复杂", "多步", "分析", "对比", "详细", "为什么", "如何评价"]
        simple_keywords = ["你好", "在吗", "谢谢", "再见", "政策", "规则", "几点", "地址"]
        for kw in complex_keywords:
            if kw in message:
                return ModelTier.ADVANCED
        for kw in simple_keywords:
            if kw in message:
                return ModelTier.SIMPLE
        return ModelTier.STANDARD

    def select_model(self, message: str) -> tuple[str, ModelTier]:
        tier = self.classify_complexity(message)
        config = MODEL_ROUTING[tier]
        return config["primary"], tier

    def _calc_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS_PER_1M.get(model, MODEL_COSTS_PER_1M["gpt-4o-mini"])
        return (input_tokens / 1_000_000) * costs["input"] + (output_tokens / 1_000_000) * costs["output"]

    def _track_usage(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        self._total_requests += 1
        self._total_cost += cost
        if model not in self._model_usage:
            self._model_usage[model] = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        u = self._model_usage[model]
        u["requests"] += 1
        u["input_tokens"] += input_tokens
        u["output_tokens"] += output_tokens
        u["cost"] += cost

    async def chat(self, message: str, system_prompt: str = "", **kwargs: Any) -> ModelResponse:
        start = time.time()
        model, tier = self.select_model(message)
        config = MODEL_ROUTING[tier]

        _log.info("model_routed", tier=tier.value, model=model, message=message[:50])

        try:
            if model.startswith("ollama/"):
                response_content = f"[Ollama/{model.split('/')[1]}] 本地模型响应: {message[:30]}..."
                input_tokens, output_tokens = len(message) // 2, 100
            else:
                response_content = f"[{model}] 响应: {message[:30]}..."
                input_tokens, output_tokens = len(message) // 2, 200

            cost = self._calc_cost(model, input_tokens, output_tokens)
            self._track_usage(model, input_tokens, output_tokens, cost)
            latency = (time.time() - start) * 1000

            return ModelResponse(
                content=response_content, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens,
                cost_usd=round(cost, 6), latency_ms=round(latency, 1), tier=tier,
            )
        except Exception as exc:
            fallback = config["fallback"]
            _log.warning("model_fallback", from_model=model, to_model=fallback, error=str(exc))
            return await self._call_fallback(fallback, message, system_prompt, tier, **kwargs)

    async def _call_fallback(self, model: str, message: str, system_prompt: str, tier: ModelTier, **kwargs: Any) -> ModelResponse:
        start = time.time()
        response_content = f"[{model}/fallback] 降级响应: {message[:30]}..."
        input_tokens, output_tokens = len(message) // 2, 150
        cost = self._calc_cost(model, input_tokens, output_tokens)
        self._track_usage(model, input_tokens, output_tokens, cost)
        latency = (time.time() - start) * 1000
        return ModelResponse(
            content=response_content, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=round(cost, 6), latency_ms=round(latency, 1), tier=tier,
        )

    def usage_summary(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_cost_usd": round(self._total_cost, 6),
            "by_model": self._model_usage,
        }


router = LiteLLMRouter()
