"""
UrbanSage AI — Citizen Environmental Reporting Models
======================================================
Pydantic v2 schemas for citizen environmental problem reporting, lifecycle tracking,
and transparent validation.

Design Principles:
------------------
1. Strict Separation: Citizen-submitted observations are permanently tagged with
   `data_source: Literal["CITIZEN_REPORT"]` and `is_verified_measurement: False`.
   They are NEVER conflated with sensor ground truth or verified municipal measurements.
2. Initial State: All reports initialize with status `SUBMITTED` and verification
   status `UNVERIFIED`.
3. Photograph Scope: `PhotoMetadata` tracks lightweight file metadata (mime type,
   byte size, timestamp) for auditability. Binary file storage or cloud S3 upload is
   explicitly NOT part of Phase 1A.
4. Stable Identifiers: Report IDs follow the format `RPT-XXXXXXXX` (8 uppercase hex chars).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


CITIZEN_SOURCE = Literal["CITIZEN_REPORT"]


class ProblemCategory(str, Enum):
    """
    Environmental problem categories supported by UrbanSage AI citizen reporting.
    Aligned with the core urban environmental hazards addressed by the platform.
    """

    FLOODING_DRAINAGE = "flooding_drainage"
    WATER_SCARCITY = "water_scarcity"
    HEAT = "heat"
    LOSS_OF_GREEN_COVER = "loss_of_green_cover"


class ReportStatus(str, Enum):
    """
    Lifecycle workflow stages for an environmental problem report.
    Supports all 14 required municipal operational states plus backward-compatible aliases.
    """

    # Stage 1: Ingestion & Review
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INFO_REQUESTED = "info_requested"
    VERIFIED = "verified"
    FLAGGED_SUSPICIOUS = "flagged_suspicious"
    CONFIRMED_FAKE = "confirmed_fake"
    DUPLICATE = "duplicate"
    OUT_OF_SCOPE = "out_of_scope"
    NO_ACTION_REQUIRED = "no_action_required"

    # Stage 2: Assignment & Field Execution
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"

    # Stage 3: Completion & Citizen Verification
    COMPLETED_AWAITING_VERIFICATION = "completed_awaiting_verification"
    VERIFICATION_FAILED = "verification_failed"
    VERIFIED_RESOLVED = "verified_resolved"

    # Backward-compatible aliases
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class VerificationStatus(str, Enum):
    """
    Verification state reflecting administrative and field validation.
    """

    UNVERIFIED = "unverified"
    COMMUNITY_CORROBORATED = "community_corroborated"
    OFFICIALLY_VERIFIED = "officially_verified"
    DISMISSED = "dismissed"


class PhotoMetadata(BaseModel):
    """
    Metadata representation of an attached photograph.

    NOTE: Phase 1A only manages structured metadata for verification readiness.
    Actual media upload pipelines and object cloud storage are deferred.
    """

    photo_id: str = Field(
        ...,
        pattern=r"^PHO-[A-F0-9]{8}$",
        description="Unique photo identifier. Format: PHO-XXXXXXXX (8 uppercase hex).",
    )
    file_name: str = Field(..., min_length=1, max_length=255, description="Client file name.")
    mime_type: str = Field(
        ...,
        description="Standard MIME type (e.g. image/jpeg, image/png, image/webp).",
    )
    size_bytes: int = Field(
        ...,
        gt=0,
        le=15_000_000,
        description="File size in bytes (max 15 MB).",
    )
    caption: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional citizen caption or notes about the photo.",
    )
    captured_at: Optional[datetime] = Field(
        default=None,
        description="Optional timestamp from camera EXIF or user declaration.",
    )

    @field_validator("file_name")
    @classmethod
    def sanitize_file_name(cls, v: str) -> str:
        """Strip client directory paths to prevent local file path leakage."""
        cleaned = Path(v).name.strip()
        if not cleaned:
            raise ValueError("File name cannot be empty")
        return cleaned

    @field_validator("mime_type")
    @classmethod
    def validate_mime(cls, v: str) -> str:
        allowed = {"image/jpeg", "image/png", "image/webp", "image/heic"}
        if v.lower() not in allowed:
            raise ValueError(f"Unsupported image MIME type: {v}. Allowed: {sorted(allowed)}")
        return v.lower()


class ResolutionEvidence(BaseModel):
    """
    Evidence recorded upon completion of an intervention or municipal remediation.
    """

    completed_by: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Name or identifier of department, contractor, or team executing work.",
    )
    completion_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Detailed description of completed remediation or intervention.",
    )
    evidence_photos: List[PhotoMetadata] = Field(
        default_factory=list,
        description="Photographic proof of completed work.",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when field work was marked completed.",
    )
    citizen_confirmed: Optional[bool] = Field(
        default=None,
        description="None if pending citizen verification; True if confirmed resolved; False if rejected/unresolved.",
    )
    citizen_feedback: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Citizen remarks or reason during verification or rejection.",
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when citizen or municipal inspector verified or rejected resolution.",
    )


class StatusTransitionLog(BaseModel):
    """
    Audit log entry recording an immutable status transition in the report lifecycle.
    """

    from_status: ReportStatus = Field(..., description="Previous status.")
    to_status: ReportStatus = Field(..., description="New status.")
    actor_role: Literal["citizen", "administrator", "contractor", "system"] = Field(
        ...,
        description="Role of actor performing transition.",
    )
    actor_id: Optional[str] = Field(default=None, description="Identifier of actor.")
    reason: Optional[str] = Field(default=None, max_length=1000, description="Reason or notes.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of transition.",
    )
    evidence: Optional[ResolutionEvidence] = Field(
        default=None,
        description="Resolution evidence attached to this transition, if any.",
    )


ALLOWED_TRANSITIONS: dict[ReportStatus, set[ReportStatus]] = {
    ReportStatus.SUBMITTED: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.INFO_REQUESTED,
        ReportStatus.VERIFIED,
        ReportStatus.ASSIGNED,  # Fast-path administrative dispatch for emergencies
        ReportStatus.FLAGGED_SUSPICIOUS,
        ReportStatus.DUPLICATE,
        ReportStatus.OUT_OF_SCOPE,
        ReportStatus.NO_ACTION_REQUIRED,
        ReportStatus.DISMISSED,
    },
    ReportStatus.UNDER_REVIEW: {
        ReportStatus.INFO_REQUESTED,
        ReportStatus.VERIFIED,
        ReportStatus.ASSIGNED,
        ReportStatus.FLAGGED_SUSPICIOUS,
        ReportStatus.CONFIRMED_FAKE,
        ReportStatus.DUPLICATE,
        ReportStatus.OUT_OF_SCOPE,
        ReportStatus.NO_ACTION_REQUIRED,
        ReportStatus.DISMISSED,
        ReportStatus.RESOLVED,
    },
    ReportStatus.INFO_REQUESTED: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.NO_ACTION_REQUIRED,
        ReportStatus.OUT_OF_SCOPE,
        ReportStatus.DISMISSED,
    },
    ReportStatus.FLAGGED_SUSPICIOUS: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.CONFIRMED_FAKE,
        ReportStatus.VERIFIED,
        ReportStatus.NO_ACTION_REQUIRED,
        ReportStatus.DISMISSED,
    },
    ReportStatus.CONFIRMED_FAKE: set(),
    ReportStatus.DUPLICATE: set(),
    ReportStatus.OUT_OF_SCOPE: set(),
    ReportStatus.NO_ACTION_REQUIRED: {ReportStatus.UNDER_REVIEW},
    ReportStatus.VERIFIED: {
        ReportStatus.ASSIGNED,
        ReportStatus.IN_PROGRESS,
        ReportStatus.UNDER_REVIEW,
    },
    ReportStatus.ASSIGNED: {
        ReportStatus.IN_PROGRESS,
        ReportStatus.COMPLETED_AWAITING_VERIFICATION,
        ReportStatus.UNDER_REVIEW,
        ReportStatus.RESOLVED,
    },
    ReportStatus.IN_PROGRESS: {
        ReportStatus.COMPLETED_AWAITING_VERIFICATION,
        ReportStatus.ASSIGNED,
        ReportStatus.VERIFIED_RESOLVED,
        ReportStatus.RESOLVED,
    },
    ReportStatus.COMPLETED_AWAITING_VERIFICATION: {
        ReportStatus.VERIFIED_RESOLVED,
        ReportStatus.VERIFICATION_FAILED,
        ReportStatus.RESOLVED,
        ReportStatus.IN_PROGRESS,
    },
    ReportStatus.VERIFICATION_FAILED: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.ASSIGNED,
        ReportStatus.IN_PROGRESS,
    },
    ReportStatus.VERIFIED_RESOLVED: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.VERIFICATION_FAILED,
    },
    ReportStatus.RESOLVED: {
        ReportStatus.UNDER_REVIEW,
        ReportStatus.VERIFICATION_FAILED,
    },
    ReportStatus.DISMISSED: {
        ReportStatus.UNDER_REVIEW,
    },
}


def validate_status_transition(
    from_status: ReportStatus,
    to_status: ReportStatus,
    actor_role: Literal["citizen", "administrator", "contractor", "system"] = "administrator",
) -> None:
    """
    Validate whether transitioning from `from_status` to `to_status` is permitted.
    Raises InvalidStatusTransitionError if the transition is disallowed.
    """
    from app.reports.exceptions import InvalidStatusTransitionError

    if from_status == to_status:
        return

    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidStatusTransitionError(
            from_status=from_status.value,
            to_status=to_status.value,
            reason=f"Transition from '{from_status.value}' to '{to_status.value}' is not permitted by workflow rules.",
        )


class CitizenReportCreate(BaseModel):
    """
    Input schema for submitting a new citizen environmental problem report.
    Validated before persistence and score calculation.
    """

    category: ProblemCategory = Field(
        ...,
        description="Environmental issue category.",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed description of the observed environmental issue.",
    )
    severity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Citizen-assessed severity scale: 1 (Minor) to 5 (Emergency/Critical).",
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90.0 to +90.0).",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180.0 to +180.0).",
    )
    location_description: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Human-readable landmark, street address, or ward reference.",
    )
    neighbourhood_id: Optional[str] = Field(
        default=None,
        pattern=r"^NBR-\d{3}$",
        description="Optional synthetic/municipal neighbourhood linkage (e.g. NBR-001).",
    )
    reporter_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional reporter identifier or anonymous session token.",
    )
    reporter_contact: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Optional citizen contact (email/phone) for follow-up verification.",
    )
    photos: List[PhotoMetadata] = Field(
        default_factory=list,
        description="List of attached photo metadata objects.",
    )

    @field_validator("description", "location_description", "reporter_contact")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class CitizenReport(BaseModel):
    """
    Authoritative stored record of a citizen environmental report.

    Includes calculated scores (Urgency, Evidence Confidence), stable identifiers,
    and clear provenance metadata.
    """

    id: str = Field(
        ...,
        pattern=r"^RPT-[A-F0-9]{8}$",
        description="Stable unique report identifier. Format: RPT-XXXXXXXX.",
    )
    category: ProblemCategory = Field(..., description="Problem category.")
    description: str = Field(..., description="Report description.")
    severity: int = Field(..., ge=1, le=5, description="Citizen severity rating (1–5).")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate.")
    location_description: Optional[str] = Field(
        default=None,
        description="Descriptive location or landmark.",
    )
    neighbourhood_id: Optional[str] = Field(
        default=None,
        description="Associated neighbourhood ID, if linked.",
    )
    reporter_id: Optional[str] = Field(
        default=None,
        description="Reporter token or identifier.",
    )
    reporter_contact: Optional[str] = Field(
        default=None,
        description="Citizen contact information.",
    )
    photos: List[PhotoMetadata] = Field(
        default_factory=list,
        description="Attached photo metadata records.",
    )

    # Lifecycle & Verification States
    status: ReportStatus = Field(
        default=ReportStatus.SUBMITTED,
        description="Operational workflow status.",
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification audit status.",
    )
    is_verified_measurement: bool = Field(
        default=False,
        description=(
            "Strict sentinel: False indicates unverified citizen claim. "
            "Must NEVER be True for raw citizen reports."
        ),
    )
    data_source: CITIZEN_SOURCE = Field(
        default="CITIZEN_REPORT",
        description="Sentinel tracking origin as citizen crowd-sourced data.",
    )

    # Transparent Calculated Scores (0.0 to 100.0)
    urgency_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Computed triaging urgency score (0.0–100.0).",
    )
    evidence_confidence_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Computed documentary completeness & auditability score (0.0–100.0).",
    )

    # Resolution Evidence & Lifecycle Audit Trail
    resolution_evidence: Optional[ResolutionEvidence] = Field(
        default=None,
        description="Resolution evidence submitted upon remediation completion.",
    )
    timeline: List[StatusTransitionLog] = Field(
        default_factory=list,
        description="Immutable chronological lifecycle audit trail.",
    )

    # Audit Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC last update timestamp.",
    )


class CitizenReportPublic(BaseModel):
    """
    Public representation of a citizen report.

    SECURITY & PRIVACY:
    -------------------
    Omits `reporter_contact` entirely so private email addresses or phone numbers
    are never returned to public API callers.
    """

    id: str = Field(
        ...,
        pattern=r"^RPT-[A-F0-9]{8}$",
        description="Unique report identifier.",
    )
    category: ProblemCategory = Field(..., description="Problem category.")
    description: str = Field(..., description="Report description.")
    severity: int = Field(..., ge=1, le=5, description="Citizen severity rating (1–5).")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate.")
    location_description: Optional[str] = Field(
        default=None,
        description="Descriptive location or landmark.",
    )
    neighbourhood_id: Optional[str] = Field(
        default=None,
        description="Associated neighbourhood ID, if linked.",
    )
    photos: List[PhotoMetadata] = Field(
        default_factory=list,
        description="Attached photo metadata records.",
    )
    status: ReportStatus = Field(..., description="Operational workflow status.")
    verification_status: VerificationStatus = Field(..., description="Verification status.")
    is_verified_measurement: bool = Field(..., description="Measurement verification flag.")
    data_source: CITIZEN_SOURCE = Field(..., description="Data provenance sentinel.")
    urgency_score: float = Field(..., ge=0.0, le=100.0, description="Computed urgency score.")
    evidence_confidence_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Computed documentary completeness score.",
    )
    resolution_evidence: Optional[ResolutionEvidence] = Field(
        default=None,
        description="Resolution evidence submitted upon remediation completion.",
    )
    timeline: List[StatusTransitionLog] = Field(
        default_factory=list,
        description="Chronological lifecycle audit trail.",
    )
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    updated_at: datetime = Field(..., description="UTC last update timestamp.")

    @classmethod
    def from_report(cls, report: CitizenReport) -> CitizenReportPublic:
        """Construct a public report representation, stripping private contact and reporter identifier data."""
        data = report.model_dump()
        data.pop("reporter_contact", None)
        data.pop("reporter_id", None)
        # Redact private citizen actor IDs from public timeline entries for privacy
        sanitized_timeline = []
        for entry in data.get("timeline", []):
            if entry.get("actor_role") == "citizen":
                entry_copy = dict(entry)
                entry_copy["actor_id"] = None
                sanitized_timeline.append(entry_copy)
            else:
                sanitized_timeline.append(entry)
        data["timeline"] = sanitized_timeline
        return cls(**data)


class PaginatedReportsResponse(BaseModel):
    """
    Stable pagination envelope for report listings.
    """

    items: List[CitizenReportPublic] = Field(..., description="Page items.")
    total: int = Field(..., ge=0, description="Total matching items count.")
    limit: int = Field(..., ge=1, le=100, description="Page size limit.")
    offset: int = Field(..., ge=0, description="Page offset.")


class ReportStatusUpdate(BaseModel):
    """Request payload for administrative or operational status update."""

    status: ReportStatus = Field(..., description="Target operational status.")
    actor_role: Literal["citizen", "administrator", "contractor", "system"] = Field(
        default="administrator",
        description="Role of actor performing transition.",
    )
    actor_id: Optional[str] = Field(default=None, max_length=100, description="Actor username or ID.")
    reason: Optional[str] = Field(default=None, max_length=1000, description="Audit reason or notes.")
    evidence: Optional[ResolutionEvidence] = Field(
        default=None,
        description="Resolution evidence required when transitioning to 'completed_awaiting_verification'.",
    )


class CitizenVerificationPayload(BaseModel):
    """Request payload for citizen confirming or disputing resolution."""

    confirmed_resolved: bool = Field(
        ...,
        description="True if citizen confirms issue is resolved; False if issue remains unresolved.",
    )
    feedback: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Citizen remarks or feedback regarding resolution.",
    )
    actor_id: Optional[str] = Field(default=None, max_length=100, description="Optional citizen ID.")


class AdditionalEvidencePayload(BaseModel):
    """Request payload for citizen submitting additional evidence following info request."""

    additional_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional clarifying context from citizen.",
    )
    photos: List[PhotoMetadata] = Field(
        default_factory=list,
        description="Additional photographs provided by citizen.",
    )
    actor_id: Optional[str] = Field(default=None, max_length=100, description="Optional citizen ID.")


# ---------------------------------------------------------------------------
# Administrator Intelligence Dashboard Schemas (Stage 4)
# ---------------------------------------------------------------------------

ACTIVE_STATUSES: set[ReportStatus] = {
    ReportStatus.SUBMITTED,
    ReportStatus.UNDER_REVIEW,
    ReportStatus.INFO_REQUESTED,
    ReportStatus.VERIFIED,
    ReportStatus.ASSIGNED,
    ReportStatus.IN_PROGRESS,
    ReportStatus.COMPLETED_AWAITING_VERIFICATION,
    ReportStatus.VERIFICATION_FAILED,
}

CLOSED_STATUSES: set[ReportStatus] = {
    ReportStatus.VERIFIED_RESOLVED,
    ReportStatus.RESOLVED,
    ReportStatus.CONFIRMED_FAKE,
    ReportStatus.DUPLICATE,
    ReportStatus.OUT_OF_SCOPE,
    ReportStatus.NO_ACTION_REQUIRED,
    ReportStatus.DISMISSED,
}


class BriefReportItem(BaseModel):
    """Summarized report item included in the Administrator Decision Brief."""

    id: str = Field(..., description="Report ID.")
    category: ProblemCategory = Field(..., description="Hazard category.")
    description: str = Field(..., description="Description snippet.")
    severity: int = Field(..., description="Citizen severity (1-5).")
    status: ReportStatus = Field(..., description="Workflow status.")
    urgency_score: float = Field(..., description="Calculated urgency (0-100).")
    evidence_confidence_score: float = Field(..., description="Evidence completeness (0-100).")
    latitude: float = Field(..., description="Latitude.")
    longitude: float = Field(..., description="Longitude.")
    location_description: Optional[str] = Field(default=None, description="Landmark or address.")
    neighbourhood_id: Optional[str] = Field(default=None, description="Neighbourhood ID.")
    created_at: datetime = Field(..., description="Submission time.")
    age_hours: float = Field(..., description="Age in hours since submission.")
    prioritization_reason: str = Field(..., description="Deterministic prioritization explanation.")


class DecisionBriefSummary(BaseModel):
    """Aggregate metric counts for the Daily Decision Brief."""

    total_reports: int = Field(..., ge=0)
    active_reports: int = Field(..., ge=0)
    high_urgency_active_count: int = Field(..., ge=0)
    awaiting_review_count: int = Field(..., ge=0)
    awaiting_citizen_verification_count: int = Field(..., ge=0)
    verification_failed_count: int = Field(..., ge=0)
    overdue_active_count: int = Field(..., ge=0)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class DecisionBriefResponse(BaseModel):
    """Root response model for the Daily Decision Brief API."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overdue_threshold_hours: int = Field(default=48, description="Threshold for overdue active tickets.")
    summary: DecisionBriefSummary
    high_urgency_items: list[BriefReportItem] = Field(default_factory=list)
    awaiting_review_items: list[BriefReportItem] = Field(default_factory=list)
    awaiting_citizen_verification_items: list[BriefReportItem] = Field(default_factory=list)
    failed_verification_items: list[BriefReportItem] = Field(default_factory=list)
    overdue_items: list[BriefReportItem] = Field(default_factory=list)
    recent_activity: list[StatusTransitionLog] = Field(default_factory=list)


