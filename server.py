from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.managers.similarity.manager import similarity_manager
from app.modules.logger import bastion_logger
from app.routers.pipeline import pipeline_router
from settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app_: FastAPI):
    yield
    await similarity_manager.close_connections()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan, description="API for LLM Protection", version="1.0.0")

app.include_router(pipeline_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="warning")
    bastion_logger.info("Server is running: %s:%s", settings.HOST, settings.PORT)
