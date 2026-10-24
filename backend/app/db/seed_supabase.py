"""
UrbanSage AI — Supabase PostgreSQL Idempotent Seeder
====================================================
Seeds calibrated, realistic demonstration records directly into Supabase PostgreSQL.
Idempotent: Uses primary key upserts with on_conflict so repeated runs create no duplicates.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("urbansage.seed_supabase")


def get_client():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in environment.")
    return create_client(url, key)


def seed_supabase():
    client = get_client()
    now = datetime.datetime.now(timezone.utc)
    now_iso = now.isoformat()
    yesterday_iso = (now - datetime.timedelta(days=1)).isoformat()
    two_days_ago_iso = (now - datetime.timedelta(days=2)).isoformat()
    three_days_ago_iso = (now - datetime.timedelta(days=3)).isoformat()

    logger.info("Connecting to Supabase PostgreSQL...")

    # -------------------------------------------------------------------------
    # 1. Citizen Reports (RPT-00000001 through RPT-00000010)
    # -------------------------------------------------------------------------
    reports = [
        {
            "id": "RPT-00000001",
            "category": "flooding_drainage",
            "description": "Severe stormwater drain overflow causing 2-foot waterlogging on 100ft road near Commercial Street intersection. [Synthetic benchmark record]",
            "severity": 4,
            "latitude": 12.9856,
            "longitude": 77.6057,
            "location_description": "Near Commercial St Junction, Shivajinagar",
            "neighbourhood_id": "NBR-001",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "assigned",
            "verification_status": "officially_verified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 82.5,
            "evidence_confidence_score": 88.0,
            "created_at": three_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000002",
            "category": "flooding_drainage",
            "description": "Culvert blockage behind Maharaja signal causing roadside silt accumulation and pedestrian obstruction after evening rain. [Synthetic benchmark record]",
            "severity": 3,
            "latitude": 12.9345,
            "longitude": 77.6266,
            "location_description": "Maharaja Signal Service Road, Koramangala",
            "neighbourhood_id": "NBR-002",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "under_review",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 74.0,
            "evidence_confidence_score": 76.0,
            "created_at": two_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000003",
            "category": "water_scarcity",
            "description": "Continuous pipe supply failure for 5 consecutive days affecting 45 industrial worker tenements. Groundwater TDS exceeds 1200. [Synthetic benchmark record]",
            "severity": 4,
            "latitude": 13.0285,
            "longitude": 77.5197,
            "location_description": "Phase 2 Labour Colony, Peenya",
            "neighbourhood_id": "NBR-003",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "assigned",
            "verification_status": "officially_verified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 85.0,
            "evidence_confidence_score": 82.0,
            "created_at": two_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000004",
            "category": "water_scarcity",
            "description": "Deep borewell drying up in residential layout; municipal tanker delivery disrupted without prior public notification. [Synthetic benchmark record]",
            "severity": 3,
            "latitude": 12.9698,
            "longitude": 77.7499,
            "location_description": "Outer Ring Road Extension, Whitefield",
            "neighbourhood_id": "NBR-005",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 71.5,
            "evidence_confidence_score": 70.0,
            "created_at": yesterday_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000005",
            "category": "heat",
            "description": "Asphalt heat island effect registering extreme ambient temperature at unshaded major bus interchange. Commuters in severe distress. [Synthetic benchmark record]",
            "severity": 5,
            "latitude": 13.0285,
            "longitude": 77.5197,
            "location_description": "Peenya Bus Interchange, Peenya",
            "neighbourhood_id": "NBR-003",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "under_review",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 91.0,
            "evidence_confidence_score": 85.0,
            "created_at": yesterday_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000006",
            "category": "heat",
            "description": "Lack of tree canopy and metal roof bus stops creating unbearable afternoon heat conditions for senior citizens. [Synthetic benchmark record]",
            "severity": 3,
            "latitude": 12.9856,
            "longitude": 77.6057,
            "location_description": "Mehkri Circle Bus Shelter, Shivajinagar",
            "neighbourhood_id": "NBR-001",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 68.0,
            "evidence_confidence_score": 72.0,
            "created_at": now_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000007",
            "category": "loss_of_green_cover",
            "description": "Unauthorized felling of 4 mature rain trees along pedestrian walkway without BBMP Tree Officer public permission notice. [Synthetic benchmark record]",
            "severity": 4,
            "latitude": 12.9784,
            "longitude": 77.6408,
            "location_description": "12th Main Road, Indiranagar",
            "neighbourhood_id": "NBR-004",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "completed_awaiting_verification",
            "verification_status": "community_corroborated",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 76.5,
            "evidence_confidence_score": 90.0,
            "created_at": three_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000008",
            "category": "loss_of_green_cover",
            "description": "Park perimeter hedge encroached and cleared for unauthorized vehicle parking; soil compaction damaging remaining neem root zones. [Synthetic benchmark record]",
            "severity": 3,
            "latitude": 12.9250,
            "longitude": 77.5838,
            "location_description": "Madhavan Park Perimeter, Jayanagar",
            "neighbourhood_id": "NBR-006",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "verified_resolved",
            "verification_status": "officially_verified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 65.0,
            "evidence_confidence_score": 78.0,
            "created_at": three_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000009",
            "category": "flooding_drainage",
            "description": "Critical wetland overflow causing blackwater backflow into ground-floor residences along lower lake catchment boundary. [Synthetic benchmark record]",
            "severity": 5,
            "latitude": 12.9260,
            "longitude": 77.6762,
            "location_description": "Bellandur Lower Lake Road, Bellandur",
            "neighbourhood_id": "NBR-007",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "assigned",
            "verification_status": "officially_verified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 96.0,
            "evidence_confidence_score": 92.0,
            "created_at": two_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "id": "RPT-00000010",
            "category": "flooding_drainage",
            "description": "Heritage stonework drain partially collapsed after monsoon showers; standing water attracting mosquito breeding. [Synthetic benchmark record]",
            "severity": 2,
            "latitude": 13.0031,
            "longitude": 77.5643,
            "location_description": "8th Cross Heritage Lane, Malleswaram",
            "neighbourhood_id": "NBR-008",
            "reporter_id": "citizen-demo-1",
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 52.0,
            "evidence_confidence_score": 74.0,
            "created_at": yesterday_iso,
            "updated_at": now_iso,
        },
    ]

    for r in reports:
        client.table("citizen_reports").upsert(r, on_conflict="id").execute()
    logger.info("Upserted %d citizen reports into Supabase.", len(reports))

    # -------------------------------------------------------------------------
    # 2. Allocations (ALC-00000001, ALC-00000002, ALC-00000003)
    # -------------------------------------------------------------------------
    allocations = [
        {
            "allocation_id": "ALC-00000001",
            "title": "Koramangala Valley Stormwater Drain Desilting & Bioswales [Synthetic]",
            "neighbourhood_id": "NBR-001",
            "neighbourhood_name": "Koramangala",
            "intervention_id": "INT-DRAIN-01",
            "intervention_name": "Engineered Bioswales & Silt Traps",
            "category": "flooding_drainage",
            "fiscal_year": "2025-2026",
            "currency": "INR",
            "allocated_amount_lakh": 35.0,
            "committed_amount_lakh": 32.5,
            "disbursed_amount_lakh": 25.0,
            "planned_units": 4,
            "status": "in_progress",
            "authorized_by": "MUNICIPAL_COMMISSIONER",
            "council_resolution_ref": "BBMP/CR/2025/ENV-042",
            "source_optimizer_run_id": "PLN-DEMO-2026",
            "created_at": three_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "allocation_id": "ALC-00000002",
            "title": "Indiranagar 100ft Road Permeable Pavements & Rain Gardens [Synthetic]",
            "neighbourhood_id": "NBR-002",
            "neighbourhood_name": "Indiranagar",
            "intervention_id": "INT-RAIN-02",
            "intervention_name": "Interlocking Permeable Concrete Pavement",
            "category": "flooding_drainage",
            "fiscal_year": "2025-2026",
            "currency": "INR",
            "allocated_amount_lakh": 25.0,
            "committed_amount_lakh": 24.0,
            "disbursed_amount_lakh": 8.0,
            "planned_units": 3,
            "status": "in_progress",
            "authorized_by": "MUNICIPAL_COMMISSIONER",
            "council_resolution_ref": "BBMP/CR/2025/ENV-049",
            "source_optimizer_run_id": "PLN-DEMO-2026",
            "created_at": two_days_ago_iso,
            "updated_at": now_iso,
        },
        {
            "allocation_id": "ALC-00000003",
            "title": "Whitefield IT Corridor Micro-Forest Canopy & Miyawaki Afforestation [Synthetic]",
            "neighbourhood_id": "NBR-004",
            "neighbourhood_name": "Whitefield",
            "intervention_id": "INT-TREE-01",
            "intervention_name": "High-Density Miyawaki Urban Forest",
            "category": "loss_of_green_cover",
            "fiscal_year": "2025-2026",
            "currency": "INR",
            "allocated_amount_lakh": 40.0,
            "committed_amount_lakh": 38.0,
            "disbursed_amount_lakh": 12.0,
            "planned_units": 2,
            "status": "in_progress",
            "authorized_by": "MUNICIPAL_COMMISSIONER",
            "council_resolution_ref": "BBMP/CR/2025/ENV-055",
            "source_optimizer_run_id": "PLN-DEMO-2026",
            "created_at": two_days_ago_iso,
            "updated_at": now_iso,
        },
    ]

    for a in allocations:
        client.table("allocations").upsert(a, on_conflict="allocation_id").execute()
    logger.info("Upserted %d allocations into Supabase.", len(allocations))

    # -------------------------------------------------------------------------
    # 3. Commitments
    # -------------------------------------------------------------------------
    commitments = [
        {
            "commitment_id": "CMT-00000001",
            "allocation_id": "ALC-00000001",
            "vendor_id": "VND-BBMP-WORKS-01",
            "vendor_name": "Bengaluru Urban Drainage & Infra Ltd",
            "contract_reference": "CNT-2025-BLR-0114",
            "committed_amount_lakh": 32.5,
            "status": "active",
            "approved_by": "FINANCE_OFFICER_01",
            "created_at": three_days_ago_iso,
        },
        {
            "commitment_id": "CMT-00000002",
            "allocation_id": "ALC-00000002",
            "vendor_id": "VND-ECO-INFRA-02",
            "vendor_name": "GreenGrid Urban Solutions Pvt Ltd",
            "contract_reference": "CNT-2025-BLR-0205",
            "committed_amount_lakh": 24.0,
            "status": "active",
            "approved_by": "FINANCE_OFFICER_01",
            "created_at": two_days_ago_iso,
        },
    ]

    for c in commitments:
        client.table("commitments").upsert(c, on_conflict="commitment_id").execute()
    logger.info("Upserted %d commitments into Supabase.", len(commitments))

    # -------------------------------------------------------------------------
    # 4. Milestones
    # -------------------------------------------------------------------------
    milestones = [
        {
            "milestone_id": "MLS-00000001",
            "allocation_id": "ALC-00000001",
            "title": "Site Survey, Bathymetry & Sediment Cleansing [Synthetic]",
            "description": "Initial sediment profiling, boundary demarcations and heavy machinery mobilization.",
            "sequence_order": 1,
            "target_completion_date": "2026-03-15",
            "status": "verified_complete",
            "disbursement_tied_amount_lakh": 10.0,
            "percent_progress": 100,
            "completed_at": two_days_ago_iso,
            "created_at": three_days_ago_iso,
            "updated_at": two_days_ago_iso,
        },
        {
            "milestone_id": "MLS-00000002",
            "allocation_id": "ALC-00000001",
            "title": "Bioswale Channel Shaping & Native Vetiver Planting [Synthetic]",
            "description": "Grading channel edges to 3:1 slopes and planting vetiver roots for natural filtration.",
            "sequence_order": 2,
            "target_completion_date": "2026-04-10",
            "status": "verified_complete",
            "disbursement_tied_amount_lakh": 15.0,
            "percent_progress": 100,
            "completed_at": yesterday_iso,
            "created_at": three_days_ago_iso,
            "updated_at": yesterday_iso,
        },
        {
            "milestone_id": "MLS-00000003",
            "allocation_id": "ALC-00000001",
            "title": "Perimeter Overflow Weir & Monitoring Telemetry Installation [Synthetic]",
            "description": "Reinforced concrete overflow spillway and automated ultrasonic level sensors.",
            "sequence_order": 3,
            "target_completion_date": "2026-05-30",
            "status": "in_progress",
            "disbursement_tied_amount_lakh": 7.5,
            "percent_progress": 60,
            "completed_at": None,
            "created_at": three_days_ago_iso,
            "updated_at": now_iso,
        },
    ]

    for m in milestones:
        client.table("milestones").upsert(m, on_conflict="milestone_id").execute()
    logger.info("Upserted %d milestones into Supabase.", len(milestones))

    # -------------------------------------------------------------------------
    # 5. Evidence Metadata
    # -------------------------------------------------------------------------
    evidence = [
        {
            "evidence_id": "EVD-00000001",
            "milestone_id": "MLS-00000001",
            "evidence_type": "geo_survey",
            "title": "Bathymetric Survey & Silt Analysis Certificate [Synthetic]",
            "description": "Total station survey and core sample lab results confirming 1.2m sediment clearance.",
            "file_name": "bathymetry_survey_shv.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2450000,
            "document_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "submitted_by": "VND-BBMP-WORKS-01",
            "submitted_at": two_days_ago_iso,
            "verification_status": "verified",
            "verification_notes": "Inspected and certified by Assistant Executive Engineer",
        }
    ]

    for e in evidence:
        client.table("evidence_metadata").upsert(e, on_conflict="evidence_id").execute()
    logger.info("Upserted %d evidence records into Supabase.", len(evidence))

    # -------------------------------------------------------------------------
    # 6. Verification Decisions
    # -------------------------------------------------------------------------
    vdecs = [
        {
            "decision_id": "VDEC-00000001",
            "milestone_id": "MLS-00000001",
            "decision": "approved",
            "verifier_id": "INSP-BBMP-08",
            "verifier_name": "Er. S. Raghavan (Chief Drainage Engineer)",
            "comments": "Physical inspection verified: Channel cross-section aligns with approved engineering drawings.",
            "decided_at": two_days_ago_iso,
            "passed_inspection": True,
        }
    ]

    for v in vdecs:
        client.table("verification_decisions").upsert(v, on_conflict="decision_id").execute()
    logger.info("Upserted %d verification decisions into Supabase.", len(vdecs))

    # -------------------------------------------------------------------------
    # 7. Disbursements
    # -------------------------------------------------------------------------
    disbursements = [
        {
            "disbursement_id": "DSB-00000001",
            "allocation_id": "ALC-00000001",
            "commitment_id": "CMT-00000001",
            "milestone_id": "MLS-00000001",
            "amount_lakh": 10.0,
            "payment_reference": "NEFT-BBMP-2025-00101",
            "recipient_entity": "Bengaluru Urban Drainage & Infra Ltd",
            "status": "completed",
            "approved_by": "FINANCE_SECRETARY",
            "disbursed_at": two_days_ago_iso,
        },
        {
            "disbursement_id": "DSB-00000002",
            "allocation_id": "ALC-00000001",
            "commitment_id": "CMT-00000001",
            "milestone_id": "MLS-00000002",
            "amount_lakh": 15.0,
            "payment_reference": "NEFT-BBMP-2025-00102",
            "recipient_entity": "Bengaluru Urban Drainage & Infra Ltd",
            "status": "completed",
            "approved_by": "FINANCE_SECRETARY",
            "disbursed_at": yesterday_iso,
        },
    ]

    for d in disbursements:
        client.table("disbursements").upsert(d, on_conflict="disbursement_id").execute()
    logger.info("Upserted %d disbursements into Supabase.", len(disbursements))

    # -------------------------------------------------------------------------
    # 8. Genesis Audit Events & Governance Records
    # -------------------------------------------------------------------------
    audit_events = [
        {
            "event_id": "AUD-00000001",
            "timestamp": three_days_ago_iso,
            "actor_id": "MUNICIPAL_COMMISSIONER",
            "actor_role": "administrator",
            "event_type": "allocation_created",
            "entity_type": "ALLOCATION",
            "entity_id": "ALC-00000001",
            "summary": "Demonstration seed genesis allocation authorized. [Synthetic record]",
            "previous_state": None,
            "new_state": {"allocated_amount_lakh": 35.0, "status": "in_progress"},
            "previous_event_hash": "GENESIS",
            "event_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        {
            "event_id": "AUD-00000002",
            "timestamp": two_days_ago_iso,
            "actor_id": "demo-admin-1",
            "actor_role": "administrator",
            "event_type": "BUDGET_PLAN_PROPOSED",
            "entity_type": "ALLOCATION",
            "entity_id": "ALC-00000001",
            "summary": "Baseline Capital Budget Plan FY 2026-27 proposed via SciPy HiGHS MILP optimizer. [Synthetic record]",
            "previous_state": None,
            "new_state": {
                "plan_id": "PLN-DEMO-2026",
                "title": "Municipal Climate Resilience Capital Budget Plan FY 2026-27",
                "budget_lakh": 500.0,
                "equity_threshold": 0.30,
                "total_allocated_lakh": 482.5,
                "remaining_balance_lakh": 17.5,
                "status": "proposed",
                "created_by": "demo-admin-1",
                "items": [
                    {
                        "item_id": "ITM-DEMO-01",
                        "neighbourhood_id": "NBR-001",
                        "neighbourhood_name": "Shivajinagar Central",
                        "intervention_id": "INT-01",
                        "intervention_name": "Permeable Bioswales & Urban Silt Traps",
                        "category": "flooding_drainage",
                        "units": 3,
                        "cost_per_unit_lakh": 25.0,
                        "total_cost_lakh": 75.0,
                        "rationale": "High recurrence of road overflow near Commercial Street.",
                    },
                    {
                        "item_id": "ITM-DEMO-02",
                        "neighbourhood_id": "NBR-003",
                        "neighbourhood_name": "Peenya Industrial Area",
                        "intervention_id": "INT-02",
                        "intervention_name": "High-Albedo Cool Pavement & Shade Canopies",
                        "category": "heat",
                        "units": 4,
                        "cost_per_unit_lakh": 35.0,
                        "total_cost_lakh": 140.0,
                        "rationale": "High social vulnerability (SVI 76.0); satisfies equity floor.",
                    },
                    {
                        "item_id": "ITM-DEMO-03",
                        "neighbourhood_id": "NBR-007",
                        "neighbourhood_name": "Bellandur Catchment",
                        "intervention_id": "INT-03",
                        "intervention_name": "Engineered Retention Wetlands & Overflow Weirs",
                        "category": "flooding_drainage",
                        "units": 2,
                        "cost_per_unit_lakh": 85.0,
                        "total_cost_lakh": 170.0,
                        "rationale": "Mitigates critical lake backflow hazards during monsoon flash floods.",
                    },
                    {
                        "item_id": "ITM-DEMO-04",
                        "neighbourhood_id": "NBR-005",
                        "neighbourhood_name": "Whitefield Tech Belt",
                        "intervention_id": "INT-04",
                        "intervention_name": "Deep Aquifer Recharge Wells & Permeable Basins",
                        "category": "water_scarcity",
                        "units": 3,
                        "cost_per_unit_lakh": 32.5,
                        "total_cost_lakh": 97.5,
                        "rationale": "Reverses acute groundwater depletion index across peripheral growth corridor.",
                    },
                ],
            },
            "previous_event_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "event_hash": "b2f0a1c984fe7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a09",
        },
    ]

    for a in audit_events:
        client.table("audit_events").upsert(a, on_conflict="event_id").execute()
    logger.info("Upserted %d audit events into Supabase.", len(audit_events))

    logger.info("Supabase database seeding successfully completed! Single source of truth is ready.")


if __name__ == "__main__":
    seed_supabase()
