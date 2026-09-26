"""
E-commerce AI Video Customer Service Agent

Main entry point. Uses LiveKit Agents for real-time video/audio and
LangChain for intelligent response generation with RAG.

P0 生产就绪：
- 服务健康检查
- 指标采集与监控
- 数据备份
- 安全输入验证
"""

import logging
import time
from dataclasses import dataclass, field

from dotenv import find_dotenv, load_dotenv

from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    metrics,
    MetricsCollectedEvent,
)
from livekit.plugins import lemonslice

from agent.ecommerce_agent import EcommerceSupportAgent
from knowledge.rag_engine import get_rag_chain
from tools.product_tools import ProductTools
from tools.order_tools import OrderTools
from utils.logging import SessionLogger, AgentError
from utils.resilience import degradation_manager, PresetResponses, ServiceStatus
from utils.security import validate_input, mask_sensitive_info, rate_limiter, ip_blacklist
from utils.monitoring import metrics as metrics_collector, health_checker, alert_engine
from utils.backup import backup_manager

load_dotenv(find_dotenv())
logger = logging.getLogger("ecommerce-video-cs")

server = AgentServer()


@dataclass
class SessionState:
    customer_id: str | None = None
    cart_items: list[dict] = field(default_factory=list)
    conversation_context: dict = field(default_factory=dict)
    started_at: float = 0.0
    tool_calls: int = 0


# ─── 健康检查注册 ────────────────────────────────────────────────────────────

async def _check_rag_health() -> tuple[bool, str]:
    try:
        rag = get_rag_chain()
        results = await rag.search_products("健康检查", max_results=1)
        return True, f"ChromaDB OK, {len(results)} results"
    except Exception as exc:
        return False, str(exc)


async def _check_openai_health() -> tuple[bool, str]:
    import os
    if not os.getenv("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY not set"
    return True, "API key configured"


async def _check_deepgram_health() -> tuple[bool, str]:
    import os
    if not os.getenv("DEEPGRAM_API_KEY"):
        return False, "DEEPGRAM_API_KEY not set"
    return True, "API key configured"


async def _check_cartesia_health() -> tuple[bool, str]:
    import os
    if not os.getenv("CARTESIA_API_KEY"):
        return False, "CARTESIA_API_KEY not set"
    return True, "API key configured"


health_checker.register("rag_chromadb", _check_rag_health)
health_checker.register("llm_openai", _check_openai_health)
health_checker.register("stt_deepgram", _check_deepgram_health)
health_checker.register("tts_cartesia", _check_cartesia_health)


# ─── 启动时自动备份 ──────────────────────────────────────────────────────────

def _startup_backup():
    try:
        result = backup_manager.create_backup(label="startup")
        if result["success"]:
            logger.info("Startup backup created: %s", result["backup_name"])
    except Exception:
        logger.warning("Startup backup failed", exc_info=True)


# ─── 入口 ────────────────────────────────────────────────────────────────────

@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    log = SessionLogger("session", room=ctx.room.name)
    session_start = time.time()

    try:
        health_status = await health_checker.check_all()
        log.set(health=health_status)

        rag_engine = get_rag_chain()
        degradation_manager.mark_healthy("rag")
        log.set(component="rag", status="initialized")

        product_tools = ProductTools(rag_engine)
        order_tools = OrderTools()
        log.set(component="tools", status="initialized")

        agent = EcommerceSupportAgent(
            product_tools=product_tools,
            order_tools=order_tools,
            session_log=log,
        )

        session = AgentSession(
            stt=inference.STT("deepgram/nova-3", language="zh"),
            llm=inference.LLM("openai/gpt-4o"),
            tts=inference.TTS("cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
            turn_handling=TurnHandlingOptions(
                interruption={
                    "resume_false_interruption": True,
                    "false_interruption_timeout": 1.0,
                },
                preemptive_generation={"enabled": True, "max_retries": 3},
            ),
            aec_warmup_duration=3.0,
        )

        @session.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent) -> None:
            if ev.metrics.type != "stt_metrics":
                metrics.log_metrics(ev.metrics)
            metrics_collector.observe(
                f"{ev.metrics.type}_latency",
                getattr(ev.metrics, "latency", 0) * 1000,
            )

        avatar = lemonslice.AvatarSession(
            agent_image_url="https://placeholder.com/cs-avatar.png",
            agent_prompt="A friendly e-commerce customer service representative, professional and warm demeanor",
            agent_idle_prompt="Waiting attentively for customer questions",
            idle_timeout=120,
            response_done_timeout=2,
        )

        await avatar.start(session, room=ctx.room)
        await session.start(agent=agent, room=ctx.room)
        await avatar.wait_for_join()

        degradation_manager.mark_healthy("lemonslice")
        degradation_manager.mark_healthy("livekit")

        session.generate_reply(
            instructions="Greet the customer warmly in Chinese, introduce yourself as an AI shopping assistant, "
            "and ask how you can help them today."
        )

        metrics_collector.increment("sessions_total")
        metrics_collector.set_gauge("active_sessions",
            metrics_collector.get_counter("sessions_total")
            - metrics_collector.get_counter("sessions_ended"))

        log.info(
            "session_started",
            avatar="lemonslice",
            stt="deepgram/nova-3",
            llm="openai/gpt-4o",
            tts="cartesia/sonic-3",
            health={k: v["healthy"] for k, v in health_status.get("checks", {}).items()},
        )

        alert_engine.evaluate()

    except Exception as exc:
        error = AgentError.wrap(exc, message="Failed to start CS session", step="entrypoint")
        metrics_collector.increment("session_start_failures")
        log.error("session_start_failed", error=str(exc), step="entrypoint")
        raise


if __name__ == "__main__":
    _startup_backup()
    cli.run_app(server)
