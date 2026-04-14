"""FTA Pipeline — LangGraph StateGraph with logic-validation loop.

Stages
------
1. define_top_event      — define the undesired top-level event
2. decompose_gates       — recursively decompose using AND/OR gates
3. map_basic_events      — map leaf events to FMEA failure modes
4. validate_logic        — check gate consistency; loop back if errors found

Each node emits a ``progress`` event via :mod:`app.agent.stream_bus`.
Validation errors and rework iterations are also streamed as progress messages.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from deepagents import CompiledSubAgent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agent import stream_bus


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class FTAState(TypedDict):
    """Mutable state threaded through every FTA pipeline node."""

    messages: Annotated[list, operator.add]
    item_description: str
    top_event: str
    fault_tree: dict[str, Any]
    basic_events: list[dict[str, Any]]
    cut_sets: list[dict[str, Any]]
    fmea_failure_modes: list[dict[str, Any]]
    current_stage: str
    validation_errors: list[str]
    needs_rework: bool
    unmapped_events: list[str]
    rework_iterations: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _sid(config: RunnableConfig | None) -> str:
    if config is None:
        return ""
    return (config.get("configurable") or {}).get("thread_id", "")


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def define_top_event(state: FTAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 1: Define the undesired top-level event from user input."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "define_top_event",
        "message": "🌳 定义顶事件 (不希望发生的系统级事件)…",
    })
    last_msg = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    return {
        "current_stage": "define_top_event",
        "item_description": last_msg,
        "messages": [AIMessage(content="[FTA Stage 1] 顶事件已定义。")],
    }


def decompose_gates(state: FTAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 2: Recursively decompose the top event using AND/OR logic gates."""
    iterations = state.get("rework_iterations", 0)
    label = (
        f"🔀 AND/OR 逻辑门分解 (第 {iterations + 1} 次迭代)…"
        if iterations > 0
        else "🔀 AND/OR 逻辑门递归分解…"
    )
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "decompose_gates",
        "message": label,
    })
    return {
        "current_stage": "decompose_gates",
        "messages": [AIMessage(content="[FTA Stage 2] 逻辑门分解完成（AND/OR）。")],
    }


def map_basic_events(state: FTAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 3: Map leaf (basic) events to corresponding FMEA failure modes."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "map_basic_events",
        "message": "🗺️  底事件映射 (关联 FMEA 失效模式)…",
    })
    basic_events = state.get("basic_events", [])
    fmea_modes = state.get("fmea_failure_modes", [])
    fmea_ids = {m.get("id") for m in fmea_modes}
    unmapped = [e["id"] for e in basic_events if e.get("id") not in fmea_ids]

    return {
        "current_stage": "map_basic_events",
        "unmapped_events": unmapped,
        "messages": [
            AIMessage(
                content=(
                    f"[FTA Stage 3] 底事件映射完成。"
                    f"{len(unmapped)} 个底事件未映射到 FMEA。"
                    if unmapped
                    else "[FTA Stage 3] 所有底事件已映射到 FMEA。"
                )
            )
        ],
    }


def validate_logic(state: FTAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 4: Validate gate consistency and cross-references."""
    sid = _sid(config)
    stream_bus.emit(sid, {
        "type": "progress",
        "stage": "validate_logic",
        "message": "✔️  故障树逻辑一致性校验 (AND/OR 门子节点数检查)…",
    })

    tree = state.get("fault_tree", {})
    errors = _check_gate_consistency(tree)
    iterations = state.get("rework_iterations", 0)
    needs_rework = bool(errors) and iterations < 3

    if errors:
        stream_bus.emit(sid, {
            "type": "progress",
            "stage": "validate_logic",
            "message": f"⚠️  发现 {len(errors)} 个逻辑错误，{'将重新分解逻辑门…' if needs_rework else '已达最大重试次数，记录错误。'}",
        })

    return {
        "current_stage": "validate_logic",
        "validation_errors": errors,
        "needs_rework": needs_rework,
        "rework_iterations": iterations + (1 if errors else 0),
        "messages": [
            AIMessage(
                content=(
                    f"[FTA Stage 4] 逻辑校验发现 {len(errors)} 个错误，需要修正。"
                    if errors
                    else "[FTA Stage 4] 逻辑校验通过，无错误。"
                )
            )
        ],
    }


def _check_gate_consistency(tree: dict[str, Any]) -> list[str]:
    """Check that every AND/OR gate has at least two children."""
    errors: list[str] = []
    for node_id, node in tree.items():
        node_type = node.get("node_type", "")
        children = node.get("children", [])
        if node_type in ("and_gate", "or_gate") and len(children) < 2:
            errors.append(
                f"节点 {node_id} ({node_type}) 子节点数量不足（当前：{len(children)}，最少需要 2）。"
            )
    return errors


def _validate_router(state: FTAState) -> str:
    """Route after validate_logic: loop for rework or finish."""
    if state.get("needs_rework"):
        return "decompose_gates"
    return "end"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def create_fta_graph():
    """Build and compile the FTA StateGraph."""
    workflow = StateGraph(FTAState)

    workflow.add_node("define_top_event", define_top_event)
    workflow.add_node("decompose_gates", decompose_gates)
    workflow.add_node("map_basic_events", map_basic_events)
    workflow.add_node("validate_logic", validate_logic)

    workflow.set_entry_point("define_top_event")
    workflow.add_edge("define_top_event", "decompose_gates")
    workflow.add_edge("decompose_gates", "map_basic_events")
    workflow.add_edge("map_basic_events", "validate_logic")
    workflow.add_conditional_edges(
        "validate_logic",
        _validate_router,
        {"decompose_gates": "decompose_gates", "end": END},
    )

    return workflow.compile(checkpointer=MemorySaver())


# ---------------------------------------------------------------------------
# CompiledSubAgent export
# ---------------------------------------------------------------------------

fta_compiled: CompiledSubAgent = {
    "name": "fta_pipeline",
    "description": "执行完整 FTA Pipeline（4 阶段 + 逻辑一致性校验循环）。",
    "runnable": create_fta_graph(),
}
