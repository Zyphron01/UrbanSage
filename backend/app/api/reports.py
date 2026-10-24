"""
UrbanSage AI — Citizen Reporting REST API Router
=================================================
FastAPI endpoints for citizen environmental problem reporting.

Endpoints:
----------
- POST /api/reports: Submit a new citizen report (201 Created).
- GET  /api/reports: Retrieve paginated reports with optional category/status filters.
- GET  /api/reports/{report_id}: Retrieve a single report by ID (404 if missing).

Privacy & Security:
-------------------
All public endpoints serialize responses into `CitizenReportPublic`, which
strictly omits private `reporter_contact` information.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import AuthenticatedUser, require_admin_or_contractor

from app.reports.exceptions import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportPersistenceError,
    ReportValidationError,
)
from app.reports.base import BaseCitizenReportRepository
from app.reports.factory import get_report_repository
from app.reports.models import (
    AdditionalEvidencePayload,
    CitizenReportCreate,
    CitizenReportPublic,
    CitizenVerificationPayload,
    PaginatedReportsResponse,
    ProblemCategory,
    ReportStatus,
    ReportStatusUpdate,
)

logger = logging.getLogger("urbansage.api.reports")

router = APIRouter(prefix="/api/reports", tags=["Citizen Reports"])


@router.post(
    "",
    response_model=CitizenReportPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen environmental problem report",
    description=(
        "Accepts a validated citizen report, calculates operational urgency and "
        "documentary evidence completeness scores, and persists the record. "
        "Private contact details are stored securely but omitted from the response."
    ),
)
def create_report(
    report_in: CitizenReportCreate,
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> CitizenReportPublic:
    try:
        created = repo.create_report(report_in)
        return CitizenReportPublic.from_report(created)
    except DuplicateReportError as e:
        logger.warning("Duplicate report submission rejected: %s", e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ReportValidationError as e:
        logger.warning("Validation error during report creation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except ReportPersistenceError as e:
        logger.error("Database persistence failure: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while persisting the report.",
        ) from e
    except Exception as e:
        logger.critical("Unhandled error during report creation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred.",
        ) from e


@router.get(
    "",
    response_model=PaginatedReportsResponse,
    status_code=status.HTTP_200_OK,
    summary="List citizen environmental reports",
    description=(
        "Returns a paginated list of citizen reports with stable pagination metadata. "
        "Supports filtering by problem category and lifecycle status."
    ),
)
def list_reports(
    category: Optional[ProblemCategory] = Query(
        default=None,
        description="Filter by environmental problem category.",
    ),
    report_status: Optional[ReportStatus] = Query(
        default=None,
        alias="status",
        description="Filter by operational lifecycle status.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Page size limit (maximum 100 items).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination.",
    ),
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> PaginatedReportsResponse:
    try:
        reports = repo.list_reports(
            category=category,
            status=report_status,
            limit=limit,
            offset=offset,
        )
        total = repo.count_reports(category=category, status=report_status)
        public_items = [CitizenReportPublic.from_report(r) for r in reports]
        return PaginatedReportsResponse(
            items=public_items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except ReportPersistenceError as e:
        logger.error("Database query failure while listing reports: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving reports.",
        ) from e
    except Exception as e:
        logger.critical("Unhandled error in list_reports: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred.",
        ) from e


@router.get(
    "/{report_id}",
    response_model=CitizenReportPublic,
    status_code=status.HTTP_200_OK,
    summary="Get citizen report details by ID",
    description="Returns public details for a single report. Returns 404 if not found.",
)
def get_report(
    report_id: str,
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> CitizenReportPublic:
    try:
        report = repo.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Citizen report not found: {report_id}",
            )
        return CitizenReportPublic.from_report(report)
    except HTTPException:
        raise
    except ReportPersistenceError as e:
        logger.error("Database query failure for report %s: %s", report_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the report.",
        ) from e
    except Exception as e:
        logger.critical("Unhandled error in get_report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred.",
        ) from e


@router.patch(
    "/{report_id}/status",
    response_model=CitizenReportPublic,
    status_code=status.HTTP_200_OK,
    summary="Update report status (Admin review, assignment, completion)",
    description=(
        "Updates the operational lifecycle status of a citizen report. "
        "Requires administrator or contractor authorization. Enforces state transition rules, "
        "records audit history, and requires resolution evidence when marking work completed."
    ),
)
def update_report_status(
    report_id: str,
    payload: ReportStatusUpdate,
    user: AuthenticatedUser = Depends(require_admin_or_contractor),
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> CitizenReportPublic:
    try:
        effective_role = user.role if user.role in ("administrator", "contractor", "system") else payload.actor_role
        effective_actor_id = payload.actor_id or user.user_id

        updated = repo.update_status(
            report_id=report_id,
            status=payload.status,
            actor_role=effective_role,
            actor_id=effective_actor_id,
            reason=payload.reason,
            evidence=payload.evidence,
            validate_transition=True,
        )
        return CitizenReportPublic.from_report(updated)
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ReportValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except ReportPersistenceError as e:
        logger.error("Failed to update status for report %s: %s", report_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating status.",
        ) from e


@router.post(
    "/{report_id}/verify",
    response_model=CitizenReportPublic,
    status_code=status.HTTP_200_OK,
    summary="Citizen verification of resolution",
    description=(
        "Allows citizens to confirm that a reported issue is satisfactorily resolved "
        "(transitioning to 'verified_resolved') or reject the resolution if the problem "
        "persists (transitioning to 'verification_failed' and returning to the municipal queue)."
    ),
)
def verify_report_resolution(
    report_id: str,
    payload: CitizenVerificationPayload,
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> CitizenReportPublic:
    try:
        updated = repo.verify_resolution(
            report_id=report_id,
            confirmed_resolved=payload.confirmed_resolved,
            feedback=payload.feedback,
            actor_id=payload.actor_id,
        )
        return CitizenReportPublic.from_report(updated)
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ReportValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except ReportPersistenceError as e:
        logger.error("Failed to process verification for report %s: %s", report_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing verification.",
        ) from e


@router.post(
    "/{report_id}/evidence",
    response_model=CitizenReportPublic,
    status_code=status.HTTP_200_OK,
    summary="Submit additional evidence for report",
    description=(
        "Allows citizens to attach additional photographs or explanatory notes "
        "when additional information was requested by municipal reviewers."
    ),
)
def add_report_evidence(
    report_id: str,
    payload: AdditionalEvidencePayload,
    repo: BaseCitizenReportRepository = Depends(get_report_repository),
) -> CitizenReportPublic:
    try:
        updated = repo.add_additional_evidence(
            report_id=report_id,
            additional_notes=payload.additional_notes,
            photos=payload.photos,
            actor_id=payload.actor_id,
        )
        return CitizenReportPublic.from_report(updated)
    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ReportValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except ReportPersistenceError as e:
        logger.error("Failed to append evidence for report %s: %s", report_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while appending evidence.",
        ) from e
