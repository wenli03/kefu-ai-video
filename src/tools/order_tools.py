"""
Order Tools for E-commerce Customer Service

Order status, tracking, returns, and coupon management.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logging import SessionLogger

_log = SessionLogger("tools.order")


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNING = "returning"
    RETURNED = "returned"


@dataclass
class OrderItem:
    id: str
    product_id: str
    product_name: str
    quantity: int
    price: float


@dataclass
class Order:
    id: str
    customer_id: str
    items: list[OrderItem]
    status: OrderStatus
    total: float
    created_at: datetime
    shipping_address: str
    tracking_number: str = ""
    carrier: str = ""


class OrderTools:

    def __init__(self) -> None:
        self._orders_db: dict[str, Order] = self._load_sample_orders()
        self._coupons_db: dict[str, dict] = self._load_sample_coupons()

    def _load_sample_orders(self) -> dict[str, Order]:
        return {
            "ORD20240101001": Order(
                id="ORD20240101001", customer_id="C001",
                items=[
                    OrderItem("I001", "P001", "智能蓝牙耳机 Pro", 1, 299.00),
                    OrderItem("I002", "P003", "保温杯 大容量", 2, 89.00),
                ],
                status=OrderStatus.SHIPPED, total=477.00,
                created_at=datetime(2024, 1, 1, 10, 30),
                shipping_address="北京市朝阳区xxx路xxx号",
                tracking_number="SF1234567890", carrier="顺丰速运",
            ),
            "ORD20240102002": Order(
                id="ORD20240102002", customer_id="C001",
                items=[OrderItem("I003", "P002", "运动跑鞋 飞翼系列", 1, 459.00)],
                status=OrderStatus.PAID, total=459.00,
                created_at=datetime(2024, 1, 2, 14, 20),
                shipping_address="北京市朝阳区xxx路xxx号",
            ),
        }

    def _load_sample_coupons(self) -> dict[str, dict]:
        return {
            "NEW20": {"code": "NEW20", "name": "新人专享", "discount": 20,
                      "min_order": 99, "valid_until": "2024-12-31", "used": False},
            "DIGI80": {"code": "DIGI80", "name": "数码狂欢节", "discount": 80,
                       "min_order": 500, "category": "数码", "valid_until": "2024-03-31", "used": False},
        }

    async def query_order_status(self, order_id: str) -> str:
        order = self._orders_db.get(order_id)
        if not order:
            _log.info("order_not_found", order_id=order_id)
            return json.dumps({"error": "订单不存在", "order_id": order_id,
                               "suggestion": "请检查订单号是否正确"}, ensure_ascii=False)

        status_text = {
            OrderStatus.PENDING: "待付款", OrderStatus.PAID: "待发货",
            OrderStatus.SHIPPED: "已发货", OrderStatus.DELIVERED: "已签收",
            OrderStatus.CANCELLED: "已取消", OrderStatus.RETURNING: "退货中",
            OrderStatus.RETURNED: "已退货",
        }

        _log.info("order_queried", order_id=order_id, status=order.status.value)
        return json.dumps({
            "order_id": order.id, "status": status_text.get(order.status, order.status.value),
            "total": order.total, "items_count": len(order.items),
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
            "shipping_address": order.shipping_address[:20] + "...",
            "items": [{"name": i.product_name, "quantity": i.quantity, "price": i.price} for i in order.items],
        }, ensure_ascii=False)

    async def get_tracking_info(self, order_id: str) -> str:
        order = self._orders_db.get(order_id)
        if not order:
            return json.dumps({"error": "订单不存在", "order_id": order_id}, ensure_ascii=False)

        if order.status != OrderStatus.SHIPPED:
            return json.dumps({"order_id": order_id, "status": "暂未发货",
                               "message": "您的订单尚未发货，请耐心等待"}, ensure_ascii=False)

        tracking_events = [
            {"time": "2024-01-02 08:00", "status": "包裹已揽收", "location": "北京朝阳"},
            {"time": "2024-01-02 14:00", "status": "运输中", "location": "北京转运中心"},
            {"time": "2024-01-03 06:00", "status": "运输中", "location": "上海转运中心"},
            {"time": "2024-01-03 10:00", "status": "派送中", "location": "上海浦东"},
        ]

        _log.info("tracking_queried", order_id=order_id, carrier=order.carrier)
        return json.dumps({
            "order_id": order_id, "carrier": order.carrier,
            "tracking_number": order.tracking_number, "status": "运输中",
            "estimated_delivery": "预计明天送达", "tracking_events": tracking_events,
        }, ensure_ascii=False)

    async def initiate_return(self, order_id: str, item_ids: str, reason: str) -> str:
        order = self._orders_db.get(order_id)
        if not order:
            return json.dumps({"error": "订单不存在", "order_id": order_id}, ensure_ascii=False)

        if order.status not in [OrderStatus.DELIVERED, OrderStatus.SHIPPED]:
            _log.warning("return_rejected", order_id=order_id, status=order.status.value)
            return json.dumps({
                "error": "当前订单状态不支持退货", "order_id": order_id,
                "current_status": order.status.value, "suggestion": "请在签收后7天内申请退货",
            }, ensure_ascii=False)

        item_list = [i.strip() for i in item_ids.split(",")]
        _log.info("return_initiated", order_id=order_id, items=item_list, reason=reason)

        return json.dumps({
            "return_id": f"RET{order_id}", "order_id": order_id,
            "items": item_list, "reason": reason, "status": "待审核",
            "message": "退货申请已提交，预计1-2个工作日内审核",
            "next_steps": ["等待审核通过", "按指引寄回商品", "商家收货后退款"],
        }, ensure_ascii=False)

    async def check_return_policy(self, product_category: str = "") -> str:
        policies = {
            "default": {
                "return_days": 7, "exchange_days": 15,
                "conditions": ["商品未经使用", "包装完好", "附件齐全"],
                "exceptions": ["定制商品", "贴身衣物", "食品类"],
            },
            "数码": {
                "return_days": 7, "exchange_days": 15,
                "conditions": ["商品未经使用", "包装完好", "配件齐全", "激活后不支持无理由退货"],
            },
            "服装": {
                "return_days": 7, "exchange_days": 30,
                "conditions": ["未洗涤", "未穿着外出", "吊牌完好"],
            },
        }
        policy = policies.get(product_category, policies["default"])
        return json.dumps({
            "category": product_category or "通用", "policy": policy,
            "customer_service_note": "如有质量问题，可随时联系客服处理",
        }, ensure_ascii=False)

    async def apply_coupon(self, coupon_code: str, order_id: str = "") -> str:
        coupon = self._coupons_db.get(coupon_code.upper())
        if not coupon:
            _log.info("coupon_not_found", code=coupon_code)
            return json.dumps({"error": "优惠券不存在", "code": coupon_code}, ensure_ascii=False)

        if coupon.get("used"):
            _log.info("coupon_already_used", code=coupon_code)
            return json.dumps({"error": "优惠券已使用", "code": coupon_code}, ensure_ascii=False)

        _log.info("coupon_applied", code=coupon_code, discount=coupon["discount"])
        return json.dumps({
            "code": coupon["code"], "name": coupon["name"], "discount": coupon["discount"],
            "min_order": coupon["min_order"], "valid_until": coupon["valid_until"],
            "status": "可用", "message": f"满{coupon['min_order']}元可减{coupon['discount']}元",
        }, ensure_ascii=False)
