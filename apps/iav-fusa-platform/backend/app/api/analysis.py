"""Analysis API router — WebSocket streaming via LangChain callbacks.

架构说明
--------
- ``_run_analysis`` 用 ``ainvoke`` + LangChain AsyncCallbackHandler 执行分析。
  Callback 在每个 chain_start / tool_start / tool_end 时广播事件，比
  ``astream_events`` 更可靠（DeepAgents 不一定正确实现 astream_events）。
- ``ainvoke`` 保证返回后立即发送 ``complete``，不会卡住。
- 前端同时保留 HTTP 轮询（GET /api/analysis/{id}）作为兜底。

WebSocket 事件类型
------------------
- ``{"type": "status",   "status": "running|completed|..."}``
- ``{"type": "progress", "stage": "<node>",  "message": "<label>"}``
- ``{"type": "subagent", "agent": "<name>",  "message": "<label>"}``
- ``{"type": "tool_start","tool": "<name>",  "message": "...", "input": {...}}``
- ``{"type": "tool_end",  "tool": "<name>"}``
- ``{"type": "approval_required", "gate_type": "...", "data": {...}}``
- ``{"type": "complete",  "result": {...}}``
- ``{"type": "error",     "error": "..."}``
- ``{"type": "ping"}``
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import stream_bus
from app.db import get_pool
from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
)
from app.router.intent import route_request

logger = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict[str, dict[str, Any]] = {}
_ws_connections: dict[str, WebSocket] = {}


# ---------------------------------------------------------------------------
# DB helpers (best-effort — silently skip if pool unavailable)
# ---------------------------------------------------------------------------


async def _db_upsert_session(session: dict[str, Any]) -> None:
    pool = get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO analysis_session
                    (session_id, project_id, analysis_type, status,
                     input_text, result, error, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)
                ON CONFLICT (session_id) DO UPDATE SET
                    status      = EXCLUDED.status,
                    result      = EXCLUDED.result,
                    error       = EXCLUDED.error,
                    updated_at  = EXCLUDED.updated_at
                """,
                session["session_id"],
                session.get("project_id"),
                session.get("analysis_type"),
                session["status"],
                session.get("input_text"),
                json.dumps(session["result"]) if session.get("result") is not None else None,
                session.get("error"),
                session["created_at"],
                session["updated_at"],
            )
    except Exception:
        logger.debug("DB upsert session failed", exc_info=True)


