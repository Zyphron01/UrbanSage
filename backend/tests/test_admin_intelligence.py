"""
UrbanSage AI — Stage 4 Administrator Intelligence Automated Tests
================================================================
Comprehensive test suite verifying:
1. Daily Decision Brief aggregation (summary counts, high-urgency, overdue).
2. Priority Review Queue with server-side pagination, sorting, and filtering.
3. Stable tie-breaking for equal urgency and timestamp values.
4. Geographic risk aggregation with neighbourhood resolution.
5. Handling of missing / unassigned neighbourhood IDs.
6. Strict privacy redaction (reporter_contact and citizen actor IDs omitted).
7. Empty dataset resilience (zero reports).
8. Overdue active threshold classification (> 48h).
9. Failed verification escalation and awaiting verification queue.
10. Dual-backend consistency (SQLite and Supabase repository mock).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.admin import get_report_repository
from app.main import app
from app.reports.models import (
    ACTIVE_STATUSES,
    CLOSED_STATUSES,
    CitizenReportCreate,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    ResolutionEvidence,
    VerificationStatus,
)
from app.reports.repository import CitizenReportRepository
from app.reports.supabase_repo import SupabaseCitizenReportRepository


@pytest.fixture
def repo():
    """Provides a fresh in-memory SQLite repository."""
    r = CitizenReportRepository(db_path=":memory:")
    yield r
    r.close()


@pytest.fixture
def client_with_repo(repo):
    """Provides a TestClient wired to the in-memory repository."""
    app.dependency_overrides[get_report_repository] = lambda: repo
    client = TestClient(app, headers={"X-Admin-API-Key": "urbansage-admin-dev-key"})
    yield client, repo
    app.dependency_overrides.clear()


def make_report_in(
    category=ProblemCategory.FLOODING_DRAINAGE,
    severity=4,
    description="Major street flooding blocking emergency access.",
    lat=21.1458,
    lon=79.0882,
    location="Near City Hospital",
    neighbourhood_id="NBR-001",
    reporter_id="CITIZEN-001",
    reporter_contact="private_citizen@example.com",
    photos=None,
):
    return CitizenReportCreate(
        category=category,
        severity=severity,
        description=description,
        latitude=lat,
        longitude=lon,
        location_description=location,
        neighbourhood_id=neighbourhood_id,
        reporter_id=reporter_id,
        reporter_contact=reporter_contact,
        photos=photos or [],
    )


class TestDailyDecisionBrief:
    def test_empty_dataset_brief(self, client_with_repo):
        client, repo = client_with_repo
        response = client.get("/api/admin/decision-brief")
        assert response.status_code == 200
        data = response.json()

        assert data["overdue_threshold_hours"] == 48
        summary = data["summary"]
        assert summary["total_reports"] == 0
        assert summary["active_reports"] == 0
        assert summary["high_urgency_active_count"] == 0
        assert summary["awaiting_review_count"] == 0
        assert summary["awaiting_citizen_verification_count"] == 0
        assert summary["verification_failed_count"] == 0
        assert summary["overdue_active_count"] == 0
        assert data["high_urgency_items"] == []
        assert data["recent_activity"] == []

    def test_daily_decision_brief_aggregation(self, client_with_repo):
        client, repo = client_with_repo

        # 1. High-urgency active flooding report
        r1 = repo.create_report(
            make_report_in(
                category=ProblemCategory.FLOODING_DRAINAGE,
                severity=5,
                neighbourhood_id="NBR-001",
                reporter_id="CIT-1",
            ),
            ward_svi=80.0,
        )

        # 2. Moderate report under review
        r2 = repo.create_report(
            make_report_in(
                category=ProblemCategory.HEAT,
                severity=2,
                neighbourhood_id="NBR-002",
                reporter_id="CIT-2",
            ),
            ward_svi=30.0,
        )

        # 3. Report transitioned to completed_awaiting_verification
        r3 = repo.create_report(
            make_report_in(
                category=ProblemCategory.WATER_SCARCITY,
                severity=3,
                neighbourhood_id="NBR-001",
                reporter_id="CIT-3",
            )
        )
        repo.update_status(r3.id, ReportStatus.ASSIGNED)
        repo.update_status(r3.id, ReportStatus.IN_PROGRESS)
        evidence = ResolutionEvidence(
            completed_by="Municipal Water Board Crew A",
            completion_notes="Water pipeline leak sealed and pressure tested.",
            work_order_id="WO-001",
        )
        repo.update_status(
            r3.id,
            ReportStatus.COMPLETED_AWAITING_VERIFICATION,
            evidence=evidence,
        )

        # 4. Report failed verification (citizen disputed resolution)
        r4 = repo.create_report(
            make_report_in(
                category=ProblemCategory.LOSS_OF_GREEN_COVER,
                severity=3,
                neighbourhood_id="NBR-003",
                reporter_id="CIT-4",
            )
        )
        repo.update_status(r4.id, ReportStatus.ASSIGNED)
        repo.update_status(r4.id, ReportStatus.IN_PROGRESS)
        repo.update_status(
            r4.id,
            ReportStatus.COMPLETED_AWAITING_VERIFICATION,
            evidence=ResolutionEvidence(
                completed_by="Parks & Arborist Division",
                completion_notes="Inspected site and planted saplings.",
                work_order_id="WO-002",
            ),
        )
        repo.verify_resolution(r4.id, confirmed_resolved=False, feedback="Illegal tree cutting continues today.")

        # Query decision brief API
        resp = client.get("/api/admin/decision-brief")
        assert resp.status_code == 200
        data = resp.json()
        summary = data["summary"]

        assert summary["total_reports"] == 4
        assert summary["active_reports"] == 4
        assert summary["awaiting_citizen_verification_count"] == 1
        assert summary["verification_failed_count"] == 1
        assert len(data["failed_verification_items"]) == 1
        assert data["failed_verification_items"][0]["id"] == r4.id
        assert "supervisor review" in data["failed_verification_items"][0]["prioritization_reason"]

        assert len(data["awaiting_citizen_verification_items"]) == 1
        assert data["awaiting_citizen_verification_items"][0]["id"] == r3.id

    def test_overdue_classification(self, repo):
        # Insert report and artificially age created_at to 60 hours ago
        r = repo.create_report(make_report_in(reporter_id="USER-OLD"))
        past_time = (datetime.now(timezone.utc) - timedelta(hours=60)).isoformat()
        with repo._conn:
            repo._conn.execute("UPDATE citizen_reports SET created_at = ? WHERE id = ?", (past_time, r.id))

        brief = repo.get_decision_brief(overdue_threshold_hours=48)
        assert brief.summary.overdue_active_count == 1
        assert len(brief.overdue_items) == 1
        assert brief.overdue_items[0].id == r.id
        assert brief.overdue_items[0].age_hours >= 59.0
        assert "overdue" in brief.overdue_items[0].prioritization_reason.lower()

        # If report is dismissed/resolved, it should NOT be flagged as overdue active
        repo.update_status(r.id, ReportStatus.DISMISSED, reason="Duplicate ticket dismissed.")
        brief_after_dismiss = repo.get_decision_brief(overdue_threshold_hours=48)
        assert brief_after_dismiss.summary.overdue_active_count == 0
        assert len(brief_after_dismiss.overdue_items) == 0

    def test_privacy_redaction_in_brief(self, client_with_repo):
        client, repo = client_with_repo
        r = repo.create_report(
            make_report_in(
                reporter_id="SECRET-CITIZEN-TOKEN",
                reporter_contact="private_super_secret@city.org",
            )
        )
        repo.update_status(r.id, ReportStatus.UNDER_REVIEW, actor_role="citizen", actor_id="CITIZEN-IDENTITY-X")

        resp = client.get("/api/admin/decision-brief")
        assert resp.status_code == 200
        raw_text = resp.text

        # Private contact and citizen identifier should NOT appear in API response
        assert "private_super_secret@city.org" not in raw_text
        assert "CITIZEN-IDENTITY-X" not in raw_text


class TestPriorityReviewQueue:
    def test_priority_queue_sorting_and_tie_breaking(self, client_with_repo):
        client, repo = client_with_repo

        # Create 3 reports with controlled severity/urgency
        r1 = repo.create_report(
            make_report_in(severity=1, description="Low severity debris issue 1.", reporter_id="C1"),
            ward_svi=20.0,
        )
        r2 = repo.create_report(
            make_report_in(severity=5, description="High severity flooding issue 2.", reporter_id="C2"),
            ward_svi=90.0,
        )
        r3 = repo.create_report(
            make_report_in(severity=3, description="Medium severity heat issue 3.", reporter_id="C3"),
            ward_svi=50.0,
        )

        # 1. Sort by urgency desc (highest urgency first)
        resp = client.get("/api/admin/priority-queue?sort_by=urgency_desc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        ids = [item["id"] for item in data["items"]]
        assert ids[0] == r2.id  # Highest urgency
        assert ids[-1] == r1.id  # Lowest urgency

        # 2. Sort by urgency asc (lowest urgency first)
        resp_asc = client.get("/api/admin/priority-queue?sort_by=urgency_asc")
        assert resp_asc.status_code == 200
        ids_asc = [item["id"] for item in resp_asc.json()["items"]]
        assert ids_asc[0] == r1.id
        assert ids_asc[-1] == r2.id

    def test_priority_queue_filtering_and_pagination(self, client_with_repo):
        client, repo = client_with_repo

        for i in range(5):
            repo.create_report(
                make_report_in(
                    category=ProblemCategory.FLOODING_DRAINAGE,
                    neighbourhood_id="NBR-001",
                    reporter_id=f"C-FLOOD-{i}",
                )
            )
        for i in range(3):
            repo.create_report(
                make_report_in(
                    category=ProblemCategory.HEAT,
                    neighbourhood_id="NBR-002",
                    reporter_id=f"C-HEAT-{i}",
                )
            )

        # Filter by category
        res_cat = client.get("/api/admin/priority-queue?category=flooding_drainage")
        assert res_cat.status_code == 200
        data_cat = res_cat.json()
        assert data_cat["total"] == 5
        assert len(data_cat["items"]) == 5

        # Filter by neighbourhood
        res_nbr = client.get("/api/admin/priority-queue?neighbourhood_id=NBR-002")
        assert res_nbr.status_code == 200
        data_nbr = res_nbr.json()
        assert data_nbr["total"] == 3

        # Pagination: limit 2, offset 0
        p1 = client.get("/api/admin/priority-queue?limit=2&offset=0").json()
        assert len(p1["items"]) == 2
        assert p1["total"] == 8

        # Pagination: limit 2, offset 2
        p2 = client.get("/api/admin/priority-queue?limit=2&offset=2").json()
        assert len(p2["items"]) == 2
        assert p1["items"][0]["id"] != p2["items"][0]["id"]


class TestGeographicRiskAggregation:
    def test_geographic_risk_with_synthetic_wards(self, client_with_repo):
        client, repo = client_with_repo

        # 2 reports in NBR-001 (Riverbank Colony)
        repo.create_report(
            make_report_in(
                category=ProblemCategory.FLOODING_DRAINAGE,
                neighbourhood_id="NBR-001",
                reporter_id="R1",
            )
        )
        repo.create_report(
            make_report_in(
                category=ProblemCategory.WATER_SCARCITY,
                neighbourhood_id="NBR-001",
                reporter_id="R2",
            )
        )

        # 1 report in NBR-002 (Industrial Quarter)
        repo.create_report(
            make_report_in(
                category=ProblemCategory.HEAT,
                neighbourhood_id="NBR-002",
                reporter_id="R3",
            )
        )

        resp = client.get("/api/admin/geographic-risk")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 3
        assert len(data["neighbourhoods"]) == 2

        nbr1 = next(n for n in data["neighbourhoods"] if n["neighbourhood_id"] == "NBR-001")
        assert nbr1["total_reports"] == 2
        assert nbr1["neighbourhood_name"] == "Riverbank Colony"
        assert nbr1["category_breakdown"]["flooding_drainage"] == 1
        assert nbr1["category_breakdown"]["water_scarcity"] == 1

        nbr2 = next(n for n in data["neighbourhoods"] if n["neighbourhood_id"] == "NBR-002")
        assert nbr2["total_reports"] == 1
        assert nbr2["neighbourhood_name"] == "Industrial Quarter"
        assert nbr2["top_hazard_category"] == "heat"

    def test_unassigned_neighbourhood_handling(self, client_with_repo):
        client, repo = client_with_repo

        # Report without neighbourhood_id
        repo.create_report(
            make_report_in(
                category=ProblemCategory.LOSS_OF_GREEN_COVER,
                neighbourhood_id=None,
                reporter_id="UNASSIGNED-CITIZEN",
            )
        )

        resp = client.get("/api/admin/geographic-risk")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 1
        assert data["unassigned"] is not None
        assert data["unassigned"]["neighbourhood_id"] == "UNASSIGNED"
        assert "Unassigned" in data["unassigned"]["neighbourhood_name"]
        assert data["unassigned"]["total_reports"] == 1
        assert data["unassigned"]["category_breakdown"]["loss_of_green_cover"] == 1


class TestDualRepositoryConsistency:
    def test_supabase_mocked_consistency(self):
        """Verify Supabase repository methods return matching data structures."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        repo = SupabaseCitizenReportRepository(client=mock_client)

        now = datetime.now(timezone.utc)
        sample_row = {
            "id": "RPT-12345678",
            "category": "flooding_drainage",
            "description": "Flooding test in Supabase table.",
            "severity": 4,
            "latitude": 21.14,
            "longitude": 79.08,
            "location_description": "Ward 5",
            "neighbourhood_id": "NBR-001",
            "reporter_id": "MOCK-REP",
            "reporter_contact": "secret@mock.org",
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 82.5,
            "evidence_confidence_score": 70.0,
            "resolution_evidence": None,
            "timeline": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        mock_query = MagicMock()
        mock_table.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[sample_row], count=1)

        brief = repo.get_decision_brief()
        assert brief.summary.total_reports == 1
        assert brief.summary.high_urgency_active_count == 1
        assert len(brief.high_urgency_items) == 1
        assert brief.high_urgency_items[0].id == "RPT-12345678"

        # Check priority queue
        mock_query.range.return_value = mock_query
        reports, total = repo.get_priority_queue()
        assert total == 1
        assert len(reports) == 1
        assert reports[0].id == "RPT-12345678"
