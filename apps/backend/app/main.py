"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import podcasts

from .config import settings


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks.

    Runs once when the app starts and once when it stops.
    Used for DB connection pools, background task setup, etc.
    """
    logger.info("Backend starting up — env=%s", settings.app_env)
    yield
    logger.info("Backend shutting down")


app = FastAPI(
    title="Personal Podcast Generator",
    version="0.1.0",
    description="Generate personalized news podcasts on a schedule.",
    lifespan=lifespan,
)

# CORS — allow the frontend (Vite default port 5173) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(podcasts.router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is up."""
    return {"status": "ok", "env": settings.app_env}