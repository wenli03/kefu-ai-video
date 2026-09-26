"""
E-commerce Data Collector

Scrapes product data from JD.com and Pinduoduo.
Includes rate limiting, error handling, and data normalization.

Note: This is a demo module. For production use, ensure compliance with
platform terms of service and robots.txt.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from utils.logging import SessionLogger

_log = SessionLogger("data_collector")
logger = logging.getLogger(__name__)


@dataclass
class CollectedProduct:
    """Normalized product data from e-commerce platforms."""
    source_id: str
    platform: str  # "jd" or "pinduoduo"
    name: str
    category: str
    price: float
    original_price: float
    description: str
    specs: dict
    sales_count: int
    rating: float
    url: str
    collected_at: str


class DataCollector:
    """Base collector for e-commerce platforms."""

    def __init__(self, rate_limit: float = 1.0) -> None:
        self._rate_limit = rate_limit
        self._last_request = 0.0
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )

    async def _respect_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._rate_limit:
            await __import__("asyncio").sleep(self._rate_limit - elapsed)
        self._last_request = time.time()


class JDCollector(DataCollector):
    """JD.com product data collector."""

    BASE_URL = "https://item.jd.com"

    async def collect_product(self, product_id: str) -> Optional[CollectedProduct]:
        """Collect product data from JD.com by product ID."""
        await self._respect_rate_limit()

        try:
            url = f"{self.BASE_URL}/{product_id}.html"
            response = await self._client.get(url)
            response.raise_for_status()

            # Note: This is a simplified demo. Real scraping would parse HTML.
            # For demo purposes, we return mock data structure.
            _log.info("jd_collect", product_id=product_id, status="demo_mode")

            return CollectedProduct(
                source_id=product_id,
                platform="jd",
                name=f"JD商品{product_id}",
                category="数码",
                price=299.00,
                original_price=499.00,
                description="京东商品示例",
                specs={},
                sales_count=1000,
                rating=4.8,
                url=url,
                collected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as exc:
            _log.error("jd_collect_failed", product_id=product_id, error=str(exc))
            return None


class PinduoduoCollector(DataCollector):
    """Pinduoduo product data collector."""

    BASE_URL = "https://mobile.yangkeduo.com"

    async def collect_product(self, product_id: str) -> Optional[CollectedProduct]:
        """Collect product data from Pinduoduo by product ID."""
        await self._respect_rate_limit()

        try:
            url = f"{self.BASE_URL}/goods.html?goods_id={product_id}"
            response = await self._client.get(url)
            response.raise_for_status()

            _log.info("pdd_collect", product_id=product_id, status="demo_mode")

            return CollectedProduct(
                source_id=product_id,
                platform="pinduoduo",
                name=f"拼多多商品{product_id}",
                category="家居",
                price=89.00,
                original_price=159.00,
                description="拼多多商品示例",
                specs={},
                sales_count=5000,
                rating=4.6,
                url=url,
                collected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as exc:
            _log.error("pdd_collect_failed", product_id=product_id, error=str(exc))
            return None


class DataCollectorManager:
    """Manages multiple platform collectors."""

    def __init__(self) -> None:
        self._collectors = {
            "jd": JDCollector(rate_limit=1.5),
            "pinduoduo": PinduoduoCollector(rate_limit=2.0),
        }

    async def collect(self, platform: str, product_id: str) -> Optional[CollectedProduct]:
        """Collect product from specified platform."""
        collector = self._collectors.get(platform)
        if not collector:
            _log.error("unknown_platform", platform=platform)
            return None
        return await collector.collect_product(product_id)

    async def collect_batch(self, platform: str, product_ids: list[str]) -> list[CollectedProduct]:
        """Collect multiple products from a platform."""
        collector = self._collectors.get(platform)
        if not collector:
            return []

        results = []
        for pid in product_ids:
            product = await collector.collect_product(pid)
            if product:
                results.append(product)
        return results


_collector_manager: Optional[DataCollectorManager] = None


def get_collector_manager() -> DataCollectorManager:
    """Get or create collector manager singleton."""
    global _collector_manager
    if _collector_manager is None:
        _collector_manager = DataCollectorManager()
    return _collector_manager
