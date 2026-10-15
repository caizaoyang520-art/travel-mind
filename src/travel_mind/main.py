from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import (
    AsyncPostgresSaver,
)

from travel_mind.api.routes import router as travel_router
from travel_mind.config import get_settings
from travel_mind.graph.workflow import build_travel_graph


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """初始化并关闭应用共享资源。"""

    settings = get_settings()

    database_url = settings.database_url.get_secret_value().replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )

    async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
        await checkpointer.setup()

        app.state.travel_graph = build_travel_graph(checkpointer)
        app.state.travel_checkpointer = checkpointer

        yield


app = FastAPI(
    title="TravelMind",
    description="智能旅行规划与动态执行 Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(travel_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "TravelMind",
    }