async def _db_append_event(session_id: str, event: dict[str, Any]) -> None:
    pool = get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO session_event (session_id, event_type, payload)
                VALUES ($1, $2, $3::jsonb)
                """,
                session_id,
                event.get("type", "unknown"),
                json.dumps(event),
            )
    except Exception:
        logger.debug("DB append event failed", exc_info=True)

# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

_STAGE_LABELS: dict[str, str] = {
    "parse_item_definition":  "📋 解析 Item Definition",
    "identify_failure_modes": "🔍 识别失效模式 (Loss/Degradation/Unintended/Incorrect)",
    "derive_hazards":         "⚠️  推导车辆级危害",
    "estimate_seco":          "📊 评估 S/E/C/O 参数",
    "classify_asil":          "🏷️  确定 ASIL 等级",
    "generate_safety_goals":  "🎯 生成安全目标",
    "analyze_structure":      "🏗️  系统结构分析",
    "mine_failure_modes":     "🔍 失效模式挖掘",
    "calculate_rpn":          "📊 计算 RPN (S×O×D)",
    "recommend_actions":      "✅ 生成纠正措施",
    "define_top_event":       "🌳 定义顶事件",
    "decompose_gates":        "🔀 AND/OR 逻辑门分解",
    "map_basic_events":       "🗺️  底事件映射",
    "validate_logic":         "✔️  故障树逻辑校验",
    "hara_analyst":           "🤖 HARA 子代理分析中",
    "fmea_analyst":           "🤖 FMEA 子代理分析中",
    "fta_analyst":            "🤖 FTA 子代理分析中",
}

_SUBAGENT_NAMES = frozenset({"hara_analyst", "fmea_analyst", "fta_analyst"})
_SKIP_NODES = frozenset({"__start__", "__end__", "tools", "agent", ""})


def _stage_label(node: str) -> str:
    return _STAGE_LABELS.get(node, f"▶ {node}")


def _tool_msg(name: str, inp: Any) -> str:
    if not isinstance(inp, dict):
        try:
            import json
            inp = json.loads(inp) if isinstance(inp, str) else {}
        except Exception:
            inp = {}
    if name == "search_knowledge_base":
        return f"📚 检索知识库 [{inp.get('collection', '')}]: {str(inp.get('query', ''))[:80]}"
    if name == "asil_lookup":
        return f"🔢 ASIL 查表: S={inp.get('severity')} / E={inp.get('exposure')} / C={inp.get('controllability')}"
    return f"🔧 {name}: {str(inp)[:60]}"


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------


async def _broadcast(session_id: str, message: dict[str, Any]) -> None:
    ws = _ws_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(message)
        except Exception:
            pass
    # Persist all non-ping events to session_event table
    if message.get("type") not in ("ping", "status"):
        asyncio.create_task(_db_append_event(session_id, message))


async def _drain_bus(session_id: str) -> None:
    q = stream_bus.get_queue(session_id)
    if q is None:
        return
    while not q.empty():
        try:
            event = q.get_nowait()
            await _broadcast(session_id, event)
            if event.get("type") == "approval_required":
                s = _sessions.get(session_id)
                if s:
                    s["status"] = AnalysisStatus.AWAITING_APPROVAL
                    s["updated_at"] = datetime.now(tz=timezone.utc)
        except asyncio.QueueEmpty:
            break


# ---------------------------------------------------------------------------
# Streaming callback
# ---------------------------------------------------------------------------


class _StreamCallback(AsyncCallbackHandler):
    """Bridges LangChain execution events to the WebSocket client."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self._sid = session_id
        self._seen: set[str] = set()

    # -- Chain (graph node) events --

    async def on_chain_start(
        self, serialized: dict, inputs: dict, *,
        run_id: Any = None, parent_run_id: Any = None,
        tags: list | None = None, metadata: dict | None = None, **kwargs: Any
    ) -> None:
        await _drain_bus(self._sid)
        node = (
            (metadata or {}).get("langgraph_node")
            or (serialized or {}).get("name", "")
        )
        if not node or node in _SKIP_NODES or node in self._seen:
            return
        self._seen.add(node)
        logger.info("[%s] node: %s", self._sid[:8], node)
        if node in _SUBAGENT_NAMES:
            await _broadcast(self._sid, {
                "type": "subagent", "agent": node, "message": _stage_label(node),
            })
        else:
            await _broadcast(self._sid, {
                "type": "progress", "stage": node, "message": _stage_label(node),
            })

    async def on_chain_end(
        self, outputs: dict, *,
        run_id: Any = None, parent_run_id: Any = None,
        tags: list | None = None, metadata: dict | None = None, **kwargs: Any
    ) -> None:
        await _drain_bus(self._sid)
        # Detect approval gate in pipeline state output
        if isinstance(outputs, dict) and outputs.get("awaiting_approval"):
            await _broadcast(self._sid, {
                "type": "approval_required",
                "gate_type": outputs.get("approval_type", "unknown"),
                "data": outputs.get("approval_detail", {}),
            })
            s = _sessions.get(self._sid)
            if s:
                s["status"] = AnalysisStatus.AWAITING_APPROVAL
                s["updated_at"] = datetime.now(tz=timezone.utc)

    # -- Tool events --

    async def on_tool_start(
        self, serialized: dict, input_str: str, *,
        run_id: Any = None, **kwargs: Any
    ) -> None:
        name = (serialized or {}).get("name", "")
        logger.info("[%s] tool: %s", self._sid[:8], name)
        await _broadcast(self._sid, {
            "type": "tool_start",
            "tool": name,
            "message": _tool_msg(name, input_str),
            "input": input_str if isinstance(input_str, dict) else {},
        })

    async def on_tool_end(self, output: str, *, run_id: Any = None, **kwargs: Any) -> None:
        await _broadcast(self._sid, {"type": "tool_end", "tool": ""})

    # -- LLM events (just log, don't flood WS) --

    async def on_llm_start(
        self, serialized: dict, prompts: list, *,
        run_id: Any = None, metadata: dict | None = None, **kwargs: Any
    ) -> None:
        node = (metadata or {}).get("langgraph_node", "")
        logger.info("[%s] llm_start (node=%s)", self._sid[:8], node)

    async def on_llm_end(self, response: Any, *, run_id: Any = None, **kwargs: Any) -> None:
        logger.info("[%s] llm_end", self._sid[:8])


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------


