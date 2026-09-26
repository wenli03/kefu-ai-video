"""
Multi-Agent Supervisor System

Supervisor agent routes tasks to specialized sub-agents:
- ProductAgent: search, details, inventory, recommendations
- OrderAgent: order status, tracking, returns, coupons
- SupportAgent: general QA, policy, escalation

Each sub-agent has its own tool set and system prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from utils.logging import SessionLogger

_log = SessionLogger("multi_agent")


class AgentRole(str, Enum):
    PRODUCT = "product"
    ORDER = "order"
    SUPPORT = "support"


PRODUCT_INSTRUCTIONS = """你是电商商品专家。职责：
1. 搜索和推荐商品
2. 提供商品详情、规格、价格信息
3. 查询库存状态
4. 介绍促销活动
用中文回答，简洁专业。"""

ORDER_INSTRUCTIONS = """你是订单服务专家。职责：
1. 查询订单状态和物流信息
2. 处理退换货申请
3. 查询退换政策
4. 使用优惠券
用中文回答，准确高效。"""

SUPPORT_INSTRUCTIONS = """你是综合客服专家。职责：
1. 回答一般性问题
2. 提供购物指导
3. 处理投诉和建议
4. 必要时转接人工客服
用中文回答，友好耐心。"""


@dataclass
class AgentResult:
    role: AgentRole
    response: str
    tools_used: list[str] = field(default_factory=list)
    confidence: float = 1.0


class Supervisor:

    def __init__(self, product_tools: Any = None, order_tools: Any = None):
        self._product_tools = product_tools
        self._order_tools = order_tools
        self._agents: dict[AgentRole, dict] = {
            AgentRole.PRODUCT: {"instructions": PRODUCT_INSTRUCTIONS, "tools": self._product_tools},
            AgentRole.ORDER: {"instructions": ORDER_INSTRUCTIONS, "tools": self._order_tools},
            AgentRole.SUPPORT: {"instructions": SUPPORT_INSTRUCTIONS, "tools": None},
        }

    def select_agent(self, message: str) -> AgentRole:
        keywords = {
            AgentRole.PRODUCT: ["商品", "产品", "价格", "库存", "推荐", "多少钱", "有没有", "规格", "促销", "优惠", "搜索"],
            AgentRole.ORDER: ["订单", "物流", "快递", "退货", "退换", "发货", "运单", "退款", "售后", "单号"],
            AgentRole.SUPPORT: ["你好", "帮助", "怎么", "如何", "问题", "投诉", "人工", "客服"],
        }
        scores = {role: 0 for role in AgentRole}
        for role, kws in keywords.items():
            for kw in kws:
                if kw in message:
                    scores[role] += 1
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return AgentRole.SUPPORT
        return best

    async def dispatch(self, message: str) -> AgentResult:
        role = self.select_agent(message)
        agent_info = self._agents[role]
        _log.info("supervisor_dispatch", role=role.value, message=message[:50])

        if role == AgentRole.PRODUCT and self._product_tools:
            return AgentResult(role=role, response=f"[ProductAgent] 处理: {message}", tools_used=["search_products"])
        if role == AgentRole.ORDER and self._order_tools:
            return AgentResult(role=role, response=f"[OrderAgent] 处理: {message}", tools_used=["query_order_status"])
        return AgentResult(role=role, response=f"[SupportAgent] 处理: {message}")

    def get_agent_instructions(self, role: AgentRole) -> str:
        return self._agents[role]["instructions"]
