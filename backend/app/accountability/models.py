"""
UrbanSage AI — Financial Accountability & Audit Data Models (Stage 6)
=====================================================================
Pydantic v2 schemas for the municipal financial accountability ledger,
milestone verification, discrepancy detection, and tamper-evident audit trail.

Design Principles:
------------------
1. Separation of Concerns:
   Optimizer recommendations represent computational suggestions;
   Financial Allocations represent legally authorized public fund commitments.
2. Explicit Monetary Units:
   All currency values are explicitly tracked in INR Lakhs (`amount_lakh`)
   with 4 decimal places of precision (exact to ₹10).
3. Budget Non-Exceedance:
   Recorded disbursements must never exceed authorized allocations.
4. Privacy Redaction:
   Public views aggregate data and omit contractor commercial-in-confidence
   banking details, internal inspector notes, and citizen identities.
"""

from __future__ import annotations

import datetime
from datetime import timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AllocationStatus(str, Enum):
    """Lifecycle status of a municipal capital expenditure allocation."""
    PLANNED = "planned"
    COMMITTED = "committed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FROZEN = "frozen"
    CANCELLED = "cancelled"


class CommitmentStatus(str, Enum):
    """Status of an administrative contract or purchase order."""
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class MilestoneStatus(str, Enum):
    """Physical delivery status of an intervention implementation milestone."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED_FOR_REVIEW = "submitted_for_review"
    VERIFIED_COMPLETE = "verified_complete"
    FAILED_VERIFICATION = "failed_verification"


class DisbursementStatus(str, Enum):
    """Financial execution status of a contractor payout."""
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    REVERSED = "reversed"


class EvidenceType(str, Enum):
    """Categorization of submitted documentary evidence."""
    SITE_PHOTO = "site_photo"
    INSPECTION_REPORT = "inspection_report"
    MATERIAL_INVOICE = "material_invoice"
    COMMUNITY_SIGN_OFF = "community_sign_off"
    GEO_SURVEY = "geo_survey"


class EvidenceVerificationStatus(str, Enum):
    """Review status of attached evidence metadata."""
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DiscrepancySeverity(str, Enum):
    """Urgency level of a flagged financial anomaly."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiscrepancyType(str, Enum):
    """Classification of automated financial discrepancy."""
    COST_OVERRUN = "cost_overrun"
    UNVERIFIED_DISBURSEMENT = "unverified_disbursement"
    MILESTONE_STALLED = "milestone_stalled"
    EVIDENCE_MISSING = "evidence_missing"
    BUDGET_MISMATCH = "budget_mismatch"


