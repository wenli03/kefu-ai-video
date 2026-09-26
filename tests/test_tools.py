"""
Tests for e-commerce tools.
"""

import pytest
from src.tools.product_tools import ProductTools
from src.tools.order_tools import OrderTools


class TestProductTools:
    """Test product-related tools."""

    @pytest.fixture
    def product_tools(self):
        """Create product tools instance."""
        from src.knowledge.rag_engine import RAGEngine, MockEmbeddings
        # Use mock RAG for testing
        class MockRAG:
            async def search_products(self, *args, **kwargs):
                return []
            async def get_recommendations(self, *args, **kwargs):
                return []
        return ProductTools(MockRAG())

    @pytest.mark.asyncio
    async def test_search_products(self, product_tools):
        """Test product search."""
        result = await product_tools.search_products("耳机")
        assert "results" in result or "source" in result

    @pytest.mark.asyncio
    async def test_get_product_details(self, product_tools):
        """Test getting product details."""
        result = await product_tools.get_product_details("P001")
        assert "P001" in result or "name" in result

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, product_tools):
        """Test product not found."""
        result = await product_tools.get_product_details("INVALID")
        assert "error" in result or "不存在" in result

    @pytest.mark.asyncio
    async def test_check_inventory(self, product_tools):
        """Test inventory check."""
        result = await product_tools.check_inventory("P001")
        assert "inventory" in result or "status" in result


class TestOrderTools:
    """Test order-related tools."""

    @pytest.fixture
    def order_tools(self):
        """Create order tools instance."""
        return OrderTools()

    @pytest.mark.asyncio
    async def test_query_order_status(self, order_tools):
        """Test order status query."""
        result = await order_tools.query_order_status("ORD20240101001")
        assert "order_id" in result or "status" in result

    @pytest.mark.asyncio
    async def test_query_order_not_found(self, order_tools):
        """Test order not found."""
        result = await order_tools.query_order_status("INVALID")
        assert "error" in result or "不存在" in result

    @pytest.mark.asyncio
    async def test_get_tracking_info(self, order_tools):
        """Test tracking info."""
        result = await order_tools.get_tracking_info("ORD20240101001")
        assert "tracking" in result or "carrier" in result or "status" in result

    @pytest.mark.asyncio
    async def test_check_return_policy(self, order_tools):
        """Test return policy."""
        result = await order_tools.check_return_policy()
        assert "policy" in result or "return_days" in result

    @pytest.mark.asyncio
    async def test_apply_coupon(self, order_tools):
        """Test coupon application."""
        result = await order_tools.apply_coupon("NEW20")
        assert "discount" in result or "code" in result

    @pytest.mark.asyncio
    async def test_apply_invalid_coupon(self, order_tools):
        """Test invalid coupon."""
        result = await order_tools.apply_coupon("INVALID")
        assert "error" in result or "不存在" in result
