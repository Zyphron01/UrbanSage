"""
UrbanSage AI — FastAPI Application Entry Point
==============================================
Main web application serving citizen environmental reporting and decision support.

Startup:
--------
    python -m uvicorn app.main:app --reload

Configuration:
--------------
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins.
  Defaults to local Next.js frontend ("http://localhost:3000,http://127.0.0.1:3000").
- `REPORTS_DB_PATH`: SQLite database file path.
  Defaults to "urbansage_reports.db" in the backend working directory.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
from dotenv import load_dotenv

# Load local environment configuration if present
load_dotenv(override=True)

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import AuthenticatedUser, get_current_user
from app.api.admin import router as admin_router
from app.api.optimizer import router as optimizer_router
from app.api.reports import router as reports_router
from app.reports.exceptions import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportPersistenceError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("urbansage.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for clean startup and shutdown."""
    logger.info("UrbanSage AI API server starting up...")
    yield
    logger.info("UrbanSage AI API server shutting down...")


app = FastAPI(
    title="UrbanSage AI API",
    description=(
        "Urban sustainability decision-support and citizen environmental problem reporting platform. "
        "Provides transparent scoring, local persistence, and explainable decision tools."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
# Strict, configurable origin list — wildcard '*' is never used by default.
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Admin-API-Key", "X-API-Key"],
)

# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------


@app.exception_handler(ReportNotFoundError)
async def handle_report_not_found(request: Request, exc: ReportNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateReportError)
async def handle_duplicate_report(request: Request, exc: DuplicateReportError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ReportPersistenceError)
async def handle_persistence_error(request: Request, exc: ReportPersistenceError) -> JSONResponse:
    # Log the full database error internally, but return a safe generic message to client
    logger.error("Internal database persistence error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Internal details have been logged."},
    )


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    # Never leak raw stack traces or internal errors to callers
    logger.critical("Unhandled exception processing %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ---------------------------------------------------------------------------
# Core Endpoints & Routers
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["System"],
)
async def health_check() -> dict:
    """Service health and liveness probe."""
    from app.reports.factory import get_database_backend

    return {
        "status": "healthy",
        "service": "UrbanSage AI API",
        "version": "1.0.0",
        "database_backend": get_database_backend(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Authentication & Demo Token Endpoint
# ---------------------------------------------------------------------------
from pydantic import BaseModel, Field

class TokenRequest(BaseModel):
    user_id: str = Field(default="demo-admin-1")
    role: str = Field(default="administrator")
    department: str = Field(default="Environmental Protection Division")
    expires_in_hours: int = Field(default=24)

@app.post(
    "/api/auth/token",
    summary="Issue demo JWT access token",
    tags=["Authentication"],
)
async def issue_token(payload: TokenRequest) -> dict:
    """Issues a signed JWT access token for testing and dashboard access."""
    from app.auth import create_access_token, RoleType

    # In production environments, arbitrary privileged role minting is disabled
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production" and payload.role in ("administrator", "contractor", "system"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileged token self-issuance is disabled in production environments.",
        )

    valid_roles = ("administrator", "contractor", "citizen", "system")
    role = payload.role if payload.role in valid_roles else "citizen"
    token = create_access_token(
        user_id=payload.user_id,
        role=role,  # type: ignore
        department=payload.department,
        expires_in_hours=payload.expires_in_hours,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": payload.user_id,
        "role": role,
    }


@app.get(
    "/api/auth/me",
    summary="Get verified user profile and role",
    tags=["Authentication"],
)
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Returns the verified identity, role, and claims for the authenticated caller."""
    return {
        "user_id": current_user.user_id,
        "role": current_user.role,
        "email": current_user.email,
        "name": current_user.name,
        "department": current_user.department,
        "vendor_id": current_user.vendor_id,
        "is_admin": current_user.is_admin,
        "is_contractor": current_user.is_contractor,
    }


# Register domain routers
from app.api.accountability import router as accountability_router

app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(optimizer_router)
app.include_router(accountability_router)


