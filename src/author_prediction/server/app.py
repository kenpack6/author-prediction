import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI

from author_prediction.server.dependencies import DbConn, get_db
from author_prediction.server.routers import projects_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        app.state.db_pool = await asyncpg.create_pool(database_url)
    else:
        app.state.db_pool = None
    yield
    if app.state.db_pool is not None:
        await app.state.db_pool.close()


app = FastAPI(title="Author Prediction API", lifespan=lifespan)
app.include_router(projects_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}




