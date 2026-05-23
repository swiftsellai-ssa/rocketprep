"""FastAPI application entry point for RocketPrep Simulator."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes.simulate import router as simulate_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models.simulation_record import SimulationRecord  # noqa: F401

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown."""
    logger.info(
        "Starting RocketPrep Simulator [%s] on %s:%s",
        settings.app_env,
        settings.app_host,
        settings.app_port,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down RocketPrep Simulator")


app = FastAPI(
    title="RocketPrep Simulator",
    description=(
        "API for simulating rocket material preparation and protective "
        "coating workflows."
    ),
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.app_debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulate_router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the RocketPrep single-page frontend."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get(
    "/health",
    summary="Health check",
    description="Returns service health status for load balancers and probes.",
)
async def health() -> dict[str, str]:
    """Confirm the API is running."""
    return {"status": "ok", "service": "rocketprep"}
