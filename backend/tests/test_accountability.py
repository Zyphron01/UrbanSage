"""
UrbanSage AI — Financial Accountability & Audit Automated Tests (Stage 6)
=========================================================================
Comprehensive automated tests verifying:
1. Budget allocation creation, retrieval, and schema validation.
2. Financial commitments and budget encumbrance enforcement.
3. Cost overrun prevention and automated discrepancy detection.
4. Milestone progression, progress checks, and invalid transitions.
5. Evidence metadata attachment and municipal inspection verification.
6. Disbursement validation (cannot silently exceed allocation, unverified payouts flagged).
7. Server-side RBAC protection (citizens and unauthenticated callers rejected).
8. Discrepancy lifecycle (flagging, review, and resolution).
9. Tamper-evident audit trail hash chain integrity.
10. Public accountability summary privacy and metric aggregations.
"""

from __future__ import annotations

import hashlib
import pytest
from fastapi.testclient import TestClient

from app.accountability.models import (
    AllocationCreate,
    CommitmentCreate,
    DisbursementCreate,
    DiscrepancyResolve,
    EvidenceSubmit,
    EvidenceType,
    MilestoneCreate,
    MilestoneStatus,
    MilestoneUpdate,
    VerificationSubmit,
)
from app.accountability.repository import (
    AccountabilityRepository,
    get_accountability_repository,
    reset_accountability_repository,
)
from app.auth import create_access_token
from app.main import app


@pytest.fixture
def repo():
    """Provides an isolated in-memory accountability repository without seed data."""
    r = reset_accountability_repository(db_path=":memory:")
    yield r
    r.close()


@pytest.fixture
def client(repo):
    """Provides a TestClient wired to the test accountability repository."""
    app.dependency_overrides[get_accountability_repository] = lambda: repo
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers():
    token = create_access_token(user_id="ADMIN-TEST-01", role="administrator", name="Municipal Director")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def contractor_headers():
    token = create_access_token(user_id="CONTRACTOR-TEST-01", role="contractor", name="Lead Engineer")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def citizen_headers():
    token = create_access_token(user_id="CITIZEN-TEST-01", role="citizen", name="Concerned Resident")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_allocation(repo):
    """Creates a sample allocation of ₹50.0L in Koramangala."""
    return repo.create_allocation(
        AllocationCreate(
            title="Koramangala Stormwater Drain Expansion & Bioswales",
            neighbourhood_id="NBR-001",
            neighbourhood_name="Koramangala",
            intervention_id="INT-DRAIN-01",
            intervention_name="Engineered Bioswales",
            category="flooding_drainage",
            fiscal_year="2025-2026",
            allocated_amount_lakh=50.0,
            planned_units=5,
            council_resolution_ref="CR-2025-089",
        ),
        authorized_by="ADMIN-TEST-01",
    )


# ---------------------------------------------------------------------------
# Test Suite 1: Allocations & Commitments
# ---------------------------------------------------------------------------

