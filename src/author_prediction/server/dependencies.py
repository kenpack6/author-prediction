from typing import Annotated, AsyncIterator

import asyncpg
from fastapi import Depends, Request


async def get_db(request: Request) -> AsyncIterator[asyncpg.Connection]:
    if request.app.state.db_pool is None:
        raise RuntimeError("Database connection pool is not initialized")
    async with request.app.state.db_pool.acquire() as connection:
        yield connection


DbConn = Annotated[asyncpg.Connection, Depends(get_db)]
