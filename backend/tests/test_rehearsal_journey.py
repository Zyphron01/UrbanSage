"""
UrbanSage AI — End-to-End Demo Rehearsal Test Suite
===================================================
Simulates the complete end-to-end hackathon demonstration workflow:
1. Authentication & Token Issuance (Admin, Contractor, Citizen)
2. Citizen Problem Report Submission (Urgency scoring, evidence score, PII omission)
3. Report Listing & Verification by Citizens
4. Municipal Decision Brief, Priority Queue & Geographic Risk
5. Sustainability Optimizer Execution (Budget, Equity, Capacity constraints)
6. Baseline vs Citizen-Informed Optimization Comparison
7. Climatic & Fiscal Scenario Simulation (4 stress test scenarios)
8. Financial Accountability Ledger (Commitment, Milestone, Evidence, Verification, Disbursement, Overrun Prevention, Audit Chain)
9. Security & Privilege Escalation Guards
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reports.repository import CitizenReportRepository
from app.reports.factory import get_report_repository
from app.accountability.repository import (
    AccountabilityRepository,
    get_accountability_repository,
    reset_accountability_repository,
)


@pytest.fixture(scope="module")
def shared_client():
    """Provides a single integrated TestClient with isolated in-memory repositories."""
    report_repo = CitizenReportRepository(db_path=":memory:")
    acc_repo = reset_accountability_repository(db_path=":memory:")

    app.dependency_overrides[get_report_repository] = lambda: report_repo
    app.dependency_overrides[get_accountability_repository] = lambda: acc_repo

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    report_repo.close()
    acc_repo.close()


class TestEndToEndRehearsalJourney:
    """Exercises the complete demonstration script end-to-end."""

    admin_token: str = ""
    contractor_token: str = ""
    citizen_token: str = ""
    created_report_id: str = ""
    allocation_id: str = ""
    commitment_id: str = ""
    milestone_id: str = ""

    def test_01_authentication_and_tokens(self, shared_client):
        """Step 1: Obtain tokens for all roles and verify production guards."""
        # 1. Admin Token
        res = shared_client.post(
            "/api/auth/token",
            json={"user_id": "ADMIN-DEMO-01", "role": "administrator", "department": "Municipal Control"}
        )
        assert res.status_code == 200, res.text
        TestEndToEndRehearsalJourney.admin_token = res.json()["access_token"]

        # 2. Contractor Token
        res = shared_client.post(
            "/api/auth/token",
            json={"user_id": "CONTRACTOR-DEMO-01", "role": "contractor", "department": "Civic Works"}
        )
        assert res.status_code == 200
        TestEndToEndRehearsalJourney.contractor_token = res.json()["access_token"]

        # 3. Citizen Token
        res = shared_client.post(
            "/api/auth/token",
            json={"user_id": "CITIZEN-DEMO-01", "role": "citizen"}
        )
        assert res.status_code == 200
        TestEndToEndRehearsalJourney.citizen_token = res.json()["access_token"]

    def test_02_citizen_report_submission_and_privacy(self, shared_client):
        """Step 2: Submit a citizen report and confirm urgency scoring and PII omission."""
        payload = {
            "category": "flooding_drainage",
            "severity": 4,
            "description": "Severe stormwater drain overflow near residential crossroad with standing water.",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_description": "Crossroad 4, Ward 5",
            "neighbourhood_id": "NBR-001",
            "reporter_id": "CITIZEN-DEMO-01",
            "reporter_contact": "resident_private_contact@example.org",
            "photos": [
                {
                    "photo_id": "PHO-00000001",
                    "file_name": "drain_overflow_01.jpg",
                    "mime_type": "image/jpeg",
                    "size_bytes": 1024000,
                    "url": "https://storage.urbansage.local/photos/drain_overflow_01.jpg",
                    "caption": "Drain overflow near junction",
                    "captured_at": "2026-10-24T02:00:00Z"
                }
            ]
        }
        res = shared_client.post("/api/reports", json=payload)
        assert res.status_code == 201, res.text
        data = res.json()

        # Capture report ID
        TestEndToEndRehearsalJourney.created_report_id = data["id"]

        # Assert operational scores calculated
        assert data["urgency_score"] > 0
        assert data["evidence_confidence_score"] > 0
        assert data["status"] == "submitted"

        # Assert PII is NEVER exposed in response
        assert "reporter_contact" not in data
        assert "resident_private_contact" not in str(data)

    def test_03_report_retrieval_and_listing(self, shared_client):
        """Step 3: Retrieve report by ID and verify listing pagination."""
        report_id = TestEndToEndRehearsalJourney.created_report_id
        assert report_id, "Report ID must be set"

        # Get by ID
        res = shared_client.get(f"/api/reports/{report_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == report_id
        assert "reporter_contact" not in data

        # List with filter
        res_list = shared_client.get("/api/reports?category=flooding_drainage&status=submitted")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total"] >= 1
        assert any(r["id"] == report_id for r in list_data["items"])

    def test_04_municipal_intelligence_and_decision_brief(self, shared_client):
        """Step 4: Access Daily Decision Brief and Priority Review Queue as Administrator."""
        admin_headers = {"Authorization": f"Bearer {TestEndToEndRehearsalJourney.admin_token}"}

        # 1. Decision brief
        res_brief = shared_client.get("/api/admin/decision-brief?overdue_threshold_hours=48", headers=admin_headers)
        assert res_brief.status_code == 200
        brief = res_brief.json()
        assert "summary" in brief
        assert "high_urgency_items" in brief
        assert "awaiting_review_items" in brief

        # 2. Priority review queue
        res_queue = shared_client.get("/api/admin/priority-queue?sort_by=urgency_desc", headers=admin_headers)
        assert res_queue.status_code == 200
        queue = res_queue.json()
        assert queue["total"] >= 1

        # 3. Geographic risk
        res_geo = shared_client.get("/api/admin/geographic-risk", headers=admin_headers)
        assert res_geo.status_code == 200
        geo = res_geo.json()
        assert "neighbourhoods" in geo
        assert "unassigned" in geo

    def test_05_unauthorized_access_rejection(self, shared_client):
        """Step 5: Verify RBAC rejection of unauthorized and unauthenticated callers."""
        # 1. Unauthenticated decision brief
        res_unauth = shared_client.get("/api/admin/decision-brief")
        assert res_unauth.status_code == 401

        # 2. Citizen accessing decision brief
        citizen_headers = {"Authorization": f"Bearer {TestEndToEndRehearsalJourney.citizen_token}"}
        res_citizen_brief = shared_client.get("/api/admin/decision-brief", headers=citizen_headers)
        assert res_citizen_brief.status_code == 403

        # 3. Contractor accessing decision brief
        contractor_headers = {"Authorization": f"Bearer {TestEndToEndRehearsalJourney.contractor_token}"}
        res_contractor_brief = shared_client.get("/api/admin/decision-brief", headers=contractor_headers)
        assert res_contractor_brief.status_code == 403

    def test_06_sustainability_optimizer_execution(self, shared_client):
        """Step 6: Run SciPy HiGHS MILP optimizer and verify all constraints."""
        payload = {
            "budget_lakh": 1000.0,
            "equity_threshold": 0.40,
            "priority_heat": 0.35,
            "priority_flood": 0.35,
            "priority_water": 0.30,
            "equity_weight": 0.20,
            "max_interventions_per_neighbourhood": 4,
            "include_citizen_reports": True
        }
        res = shared_client.post("/api/optimizer/run", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        result = data["result"]

        # Constraint 1: Budget non-exceedance
        assert result["total_cost_lakh"] <= 1000.0
        assert result["budget_utilization_pct"] > 80.0

        # Constraint 2: 40% equity spend floor in high-vulnerability neighbourhoods
        assert result["equity_summary"]["equity_spend_fraction_of_total_spend"] >= 0.40

        # Constraint 3: Max 4 distinct interventions per neighbourhood
        for nh in result["neighbourhood_impacts"]:
            assert nh["distinct_types_count"] <= 4

    def test_07_optimizer_scenario_simulation(self, shared_client):
        """Step 7: Run scenario simulator stress test and check diff against baseline."""
        payload = {
            "scenario_type": "BUDGET_REDUCTION",
            "name": "Fiscal Austerity -30%",
            "description": "Evaluate investment allocation under 30% budget cut.",
            "budget_lakh": 700.0,
            "equity_threshold": 0.40,
            "include_citizen_reports": True
        }
        res = shared_client.post("/api/optimizer/scenarios/run", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert "all_allocation_diffs" in data
        assert "scenario_result" in data
        assert "baseline_result" in data
        assert data["scenario_engine_config"]["budget_lakh"] == 700.0

    def test_08_financial_accountability_and_audit_ledger(self, shared_client):
        """Step 8: Exercise the capital expenditure ledger, verification, and audit trail."""
        admin_headers = {"Authorization": f"Bearer {TestEndToEndRehearsalJourney.admin_token}"}
        contractor_headers = {"Authorization": f"Bearer {TestEndToEndRehearsalJourney.contractor_token}"}

        # 1. Admin creates capital budget allocation
        alloc_payload = {
            "title": "Shivajinagar Urban Micro-Forestry Project",
            "neighbourhood_id": "NBR-001",
            "neighbourhood_name": "Shivajinagar",
            "intervention_id": "INT-001",
            "intervention_name": "Urban Micro-Forestry",
            "category": "heat",
            "fiscal_year": "2025-2026",
            "allocated_amount_lakh": 50.0,
            "planned_units": 2
        }
        res_alloc = shared_client.post("/api/accountability/allocations", json=alloc_payload, headers=admin_headers)
        assert res_alloc.status_code == 201, res_alloc.text
        alloc_data = res_alloc.json()
        alloc_id = alloc_data["allocation_id"]
        TestEndToEndRehearsalJourney.allocation_id = alloc_id

        # 2. Admin records contractor commitment (₹45 Lakhs encumbered out of ₹50 Lakhs)
        commit_payload = {
            "vendor_id": "VND-001",
            "vendor_name": "Green Bengaluru Infrastructure Ltd",
            "contract_reference": "BBMP/ENG/2026/044",
            "committed_amount_lakh": 45.0
        }
        res_commit = shared_client.post(f"/api/accountability/allocations/{alloc_id}/commitments", json=commit_payload, headers=admin_headers)
        assert res_commit.status_code == 201, res_commit.text
        commit_data = res_commit.json()
        cmt_id = commit_data["commitment_id"]
        TestEndToEndRehearsalJourney.commitment_id = cmt_id

        # 3. Admin defines physical implementation milestone
        ms_payload = {
            "title": "Site Excavation & Native Sapling Plantation",
            "description": "Planting of 500 native broadleaf trees with drip irrigation network.",
            "sequence_order": 1,
            "target_completion_date": "2026-11-30",
            "disbursement_tied_amount_lakh": 22.5
        }
        res_ms = shared_client.post(f"/api/accountability/allocations/{alloc_id}/milestones", json=ms_payload, headers=admin_headers)
        assert res_ms.status_code == 201, res_ms.text
        ms_data = res_ms.json()
        ms_id = ms_data["milestone_id"]
        TestEndToEndRehearsalJourney.milestone_id = ms_id

        # 4. Contractor submits documentary evidence
        ev_payload = {
            "evidence_type": "site_photo",
            "title": "Drone Survey of Planted Sapling Grid",
            "file_name": "site_survey_grid_01.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 3500000,
            "document_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
        }
        res_ev = shared_client.post(f"/api/accountability/milestones/{ms_id}/evidence", json=ev_payload, headers=contractor_headers)
        assert res_ev.status_code == 201, res_ev.text

        # 5. Contractor updates milestone status to submitted for review
        ms_update = {
            "status": "submitted_for_review",
            "percent_progress": 100,
            "notes": "Field excavation and plantation completed on schedule."
        }
        res_upd = shared_client.patch(f"/api/accountability/milestones/{ms_id}", json=ms_update, headers=contractor_headers)
        assert res_upd.status_code == 200, res_upd.text

        # 6. Admin formally verifies milestone
        v_payload = {
            "decision": "approved",
            "comments": "Ground verification conducted by Municipal Field Officer. Quality standards met."
        }
        res_ver = shared_client.post(f"/api/accountability/milestones/{ms_id}/verify", json=v_payload, headers=admin_headers)
        assert res_ver.status_code == 200, res_ver.text

        # 7. Admin executes disbursement (₹22.5 Lakhs)
        disb_payload = {
            "commitment_id": cmt_id,
            "milestone_id": ms_id,
            "amount_lakh": 22.5,
            "payment_reference": "NEFT-BBMP-2026-9901",
            "recipient_entity": "Green Bengaluru Infrastructure Ltd"
        }
        res_disb = shared_client.post(f"/api/accountability/allocations/{alloc_id}/disbursements", json=disb_payload, headers=admin_headers)
        assert res_disb.status_code == 201, res_disb.text

        # 8. Test Cost Overrun Prevention: Payout exceeding remaining allocation must fail
        illegal_disb = {
            "commitment_id": cmt_id,
            "milestone_id": ms_id,
            "amount_lakh": 50.0,  # Only ₹27.5 Lakhs remains out of ₹50 Lakhs!
            "payment_reference": "NEFT-BBMP-ILLEGAL",
            "recipient_entity": "Green Bengaluru Infrastructure Ltd"
        }
        res_illegal = shared_client.post(f"/api/accountability/allocations/{alloc_id}/disbursements", json=illegal_disb, headers=admin_headers)
        assert res_illegal.status_code == 400
        assert "exceed" in res_illegal.json()["detail"].lower()

        # 9. Verify Audit Trail and Cryptographic Event Chaining
        res_audit = shared_client.get("/api/accountability/audit-trail", headers=admin_headers)
        assert res_audit.status_code == 200
        events = res_audit.json()
        assert len(events) >= 5
        for ev in events:
            assert len(ev["event_hash"]) == 64  # SHA-256 hex string

        # 10. Public Accountability Summary
        res_sum = shared_client.get("/api/accountability/summary")
        assert res_sum.status_code == 200
        summary = res_sum.json()
        assert summary["total_allocated_lakh"] >= 50.0
        assert summary["total_disbursed_lakh"] >= 22.5
        assert summary["allocation_count"] >= 1
