"""FastAPI application entrypoint for modelScaniTem API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.routers import inspections, scan, trays
from api.schemas import HealthResponse
from core.inspections import available_trays, ensure_tables

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("modelScaniTem.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing modelScaniTem API...")
    ok, msg = ensure_tables()
    if ok:
        logger.info("Database inspection tables verified.")
    else:
        logger.warning(f"Database offline or unconfigured: {msg}")

    trays_list = available_trays()
    logger.info(f"Loaded {len(trays_list)} tray template(s): {', '.join(trays_list)}")
    yield
    logger.info("Shutting down modelScaniTem API...")


app = FastAPI(
    title="modelScaniTem Inspection API",
    description=(
        "⚡ High-performance REST API for AI-assisted tool tray inspection.\n\n"
        "Features:\n"
        "- 📷 **Live Camera Overlay Guides**: Transparent PNG wireframes for mobile/web viewports.\n"
        "- 🔍 **Multi-Slot Computer Vision**: Quality check, homography alignment, contour & empty-reference matching.\n"
        "- 📊 **Instant Status Reporting**: Correct (🟢), Missing (🔴), Misplaced (🟡), Recheck (↩️).\n"
        "- 🗄️ **Inspection History**: Persistence to database with color-annotated detection images."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for mobile apps, web dashboards, and LINE webhook bridges
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(trays.router, prefix="/api/v1")
app.include_router(scan.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")


@app.get("/", summary="API Root Status")
def root():
    return {
        "service": "modelScaniTem Inspection API",
        "version": __version__,
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "trays": "/api/v1/trays",
            "tray_guide": "/api/v1/trays/{tray_id}/guide",
            "scan_tray": "/api/v1/scan/tray",
            "scan_tool": "/api/v1/scan/tool",
            "inspections": "/api/v1/inspections",
        },
    }


@app.get("/health", response_model=HealthResponse, summary="Service Health Check")
def health_check() -> HealthResponse:
    """Return system status and available tray configurations."""
    trays_list = available_trays()
    return HealthResponse(
        status="ok",
        version=__version__,
        timestamp=datetime.utcnow().isoformat() + "Z",
        available_trays=trays_list,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

