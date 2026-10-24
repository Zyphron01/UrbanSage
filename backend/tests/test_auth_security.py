"""
UrbanSage AI — Security, Authentication & Role-Based Access Control (RBAC) Tests
================================================================================
Comprehensive automated tests verifying:
1. Strict server-side authentication on administrator-only endpoints.
2. Protection of report-status modification and privileged operations.
3. Proper 401 Unauthorized responses for missing, expired, or forged tokens.
4. Proper 403 Forbidden responses when citizens attempt privileged operations.
5. Role enforcement:
   - administrator: full access to admin intelligence and status mutations
   - contractor: access to status mutations / evidence submission, but blocked from admin briefs
   - citizen: restricted to reporting, viewing public reports, and resolution verification
6. Safe dev fallback via X-Admin-API-Key and JWT bearer token issuance.
7. Public endpoints (reporting, public view, health probe) remain accessible without credentials.
"""

from __future__ import annotations

import time
import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.admin import get_report_repository
from app.auth import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    decode_access_token,
)
from app.main import app
from app.reports.models import CitizenReportCreate, ProblemCategory
from app.reports.repository import CitizenReportRepository


@pytest.fixture
def repo():
    """In-memory SQLite repository for isolated testing."""
    r = CitizenReportRepository(db_path=":memory:")
    yield r
    r.close()


@pytest.fixture
def client(repo):
    """TestClient wired to isolated in-memory repository without default auth headers."""
    app.dependency_overrides[get_report_repository] = lambda: repo
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_report_id(repo):
    """Creates a sample report and returns its ID."""
    created = repo.create_report(
        CitizenReportCreate(
            category=ProblemCategory.FLOODING_DRAINAGE,
            severity=4,
            description="Flooded underpass requiring municipal pump assignment.",
            latitude=12.9716,
            longitude=77.5946,
            location_description="Majestic Underpass",
            neighbourhood_id="NBR-001",
            reporter_id="CITIZEN-999",
            reporter_contact="citizen@example.com",
            photos=[],
        )
    )
    return created.id


