"""
UrbanSage AI — Citizen Environmental Reporting Module (Phase 1A)
================================================================
Foundational data models, transparent scoring engine, and SQLite persistence
layer for citizen environmental reporting.
"""

from app.reports.exceptions import (
    DuplicateReportError,
    ReportError,
    ReportNotFoundError,
    ReportPersistenceError,
    ReportValidationError,
)
from app.reports.models import (
    CitizenReport,
    CitizenReportCreate,
    CitizenReportPublic,
    PaginatedReportsResponse,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    VerificationStatus,
)
from app.reports.repository import CitizenReportRepository
from app.reports.scoring import (
    CATEGORY_ACUTE_HAZARD_SCORES,
    calculate_evidence_confidence_score,
    calculate_urgency_score,
)

__all__ = [
    "ProblemCategory",
    "ReportStatus",
    "VerificationStatus",
    "PhotoMetadata",
    "CitizenReportCreate",
    "CitizenReport",
    "CitizenReportPublic",
    "PaginatedReportsResponse",
    "calculate_urgency_score",
    "calculate_evidence_confidence_score",
    "CATEGORY_ACUTE_HAZARD_SCORES",
    "CitizenReportRepository",
    "ReportError",
    "ReportNotFoundError",
    "ReportValidationError",
    "DuplicateReportError",
    "ReportPersistenceError",
]
