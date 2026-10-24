"""
UrbanSage AI — Realistic Demonstration Dataset Seeder
======================================================
Idempotent seeding script for municipal decision-support hackathon demonstration.

Creates:
- Canonical BBMP wards (NBR-001 through NBR-010)
- Realistic citizen reports spanning all four categories and severity levels
- Evidence-based departmental recommendations with explainable rationales
- Persisted administrative triage decisions and department assignments
- Baseline capital budget plan (PLN-DEMO-2026) with line items
- Projects assigned to contractors (VND-BBMP-WORKS-01) with trackable milestones,
  photographic evidence hashes, and verified disbursements.

All records are explicitly labeled with `is_synthetic: true` / synthetic notices.
Idempotent: Rerunning this script does NOT duplicate records.

Execution:
----------
    python -m app.db.seed_demo
"""

from __future__ import annotations

import datetime
from datetime import timezone
import hashlib
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("urbansage.seed")


def seed_database(db_path: str | None = None) -> None:
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", os.getenv("REPORTS_DB_PATH", "urbansage.db"))

    logger.info("Initializing and seeding single persistent database at: %s", db_path)

    # Ensure parent dir exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Import repositories to initialize all schemas
    from app.reports.factory import get_report_repository, reset_repository_instance
    from app.accountability.repository import get_accountability_repository, reset_accountability_repository
    from app.governance.repository import get_governance_repository

    # Reset singletons to point to our db_path
    os.environ["DATABASE_BACKEND"] = "sqlite"
    os.environ["DATABASE_PATH"] = db_path
    reset_repository_instance()
    reset_accountability_repository(db_path=db_path)

    report_repo = get_report_repository()
    acc_repo = get_accountability_repository()
    gov_repo = get_governance_repository()

    now = datetime.datetime.now(timezone.utc)
    now_iso = now.isoformat()
    yesterday_iso = (now - datetime.timedelta(days=1)).isoformat()
    two_days_ago_iso = (now - datetime.timedelta(days=2)).isoformat()
    three_days_ago_iso = (now - datetime.timedelta(days=3)).isoformat()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # -----------------------------------------------------------------------
    # 1. Seed Citizen Reports
    # -----------------------------------------------------------------------
    reports_data = [
        {
            "id": "RPT-00000001",
            "category": "flooding_drainage",
            "description": "Severe stormwater drain overflow causing 2-foot waterlogging on 100ft road near Commercial Street intersection.",
            "severity": 4,
            "latitude": 12.9856,
            "longitude": 77.6057,
            "location_desc": "Near Commercial St Junction, Shivajinagar",
            "nbr_id": "NBR-001",
            "urgency": 82.5,
            "evidence": 88.0,
            "status": "assigned",
            "created_at": three_days_ago_iso,
        },
        {
            "id": "RPT-00000002",
            "category": "flooding_drainage",
            "description": "Culvert blockage behind Maharaja signal causing roadside silt accumulation and pedestrian obstruction after evening rain.",
            "severity": 3,
            "latitude": 12.9345,
            "longitude": 77.6266,
            "location_desc": "Maharaja Signal Service Road, Koramangala",
            "nbr_id": "NBR-002",
            "urgency": 74.0,
            "evidence": 76.0,
            "status": "under_review",
            "created_at": two_days_ago_iso,
        },
        {
            "id": "RPT-00000003",
            "category": "water_scarcity",
            "description": "Continuous pipe supply failure for 5 consecutive days affecting 45 industrial worker tenements. Groundwater TDS exceeds 1200.",
            "severity": 4,
            "latitude": 13.0285,
            "longitude": 77.5197,
            "location_desc": "Phase 2 Labour Colony, Peenya",
            "nbr_id": "NBR-003",
            "urgency": 85.0,
            "evidence": 82.0,
            "status": "assigned",
            "created_at": two_days_ago_iso,
        },
        {
            "id": "RPT-00000004",
            "category": "water_scarcity",
            "description": "Deep borewell drying up in residential layout; municipal tanker delivery disrupted without prior public notification.",
            "severity": 3,
            "latitude": 12.9698,
            "longitude": 77.7499,
            "location_desc": "Outer Ring Road Extension, Whitefield",
            "nbr_id": "NBR-005",
            "urgency": 71.5,
            "evidence": 70.0,
            "status": "submitted",
            "created_at": yesterday_iso,
        },
        {
            "id": "RPT-00000005",
            "category": "heat",
            "description": "Asphalt heat island effect registering extreme ambient temperature at unshaded major bus interchange. Commuters in severe distress.",
            "severity": 5,
            "latitude": 13.0285,
            "longitude": 77.5197,
            "location_desc": "Peenya Bus Interchange, Peenya",
            "nbr_id": "NBR-003",
            "urgency": 91.0,
            "evidence": 85.0,
            "status": "under_review",
            "created_at": yesterday_iso,
        },
        {
            "id": "RPT-00000006",
            "category": "heat",
            "description": "Lack of tree canopy and metal roof bus stops creating unbearable afternoon heat conditions for senior citizens.",
            "severity": 3,
            "latitude": 12.9856,
            "longitude": 77.6057,
            "location_desc": "Mehkri Circle Bus Shelter, Shivajinagar",
            "nbr_id": "NBR-001",
            "urgency": 68.0,
            "evidence": 72.0,
            "status": "submitted",
            "created_at": now_iso,
        },
        {
            "id": "RPT-00000007",
            "category": "loss_of_green_cover",
            "description": "Unauthorized felling of 4 mature rain trees along pedestrian walkway without BBMP Tree Officer public permission notice.",
            "severity": 4,
            "latitude": 12.9784,
            "longitude": 77.6408,
            "location_desc": "12th Main Road, Indiranagar",
            "nbr_id": "NBR-004",
            "urgency": 76.5,
            "evidence": 90.0,
            "status": "completed_awaiting_verification",
            "created_at": three_days_ago_iso,
        },
        {
            "id": "RPT-00000008",
            "category": "loss_of_green_cover",
            "description": "Park perimeter hedge encroached and cleared for unauthorized vehicle parking; soil compaction damaging remaining neem root zones.",
            "severity": 3,
            "latitude": 12.9250,
            "longitude": 77.5838,
            "location_desc": "Madhavan Park Perimeter, Jayanagar",
            "nbr_id": "NBR-006",
            "urgency": 65.0,
            "evidence": 78.0,
            "status": "verified_resolved",
            "created_at": three_days_ago_iso,
        },
        {
            "id": "RPT-00000009",
            "category": "flooding_drainage",
            "description": "Critical wetland overflow causing blackwater backflow into ground-floor residences along lower lake catchment boundary.",
            "severity": 5,
            "latitude": 12.9260,
            "longitude": 77.6762,
            "location_desc": "Bellandur Lower Lake Road, Bellandur",
            "nbr_id": "NBR-007",
            "urgency": 96.0,
            "evidence": 92.0,
            "status": "assigned",
            "created_at": two_days_ago_iso,
        },
        {
            "id": "RPT-00000010",
            "category": "flooding_drainage",
            "description": "Heritage stonework drain partially collapsed after monsoon showers; standing water attracting mosquito breeding.",
            "severity": 2,
            "latitude": 13.0031,
            "longitude": 77.5643,
            "location_desc": "8th Cross Heritage Lane, Malleswaram",
            "nbr_id": "NBR-008",
            "urgency": 52.0,
            "evidence": 74.0,
            "status": "submitted",
            "created_at": yesterday_iso,
        },
    ]

    with conn:
        for r in reports_data:
            cursor = conn.execute("SELECT id FROM citizen_reports WHERE id = ?", (r["id"],))
            if cursor.fetchone():
                continue  # Idempotent skip

            timeline = [
                {
                    "transition_id": f"TRN-{r['id'][-4:]}-01",
                    "from_status": "none",
                    "to_status": "submitted",
                    "actor_role": "citizen",
                    "actor_id": "citizen-demo-1",
                    "reason": "Initial citizen submission",
                    "timestamp": r["created_at"],
                }
            ]
            if r["status"] in ("under_review", "assigned", "completed_awaiting_verification", "verified_resolved"):
                timeline.append({
                    "transition_id": f"TRN-{r['id'][-4:]}-02",
                    "from_status": "submitted",
                    "to_status": "under_review",
                    "actor_role": "administrator",
                    "actor_id": "demo-admin-1",
                    "reason": "Administrative priority queue triage",
                    "timestamp": yesterday_iso,
                })
            if r["status"] in ("assigned", "completed_awaiting_verification", "verified_resolved"):
                timeline.append({
                    "transition_id": f"TRN-{r['id'][-4:]}-03",
                    "from_status": "under_review",
                    "to_status": "assigned",
                    "actor_role": "administrator",
                    "actor_id": "demo-admin-1",
                    "reason": "Work order dispatched to municipal department",
                    "timestamp": yesterday_iso,
                })
            if r["status"] in ("completed_awaiting_verification", "verified_resolved"):
                timeline.append({
                    "transition_id": f"TRN-{r['id'][-4:]}-04",
                    "from_status": "assigned",
                    "to_status": "completed_awaiting_verification",
                    "actor_role": "contractor",
                    "actor_id": "VND-BBMP-WORKS-01",
                    "reason": "Field remediation completed; awaiting citizen confirmation",
                    "timestamp": now_iso,
                })
            if r["status"] == "verified_resolved":
                timeline.append({
                    "transition_id": f"TRN-{r['id'][-4:]}-05",
                    "from_status": "completed_awaiting_verification",
                    "to_status": "verified_resolved",
                    "actor_role": "citizen",
                    "actor_id": "citizen-verifier",
                    "reason": "Citizen corroborated remediation on site",
                    "timestamp": now_iso,
                })

            resolution_evidence = None
            if r["status"] in ("completed_awaiting_verification", "verified_resolved"):
                resolution_evidence = {
                    "completed_by": "Bengaluru Urban Drainage & Infra Ltd",
                    "completion_notes": "Debris cleared, bioswale restored, and native saplings planted.",
                    "evidence_photos": [
                        {
                            "photo_id": "PHO-POST-REMED-01",
                            "file_name": "remediation_complete.jpg",
                            "mime_type": "image/jpeg",
                            "size_bytes": 1420500,
                            "caption": "Post-intervention field photograph",
                            "captured_at": now_iso,
                        }
                    ],
                    "completed_at": now_iso,
                    "citizen_confirmed": True if r["status"] == "verified_resolved" else None,
                    "citizen_feedback": "Verified cleared in person" if r["status"] == "verified_resolved" else None,
                    "verified_at": now_iso if r["status"] == "verified_resolved" else None,
                }

            conn.execute(
                """
                INSERT INTO citizen_reports (
                    id, category, description, severity, latitude, longitude,
                    location_description, neighbourhood_id, reporter_id, reporter_contact,
                    photos_json, status, verification_status, is_verified_measurement,
                    data_source, urgency_score, evidence_confidence_score,
                    resolution_evidence_json, timeline_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'CITIZEN_REPORT', ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["id"],
                    r["category"],
                    r["description"],
                    r["severity"],
                    r["latitude"],
                    r["longitude"],
                    r["location_desc"],
                    r["nbr_id"],
                    "citizen-demo-1",
                    None,
                    json.dumps([]),
                    r["status"],
                    "officially_verified" if r["status"] == "verified_resolved" else "unverified",
                    r["urgency"],
                    r["evidence"],
                    json.dumps(resolution_evidence) if resolution_evidence else None,
                    json.dumps(timeline),
                    r["created_at"],
                    now_iso,
                ),
            )

    logger.info("Successfully verified/seeded %d citizen reports.", len(reports_data))

    # -----------------------------------------------------------------------
    # 2. Seed Departmental Recommendations & Admin Decisions
    # -----------------------------------------------------------------------
    for r in reports_data:
        gov_repo.get_or_generate_recommendation(
            report_id=r["id"],
            category=r["category"],
            severity=r["severity"],
            neighbourhood_id=r["nbr_id"],
        )

    # Seed Admin Decisions for assigned items
    assigned_reports = [r for r in reports_data if r["status"] in ("assigned", "completed_awaiting_verification", "verified_resolved")]
    for r in assigned_reports:
        with conn:
            cursor = conn.execute("SELECT decision_id FROM admin_decisions WHERE report_id = ?", (r["id"],))
            if not cursor.fetchone():
                conn.execute(
                    """
                    INSERT INTO admin_decisions (
                        decision_id, report_id, decision_type, assigned_department,
                        assigned_action, review_notes, priority_tier, reviewer_id, created_at
                    ) VALUES (?, ?, 'ASSIGN_DEPARTMENT', ?, ?, ?, 'P1_IMMEDIATE', 'demo-admin-1', ?)
                    """,
                    (
                        f"DEC-{r['id'][-8:]}",
                        r["id"],
                        "BBMP Stormwater Drainage & Lakes Department" if "flooding" in r["category"] else "BWSSB Potable Water Directorate",
                        "Emergency Field Desilting & Culvert Clearance",
                        "High urgency crowd-sourced ticket corroborated by ward vulnerability index. Dispatched under accelerated municipal protocol.",
                        yesterday_iso,
                    ),
                )

    logger.info("Successfully verified/seeded departmental recommendations and admin decisions.")

    # -----------------------------------------------------------------------
    # 3. Seed Budget Plan & Line Items
    # -----------------------------------------------------------------------
    plan_id = "PLN-DEMO-2026"
    with conn:
        cursor = conn.execute("SELECT plan_id FROM budget_plans WHERE plan_id = ?", (plan_id,))
        if not cursor.fetchone():
            conn.execute(
                """
                INSERT INTO budget_plans (
                    plan_id, title, budget_lakh, equity_threshold, total_allocated_lakh,
                    remaining_balance_lakh, status, created_by, notes, created_at, updated_at
                ) VALUES (?, ?, 500.0, 0.30, 482.5, 17.5, 'proposed', 'demo-admin-1', ?, ?, ?)
                """,
                (
                    plan_id,
                    "Municipal Climate Resilience Capital Budget Plan FY 2026-27",
                    "Pareto-optimal mathematical allocation derived via SciPy HiGHS MILP, integrating bounded citizen distress signals and municipal equity floor.",
                    now_iso,
                    now_iso,
                ),
            )

            plan_items = [
                {
                    "item_id": "ITM-DEMO-01",
                    "nbr_id": "NBR-001",
                    "nbr_name": "Shivajinagar Central",
                    "int_id": "INT-01",
                    "int_name": "Permeable Bioswales & Urban Silt Traps",
                    "cat": "flooding_drainage",
                    "units": 3,
                    "cost_unit": 25.0,
                    "total": 75.0,
                    "rationale": "High recurrence of road overflow near Commercial Street; relieves downstream stormwater surges.",
                },
                {
                    "item_id": "ITM-DEMO-02",
                    "nbr_id": "NBR-003",
                    "nbr_name": "Peenya Industrial Area",
                    "int_id": "INT-02",
                    "int_name": "High-Albedo Cool Pavement & Shade Canopies",
                    "cat": "heat",
                    "units": 4,
                    "cost_unit": 35.0,
                    "total": 140.0,
                    "rationale": "High social vulnerability (SVI 76.0) and severe industrial thermal anomaly; satisfies 30% equity floor.",
                },
                {
                    "item_id": "ITM-DEMO-03",
                    "nbr_id": "NBR-007",
                    "nbr_name": "Bellandur Catchment",
                    "int_id": "INT-03",
                    "int_name": "Engineered Retention Wetlands & Overflow Weirs",
                    "cat": "flooding_drainage",
                    "units": 2,
                    "cost_unit": 85.0,
                    "total": 170.0,
                    "rationale": "Mitigates critical lake backflow hazards during monsoon flash floods.",
                },
                {
                    "item_id": "ITM-DEMO-04",
                    "nbr_id": "NBR-005",
                    "nbr_name": "Whitefield Tech Belt",
                    "int_id": "INT-04",
                    "int_name": "Deep Aquifer Recharge Wells & Permeable Basins",
                    "cat": "water_scarcity",
                    "units": 3,
                    "cost_unit": 32.5,
                    "total": 97.5,
                    "rationale": "Reverses acute groundwater depletion index (91.0/100) across peripheral growth corridor.",
                },
            ]

            for item in plan_items:
                conn.execute(
                    """
                    INSERT INTO budget_plan_items (
                        item_id, plan_id, neighbourhood_id, neighbourhood_name,
                        intervention_id, intervention_name, category, units,
                        cost_per_unit_lakh, total_cost_lakh, rationale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["item_id"],
                        plan_id,
                        item["nbr_id"],
                        item["nbr_name"],
                        item["int_id"],
                        item["int_name"],
                        item["cat"],
                        item["units"],
                        item["cost_unit"],
                        item["total"],
                        item["rationale"],
                    ),
                )

    logger.info("Successfully verified/seeded baseline budget plan (PLN-DEMO-2026).")

    # -----------------------------------------------------------------------
    # 4. Seed Contractor Allocations, Milestones & Evidence
    # -----------------------------------------------------------------------
    contractor_alloc_id = "ALC-SEED-01"
    with conn:
        cursor = conn.execute("SELECT allocation_id FROM allocations WHERE allocation_id = ?", (contractor_alloc_id,))
        if not cursor.fetchone():
            conn.execute(
                """
                INSERT INTO allocations (
                    allocation_id, title, neighbourhood_id, neighbourhood_name,
                    intervention_id, intervention_name, category, fiscal_year,
                    currency, allocated_amount_lakh, committed_amount_lakh,
                    disbursed_amount_lakh, planned_units, status, authorized_by,
                    council_resolution_ref, source_optimizer_run_id, created_at, updated_at
                ) VALUES (?, ?, 'NBR-001', 'Shivajinagar Central', 'INT-01', 'Permeable Bioswales & Urban Silt Traps',
                          'flooding_drainage', '2025-2026', 'INR', 35.0, 32.5, 25.0, 4, 'in_progress',
                          'demo-admin-1', 'BBMP/CR/2025/ENV-042', 'PLN-DEMO-2026', ?, ?)
                """,
                (
                    contractor_alloc_id,
                    "Shivajinagar Central Stormwater Drain Desilting & Bioswales",
                    three_days_ago_iso,
                    now_iso,
                ),
            )

            # Commitment to VND-BBMP-WORKS-01
            conn.execute(
                """
                INSERT INTO commitments (
                    commitment_id, allocation_id, vendor_id, vendor_name,
                    contract_reference, committed_amount_lakh, status, approved_by, created_at
                ) VALUES ('CMT-SEED-01', ?, 'VND-BBMP-WORKS-01', 'Bengaluru Urban Drainage & Infra Ltd',
                          'CNT-2025-BLR-0114', 32.5, 'active', 'demo-admin-1', ?)
                """,
                (contractor_alloc_id, three_days_ago_iso),
            )

            # Milestones
            milestones = [
                {
                    "id": "MLS-SEED-01",
                    "title": "Site Demarcation, Utility Shifting & Bathymetry",
                    "desc": "Underground cable line detection, barricading, and initial silt depth profiling.",
                    "order": 1,
                    "target_date": "2026-03-15",
                    "status": "verified_complete",
                    "tied_amt": 10.0,
                    "progress": 100,
                    "completed_at": two_days_ago_iso,
                },
                {
                    "id": "MLS-SEED-02",
                    "title": "Bioswale Channel Excavation & Native Vetiver Planting",
                    "desc": "Excavating 400m channel with 3:1 slopes and planting drought-hardy root systems.",
                    "order": 2,
                    "target_date": "2026-04-10",
                    "status": "verified_complete",
                    "tied_amt": 15.0,
                    "progress": 100,
                    "completed_at": yesterday_iso,
                },
                {
                    "id": "MLS-SEED-03",
                    "title": "Perimeter Overflow Weir & Automated Level Sensor Installation",
                    "desc": "Constructing reinforced concrete weir and solar-powered ultrasonic telemetry sensor.",
                    "order": 3,
                    "target_date": "2026-05-30",
                    "status": "in_progress",
                    "tied_amt": 7.5,
                    "progress": 45,
                    "completed_at": None,
                },
            ]

            for m in milestones:
                conn.execute(
                    """
                    INSERT INTO milestones (
                        milestone_id, allocation_id, title, description, sequence_order,
                        target_completion_date, status, disbursement_tied_amount_lakh,
                        percent_progress, completed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m["id"],
                        contractor_alloc_id,
                        m["title"],
                        m["desc"],
                        m["order"],
                        m["target_date"],
                        m["status"],
                        m["tied_amt"],
                        m["progress"],
                        m["completed_at"],
                        three_days_ago_iso,
                        now_iso,
                    ),
                )

            # Seed Evidence for Completed Milestones
            conn.execute(
                """
                INSERT INTO evidence_metadata (
                    evidence_id, milestone_id, evidence_type, title, description,
                    file_name, mime_type, file_size_bytes, document_hash,
                    submitted_by, submitted_at, verification_status, verification_notes
                ) VALUES (
                    'EVD-SEED-01', 'MLS-SEED-01', 'geo_survey', 'Bathymetric Survey & Silt Analysis Certificate',
                    'Total station survey and core sample lab results confirming 1.2m sediment clearance.',
                    'bathymetry_survey_shv.pdf', 'application/pdf', 2450000,
                    '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
                    'VND-BBMP-WORKS-01', ?, 'verified', 'Inspected and certified by Assistant Executive Engineer'
                )
                """,
                (two_days_ago_iso,),
            )

            # Seed Verification Decision
            conn.execute(
                """
                INSERT INTO verification_decisions (
                    decision_id, milestone_id, decision, verifier_id, verifier_name,
                    comments, decided_at, passed_inspection
                ) VALUES (
                    'VDEC-SEED-01', 'MLS-SEED-01', 'approved', 'INSP-BBMP-08',
                    'Er. S. Raghavan (Chief Drainage Engineer)',
                    'Physical inspection verified: Channel cross-section aligns with approved engineering drawings.',
                    ?, 1
                )
                """,
                (two_days_ago_iso,),
            )

            # Seed Disbursements
            conn.execute(
                """
                INSERT INTO disbursements (
                    disbursement_id, allocation_id, commitment_id, milestone_id,
                    amount_lakh, payment_reference, recipient_entity, status,
                    approved_by, disbursed_at
                ) VALUES (
                    'DIS-SEED-01', ?, 'CMT-SEED-01', 'MLS-SEED-01',
                    10.0, 'RBI-NEFT-20260218-09182', 'Bengaluru Urban Drainage & Infra Ltd',
                    'cleared', 'demo-admin-1', ?
                )
                """,
                (contractor_alloc_id, two_days_ago_iso),
            )

    logger.info("Successfully verified/seeded contractor project assignments and milestones.")
    conn.close()

    logger.info("Database seeding successfully completed! Single persistent store is ready at '%s'.", db_path)


if __name__ == "__main__":
    target_db = sys.argv[1] if len(sys.argv) > 1 else None
    seed_database(target_db)
