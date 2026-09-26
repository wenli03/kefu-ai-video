"""
Product Tools for E-commerce Customer Service

Product search, details, inventory, recommendations via LangChain RAG.
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils.logging import SessionLogger, AgentError

if TYPE_CHECKING:
    from knowledge.rag_engine import RAGEngine

_log = SessionLogger("tools.product")


@dataclass
class Product:
    id: str
    name: str
    category: str
    price: float
    description: str
    specs: dict
    inventory: int
    images: list[str]


class ProductTools:

    def __init__(self, rag_engine: "RAGEngine") -> None:
        self._rag = rag_engine
        self._products_db: dict[str, Product] = self._load_sample_products()

    def _load_sample_products(self) -> dict[str, Product]:
        products = [
            Product(
                id="P001", name="智能蓝牙耳机 Pro", category="数码", price=299.00,
                description="高品质降噪蓝牙耳机，支持主动降噪，续航30小时",
                specs={"颜色": ["黑色", "白色"], "蓝牙版本": "5.3", "降噪": "主动降噪"},
                inventory=150, images=["https://placeholder.com/p001-1.jpg"],
            ),
            Product(
                id="P002", name="运动跑鞋 飞翼系列", category="服装", price=459.00,
                description="轻量化跑步鞋，透气网面，缓震科技",
                specs={"尺码": ["38", "39", "40", "41", "42", "43"], "颜色": ["黑灰", "蓝白"]},
                inventory=80, images=["https://placeholder.com/p002-1.jpg"],
            ),
            Product(
                id="P003", name="保温杯 大容量", category="家居", price=89.00,
                description="316不锈钢内胆，12小时保温，500ml容量",
                specs={"容量": "500ml", "材质": "316不锈钢", "颜色": ["银色", "黑色", "粉色"]},
                inventory=300, images=["https://placeholder.com/p003-1.jpg"],
            ),
            Product(
                id="P004", name="机械键盘 青轴", category="数码", price=349.00,
                description="87键紧凑布局，Cherry青轴，RGB背光",
                specs={"轴体": "青轴", "键数": "87", "连接": "有线USB"},
                inventory=60, images=["https://placeholder.com/p004-1.jpg"],
            ),
            Product(
                id="P005", name="瑜伽垫 加厚款", category="运动", price=128.00,
                description="TPE环保材质，8mm加厚，防滑纹理",
                specs={"厚度": "8mm", "材质": "TPE", "尺寸": "183x61cm"},
                inventory=200, images=["https://placeholder.com/p005-1.jpg"],
            ),
        ]
        return {p.id: p for p in products}

    async def search_products(self, query: str, category: str = "", max_results: int = 5) -> str:
        try:
            rag_results = await self._rag.search_products(query, category, max_results)
            if rag_results:
                _log.info("search", source="rag", query=query, count=len(rag_results))
                return json.dumps({"source": "rag", "query": query, "results": rag_results}, ensure_ascii=False)
        except AgentError:
            _log.warning("search_rag_fallback", query=query, reason="rag_unavailable")

        results = []
        query_lower = query.lower()
        for product in self._products_db.values():
            if category and product.category != category:
                continue
            if (query_lower in product.name.lower()
                    or query_lower in product.description.lower()
                    or query_lower in product.category.lower()):
                results.append({
                    "id": product.id, "name": product.name, "price": product.price,
                    "category": product.category, "description": product.description[:100] + "...",
                })
                if len(results) >= max_results:
                    break

        _log.info("search", source="keyword", query=query, count=len(results))
        return json.dumps({"source": "keyword", "query": query, "count": len(results), "results": results}, ensure_ascii=False)

    async def get_product_details(self, product_id: str) -> str:
        product = self._products_db.get(product_id)
        if not product:
            return json.dumps({"error": "商品不存在", "product_id": product_id}, ensure_ascii=False)

        return json.dumps({
            "id": product.id, "name": product.name, "category": product.category,
            "price": product.price, "description": product.description,
            "specs": product.specs, "inventory": product.inventory, "in_stock": product.inventory > 0,
        }, ensure_ascii=False)

    async def check_inventory(self, product_id: str, sku: str = "") -> str:
        product = self._products_db.get(product_id)
        if not product:
            return json.dumps({"error": "商品不存在", "product_id": product_id}, ensure_ascii=False)

        status = "有货" if product.inventory > 10 else "库存紧张" if product.inventory > 0 else "缺货"
        return json.dumps({
            "product_id": product_id, "product_name": product.name,
            "inventory": product.inventory, "status": status, "sku": sku or "全部规格",
        }, ensure_ascii=False)

    async def get_recommendations(self, preference: str, budget_min: float = 0, budget_max: float = 0) -> str:
        try:
            rag_results = await self._rag.get_recommendations(preference, budget_min, budget_max)
            if rag_results:
                _log.info("recommend", source="rag", preference=preference, count=len(rag_results))
                return json.dumps({
                    "source": "rag", "preference": preference,
                    "budget": {"min": budget_min, "max": budget_max}, "recommendations": rag_results,
                }, ensure_ascii=False)
        except AgentError:
            _log.warning("recommend_rag_fallback", preference=preference, reason="rag_unavailable")

        results = []
        for product in self._products_db.values():
            if budget_min > 0 and product.price < budget_min:
                continue
            if budget_max > 0 and product.price > budget_max:
                continue
            results.append({
                "id": product.id, "name": product.name, "price": product.price, "category": product.category,
            })

        _log.info("recommend", source="filter", preference=preference, count=len(results))
        return json.dumps({
            "source": "filter", "preference": preference,
            "budget": {"min": budget_min, "max": budget_max},
            "count": len(results), "recommendations": results[:5],
        }, ensure_ascii=False)

    async def get_current_promotions(self, category: str = "") -> str:
        promotions = [
            {"id": "PROMO001", "name": "新人专享", "description": "新用户首单立减20元",
             "condition": "订单满99元可用", "discount": "20元"},
            {"id": "PROMO002", "name": "数码狂欢节", "description": "数码品类满500减80",
             "condition": "仅限数码类目", "discount": "80元", "category": "数码"},
            {"id": "PROMO003", "name": "满减活动", "description": "全场满299减30",
             "condition": "全品类通用", "discount": "30元"},
        ]
        if category:
            promotions = [p for p in promotions if "category" not in p or p["category"] == category]

        return json.dumps({"promotions": promotions, "total": len(promotions)}, ensure_ascii=False)
