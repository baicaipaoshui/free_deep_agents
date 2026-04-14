"""IAV FuSa Platform — FastAPI application entry point.

Starts the FastAPI server, registers routers, and sets up
LangSmith tracing and CORS on startup.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graphs.hara_pipeline import close_hara_graph, init_hara_graph
from app.api import analysis, approval, projects
from app.config import LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_TRACING
from app.db import close_pool, get_pool, init_pool

logger = logging.getLogger(__name__)


async def _recover_interrupted_sessions() -> None:
    """On startup, mark any sessions stuck in running/pending as interrupted."""
    pool = get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE analysis_session
                SET    status     = 'interrupted',
                       updated_at = NOW()
                WHERE  status IN ('running', 'pending')
                """
            )
        logger.info("Startup recovery: %s", result)
    except Exception:
        logger.exception("Startup recovery query failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure services on startup / teardown."""
    if LANGSMITH_TRACING and LANGSMITH_API_KEY:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", LANGSMITH_PROJECT)

    await init_pool()
    await _recover_interrupted_sessions()
    await init_hara_graph()
    yield
    await close_hara_graph()
    await close_pool()


app = FastAPI(
    title="IAV FuSa Platform",
    description="AI-powered functional-safety analysis: HARA, FMEA, FTA via multi-agent orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(approval.router, prefix="/api/approval", tags=["approval"])


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
