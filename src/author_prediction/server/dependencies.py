from typing import Annotated, AsyncIterator, AsyncGenerator

import asyncpg
from fastapi import Depends, Request

from author_prediction.server.worker import InferenceWorker


async def get_db(request: Request) -> AsyncIterator[asyncpg.Connection]:
    if request.app.state.db_pool is None:
        raise RuntimeError("Database connection pool is not initialized")
    async with request.app.state.db_pool.acquire() as connection:
        yield connection


DbConn = Annotated[asyncpg.Connection, Depends(get_db)]

async def get_worker(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    yield request.app.state.worker

Worker = Annotated[InferenceWorker, Depends(get_worker)]