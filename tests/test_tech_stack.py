"""
Tests for new tech stack modules:
- LangGraph workflow
- Multi-Agent supervisor
- LangSmith integration
- LiteLLM router
- FastAPI server
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── LangGraph Workflow ────────────────────────────────────────────────────────

class TestLangGraphWorkflow:

    def test_classify_intent_product(self):
        from graph.workflow import classify_intent, Intent
        result = classify_intent("推荐一款商品")
        assert result == Intent.PRODUCT

    def test_classify_intent_order(self):
        from graph.workflow import classify_intent, Intent
        result = classify_intent("我的订单到哪了")
        assert result == Intent.ORDER

    def test_classify_intent_support(self):
        from graph.workflow import classify_intent, Intent
        result = classify_intent("你好，我需要帮助")
        assert result == Intent.SUPPORT

    def test_classify_intent_unknown(self):
        from graph.workflow import classify_intent, Intent
        result = classify_intent("苹果香蕉橘子")
        assert result == Intent.UNKNOWN

    def test_build_workflow(self):
        from graph.workflow import build_workflow
        graph = build_workflow()
        assert graph is not None

    def test_get_graph_singleton(self):
        from graph.workflow import get_graph
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2

    def test_route_by_intent_product(self):
        from graph.workflow import route_by_intent, Intent, AgentState
        state = AgentState(messages=[], intent=Intent.PRODUCT)
        assert route_by_intent(state) == "product_agent"

    def test_route_by_intent_order(self):
        from graph.workflow import route_by_intent, Intent, AgentState
        state = AgentState(messages=[], intent=Intent.ORDER)
        assert route_by_intent(state) == "order_agent"

    def test_route_by_intent_support(self):
        from graph.workflow import route_by_intent, Intent, AgentState
        state = AgentState(messages=[], intent=Intent.SUPPORT)
        assert route_by_intent(state) == "support_agent"

    def test_route_by_intent_unknown(self):
        from graph.workflow import route_by_intent, Intent, AgentState
        state = AgentState(messages=[], intent=Intent.UNKNOWN)
        assert route_by_intent(state) == "response"


# ─── Multi-Agent Supervisor ─────────────────────────────────────────────────────

class TestMultiAgent:

    def test_agent_role_enum(self):
        from agent.multi_agent import AgentRole
        assert AgentRole.PRODUCT.value == "product"
        assert AgentRole.ORDER.value == "order"
        assert AgentRole.SUPPORT.value == "support"

    def test_supervisor_select_agent_product(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        role = sup.select_agent("推荐一款好用的商品")
        assert role == AgentRole.PRODUCT

    def test_supervisor_select_agent_order(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        role = sup.select_agent("查一下订单状态")
        assert role == AgentRole.ORDER

    def test_supervisor_select_agent_support(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        role = sup.select_agent("我要投诉")
        assert role == AgentRole.SUPPORT

    def test_supervisor_default_to_support(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        role = sup.select_agent("今天天气不错")
        assert role == AgentRole.SUPPORT

    def test_agent_result_dataclass(self):
        from agent.multi_agent import AgentResult, AgentRole
        result = AgentResult(
            role=AgentRole.PRODUCT,
            response="找到了3件商品",
            tools_used=["search_products"],
            confidence=0.9,
        )
        assert result.role == AgentRole.PRODUCT
        assert result.confidence == 0.9

    def test_get_agent_instructions(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        instructions = sup.get_agent_instructions(AgentRole.PRODUCT)
        assert "商品" in instructions

    @pytest.mark.asyncio
    async def test_dispatch_product(self):
        from agent.multi_agent import Supervisor, AgentRole
        sup = Supervisor()
        result = await sup.dispatch("推荐一款商品")
        assert result.role == AgentRole.PRODUCT


# ─── LangSmith Integration ──────────────────────────────────────────────────────

class TestLangSmithIntegration:

    def test_tracing_callback_handler(self):
        from utils.langsmith_integration import TracingCallbackHandler
        handler = TracingCallbackHandler()
        assert hasattr(handler, "on_llm_start")
        assert hasattr(handler, "on_tool_start")

    def test_tracing_records_traces(self):
        from utils.langsmith_integration import TracingCallbackHandler
        handler = TracingCallbackHandler()
        handler.on_llm_start(model="gpt-4o", prompt="hello")
        handler.on_llm_end(response="hi", tokens=10)
        assert len(handler.get_traces()) == 2

    def test_tracing_flush(self):
        from utils.langsmith_integration import TracingCallbackHandler
        handler = TracingCallbackHandler()
        handler.on_llm_start(model="gpt-4o", prompt="test")
        count = handler.flush()
        assert count == 1
        assert len(handler.get_traces()) == 0

    def test_cost_tracker_record(self):
        from utils.langsmith_integration import CostTracker
        tracker = CostTracker()
        tracker.record("gpt-4o", input_tokens=100, output_tokens=50)
        summary = tracker.summary()
        assert summary["total_calls"] == 1

    def test_cost_tracker_budget(self):
        from utils.langsmith_integration import CostTracker
        tracker = CostTracker(daily_budget_usd=0.001)
        tracker.record("gpt-4o", input_tokens=100000, output_tokens=50000)
        summary = tracker.summary()
        assert summary["total_cost_usd"] > 0

    def test_eval_harness_has_cases(self):
        from utils.langsmith_integration import EvaluationHarness
        harness = EvaluationHarness()
        assert len(harness._cases) == 8

    def test_model_costs_dict(self):
        from utils.langsmith_integration import MODEL_COSTS
        assert "gpt-4o" in MODEL_COSTS
        assert "gpt-4o-mini" in MODEL_COSTS


# ─── LiteLLM Router ─────────────────────────────────────────────────────────────

class TestLiteLLMRouter:

    def test_model_tier_enum(self):
        from utils.litellm_router import ModelTier
        assert ModelTier.SIMPLE.value == "simple"
        assert ModelTier.STANDARD.value == "standard"
        assert ModelTier.ADVANCED.value == "advanced"

    def test_classify_complexity_simple(self):
        from utils.litellm_router import LiteLLMRouter, ModelTier
        r = LiteLLMRouter()
        tier = r.classify_complexity("你好")
        assert tier == ModelTier.SIMPLE

    def test_classify_complexity_advanced(self):
        from utils.litellm_router import LiteLLMRouter, ModelTier
        r = LiteLLMRouter()
        tier = r.classify_complexity("请帮我分析这个复杂的投诉问题")
        assert tier == ModelTier.ADVANCED

    def test_classify_complexity_standard_default(self):
        from utils.litellm_router import LiteLLMRouter, ModelTier
        r = LiteLLMRouter()
        tier = r.classify_complexity("我想买一个手机壳")
        assert tier == ModelTier.STANDARD

    def test_select_model_returns_tuple(self):
        from utils.litellm_router import LiteLLMRouter, ModelTier
        r = LiteLLMRouter()
        model, tier = r.select_model("你好")
        assert model == "gpt-4o-mini"
        assert tier == ModelTier.SIMPLE

    def test_model_routing_has_fallback(self):
        from utils.litellm_router import MODEL_ROUTING, ModelTier
        config = MODEL_ROUTING[ModelTier.SIMPLE]
        assert "fallback" in config

    def test_ollama_in_costs(self):
        from utils.litellm_router import MODEL_COSTS_PER_1M
        assert "ollama/qwen2:7b" in MODEL_COSTS_PER_1M
        assert MODEL_COSTS_PER_1M["ollama/qwen2:7b"]["input"] == 0.0

    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        from utils.litellm_router import LiteLLMRouter
        r = LiteLLMRouter()
        resp = await r.chat("你好")
        assert resp.content
        assert resp.model
        assert resp.tier

    def test_usage_summary(self):
        from utils.litellm_router import LiteLLMRouter
        r = LiteLLMRouter()
        summary = r.usage_summary()
        assert "total_requests" in summary
        assert "total_cost_usd" in summary


# ─── FastAPI Server ─────────────────────────────────────────────────────────────

class TestFastAPIServer:

    def test_app_creation(self):
        from api.server import app
        assert app is not None
        assert app.title == "ShopMind AI — E-commerce Customer Service API"

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")

    def test_metrics_endpoint(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "counters" in data

    def test_cost_endpoint(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.get("/api/cost")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data

    def test_traces_endpoint(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.get("/api/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data

    def test_session_not_found(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.get("/api/session/nonexistent")
        assert resp.status_code == 404

    def test_chat_endpoint(self):
        from fastapi.testclient import TestClient
        from api.server import app
        client = TestClient(app)
        resp = client.post("/api/chat", json={"message": "推荐一款商品"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "intent" in data
        assert "session_id" in data