def _build_messages(session: dict[str, Any], new_user_text: str) -> list:
    """Build LangChain message list from session history + new user message."""
    msgs = []
    for turn in session.get("history", []):
        if turn["role"] == "user":
            msgs.append(HumanMessage(content=turn["content"]))
        else:
            msgs.append(AIMessage(content=turn["content"]))
    msgs.append(HumanMessage(content=new_user_text))
    return msgs


async def _run_analysis(session_id: str, session: dict[str, Any],
                        user_text: str | None = None) -> None:
    from app.agent.graphs.hara_pipeline import hara_graph  # noqa: PLC0415
    from app.agent.orchestrator import get_orchestrator  # noqa: PLC0415

    stream_bus.register(session_id)
    stream_bus.bind(session_id)

    session["status"] = AnalysisStatus.RUNNING
    session["updated_at"] = datetime.now(tz=timezone.utc)
    await _db_upsert_session(session)
    await _broadcast(session_id, {"type": "status", "status": AnalysisStatus.RUNNING})

    try:
        agent = get_orchestrator()

        if user_text is None:
            # First turn: build structured prompt
            route = route_request(session["input_text"])
            prompt = (
                f"请执行 {route['analysis_type'].upper()} 分析。\n\n"
                f"分析对象：{session['input_text']}"
            )
        else:
            # Follow-up turn: user's reply text
            prompt = user_text

        messages = _build_messages(session, prompt)

        callback = _StreamCallback(session_id)
        logger.info("[%s] invoking agent, turns=%d", session_id[:8], len(messages))

        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [callback],
        }

        result = await agent.ainvoke(
            {"messages": messages},
            config=config,
        )

        await _drain_bus(session_id)

        # ---------------------------------------------------------------
        # Detect LangGraph interrupt: hara_graph paused before classify_asil
        # ---------------------------------------------------------------
        if hara_graph is not None:
            hara_config = {"configurable": {"thread_id": session_id}}
            try:
                snapshot = await hara_graph.aget_state(hara_config)
                if snapshot.next:  # e.g. ('classify_asil',)
                    state_vals = snapshot.values
                    await _broadcast(session_id, {
                        "type": "approval_required",
                        "gate_type": "asil_confirmation",
                        "thread_id": session_id,
                        "stage": "estimate_seco",
                        "data": {
                            "message": "请确认以下 S/E/C/O 评估结果和 ASIL 定级",
                            "seco_ratings": state_vals.get("seco_ratings", []),
                        },
                    })
                    session["status"] = AnalysisStatus.AWAITING_APPROVAL
                    session["updated_at"] = datetime.now(tz=timezone.utc)
                    session["result"] = {
                        "approval_type": "asil_confirmation",
                        "seco_ratings": state_vals.get("seco_ratings", []),
                    }
                    await _db_upsert_session(session)
                    await _broadcast(session_id, {
                        "type": "status",
                        "status": AnalysisStatus.AWAITING_APPROVAL,
                    })
                    return  # do not mark completed yet
            except Exception:
                pass  # hara_graph not used for this session — ignore

        # Log raw result structure for debugging
        logger.info("[%s] raw result type=%s keys=%s",
                    session_id[:8],
                    type(result).__name__,
                    list(result.keys()) if isinstance(result, dict) else "N/A")

        # Save history for multi-turn
        session["history"].append({"role": "user", "content": prompt})

        # Extract final text — try multiple result shapes DeepAgents may return
        final_text = ""
        if isinstance(result, dict):
            # Shape 1: {"messages": [AIMessage(content="...")]}
            for msg in reversed(result.get("messages", [])):
                content = getattr(msg, "content", None)
                if content and isinstance(content, str) and content.strip():
                    final_text = content
                    logger.info("[%s] extracted from messages[-1]", session_id[:8])
                    break
            # Shape 2: {"output": "..."} or {"result": "..."}
            if not final_text:
                for key in ("output", "result", "response", "text", "answer"):
                    v = result.get(key)
                    if v and isinstance(v, str) and v.strip():
                        final_text = v
                        logger.info("[%s] extracted from result[%s]", session_id[:8], key)
                        break
        elif isinstance(result, str) and result.strip():
            final_text = result

        logger.info("[%s] complete, text_len=%d", session_id[:8], len(final_text))

        if final_text:
            session["history"].append({"role": "assistant", "content": final_text})

        session["result"] = {"summary": final_text}
        session["status"] = AnalysisStatus.COMPLETED
        session["updated_at"] = datetime.now(tz=timezone.utc)
        await _db_upsert_session(session)
        await _broadcast(session_id, {"type": "complete", "result": session["result"]})

    except Exception as exc:
        logger.exception("[%s] analysis failed", session_id[:8])
        session["status"] = AnalysisStatus.FAILED
        session["error"] = str(exc)
        session["updated_at"] = datetime.now(tz=timezone.utc)
        await _db_upsert_session(session)
        await _broadcast(session_id, {"type": "error", "error": str(exc)})

    finally:
        stream_bus.unregister(session_id)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=AnalysisResponse, status_code=202)
