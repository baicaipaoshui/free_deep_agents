"""Lightweight async event bus for cross-module streaming.

Pipeline nodes and tool wrappers call :func:`emit_current` without knowing
the session_id.  The session_id is bound to the current asyncio task context
via :func:`bind` before the analysis task runs.

Usage::

    # In the background task (analysis.py):
    queue = stream_bus.register(session_id)
    stream_bus.bind(session_id)

    # Anywhere in the call stack (nodes, tools):
    stream_bus.emit_current({"type": "progress", "stage": "...", "message": "..."})

    # Drain the queue and broadcast:
    while not queue.empty():
        await _broadcast(session_id, queue.get_nowait())
"""
from __future__ import annotations

import asyncio
import contextvars
from typing import Any

# Per-session event queues
_queues: dict[str, asyncio.Queue[Any]] = {}

# Context variable so nodes/tools can emit without knowing session_id
_current_session: contextvars.ContextVar[str] = contextvars.ContextVar(
    "fusa_session_id", default=""
)


def register(session_id: str) -> asyncio.Queue:
    """Create and register an event queue for *session_id*."""
    q: asyncio.Queue = asyncio.Queue()
    _queues[session_id] = q
    return q


def bind(session_id: str) -> None:
    """Bind *session_id* to the current async-task context."""
    _current_session.set(session_id)


def get_queue(session_id: str) -> asyncio.Queue | None:
    """Return the queue for *session_id*, or ``None`` if not registered."""
    return _queues.get(session_id)


def unregister(session_id: str) -> None:
    """Remove the queue for *session_id*."""
    _queues.pop(session_id, None)


def emit(session_id: str, event: dict[str, Any]) -> None:
    """Enqueue *event* for *session_id* (non-blocking, safe to call from sync code)."""
    q = _queues.get(session_id)
    if q is not None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # drop silently rather than block


def emit_current(event: dict[str, Any]) -> None:
    """Enqueue *event* for the session bound to the current context."""
    sid = _current_session.get("")
    if sid:
        emit(sid, event)
