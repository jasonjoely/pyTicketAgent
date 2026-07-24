"""asyncpg connection pool helpers."""

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    """Create an asyncpg pool using library defaults."""
    return await asyncpg.create_pool(dsn)


async def close_pool(pool: asyncpg.Pool) -> None:
    """Close an asyncpg pool and release all connections."""
    await pool.close()