class DiscrepancyStatus(str, Enum):
    """Operational resolution state of a discrepancy flag."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AuditEventType(str, Enum):
    """Traceable domain events recorded in the accountability log."""
    ALLOCATION_CREATED = "allocation_created"
    COMMITMENT_RECORDED = "commitment_recorded"
    MILESTONE_UPDATED = "milestone_updated"
    EVIDENCE_ATTACHED = "evidence_attached"
    VERIFICATION_RECORDED = "verification_recorded"
    DISBURSEMENT_EXECUTED = "disbursement_executed"
    DISCREPANCY_FLAGGED = "discrepancy_flagged"
    DISCREPANCY_RESOLVED = "discrepancy_resolved"


# ---------------------------------------------------------------------------
# Core Domain Schemas
# ---------------------------------------------------------------------------

class EvidenceMetadata(BaseModel):
    """
    Metadata recording documentary evidence submitted for a milestone.
    NOTE: In this MVP, metadata records document attributes and hashes;
    it does not perform automated cryptographic image forensics.
    """
    evidence_id: str = Field(..., pattern=r"^EVD-[0-9A-F]{8}$", description="Format: EVD-XXXXXXXX")
    milestone_id: str = Field(..., pattern=r"^MLS-[0-9A-F]{8}$")
    evidence_type: EvidenceType
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., max_length=100)
    file_size_bytes: int = Field(..., gt=0, le=50_000_000)
    document_hash: str = Field(..., description="SHA-256 hash representing document content integrity")
    submitted_by: str = Field(..., min_length=1, max_length=100)
    submitted_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    verification_status: EvidenceVerificationStatus = Field(default=EvidenceVerificationStatus.PENDING_REVIEW)
    verification_notes: Optional[str] = Field(default=None, max_length=1000)


class VerificationDecision(BaseModel):
    """Formal municipal inspection decision on milestone completion."""
    decision_id: str = Field(..., pattern=r"^VDEC-[0-9A-F]{8}$")
    milestone_id: str = Field(..., pattern=r"^MLS-[0-9A-F]{8}$")
    decision: Literal["approved", "rejected", "revision_requested"]
    verifier_id: str = Field(..., min_length=1, max_length=100)
    verifier_name: str = Field(..., min_length=1, max_length=150)
    comments: str = Field(..., min_length=5, max_length=2000)
    decided_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    passed_inspection: bool = Field(...)


class ImplementationMilestone(BaseModel):
    """Trackable engineering or ecological milestone within an allocation."""
    milestone_id: str = Field(..., pattern=r"^MLS-[0-9A-F]{8}$")
    allocation_id: str = Field(..., pattern=r"^ALC-[0-9A-F]{8}$")
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5, max_length=1000)
    sequence_order: int = Field(..., ge=1, le=50)
    target_completion_date: str = Field(..., description="ISO Date string YYYY-MM-DD")
    status: MilestoneStatus = Field(default=MilestoneStatus.PENDING)
    disbursement_tied_amount_lakh: float = Field(
        ...,
        ge=0.0,
        description="Amount in Lakhs INR eligible for release upon verified completion",
    )
    percent_progress: int = Field(default=0, ge=0, le=100)
    evidence_items: List[EvidenceMetadata] = Field(default_factory=list)
    verification_decision: Optional[VerificationDecision] = Field(default=None)
    completed_at: Optional[datetime.datetime] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))


class FinancialCommitment(BaseModel):
    """Contractual commitment or work order encumbering funds against an allocation."""
    commitment_id: str = Field(..., pattern=r"^CMT-[0-9A-F]{8}$")
    allocation_id: str = Field(..., pattern=r"^ALC-[0-9A-F]{8}$")
    vendor_id: str = Field(..., min_length=1, max_length=100)
    vendor_name: str = Field(..., min_length=1, max_length=200)
    contract_reference: str = Field(..., min_length=1, max_length=100)
    committed_amount_lakh: float = Field(..., gt=0.0, description="Amount in Lakhs INR")
    status: CommitmentStatus = Field(default=CommitmentStatus.ACTIVE)
    approved_by: str = Field(..., min_length=1, max_length=100)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))


class DisbursementRecord(BaseModel):
    """Actual monetary disbursement issued against an authorized commitment and milestone."""
    disbursement_id: str = Field(..., pattern=r"^DSB-[0-9A-F]{8}$")
    allocation_id: str = Field(..., pattern=r"^ALC-[0-9A-F]{8}$")
    commitment_id: str = Field(..., pattern=r"^CMT-[0-9A-F]{8}$")
    milestone_id: Optional[str] = Field(default=None, pattern=r"^MLS-[0-9A-F]{8}$")
    amount_lakh: float = Field(..., gt=0.0, description="Disbursed amount in Lakhs INR")
    payment_reference: str = Field(..., min_length=4, max_length=100)
    recipient_entity: str = Field(..., min_length=1, max_length=200)
    status: DisbursementStatus = Field(default=DisbursementStatus.COMPLETED)
    approved_by: str = Field(..., min_length=1, max_length=100)
    disbursed_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))


class FinancialDiscrepancy(BaseModel):
    """Automated discrepancy detected in financial flows or milestone progress."""
    discrepancy_id: str = Field(..., pattern=r"^DSC-[0-9A-F]{8}$")
    allocation_id: str = Field(..., pattern=r"^ALC-[0-9A-F]{8}$")
    severity: DiscrepancySeverity
    discrepancy_type: DiscrepancyType
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    amount_involved_lakh: float = Field(default=0.0, ge=0.0)
    detected_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    status: DiscrepancyStatus = Field(default=DiscrepancyStatus.OPEN)
    resolved_by: Optional[str] = Field(default=None)
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)
    resolved_at: Optional[datetime.datetime] = Field(default=None)


class AuditEvent(BaseModel):
    """
    Immutable audit log entry recording state transitions and transactions.
    Contains a cryptographic hash chain link for tamper evidence.
    """
    event_id: str = Field(..., pattern=r"^AUD-[0-9A-F]{8}$")
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    actor_id: str = Field(..., min_length=1, max_length=100)
    actor_role: Literal["administrator", "contractor", "system"]
    event_type: AuditEventType
    entity_type: Literal["ALLOCATION", "COMMITMENT", "MILESTONE", "EVIDENCE", "DISBURSEMENT", "DISCREPANCY"]
    entity_id: str
    summary: str = Field(..., min_length=5, max_length=500)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    previous_event_hash: str = Field(default="GENESIS", max_length=64)
    event_hash: str = Field(..., max_length=64)


class InterventionAllocation(BaseModel):
    """
    Authoritative public record of municipal capital expenditure for a sustainability project.
    Represents actual appropriated funds, distinct from mathematical optimizer recommendations.
    """
    allocation_id: str = Field(..., pattern=r"^ALC-[0-9A-F]{8}$")
    title: str = Field(..., min_length=5, max_length=200)
    neighbourhood_id: str = Field(..., min_length=3, max_length=32)
    neighbourhood_name: str = Field(..., min_length=2, max_length=100)
    intervention_id: str = Field(..., min_length=3, max_length=32)
    intervention_name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    fiscal_year: str = Field(default="2025-2026", pattern=r"^\d{4}-\d{4}$")
    currency: Literal["INR"] = "INR"
    allocated_amount_lakh: float = Field(..., gt=0.0, description="Total authorized budget in Lakhs INR")
    committed_amount_lakh: float = Field(default=0.0, ge=0.0, description="Amount contracted in Lakhs INR")
    disbursed_amount_lakh: float = Field(default=0.0, ge=0.0, description="Amount disbursed in Lakhs INR")
    planned_units: int = Field(..., gt=0)
    status: AllocationStatus = Field(default=AllocationStatus.PLANNED)
    authorized_by: str = Field(..., min_length=1, max_length=100)
    council_resolution_ref: Optional[str] = Field(default=None, max_length=100)
    source_optimizer_run_id: Optional[str] = Field(default=None, description="Optional link to optimizer proposal")
    milestones: List[ImplementationMilestone] = Field(default_factory=list)
    commitments: List[FinancialCommitment] = Field(default_factory=list)
    disbursements: List[DisbursementRecord] = Field(default_factory=list)
    discrepancies: List[FinancialDiscrepancy] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))

    @computed_field  # type: ignore[misc]
    @property
    def remaining_budget_lakh(self) -> float:
        """Uncommitted capital allocation in Lakhs INR."""
        return round(max(0.0, self.allocated_amount_lakh - self.committed_amount_lakh), 4)

    @computed_field  # type: ignore[misc]
    @property
    def undisbursed_committed_lakh(self) -> float:
        """Committed funds awaiting milestone verification for release."""
        return round(max(0.0, self.committed_amount_lakh - self.disbursed_amount_lakh), 4)

    @computed_field  # type: ignore[misc]
    @property
    def disbursement_progress_pct(self) -> float:
        """Percentage of authorized budget disbursed."""
        if self.allocated_amount_lakh <= 0:
            return 0.0
        return round(min(100.0, (self.disbursed_amount_lakh / self.allocated_amount_lakh) * 100.0), 1)


# ---------------------------------------------------------------------------
# API Request & Response Schemas
# ---------------------------------------------------------------------------

class AllocationCreate(BaseModel):
    """Payload for creating a new authorized municipal allocation."""
    title: str = Field(..., min_length=5, max_length=200)
    neighbourhood_id: str = Field(..., min_length=3, max_length=32)
    neighbourhood_name: str = Field(..., min_length=2, max_length=100)
    intervention_id: str = Field(..., min_length=3, max_length=32)
    intervention_name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    fiscal_year: str = Field(default="2025-2026", pattern=r"^\d{4}-\d{4}$")
    allocated_amount_lakh: float = Field(..., gt=0.0)
    planned_units: int = Field(..., gt=0)
    council_resolution_ref: Optional[str] = Field(default=None, max_length=100)
    source_optimizer_run_id: Optional[str] = Field(default=None)


class CommitmentCreate(BaseModel):
    """Payload for recording a contract commitment against an allocation."""
    vendor_id: str = Field(..., min_length=1, max_length=100)
    vendor_name: str = Field(..., min_length=1, max_length=200)
    contract_reference: str = Field(..., min_length=1, max_length=100)
    committed_amount_lakh: float = Field(..., gt=0.0)


class MilestoneCreate(BaseModel):
    """Payload for adding an implementation milestone."""
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5, max_length=1000)
    sequence_order: int = Field(..., ge=1, le=50)
    target_completion_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    disbursement_tied_amount_lakh: float = Field(..., ge=0.0)


class MilestoneUpdate(BaseModel):
    """Payload for updating milestone execution progress."""
    status: Optional[MilestoneStatus] = None
    percent_progress: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


class EvidenceSubmit(BaseModel):
    """Payload for submitting evidence metadata."""
    evidence_type: EvidenceType
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    file_name: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., max_length=100)
    file_size_bytes: int = Field(..., gt=0, le=50_000_000)
    document_hash: Optional[str] = Field(default=None, max_length=64)


class VerificationSubmit(BaseModel):
    """Payload for administrative milestone verification."""
    decision: Literal["approved", "rejected", "revision_requested"]
    comments: str = Field(..., min_length=5, max_length=2000)


class DisbursementCreate(BaseModel):
    """Payload for recording an authorized monetary disbursement."""
    commitment_id: str = Field(..., pattern=r"^CMT-[0-9A-F]{8}$")
    milestone_id: Optional[str] = Field(default=None, pattern=r"^MLS-[0-9A-F]{8}$")
    amount_lakh: float = Field(..., gt=0.0)
    payment_reference: str = Field(..., min_length=4, max_length=100)
    recipient_entity: str = Field(..., min_length=1, max_length=200)


class DiscrepancyResolve(BaseModel):
    """Payload for resolving a financial discrepancy."""
    resolution_notes: str = Field(..., min_length=10, max_length=1000)
    action_taken: Literal["resolved", "dismissed"] = "resolved"


class PublicAccountabilitySummary(BaseModel):
    """
    Public-facing transparency summary for citizens and civic auditors.
    Omit internal vendor banking info, officer private notes, and raw citizen data.
    """
    fiscal_year: str
    total_allocated_lakh: float
    total_committed_lakh: float
    total_disbursed_lakh: float
    total_remaining_lakh: float
    allocation_count: int
    completed_milestones_count: int
    pending_milestones_count: int
    open_discrepancies_count: int
    resolved_discrepancies_count: int
    by_category: Dict[str, Dict[str, float]]
    by_neighbourhood: List[Dict[str, Any]]
    disclaimer: str = (
        "UrbanSage AI Accountability Portal: This financial ledger presents municipal budget "
        "appropriations, vendor commitments, verified milestone completions, and disbursements. "
        "Demonstration datasets use calibrated synthetic spending estimates for transparency."
    )


class ExpenditureRequestCreate(BaseModel):
    """Payload submitted by Infrastructure Partner to request an expenditure against their commitment."""
    commitment_id: str = Field(..., pattern=r"^CMT-[0-9A-F]{8}$")
    milestone_id: Optional[str] = Field(default=None, pattern=r"^MLS-[0-9A-F]{8}$")
    amount_lakh: float = Field(..., gt=0.0, description="Requested expenditure amount in Lakhs INR")
    payment_reference: str = Field(..., min_length=3, max_length=100, description="Invoice or claim voucher reference")
    recipient_entity: str = Field(..., min_length=2, max_length=200, description="Payee / contractor registered name")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Work completed / justification notes")


class PartnerProposalItem(BaseModel):
    """Proposal or expenditure claim submitted against a project commitment."""
    proposal_id: str
    allocation_id: str
    project_title: str
    amount_lakh: float
    purpose: str
    status: str
    submission_date: str


class PartnerProjectBudget(BaseModel):
    """Financial breakdown of an allocated project assigned to a specific partner."""
    allocation_id: str
    title: str
    category: str
    neighbourhood_id: str
    neighbourhood_name: str
    contract_reference: str
    allocated_amount_lakh: float = 0.0
    committed_amount_lakh: float
    disbursed_amount_lakh: float
    pending_requests_lakh: float
    remaining_balance_lakh: float
    utilization_pct: float
    milestones_count: int
    verified_milestones_count: int


class PartnerBudgetSummary(BaseModel):
    """Comprehensive budget visibility for an authenticated Infrastructure Partner."""
    vendor_id: str
    vendor_name: str
    total_allocated_lakh: float = 0.0
    total_committed_lakh: float
    total_disbursed_lakh: float
    total_pending_requests_lakh: float
    total_remaining_balance_lakh: float
    overall_utilization_pct: float
    projects: List[PartnerProjectBudget]
    proposals: List[PartnerProposalItem] = Field(default_factory=list)
    disclaimer: str = (
        "Infrastructure Partner Financial View: Budget commitments and disbursements are authoritative "
        "records from the Municipal Capital Ledger. Proposed expenditure requests require official municipal approval."
    )