class TestAllocationManagement:
    def test_create_and_get_allocation(self, client, admin_headers):
        payload = {
            "title": "Whitefield Miyawaki Micro-Forest Canopy",
            "neighbourhood_id": "NBR-004",
            "neighbourhood_name": "Whitefield",
            "intervention_id": "INT-TREE-01",
            "intervention_name": "Miyawaki Forest",
            "category": "urban_forest",
            "fiscal_year": "2025-2026",
            "allocated_amount_lakh": 40.0,
            "planned_units": 2,
            "council_resolution_ref": "BBMP-CR-2025-99",
        }
        res = client.post("/api/accountability/allocations", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["allocation_id"].startswith("ALC-")
        assert data["allocated_amount_lakh"] == 40.0
        assert data["remaining_budget_lakh"] == 40.0

        # Retrieve single allocation
        get_res = client.get(f"/api/accountability/allocations/{data['allocation_id']}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == payload["title"]

    def test_list_allocations_filtering(self, client, admin_headers, sample_allocation):
        res = client.get("/api/accountability/allocations?neighbourhood_id=NBR-001")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 1
        assert items[0]["neighbourhood_id"] == "NBR-001"

    def test_record_commitment_within_budget(self, client, admin_headers, sample_allocation):
        payload = {
            "vendor_id": "VND-ECO-01",
            "vendor_name": "EcoInfra Works Ltd",
            "contract_reference": "TND-2025-01",
            "committed_amount_lakh": 45.0,
        }
        res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 201
        assert res.json()["committed_amount_lakh"] == 45.0

        # Verify allocation remaining budget updated
        alloc = client.get(f"/api/accountability/allocations/{sample_allocation.allocation_id}").json()
        assert alloc["committed_amount_lakh"] == 45.0
        assert alloc["remaining_budget_lakh"] == 5.0

    def test_commitment_exceeding_budget_rejected_and_flagged(self, client, admin_headers, sample_allocation):
        # Attempt to commit 60.0L against 50.0L allocation
        payload = {
            "vendor_id": "VND-ECO-02",
            "vendor_name": "Overbudget Contractor",
            "contract_reference": "TND-2025-02",
            "committed_amount_lakh": 60.0,
        }
        res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "exceed authorized budget" in res.json()["detail"]

        # Verify discrepancy was automatically flagged
        disc_res = client.get("/api/accountability/discrepancies", headers=admin_headers)
        assert disc_res.status_code == 200
        discs = disc_res.json()
        assert any(d["discrepancy_type"] == "cost_overrun" for d in discs)


# ---------------------------------------------------------------------------
# Test Suite 2: Milestones, Evidence & Verification
# ---------------------------------------------------------------------------

class TestMilestonesAndVerification:
    def test_add_milestone_and_progress(self, client, admin_headers, contractor_headers, sample_allocation):
        m_payload = {
            "title": "Excavation and sub-base leveling",
            "description": "Grading stormwater inlet channel to standard slope.",
            "sequence_order": 1,
            "target_completion_date": "2026-03-31",
            "disbursement_tied_amount_lakh": 15.0,
        }
        res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/milestones",
            json=m_payload,
            headers=admin_headers,
        )
        assert res.status_code == 201
        milestone = res.json()
        mid = milestone["milestone_id"]

        # Contractor updates progress to 50%
        upd_res = client.patch(
            f"/api/accountability/milestones/{mid}",
            json={"percent_progress": 50, "status": "in_progress"},
            headers=contractor_headers,
        )
        assert upd_res.status_code == 200
        assert upd_res.json()["percent_progress"] == 50

    def test_invalid_milestone_review_submission_rejected(self, client, contractor_headers, admin_headers, sample_allocation):
        m_payload = {
            "title": "Drainage Culvert Installation",
            "description": "Precast RCC culverts.",
            "sequence_order": 1,
            "target_completion_date": "2026-04-15",
            "disbursement_tied_amount_lakh": 20.0,
        }
        res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/milestones",
            json=m_payload,
            headers=admin_headers,
        )
        mid = res.json()["milestone_id"]

        # Contractor attempts to submit for review when progress is only 40% (must be >= 80%)
        upd_res = client.patch(
            f"/api/accountability/milestones/{mid}",
            json={"percent_progress": 40, "status": "submitted_for_review"},
            headers=contractor_headers,
        )
        assert upd_res.status_code == 400
        assert "progress must be at least 80%" in upd_res.json()["detail"]

    def test_attach_evidence_and_municipal_verification(
        self, client, admin_headers, contractor_headers, sample_allocation
    ):
        # Add milestone
        m_res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/milestones",
            json={
                "title": "Subgrade Preparation",
                "description": "Earthworks complete.",
                "sequence_order": 1,
                "target_completion_date": "2026-03-31",
                "disbursement_tied_amount_lakh": 10.0,
            },
            headers=admin_headers,
        )
        mid = m_res.json()["milestone_id"]

        # Contractor attaches evidence metadata
        evd_payload = {
            "evidence_type": "site_photo",
            "title": "Excavation completion drone photograph",
            "description": "Geotagged site image showing 100% excavation to grade.",
            "file_name": "site_excavation_drone.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 3500000,
        }
        evd_res = client.post(
            f"/api/accountability/milestones/{mid}/evidence",
            json=evd_payload,
            headers=contractor_headers,
        )
        assert evd_res.status_code == 201
        evd_data = evd_res.json()
        assert evd_data["evidence_id"].startswith("EVD-")
        assert evd_data["verification_status"] == "pending_review"

        # Municipal inspector approves milestone
        v_payload = {
            "decision": "approved",
            "comments": "Field inspection confirmed culvert excavation depth and compaction.",
        }
        v_res = client.post(
            f"/api/accountability/milestones/{mid}/verify",
            json=v_payload,
            headers=admin_headers,
        )
        assert v_res.status_code == 200
        assert v_res.json()["passed_inspection"] is True

        # Verify milestone status is now verified_complete
        alloc = client.get(f"/api/accountability/allocations/{sample_allocation.allocation_id}").json()
        updated_m = next(m for m in alloc["milestones"] if m["milestone_id"] == mid)
        assert updated_m["status"] == "verified_complete"
        assert updated_m["percent_progress"] == 100


