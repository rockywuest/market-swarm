"""FastAPI application for Market Swarm.

Wraps the existing CLI engine with a REST API. Serves the dashboard
as static files at the root URL.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .jobs import JobManager
from .routes import init_job_manager, router

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Initialize services on startup."""
    storage_path = os.getenv("MARKET_SWARM_STORAGE_PATH", str(_project_root / "results"))
    manager = JobManager(storage_dir=storage_path)
    init_job_manager(manager)
    yield


app = FastAPI(
    title="Market Swarm API",
    version="1.0.0",
    description="LLM-powered market simulation for product launches",
    lifespan=lifespan,
)

# --- CORS ---

_cors_origins_env = os.getenv("MARKET_SWARM_CORS_ORIGINS", "")
_cors_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if _cors_origins_env:
    _cors_origins.extend(o.strip() for o in _cors_origins_env.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# --- Routes ---


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "1.0.0"}


app.include_router(router)

# --- Static files (dashboard) — must be last (catch-all) ---

_dashboard_dir = _project_root / "dashboard"
if _dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