class TestAuthenticationEnforcement:
    """Verifies that unauthenticated callers are rejected with HTTP 401."""

    def test_admin_decision_brief_requires_auth(self, client):
        res = client.get("/api/admin/decision-brief")
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

    def test_admin_priority_queue_requires_auth(self, client):
        res = client.get("/api/admin/priority-queue")
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

    def test_admin_geographic_risk_requires_auth(self, client):
        res = client.get("/api/admin/geographic-risk")
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

    def test_report_status_patch_requires_auth(self, client, sample_report_id):
        res = client.patch(
            f"/api/reports/{sample_report_id}/status",
            json={
                "status": "under_review",
                "actor_role": "administrator",
                "actor_id": "rogue_actor",
                "reason": "Unauthenticated attempt to change status",
            },
        )
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

    def test_invalid_bearer_token_returns_401(self, client):
        headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 401
        assert "Invalid authentication token" in res.json()["detail"]

    def test_token_with_wrong_secret_returns_401(self, client):
        fake_token = jwt.encode(
            {"sub": "attacker", "role": "administrator", "exp": time.time() + 3600},
            "completely-wrong-secret-key-12345678",
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {fake_token}"}
        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 401
        assert "Invalid authentication token" in res.json()["detail"]

    def test_expired_token_returns_401(self, client):
        expired_token = jwt.encode(
            {"sub": "expired_admin", "role": "administrator", "exp": time.time() - 3600},
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 401
        assert "Authentication token has expired" in res.json()["detail"]


class TestRoleBasedAccessControl:
    """Verifies that authenticated users with insufficient privileges receive HTTP 403."""

    def test_citizen_role_forbidden_from_admin_endpoints(self, client):
        citizen_token = create_access_token(user_id="CITIZEN-101", role="citizen")
        headers = {"Authorization": f"Bearer {citizen_token}"}

        # Decision brief
        res1 = client.get("/api/admin/decision-brief", headers=headers)
        assert res1.status_code == 403
        assert "requires 'administrator' role" in res1.json()["detail"]

        # Priority review queue
        res2 = client.get("/api/admin/priority-queue", headers=headers)
        assert res2.status_code == 403
        assert "requires 'administrator' role" in res2.json()["detail"]

        # Geographic risk
        res3 = client.get("/api/admin/geographic-risk", headers=headers)
        assert res3.status_code == 403
        assert "requires 'administrator' role" in res3.json()["detail"]

    def test_citizen_role_forbidden_from_modifying_status(self, client, sample_report_id):
        citizen_token = create_access_token(user_id="CITIZEN-101", role="citizen")
        headers = {"Authorization": f"Bearer {citizen_token}"}

        res = client.patch(
            f"/api/reports/{sample_report_id}/status",
            headers=headers,
            json={
                "status": "resolved",
                "actor_role": "citizen",
                "actor_id": "CITIZEN-101",
                "reason": "Citizen trying to self-resolve report without municipal verification",
            },
        )
        assert res.status_code == 403
        assert "requires 'contractor' or 'administrator' role" in res.json()["detail"]

    def test_contractor_forbidden_from_admin_intelligence(self, client):
        contractor_token = create_access_token(user_id="CONTRACTOR-501", role="contractor")
        headers = {"Authorization": f"Bearer {contractor_token}"}

        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 403
        assert "requires 'administrator' role" in res.json()["detail"]

    def test_contractor_allowed_to_update_operational_status(self, client, sample_report_id):
        contractor_token = create_access_token(user_id="CONTRACTOR-501", role="contractor")
        headers = {"Authorization": f"Bearer {contractor_token}"}

        # Admin assigns the work first (SUBMITTED -> ASSIGNED)
        admin_token = create_access_token(user_id="ADMIN-001", role="administrator")
        client.patch(
            f"/api/reports/{sample_report_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "assigned", "actor_role": "administrator", "actor_id": "ADMIN-001"},
        )

        # Contractor transitions ASSIGNED -> IN_PROGRESS
        res = client.patch(
            f"/api/reports/{sample_report_id}/status",
            headers=headers,
            json={
                "status": "in_progress",
                "actor_role": "contractor",
                "actor_id": "CONTRACTOR-501",
                "reason": "Field team dispatched on site.",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"


class TestAdminAuthorizationSuccess:
    """Verifies that legitimate administrators can successfully access all privileged endpoints."""

    def test_admin_jwt_accesses_decision_brief(self, client):
        admin_token = create_access_token(user_id="ADMIN-001", role="administrator")
        headers = {"Authorization": f"Bearer {admin_token}"}

        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 200
        assert "summary" in res.json()

    def test_api_key_header_accesses_admin_endpoints(self, client):
        headers = {"X-Admin-API-Key": "urbansage-admin-dev-key"}
        res = client.get("/api/admin/decision-brief", headers=headers)
        assert res.status_code == 200
        assert "summary" in res.json()

    def test_admin_jwt_modifies_report_status(self, client, sample_report_id):
        admin_token = create_access_token(user_id="OFFICER-42", role="administrator")
        headers = {"Authorization": f"Bearer {admin_token}"}

        res = client.patch(
            f"/api/reports/{sample_report_id}/status",
            headers=headers,
            json={
                "status": "under_review",
                "actor_role": "administrator",
                "actor_id": "OFFICER-42",
                "reason": "Authorized officer triaged priority 1 incident.",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "under_review"


class TestTokenEndpoint:
    """Verifies the /api/auth/token endpoint for issuing authentication tokens."""

    def test_issue_admin_token(self, client):
        res = client.post(
            "/api/auth/token",
            json={"user_id": "ADMIN-99", "role": "administrator", "expires_in_hours": 12},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "administrator"

        # Verify decoded payload
        payload = decode_access_token(data["access_token"])
        assert payload.user_id == "ADMIN-99"
        assert payload.role == "administrator"

    def test_issue_contractor_token(self, client):
        res = client.post(
            "/api/auth/token",
            json={"user_id": "CONTRACTOR-88", "role": "contractor"},
        )
        assert res.status_code == 200
        data = res.json()
        payload = decode_access_token(data["access_token"])
        assert payload.role == "contractor"


class TestPublicEndpointAccessibility:
    """Confirms that public citizen endpoints remain functional without requiring authentication."""

    def test_health_check_public(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_report_submission_public(self, client):
        res = client.post(
            "/api/reports",
            json={
                "category": "flooding_drainage",
                "severity": 3,
                "description": "Public street water logging reported by local resident.",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "location_description": "MG Road",
                "neighbourhood_id": "NBR-001",
                "reporter_id": "CITIZEN-PUBLIC",
                "reporter_contact": "resident@example.com",
            },
        )
        assert res.status_code == 201

    def test_public_reports_listing_public(self, client):
        res = client.get("/api/reports")
        assert res.status_code == 200

    def test_public_report_detail_public(self, client, sample_report_id):
        res = client.get(f"/api/reports/{sample_report_id}")
        assert res.status_code == 200
        assert "reporter_contact" not in res.json()
