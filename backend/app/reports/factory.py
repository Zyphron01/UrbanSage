"""
UrbanSage AI — Citizen Report Repository Factory
================================================
Centralized factory for instantiating the appropriate database repository.

Enforcement Rules:
------------------
1. Default Backend is Supabase PostgreSQL:
   Production requires Supabase PostgreSQL (`DATABASE_BACKEND=supabase`, which is default).
2. Explicit Offline Fallback Only:
   SQLite is ONLY used when explicitly requested via `DATABASE_BACKEND=sqlite`.
3. No Silent Fallback:
   If Supabase is selected and credentials are missing or the connection fails,
   the application raises an immediate ReportPersistenceError and logs the failure
   securely. It never silently falls back to SQLite.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from app.reports.base import BaseCitizenReportRepository
from app.reports.exceptions import ReportPersistenceError
from app.reports.repository import SQLiteCitizenReportRepository
from app.reports.supabase_repo import SupabaseCitizenReportRepository

logger = logging.getLogger("urbansage.reports.factory")

_repository_instance: Optional[BaseCitizenReportRepository] = None


def get_database_backend() -> str:
    """
    Get the configured database backend name.
    Defaults to 'supabase' as the primary database.
    """
    return os.getenv("DATABASE_BACKEND", "supabase").strip().lower()


def get_report_repository() -> BaseCitizenReportRepository:
    """
    FastAPI dependency supplying the citizen report repository.
    Can be overridden in tests via app.dependency_overrides.
    """
    global _repository_instance
    if _repository_instance is not None:
        return _repository_instance

    backend = get_database_backend()

    if backend == "supabase":
        logger.info("Initializing primary Supabase PostgreSQL citizen report repository...")
        try:
            _repository_instance = SupabaseCitizenReportRepository()
            logger.info("Supabase PostgreSQL citizen report repository successfully initialized.")
        except Exception as e:
            logger.critical("Fatal error initializing Supabase repository: %s", e)
            raise ReportPersistenceError(
                f"Failed to connect to primary Supabase PostgreSQL database: {e}. "
                "Ensure SUPABASE_URL and SUPABASE_SECRET_KEY are set in environment variables."
            ) from e

    elif backend == "sqlite":
        raise ReportPersistenceError(
            "SQLite is no longer supported as an application database. "
            "Supabase PostgreSQL is the sole persistent database for UrbanSage AI across all portals."
        )

    else:
        raise ReportPersistenceError(
            f"Unsupported DATABASE_BACKEND '{backend}'. Only 'supabase' is supported."
        )

    return _repository_instance


def reset_repository_instance() -> None:
    """
    Reset the cached repository singleton. Useful in test teardown.
    """
    global _repository_instance
    if _repository_instance is not None:
        try:
            _repository_instance.close()
        except Exception:
            pass
        _repository_instance = None