async def start_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    now = datetime.now(tz=timezone.utc)
    session_id = str(uuid.uuid4())
    session: dict[str, Any] = {
        "session_id": session_id,
        "project_id": payload.project_id,
        "analysis_type": payload.analysis_type,
        "input_text": payload.input_text,
        "options": payload.options,
        "status": AnalysisStatus.PENDING,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "history": [],  # list of {"role": "user"|"assistant", "content": "..."}
    }
    _sessions[session_id] = session
    await _db_upsert_session(session)
    asyncio.create_task(_run_analysis(session_id, session))
    return AnalysisResponse(**{k: v for k, v in session.items() if k != "input_text"})


@router.get("/{session_id}", response_model=AnalysisResponse)
async def get_analysis(session_id: str) -> AnalysisResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return AnalysisResponse(**{k: v for k, v in session.items() if k != "input_text"})


@router.get("/{session_id}/history")
async def get_history(session_id: str) -> list[dict]:
    """Return the full conversation history for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session.get("history", [])


@router.post("/{session_id}/reply", response_model=AnalysisResponse)
async def reply_analysis(session_id: str, payload: dict) -> AnalysisResponse:
    """Send a follow-up message to a completed/failed session.

    Body: {"message": "...用户补充信息或追问..."}
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if session["status"] == AnalysisStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Session is still running.")

    user_message = (payload.get("message") or "").strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="message field is required.")

    # Reset session for next turn
    session["status"] = AnalysisStatus.PENDING
    session["result"] = None
    session["error"] = None
    session["updated_at"] = datetime.now(tz=timezone.utc)

    asyncio.create_task(_run_analysis(session_id, session, user_text=user_message))
    return AnalysisResponse(**{k: v for k, v in session.items() if k != "input_text"})


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@router.websocket("/ws/{session_id}")
async def analysis_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    _ws_connections[session_id] = websocket

    session = _sessions.get(session_id)
    if session:
        await websocket.send_json({"type": "status", "status": session["status"]})
        # If analysis already completed before WS connected, send result immediately
        if session["status"] == AnalysisStatus.COMPLETED and session.get("result"):
            await websocket.send_json({"type": "complete", "result": session["result"]})
        elif session["status"] == AnalysisStatus.FAILED and session.get("error"):
            await websocket.send_json({"type": "error", "error": session["error"]})

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.pop(session_id, None)
