"""
UrbanSage AI — Live Supabase PostgreSQL Verification Test Script
================================================================
Non-destructive live integration test for validating Supabase PostgreSQL connection,
tables, views, permissions, CRUD lifecycle, and public privacy guarantees.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from supabase import create_client

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# 1. Load environment configuration
env_path = backend_dir.parent / "frontend" / ".env.local"
if env_path.exists():
    for k, v in dotenv_values(env_path).items():
        if k and v and k not in os.environ:
            os.environ[k] = v

# Ensure DATABASE_BACKEND is supabase for this run
os.environ["DATABASE_BACKEND"] = "supabase"

from app.auth import create_access_token, ADMIN_API_KEY
from app.main import app
from app.reports.factory import get_report_repository, reset_repository_instance
from app.reports.models import (
    CitizenReportCreate,
    ProblemCategory,
    ReportStatus,
    VerificationStatus,
)
from app.reports.supabase_repo import SupabaseCitizenReportRepository


def run_verification() -> Dict[str, Any]:
    results: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live_supabase_connected": False,
        "table_checks": {},
        "tests": {},
        "errors": [],
        "secrets_exposed": False,
    }

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        results["errors"].append("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in configuration.")
        return results

    # 1. Connect Client
    try:
        supabase_client = create_client(url, key)
        results["live_supabase_connected"] = True
    except Exception as e:
        results["errors"].append(f"Failed to initialize Supabase client: {e}")
        return results

    # 2. Confirm Required Tables and View
    required_objects = [
        ("citizen_reports", "table"),
        ("citizen_reports_public", "view"),
        ("allocations", "table"),
        ("commitments", "table"),
        ("milestones", "table"),
        ("evidence_metadata", "table"),
        ("verification_decisions", "table"),
        ("disbursements", "table"),
        ("discrepancies", "table"),
        ("audit_events", "table"),
    ]

    all_objects_found = True
    for name, obj_type in required_objects:
        try:
            res = supabase_client.table(name).select("*").limit(1).execute()
            results["table_checks"][name] = {
                "status": "EXISTS",
                "type": obj_type,
                "accessible": True,
            }
        except Exception as e:
            all_objects_found = False
            results["table_checks"][name] = {
                "status": "ERROR",
                "type": obj_type,
                "error": str(e)[:150],
            }

    results["tests"]["required_schema_objects_exist"] = all_objects_found

    # 3. Non-destructive Connectivity Check
    reset_repository_instance()
    try:
        repo = SupabaseCitizenReportRepository(
            supabase_url=url,
            supabase_key=key,
        )
        is_healthy = repo.health_check()
        results["tests"]["connectivity_health_check"] = is_healthy
    except Exception as e:
        results["tests"]["connectivity_health_check"] = False
        results["errors"].append(f"Connectivity health check failed: {e}")
        return results

    # 4. Test Citizen Report Creation, Retrieval, and Persistence
    test_report_id = None
    created_at_time = datetime.now(timezone.utc)
    test_tag = f"LIVE-TEST-{int(time.time())}"
    
    try:
        report_payload = CitizenReportCreate(
            category=ProblemCategory.FLOODING_DRAINAGE,
            description=f"[{test_tag}] Automated live Supabase integration verification test probe.",
            severity=3,
            latitude=12.9716,
            longitude=77.5946,
            location_description="Automated Test Node Alpha",
            neighbourhood_id="NBR-001",
            reporter_id=f"test-probe-{test_tag}",
            reporter_contact="private-contact-test@example.com",
            photos=[],
        )

        created_report = repo.create_report(report_payload, allow_duplicate=True)
        test_report_id = created_report.id
        results["tests"]["report_creation"] = {
            "passed": bool(test_report_id and test_report_id.startswith("RPT-")),
            "report_id": test_report_id,
        }

        # Retrieval check
        retrieved_report = repo.get_report(test_report_id)
        report_retrieved_ok = (
            retrieved_report is not None
            and retrieved_report.id == test_report_id
            and retrieved_report.category == ProblemCategory.FLOODING_DRAINAGE
            and retrieved_report.severity == 3
            and retrieved_report.neighbourhood_id == "NBR-001"
            and retrieved_report.urgency_score > 0
            and retrieved_report.evidence_confidence_score > 0
        )
        results["tests"]["report_retrieval_and_persistence"] = {
            "passed": report_retrieved_ok,
            "category_persisted": retrieved_report.category.value if retrieved_report else None,
            "urgency_score": retrieved_report.urgency_score if retrieved_report else None,
        }

    except Exception as e:
        results["tests"]["report_creation"] = {"passed": False, "error": str(e)}
        results["tests"]["report_retrieval_and_persistence"] = {"passed": False, "error": str(e)}
        results["errors"].append(f"Report persistence test failed: {e}")

    # 5. Test Public View & Response Privacy Guarantees
    if test_report_id:
        try:
            # Query public view directly on live Supabase
            pub_res = supabase_client.table("citizen_reports_public").select("*").eq("id", test_report_id).execute()
            pub_data = pub_res.data or []
            
            view_hides_pii = False
            if pub_data:
                row = pub_data[0]
                has_reporter_contact = "reporter_contact" in row
                has_reporter_id = "reporter_id" in row
                view_hides_pii = (not has_reporter_contact) and (not has_reporter_id)
            
            results["tests"]["public_view_omits_pii"] = {
                "passed": view_hides_pii,
                "record_present_in_view": len(pub_data) > 0,
                "reporter_contact_omitted": not ("reporter_contact" in pub_data[0]) if pub_data else False,
                "reporter_id_omitted": not ("reporter_id" in pub_data[0]) if pub_data else False,
            }

            # Query via FastAPI test client
            client = TestClient(app)
            resp = client.get(f"/api/reports/{test_report_id}")
            api_data = resp.json() if resp.status_code == 200 else {}
            api_hides_pii = (
                resp.status_code == 200
                and "reporter_contact" not in api_data
                and "reporter_id" not in api_data
            )
            results["tests"]["public_api_endpoint_omits_pii"] = {
                "passed": api_hides_pii,
                "status_code": resp.status_code,
                "reporter_contact_leaked": "reporter_contact" in api_data,
            }
        except Exception as e:
            results["tests"]["public_view_omits_pii"] = {"passed": False, "error": str(e)}
            results["tests"]["public_api_endpoint_omits_pii"] = {"passed": False, "error": str(e)}

    # 6. Test Accountability Allocation Read Operations
    try:
        # Live Supabase query
        sb_alloc = supabase_client.table("allocations").select("*").limit(5).execute()
        sb_alloc_count = len(sb_alloc.data) if sb_alloc.data is not None else 0

        # Backend API query
        client = TestClient(app)
        api_summary = client.get("/api/accountability/summary")
        api_alloc = client.get("/api/accountability/allocations")

        results["tests"]["accountability_read_operations"] = {
            "passed": api_summary.status_code == 200 and api_alloc.status_code == 200,
            "summary_status_code": api_summary.status_code,
            "allocations_status_code": api_alloc.status_code,
            "supabase_allocations_table_rows": sb_alloc_count,
        }
    except Exception as e:
        results["tests"]["accountability_read_operations"] = {"passed": False, "error": str(e)}

    # 7. Verify Administrator and Contractor Authorization Controls
    try:
        client = TestClient(app)

        # A. Unauthenticated request to restricted endpoints
        unauth_disc = client.get("/api/accountability/discrepancies")
        unauth_audit = client.get("/api/accountability/audit-trail")
        unauth_admin_brief = client.get("/api/admin/decision-brief")

        # B. Contractor JWT request to admin-only endpoint (discrepancies)
        contractor_token = create_access_token(user_id="contractor-1", role="contractor")
        contractor_disc = client.get(
            "/api/accountability/discrepancies",
            headers={"Authorization": f"Bearer {contractor_token}"},
        )

        # C. Admin API Key request
        admin_key_brief = client.get(
            "/api/admin/decision-brief",
            headers={"X-API-Key": ADMIN_API_KEY},
        )

        # D. Admin JWT request
        admin_token = create_access_token(user_id="admin-1", role="administrator")
        admin_jwt_disc = client.get(
            "/api/accountability/discrepancies",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        auth_controls_passed = (
            unauth_disc.status_code in (401, 403)
            and unauth_audit.status_code in (401, 403)
            and unauth_admin_brief.status_code in (401, 403)
            and contractor_disc.status_code == 403
            and admin_key_brief.status_code == 200
            and admin_jwt_disc.status_code == 200
        )

        results["tests"]["authorization_controls"] = {
            "passed": auth_controls_passed,
            "unauth_discrepancies_status": unauth_disc.status_code,
            "unauth_audit_status": unauth_audit.status_code,
            "unauth_admin_brief_status": unauth_admin_brief.status_code,
            "contractor_forbidden_on_discrepancies": contractor_disc.status_code == 403,
            "admin_api_key_brief_status": admin_key_brief.status_code,
            "admin_jwt_discrepancies_status": admin_jwt_disc.status_code,
        }
    except Exception as e:
        results["tests"]["authorization_controls"] = {"passed": False, "error": str(e)}

    # 8. Clean up Test Record
    if test_report_id and test_report_id.startswith("RPT-"):
        try:
            # Confirm unambiguous identity before deletion
            target_check = supabase_client.table("citizen_reports").select("id, description").eq("id", test_report_id).execute()
            if target_check.data and test_tag in target_check.data[0].get("description", ""):
                del_res = supabase_client.table("citizen_reports").delete().eq("id", test_report_id).execute()
                
                # Verify deletion
                post_del = supabase_client.table("citizen_reports").select("id").eq("id", test_report_id).execute()
                cleaned_up = len(post_del.data or []) == 0
                results["tests"]["test_record_cleanup"] = {
                    "passed": cleaned_up,
                    "deleted_id": test_report_id,
                }
            else:
                results["tests"]["test_record_cleanup"] = {
                    "passed": False,
                    "reason": "Test record identity verification mismatch. Deletion skipped for safety.",
                }
        except Exception as e:
            results["tests"]["test_record_cleanup"] = {"passed": False, "error": str(e)}

    return results


if __name__ == "__main__":
    verification_output = run_verification()
    # Print results as clean JSON without printing any secret values
    print(json.dumps(verification_output, indent=2))