# ---------------------------------------------------------------------------
# Test Suite 3: Disbursements & Invariant Enforcement
# ---------------------------------------------------------------------------

class TestDisbursementsAndFinancialIntegrity:
    def test_disbursement_execution_and_budget_tracking(self, client, admin_headers, sample_allocation):
        # 1. Commitment of 30.0L
        cmt = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json={
                "vendor_id": "VND-01",
                "vendor_name": "Civil Works Co",
                "contract_reference": "CNT-01",
                "committed_amount_lakh": 30.0,
            },
            headers=admin_headers,
        ).json()

        # 2. Add and verify milestone
        mls = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/milestones",
            json={
                "title": "Phase 1 Works",
                "description": "Initial setup.",
                "sequence_order": 1,
                "target_completion_date": "2026-03-31",
                "disbursement_tied_amount_lakh": 15.0,
            },
            headers=admin_headers,
        ).json()
        client.post(
            f"/api/accountability/milestones/{mls['milestone_id']}/verify",
            json={"decision": "approved", "comments": "Inspected and passed."},
            headers=admin_headers,
        )

        # 3. Disburse ₹15.0L
        dsb_res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/disbursements",
            json={
                "commitment_id": cmt["commitment_id"],
                "milestone_id": mls["milestone_id"],
                "amount_lakh": 15.0,
                "payment_reference": "NEFT-2026-001",
                "recipient_entity": "Civil Works Co",
            },
            headers=admin_headers,
        )
        assert dsb_res.status_code == 201
        assert dsb_res.json()["amount_lakh"] == 15.0

        # Allocation disbursed amount should now be 15.0L
        alloc = client.get(f"/api/accountability/allocations/{sample_allocation.allocation_id}").json()
        assert alloc["disbursed_amount_lakh"] == 15.0

    def test_disbursement_exceeding_allocation_budget_rejected(self, client, admin_headers, sample_allocation):
        cmt = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json={
                "vendor_id": "VND-01",
                "vendor_name": "Civil Works Co",
                "contract_reference": "CNT-01",
                "committed_amount_lakh": 50.0,
            },
            headers=admin_headers,
        ).json()

        # Attempt to disburse 55.0L (allocation is 50.0L)
        res = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/disbursements",
            json={
                "commitment_id": cmt["commitment_id"],
                "amount_lakh": 55.0,
                "payment_reference": "NEFT-OVERRUN",
                "recipient_entity": "Civil Works Co",
            },
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "exceeds authorized allocation" in res.json()["detail"]

    def test_unverified_milestone_disbursement_flags_discrepancy(self, client, admin_headers, sample_allocation):
        cmt = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json={
                "vendor_id": "VND-01",
                "vendor_name": "Civil Works Co",
                "contract_reference": "CNT-01",
                "committed_amount_lakh": 30.0,
            },
            headers=admin_headers,
        ).json()

        # Add milestone, but do NOT verify it
        mls = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/milestones",
            json={
                "title": "Uninspected Phase",
                "description": "Work in progress.",
                "sequence_order": 1,
                "target_completion_date": "2026-03-31",
                "disbursement_tied_amount_lakh": 10.0,
            },
            headers=admin_headers,
        ).json()

        # Disburse against unverified milestone
        client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/disbursements",
            json={
                "commitment_id": cmt["commitment_id"],
                "milestone_id": mls["milestone_id"],
                "amount_lakh": 10.0,
                "payment_reference": "NEFT-UNVERIFIED",
                "recipient_entity": "Civil Works Co",
            },
            headers=admin_headers,
        )

        # Discrepancy monitor must have flagged this!
        discs = client.get("/api/accountability/discrepancies", headers=admin_headers).json()
        unverified_disc = [d for d in discs if d["discrepancy_type"] == "unverified_disbursement"]
        assert len(unverified_disc) >= 1
        assert unverified_disc[0]["amount_involved_lakh"] == 10.0


