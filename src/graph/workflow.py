"""
LangGraph Workflow Orchestration

State graph for routing user messages to specialized agents:
  START → Router → [ProductAgent | OrderAgent | SupportAgent] → Response → END

Uses LangGraph StateGraph with conditional edges for dynamic routing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Literal, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from utils.logging import SessionLogger

_log = SessionLogger("graph")


class Intent(str, Enum):
    PRODUCT = "product"
    ORDER = "order"
    SUPPORT = "support"
    UNKNOWN = "unknown"


@dataclass
class AgentState:
    messages: Annotated[Sequence[BaseMessage], add_messages] = field(default_factory=list)
    intent: Intent = Intent.UNKNOWN
    current_agent: str = ""
    tool_results: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ─── Intent Router ───────────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.PRODUCT: ["商品", "产品", "价格", "库存", "推荐", "多少钱", "有没有", "规格", "促销", "优惠", "搜索", "找"],
    Intent.ORDER: ["订单", "物流", "快递", "退货", "退换", "发货", "运单", "退款", "售后", "单号"],
    Intent.SUPPORT: ["你好", "帮助", "怎么", "如何", "问题", "投诉", "人工", "客服"],
}


def classify_intent(message: str) -> Intent:
    scores: dict[Intent, int] = {k: 0 for k in Intent}
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in message:
                scores[intent] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Intent.UNKNOWN


async def router_node(state: AgentState) -> dict:
    last_msg = state.messages[-1] if state.messages else ""
    text = last_msg.content if isinstance(last_msg, (HumanMessage, AIMessage)) else str(last_msg)
    intent = classify_intent(text)
    _log.info("intent_routed", intent=intent.value, text=text[:50])
    return {"intent": intent}


def route_by_intent(state: AgentState) -> Literal["product_agent", "order_agent", "support_agent", "response"]:
    if state.intent == Intent.PRODUCT:
        return "product_agent"
    if state.intent == Intent.ORDER:
        return "order_agent"
    if state.intent == Intent.SUPPORT:
        return "support_agent"
    return "response"


# ─── Specialized Agent Nodes ─────────────────────────────────────────────────

async def product_agent_node(state: AgentState) -> dict:
    _log.info("agent_activated", agent="product", intent=state.intent.value)
    return {"current_agent": "product_agent", "metadata": {"agent": "product"}}


async def order_agent_node(state: AgentState) -> dict:
    _log.info("agent_activated", agent="order", intent=state.intent.value)
    return {"current_agent": "order_agent", "metadata": {"agent": "order"}}


async def support_agent_node(state: AgentState) -> dict:
    _log.info("agent_activated", agent="support", intent=state.intent.value)
    return {"current_agent": "support_agent", "metadata": {"agent": "support"}}


async def response_node(state: AgentState) -> dict:
    _log.info("response_generated", agent=state.current_agent or "router")
    return {"metadata": {"response_ready": True}}


# ─── Graph Builder ───────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("product_agent", product_agent_node)
    workflow.add_node("order_agent", order_agent_node)
    workflow.add_node("support_agent", support_agent_node)
    workflow.add_node("response", response_node)

    workflow.add_edge(START, "router")
    workflow.add_conditional_edges("router", route_by_intent)
    workflow.add_edge("product_agent", "response")
    workflow.add_edge("order_agent", "response")
    workflow.add_edge("support_agent", "response")
    workflow.add_edge("response", END)

    return workflow.compile()


_graph_instance = None


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_workflow()
    return _graph_instance
