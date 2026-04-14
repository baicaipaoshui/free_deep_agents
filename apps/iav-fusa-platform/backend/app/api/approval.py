"""Approval API router — human-in-the-loop review gates.

When the HARA pipeline pauses at the interrupt_before=["classify_asil"]
boundary, the session enters AWAITING_APPROVAL status and the frontend
opens a review dialog.  The engineer then calls:

  POST /api/approval/{session_id}/approve   — confirm (optionally with edits)
  POST /api/approval/{session_id}/reject    — cancel the session

On approval this module:
1. Writes an audit_log row to PostgreSQL (ISO 26262 traceability).
2. Calls hara_graph.aupdate_state() if the engineer modified seco_ratings.
3. Calls hara_graph.ainvoke(None, config) to resume past the interrupt.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agent.graphs.hara_pipeline import hara_graph
from app.db import get_pool
from app.models.schemas import (
    AnalysisStatus,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    PendingApproval,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Shared session store — populated by analysis.py
from app.api.analysis import _sessions  # noqa: E402

# In-memory approval audit (supplemental to DB; used for GET responses)
_approvals: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# PostgreSQL audit_log helper
# ---------------------------------------------------------------------------


async def _write_audit_log(
    thread_id: str,
    stage: str,
    engineer_id: str,
    decision: str,
    original_data: dict | None,
    modified_data: dict | None,
) -> None:
    """Insert one row into audit_log table."""
    pool = get_pool()
    if pool is None:
        logger.warning("[audit_log] DB pool unavailable — skipping audit row for %s", thread_id)
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log
                    (thread_id, stage, engineer_id, decision, original_data, modified_data)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
                """,
                thread_id,
                stage,
                engineer_id,
                decision,
                json.dumps(original_data) if original_data is not None else None,
                json.dumps(modified_data) if modified_data is not None else None,
            )
    except Exception:
        logger.exception("[audit_log] failed to write row for thread_id=%s", thread_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pending_sessions() -> list[dict[str, Any]]:
    return [s for s in _sessions.values() if s.get("status") == AnalysisStatus.AWAITING_APPROVAL]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[PendingApproval])
async def list_pending_approvals() -> list[PendingApproval]:
    """Return all analysis sessions waiting for human review."""
    pending = []
    for s in _get_pending_sessions():
        raw = s.get("result") or {}
        pending.append(
            PendingApproval(
                session_id=s["session_id"],
                project_id=s["project_id"],
                analysis_type=s["analysis_type"],
                gate_type=raw.get("approval_type", "unknown"),
                gate_data=raw,
                created_at=s["created_at"],
            )
        )
    return pending


@router.post("/{session_id}/approve", response_model=ApprovalResponse)
async def approve(session_id: str, payload: ApprovalRequest) -> ApprovalResponse:
    """Approve the ASIL review gate and resume the HARA pipeline."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if session.get("status") != AnalysisStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_id}' is not awaiting approval (status: {session['status']}).",
        )

    now = datetime.now(tz=timezone.utc)
    original_data = (session.get("result") or {}).get("seco_ratings")
    modified_data = payload.modified_data  # dict | None; reviewer edits, if any

    # 1. Write audit log
    await _write_audit_log(
        thread_id=session_id,
        stage="estimate_seco",
        engineer_id=payload.reviewer_id,
        decision="approved",
        original_data=original_data,
        modified_data=modified_data,
    )

    # 2. If the reviewer modified seco_ratings, push the update into the graph state
    if hara_graph is not None:
        hara_config = {"configurable": {"thread_id": session_id}}
        if modified_data is not None:
            await hara_graph.aupdate_state(
                hara_config,
                {"seco_ratings": modified_data},
            )

        # 3. Resume execution past the interrupt
        try:
            await hara_graph.ainvoke(None, hara_config)
        except Exception:
            logger.exception("[%s] hara_graph resume failed", session_id[:8])

    # Update session
    _approvals[session_id] = {
        "session_id": session_id,
        "status": ApprovalStatus.APPROVED,
        "comment": payload.comment,
        "reviewer_id": payload.reviewer_id,
        "reviewed_at": now,
    }
    session["status"] = AnalysisStatus.RUNNING
    session["updated_at"] = now

    return ApprovalResponse(**_approvals[session_id])


@router.post("/{session_id}/reject", response_model=ApprovalResponse)
async def reject(session_id: str, payload: ApprovalRequest) -> ApprovalResponse:
    """Reject the review gate and cancel the analysis session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if session.get("status") != AnalysisStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_id}' is not awaiting approval (status: {session['status']}).",
        )

    now = datetime.now(tz=timezone.utc)
    original_data = (session.get("result") or {}).get("seco_ratings")

    await _write_audit_log(
        thread_id=session_id,
        stage="estimate_seco",
        engineer_id=payload.reviewer_id,
        decision="rejected",
        original_data=original_data,
        modified_data=None,
    )

    _approvals[session_id] = {
        "session_id": session_id,
        "status": ApprovalStatus.REJECTED,
        "comment": payload.comment,
        "reviewer_id": payload.reviewer_id,
        "reviewed_at": now,
    }
    session["status"] = AnalysisStatus.CANCELLED
    session["updated_at"] = now
    session["error"] = f"Rejected by {payload.reviewer_id}: {payload.comment}"

    return ApprovalResponse(**_approvals[session_id])