class NeighbourhoodRiskAggregate(BaseModel):
    """Aggregated environmental hazard metrics for a single neighbourhood."""

    neighbourhood_id: str = Field(..., description="Neighbourhood ID or 'UNASSIGNED'.")
    neighbourhood_name: Optional[str] = Field(default=None, description="Human-readable neighbourhood name.")
    total_reports: int = Field(..., ge=0)
    active_reports: int = Field(..., ge=0)
    resolved_reports: int = Field(..., ge=0)
    high_urgency_reports: int = Field(..., ge=0)
    average_urgency: float = Field(..., ge=0.0, le=100.0)
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    top_hazard_category: Optional[ProblemCategory] = None


class GeographicRiskResponse(BaseModel):
    """Root response model for geographic risk aggregation."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    time_window_days: Optional[int] = Field(default=None, description="Time filter applied in days, or null for all time.")
    total_reports: int = Field(..., ge=0)
    neighbourhoods: list[NeighbourhoodRiskAggregate] = Field(default_factory=list)
    unassigned: Optional[NeighbourhoodRiskAggregate] = None


class PriorityQueueResponse(BaseModel):
    """Paginated, urgency-sorted priority review queue response."""

    items: list[CitizenReportPublic] = Field(..., description="Reports on current page.")
    total: int = Field(..., ge=0, description="Total matching reports.")
    limit: int = Field(..., ge=1, le=100)
    offset: int = Field(..., ge=0)
    sort_by: str = Field(default="urgency_desc")