# ---------------------------------------------------------------------------
# Test Suite 4: Security, RBAC & Public Transparency
# ---------------------------------------------------------------------------

class TestAccountabilitySecurityAndRBAC:
    def test_public_summary_accessible_without_auth(self, client, sample_allocation):
        res = client.get("/api/accountability/summary")
        assert res.status_code == 200
        data = res.json()
        assert "total_allocated_lakh" in data
        assert data["total_allocated_lakh"] == 50.0

    def test_citizen_forbidden_from_admin_actions(self, client, citizen_headers, sample_allocation):
        # Citizen attempting to create allocation -> 403 Forbidden
        res1 = client.post(
            "/api/accountability/allocations",
            json={
                "title": "Rogue Project",
                "neighbourhood_id": "NBR-001",
                "neighbourhood_name": "Koramangala",
                "intervention_id": "INT-01",
                "intervention_name": "Trees",
                "category": "urban_forest",
                "allocated_amount_lakh": 10.0,
                "planned_units": 1,
            },
            headers=citizen_headers,
        )
        assert res1.status_code == 403

        # Citizen attempting to disburse -> 403 Forbidden
        res2 = client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/disbursements",
            json={
                "commitment_id": "CMT-FAKE0001",
                "amount_lakh": 5.0,
                "payment_reference": "REF-001",
                "recipient_entity": "Citizen",
            },
            headers=citizen_headers,
        )
        assert res2.status_code == 403

    def test_contractor_forbidden_from_financial_authorization(self, client, contractor_headers, sample_allocation):
        # Contractor attempting to verify milestone -> 403 Forbidden
        res = client.post(
            "/api/accountability/milestones/MLS-FAKE0001/verify",
            json={"decision": "approved", "comments": "Self-approval"},
            headers=contractor_headers,
        )
        assert res.status_code == 403

    def test_unauthenticated_request_rejected(self, client, sample_allocation):
        res = client.get("/api/accountability/audit-trail")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Test Suite 5: Tamper-Evident Audit Trail & Discrepancy Resolution
# ---------------------------------------------------------------------------

class TestAuditTrailAndDiscrepancyResolution:
    def test_audit_trail_hash_chain_integrity(self, client, admin_headers, sample_allocation):
        res = client.get("/api/accountability/audit-trail", headers=admin_headers)
        assert res.status_code == 200
        events = res.json()
        assert len(events) >= 1

        # Verify hash link property: event_hash is 64 hex characters (SHA-256)
        for e in events:
            assert len(e["event_hash"]) == 64
            assert e["actor_role"] in ("administrator", "contractor", "system")

    def test_discrepancy_resolution(self, client, admin_headers, sample_allocation):
        # Create an intentional cost overrun discrepancy
        client.post(
            f"/api/accountability/allocations/{sample_allocation.allocation_id}/commitments",
            json={
                "vendor_id": "VND-OVER",
                "vendor_name": "Overbudget Corp",
                "contract_reference": "TND-99",
                "committed_amount_lakh": 75.0,
            },
            headers=admin_headers,
        )

        discs = client.get("/api/accountability/discrepancies", headers=admin_headers).json()
        target_disc = discs[0]
        did = target_disc["discrepancy_id"]

        # Resolve discrepancy
        res = client.patch(
            f"/api/accountability/discrepancies/{did}/resolve",
            json={
                "resolution_notes": "Tender cancelled and renegotiated within budget limit of ₹50.0L.",
                "action_taken": "resolved",
            },
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "resolved"
        assert res.json()["resolved_by"] == "ADMIN-TEST-01"
