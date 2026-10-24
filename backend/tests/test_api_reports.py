"""
test_api_reports.py — API Integration Tests for Citizen Reporting
==================================================================
Tests for FastAPI citizen reporting endpoints and application lifecycle:
1. Health endpoint.
2. Valid report submission.
3. Invalid category or coordinates.
4. Missing required fields.
5. Successful retrieval of a report.
6. Retrieval of a nonexistent report.
7. Report listing and pagination.
8. Category and status filtering.
9. Duplicate-conflict handling (HTTP 409).
10. Persistence across repository reopening.
11. Privacy: contact information is never exposed in responses.
12. Generic handling of unexpected persistence errors (HTTP 500 without leaking internals).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.reports import get_report_repository
from app.main import app
from app.reports.exceptions import ReportPersistenceError
from app.reports.models import ProblemCategory, ReportStatus
from app.reports.repository import CitizenReportRepository


@pytest.fixture
def client_with_memory_repo():
    """Provides a TestClient wired to an isolated in-memory SQLite repository."""
    repo = CitizenReportRepository(db_path=":memory:")
    app.dependency_overrides[get_report_repository] = lambda: repo
    client = TestClient(app)
    yield client, repo
    app.dependency_overrides.clear()
    repo.close()


def make_valid_payload(**overrides) -> dict:
    base = {
        "category": "flooding_drainage",
        "description": "Main street underpass is completely flooded after heavy rain.",
        "severity": 4,
        "latitude": 21.1458,
        "longitude": 79.0882,
        "location_description": "Underpass near City Center",
        "neighbourhood_id": "NBR-001",
        "reporter_id": "CITIZEN-USER-1",
        "reporter_contact": "secret_email@example.org",
        "photos": [],
    }
    base.update(overrides)
    return base


# ===========================================================================
# 1. Health Endpoint
# ===========================================================================


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "UrbanSage AI API"
    assert "timestamp" in data


# ===========================================================================
# 2. Valid Report Submission
# ===========================================================================


def test_valid_report_submission(client_with_memory_repo):
    client, repo = client_with_memory_repo
    payload = make_valid_payload()
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("RPT-")
    assert data["category"] == "flooding_drainage"
    assert data["severity"] == 4
    assert data["status"] == "submitted"
    assert data["verification_status"] == "unverified"
    assert data["is_verified_measurement"] is False
    assert data["data_source"] == "CITIZEN_REPORT"
    assert 0.0 <= data["urgency_score"] <= 100.0
    assert 0.0 <= data["evidence_confidence_score"] <= 100.0


# ===========================================================================
# 3. Invalid Category and Coordinates Validation
# ===========================================================================


def test_invalid_category_rejected(client_with_memory_repo):
    client, _ = client_with_memory_repo
    payload = make_valid_payload(category="industrial_chemical_leak")
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 422


def test_invalid_coordinates_rejected(client_with_memory_repo):
    client, _ = client_with_memory_repo
    # Latitude > 90
    response = client.post("/api/reports", json=make_valid_payload(latitude=95.0))
    assert response.status_code == 422

    # Longitude < -180
    response = client.post("/api/reports", json=make_valid_payload(longitude=-185.0))
    assert response.status_code == 422


# ===========================================================================
# 4. Missing Required Fields
# ===========================================================================


def test_missing_required_fields_rejected(client_with_memory_repo):
    client, _ = client_with_memory_repo
    payload = make_valid_payload()
    del payload["description"]
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 422


# ===========================================================================
# 5 & 6. Retrieval of Reports (Success & 404)
# ===========================================================================


def test_successful_report_retrieval(client_with_memory_repo):
    client, _ = client_with_memory_repo
    create_res = client.post("/api/reports", json=make_valid_payload())
    report_id = create_res.json()["id"]

    get_res = client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == report_id


def test_retrieval_of_nonexistent_report_returns_404(client_with_memory_repo):
    client, _ = client_with_memory_repo
    response = client.get("/api/reports/RPT-00000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ===========================================================================
# 7 & 8. Report Listing, Pagination, and Filtering
# ===========================================================================


def test_report_listing_and_pagination(client_with_memory_repo):
    client, _ = client_with_memory_repo
    # Seed 5 reports
    for i in range(5):
        client.post(
            "/api/reports",
            json=make_valid_payload(
                reporter_id=f"USER-{i}",
                description=f"Unique environmental issue number {i} on the road.",
            ),
        )

    # Page 1: limit 2, offset 0
    res1 = client.get("/api/reports?limit=2&offset=0")
    assert res1.status_code == 200
    page1 = res1.json()
    assert page1["total"] == 5
    assert page1["limit"] == 2
    assert page1["offset"] == 0
    assert len(page1["items"]) == 2

    # Page 2: limit 2, offset 2
    res2 = client.get("/api/reports?limit=2&offset=2")
    assert res2.status_code == 200
    page2 = res2.json()
    assert len(page2["items"]) == 2
    assert page1["items"][0]["id"] != page2["items"][0]["id"]


def test_filtering_by_category_and_status(client_with_memory_repo):
    client, _ = client_with_memory_repo
    client.post(
        "/api/reports",
        json=make_valid_payload(category="heat", reporter_id="USER-HEAT"),
    )
    client.post(
        "/api/reports",
        json=make_valid_payload(category="flooding_drainage", reporter_id="USER-FLOOD"),
    )

    # Filter by category
    res = client.get("/api/reports?category=heat")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "heat"

    # Filter by status
    res_status = client.get("/api/reports?status=submitted")
    assert res_status.status_code == 200
    assert len(res_status.json()["items"]) == 2


# ===========================================================================
# 9. Duplicate-Conflict Handling (HTTP 409)
# ===========================================================================


def test_duplicate_submission_returns_409(client_with_memory_repo):
    client, _ = client_with_memory_repo
    payload = make_valid_payload(reporter_id="SPAMMER-1")

    # First succeeds (201)
    res1 = client.post("/api/reports", json=payload)
    assert res1.status_code == 201

    # Immediate duplicate from same reporter in same category returns 409
    res2 = client.post("/api/reports", json=payload)
    assert res2.status_code == 409
    assert "duplicate" in res2.json()["detail"].lower()


# ===========================================================================
# 10. Persistence Across Repository Reopening
# ===========================================================================


def test_persistence_across_reopening(tmp_path: Path):
    db_path = str(tmp_path / "api_test_store.db")

    # Instance 1: write report
    repo1 = CitizenReportRepository(db_path=db_path)
    app.dependency_overrides[get_report_repository] = lambda: repo1
    client1 = TestClient(app)

    create_res = client1.post("/api/reports", json=make_valid_payload())
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]
    repo1.close()

    # Instance 2: reopen store and query
    repo2 = CitizenReportRepository(db_path=db_path)
    app.dependency_overrides[get_report_repository] = lambda: repo2
    client2 = TestClient(app)

    get_res = client2.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == report_id
    assert get_res.json()["description"] == make_valid_payload()["description"]

    app.dependency_overrides.clear()
    repo2.close()


# ===========================================================================
# 11. Privacy: Contact Information Never Exposed
# ===========================================================================


def test_privacy_contact_and_reporter_identity_not_exposed(client_with_memory_repo):
    client, _ = client_with_memory_repo
    secret_contact = "confidential_citizen_99@private.org"
    secret_reporter = "private_token_user_xyz"
    payload = make_valid_payload(
        reporter_contact=secret_contact,
        reporter_id=secret_reporter,
    )

    # 1. POST response must not leak contact or reporter ID
    post_res = client.post("/api/reports", json=payload)
    assert post_res.status_code == 201
    assert "reporter_contact" not in post_res.json()
    assert "reporter_id" not in post_res.json()
    assert secret_contact not in str(post_res.json())
    assert secret_reporter not in str(post_res.json())

    report_id = post_res.json()["id"]

    # 2. GET by ID must not leak contact or reporter ID
    get_res = client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert "reporter_contact" not in get_res.json()
    assert "reporter_id" not in get_res.json()
    assert secret_contact not in str(get_res.json())
    assert secret_reporter not in str(get_res.json())

    # 3. GET list must not leak contact or reporter ID
    list_res = client.get("/api/reports")
    assert list_res.status_code == 200
    for item in list_res.json()["items"]:
        assert "reporter_contact" not in item
        assert "reporter_id" not in item
        assert secret_contact not in str(item)
        assert secret_reporter not in str(item)


# ===========================================================================
# 12. Generic Handling of Persistence Errors (HTTP 500)
# ===========================================================================


def test_persistence_error_returns_generic_500():
    mock_repo = MagicMock()
    mock_repo.create_report.side_effect = ReportPersistenceError("Internal sqlite disk I/O sector corruption")
    app.dependency_overrides[get_report_repository] = lambda: mock_repo

    client = TestClient(app)
    response = client.post("/api/reports", json=make_valid_payload())
    assert response.status_code == 500
    # Must NOT leak internal database/sector details to client
    detail = response.json()["detail"]
    assert "disk I/O" not in detail
    assert "sqlite" not in detail.lower()
    assert "error" in detail.lower()

    app.dependency_overrides.clear()
