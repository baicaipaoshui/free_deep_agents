"""Asyncpg connection pool — module-level singleton.

Usage
-----
Call ``await init_pool()`` once at application startup (lifespan handler).
Then call ``get_pool()`` anywhere to acquire connections::

    async with get_pool().acquire() as conn:
        await conn.execute(...)

Call ``await close_pool()`` on shutdown.
"""

from __future__ import annotations

import logging

import asyncpg

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the shared asyncpg connection pool."""
    global _pool
    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("DB pool initialised: %s", DATABASE_URL.split("@")[-1])
    except Exception:
        logger.exception("DB pool init failed — DB persistence disabled")
        _pool = None


async def close_pool() -> None:
    """Close the pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    """Return the pool, or None if unavailable (DB not configured)."""
    return _pool
