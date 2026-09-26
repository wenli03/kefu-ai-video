"""
E-commerce Support Agent

Chinese e-commerce customer service agent with product inquiry,
order service, return/exchange, and promotion tools.

P0 生产就绪：
- 输入验证与清洗
- 工具调用指标采集
- 结构化错误处理
- 敏感信息脱敏
"""

import time
from typing import TYPE_CHECKING

from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool, ChatContext

from utils.logging import SessionLogger, AgentError
from utils.security import validate_input, mask_sensitive_info, sanitize_text
from utils.monitoring import metrics as metrics_collector
from utils.resilience import degradation_manager

if TYPE_CHECKING:
    from tools.product_tools import ProductTools
    from tools.order_tools import OrderTools


SYSTEM_INSTRUCTIONS = """你是一位专业的电商AI视频客服助手，名叫小智。你的职责是：

1. **商品咨询**：帮助客户了解商品详情、规格、价格、库存等信息
2. **购物推荐**：根据客户需求推荐合适的商品
3. **订单服务**：查询订单状态、物流信息、配送时间
4. **售后支持**：处理退换货、投诉、质量问题等售后问题
5. **促销活动**：介绍当前优惠活动、优惠券使用等

沟通原则：
- 使用友好、专业的语气
- 回答简洁明了，避免冗长
- 遇到复杂问题及时转接人工客服
- 保护客户隐私，不主动询问敏感信息
- 对于不确定的信息，诚实告知并承诺核实

你必须使用中文与客户交流。
"""


