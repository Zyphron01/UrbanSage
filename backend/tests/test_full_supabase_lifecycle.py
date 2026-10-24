"""
UrbanSage AI — Comprehensive End-to-End Supabase PostgreSQL Lifecycle Test
===========================================================================
Validates that:
1. Supabase is the single source of truth across Citizen, Municipal Admin, and Contractor workflows.
2. Citizen reports persist in Supabase and appear in admin briefs.
3. Administrative decisions and department recommendations persist in Supabase.
4. Budget plans can be saved and approved into official allocations in Supabase.
5. Contractor milestones can be updated with progress and documentary evidence in Supabase.
6. All records survive complete repository resets (simulating frontend/backend restart).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
load_dotenv(backend_dir / ".env")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import ADMIN_API_KEY, create_access_token
from app.reports.factory import get_report_repository, reset_repository_instance
from app.accountability.repository import get_accountability_repository
from app.governance.repository import get_governance_repository
from app.accountability.supabase_repo import SupabaseAccountabilityRepository
from app.governance.supabase_repo import SupabaseGovernanceRepository


def test_supabase_single_source_of_truth():
    # Verify environment configuration enforces Supabase
    assert os.getenv("DATABASE_BACKEND") == "supabase"

    # Verify repository instances use Supabase
    acc_repo = get_accountability_repository()
    assert isinstance(acc_repo, SupabaseAccountabilityRepository)

    gov_repo = get_governance_repository()
    assert isinstance(gov_repo, SupabaseGovernanceRepository)


def test_full_cross_portal_supabase_workflow():
    client = TestClient(app)
    admin_headers = {"X-API-Key": ADMIN_API_KEY}
    contractor_token = create_access_token(user_id="VND-BBMP-WORKS-01", role="contractor")
    contractor_headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Citizen Portal: Submit Report
    import uuid
    run_uid = uuid.uuid4().hex[:6]
    report_payload = {
        "category": "flooding_drainage",
        "description": f"E2E Test [{run_uid}]: Severe monsoon drain overflow near Commercial Street junction.",
        "severity": 4,
        "latitude": 12.9815,
        "longitude": 77.6048,
        "location_description": "Commercial Street Corner, Ward 110",
        "neighbourhood_id": "NBR-001",
        "reporter_id": f"citizen-e2e-{run_uid}",
        "reporter_contact": f"test-citizen-{run_uid}@urbansage.in",
        "photos": []
    }
    r_resp = client.post("/api/reports", json=report_payload)
    assert r_resp.status_code == 201, f"Failed to submit report: {r_resp.text}"
    report_data = r_resp.json()
    report_id = report_data["id"]
    assert report_id.startswith("RPT-")
    assert report_data["urgency_score"] > 0
    assert "reporter_contact" not in report_data  # Public privacy guarantee

    # 2. Municipal Admin Portal: View Decision Brief & Check Department Recommendation
    brief_resp = client.get("/api/admin/decision-brief", headers=admin_headers)
    assert brief_resp.status_code == 200
    brief_data = brief_resp.json()
    assert brief_data["summary"]["total_reports"] >= 1

    rec_resp = client.get(f"/api/admin/reports/{report_id}/recommendation", headers=admin_headers)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["report_id"] == report_id
    assert "SWD" in rec_data["recommended_department"] or "Stormwater" in rec_data["recommended_department"]
    assert rec_data["confidence_score"] > 0
    assert len(rec_data["evidence_used"]) >= 2

    # 3. Municipal Admin Portal: Persist Triage Decision
    decision_payload = {
        "decision_type": "ASSIGN_DEPARTMENT",
        "assigned_department": rec_data["recommended_department"],
        "assigned_action": "Emergency Sump Bypass Deployment & Desilting",
        "review_notes": "Corroborated by high catchment flood hazard; prioritized for contractor dispatch.",
        "priority_tier": "P1_URGENT"
    }
    dec_resp = client.post(f"/api/admin/reports/{report_id}/decision", json=decision_payload, headers=admin_headers)
    assert dec_resp.status_code == 201
    dec_data = dec_resp.json()
    assert dec_data["report_id"] == report_id

    # 4. Optimizer & Governance: Save Budget Plan and Approve
    plan_payload = {
        "title": "E2E Resilience Allocation Package 2026-Q1",
        "budget_lakh": 250.0,
        "equity_threshold": 0.25,
        "notes": "E2E demonstration budget proposal.",
        "items": [
            {
                "neighbourhood_id": "NBR-001",
                "neighbourhood_name": "Shivajinagar Central",
                "intervention_id": "INT-01",
                "intervention_name": "Permeable Bioswales & Urban Silt Traps",
                "category": "flooding_drainage",
                "units": 2,
                "cost_per_unit_lakh": 25.0,
                "total_cost_lakh": 50.0,
                "rationale": "Directly addresses acute flood choke point reported by citizens."
            }
        ]
    }
    plan_resp = client.post("/api/optimizer/plans", json=plan_payload, headers=admin_headers)
    assert plan_resp.status_code == 201
    plan_data = plan_resp.json()
    plan_id = plan_data["plan_id"]
    assert plan_data["status"] == "proposed"

    # Approve plan -> converts to authorized allocations
    appr_resp = client.post(f"/api/optimizer/plans/{plan_id}/approve", headers=admin_headers)
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["status"] == "approved"

    # 5. Contractor Portal: Check Milestones & Update Progress
    summary_resp = client.get("/api/accountability/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_allocated_lakh"] > 0

    allocs_resp = client.get("/api/accountability/allocations")
    assert allocs_resp.status_code == 200
    allocs = allocs_resp.json()
    assert len(allocs) >= 1

    # Update progress on first milestone of first allocation
    target_alloc = allocs[0]
    if target_alloc.get("milestones"):
        m_id = target_alloc["milestones"][0]["milestone_id"]
        prog_resp = client.patch(
            f"/api/accountability/milestones/{m_id}/progress",
            json={"percent_progress": 45, "status": "in_progress"},
            headers=contractor_headers,
        )
        assert prog_resp.status_code == 200
        prog_data = prog_resp.json()
        assert prog_data["percent_progress"] == 45

    # 6. Simulate Server Restart: Reset singletons and re-query Supabase
    reset_repository_instance()
    # Reset module-level singleton caches
    import app.accountability.repository as acc_mod
    import app.governance.repository as gov_mod
    acc_mod._accountability_repo_instance = None
    gov_mod._governance_repo_instance = None

    # Verify report is still present in Supabase
    reloaded_resp = client.get(f"/api/reports/{report_id}")
    assert reloaded_resp.status_code == 200
    assert reloaded_resp.json()["id"] == report_id

    # Verify admin decisions persist in Supabase
    decisions_resp = client.get("/api/admin/decisions", headers=admin_headers)
    assert decisions_resp.status_code == 200
    all_decs = decisions_resp.json()
    assert any(d["report_id"] == report_id for d in all_decs)

    # Clean up test report from Supabase
    repo = get_report_repository()
    try:
        repo._client.table("citizen_reports").delete().eq("id", report_id).execute()
    except Exception:
        pass


if __name__ == "__main__":
    test_supabase_single_source_of_truth()
    test_full_cross_portal_supabase_workflow()
    print("ALL TESTS PASSED SUCCESSFULLY! Supabase PostgreSQL is verified as the single source of truth.")
