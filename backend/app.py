"""
Smart Commute Optimization -- FastAPI entry point.

All backend functionality is exposed exclusively through REST endpoints.
The frontend communicates with Azure Maps and other cloud services only
through this API layer; it never accesses Azure keys directly.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routes import commute_router
from backend.middleware import register_error_handlers

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Commute Optimization",
    description=(
        "Planning, Navigation UX, and Sustainability Optimization API. "
        "Exposes Azure Maps route-matrix calculations to the frontend "
        "without leaking any Azure credentials."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

register_error_handlers(app)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(commute_router)


@app.get("/")
async def root():
    """Root health-check / service description."""
    return {
        "service": "smart-commute-optimization",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/commute/optimize",
            "GET  /api/commute/health",
        ],
    }


# ---------------------------------------------------------------------------
# CLI entry point  (python -m backend.app)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
