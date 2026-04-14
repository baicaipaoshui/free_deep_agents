"""HARA Pipeline — 6-stage LangGraph StateGraph with human-in-the-loop gate.

Stages
------
1. parse_item_definition   — extract structured item definition
2. identify_failure_modes  — apply 4-keyword template
3. derive_hazards          — map failure modes to vehicle-level hazards
4. estimate_seco           — assign S/E/C/O for each scenario
5. classify_asil           — compute ASIL; LangGraph interrupt_before here
6. generate_safety_goals   — produce ISO 26262 safety goals

The graph pauses **before** ``classify_asil`` via ``interrupt_before``.
The WebSocket layer in ``analysis.py`` detects the pause with::

    snapshot = await hara_graph.aget_state(config)
    if snapshot.next:          # ('classify_asil',)
        stream approval_required event → frontend

After human confirmation ``approval.py`` resumes with::

    await hara_graph.aupdate_state(config, modified_seco)   # if edits
    await hara_graph.ainvoke(None, config)                  # resume

Checkpointer: AsyncRedisSaver (Redis URL from app.config.REDIS_URL).
The module-level ``hara_graph`` is initialised once at application startup
by calling ``await init_hara_graph()``.

Each node emits a ``progress`` event via :mod:`app.agent.stream_bus`.
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph import END, StateGraph
from redis.exceptions import ResponseError
from typing_extensions import TypedDict

from app.agent import stream_bus
from app.config import REDIS_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class HARAState(TypedDict):
    """Mutable state threaded through every HARA pipeline node."""

    messages: Annotated[list, operator.add]
    item_definition: str
    failure_modes: list[dict[str, Any]]
    hazards: list[dict[str, Any]]
    seco_ratings: list[dict[str, Any]]
    asil_results: list[dict[str, Any]]
    safety_goals: list[dict[str, Any]]
    current_stage: str
    validation_errors: list[str]


# ---------------------------------------------------------------------------
# Helper: extract thread_id from LangGraph config
# ---------------------------------------------------------------------------


def _sid(config: RunnableConfig | None) -> str:
    if config is None:
        return ""
    return (config.get("configurable") or {}).get("thread_id", "")


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def parse_item_definition(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 1: Extract a structured item definition from the user's input."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "parse_item_definition",
        "message": "📋 解析 Item Definition (系统边界 / 功能列表 / 工况范围)…",
    })
    last_user_msg = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    return {
        "current_stage": "parse_item_definition",
        "item_definition": last_user_msg,
        "messages": [AIMessage(content=f"[HARA Stage 1] Item Definition 已提取。\n{last_user_msg}")],
    }


def identify_failure_modes(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 2: Generate functional failure modes using the 4-keyword template."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "identify_failure_modes",
        "message": "🔍 识别失效模式 (Loss / Degradation / Unintended / Incorrect)…",
    })
    return {
        "current_stage": "identify_failure_modes",
        "messages": [AIMessage(content="[HARA Stage 2] 失效模式识别完成（4关键词模板）。")],
    }


def derive_hazards(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 3: Derive vehicle-level hazards from functional failure modes."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "derive_hazards",
        "message": "⚠️  推导车辆级危害 (考虑驾驶工况 / 环境因素)…",
    })
    return {
        "current_stage": "derive_hazards",
        "messages": [AIMessage(content="[HARA Stage 3] 车辆级危害推导完成。")],
    }


def estimate_seco(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 4: Estimate S/E/C/O for each hazardous event.

    After this node completes the graph will pause at the
    interrupt_before=["classify_asil"] boundary.  The WebSocket layer
    detects the pause via aget_state() and sends approval_required.
    """
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "estimate_seco",
        "message": "📊 评估 S/E/C/O 参数 (S0-S3 / E0-E4 / C0-C3)…",
    })
    return {
        "current_stage": "estimate_seco",
        "messages": [AIMessage(content="[HARA Stage 4] S/E/C/O 评估完成，等待人工审批…")],
    }


def classify_asil(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 5: Classify ASIL using the confirmed S/E/C/O ratings."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "classify_asil",
        "message": "🏷️  确定 ASIL 等级 (QM / A / B / C / D)…",
    })
    return {
        "current_stage": "classify_asil",
        "messages": [AIMessage(content="[HARA Stage 5] ASIL 定级完成。")],
    }


def generate_safety_goals(state: HARAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 6: Generate ISO 26262 safety goals from ASIL-rated hazardous events."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "generate_safety_goals",
        "message": "🎯 生成安全目标 (格式: [系统] 的 [功能] 不得因 [失效] 导致 [危害])…",
    })
    return {
        "current_stage": "generate_safety_goals",
        "messages": [AIMessage(content="[HARA Stage 6] 安全目标生成完成。")],
    }


# ---------------------------------------------------------------------------
# Graph construction + module-level instance
# ---------------------------------------------------------------------------

# Populated by init_hara_graph() at application startup.
hara_graph = None
_redis_cm = None  # holds the async context manager so we can close it on shutdown


def _build_workflow() -> StateGraph:
    workflow = StateGraph(HARAState)

    workflow.add_node("parse_item_definition", parse_item_definition)
    workflow.add_node("identify_failure_modes", identify_failure_modes)
    workflow.add_node("derive_hazards", derive_hazards)
    workflow.add_node("estimate_seco", estimate_seco)
    workflow.add_node("classify_asil", classify_asil)
    workflow.add_node("generate_safety_goals", generate_safety_goals)

    workflow.set_entry_point("parse_item_definition")
    workflow.add_edge("parse_item_definition", "identify_failure_modes")
    workflow.add_edge("identify_failure_modes", "derive_hazards")
    workflow.add_edge("derive_hazards", "estimate_seco")
    workflow.add_edge("estimate_seco", "classify_asil")
    workflow.add_edge("classify_asil", "generate_safety_goals")
    workflow.add_edge("generate_safety_goals", END)

    return workflow


async def init_hara_graph() -> None:
    """Initialise the module-level ``hara_graph`` with AsyncRedisSaver.

    Call once from the FastAPI lifespan startup handler::

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await init_hara_graph()
            yield
            await close_hara_graph()
    """
    global hara_graph, _redis_cm
    checkpointer = None

    try:
        _redis_cm = AsyncRedisSaver.from_conn_string(REDIS_URL)
        checkpointer = await _redis_cm.__aenter__()
        await checkpointer.asetup()
        logger.info("HARA graph checkpointer initialized with Redis: %s", REDIS_URL)
    except ResponseError as exc:
        _redis_cm = None
        logger.warning(
            "Redis checkpointer unavailable (%s). Falling back to in-memory checkpoints. "
            "This disables cross-process persistence for HARA approvals.",
            exc,
        )
        checkpointer = MemorySaver()

    hara_graph = _build_workflow().compile(
        checkpointer=checkpointer,
        interrupt_before=["classify_asil"],
    )


async def close_hara_graph() -> None:
    """Release the Redis connection. Call from the FastAPI lifespan shutdown handler."""
    global _redis_cm
    if _redis_cm is not None:
        await _redis_cm.__aexit__(None, None, None)
        _redis_cm = None
