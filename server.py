from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.managers import ALL_MANAGERS_MAP
from app.modules.logger import bastion_logger
from app.pipelines import PIPELINES_MAP
from app.routers.manager import manager_router
from app.routers.flow import flow_router
from settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app_: FastAPI):
    for manager in PIPELINES_MAP.values():
        await manager.activate()
    yield
    for manager in ALL_MANAGERS_MAP.values():
        await manager.close_connections()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    description="API for LLM Protection",
    version="1.0.0",
    prefix="/api/v1",
)

app.include_router(flow_router)
app.include_router(manager_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    bastion_logger.info(f"[{settings.PROJECT_NAME}] Server is running: {settings.HOST}:{settings.PORT}")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="warning")
