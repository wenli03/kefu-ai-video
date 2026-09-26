"""Data module for e-commerce product database and collection."""

from data.product_database import (
    Product,
    SAMPLE_PRODUCTS,
    get_all_products,
    get_products_by_category,
    get_products_by_platform,
    search_products,
)
from data.collector import (
    CollectedProduct,
    DataCollector,
    JDCollector,
    PinduoduoCollector,
    DataCollectorManager,
    get_collector_manager,
)

__all__ = [
    "Product",
    "SAMPLE_PRODUCTS",
    "get_all_products",
    "get_products_by_category",
    "get_products_by_platform",
    "search_products",
    "CollectedProduct",
    "DataCollector",
    "JDCollector",
    "PinduoduoCollector",
    "DataCollectorManager",
    "get_collector_manager",
]
