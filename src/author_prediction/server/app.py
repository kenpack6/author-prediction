import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI

from author_prediction.server.routers import projects_router
from author_prediction.server.worker import InferenceWorker

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        db_pool = await asyncpg.create_pool(database_url)
        app.state.db_pool = db_pool
    else:
        raise Exception("Database URL not provided")

    worker = InferenceWorker(database_url)
    app.state.worker = worker
    worker.start()
    yield
    worker.shutdown()
    if app.state.db_pool is not None:
        await app.state.db_pool.close()


app = FastAPI(title="Author Prediction API", lifespan=lifespan)
app.include_router(projects_router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}




