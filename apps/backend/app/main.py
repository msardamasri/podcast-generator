"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import podcasts, preferences, admin

from .config import settings

import uuid

from sqlalchemy import select

from .db import AsyncSessionLocal
from .models import User


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("Backend starting up — env=%s", settings.app_env)

    # Ensure the demo user exists. For the take-home we operate with a
    # single user; in production this would come from auth.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.default_user_email)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(email=settings.default_user_email)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Created demo user %s", user.id)
        else:
            logger.info("Using existing demo user %s", user.id)
        app.state.demo_user_id = user.id

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
app.include_router(preferences.router)
app.include_router(admin.router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is up."""
    return {"status": "ok", "env": settings.app_env}