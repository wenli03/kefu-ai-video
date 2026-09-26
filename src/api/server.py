"""
FastAPI Backend

REST API for the e-commerce AI customer service system.
Integrates Ollama local LLM, ChromaDB knowledge base, and real product data.

Endpoints:
  POST /api/chat       — send a message and get AI response (calls Ollama)
  GET  /api/session    — get session info
  GET  /api/metrics    — get system metrics
  GET  /api/health     — health check
  POST /api/eval       — run evaluation
  GET  /api/cost       — cost tracking summary
  GET  /api/products   — search products from knowledge base
  GET  /api/ollama/models — list available Ollama models
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.logging import SessionLogger
from utils.monitoring import metrics as metrics_collector, health_checker
from utils.langsmith_integration import tracing_handler, cost_tracker, eval_harness
from utils.ollama_client import get_ollama_client
from graph.workflow import get_graph, classify_intent, Intent
from knowledge.rag_engine import get_rag_chain

_log = SessionLogger("api")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.info("api_server_started")
    yield
    _log.info("api_server_stopped")


app = FastAPI(title="ShopMind AI — E-commerce Customer Service API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    customer_id: str = ""


class ChatResponse(BaseModel):
    response: str
    intent: str
    agent: str
    session_id: str
    latency_ms: float
    tools_used: list[str] = []
    products: list[dict] = []


class EvalRequest(BaseModel):
    intent: str = ""
    tools: list[str] = []


# ─── Session Store ───────────────────────────────────────────────────────────

@dataclass
class Session:
    id: str
    customer_id: str
    messages: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    tool_calls: int = 0
    last_products: list[dict] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def _get_or_create_session(session_id: str, customer_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(id=session_id, customer_id=customer_id)
    return _sessions[session_id]


# ─── Fallback Response Generator ─────────────────────────────────────────────

_PLATFORM_URLS = {
    "jd": "https://search.jd.com/Search?keyword={keyword}&enc=utf-8",
    "pinduoduo": "https://mobile.yangkeduo.com/search_result.html?search_key={keyword}",
}


def _platform_url(platform: str, keyword: str) -> str:
    template = _PLATFORM_URLS.get(platform, _PLATFORM_URLS["jd"])
    return template.replace("{keyword}", keyword)


def _build_product_cards(rag_results: list[dict]) -> list[dict]:
    """Build structured product card data with platform navigation URLs."""
    platform_names = {"jd": "京东", "pinduoduo": "拼多多"}
    sorted_results = sorted(rag_results, key=lambda r: r.get("price", 999999))
    cards = []
    for p in sorted_results:
        name = p.get("name", "未知商品")
        platform = p.get("platform", "jd")
        cards.append({
            "id": p.get("id", ""),
            "name": name,
            "price": p.get("price", 0),
            "original_price": p.get("original_price", 0),
            "platform": platform,
            "platform_name": platform_names.get(platform, "京东"),
            "rating": p.get("rating", 0),
            "sales_count": p.get("sales_count", 0),
            "url": _platform_url(platform, name),
            "discount": round((1 - p.get("price", 0) / max(p.get("original_price", 1), 1)) * 100) if p.get("original_price", 0) > p.get("price", 0) else 0,
        })
    return cards


def _build_fallback_response(message: str, rag_results: list[dict], intent: Any) -> str:
    """Generate an intent-aware response from knowledge base data when Ollama is unavailable."""
    t = message.lower()

    def has(*kws: str) -> bool:
        return any(k in t for k in kws)

    # 1. 服务类意图：优先于商品推荐，避免答非所问
    if has("你是谁", "介绍自己", "自我介绍", "你叫什么", "什么名字"):
        return ('我是小智，ShopMind 的 AI 购物助手，已接入 ChromaDB 商品知识库'
                '（65 件真实商品，覆盖京东和拼多多货源）。\n'
                '我可以帮您搜货比价、推荐最低价货源、查订单物流、办理退换货、找优惠券。')
    if has("能做什么", "会什么", "有什么功能", "你能干", "功能"):
        return ('我可以帮您：\n'
                '1. 搜索商品并自动比价，默认推荐最低价货源\n'
                '2. 点击商品卡片直接跳转京东/拼多多页面\n'
                '3. 查询订单和物流状态\n'
                '4. 办理退换货\n'
                '5. 查找优惠券和促销活动\n\n'
                '直接告诉我想买什么，比如"帮我找最便宜的蓝牙耳机"。')
    if has("谢谢", "感谢", "辛苦了"):
        return '不客气！能帮到您就好。还有别的需要吗？'
    if has("再见", "拜拜", "就这些", "没事了", "结束"):
        return '好的，感谢光临！有问题随时找我，祝您购物愉快～'
    if has("人工", "真人", "转接"):
        return ('我理解您想联系真人客服。订单、价格、库存、退换货这些问题我都能直接处理，'
                '要不先告诉我您的具体问题？确实处理不了的话我马上帮您转人工，预计等待 2 分钟。')
    if has("投诉"):
        return ('非常抱歉给您带来不好的体验！您的投诉我已记录并会优先处理。'
                '请告诉我具体的订单号或问题细节，我马上帮您核实解决。')
    if has("退货", "退款", "换货", "退换", "不想要了", "质量问题"):
        return ('可以办理的。平台支持 7 天无理由退换（部分商品除外）。'
                '请提供您的订单号（ORD 开头）和退换原因，我马上为您发起退换申请。')
    if has("订单", "物流", "快递", "发货", "运单", "包裹", "到哪"):
        return ('好的，请提供您的订单号（一般是 ORD + 日期 + 编号，如 ORD20240101001），'
                '我马上帮您查询物流状态。')
    if has("优惠", "券", "折扣", "满减", "活动", "打折", "特价"):
        return ('当前优惠活动：\n'
                '1. 新人首单立减 20 元\n'
                '2. 满 99 减 10 元优惠券\n'
                '3. 部分商品满 2 件 8 折\n\n'
                '告诉我您想买什么，我帮您看看哪件最划算。')
    if has("支付", "付款", "花呗", "分期"):
        return ('我们支持微信支付、支付宝、银联卡，花呗可选 3/6/12 期分期。'
                '需要我帮您算一下分期金额吗？')

    # 2. 商品推荐（含"你好+想买X"这类混合句）
    if rag_results:
        platform_names = {"jd": "京东", "pinduoduo": "拼多多"}

        sorted_results = sorted(rag_results, key=lambda r: r.get("price", 999999))
        cheapest = sorted_results[0]

        lines = []
        lines.append(f"为您找到 {len(rag_results)} 件相关商品，为您推荐：")
        lines.append("")

        for i, p in enumerate(sorted_results, 1):
            name = p.get("name", "未知商品")
            price = p.get("price", 0)
            original_price = p.get("original_price", 0)
            platform = platform_names.get(p.get("platform", ""), "")
            rating = p.get("rating", 0)
            sales = p.get("sales_count", 0)

            line = f"{i}. {name}"
            if original_price and original_price > price:
                line += f" | {price}元 (原价{original_price}元)"
            else:
                line += f" | {price}元"
            if platform:
                line += f" | {platform}"
            if rating:
                line += f" | 评分{rating}"
            if sales:
                line += f" | 已售{sales}"
            lines.append(line)

        lines.append("")
        lines.append(f"其中最低价是 {cheapest.get('name', '')}，仅需 {cheapest.get('price', 0)}元")
        cheapest_platform = platform_names.get(cheapest.get("platform", ""), "")
        if cheapest_platform:
            lines.append(f"（来自{cheapest_platform}），性价比很高哦！")
        else:
            lines.append("，性价比很高哦！")

        lines.append("")
        lines.append("需要了解更多详情，或者帮您下单吗？")

        return "\n".join(lines)

    # 3. 纯寒暄
    if has("你好", "您好", "hi", "hello", "嗨", "在吗", "早上好", "下午好", "晚上好"):
        return ('您好！我是 AI 购物助手小智，已接入京东/拼多多真实商品库。'
                '想买什么直接说，我帮您比价并推荐最低价货源～')

    # 4. 未命中：针对用户原问题回应，不返回通用介绍
    topic = message.strip().rstrip("？?。.!！")
    return (f'抱歉，暂时没有与「{topic[:20]}」完全匹配的答案。您可以试试：\n'
            '1. 说出具体品类（如耳机、保温杯、跑鞋），我会比价京东/拼多多并推荐最低价\n'
            '2. 提供订单号（ORD 开头）查询物流\n'
            '3. 或问我退换货、优惠券等服务问题')


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    status = await health_checker.check_all()
    all_healthy = all(v.get("healthy", False) for v in status.get("checks", {}).values())
    return {"status": "healthy" if all_healthy else "degraded", "checks": status.get("checks", {})}


_ANAPHORA_MARKERS = (
    "刚才", "刚刚", "上一", "第一款", "第二款", "第三款", "这款", "那款",
    "它", "划算", "便宜点", "还有货", "下单", "买它",
)


def _is_anaphoric_followup(message: str) -> bool:
    """Follow-up referring to previously shown products, e.g. 刚才推荐的第一款."""
    return any(m in message for m in _ANAPHORA_MARKERS)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process chat message using Ollama LLM and RAG knowledge base."""
    start = time.time()
    session_id = req.session_id or str(uuid.uuid4())[:8]
    session = _get_or_create_session(session_id, req.customer_id)

    # Classify intent
    intent = classify_intent(req.message)
    _log.info("chat_intent", intent=intent.value, message=req.message[:50])

    # Get RAG engine and search for relevant products
    rag_engine = get_rag_chain()
    reused_products = bool(session.last_products) and _is_anaphoric_followup(req.message)
    if reused_products:
        # 追问指代上一轮商品（"刚才推荐的第一款"）：新检索只会引入噪声，直接沿用上轮结果
        rag_results = session.last_products
    else:
        rag_results = await rag_engine.search_products(req.message, max_results=3)

    # Build context from RAG results — numbered in the SAME order as the
    # product cards shown to the user (price ascending), so "第一款" resolves correctly
    context = ""
    if rag_results:
        ordered = sorted(rag_results, key=lambda r: r.get("price", 999999))
        if reused_products:
            context = "以下是你上一轮推荐给用户的商品（用户正在追问这些商品，请基于它们回答）：\n"
        else:
            context = "以下是相关商品信息：\n"
        context += "编号与用户看到的商品卡片顺序一致（第1款是最前面的卡片）：\n"
        for i, product in enumerate(ordered, 1):
            context += f"第{i}款: {product['name']} - {product['price']}元 ({product['category']})\n"
            context += f"   {product['description'][:100]}\n\n"

    # Call Ollama LLM
    ollama_client = get_ollama_client()
    messages = [
        {"role": "system", "content": """你是 ShopMind AI 电商客服助手"小智"。
你的职责是帮助用户解决购物问题，包括商品咨询、订单查询、退换货等。
回答要自然、友好、像真人一样，不要过于机械。
如果用户询问商品，根据提供的商品信息给出推荐。
如果用户提到"第N款/第一款"，严格按商品信息里的编号对应，回答时说商品全名，不要说编号。
如果用户询问订单，帮助查询订单状态。
保持简洁，每次回复不超过100字。"""},
    ]

    # Add conversation history
    for msg in session.messages[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current message with context
    user_message = req.message
    if context:
        user_message = f"{context}\n用户问题：{req.message}"
    messages.append({"role": "user", "content": user_message})

    try:
        response_text = await ollama_client.chat(messages, temperature=0.7)
        tracing_handler.on_llm_start(model=ollama_client._model, prompt=req.message)
        agent_name = "ollama"
    except Exception as exc:
        _log.error("ollama_call_failed", error=str(exc))
        response_text = _build_fallback_response(req.message, rag_results, intent)
        agent_name = "rag_fallback"
        tracing_handler.on_llm_start(model="fallback", prompt=req.message)

    session.messages.append({"role": "user", "content": req.message})
    session.messages.append({"role": "assistant", "content": response_text})

    latency = (time.time() - start) * 1000
    tracing_handler.on_llm_end(response=response_text, latency_ms=latency)
    metrics_collector.increment("api_chat_requests")
    metrics_collector.observe("api_chat_latency", latency)

    if rag_results and not reused_products:
        session.last_products = rag_results

    tools_used = [] if reused_products else (["rag_search"] if rag_results else [])
    if agent_name == "ollama":
        tools_used.append("ollama_chat")

    return ChatResponse(
        response=response_text,
        intent=intent.value,
        agent=agent_name,
        session_id=session_id,
        latency_ms=round(latency, 1),
        tools_used=tools_used,
        products=_build_product_cards(rag_results),
    )


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    return {
        "id": s.id, "customer_id": s.customer_id,
        "message_count": len(s.messages), "created_at": s.created_at,
        "messages": s.messages[-20:],
    }


@app.get("/api/metrics")
async def get_metrics():
    snapshot = metrics_collector.snapshot()
    return {
        "counters": {k: v["value"] for k, v in snapshot.get("counters", {}).items()},
        "gauges": {k: v["value"] for k, v in snapshot.get("gauges", {}).items()},
        "histograms": {k: {"count": v["count"], "mean": round(v.get("mean", 0), 1)} for k, v in snapshot.get("histograms", {}).items()},
    }


@app.get("/api/cost")
async def get_cost():
    return cost_tracker.summary()


@app.post("/api/eval")
async def run_eval(req: EvalRequest):
    if req.intent and req.tools:
        results = eval_harness.evaluate(req.intent, req.tools)
        return {"results": [{"case": r.case_id, "passed": r.passed, "score": r.score} for r in results]}
    summary = eval_harness.run_all(lambda msg: (classify_intent(msg).value, []))
    return summary


@app.get("/api/traces")
async def get_traces():
    traces = tracing_handler.get_traces()
    return {"count": len(traces), "traces": traces[-50:]}


@app.get("/api/products")
async def search_products_api(query: str = "", category: str = "", platform: str = ""):
    """Search products from knowledge base."""
    rag_engine = get_rag_chain()
    try:
        results = await rag_engine.search_products(query or "热门商品", category=category, max_results=10)
        return {"count": len(results), "products": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ollama/models")
async def list_ollama_models():
    """List available Ollama models."""
    ollama_client = get_ollama_client()
    try:
        models = await ollama_client.list_models()
        return {"models": models, "current": ollama_client._model}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ollama/health")
async def ollama_health():
    """Check Ollama service health."""
    ollama_client = get_ollama_client()
    is_healthy = await ollama_client.health_check()
    return {"healthy": is_healthy, "model": ollama_client._model}
