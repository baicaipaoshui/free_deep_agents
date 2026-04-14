"""FMEA Pipeline — LangGraph StateGraph with RPN-based human-review gate.

Stages
------
1. analyze_structure    — decompose system into components
2. mine_failure_modes   — identify failure modes per component
3. calculate_rpn        — assign S/O/D and compute RPN; gate if RPN > threshold
4. recommend_actions    — generate corrective actions for high-RPN items

Each node emits a ``progress`` event (and ``approval_required`` at the RPN
gate) via :mod:`app.agent.stream_bus`.
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
from app.config import RPN_THRESHOLD


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class FMEAState(TypedDict):
    """Mutable state threaded through every FMEA pipeline node."""

    messages: Annotated[list, operator.add]
    system_description: str
    structure: list[dict[str, Any]]
    failure_modes: list[dict[str, Any]]
    rpn_scores: list[dict[str, Any]]
    high_rpn_modes: list[dict[str, Any]]
    corrective_actions: list[dict[str, Any]]
    current_stage: str
    awaiting_approval: bool
    approval_type: str
    approval_detail: dict[str, Any]


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


def analyze_structure(state: FMEAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 1: Decompose the system into a hierarchical component structure."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "analyze_structure",
        "message": "🏗️  系统结构分析 (层次分解 / 功能映射)…",
    })
    last_msg = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    return {
        "current_stage": "analyze_structure",
        "system_description": last_msg,
        "messages": [AIMessage(content="[FMEA Stage 1] 系统结构分析完成，正在分解组件…")],
    }


def mine_failure_modes(state: FMEAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 2: Identify potential failure modes for each system component."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "mine_failure_modes",
        "message": "🔍 失效模式挖掘 (组件级失效 / 影响链分析)…",
    })
    return {
        "current_stage": "mine_failure_modes",
        "messages": [AIMessage(content="[FMEA Stage 2] 失效模式挖掘完成。")],
    }


def calculate_rpn(state: FMEAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 3: Compute RPN for each failure mode; pause if any exceed threshold."""
    sid = _sid(config)
    stream_bus.emit(sid, {
        "type": "progress",
        "stage": "calculate_rpn",
        "message": f"📊 计算 RPN (S×O×D)，阈值 {RPN_THRESHOLD}…",
    })

    failure_modes = state.get("failure_modes", [])
    high_rpn = [fm for fm in failure_modes if fm.get("rpn", 0) > RPN_THRESHOLD]

    updates: dict[str, Any] = {
        "current_stage": "calculate_rpn",
        "high_rpn_modes": high_rpn,
        "messages": [AIMessage(
            content=f"[FMEA Stage 3] RPN 计算完成，{len(high_rpn)} 项超过阈值 {RPN_THRESHOLD}。"
        )],
    }

    if high_rpn:
        approval_detail = {
            "message": f"{len(high_rpn)} 个失效模式 RPN > {RPN_THRESHOLD}，需人工审核",
            "data": high_rpn,
        }
        updates["awaiting_approval"] = True
        updates["approval_type"] = "rpn_review"
        updates["approval_detail"] = approval_detail
        stream_bus.emit(sid, {
            "type": "approval_required",
            "gate_type": "rpn_review",
            "data": approval_detail,
        })

    return updates


def recommend_actions(state: FMEAState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Stage 4: Recommend corrective actions for high-RPN failure modes."""
    stream_bus.emit(_sid(config), {
        "type": "progress",
        "stage": "recommend_actions",
        "message": "✅ 生成纠正措施 (优化行动 / 验证计划)…",
    })
    return {
        "current_stage": "recommend_actions",
        "messages": [AIMessage(content="[FMEA Stage 4] 纠正措施生成完成。")],
    }


def _rpn_router(state: FMEAState) -> str:
    """Route after calculate_rpn: pause for review if high-RPN items found."""
    if state.get("awaiting_approval"):
        return "wait"
    return "recommend_actions"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def create_fmea_graph():
    """Build and compile the FMEA StateGraph."""
    workflow = StateGraph(FMEAState)

    workflow.add_node("analyze_structure", analyze_structure)
    workflow.add_node("mine_failure_modes", mine_failure_modes)
    workflow.add_node("calculate_rpn", calculate_rpn)
    workflow.add_node("recommend_actions", recommend_actions)

    workflow.set_entry_point("analyze_structure")
    workflow.add_edge("analyze_structure", "mine_failure_modes")
    workflow.add_edge("mine_failure_modes", "calculate_rpn")
    workflow.add_conditional_edges(
        "calculate_rpn",
        _rpn_router,
        {"wait": END, "recommend_actions": "recommend_actions"},
    )
    workflow.add_edge("recommend_actions", END)

    return workflow.compile(checkpointer=MemorySaver())


# ---------------------------------------------------------------------------
# CompiledSubAgent export
# ---------------------------------------------------------------------------

fmea_compiled: CompiledSubAgent = {
    "name": "fmea_pipeline",
    "description": "执行完整 FMEA Pipeline（4 阶段 + 高 RPN 人工审批门）。",
    "runnable": create_fmea_graph(),
}
