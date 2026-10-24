"""
UrbanSage AI — Financial Accountability & Audit Repository (Stage 6)
=====================================================================
Thread-safe persistence layer for allocations, commitments, disbursements,
milestones, documentary evidence, discrepancies, and tamper-evident audit logs.

Supports both in-memory SQLite (for isolated unit tests) and file-backed SQLite
for persistent local execution.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import hashlib
import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

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
    DiscrepancySeverity,
    DiscrepancyStatus,
    DiscrepancyType,
    EvidenceMetadata,
    EvidenceSubmit,
    EvidenceType,
    EvidenceVerificationStatus,
    FinancialCommitment,
    FinancialDiscrepancy,
    ImplementationMilestone,
    InterventionAllocation,
    MilestoneCreate,
    MilestoneStatus,
    MilestoneUpdate,
    PublicAccountabilitySummary,
    VerificationDecision,
    VerificationSubmit,
)

logger = logging.getLogger("urbansage.accountability.repo")


class AccountabilityRepository:
    """
    SQLite persistence for financial accountability, milestones, and audit trails.
    """

    def __init__(self, db_path: str = ":memory:", auto_seed: bool = True):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._last_event_hash: str = "GENESIS_URBANSAGE_FINANCIAL_AUDIT_LEDGER_2025"

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA busy_timeout = 5000;")
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL;")

        self._create_tables()

        if auto_seed:
            self._seed_initial_demonstration_data()

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def _create_tables(self) -> None:
        """Initialize schema tables and indexes."""
        with self._lock:
            with self._conn:
                self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS allocations (
                    allocation_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    neighbourhood_id TEXT NOT NULL,
                    neighbourhood_name TEXT NOT NULL,
                    intervention_id TEXT NOT NULL,
                    intervention_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    fiscal_year TEXT NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'INR',
                    allocated_amount_lakh REAL NOT NULL,
                    committed_amount_lakh REAL NOT NULL DEFAULT 0.0,
                    disbursed_amount_lakh REAL NOT NULL DEFAULT 0.0,
                    planned_units INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    authorized_by TEXT NOT NULL,
                    council_resolution_ref TEXT,
                    source_optimizer_run_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commitments (
                    commitment_id TEXT PRIMARY KEY,
                    allocation_id TEXT NOT NULL,
                    vendor_id TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    contract_reference TEXT NOT NULL,
                    committed_amount_lakh REAL NOT NULL,
                    status TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(allocation_id) REFERENCES allocations(allocation_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS milestones (
                    milestone_id TEXT PRIMARY KEY,
                    allocation_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    sequence_order INTEGER NOT NULL,
                    target_completion_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    disbursement_tied_amount_lakh REAL NOT NULL,
                    percent_progress INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(allocation_id) REFERENCES allocations(allocation_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidence_metadata (
                    evidence_id TEXT PRIMARY KEY,
                    milestone_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    document_hash TEXT NOT NULL,
                    submitted_by TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    verification_notes TEXT,
                    FOREIGN KEY(milestone_id) REFERENCES milestones(milestone_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS verification_decisions (
                    decision_id TEXT PRIMARY KEY,
                    milestone_id TEXT UNIQUE NOT NULL,
                    decision TEXT NOT NULL,
                    verifier_id TEXT NOT NULL,
                    verifier_name TEXT NOT NULL,
                    comments TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    passed_inspection INTEGER NOT NULL,
                    FOREIGN KEY(milestone_id) REFERENCES milestones(milestone_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS disbursements (
                    disbursement_id TEXT PRIMARY KEY,
                    allocation_id TEXT NOT NULL,
                    commitment_id TEXT NOT NULL,
                    milestone_id TEXT,
                    amount_lakh REAL NOT NULL,
                    payment_reference TEXT NOT NULL,
                    recipient_entity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    disbursed_at TEXT NOT NULL,
                    FOREIGN KEY(allocation_id) REFERENCES allocations(allocation_id) ON DELETE CASCADE,
                    FOREIGN KEY(commitment_id) REFERENCES commitments(commitment_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS discrepancies (
                    discrepancy_id TEXT PRIMARY KEY,
                    allocation_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    discrepancy_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount_involved_lakh REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolved_by TEXT,
                    resolution_notes TEXT,
                    resolved_at TEXT,
                    FOREIGN KEY(allocation_id) REFERENCES allocations(allocation_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    previous_state TEXT,
                    new_state TEXT,
                    previous_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_allocations_neighbourhood ON allocations(neighbourhood_id);
                CREATE INDEX IF NOT EXISTS idx_allocations_category ON allocations(category);
                CREATE INDEX IF NOT EXISTS idx_commitments_allocation ON commitments(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_milestones_allocation ON milestones(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_disbursements_allocation ON disbursements(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_discrepancies_allocation ON discrepancies(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_discrepancies_status ON discrepancies(status);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
                """)

    # -----------------------------------------------------------------------
    # Tamper-Evident Audit Logging
    # -----------------------------------------------------------------------

    def _record_audit_event(
        self,
        actor_id: str,
        actor_role: str,
        event_type: AuditEventType,
        entity_type: str,
        entity_id: str,
        summary: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Record an immutable audit event with a cryptographic hash chain link."""
        with self._lock:
            # Get latest event hash
            cursor = self._conn.execute(
                "SELECT event_hash FROM audit_events ORDER BY timestamp DESC, rowid DESC LIMIT 1"
            )
            row = cursor.fetchone()
            prev_hash = row["event_hash"] if row else self._last_event_hash

            event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Deterministic SHA-256 hash chaining
            payload = f"{prev_hash}|{now_iso}|{actor_id}|{actor_role}|{event_type.value}|{entity_type}|{entity_id}|{summary}"
            event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            prev_json = json.dumps(previous_state) if previous_state else None
            new_json = json.dumps(new_state) if new_state else None

            self._conn.execute(
                """
                INSERT INTO audit_events (
                    event_id, timestamp, actor_id, actor_role, event_type,
                    entity_type, entity_id, summary, previous_state, new_state,
                    previous_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    now_iso,
                    actor_id,
                    actor_role,
                    event_type.value,
                    entity_type,
                    entity_id,
                    summary,
                    prev_json,
                    new_json,
                    prev_hash,
                    event_hash,
                ),
            )
            self._last_event_hash = event_hash

            return AuditEvent(
                event_id=event_id,
                timestamp=now,
                actor_id=actor_id,
                actor_role=actor_role,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                summary=summary,
                previous_state=previous_state,
                new_state=new_state,
                previous_event_hash=prev_hash,
                event_hash=event_hash,
            )

    # -----------------------------------------------------------------------
    # Allocation Operations
    # -----------------------------------------------------------------------

    def create_allocation(self, payload: AllocationCreate, authorized_by: str) -> InterventionAllocation:
        """Create a new authorized budget allocation."""
        with self._lock:
            allocation_id = f"ALC-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO allocations (
                        allocation_id, title, neighbourhood_id, neighbourhood_name,
                        intervention_id, intervention_name, category, fiscal_year,
                        currency, allocated_amount_lakh, committed_amount_lakh,
                        disbursed_amount_lakh, planned_units, status, authorized_by,
                        council_resolution_ref, source_optimizer_run_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        allocation_id,
                        payload.title,
                        payload.neighbourhood_id,
                        payload.neighbourhood_name,
                        payload.intervention_id,
                        payload.intervention_name,
                        payload.category,
                        payload.fiscal_year,
                        "INR",
                        round(payload.allocated_amount_lakh, 4),
                        0.0,
                        0.0,
                        payload.planned_units,
                        AllocationStatus.PLANNED.value,
                        authorized_by,
                        payload.council_resolution_ref,
                        payload.source_optimizer_run_id,
                        now_iso,
                        now_iso,
                    ),
                )

                self._record_audit_event(
                    actor_id=authorized_by,
                    actor_role="administrator",
                    event_type=AuditEventType.ALLOCATION_CREATED,
                    entity_type="ALLOCATION",
                    entity_id=allocation_id,
                    summary=f"Authorized ₹{payload.allocated_amount_lakh:.2f}L budget for {payload.title} in {payload.neighbourhood_name}.",
                    new_state=payload.model_dump(),
                )

            return self.get_allocation(allocation_id)

    def list_allocations(
        self,
        neighbourhood_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        vendor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InterventionAllocation]:
        """List budget allocations with optional filtering."""
        with self._lock:
            query = "SELECT allocation_id FROM allocations WHERE 1=1"
            params: List[Any] = []

            if neighbourhood_id:
                query += " AND neighbourhood_id = ?"
                params.append(neighbourhood_id)
            if category:
                query += " AND category = ?"
                params.append(category)
            if status:
                query += " AND status = ?"
                params.append(status)
            if vendor_id:
                query += " AND allocation_id IN (SELECT allocation_id FROM commitments WHERE vendor_id = ?)"
                params.append(vendor_id)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()

            return [self.get_allocation(row["allocation_id"]) for row in rows]

    def get_allocation(self, allocation_id: str) -> InterventionAllocation:
        """Retrieve full details of an allocation including milestones, commitments, disbursements."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM allocations WHERE allocation_id = ?", (allocation_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Allocation '{allocation_id}' not found.")

            # Fetch milestones
            m_cursor = self._conn.execute(
                "SELECT * FROM milestones WHERE allocation_id = ? ORDER BY sequence_order ASC",
                (allocation_id,),
            )
            milestones: List[ImplementationMilestone] = []
            for m_row in m_cursor.fetchall():
                mid = m_row["milestone_id"]

                # Fetch evidence items
                e_cursor = self._conn.execute("SELECT * FROM evidence_metadata WHERE milestone_id = ?", (mid,))
                evidence_items = [
                    EvidenceMetadata(
                        evidence_id=e["evidence_id"],
                        milestone_id=e["milestone_id"],
                        evidence_type=EvidenceType(e["evidence_type"]),
                        title=e["title"],
                        description=e["description"],
                        file_name=e["file_name"],
                        mime_type=e["mime_type"],
                        file_size_bytes=e["file_size_bytes"],
                        document_hash=e["document_hash"],
                        submitted_by=e["submitted_by"],
                        submitted_at=datetime.datetime.fromisoformat(e["submitted_at"]),
                        verification_status=EvidenceVerificationStatus(e["verification_status"]),
                        verification_notes=e["verification_notes"],
                    )
                    for e in e_cursor.fetchall()
                ]

                # Fetch verification decision
                v_cursor = self._conn.execute("SELECT * FROM verification_decisions WHERE milestone_id = ?", (mid,))
                v_row = v_cursor.fetchone()
                verification = (
                    VerificationDecision(
                        decision_id=v_row["decision_id"],
                        milestone_id=v_row["milestone_id"],
                        decision=v_row["decision"],
                        verifier_id=v_row["verifier_id"],
                        verifier_name=v_row["verifier_name"],
                        comments=v_row["comments"],
                        decided_at=datetime.datetime.fromisoformat(v_row["decided_at"]),
                        passed_inspection=bool(v_row["passed_inspection"]),
                    )
                    if v_row
                    else None
                )

                milestones.append(
                    ImplementationMilestone(
                        milestone_id=mid,
                        allocation_id=allocation_id,
                        title=m_row["title"],
                        description=m_row["description"],
                        sequence_order=m_row["sequence_order"],
                        target_completion_date=m_row["target_completion_date"],
                        status=MilestoneStatus(m_row["status"]),
                        disbursement_tied_amount_lakh=m_row["disbursement_tied_amount_lakh"],
                        percent_progress=m_row["percent_progress"],
                        evidence_items=evidence_items,
                        verification_decision=verification,
                        completed_at=datetime.datetime.fromisoformat(m_row["completed_at"])
                        if m_row["completed_at"]
                        else None,
                        created_at=datetime.datetime.fromisoformat(m_row["created_at"]),
                        updated_at=datetime.datetime.fromisoformat(m_row["updated_at"]),
                    )
                )

            # Fetch commitments
            c_cursor = self._conn.execute(
                "SELECT * FROM commitments WHERE allocation_id = ? ORDER BY created_at ASC",
                (allocation_id,),
            )
            commitments = [
                FinancialCommitment(
                    commitment_id=c["commitment_id"],
                    allocation_id=c["allocation_id"],
                    vendor_id=c["vendor_id"],
                    vendor_name=c["vendor_name"],
                    contract_reference=c["contract_reference"],
                    committed_amount_lakh=c["committed_amount_lakh"],
                    status=CommitmentStatus(c["status"]),
                    approved_by=c["approved_by"],
                    created_at=datetime.datetime.fromisoformat(c["created_at"]),
                )
                for c in c_cursor.fetchall()
            ]

            # Fetch disbursements
            d_cursor = self._conn.execute(
                "SELECT * FROM disbursements WHERE allocation_id = ? ORDER BY disbursed_at ASC",
                (allocation_id,),
            )
            disbursements = [
                DisbursementRecord(
                    disbursement_id=d["disbursement_id"],
                    allocation_id=d["allocation_id"],
                    commitment_id=d["commitment_id"],
                    milestone_id=d["milestone_id"],
                    amount_lakh=d["amount_lakh"],
                    payment_reference=d["payment_reference"],
                    recipient_entity=d["recipient_entity"],
                    status=DisbursementStatus(d["status"]),
                    approved_by=d["approved_by"],
                    disbursed_at=datetime.datetime.fromisoformat(d["disbursed_at"]),
                )
                for d in d_cursor.fetchall()
            ]

            # Fetch discrepancies
            disc_cursor = self._conn.execute(
                "SELECT * FROM discrepancies WHERE allocation_id = ? ORDER BY detected_at DESC",
                (allocation_id,),
            )
            discrepancies = [
                FinancialDiscrepancy(
                    discrepancy_id=disc["discrepancy_id"],
                    allocation_id=disc["allocation_id"],
                    severity=DiscrepancySeverity(disc["severity"]),
                    discrepancy_type=DiscrepancyType(disc["discrepancy_type"]),
                    title=disc["title"],
                    description=disc["description"],
                    amount_involved_lakh=disc["amount_involved_lakh"],
                    status=DiscrepancyStatus(disc["status"]),
                    detected_at=datetime.datetime.fromisoformat(disc["detected_at"]),
                    resolved_by=disc["resolved_by"],
                    resolution_notes=disc["resolution_notes"],
                    resolved_at=datetime.datetime.fromisoformat(disc["resolved_at"])
                    if disc["resolved_at"]
                    else None,
                )
                for disc in disc_cursor.fetchall()
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
                currency="INR",
                allocated_amount_lakh=row["allocated_amount_lakh"],
                committed_amount_lakh=row["committed_amount_lakh"],
                disbursed_amount_lakh=row["disbursed_amount_lakh"],
                planned_units=row["planned_units"],
                status=AllocationStatus(row["status"]),
                authorized_by=row["authorized_by"],
                council_resolution_ref=row["council_resolution_ref"],
                source_optimizer_run_id=row["source_optimizer_run_id"],
                milestones=milestones,
                commitments=commitments,
                disbursements=disbursements,
                discrepancies=discrepancies,
                created_at=datetime.datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
            )

    # -----------------------------------------------------------------------
    # Commitment Operations
    # -----------------------------------------------------------------------

    def add_commitment(
        self,
        allocation_id: str,
        payload: CommitmentCreate,
        approved_by: str,
    ) -> FinancialCommitment:
        """Add a contractor commitment, verifying it does not exceed allocated budget."""
        with self._lock:
            allocation = self.get_allocation(allocation_id)

            new_total = allocation.committed_amount_lakh + payload.committed_amount_lakh
            if new_total > allocation.allocated_amount_lakh:
                overrun = new_total - allocation.allocated_amount_lakh
                # Flag discrepancy
                self._flag_discrepancy(
                    allocation_id=allocation_id,
                    severity=DiscrepancySeverity.HIGH,
                    discrepancy_type=DiscrepancyType.COST_OVERRUN,
                    title="Contract commitment exceeds authorized allocation",
                    description=(
                        f"Attempted commitment of ₹{payload.committed_amount_lakh:.2f}L with existing "
                        f"commitments ₹{allocation.committed_amount_lakh:.2f}L exceeds authorized cap "
                        f"₹{allocation.allocated_amount_lakh:.2f}L by ₹{overrun:.2f}L."
                    ),
                    amount_involved_lakh=round(overrun, 4),
                )
                raise ValueError(
                    f"Commitment of ₹{payload.committed_amount_lakh:.2f}L would exceed authorized budget "
                    f"by ₹{overrun:.2f}L (Budget: ₹{allocation.allocated_amount_lakh:.2f}L, Existing: ₹{allocation.committed_amount_lakh:.2f}L)."
                )

            commitment_id = f"CMT-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO commitments (
                        commitment_id, allocation_id, vendor_id, vendor_name,
                        contract_reference, committed_amount_lakh, status, approved_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        commitment_id,
                        allocation_id,
                        payload.vendor_id,
                        payload.vendor_name,
                        payload.contract_reference,
                        round(payload.committed_amount_lakh, 4),
                        CommitmentStatus.APPROVED.value,
                        approved_by,
                        now_iso,
                    ),
                )

                # Update allocation committed amount
                new_status = AllocationStatus.COMMITTED.value
                self._conn.execute(
                    """
                    UPDATE allocations
                    SET committed_amount_lakh = ?, status = ?, updated_at = ?
                    WHERE allocation_id = ?
                    """,
                    (round(new_total, 4), new_status, now_iso, allocation_id),
                )

                self._record_audit_event(
                    actor_id=approved_by,
                    actor_role="administrator",
                    event_type=AuditEventType.COMMITMENT_RECORDED,
                    entity_type="COMMITMENT",
                    entity_id=commitment_id,
                    summary=f"Approved contract commitment of ₹{payload.committed_amount_lakh:.2f}L to {payload.vendor_name}.",
                    new_state=payload.model_dump(),
                )

            return FinancialCommitment(
                commitment_id=commitment_id,
                allocation_id=allocation_id,
                vendor_id=payload.vendor_id,
                vendor_name=payload.vendor_name,
                contract_reference=payload.contract_reference,
                committed_amount_lakh=round(payload.committed_amount_lakh, 4),
                status=CommitmentStatus.APPROVED,
                approved_by=approved_by,
                created_at=now,
            )

    # -----------------------------------------------------------------------
    # Milestone Operations
    # -----------------------------------------------------------------------

    def add_milestone(
        self,
        allocation_id: str,
        payload: MilestoneCreate,
        actor_id: str,
    ) -> ImplementationMilestone:
        """Add an implementation milestone to an allocation."""
        with self._lock:
            # Verify allocation exists
            self.get_allocation(allocation_id)

            milestone_id = f"MLS-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO milestones (
                        milestone_id, allocation_id, title, description,
                        sequence_order, target_completion_date, status,
                        disbursement_tied_amount_lakh, percent_progress,
                        completed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        milestone_id,
                        allocation_id,
                        payload.title,
                        payload.description,
                        payload.sequence_order,
                        payload.target_completion_date,
                        MilestoneStatus.PENDING.value,
                        round(payload.disbursement_tied_amount_lakh, 4),
                        0,
                        now_iso,
                        now_iso,
                    ),
                )

                self._record_audit_event(
                    actor_id=actor_id,
                    actor_role="administrator",
                    event_type=AuditEventType.MILESTONE_UPDATED,
                    entity_type="MILESTONE",
                    entity_id=milestone_id,
                    summary=f"Added milestone #{payload.sequence_order}: '{payload.title}' to allocation {allocation_id}.",
                    new_state=payload.model_dump(),
                )

            return ImplementationMilestone(
                milestone_id=milestone_id,
                allocation_id=allocation_id,
                title=payload.title,
                description=payload.description,
                sequence_order=payload.sequence_order,
                target_completion_date=payload.target_completion_date,
                status=MilestoneStatus.PENDING,
                disbursement_tied_amount_lakh=payload.disbursement_tied_amount_lakh,
                percent_progress=0,
                created_at=now,
                updated_at=now,
            )

    def update_milestone_progress(
        self,
        milestone_id: str,
        payload: MilestoneUpdate,
        actor_id: str,
        actor_role: str,
    ) -> ImplementationMilestone:
        """Update milestone progress percentage and status."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM milestones WHERE milestone_id = ?", (milestone_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Milestone '{milestone_id}' not found.")

            current_status = MilestoneStatus(row["status"])
            current_progress = row["percent_progress"]
            allocation_id = row["allocation_id"]

            new_status = payload.status if payload.status is not None else current_status
            new_progress = payload.percent_progress if payload.percent_progress is not None else current_progress

            # If contractor submits for review, progress must be 100% or marked submitted
            if new_status == MilestoneStatus.SUBMITTED_FOR_REVIEW and new_progress < 80:
                raise ValueError("Milestone progress must be at least 80% to submit for municipal review.")

            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    UPDATE milestones
                    SET status = ?, percent_progress = ?, updated_at = ?
                    WHERE milestone_id = ?
                    """,
                    (new_status.value, new_progress, now_iso, milestone_id),
                )

                # If milestone progress is moving, update allocation status to IN_PROGRESS
                if new_progress > 0:
                    self._conn.execute(
                        "UPDATE allocations SET status = ?, updated_at = ? WHERE allocation_id = ?",
                        (AllocationStatus.IN_PROGRESS.value, now_iso, allocation_id),
                    )

                self._record_audit_event(
                    actor_id=actor_id,
                    actor_role=actor_role,
                    event_type=AuditEventType.MILESTONE_UPDATED,
                    entity_type="MILESTONE",
                    entity_id=milestone_id,
                    summary=f"Updated progress to {new_progress}% (status: {new_status.value}).",
                    previous_state={"status": current_status.value, "percent_progress": current_progress},
                    new_state={"status": new_status.value, "percent_progress": new_progress},
                )

            # Return updated allocation's milestone
            alloc = self.get_allocation(allocation_id)
            for m in alloc.milestones:
                if m.milestone_id == milestone_id:
                    return m
            raise ValueError("Updated milestone not found.")

    def submit_evidence(
        self,
        milestone_id: str,
        payload: EvidenceSubmit,
        submitted_by: str,
        actor_role: str,
    ) -> EvidenceMetadata:
        """Attach documentary evidence metadata to a milestone."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM milestones WHERE milestone_id = ?", (milestone_id,))
            m_row = cursor.fetchone()
            if not m_row:
                raise ValueError(f"Milestone '{milestone_id}' not found.")

            evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Hash generation if not provided
            doc_hash = payload.document_hash or hashlib.sha256(
                f"{payload.file_name}|{payload.file_size_bytes}|{now_iso}".encode("utf-8")
            ).hexdigest()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO evidence_metadata (
                        evidence_id, milestone_id, evidence_type, title, description,
                        file_name, mime_type, file_size_bytes, document_hash,
                        submitted_by, submitted_at, verification_status, verification_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        evidence_id,
                        milestone_id,
                        payload.evidence_type.value,
                        payload.title,
                        payload.description,
                        payload.file_name,
                        payload.mime_type,
                        payload.file_size_bytes,
                        doc_hash,
                        submitted_by,
                        now_iso,
                        EvidenceVerificationStatus.PENDING_REVIEW.value,
                    ),
                )

                self._record_audit_event(
                    actor_id=submitted_by,
                    actor_role=actor_role,
                    event_type=AuditEventType.EVIDENCE_ATTACHED,
                    entity_type="EVIDENCE",
                    entity_id=evidence_id,
                    summary=f"Attached evidence '{payload.title}' ({payload.evidence_type.value}) to milestone {milestone_id}.",
                    new_state=payload.model_dump(),
                )

            return EvidenceMetadata(
                evidence_id=evidence_id,
                milestone_id=milestone_id,
                evidence_type=payload.evidence_type,
                title=payload.title,
                description=payload.description,
                file_name=payload.file_name,
                mime_type=payload.mime_type,
                file_size_bytes=payload.file_size_bytes,
                document_hash=doc_hash,
                submitted_by=submitted_by,
                submitted_at=now,
                verification_status=EvidenceVerificationStatus.PENDING_REVIEW,
            )

    def verify_milestone(
        self,
        milestone_id: str,
        payload: VerificationSubmit,
        verifier_id: str,
        verifier_name: str,
    ) -> VerificationDecision:
        """Record formal municipal inspection decision on milestone completion."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM milestones WHERE milestone_id = ?", (milestone_id,))
            m_row = cursor.fetchone()
            if not m_row:
                raise ValueError(f"Milestone '{milestone_id}' not found.")

            passed = payload.decision == "approved"
            decision_id = f"VDEC-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            new_status = MilestoneStatus.VERIFIED_COMPLETE if passed else MilestoneStatus.FAILED_VERIFICATION

            with self._conn:
                # Upsert verification decision
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO verification_decisions (
                        decision_id, milestone_id, decision, verifier_id, verifier_name,
                        comments, decided_at, passed_inspection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        milestone_id,
                        payload.decision,
                        verifier_id,
                        verifier_name,
                        payload.comments,
                        now_iso,
                        1 if passed else 0,
                    ),
                )

                # Update milestone status and completion timestamp
                self._conn.execute(
                    """
                    UPDATE milestones
                    SET status = ?, percent_progress = ?, completed_at = ?, updated_at = ?
                    WHERE milestone_id = ?
                    """,
                    (
                        new_status.value,
                        100 if passed else m_row["percent_progress"],
                        now_iso if passed else None,
                        now_iso,
                        milestone_id,
                    ),
                )

                # Also update evidence items associated with milestone
                evidence_status = (
                    EvidenceVerificationStatus.VERIFIED.value if passed else EvidenceVerificationStatus.REJECTED.value
                )
                self._conn.execute(
                    """
                    UPDATE evidence_metadata
                    SET verification_status = ?, verification_notes = ?
                    WHERE milestone_id = ?
                    """,
                    (evidence_status, payload.comments, milestone_id),
                )

                self._record_audit_event(
                    actor_id=verifier_id,
                    actor_role="administrator",
                    event_type=AuditEventType.VERIFICATION_RECORDED,
                    entity_type="MILESTONE",
                    entity_id=milestone_id,
                    summary=f"Milestone verification decision '{payload.decision.upper()}' by {verifier_name}.",
                    new_state=payload.model_dump(),
                )

            return VerificationDecision(
                decision_id=decision_id,
                milestone_id=milestone_id,
                decision=payload.decision,
                verifier_id=verifier_id,
                verifier_name=verifier_name,
                comments=payload.comments,
                decided_at=now,
                passed_inspection=passed,
            )

    # -----------------------------------------------------------------------
    # Disbursement Operations
    # -----------------------------------------------------------------------

    def execute_disbursement(
        self,
        allocation_id: str,
        payload: DisbursementCreate,
        approved_by: str,
    ) -> DisbursementRecord:
        """
        Record a monetary disbursement to a contractor.
        Enforces:
        1. Disbursement must not cause total disbursements to exceed allocated budget.
        2. If tied to a milestone, verifies whether the milestone was approved. If unverified, flags discrepancy.
        """
        with self._lock:
            allocation = self.get_allocation(allocation_id)

            if payload.amount_lakh <= 0:
                raise ValueError("Disbursement amount must be greater than zero.")

            new_disbursed_total = allocation.disbursed_amount_lakh + payload.amount_lakh
            if new_disbursed_total > allocation.allocated_amount_lakh:
                overrun = new_disbursed_total - allocation.allocated_amount_lakh
                self._flag_discrepancy(
                    allocation_id=allocation_id,
                    severity=DiscrepancySeverity.CRITICAL,
                    discrepancy_type=DiscrepancyType.COST_OVERRUN,
                    title="Disbursement exceeds authorized allocation budget",
                    description=(
                        f"Attempted disbursement of ₹{payload.amount_lakh:.2f}L would push total disbursements "
                        f"to ₹{new_disbursed_total:.2f}L, exceeding authorized allocation ₹{allocation.allocated_amount_lakh:.2f}L."
                    ),
                    amount_involved_lakh=round(overrun, 4),
                )
                raise ValueError(
                    f"Disbursement of ₹{payload.amount_lakh:.2f}L exceeds authorized allocation "
                    f"budget by ₹{overrun:.2f}L (Cap: ₹{allocation.allocated_amount_lakh:.2f}L, Disbursed: ₹{allocation.disbursed_amount_lakh:.2f}L)."
                )

            # Check milestone status if tied
            if payload.milestone_id:
                m_found = next((m for m in allocation.milestones if m.milestone_id == payload.milestone_id), None)
                if not m_found or m_found.status != MilestoneStatus.VERIFIED_COMPLETE:
                    # Flag unverified disbursement discrepancy
                    self._flag_discrepancy(
                        allocation_id=allocation_id,
                        severity=DiscrepancySeverity.HIGH,
                        discrepancy_type=DiscrepancyType.UNVERIFIED_DISBURSEMENT,
                        title="Disbursement executed for unverified milestone",
                        description=(
                            f"Disbursement of ₹{payload.amount_lakh:.2f}L was issued against milestone "
                            f"'{payload.milestone_id}' before municipal verification was approved."
                        ),
                        amount_involved_lakh=payload.amount_lakh,
                    )

            disbursement_id = f"DSB-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO disbursements (
                        disbursement_id, allocation_id, commitment_id, milestone_id,
                        amount_lakh, payment_reference, recipient_entity, status, approved_by, disbursed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        disbursement_id,
                        allocation_id,
                        payload.commitment_id,
                        payload.milestone_id,
                        round(payload.amount_lakh, 4),
                        payload.payment_reference,
                        payload.recipient_entity,
                        DisbursementStatus.COMPLETED.value,
                        approved_by,
                        now_iso,
                    ),
                )

                # Update allocation disbursed total
                all_completed = False
                if allocation.milestones:
                    all_completed = all(m.status == MilestoneStatus.VERIFIED_COMPLETE for m in allocation.milestones)

                alloc_status = AllocationStatus.COMPLETED.value if all_completed else AllocationStatus.IN_PROGRESS.value

                self._conn.execute(
                    """
                    UPDATE allocations
                    SET disbursed_amount_lakh = ?, status = ?, updated_at = ?
                    WHERE allocation_id = ?
                    """,
                    (round(new_disbursed_total, 4), alloc_status, now_iso, allocation_id),
                )

                self._record_audit_event(
                    actor_id=approved_by,
                    actor_role="administrator",
                    event_type=AuditEventType.DISBURSEMENT_EXECUTED,
                    entity_type="DISBURSEMENT",
                    entity_id=disbursement_id,
                    summary=f"Executed payout of ₹{payload.amount_lakh:.2f}L to {payload.recipient_entity} (Ref: {payload.payment_reference}).",
                    new_state=payload.model_dump(),
                )

            return DisbursementRecord(
                disbursement_id=disbursement_id,
                allocation_id=allocation_id,
                commitment_id=payload.commitment_id,
                milestone_id=payload.milestone_id,
                amount_lakh=round(payload.amount_lakh, 4),
                payment_reference=payload.payment_reference,
                recipient_entity=payload.recipient_entity,
                status=DisbursementStatus.COMPLETED,
                approved_by=approved_by,
                disbursed_at=now,
            )

    # -----------------------------------------------------------------------
    # Discrepancy Management
    # -----------------------------------------------------------------------

    def _flag_discrepancy(
        self,
        allocation_id: str,
        severity: DiscrepancySeverity,
        discrepancy_type: DiscrepancyType,
        title: str,
        description: str,
        amount_involved_lakh: float = 0.0,
    ) -> FinancialDiscrepancy:
        """Internal helper to log a detected discrepancy flag."""
        discrepancy_id = f"DSC-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.now(timezone.utc)
        now_iso = now.isoformat()

        self._conn.execute(
            """
            INSERT INTO discrepancies (
                discrepancy_id, allocation_id, severity, discrepancy_type,
                title, description, amount_involved_lakh, status, detected_at,
                resolved_by, resolution_notes, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                discrepancy_id,
                allocation_id,
                severity.value,
                discrepancy_type.value,
                title,
                description,
                round(amount_involved_lakh, 4),
                DiscrepancyStatus.OPEN.value,
                now_iso,
            ),
        )

        self._record_audit_event(
            actor_id="system-audit-monitor",
            actor_role="system",
            event_type=AuditEventType.DISCREPANCY_FLAGGED,
            entity_type="DISCREPANCY",
            entity_id=discrepancy_id,
            summary=f"Flagged {severity.value.upper()} discrepancy: {title} on allocation {allocation_id}.",
            new_state={"type": discrepancy_type.value, "amount_lakh": amount_involved_lakh},
        )

        return FinancialDiscrepancy(
            discrepancy_id=discrepancy_id,
            allocation_id=allocation_id,
            severity=severity,
            discrepancy_type=discrepancy_type,
            title=title,
            description=description,
            amount_involved_lakh=amount_involved_lakh,
            status=DiscrepancyStatus.OPEN,
            detected_at=now,
        )

    def list_discrepancies(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[FinancialDiscrepancy]:
        """List flagged discrepancies."""
        with self._lock:
            query = "SELECT * FROM discrepancies WHERE 1=1"
            params: List[Any] = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY detected_at DESC"
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                FinancialDiscrepancy(
                    discrepancy_id=r["discrepancy_id"],
                    allocation_id=r["allocation_id"],
                    severity=DiscrepancySeverity(r["severity"]),
                    discrepancy_type=DiscrepancyType(r["discrepancy_type"]),
                    title=r["title"],
                    description=r["description"],
                    amount_involved_lakh=r["amount_involved_lakh"],
                    status=DiscrepancyStatus(r["status"]),
                    detected_at=datetime.datetime.fromisoformat(r["detected_at"]),
                    resolved_by=r["resolved_by"],
                    resolution_notes=r["resolution_notes"],
                    resolved_at=datetime.datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None,
                )
                for r in rows
            ]

    def resolve_discrepancy(
        self,
        discrepancy_id: str,
        resolution_notes: str,
        action_taken: str,
        resolved_by: str,
    ) -> FinancialDiscrepancy:
        """Resolve or dismiss an open discrepancy with justification."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM discrepancies WHERE discrepancy_id = ?", (discrepancy_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Discrepancy '{discrepancy_id}' not found.")

            status_val = DiscrepancyStatus.RESOLVED.value if action_taken == "resolved" else DiscrepancyStatus.DISMISSED.value
            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    UPDATE discrepancies
                    SET status = ?, resolved_by = ?, resolution_notes = ?, resolved_at = ?
                    WHERE discrepancy_id = ?
                    """,
                    (status_val, resolved_by, resolution_notes, now_iso, discrepancy_id),
                )

                self._record_audit_event(
                    actor_id=resolved_by,
                    actor_role="administrator",
                    event_type=AuditEventType.DISCREPANCY_RESOLVED,
                    entity_type="DISCREPANCY",
                    entity_id=discrepancy_id,
                    summary=f"Resolved discrepancy '{row['title']}' ({action_taken}). Notes: {resolution_notes[:100]}...",
                    new_state={"status": status_val, "notes": resolution_notes},
                )

            return FinancialDiscrepancy(
                discrepancy_id=discrepancy_id,
                allocation_id=row["allocation_id"],
                severity=DiscrepancySeverity(row["severity"]),
                discrepancy_type=DiscrepancyType(row["discrepancy_type"]),
                title=row["title"],
                description=row["description"],
                amount_involved_lakh=row["amount_involved_lakh"],
                status=DiscrepancyStatus(status_val),
                detected_at=datetime.datetime.fromisoformat(row["detected_at"]),
                resolved_by=resolved_by,
                resolution_notes=resolution_notes,
                resolved_at=now,
            )

    # -----------------------------------------------------------------------
    # Audit Trail Operations
    # -----------------------------------------------------------------------

    def get_audit_trail(self, limit: int = 100, entity_id: Optional[str] = None) -> List[AuditEvent]:
        """Retrieve the hash-chained audit event history."""
        with self._lock:
            query = "SELECT * FROM audit_events WHERE 1=1"
            params: List[Any] = []

            if entity_id:
                query += " AND entity_id = ?"
                params.append(entity_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                AuditEvent(
                    event_id=r["event_id"],
                    timestamp=datetime.datetime.fromisoformat(r["timestamp"]),
                    actor_id=r["actor_id"],
                    actor_role=r["actor_role"],
                    event_type=AuditEventType(r["event_type"]),
                    entity_type=r["entity_type"],
                    entity_id=r["entity_id"],
                    summary=r["summary"],
                    previous_state=json.loads(r["previous_state"]) if r["previous_state"] else None,
                    new_state=json.loads(r["new_state"]) if r["new_state"] else None,
                    previous_event_hash=r["previous_event_hash"],
                    event_hash=r["event_hash"],
                )
                for r in rows
            ]

    # -----------------------------------------------------------------------
    # Public Accountability Summary
    # -----------------------------------------------------------------------

    def get_public_summary(self) -> PublicAccountabilitySummary:
        """Aggregate public financial ledger transparency summary."""
        with self._lock:
            # Totals
            cursor = self._conn.execute(
                """
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(allocated_amount_lakh), 0.0) as total_allocated,
                    COALESCE(SUM(committed_amount_lakh), 0.0) as total_committed,
                    COALESCE(SUM(disbursed_amount_lakh), 0.0) as total_disbursed
                FROM allocations
                """
            )
            agg = cursor.fetchone()
            tot_allocated = round(agg["total_allocated"], 2)
            tot_committed = round(agg["total_committed"], 2)
            tot_disbursed = round(agg["total_disbursed"], 2)
            tot_remaining = round(max(0.0, tot_allocated - tot_disbursed), 2)
            alloc_count = agg["count"]

            # Milestones counts
            m_cursor = self._conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'verified_complete' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status != 'verified_complete' THEN 1 ELSE 0 END) as pending
                FROM milestones
                """
            )
            m_agg = m_cursor.fetchone()
            completed_milestones = m_agg["completed"] or 0
            pending_milestones = m_agg["pending"] or 0

            # Discrepancies counts
            d_cursor = self._conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count,
                    SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as resolved_count
                FROM discrepancies
                """
            )
            d_agg = d_cursor.fetchone()
            open_discrepancies = d_agg["open_count"] or 0
            resolved_discrepancies = d_agg["resolved_count"] or 0

            # Breakdown by category
            c_cursor = self._conn.execute(
                """
                SELECT
                    category,
                    COUNT(*) as count,
                    COALESCE(SUM(allocated_amount_lakh), 0.0) as allocated,
                    COALESCE(SUM(committed_amount_lakh), 0.0) as committed,
                    COALESCE(SUM(disbursed_amount_lakh), 0.0) as disbursed
                FROM allocations
                GROUP BY category
                """
            )
            by_category: Dict[str, Dict[str, float]] = {}
            for r in c_cursor.fetchall():
                by_category[r["category"]] = {
                    "count": float(r["count"]),
                    "allocated_lakh": round(r["allocated"], 2),
                    "committed_lakh": round(r["committed"], 2),
                    "disbursed_lakh": round(r["disbursed"], 2),
                }

            # Breakdown by neighbourhood
            n_cursor = self._conn.execute(
                """
                SELECT
                    neighbourhood_id,
                    neighbourhood_name,
                    COUNT(*) as project_count,
                    COALESCE(SUM(allocated_amount_lakh), 0.0) as allocated_lakh,
                    COALESCE(SUM(disbursed_amount_lakh), 0.0) as disbursed_lakh
                FROM allocations
                GROUP BY neighbourhood_id, neighbourhood_name
                ORDER BY allocated_lakh DESC
                """
            )
            by_neighbourhood = [
                {
                    "neighbourhood_id": r["neighbourhood_id"],
                    "neighbourhood_name": r["neighbourhood_name"],
                    "project_count": r["project_count"],
                    "allocated_lakh": round(r["allocated_lakh"], 2),
                    "disbursed_lakh": round(r["disbursed_lakh"], 2),
                }
                for r in n_cursor.fetchall()
            ]

            return PublicAccountabilitySummary(
                fiscal_year="2025-2026",
                total_allocated_lakh=tot_allocated,
                total_committed_lakh=tot_committed,
                total_disbursed_lakh=tot_disbursed,
                total_remaining_lakh=tot_remaining,
                allocation_count=alloc_count,
                completed_milestones_count=completed_milestones,
                pending_milestones_count=pending_milestones,
                open_discrepancies_count=open_discrepancies,
                resolved_discrepancies_count=resolved_discrepancies,
                by_category=by_category,
                by_neighbourhood=by_neighbourhood,
            )

    # -----------------------------------------------------------------------
    # Demonstration Seed Data
    # -----------------------------------------------------------------------

    def _seed_initial_demonstration_data(self) -> None:
        """Seed realistic Bengaluru municipal sustainability allocations for demonstration."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) as c FROM allocations")
            if cursor.fetchone()["c"] > 0:
                return

            seed_allocations = [
                {
                    "title": "Koramangala Valley Stormwater Drain Desilting & Bioswales",
                    "neighbourhood_id": "NBR-001",
                    "neighbourhood_name": "Koramangala",
                    "intervention_id": "INT-DRAIN-01",
                    "intervention_name": "Engineered Bioswales & Silt Traps",
                    "category": "drainage",
                    "allocated_amount_lakh": 35.0,
                    "planned_units": 4,
                    "council_resolution_ref": "BBMP/CR/2025/ENV-042",
                    "vendor_id": "VND-BBMP-WORKS-01",
                    "vendor_name": "Bengaluru Urban Drainage & Infra Ltd",
                    "contract_ref": "CNT-2025-BLR-0114",
                    "committed_amount": 32.5,
                    "milestones": [
                        {
                            "title": "Site Survey, Bathymetry & Sediment Cleansing",
                            "desc": "Initial sediment profiling, boundary demarcations and heavy machinery mobilization.",
                            "tied_amt": 10.0,
                            "order": 1,
                            "progress": 100,
                            "status": MilestoneStatus.VERIFIED_COMPLETE,
                            "completed": True,
                        },
                        {
                            "title": "Bioswale Channel Shaping & Native Vetiver Planting",
                            "desc": "Grading channel edges to 3:1 slopes and planting vetiver roots for natural filtration.",
                            "tied_amt": 15.0,
                            "order": 2,
                            "progress": 100,
                            "status": MilestoneStatus.VERIFIED_COMPLETE,
                            "completed": True,
                        },
                        {
                            "title": "Perimeter Overflow Weir & Monitoring Telemetry Installation",
                            "desc": "Reinforced concrete overflow spillway and automated ultrasonic level sensors.",
                            "tied_amt": 7.5,
                            "order": 3,
                            "progress": 60,
                            "status": MilestoneStatus.IN_PROGRESS,
                            "completed": False,
                        },
                    ],
                    "disbursed_amount": 25.0,
                },
                {
                    "title": "Indiranagar 100ft Road Permeable Pavements & Rain Gardens",
                    "neighbourhood_id": "NBR-002",
                    "neighbourhood_name": "Indiranagar",
                    "intervention_id": "INT-RAIN-02",
                    "intervention_name": "Interlocking Permeable Concrete Pavement",
                    "category": "flooding_drainage",
                    "allocated_amount_lakh": 25.0,
                    "planned_units": 3,
                    "council_resolution_ref": "BBMP/CR/2025/ENV-049",
                    "vendor_id": "VND-ECO-INFRA-02",
                    "vendor_name": "GreenGrid Urban Solutions Pvt Ltd",
                    "contract_ref": "CNT-2025-BLR-0205",
                    "committed_amount": 24.0,
                    "milestones": [
                        {
                            "title": "Sub-base Excavation & Geotextile Membrane Laying",
                            "desc": "Excavation of 450mm base layer and placement of non-woven needle-punched geotextile.",
                            "tied_amt": 8.0,
                            "order": 1,
                            "progress": 100,
                            "status": MilestoneStatus.VERIFIED_COMPLETE,
                            "completed": True,
                        },
                        {
                            "title": "Permeable Paver Placement & Open-graded Infill",
                            "desc": "80mm heavy-duty porous interlocking blocks laid with clean aggregate infill.",
                            "tied_amt": 12.0,
                            "order": 2,
                            "progress": 75,
                            "status": MilestoneStatus.SUBMITTED_FOR_REVIEW,
                            "completed": False,
                        },
                    ],
                    "disbursed_amount": 8.0,
                },
                {
                    "title": "Whitefield IT Corridor Micro-Forest Canopy & Miyawaki Afforestation",
                    "neighbourhood_id": "NBR-004",
                    "neighbourhood_name": "Whitefield",
                    "intervention_id": "INT-TREE-01",
                    "intervention_name": "High-Density Miyawaki Urban Forest",
                    "category": "urban_forest",
                    "allocated_amount_lakh": 40.0,
                    "planned_units": 2,
                    "council_resolution_ref": "BBMP/CR/2025/ENV-055",
                    "vendor_id": "VND-AGRI-FOREST-03",
                    "vendor_name": "Karnataka Ecological Restoration Trust",
                    "contract_ref": "CNT-2025-BLR-0318",
                    "committed_amount": 38.0,
                    "milestones": [
                        {
                            "title": "Soil Conditioning & Organic Mulching (1.5m deep)",
                            "desc": "Enrichment with coir pith, dry bagasse, and microbial bio-fertilizers.",
                            "tied_amt": 12.0,
                            "order": 1,
                            "progress": 100,
                            "status": MilestoneStatus.VERIFIED_COMPLETE,
                            "completed": True,
                        },
                        {
                            "title": "Planting of 3,200 Native Canopy & Sub-Canopy Saplings",
                            "desc": "Neem, Honge, Jamun, Mahua and bamboo planted at 3 saplings per square meter.",
                            "tied_amt": 18.0,
                            "order": 2,
                            "progress": 30,
                            "status": MilestoneStatus.IN_PROGRESS,
                            "completed": False,
                        },
                    ],
                    "disbursed_amount": 12.0,
                },
            ]

            now = datetime.datetime.now(timezone.utc)
            now_iso = now.isoformat()

            for item in seed_allocations:
                alloc_id = f"ALC-{uuid.uuid4().hex[:8].upper()}"
                self._conn.execute(
                    """
                    INSERT INTO allocations (
                        allocation_id, title, neighbourhood_id, neighbourhood_name,
                        intervention_id, intervention_name, category, fiscal_year,
                        currency, allocated_amount_lakh, committed_amount_lakh,
                        disbursed_amount_lakh, planned_units, status, authorized_by,
                        council_resolution_ref, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alloc_id,
                        item["title"],
                        item["neighbourhood_id"],
                        item["neighbourhood_name"],
                        item["intervention_id"],
                        item["intervention_name"],
                        item["category"],
                        "2025-2026",
                        "INR",
                        item["allocated_amount_lakh"],
                        item["committed_amount"],
                        item["disbursed_amount"],
                        item["planned_units"],
                        AllocationStatus.IN_PROGRESS.value,
                        "MUNICIPAL_COMMISSIONER",
                        item["council_resolution_ref"],
                        now_iso,
                        now_iso,
                    ),
                )

                # Commitment
                cmt_id = f"CMT-{uuid.uuid4().hex[:8].upper()}"
                self._conn.execute(
                    """
                    INSERT INTO commitments (
                        commitment_id, allocation_id, vendor_id, vendor_name,
                        contract_reference, committed_amount_lakh, status, approved_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cmt_id,
                        alloc_id,
                        item["vendor_id"],
                        item["vendor_name"],
                        item["contract_ref"],
                        item["committed_amount"],
                        CommitmentStatus.ACTIVE.value,
                        "FINANCE_OFFICER_01",
                        now_iso,
                    ),
                )

                # Milestones
                for m in item["milestones"]:
                    mls_id = f"MLS-{uuid.uuid4().hex[:8].upper()}"
                    self._conn.execute(
                        """
                        INSERT INTO milestones (
                            milestone_id, allocation_id, title, description,
                            sequence_order, target_completion_date, status,
                            disbursement_tied_amount_lakh, percent_progress,
                            completed_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            mls_id,
                            alloc_id,
                            m["title"],
                            m["desc"],
                            m["order"],
                            "2026-03-31",
                            m["status"].value,
                            m["tied_amt"],
                            m["progress"],
                            now_iso if m["completed"] else None,
                            now_iso,
                            now_iso,
                        ),
                    )

                    # Add sample verified evidence for completed milestones
                    if m["completed"]:
                        evd_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
                        doc_hash = hashlib.sha256(f"evidence-{mls_id}".encode()).hexdigest()
                        self._conn.execute(
                            """
                            INSERT INTO evidence_metadata (
                                evidence_id, milestone_id, evidence_type, title, description,
                                file_name, mime_type, file_size_bytes, document_hash,
                                submitted_by, submitted_at, verification_status, verification_notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                evd_id,
                                mls_id,
                                EvidenceType.SITE_PHOTO.value,
                                f"Physical Completion Photo - {m['title']}",
                                "High-resolution geotagged site inspection photo confirming construction compliance.",
                                "inspection_photo_01.jpg",
                                "image/jpeg",
                                4200150,
                                doc_hash,
                                item["vendor_id"],
                                now_iso,
                                EvidenceVerificationStatus.VERIFIED.value,
                                "Verified by Superintending Engineer; meets CPWD environmental specifications.",
                            ),
                        )

                        # Verification decision
                        vdec_id = f"VDEC-{uuid.uuid4().hex[:8].upper()}"
                        self._conn.execute(
                            """
                            INSERT INTO verification_decisions (
                                decision_id, milestone_id, decision, verifier_id, verifier_name,
                                comments, decided_at, passed_inspection
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                vdec_id,
                                mls_id,
                                "approved",
                                "OFFICER_SE_01",
                                "Er. Rajeshwari Kumar (SE Environmental)",
                                "Independent physical verification completed. Dimensions, grade, and materials comply with approved design.",
                                now_iso,
                                1,
                            ),
                        )

                # Disbursements
                if item["disbursed_amount"] > 0:
                    dsb_id = f"DSB-{uuid.uuid4().hex[:8].upper()}"
                    self._conn.execute(
                        """
                        INSERT INTO disbursements (
                            disbursement_id, allocation_id, commitment_id, milestone_id,
                            amount_lakh, payment_reference, recipient_entity, status, approved_by, disbursed_at
                        ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            dsb_id,
                            alloc_id,
                            cmt_id,
                            item["disbursed_amount"],
                            f"NEFT-BBMP-2025-{uuid.uuid4().hex[:6].upper()}",
                            item["vendor_name"],
                            DisbursementStatus.COMPLETED.value,
                            "FINANCE_SECRETARY",
                            now_iso,
                        ),
                    )

                # Record creation audit event
                self._record_audit_event(
                    actor_id="MUNICIPAL_COMMISSIONER",
                    actor_role="administrator",
                    event_type=AuditEventType.ALLOCATION_CREATED,
                    entity_type="ALLOCATION",
                    entity_id=alloc_id,
                    summary=f"Initialized demonstration budget allocation ₹{item['allocated_amount_lakh']:.2f}L for {item['title']}.",
                )

            self._conn.commit()


_accountability_repo_instance: Optional[AccountabilityRepository] = None


def get_accountability_repository() -> AccountabilityRepository:
    """Dependency injection provider for the accountability repository backed by Supabase PostgreSQL."""
    global _accountability_repo_instance
    if _accountability_repo_instance is None:
        backend = os.getenv("DATABASE_BACKEND", "supabase").strip().lower()
        if backend == "supabase":
            from app.accountability.supabase_repo import SupabaseAccountabilityRepository
            _accountability_repo_instance = SupabaseAccountabilityRepository()
        else:
            db_path = os.getenv("DATABASE_PATH", os.getenv("ACCOUNTABILITY_DB_PATH", "urbansage.db"))
            _accountability_repo_instance = AccountabilityRepository(db_path=db_path, auto_seed=True)
    return _accountability_repo_instance


def reset_accountability_repository(db_path: str = ":memory:") -> AccountabilityRepository:
    """Reset repository instance for testing."""
    global _accountability_repo_instance
    if _accountability_repo_instance is not None:
        try:
            _accountability_repo_instance.close()
        except Exception:
            pass
    _accountability_repo_instance = AccountabilityRepository(db_path=db_path, auto_seed=False)
    return _accountability_repo_instance
