"""Safety gate hooks for the IAV FuSa Platform.

These functions are applied as post-processing steps on LangGraph state dicts.
They inspect analysis results and set the `awaiting_approval` flag when human
review is required, or record validation warnings automatically.

Hook categories
---------------
- **Approval gates** (human required): `asil_gate_hook`, `rpn_gate_hook`
- **Automatic validators** (no human): `fta_logic_check_hook`, `fta_xref_fmea_hook`
"""

from __future__ import annotations

from typing import Any

from app.config import RPN_THRESHOLD


def asil_gate_hook(state: dict[str, Any]) -> dict[str, Any]:
    """Pause after S/E/C/O estimation to require human confirmation of ASIL ratings.

    Sets `awaiting_approval=True` and populates `approval_detail` with the
    current S/E/C/O ratings so the reviewer can inspect them via the
    `/api/approval` endpoint.

    Args:
        state: Current LangGraph state dict.

    Returns:
        Updated state dict with approval gate fields populated.
    """
    seco = state.get("seco_ratings", [])
    if not seco:
        return state

    state["awaiting_approval"] = True
    state["approval_type"] = "asil_confirmation"
    state["approval_detail"] = {
        "message": "请确认以下 S/E/C/O 评估结果和 ASIL 定级",
        "data": seco,
    }
    return state


def rpn_gate_hook(state: dict[str, Any]) -> dict[str, Any]:
    """Pause when one or more failure modes exceed the RPN threshold.

    Args:
        state: Current LangGraph state dict.

    Returns:
        Updated state with approval gate fields if high-RPN items exist.
    """
    high_risk = [
        fm for fm in state.get("failure_modes", [])
        if fm.get("rpn", 0) > RPN_THRESHOLD
    ]
    if not high_risk:
        return state

    state["awaiting_approval"] = True
    state["approval_type"] = "rpn_review"
    state["approval_detail"] = {
        "message": f"{len(high_risk)} 个失效模式 RPN > {RPN_THRESHOLD}，需人工审核",
        "data": high_risk,
    }
    return state


def fta_logic_check_hook(state: dict[str, Any]) -> dict[str, Any]:
    """Automatically validate fault-tree gate consistency.

    Checks that every AND/OR gate has at least two children.  Records errors
    in `validation_errors` and sets `needs_rework=True` without requiring
    human intervention.

    Args:
        state: Current LangGraph state dict.

    Returns:
        Updated state with validation results.
    """
    tree = state.get("fault_tree", {})
    errors: list[str] = []

    for node_id, node in tree.items():
        node_type = node.get("node_type", "")
        children = node.get("children", [])
        if node_type in ("and_gate", "or_gate") and len(children) < 2:
            errors.append(
                f"节点 {node_id} ({node_type}) 子节点不足 2 个（当前：{len(children)}）。"
            )

    if errors:
        state["validation_errors"] = errors
        state["needs_rework"] = True

    return state


def fta_xref_fmea_hook(state: dict[str, Any]) -> dict[str, Any]:
    """Check that every FTA basic event maps to an FMEA failure mode.

    Unmapped events are recorded in `unmapped_events` and a warning is added
    to the state.  This is an informational check — it does not block progress.

    Args:
        state: Current LangGraph state dict.

    Returns:
        Updated state with cross-reference gap information.
    """
    basic_events = state.get("basic_events", [])
    fmea_modes = state.get("fmea_failure_modes", [])
    fmea_ids = {m.get("id") for m in fmea_modes}
    unmapped = [e.get("id") for e in basic_events if e.get("id") not in fmea_ids]

    if unmapped:
        state["unmapped_events"] = unmapped
        state["warning"] = f"{len(unmapped)} 个底事件未映射到 FMEA 失效模式: {', '.join(str(u) for u in unmapped)}"

    return state
