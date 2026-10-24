"""
UrbanSage AI — Supabase PostgreSQL Financial Accountability Repository
=======================================================================
Direct Supabase PostgreSQL persistence for municipal budget allocations,
contractor commitments, implementation milestones, documentary evidence,
verification signoffs, disbursements, and tamper-evident audit events.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import hashlib
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from app.accountability.models import (
    AllocationCreate,
    AllocationStatus,
    AuditEvent,
    AuditEventType,
    CommitmentCreate,
    CommitmentStatus,
    DisbursementCreate,
    DisbursementRecord,
    DisbursementStatus,
    DiscrepancyResolve,
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
    EvidenceMetadata,
    EvidenceSubmit,
    EvidenceType,
    EvidenceVerificationStatus,
    ExpenditureRequestCreate,
    FinancialCommitment,
    FinancialDiscrepancy,
    ImplementationMilestone,
    InterventionAllocation,
    MilestoneCreate,
    MilestoneStatus,
    MilestoneUpdate,
    PartnerBudgetSummary,
    PartnerProjectBudget,
    PartnerProposalItem,
    PublicAccountabilitySummary,
    VerificationDecision,
    VerificationSubmit,
)
from app.accountability.repository import AccountabilityRepository

logger = logging.getLogger("urbansage.accountability.supabase")


class SupabaseAccountabilityRepository(AccountabilityRepository):
    """
    Supabase PostgreSQL persistence engine for capital accountability and contractor execution.
    """

    def __init__(self, client: Optional[Client] = None):
        if client:
            self.client = client
        else:
            load_dotenv()
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
            self.client = create_client(url, key)

    def _get_last_event_hash(self) -> str:
        try:
            res = (
                self.client.table("audit_events")
                .select("event_hash")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]["event_hash"]
        except Exception:
            pass
        return "GENESIS_URBANSAGE_FINANCIAL_AUDIT_LEDGER_2025"

    def _record_audit_event(
        self,
        actor_id: str,
        actor_role: str,
        event_type: Any,
        entity_type: str,
        entity_id: str,
        summary: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        prev_hash = self._get_last_event_hash()

        payload = {
            "event_id": event_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "summary": summary[:500],
            "previous_state": previous_state,
            "new_state": new_state,
            "previous_event_hash": prev_hash,
        }

        canonical = json.dumps(payload, sort_keys=True, default=str)
        event_hash = hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()
        payload["event_hash"] = event_hash
        payload["timestamp"] = now_iso

        try:
            self.client.table("audit_events").insert(payload).execute()
        except Exception as e:
            logger.warning("Failed to record audit event: %s", e)

    def create_allocation(self, payload: AllocationCreate, authorized_by: str) -> InterventionAllocation:
        alloc_id = f"ALC-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        row = {
            "allocation_id": alloc_id,
            "title": payload.title,
            "neighbourhood_id": payload.neighbourhood_id,
            "neighbourhood_name": payload.neighbourhood_name,
            "intervention_id": payload.intervention_id,
            "intervention_name": payload.intervention_name,
            "category": payload.category,
            "fiscal_year": payload.fiscal_year,
            "currency": "INR",
            "allocated_amount_lakh": round(payload.allocated_amount_lakh, 4),
            "committed_amount_lakh": 0.0,
            "disbursed_amount_lakh": 0.0,
            "planned_units": payload.planned_units,
            "status": AllocationStatus.PLANNED.value,
            "authorized_by": authorized_by,
            "council_resolution_ref": payload.council_resolution_ref,
            "source_optimizer_run_id": payload.source_optimizer_run_id,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        self.client.table("allocations").insert(row).execute()
        self._record_audit_event(
            actor_id=authorized_by,
            actor_role="administrator",
            event_type=AuditEventType.ALLOCATION_CREATED,
            entity_type="ALLOCATION",
            entity_id=alloc_id,
            summary=f"Authorized ₹{payload.allocated_amount_lakh:.2f}L budget for {payload.title} in {payload.neighbourhood_name}.",
            new_state=row,
        )

        return self.get_allocation(alloc_id)

    def list_allocations(
        self,
        neighbourhood_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        vendor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InterventionAllocation]:
        query = self.client.table("allocations").select("allocation_id").order("created_at", desc=True)
        if neighbourhood_id:
            query = query.eq("neighbourhood_id", neighbourhood_id)
        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("status", status)

        res = query.range(offset, offset + limit - 1).execute()
        alloc_ids = [r["allocation_id"] for r in (res.data or [])]

        allocations: List[InterventionAllocation] = []
        for aid in alloc_ids:
            try:
                alloc = self.get_allocation(aid)
                if vendor_id:
                    has_vendor = any(c.vendor_id == vendor_id for c in alloc.commitments)
                    if not has_vendor:
                        continue
                allocations.append(alloc)
            except Exception as e:
                logger.warning("Error fetching allocation %s: %s", aid, e)

        return allocations

    def get_allocation(self, allocation_id: str) -> InterventionAllocation:
        res = self.client.table("allocations").select("*").eq("allocation_id", allocation_id).execute()
        if not res.data or len(res.data) == 0:
            raise ValueError(f"Allocation '{allocation_id}' not found.")
        row = res.data[0]

        # Milestones
        m_res = (
            self.client.table("milestones")
            .select("*")
            .eq("allocation_id", allocation_id)
            .order("sequence_order", desc=False)
            .execute()
        )
        milestones: List[ImplementationMilestone] = []
        for m_row in (m_res.data or []):
            mid = m_row["milestone_id"]

            # Evidence
            e_res = self.client.table("evidence_metadata").select("*").eq("milestone_id", mid).execute()
            evidence_items = [
                EvidenceMetadata(
                    evidence_id=e["evidence_id"],
                    milestone_id=e["milestone_id"],
                    evidence_type=EvidenceType(e["evidence_type"]),
                    title=e["title"],
                    description=e.get("description"),
                    file_name=e["file_name"],
                    mime_type=e["mime_type"],
                    file_size_bytes=int(e["file_size_bytes"]),
                    document_hash=e["document_hash"],
                    submitted_by=e["submitted_by"],
                    submitted_at=datetime.datetime.fromisoformat(e["submitted_at"]),
                    verification_status=EvidenceVerificationStatus(e["verification_status"]),
                    verification_notes=e.get("verification_notes"),
                )
                for e in (e_res.data or [])
            ]

            # Verification Decision
            v_res = self.client.table("verification_decisions").select("*").eq("milestone_id", mid).execute()
            verification = None
            if v_res.data and len(v_res.data) > 0:
                v = v_res.data[0]
                verification = VerificationDecision(
                    decision_id=v["decision_id"],
                    milestone_id=v["milestone_id"],
                    decision=v["decision"],
                    verifier_id=v["verifier_id"],
                    verifier_name=v["verifier_name"],
                    comments=v["comments"],
                    decided_at=datetime.datetime.fromisoformat(v["decided_at"]),
                    passed_inspection=bool(v["passed_inspection"]),
                )

            milestones.append(
                ImplementationMilestone(
                    milestone_id=mid,
                    allocation_id=m_row["allocation_id"],
                    title=m_row["title"],
                    description=m_row["description"],
                    sequence_order=int(m_row["sequence_order"]),
                    target_completion_date=str(m_row["target_completion_date"]),
                    status=MilestoneStatus(m_row["status"]),
                    disbursement_tied_amount_lakh=float(m_row["disbursement_tied_amount_lakh"]),
                    percent_progress=int(m_row["percent_progress"]),
                    evidence_items=evidence_items,
                    verification_decision=verification,
                    completed_at=datetime.datetime.fromisoformat(m_row["completed_at"]) if m_row.get("completed_at") else None,
                    created_at=datetime.datetime.fromisoformat(m_row["created_at"]),
                    updated_at=datetime.datetime.fromisoformat(m_row["updated_at"]),
                )
            )

        # Commitments
        c_res = self.client.table("commitments").select("*").eq("allocation_id", allocation_id).execute()
        commitments = [
            FinancialCommitment(
                commitment_id=c["commitment_id"],
                allocation_id=c["allocation_id"],
                vendor_id=c["vendor_id"],
                vendor_name=c["vendor_name"],
                contract_reference=c["contract_reference"],
                committed_amount_lakh=float(c["committed_amount_lakh"]),
                status=CommitmentStatus(c["status"]),
                approved_by=c["approved_by"],
                created_at=datetime.datetime.fromisoformat(c["created_at"]),
            )
            for c in (c_res.data or [])
        ]

        # Disbursements
        d_res = self.client.table("disbursements").select("*").eq("allocation_id", allocation_id).execute()
        disbursements = [
            DisbursementRecord(
                disbursement_id=d["disbursement_id"],
                allocation_id=d["allocation_id"],
                commitment_id=d["commitment_id"],
                milestone_id=d.get("milestone_id"),
                amount_lakh=float(d["amount_lakh"]),
                payment_reference=d["payment_reference"],
                recipient_entity=d["recipient_entity"],
                status=DisbursementStatus(d["status"]),
                approved_by=d["approved_by"],
                disbursed_at=datetime.datetime.fromisoformat(d["disbursed_at"]),
            )
            for d in (d_res.data or [])
        ]

        # Discrepancies
        disc_res = self.client.table("discrepancies").select("*").eq("allocation_id", allocation_id).execute()
        discrepancies = [
            FinancialDiscrepancy(
                discrepancy_id=disc["discrepancy_id"],
                allocation_id=disc["allocation_id"],
                severity=DiscrepancySeverity(disc["severity"]),
                discrepancy_type=DiscrepancyType(disc["discrepancy_type"]),
                title=disc["title"],
                description=disc["description"],
                amount_involved_lakh=float(disc["amount_involved_lakh"]),
                status=DiscrepancyStatus(disc["status"]),
                detected_at=datetime.datetime.fromisoformat(disc["detected_at"]),
                resolved_by=disc.get("resolved_by"),
                resolution_notes=disc.get("resolution_notes"),
                resolved_at=datetime.datetime.fromisoformat(disc["resolved_at"]) if disc.get("resolved_at") else None,
            )
            for disc in (disc_res.data or [])
        ]

        return InterventionAllocation(
            allocation_id=row["allocation_id"],
            title=row["title"],
            neighbourhood_id=row["neighbourhood_id"],
            neighbourhood_name=row["neighbourhood_name"],
            intervention_id=row["intervention_id"],
            intervention_name=row["intervention_name"],
            category=row["category"],
            fiscal_year=row["fiscal_year"],
            currency=row["currency"],
            allocated_amount_lakh=float(row["allocated_amount_lakh"]),
            committed_amount_lakh=float(row["committed_amount_lakh"]),
            disbursed_amount_lakh=float(row["disbursed_amount_lakh"]),
            planned_units=int(row["planned_units"]),
            status=AllocationStatus(row["status"]),
            authorized_by=row["authorized_by"],
            council_resolution_ref=row.get("council_resolution_ref"),
            source_optimizer_run_id=row.get("source_optimizer_run_id"),
            milestones=milestones,
            commitments=commitments,
            disbursements=disbursements,
            discrepancies=discrepancies,
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
        )

    def add_commitment(self, allocation_id: str, payload: CommitmentCreate, approved_by: str) -> FinancialCommitment:
        alloc = self.get_allocation(allocation_id)
        new_committed = alloc.committed_amount_lakh + payload.committed_amount_lakh
        if new_committed > alloc.allocated_amount_lakh:
            raise ValueError(
                f"Commitment exceeds allocated budget. Total committed would be ₹{new_committed:.2f}L, but allocation is ₹{alloc.allocated_amount_lakh:.2f}L."
            )

        cid = f"CMT-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        row = {
            "commitment_id": cid,
            "allocation_id": allocation_id,
            "vendor_id": payload.vendor_id,
            "vendor_name": payload.vendor_name,
            "contract_reference": payload.contract_reference,
            "committed_amount_lakh": round(payload.committed_amount_lakh, 4),
            "status": CommitmentStatus.ACTIVE.value,
            "approved_by": approved_by,
            "created_at": now_iso,
        }

        self.client.table("commitments").insert(row).execute()
        new_status = AllocationStatus.COMMITTED.value if alloc.status == AllocationStatus.PLANNED else alloc.status.value
        self.client.table("allocations").update({
            "committed_amount_lakh": round(new_committed, 4),
            "status": new_status,
            "updated_at": now_iso,
        }).eq("allocation_id", allocation_id).execute()

        self._record_audit_event(
            actor_id=approved_by,
            actor_role="administrator",
            event_type=AuditEventType.COMMITMENT_RECORDED,
            entity_type="COMMITMENT",
            entity_id=cid,
            summary=f"Encumbered ₹{payload.committed_amount_lakh:.2f}L to {payload.vendor_name} ({payload.contract_reference}).",
            new_state=row,
        )

        return FinancialCommitment(
            commitment_id=cid,
            allocation_id=allocation_id,
            vendor_id=payload.vendor_id,
            vendor_name=payload.vendor_name,
            contract_reference=payload.contract_reference,
            committed_amount_lakh=payload.committed_amount_lakh,
            status=CommitmentStatus.ACTIVE,
            approved_by=approved_by,
            created_at=datetime.datetime.fromisoformat(now_iso),
        )

    def add_milestone(self, allocation_id: str, payload: MilestoneCreate, actor_id: str) -> ImplementationMilestone:
        alloc = self.get_allocation(allocation_id)
        mid = f"MLS-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        row = {
            "milestone_id": mid,
            "allocation_id": allocation_id,
            "title": payload.title,
            "description": payload.description,
            "sequence_order": payload.sequence_order,
            "target_completion_date": payload.target_completion_date.isoformat(),
            "status": MilestoneStatus.PENDING.value,
            "disbursement_tied_amount_lakh": round(payload.disbursement_tied_amount_lakh, 4),
            "percent_progress": 0,
            "completed_at": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        self.client.table("milestones").insert(row).execute()
        self._record_audit_event(
            actor_id=actor_id,
            actor_role="administrator",
            event_type=AuditEventType.MILESTONE_CREATED,
            entity_type="MILESTONE",
            entity_id=mid,
            summary=f"Created milestone '{payload.title}' for allocation {allocation_id}.",
            new_state=row,
        )

        return ImplementationMilestone(
            milestone_id=mid,
            allocation_id=allocation_id,
            title=payload.title,
            description=payload.description,
            sequence_order=payload.sequence_order,
            target_completion_date=payload.target_completion_date,
            status=MilestoneStatus.PENDING,
            disbursement_tied_amount_lakh=payload.disbursement_tied_amount_lakh,
            percent_progress=0,
            evidence_items=[],
            verification_decision=None,
            completed_at=None,
            created_at=datetime.datetime.fromisoformat(now_iso),
            updated_at=datetime.datetime.fromisoformat(now_iso),
        )

    def update_milestone_progress(
        self,
        milestone_id: str,
        payload: MilestoneUpdate,
        actor_id: str,
        actor_role: str,
    ) -> ImplementationMilestone:
        res = self.client.table("milestones").select("*").eq("milestone_id", milestone_id).execute()
        if not res.data or len(res.data) == 0:
            raise ValueError(f"Milestone '{milestone_id}' not found.")
        current = res.data[0]

        updates: Dict[str, Any] = {}
        if payload.percent_progress is not None:
            updates["percent_progress"] = payload.percent_progress
        if payload.status is not None:
            updates["status"] = payload.status.value
            if payload.status in (MilestoneStatus.VERIFIED_COMPLETE, MilestoneStatus.SUBMITTED_FOR_REVIEW) and not current.get("completed_at"):
                updates["completed_at"] = datetime.datetime.now(timezone.utc).isoformat()

        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso

        self.client.table("milestones").update(updates).eq("milestone_id", milestone_id).execute()
        self._record_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            event_type=AuditEventType.MILESTONE_UPDATED,
            entity_type="MILESTONE",
            entity_id=milestone_id,
            summary=f"Updated milestone {milestone_id} progress to {updates.get('percent_progress', current['percent_progress'])}% ({updates.get('status', current['status'])}).",
            previous_state=current,
            new_state={**current, **updates},
        )

        alloc = self.get_allocation(current["allocation_id"])
        for m in alloc.milestones:
            if m.milestone_id == milestone_id:
                return m
        raise ValueError("Failed to retrieve updated milestone.")

    def submit_evidence(
        self,
        milestone_id: str,
        payload: EvidenceSubmit,
        submitted_by: str,
        actor_role: str,
    ) -> EvidenceMetadata:
        m_res = self.client.table("milestones").select("allocation_id").eq("milestone_id", milestone_id).execute()
        if not m_res.data:
            raise ValueError(f"Milestone '{milestone_id}' not found.")

        eid = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        row = {
            "evidence_id": eid,
            "milestone_id": milestone_id,
            "evidence_type": payload.evidence_type.value,
            "title": payload.title,
            "description": payload.description,
            "file_name": payload.file_name,
            "mime_type": payload.mime_type,
            "file_size_bytes": payload.file_size_bytes,
            "document_hash": payload.document_hash,
            "submitted_by": submitted_by,
            "submitted_at": now_iso,
            "verification_status": EvidenceVerificationStatus.PENDING_REVIEW.value,
            "verification_notes": None,
        }

        self.client.table("evidence_metadata").insert(row).execute()
        self._record_audit_event(
            actor_id=submitted_by,
            actor_role=actor_role,
            event_type=AuditEventType.EVIDENCE_ATTACHED,
            entity_type="EVIDENCE",
            entity_id=eid,
            summary=f"Attached documentary evidence '{payload.title}' ({payload.file_name}) to milestone {milestone_id}.",
            new_state=row,
        )

        return EvidenceMetadata(
            evidence_id=eid,
            milestone_id=milestone_id,
            evidence_type=payload.evidence_type,
            title=payload.title,
            description=payload.description,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            document_hash=payload.document_hash,
            submitted_by=submitted_by,
            submitted_at=datetime.datetime.fromisoformat(now_iso),
            verification_status=EvidenceVerificationStatus.PENDING_REVIEW,
            verification_notes=None,
        )

    def verify_milestone(
        self,
        milestone_id: str,
        payload: VerificationSubmit,
        verifier_id: str,
        verifier_name: str,
    ) -> VerificationDecision:
        m_res = self.client.table("milestones").select("*").eq("milestone_id", milestone_id).execute()
        if not m_res.data:
            raise ValueError(f"Milestone '{milestone_id}' not found.")
        current = m_res.data[0]

        vid = f"VDEC-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        v_row = {
            "decision_id": vid,
            "milestone_id": milestone_id,
            "decision": payload.decision,
            "verifier_id": verifier_id,
            "verifier_name": verifier_name,
            "comments": payload.comments,
            "decided_at": now_iso,
            "passed_inspection": payload.passed_inspection,
        }

        self.client.table("verification_decisions").upsert(v_row, on_conflict="milestone_id").execute()

        new_status = MilestoneStatus.VERIFIED_COMPLETE.value if payload.passed_inspection and payload.decision == "approved" else MilestoneStatus.FAILED_VERIFICATION.value
        self.client.table("milestones").update({
            "status": new_status,
            "percent_progress": 100 if payload.passed_inspection else current["percent_progress"],
            "completed_at": now_iso if payload.passed_inspection else current.get("completed_at"),
            "updated_at": now_iso,
        }).eq("milestone_id", milestone_id).execute()

        self.client.table("evidence_metadata").update({
            "verification_status": EvidenceVerificationStatus.VERIFIED.value if payload.passed_inspection else EvidenceVerificationStatus.REJECTED.value,
            "verification_notes": f"Inspection decision: {payload.decision}. {payload.comments}",
        }).eq("milestone_id", milestone_id).execute()

        self._record_audit_event(
            actor_id=verifier_id,
            actor_role="administrator",
            event_type=AuditEventType.MILESTONE_VERIFIED,
            entity_type="MILESTONE",
            entity_id=milestone_id,
            summary=f"Official verification decision: {payload.decision} (Passed: {payload.passed_inspection}) by {verifier_name}.",
            new_state=v_row,
        )

        return VerificationDecision(
            decision_id=vid,
            milestone_id=milestone_id,
            decision=payload.decision,
            verifier_id=verifier_id,
            verifier_name=verifier_name,
            comments=payload.comments,
            decided_at=datetime.datetime.fromisoformat(now_iso),
            passed_inspection=payload.passed_inspection,
        )

    def execute_disbursement(
        self,
        allocation_id: str,
        payload: DisbursementCreate,
        approved_by: str,
    ) -> DisbursementRecord:
        alloc = self.get_allocation(allocation_id)
        new_disbursed = alloc.disbursed_amount_lakh + payload.amount_lakh
        if new_disbursed > alloc.allocated_amount_lakh:
            raise ValueError(
                f"Disbursement would exceed total allocation. Total disbursed: ₹{new_disbursed:.2f}L > Authorized: ₹{alloc.allocated_amount_lakh:.2f}L."
            )

        did = f"DSB-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        row = {
            "disbursement_id": did,
            "allocation_id": allocation_id,
            "commitment_id": payload.commitment_id,
            "milestone_id": payload.milestone_id,
            "amount_lakh": round(payload.amount_lakh, 4),
            "payment_reference": payload.payment_reference,
            "recipient_entity": payload.recipient_entity,
            "status": DisbursementStatus.COMPLETED.value,
            "approved_by": approved_by,
            "disbursed_at": now_iso,
        }

        self.client.table("disbursements").insert(row).execute()
        self.client.table("allocations").update({
            "disbursed_amount_lakh": round(new_disbursed, 4),
            "updated_at": now_iso,
        }).eq("allocation_id", allocation_id).execute()

        self._record_audit_event(
            actor_id=approved_by,
            actor_role="administrator",
            event_type=AuditEventType.DISBURSEMENT_EXECUTED,
            entity_type="DISBURSEMENT",
            entity_id=did,
            summary=f"Disbursed ₹{payload.amount_lakh:.2f}L to {payload.recipient_entity} (Ref: {payload.payment_reference}).",
            new_state=row,
        )

        return DisbursementRecord(
            disbursement_id=did,
            allocation_id=allocation_id,
            commitment_id=payload.commitment_id,
            milestone_id=payload.milestone_id,
            amount_lakh=payload.amount_lakh,
            payment_reference=payload.payment_reference,
            recipient_entity=payload.recipient_entity,
            status=DisbursementStatus.COMPLETED,
            approved_by=approved_by,
            disbursed_at=datetime.datetime.fromisoformat(now_iso),
        )

    def list_discrepancies(
        self,
        allocation_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[FinancialDiscrepancy]:
        query = self.client.table("discrepancies").select("*").order("detected_at", desc=True)
        if allocation_id:
            query = query.eq("allocation_id", allocation_id)
        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)

        res = query.execute()
        return [
            FinancialDiscrepancy(
                discrepancy_id=d["discrepancy_id"],
                allocation_id=d["allocation_id"],
                severity=DiscrepancySeverity(d["severity"]),
                discrepancy_type=DiscrepancyType(d["discrepancy_type"]),
                title=d["title"],
                description=d["description"],
                amount_involved_lakh=float(d["amount_involved_lakh"]),
                status=DiscrepancyStatus(d["status"]),
                detected_at=datetime.datetime.fromisoformat(d["detected_at"]),
                resolved_by=d.get("resolved_by"),
                resolution_notes=d.get("resolution_notes"),
                resolved_at=datetime.datetime.fromisoformat(d["resolved_at"]) if d.get("resolved_at") else None,
            )
            for d in (res.data or [])
        ]

    def resolve_discrepancy(
        self,
        discrepancy_id: str,
        payload: DiscrepancyResolve,
        resolved_by: str,
    ) -> FinancialDiscrepancy:
        res = self.client.table("discrepancies").select("*").eq("discrepancy_id", discrepancy_id).execute()
        if not res.data:
            raise ValueError(f"Discrepancy '{discrepancy_id}' not found.")
        current = res.data[0]

        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        updates = {
            "status": DiscrepancyStatus.RESOLVED.value,
            "resolved_by": resolved_by,
            "resolution_notes": payload.resolution_notes,
            "resolved_at": now_iso,
        }

        self.client.table("discrepancies").update(updates).eq("discrepancy_id", discrepancy_id).execute()
        self._record_audit_event(
            actor_id=resolved_by,
            actor_role="administrator",
            event_type=AuditEventType.DISCREPANCY_RESOLVED,
            entity_type="DISCREPANCY",
            entity_id=discrepancy_id,
            summary=f"Resolved discrepancy '{current['title']}': {payload.resolution_notes}",
            previous_state=current,
            new_state={**current, **updates},
        )

        return FinancialDiscrepancy(
            discrepancy_id=discrepancy_id,
            allocation_id=current["allocation_id"],
            severity=DiscrepancySeverity(current["severity"]),
            discrepancy_type=DiscrepancyType(current["discrepancy_type"]),
            title=current["title"],
            description=current["description"],
            amount_involved_lakh=float(current["amount_involved_lakh"]),
            status=DiscrepancyStatus.RESOLVED,
            detected_at=datetime.datetime.fromisoformat(current["detected_at"]),
            resolved_by=resolved_by,
            resolution_notes=payload.resolution_notes,
            resolved_at=datetime.datetime.fromisoformat(now_iso),
        )

    def get_audit_trail(
        self,
        limit: int = 50,
        offset: int = 0,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> List[AuditEvent]:
        query = self.client.table("audit_events").select("*").order("timestamp", desc=True)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_id:
            query = query.eq("entity_id", entity_id)

        res = query.range(offset, offset + limit - 1).execute()
        trail: List[AuditEvent] = []
        for a in (res.data or []):
            try:
                ev_type = AuditEventType(a["event_type"])
            except Exception:
                ev_type = AuditEventType.ALLOCATION_CREATED
            trail.append(
                AuditEvent(
                    event_id=a["event_id"],
                    timestamp=datetime.datetime.fromisoformat(a["timestamp"]),
                    actor_id=a["actor_id"],
                    actor_role=a["actor_role"],
                    event_type=ev_type,
                    entity_type=a["entity_type"],
                    entity_id=a["entity_id"],
                    summary=a["summary"],
                    previous_state=a.get("previous_state"),
                    new_state=a.get("new_state"),
                    previous_event_hash=a["previous_event_hash"],
                    event_hash=a["event_hash"],
                )
            )
        return trail


    def get_public_summary(self) -> PublicAccountabilitySummary:
        res = self.client.table("allocations").select("*").execute()
        allocs = res.data or []

        tot_allocated = sum(float(a["allocated_amount_lakh"]) for a in allocs)
        tot_committed = sum(float(a["committed_amount_lakh"]) for a in allocs)
        tot_disbursed = sum(float(a["disbursed_amount_lakh"]) for a in allocs)
        tot_remaining = tot_allocated - tot_disbursed

        m_res = self.client.table("milestones").select("status").execute()
        m_list = m_res.data or []
        completed_m = sum(1 for m in m_list if m["status"] == "verified_complete")
        pending_m = sum(1 for m in m_list if m["status"] != "verified_complete")

        disc_res = self.client.table("discrepancies").select("status").execute()
        disc_list = disc_res.data or []
        open_disc = sum(1 for d in disc_list if d["status"] in ("open", "under_review"))
        resolved_disc = sum(1 for d in disc_list if d["status"] == "resolved")

        # By category
        by_cat: Dict[str, Any] = {}
        for a in allocs:
            cat = a["category"]
            if cat not in by_cat:
                by_cat[cat] = {"count": 0, "allocated_lakh": 0.0, "committed_lakh": 0.0, "disbursed_lakh": 0.0}
            by_cat[cat]["count"] += 1
            by_cat[cat]["allocated_lakh"] += float(a["allocated_amount_lakh"])
            by_cat[cat]["committed_lakh"] += float(a["committed_amount_lakh"])
            by_cat[cat]["disbursed_lakh"] += float(a["disbursed_amount_lakh"])

        # By neighbourhood
        by_nbr_map: Dict[str, Any] = {}
        for a in allocs:
            nid = a["neighbourhood_id"]
            if nid not in by_nbr_map:
                by_nbr_map[nid] = {
                    "neighbourhood_id": nid,
                    "neighbourhood_name": a["neighbourhood_name"],
                    "project_count": 0,
                    "allocated_lakh": 0.0,
                    "disbursed_lakh": 0.0,
                }
            by_nbr_map[nid]["project_count"] += 1
            by_nbr_map[nid]["allocated_lakh"] += float(a["allocated_amount_lakh"])
            by_nbr_map[nid]["disbursed_lakh"] += float(a["disbursed_amount_lakh"])

        return PublicAccountabilitySummary(
            fiscal_year="2025-2026",
            total_allocated_lakh=round(tot_allocated, 4),
            total_committed_lakh=round(tot_committed, 4),
            total_disbursed_lakh=round(tot_disbursed, 4),
            total_remaining_lakh=round(tot_remaining, 4),
            allocation_count=len(allocs),
            completed_milestones_count=completed_m,
            pending_milestones_count=pending_m,
            open_discrepancies_count=open_disc,
            resolved_discrepancies_count=resolved_disc,
            by_category=by_cat,
            by_neighbourhood=list(by_nbr_map.values()),
            disclaimer="All figures in Lakh INR from the official municipal capital expenditure ledger in Supabase PostgreSQL.",
        )

    def get_partner_budget_summary(self, vendor_id: str) -> PartnerBudgetSummary:
        """
        Fetch budget visibility strictly for the assigned vendor/contractor.
        Computes allocated, committed, disbursed, pending, and remaining balances per project.
        """
        allocations = self.list_allocations(vendor_id=vendor_id)
        projects: List[PartnerProjectBudget] = []
        proposals: List[PartnerProposalItem] = []
        vendor_name = vendor_id
        tot_allocated = 0.0

        for alloc in allocations:
            vendor_cmts = [c for c in alloc.commitments if c.vendor_id == vendor_id]
            if not vendor_cmts:
                continue

            tot_allocated += alloc.allocated_amount_lakh
            v_committed = sum(c.committed_amount_lakh for c in vendor_cmts)
            if vendor_cmts[0].vendor_name:
                vendor_name = vendor_cmts[0].vendor_name

            cmt_ids = {c.commitment_id for c in vendor_cmts}
            v_disbursed = sum(
                d.amount_lakh for d in alloc.disbursements
                if d.commitment_id in cmt_ids and d.status == DisbursementStatus.COMPLETED
            )
            v_pending = sum(
                d.amount_lakh for d in alloc.disbursements
                if d.commitment_id in cmt_ids and d.status == DisbursementStatus.PENDING_APPROVAL
            )
            # Remaining budget = committed - disbursed - pending requests (no double counting)
            v_remaining = max(0.0, v_committed - v_disbursed - v_pending)
            v_util = round((v_disbursed / v_committed * 100.0), 1) if v_committed > 0 else 0.0

            contract_refs = ", ".join(dict.fromkeys(c.contract_reference for c in vendor_cmts))
            verified_count = sum(1 for m in alloc.milestones if m.status == MilestoneStatus.VERIFIED_COMPLETE)

            projects.append(
                PartnerProjectBudget(
                    allocation_id=alloc.allocation_id,
                    title=alloc.title,
                    category=alloc.category,
                    neighbourhood_id=alloc.neighbourhood_id,
                    neighbourhood_name=alloc.neighbourhood_name,
                    contract_reference=contract_refs,
                    allocated_amount_lakh=round(alloc.allocated_amount_lakh, 4),
                    committed_amount_lakh=round(v_committed, 4),
                    disbursed_amount_lakh=round(v_disbursed, 4),
                    pending_requests_lakh=round(v_pending, 4),
                    remaining_balance_lakh=round(v_remaining, 4),
                    utilization_pct=v_util,
                    milestones_count=len(alloc.milestones),
                    verified_milestones_count=verified_count,
                )
            )

            for d in alloc.disbursements:
                if d.commitment_id in cmt_ids:
                    proposals.append(
                        PartnerProposalItem(
                            proposal_id=d.disbursement_id,
                            allocation_id=alloc.allocation_id,
                            project_title=alloc.title,
                            amount_lakh=d.amount_lakh,
                            purpose=d.payment_reference,
                            status=d.status.value,
                            submission_date=d.disbursed_at.isoformat(),
                        )
                    )

        proposals.sort(key=lambda p: p.submission_date, reverse=True)
        tot_committed = sum(p.committed_amount_lakh for p in projects)
        tot_disbursed = sum(p.disbursed_amount_lakh for p in projects)
        tot_pending = sum(p.pending_requests_lakh for p in projects)
        tot_remaining = round(max(0.0, tot_committed - tot_disbursed - tot_pending), 4)
        overall_util = round((tot_disbursed / tot_committed * 100.0), 1) if tot_committed > 0 else 0.0

        return PartnerBudgetSummary(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            total_allocated_lakh=round(tot_allocated, 4),
            total_committed_lakh=round(tot_committed, 4),
            total_disbursed_lakh=round(tot_disbursed, 4),
            total_pending_requests_lakh=round(tot_pending, 4),
            total_remaining_balance_lakh=tot_remaining,
            overall_utilization_pct=overall_util,
            projects=projects,
            proposals=proposals,
        )

    def submit_expenditure_request(
        self,
        allocation_id: str,
        payload: ExpenditureRequestCreate,
        actor_id: str,
        actor_role: str,
        vendor_id: Optional[str] = None,
    ) -> DisbursementRecord:
        """
        Record a proposed contractor expenditure or claim request.
        Enforces strict budget caps:
        - Must be assigned to this vendor
        - Cannot exceed remaining available balance
        - Saved with status 'pending_approval' (awaits municipal authorization)
        """
        alloc = self.get_allocation(allocation_id)
        cmt = next((c for c in alloc.commitments if c.commitment_id == payload.commitment_id), None)
        if not cmt:
            raise ValueError(f"Commitment '{payload.commitment_id}' not found under allocation '{allocation_id}'.")

        if vendor_id and cmt.vendor_id != vendor_id:
            raise PermissionError("Access denied: You cannot submit expenditure for another contractor's commitment.")

        already_disbursed = sum(
            d.amount_lakh for d in alloc.disbursements
            if d.commitment_id == cmt.commitment_id and d.status == DisbursementStatus.COMPLETED
        )
        already_pending = sum(
            d.amount_lakh for d in alloc.disbursements
            if d.commitment_id == cmt.commitment_id and d.status == DisbursementStatus.PENDING_APPROVAL
        )
        available_balance = round(cmt.committed_amount_lakh - already_disbursed - already_pending, 4)

        if payload.amount_lakh > available_balance + 0.0001:
            raise ValueError(
                f"Proposed expenditure ₹{payload.amount_lakh:.2f}L exceeds available commitment balance ₹{available_balance:.2f}L "
                f"(Committed: ₹{cmt.committed_amount_lakh:.2f}L, Disbursed: ₹{already_disbursed:.2f}L, Pending: ₹{already_pending:.2f}L)."
            )

        if (alloc.disbursed_amount_lakh + payload.amount_lakh) > (alloc.allocated_amount_lakh + 0.0001):
            raise ValueError(
                f"Proposed expenditure would exceed overall municipal allocation cap of ₹{alloc.allocated_amount_lakh:.2f}L."
            )

        did = f"DSB-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()

        row = {
            "disbursement_id": did,
            "allocation_id": allocation_id,
            "commitment_id": payload.commitment_id,
            "milestone_id": payload.milestone_id,
            "amount_lakh": round(payload.amount_lakh, 4),
            "payment_reference": payload.payment_reference,
            "recipient_entity": payload.recipient_entity,
            "status": DisbursementStatus.PENDING_APPROVAL.value,
            "approved_by": "PENDING_MUNICIPAL_REVIEW",
            "disbursed_at": now_iso,
        }

        self.client.table("disbursements").insert(row).execute()

        self._record_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            event_type=AuditEventType.DISBURSEMENT_EXECUTED,
            entity_type="DISBURSEMENT",
            entity_id=did,
            summary=f"Proposed expenditure request ₹{payload.amount_lakh:.2f}L submitted by {actor_id} for review ({payload.payment_reference}).",
            new_state=row,
        )

        return DisbursementRecord(
            disbursement_id=did,
            allocation_id=allocation_id,
            commitment_id=payload.commitment_id,
            milestone_id=payload.milestone_id,
            amount_lakh=payload.amount_lakh,
            payment_reference=payload.payment_reference,
            recipient_entity=payload.recipient_entity,
            status=DisbursementStatus.PENDING_APPROVAL,
            approved_by="PENDING_MUNICIPAL_REVIEW",
            disbursed_at=datetime.datetime.fromisoformat(now_iso),
        )

