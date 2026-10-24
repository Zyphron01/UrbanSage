"""
UrbanSage AI — Financial Accountability & Audit API Router (Stage 6)
=====================================================================
REST API endpoints managing the municipal capital budget ledger, contractor
commitments, milestone tracking, documentary evidence, physical verification,
discrepancy detection, and public transparency.

Authorization Policies:
-----------------------
- Public Endpoints:
  - GET /summary (aggregate municipal budget transparency summary)
  - GET /allocations (list public project appropriations)
  - GET /allocations/{id} (detailed milestone & project view)
- Protected Contractor Endpoints (role in ['contractor', 'administrator']):
  - PATCH /milestones/{id} (update milestone execution progress)
  - POST /milestones/{id}/evidence (submit photo/document evidence metadata)
- Protected Administrator-Only Endpoints (role == 'administrator'):
  - POST /allocations (create authorized budget allocation)
  - POST /allocations/{id}/commitments (record contract commitment)
  - POST /allocations/{id}/milestones (add implementation milestone)
  - POST /milestones/{id}/verify (formal municipal verification signoff)
  - POST /allocations/{id}/disbursements (execute monetary payout)
  - GET /discrepancies (list audit flags)
  - PATCH /discrepancies/{id}/resolve (resolve discrepancy)
  - GET /audit-trail (retrieve hash-chained audit history)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.accountability.models import (
    AllocationCreate,
    AuditEvent,
    CommitmentCreate,
    DisbursementCreate,
    DisbursementRecord,
    DiscrepancyResolve,
    EvidenceMetadata,
    EvidenceSubmit,
    ExpenditureRequestCreate,
    FinancialCommitment,
    FinancialDiscrepancy,
    ImplementationMilestone,
    InterventionAllocation,
    MilestoneCreate,
    MilestoneUpdate,
    PartnerBudgetSummary,
    PublicAccountabilitySummary,
    VerificationDecision,
    VerificationSubmit,
)
from app.accountability.repository import (
    AccountabilityRepository,
    get_accountability_repository,
)
from app.auth import (
    AuthenticatedUser,
    require_admin_or_contractor,
    require_admin_role,
)

logger = logging.getLogger("urbansage.api.accountability")

router = APIRouter(prefix="/api/accountability", tags=["Financial Accountability & Audit"])


# ---------------------------------------------------------------------------
# Public Accountability & Transparency Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=PublicAccountabilitySummary,
    summary="Public Financial Accountability Summary",
    description="Aggregated budget metrics, spent funds, verified milestones, and category breakdowns.",
)
async def get_accountability_summary(
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> PublicAccountabilitySummary:
    return repo.get_public_summary()


@router.get(
    "/allocations",
    response_model=List[InterventionAllocation],
    summary="List Municipal Budget Allocations",
    description="List authorized capital expenditure projects with optional filtering.",
)
async def list_allocations(
    neighbourhood_id: Optional[str] = Query(None, description="Filter by neighbourhood ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    vendor_id: Optional[str] = Query(None, description="Filter by assigned contractor/vendor ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> List[InterventionAllocation]:
    return repo.list_allocations(
        neighbourhood_id=neighbourhood_id,
        category=category,
        status=status,
        vendor_id=vendor_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/allocations/{allocation_id}",
    response_model=InterventionAllocation,
    summary="Get Allocation Details",
    description="Retrieve full details of an allocation including milestones, commitments, and disbursements.",
)
async def get_allocation_detail(
    allocation_id: str,
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> InterventionAllocation:
    try:
        return repo.get_allocation(allocation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# Protected Administrator Operations: Allocations, Commitments & Disbursements
# ---------------------------------------------------------------------------

@router.post(
    "/allocations",
    response_model=InterventionAllocation,
    status_code=status.HTTP_201_CREATED,
    summary="Create Budget Allocation (Admin Only)",
    description="Authorize a new capital allocation for a sustainability intervention project.",
)
async def create_budget_allocation(
    payload: AllocationCreate,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> InterventionAllocation:
    try:
        return repo.create_allocation(payload, authorized_by=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/allocations/{allocation_id}/commitments",
    response_model=FinancialCommitment,
    status_code=status.HTTP_201_CREATED,
    summary="Record Contract Commitment (Admin Only)",
    description="Record an encumbrance or vendor work order against an authorized allocation.",
)
async def record_commitment(
    allocation_id: str,
    payload: CommitmentCreate,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> FinancialCommitment:
    try:
        return repo.add_commitment(allocation_id, payload, approved_by=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/allocations/{allocation_id}/milestones",
    response_model=ImplementationMilestone,
    status_code=status.HTTP_201_CREATED,
    summary="Add Implementation Milestone (Admin Only)",
    description="Add a trackable physical progress milestone to an intervention allocation.",
)
async def add_milestone(
    allocation_id: str,
    payload: MilestoneCreate,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> ImplementationMilestone:
    try:
        return repo.add_milestone(allocation_id, payload, actor_id=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/allocations/{allocation_id}/disbursements",
    response_model=DisbursementRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Monetary Disbursement (Admin Only)",
    description="Record an authorized payout to a vendor. Enforces budget caps and flags unverified milestones.",
)
async def execute_disbursement(
    allocation_id: str,
    payload: DisbursementCreate,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> DisbursementRecord:
    try:
        return repo.execute_disbursement(allocation_id, payload, approved_by=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# Contractor / Admin Milestone Execution & Evidence
# ---------------------------------------------------------------------------

@router.patch(
    "/milestones/{milestone_id}",
    response_model=ImplementationMilestone,
    summary="Update Milestone Progress (Contractor/Admin)",
    description="Update milestone execution percentage or submit for municipal review.",
)
async def update_milestone_progress(
    milestone_id: str,
    payload: MilestoneUpdate,
    user: AuthenticatedUser = Depends(require_admin_or_contractor),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> ImplementationMilestone:
    try:
        return repo.update_milestone_progress(
            milestone_id,
            payload,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/milestones/{milestone_id}/evidence",
    response_model=EvidenceMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Documentary Evidence (Contractor/Admin)",
    description="Attach photos, engineering reports, or invoices to support milestone completion.",
)
async def attach_evidence(
    milestone_id: str,
    payload: EvidenceSubmit,
    user: AuthenticatedUser = Depends(require_admin_or_contractor),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> EvidenceMetadata:
    try:
        return repo.submit_evidence(
            milestone_id,
            payload,
            submitted_by=user.user_id,
            actor_role=user.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/partner-budget",
    response_model=PartnerBudgetSummary,
    summary="Partner Budget & Expenditure Visibility",
    description="Dedicated financial visibility for an Infrastructure Partner showing commitments, disbursements, and remaining balances.",
)
async def get_partner_budget(
    vendor_id: Optional[str] = Query(None, description="Vendor ID filter (restricted for contractors)"),
    user: AuthenticatedUser = Depends(require_admin_or_contractor),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> PartnerBudgetSummary:
    # If user is contractor, strictly enforce their assigned vendor ID
    target_vendor = user.vendor_id if user.role == "contractor" else (vendor_id or user.vendor_id or "VND-BBMP-WORKS-01")
    if not target_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor ID is required to access contractor budget records.",
        )

    if hasattr(repo, "get_partner_budget_summary"):
        return repo.get_partner_budget_summary(target_vendor)
    
    # Fallback calculation if repository is sqlite base
    allocs = repo.list_allocations(vendor_id=target_vendor)
    projects = []
    vendor_name = target_vendor
    for a in allocs:
        v_cmts = [c for c in a.commitments if c.vendor_id == target_vendor]
        if not v_cmts:
            continue
        v_committed = sum(c.committed_amount_lakh for c in v_cmts)
        if v_cmts[0].vendor_name:
            vendor_name = v_cmts[0].vendor_name
        cmt_ids = {c.commitment_id for c in v_cmts}
        v_disbursed = sum(d.amount_lakh for d in a.disbursements if d.commitment_id in cmt_ids and d.status == "completed")
        v_pending = sum(d.amount_lakh for d in a.disbursements if d.commitment_id in cmt_ids and d.status == "pending_approval")
        v_rem = max(0.0, v_committed - v_disbursed)
        v_util = round((v_disbursed / v_committed * 100.0), 1) if v_committed > 0 else 0.0
        c_refs = ", ".join(dict.fromkeys(c.contract_reference for c in v_cmts))
        v_count = sum(1 for m in a.milestones if m.status == "verified_complete")
        projects.append({
            "allocation_id": a.allocation_id,
            "title": a.title,
            "category": a.category,
            "neighbourhood_id": a.neighbourhood_id,
            "neighbourhood_name": a.neighbourhood_name,
            "contract_reference": c_refs,
            "committed_amount_lakh": round(v_committed, 4),
            "disbursed_amount_lakh": round(v_disbursed, 4),
            "pending_requests_lakh": round(v_pending, 4),
            "remaining_balance_lakh": round(v_rem, 4),
            "utilization_pct": v_util,
            "milestones_count": len(a.milestones),
            "verified_milestones_count": v_count,
        })
    tot_comm = sum(p["committed_amount_lakh"] for p in projects)
    tot_disb = sum(p["disbursed_amount_lakh"] for p in projects)
    tot_pend = sum(p["pending_requests_lakh"] for p in projects)
    tot_rem = round(max(0.0, tot_comm - tot_disb), 4)
    ov_util = round((tot_disb / tot_comm * 100.0), 1) if tot_comm > 0 else 0.0
    return PartnerBudgetSummary(
        vendor_id=target_vendor,
        vendor_name=vendor_name,
        total_committed_lakh=round(tot_comm, 4),
        total_disbursed_lakh=round(tot_disb, 4),
        total_pending_requests_lakh=round(tot_pend, 4),
        total_remaining_balance_lakh=tot_rem,
        overall_utilization_pct=ov_util,
        projects=projects,
    )


@router.post(
    "/allocations/{allocation_id}/expenditure-requests",
    response_model=DisbursementRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Proposed Expenditure Request (Contractor/Admin)",
    description="Submit a contractor payment or expense claim. Enforces budget caps and saves with 'pending_approval' status.",
)
async def submit_expenditure_request(
    allocation_id: str,
    payload: ExpenditureRequestCreate,
    user: AuthenticatedUser = Depends(require_admin_or_contractor),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> DisbursementRecord:
    try:
        if hasattr(repo, "submit_expenditure_request"):
            return repo.submit_expenditure_request(
                allocation_id=allocation_id,
                payload=payload,
                actor_id=user.user_id,
                actor_role=user.role,
                vendor_id=user.vendor_id if user.role == "contractor" else None,
            )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Repository does not support expenditure requests.",
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



@router.post(
    "/milestones/{milestone_id}/verify",
    response_model=VerificationDecision,
    status_code=status.HTTP_200_OK,
    summary="Verify Milestone Completion (Admin Only)",
    description="Formal municipal inspection sign-off or rejection of milestone work.",
)
async def verify_milestone(
    milestone_id: str,
    payload: VerificationSubmit,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> VerificationDecision:
    try:
        return repo.verify_milestone(
            milestone_id,
            payload,
            verifier_id=user.user_id,
            verifier_name=user.name or user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# Discrepancies & Traceable Audit Trail
# ---------------------------------------------------------------------------

@router.get(
    "/discrepancies",
    response_model=List[FinancialDiscrepancy],
    summary="List Financial Discrepancies (Admin Only)",
    description="List automated audit discrepancies (cost overruns, unverified disbursements, stalled milestones).",
)
async def list_discrepancies(
    status: Optional[str] = Query(None, description="Filter by status (open, under_review, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> List[FinancialDiscrepancy]:
    return repo.list_discrepancies(status=status, severity=severity)


@router.patch(
    "/discrepancies/{discrepancy_id}/resolve",
    response_model=FinancialDiscrepancy,
    summary="Resolve Financial Discrepancy (Admin Only)",
    description="Resolve or dismiss a flagged discrepancy with an audit justification.",
)
async def resolve_discrepancy(
    discrepancy_id: str,
    payload: DiscrepancyResolve,
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> FinancialDiscrepancy:
    try:
        return repo.resolve_discrepancy(
            discrepancy_id=discrepancy_id,
            resolution_notes=payload.resolution_notes,
            action_taken=payload.action_taken,
            resolved_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/audit-trail",
    response_model=List[AuditEvent],
    summary="Retrieve Tamper-Evident Audit Trail (Admin Only)",
    description="Retrieve chronological audit history with cryptographic SHA-256 hash chains.",
)
async def get_audit_trail(
    limit: int = Query(100, ge=1, le=500),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    user: AuthenticatedUser = Depends(require_admin_role),
    repo: AccountabilityRepository = Depends(get_accountability_repository),
) -> List[AuditEvent]:
    return repo.get_audit_trail(limit=limit, entity_id=entity_id)
