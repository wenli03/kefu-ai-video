"""
RAG Engine for E-commerce Product Knowledge

Uses LangChain + ChromaDB for product knowledge retrieval.
Supports Ollama local embeddings for cost-free operation.

P0 生产就绪：
- 检索延迟监控
- 降级健康状态上报
- 错误指标采集
"""

import json
import logging
import os
import time
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma

from utils.logging import SessionLogger, AgentError
from utils.monitoring import metrics as metrics_collector
from utils.resilience import degradation_manager

logger = logging.getLogger(__name__)
_log = SessionLogger("rag_engine")


class RAGEngine:

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        embedding_model: str = "ollama/nomic-embed-text",
    ) -> None:
        self._persist_dir = persist_directory
        self._embeddings = self._init_embeddings(embedding_model)
        self._using_mock = isinstance(self._embeddings, MockEmbeddings)
        self._vectorstore = self._init_vectorstore()
        self._all_products: list[dict] = []
        self._index_products()

    def _init_embeddings(self, model_name: str) -> Embeddings:
        """Initialize embeddings - supports Ollama local or OpenAI."""
        # Try Ollama first (local, free)
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import httpx
            response = httpx.get(f"{ollama_base}/api/tags", timeout=5.0)
            if response.status_code == 200:
                embeddings = OllamaEmbeddings(base_url=ollama_base, model=model_name.split("/")[-1])
                probe = embeddings.embed_query("测试")
                if not embeddings.failed and any(probe):
                    logger.info("Using Ollama embeddings: %s", model_name)
                    return embeddings
                logger.warning("Ollama embedding model %s unavailable, skipping", model_name)
        except Exception:
            pass

        # Fallback to OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            from langchain_openai import OpenAIEmbeddings
            logger.info("Using OpenAI embeddings: %s", model_name)
            return OpenAIEmbeddings(model=model_name.split("/")[-1], api_key=api_key)

        # Final fallback to mock
        logger.warning("No embedding service available, using mock embeddings")
        return MockEmbeddings()

    def _init_vectorstore(self) -> Chroma:
        os.makedirs(self._persist_dir, exist_ok=True)

        vectorstore = Chroma(
            collection_name="products",
            embedding_function=self._embeddings,
            persist_directory=self._persist_dir,
        )

        if vectorstore._collection.count() == 0:
            self._load_sample_products(vectorstore)

        return vectorstore

    def _load_sample_products(self, vectorstore: Chroma) -> None:
        """Load expanded product database (55+ products from JD and Pinduoduo)."""
        from data.product_database import get_all_products

        products = get_all_products()
        documents = []
        metadatas = []
        ids = []

        for p in products:
            doc_text = (
                f"商品名称：{p.name}\n"
                f"类目：{p.category} > {p.subcategory}\n"
                f"价格：{p.price}元（原价{p.original_price}元）\n"
                f"描述：{p.description}\n"
                f"规格：{json.dumps(p.specs, ensure_ascii=False)}\n"
                f"销量：{p.sales_count}\n"
                f"评分：{p.rating}\n"
                f"平台：{'京东' if p.platform == 'jd' else '拼多多'}\n"
                f"标签：{', '.join(p.tags)}"
            )
            documents.append(doc_text)
            metadatas.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "subcategory": p.subcategory,
                "price": p.price,
                "original_price": p.original_price,
                "platform": p.platform,
                "rating": p.rating,
                "sales_count": p.sales_count,
            })
            ids.append(p.id)

        vectorstore.add_texts(texts=documents, metadatas=metadatas, ids=ids)
        logger.info("Loaded %d products into vector store", len(products))

    def _index_products(self) -> None:
        """Build in-memory product index for keyword fallback search."""
        from data.product_database import get_all_products
        products = get_all_products()
        self._all_products = [
            {
                "id": p.id, "name": p.name, "category": p.category,
                "subcategory": p.subcategory, "price": p.price,
                "original_price": p.original_price, "platform": p.platform,
                "rating": p.rating, "sales_count": p.sales_count,
                "description": p.description, "tags": p.tags,
                "search_text": (
                    f"{p.name} {p.category} {p.subcategory} "
                    f"{' '.join(p.tags)} {p.description}"
                ).lower(),
            }
            for p in products
        ]

    def _keyword_search(self, query: str, max_results: int = 5) -> list[dict]:
        """Keyword-based search fallback when embeddings are unavailable."""
        query_lower = query.lower()
        query_tokens = set()
        for i in range(len(query_lower) - 1):
            bigram = query_lower[i:i + 2]
            if all('\u4e00' <= c <= '\u9fff' for c in bigram) or bigram.isascii():
                query_tokens.add(bigram)
        for i in range(len(query_lower) - 2):
            trigram = query_lower[i:i + 3]
            if all('\u4e00' <= c <= '\u9fff' for c in trigram):
                query_tokens.add(trigram)
        ascii_words = [w for w in query_lower.replace("+", " ").split() if len(w) > 1]
        query_tokens.update(ascii_words)

        scored = []
        for p in self._all_products:
            text = p["search_text"]
            score = 0
            for token in query_tokens:
                if token in text:
                    score += len(token) * 3
                if token in p["name"].lower():
                    score += len(token) * 5
                for tag in p["tags"]:
                    if token in tag.lower() or tag.lower() in token:
                        score += len(token) * 4
            if score > 5:
                scored.append((score, p))

        scored.sort(key=lambda x: -x[0])
        results = []
        for _, p in scored[:max_results]:
            platform_name = "京东" if p["platform"] == "jd" else "拼多多"
            results.append({
                "id": p["id"], "name": p["name"],
                "category": p["category"], "subcategory": p["subcategory"],
                "price": p["price"], "original_price": p["original_price"],
                "platform": p["platform"], "rating": p["rating"],
                "sales_count": p["sales_count"],
                "description": (
                    f"商品名称：{p['name']}\n"
                    f"类目：{p['category']} > {p['subcategory']}\n"
                    f"价格：{p['price']}元（原价{p['original_price']}元）\n"
                    f"描述：{p['description']}\n"
                    f"销量：{p['sales_count']}\n"
                    f"评分：{p['rating']}\n"
                    f"平台：{platform_name}\n"
                    f"标签：{', '.join(p['tags'])}"
                )[:200] + "...",
                "relevance_score": 1.0,
            })
        return results

    def _hybrid_merge(
        self, vec_results: list[dict], query: str, max_results: int,
    ) -> list[dict]:
        """Hybrid retrieval: keyword-first, with reciprocal-rank fusion fallback.

        nomic-embed-text has weak Chinese discrimination, so literal keyword
        matches (most shopping queries) keep full precision; only when keyword
        hits are sparse does the vector result set get fused in via RRF.
        """
        kw_results = self._keyword_search(query, max_results * 2)
        if len(kw_results) >= max_results:
            return kw_results[:max_results]
        merged: dict[str, dict] = {}
        for rank, r in enumerate(vec_results):
            merged[r["id"]] = {**r, "_score": 1.0 / (60 + rank)}
        for rank, r in enumerate(kw_results):
            if r["id"] in merged:
                merged[r["id"]]["_score"] += 1.0 / (60 + rank)
            else:
                merged[r["id"]] = {**r, "_score": 1.0 / (60 + rank)}
        ranked = sorted(merged.values(), key=lambda x: -x["_score"])[:max_results]
        best = ranked[0]["_score"] if ranked else 1.0
        for r in ranked:
            r["relevance_score"] = round(r.pop("_score") / best, 4)
        return ranked

    async def search_products(
        self, query: str, category: str = "", max_results: int = 5,
    ) -> list[dict]:
        start = time.time()
        try:
            if self._using_mock:
                results = self._keyword_search(query, max_results)
            else:
                filter_dict = {"category": category} if category else None
                docs = self._vectorstore.similarity_search(
                    query=query, k=max_results * 2, filter=filter_dict,
                )
                vec_results = [
                    {
                        "id": doc.metadata.get("id"),
                        "name": doc.metadata.get("name"),
                        "category": doc.metadata.get("category"),
                        "subcategory": doc.metadata.get("subcategory"),
                        "price": doc.metadata.get("price"),
                        "original_price": doc.metadata.get("original_price"),
                        "platform": doc.metadata.get("platform"),
                        "rating": doc.metadata.get("rating"),
                        "sales_count": doc.metadata.get("sales_count"),
                        "description": doc.page_content[:200] + "...",
                    }
                    for doc in docs
                ]
                results = self._hybrid_merge(vec_results, query, max_results)
            latency = (time.time() - start) * 1000
            metrics_collector.observe("rag_search_latency", latency)
            metrics_collector.increment("rag_search_success")
            degradation_manager.mark_healthy("rag")
            return results
        except Exception as exc:
            latency = (time.time() - start) * 1000
            metrics_collector.observe("rag_search_latency", latency)
            metrics_collector.increment("rag_search_errors")
            degradation_manager.mark_degraded("rag", str(exc))
            raise AgentError.wrap(
                exc, message="商品语义搜索失败", step="rag.search",
                fix="已降级为关键词搜索",
            )

    async def get_recommendations(
        self, preference: str, budget_min: float = 0, budget_max: float = 0,
    ) -> list[dict]:
        start = time.time()
        try:
            query = f"推荐适合以下需求的商品：{preference}"
            if budget_max > 0:
                query += f"，预算在{budget_min}到{budget_max}元之间"

            results = self._vectorstore.similarity_search(query=query, k=5)

            recommendations = []
            for doc in results:
                price = doc.metadata.get("price", 0)
                if budget_min > 0 and price < budget_min:
                    continue
                if budget_max > 0 and price > budget_max:
                    continue
                recommendations.append({
                    "id": doc.metadata.get("id"),
                    "name": doc.metadata.get("name"),
                    "category": doc.metadata.get("category"),
                    "price": price,
                    "reason": self._extract_recommendation_reason(doc, preference),
                })

            latency = (time.time() - start) * 1000
            metrics_collector.observe("rag_recommend_latency", latency)
            metrics_collector.increment("rag_recommend_success")
            return recommendations[:5]
        except Exception as exc:
            latency = (time.time() - start) * 1000
            metrics_collector.observe("rag_recommend_latency", latency)
            metrics_collector.increment("rag_recommend_errors")
            raise AgentError.wrap(
                exc, message="推荐引擎异常", step="rag.recommend",
            )

    def _extract_recommendation_reason(self, doc: Document, preference: str) -> str:
        if "适合人群" in doc.page_content:
            return f"适合{preference}的用户"
        return f"与您的需求「{preference}」相关"

    async def get_product_knowledge(self, product_id: str) -> dict | None:
        results = self._vectorstore.similarity_search(
            query=f"商品ID {product_id}的详细信息",
            k=1,
            filter={"id": product_id},
        )
        if not results:
            return None
        return {
            "id": product_id,
            "content": results[0].page_content,
            "metadata": results[0].metadata,
        }


class MockEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1536 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 1536


class OllamaEmbeddings(Embeddings):
    """Ollama local embeddings using nomic-embed-text or similar."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self._base_url = base_url
        self._model = model
        self.failed = False

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed("search_document: " + text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed("search_query: " + text)

    def _embed(self, prompt: str) -> list[float]:
        import httpx
        try:
            response = httpx.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": prompt},
                timeout=30.0,
            )
            response.raise_for_status()
            embedding = response.json().get("embedding") or []
            if not embedding:
                raise ValueError("empty embedding response")
            return embedding
        except Exception as exc:
            logger.warning("Ollama embedding failed: %s", exc)
            self.failed = True
            return [0.0] * 768


_rag_engine: RAGEngine | None = None


def get_rag_chain() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
        _rag_engine = RAGEngine(persist_directory=persist_dir)
    return _rag_engine
