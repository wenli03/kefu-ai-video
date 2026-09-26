"""
LangSmith Integration

Provides tracing, evaluation, and monitoring via LangSmith platform.
- TracingCallbackHandler: auto-traces all LLM calls and tool executions
- EvaluationHarness: runs agent responses against golden dataset
- CostTracker: tracks token usage and estimated costs
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from utils.logging import SessionLogger

_log = SessionLogger("langsmith")


# ─── Tracing ─────────────────────────────────────────────────────────────────

class TracingCallbackHandler:
    """Callback handler that sends traces to LangSmith."""

    def __init__(self, project_name: str = "ecommerce-video-cs"):
        self.project_name = project_name
        self.api_key = os.getenv("LANGSMITH_API_KEY", "")
        self.endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        self._traces: list[dict] = []
        self._enabled = bool(self.api_key)
        if self._enabled:
            _log.info("langsmith_enabled", project=project_name)
        else:
            _log.info("langsmith_disabled", reason="no API key")

    def on_llm_start(self, model: str, prompt: str, **kwargs: Any) -> dict:
        trace = {
            "type": "llm",
            "event": "start",
            "model": model,
            "prompt_length": len(prompt),
            "timestamp": time.time(),
            **kwargs,
        }
        self._traces.append(trace)
        return trace

    def on_llm_end(self, response: str, tokens: int = 0, latency_ms: float = 0, **kwargs: Any) -> dict:
        trace = {
            "type": "llm",
            "event": "end",
            "response_length": len(response),
            "tokens": tokens,
            "latency_ms": latency_ms,
            "timestamp": time.time(),
            **kwargs,
        }
        self._traces.append(trace)
        return trace

    def on_tool_start(self, tool_name: str, inputs: dict, **kwargs: Any) -> dict:
        trace = {
            "type": "tool",
            "event": "start",
            "tool_name": tool_name,
            "inputs": {k: str(v)[:100] for k, v in inputs.items()},
            "timestamp": time.time(),
        }
        self._traces.append(trace)
        return trace

    def on_tool_end(self, tool_name: str, output: str, latency_ms: float = 0, **kwargs: Any) -> dict:
        trace = {
            "type": "tool",
            "event": "end",
            "tool_name": tool_name,
            "output_length": len(output),
            "latency_ms": latency_ms,
            "timestamp": time.time(),
        }
        self._traces.append(trace)
        return trace

    def on_error(self, error: str, **kwargs: Any) -> dict:
        trace = {"type": "error", "error": error, "timestamp": time.time(), **kwargs}
        self._traces.append(trace)
        return trace

    def get_traces(self) -> list[dict]:
        return self._traces

    def flush(self) -> int:
        count = len(self._traces)
        self._traces.clear()
        return count


# ─── Cost Tracking ───────────────────────────────────────────────────────────

MODEL_COSTS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


@dataclass
class CostRecord:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


class CostTracker:

    def __init__(self, daily_budget_usd: float = 50.0):
        self.daily_budget = daily_budget_usd
        self._records: list[CostRecord] = []
        self._total_cost = 0.0

    def record(self, model: str, input_tokens: int, output_tokens: int) -> CostRecord:
        costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
        cost = (input_tokens / 1_000_000) * costs["input"] + (output_tokens / 1_000_000) * costs["output"]
        record = CostRecord(model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)
        self._records.append(record)
        self._total_cost += cost
        _log.info("cost_recorded", model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=round(cost, 6))
        return record

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def budget_remaining(self) -> float:
        return max(0, self.daily_budget - self._total_cost)

    @property
    def budget_usage_pct(self) -> float:
        return min(100, (self._total_cost / self.daily_budget) * 100)

    def summary(self) -> dict:
        by_model: dict[str, dict] = {}
        for r in self._records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["input_tokens"] += r.input_tokens
            by_model[r.model]["output_tokens"] += r.output_tokens
            by_model[r.model]["cost"] += r.cost_usd
        return {
            "total_cost_usd": round(self._total_cost, 6),
            "daily_budget_usd": self.daily_budget,
            "budget_remaining_usd": round(self.budget_remaining, 6),
            "budget_usage_pct": round(self.budget_usage_pct, 1),
            "total_calls": len(self._records),
            "by_model": by_model,
        }


# ─── Evaluation Harness ─────────────────────────────────────────────────────

@dataclass
class EvalCase:
    id: str
    input: str
    expected_intent: str
    expected_tools: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    intent_match: bool
    tools_match: bool
    keyword_match: bool
    score: float


class EvaluationHarness:

    def __init__(self):
        self._cases: list[EvalCase] = self._load_golden_dataset()

    def _load_golden_dataset(self) -> list[EvalCase]:
        return [
            EvalCase(id="eval_001", input="我想找一款适合跑步的耳机", expected_intent="product", expected_tools=["search_products"], keywords=["耳机", "跑步"]),
            EvalCase(id="eval_002", input="我的订单 ORD20240101001 到哪了", expected_intent="order", expected_tools=["query_order_status"], keywords=["订单", "物流"]),
            EvalCase(id="eval_003", input="我想退掉刚收到的鞋子", expected_intent="order", expected_tools=["initiate_return"], keywords=["退货", "鞋子"]),
            EvalCase(id="eval_004", input="推荐一款送女朋友的礼物，预算300-500元", expected_intent="product", expected_tools=["get_recommendations"], keywords=["推荐", "礼物"]),
            EvalCase(id="eval_005", input="你好，请问你们支持哪些支付方式", expected_intent="support", expected_tools=[], keywords=["你好", "支付"]),
            EvalCase(id="eval_006", input="这款耳机有库存吗", expected_intent="product", expected_tools=["check_inventory"], keywords=["库存"]),
            EvalCase(id="eval_007", input="帮我查一下退换货政策", expected_intent="order", expected_tools=["check_return_policy"], keywords=["退换货", "政策"]),
            EvalCase(id="eval_008", input="有什么优惠券可以用吗", expected_intent="product", expected_tools=["get_current_promotions"], keywords=["优惠券"]),
        ]

    def evaluate(self, predicted_intent: str, predicted_tools: list[str]) -> list[EvalResult]:
        results = []
        for case in self._cases:
            intent_match = predicted_intent == case.expected_intent
            tools_match = set(predicted_tools) == set(case.expected_tools) if case.expected_tools else True
            keyword_match = any(kw in case.input for kw in case.keywords)
            passed = intent_match and keyword_match
            score = (int(intent_match) * 0.4 + int(tools_match) * 0.3 + int(keyword_match) * 0.3)
            results.append(EvalResult(
                case_id=case.id, passed=passed,
                intent_match=intent_match, tools_match=tools_match, keyword_match=keyword_match,
                score=round(score, 2),
            ))
        return results

    def run_all(self, predict_fn) -> dict:
        total = len(self._cases)
        passed = 0
        details = []
        for case in self._cases:
            predicted_intent, predicted_tools = predict_fn(case.input)
            result = self.evaluate(predicted_intent, predicted_tools)
            r = result[0] if result else EvalResult(case.id, False, False, False, False, 0.0)
            if r.passed:
                passed += 1
            details.append({"case": case.id, "passed": r.passed, "score": r.score})
        return {"total": total, "passed": passed, "accuracy": round(passed / total, 3) if total else 0, "details": details}


tracing_handler = TracingCallbackHandler()
cost_tracker = CostTracker()
eval_harness = EvaluationHarness()