class EcommerceSupportAgent(Agent):

    def __init__(
        self,
        product_tools: "ProductTools",
        order_tools: "OrderTools",
        session_log: SessionLogger | None = None,
    ) -> None:
        super().__init__(
            instructions=SYSTEM_INSTRUCTIONS,
            chat_ctx=ChatContext.empty(),
        )
        self._product_tools = product_tools
        self._order_tools = order_tools
        self._log = session_log or SessionLogger("agent")

    async def on_enter(self) -> None:
        self.session.generate_reply(
            instructions="向客户问好，介绍自己是AI购物助手小智，询问需要什么帮助。"
        )

    def _validate_and_sanitize(self, text: str, field_name: str = "") -> str:
        ok, msg = validate_input(text)
        if not ok:
            self._log.warning("input_validation_failed", field=field_name, reason=msg)
            raise ValueError(msg)
        return sanitize_text(text)

    def _record_tool_call(self, tool_name: str, success: bool, latency_ms: float):
        metrics_collector.increment(f"tool_{tool_name}_calls")
        if not success:
            metrics_collector.increment(f"tool_{tool_name}_errors")
        metrics_collector.observe(f"tool_{tool_name}_latency", latency_ms)
        metrics_collector.increment("tool_calls_total")

    @function_tool
    async def search_products(
        self, context: RunContext, query: str, category: str = "", max_results: int = 5,
    ) -> str:
        """搜索商品。当客户询问某类商品或想找特定商品时调用。

        Args:
            query: 搜索关键词，如"运动鞋"、"手机壳"
            category: 商品类目，如"服装"、"数码"、"家居"
            max_results: 最多返回结果数
        """
        start = time.time()
        try:
            query = self._validate_and_sanitize(query, "search_query")
            result = await self._product_tools.search_products(query, category, max_results)
            latency = (time.time() - start) * 1000
            self._record_tool_call("search_products", True, latency)
            self._log.info("tool_search_products", query=query, category=category, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("search_products", False, latency)
            raise AgentError.wrap(exc, message="商品搜索失败", step="search_products", fix="请稍后重试或换个关键词")

    @function_tool
    async def get_product_details(self, context: RunContext, product_id: str) -> str:
        """获取商品详细信息。当客户询问某个具体商品的详情时调用。

        Args:
            product_id: 商品ID
        """
        start = time.time()
        try:
            product_id = self._validate_and_sanitize(product_id, "product_id")
            result = await self._product_tools.get_product_details(product_id)
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_product_details", True, latency)
            self._log.info("tool_product_details", product_id=product_id, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_product_details", False, latency)
            raise AgentError.wrap(exc, message="获取商品详情失败", step="get_product_details")

    @function_tool
    async def check_inventory(self, context: RunContext, product_id: str, sku: str = "") -> str:
        """查询商品库存。当客户询问是否有货时调用。

        Args:
            product_id: 商品ID
            sku: 具体SKU编号（如颜色/尺码）
        """
        start = time.time()
        try:
            product_id = self._validate_and_sanitize(product_id, "product_id")
            result = await self._product_tools.check_inventory(product_id, sku)
            latency = (time.time() - start) * 1000
            self._record_tool_call("check_inventory", True, latency)
            self._log.info("tool_check_inventory", product_id=product_id, sku=sku, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("check_inventory", False, latency)
            raise AgentError.wrap(exc, message="库存查询失败", step="check_inventory")

    @function_tool
    async def get_recommendations(
        self, context: RunContext, preference: str, budget_min: float = 0, budget_max: float = 0,
    ) -> str:
        """根据客户偏好推荐商品。

        Args:
            preference: 客户偏好描述，如"轻便跑鞋"、"送女朋友的礼物"
            budget_min: 最低预算（元）
            budget_max: 最高预算（元）
        """
        start = time.time()
        try:
            preference = self._validate_and_sanitize(preference, "preference")
            result = await self._product_tools.get_recommendations(preference, budget_min, budget_max)
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_recommendations", True, latency)
            self._log.info("tool_recommendations", preference=preference, budget={"min": budget_min, "max": budget_max}, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_recommendations", False, latency)
            raise AgentError.wrap(exc, message="推荐失败", step="get_recommendations")

    @function_tool
    async def query_order_status(self, context: RunContext, order_id: str) -> str:
        """查询订单状态。当客户询问订单进度时调用。

        Args:
            order_id: 订单号
        """
        start = time.time()
        try:
            order_id = self._validate_and_sanitize(order_id, "order_id")
            result = await self._order_tools.query_order_status(order_id)
            latency = (time.time() - start) * 1000
            self._record_tool_call("query_order_status", True, latency)
            self._log.info("tool_order_status", order_id=order_id, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("query_order_status", False, latency)
            raise AgentError.wrap(exc, message="订单查询失败", step="query_order_status")

    @function_tool
    async def get_tracking_info(self, context: RunContext, order_id: str) -> str:
        """获取物流追踪信息。当客户询问快递到哪了时调用。

        Args:
            order_id: 订单号
        """
        start = time.time()
        try:
            order_id = self._validate_and_sanitize(order_id, "order_id")
            result = await self._order_tools.get_tracking_info(order_id)
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_tracking_info", True, latency)
            self._log.info("tool_tracking", order_id=order_id, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_tracking_info", False, latency)
            raise AgentError.wrap(exc, message="物流查询失败", step="get_tracking_info")

    @function_tool
    async def initiate_return(
        self, context: RunContext, order_id: str, item_ids: str, reason: str,
    ) -> str:
        """发起退换货申请。

        Args:
            order_id: 订单号
            item_ids: 要退换的商品ID，逗号分隔
            reason: 退换原因
        """
        start = time.time()
        try:
            order_id = self._validate_and_sanitize(order_id, "order_id")
            reason = mask_sensitive_info(reason)
            result = await self._order_tools.initiate_return(order_id, item_ids, reason)
            latency = (time.time() - start) * 1000
            self._record_tool_call("initiate_return", True, latency)
            self._log.info("tool_return", order_id=order_id, reason=reason, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("initiate_return", False, latency)
            raise AgentError.wrap(exc, message="退货申请失败", step="initiate_return", fix="请确认订单号和商品ID是否正确")

    @function_tool
    async def check_return_policy(self, context: RunContext, product_category: str = "") -> str:
        """查询退换货政策。

        Args:
            product_category: 商品类目（不同类目可能有不同政策）
        """
        start = time.time()
        try:
            result = await self._order_tools.check_return_policy(product_category)
            latency = (time.time() - start) * 1000
            self._record_tool_call("check_return_policy", True, latency)
            self._log.info("tool_return_policy", category=product_category, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("check_return_policy", False, latency)
            raise AgentError.wrap(exc, message="查询退换政策失败", step="check_return_policy")

    @function_tool
    async def get_current_promotions(self, context: RunContext, category: str = "") -> str:
        """获取当前促销活动信息。

        Args:
            category: 感兴趣的类目，留空获取全部活动
        """
        start = time.time()
        try:
            result = await self._product_tools.get_current_promotions(category)
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_current_promotions", True, latency)
            self._log.info("tool_promotions", category=category, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("get_current_promotions", False, latency)
            raise AgentError.wrap(exc, message="查询促销失败", step="get_current_promotions")

    @function_tool
    async def apply_coupon(self, context: RunContext, coupon_code: str, order_id: str = "") -> str:
        """使用优惠券。

        Args:
            coupon_code: 优惠券码
            order_id: 订单号（如已下单）
        """
        start = time.time()
        try:
            coupon_code = self._validate_and_sanitize(coupon_code, "coupon_code")
            result = await self._order_tools.apply_coupon(coupon_code, order_id)
            latency = (time.time() - start) * 1000
            self._record_tool_call("apply_coupon", True, latency)
            self._log.info("tool_coupon", code=coupon_code, order_id=order_id, latency_ms=round(latency, 1))
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_tool_call("apply_coupon", False, latency)
            raise AgentError.wrap(exc, message="优惠券使用失败", step="apply_coupon")
