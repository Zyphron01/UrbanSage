"""
UrbanSage AI — Report Lifecycle & Resolution Evidence Test Suite (Stage 3)
===========================================================================
Verifies the complete end-to-end operational lifecycle:
    SUBMITTED -> REVIEW -> ASSIGNMENT -> WORK COMPLETED -> CITIZEN VERIFICATION -> RESOLUTION

Tests:
------
1. Valid transitions across the 14-state machine.
2. Illegal transition rejection (e.g. submitted -> verified_resolved directly).
3. Resolution evidence validation and attachment on work completion.
4. Citizen confirmation (verified_resolved) and citizen dispute/rejection (verification_failed).
5. Queue routing upon failed verification back to municipal team.
6. Additional evidence submission loop (under_review -> info_requested -> citizen evidence -> under_review).
7. Immutable audit timeline logging with timestamps, actor roles, and reasons.
8. Privacy preservation (citizen actor_id redaction in public view).
9. REST API endpoints:
   - PATCH /api/reports/{id}/status
   - POST  /api/reports/{id}/verify
   - POST  /api/reports/{id}/evidence
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reports.exceptions import (
    InvalidStatusTransitionError,
    ReportNotFoundError,
    ReportValidationError,
)
from app.reports.models import (
    AdditionalEvidencePayload,
    CitizenReportCreate,
    CitizenVerificationPayload,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    ReportStatusUpdate,
    ResolutionEvidence,
    VerificationStatus,
    validate_status_transition,
)
from app.reports.factory import get_report_repository
from app.reports.repository import CitizenReportRepository


@pytest.fixture
def memory_repo() -> CitizenReportRepository:
    """Fixture providing a clean in-memory SQLite repository for each test."""
    return CitizenReportRepository(db_path=":memory:")


@pytest.fixture
def sample_report_payload() -> CitizenReportCreate:
    """Fixture providing a valid report creation payload."""
    return CitizenReportCreate(
        category=ProblemCategory.FLOODING_DRAINAGE,
        description="Storm drain completely clogged at 5th Main causing severe waterlogging.",
        severity=4,
        latitude=12.9716,
        longitude=77.5946,
        location_description="5th Main, Indiranagar",
        neighbourhood_id="NBR-001",
        reporter_id="CITIZEN-101",
        reporter_contact="citizen101@example.com",
    )


class TestLifecycleStateMachine:
    """Tests the state transition validation logic."""

    def test_valid_sequential_transitions(self):
        """Validate standard progression paths."""
        # Standard administrative review
        validate_status_transition(ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW)
        validate_status_transition(ReportStatus.UNDER_REVIEW, ReportStatus.VERIFIED)
        validate_status_transition(ReportStatus.VERIFIED, ReportStatus.ASSIGNED)
        validate_status_transition(ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS)
        validate_status_transition(ReportStatus.IN_PROGRESS, ReportStatus.COMPLETED_AWAITING_VERIFICATION)
        validate_status_transition(ReportStatus.COMPLETED_AWAITING_VERIFICATION, ReportStatus.VERIFIED_RESOLVED)

    def test_direct_illegal_transitions_rejected(self):
        """Direct skips that bypass verification or work completion must be rejected."""
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            validate_status_transition(ReportStatus.SUBMITTED, ReportStatus.VERIFIED_RESOLVED)
        assert "not permitted" in str(exc_info.value)

        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(ReportStatus.SUBMITTED, ReportStatus.COMPLETED_AWAITING_VERIFICATION)

        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(ReportStatus.VERIFIED, ReportStatus.VERIFIED_RESOLVED)

    def test_terminal_states_reject_transitions(self):
        """Confirmed fake, duplicate, and out of scope reports cannot transition."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(ReportStatus.CONFIRMED_FAKE, ReportStatus.ASSIGNED)

        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(ReportStatus.DUPLICATE, ReportStatus.IN_PROGRESS)

        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(ReportStatus.OUT_OF_SCOPE, ReportStatus.VERIFIED)


class TestRepositoryReportLifecycle:
    """Tests lifecycle persistence, transitions, and evidence logging in repository."""

    def test_full_resolution_workflow(self, memory_repo, sample_report_payload):
        """End-to-end test of the complete lifecycle through to verified resolution."""
        # 1. Citizen submits report
        report = memory_repo.create_report(sample_report_payload)
        assert report.status == ReportStatus.SUBMITTED
        assert len(report.timeline) == 1
        assert report.timeline[0].from_status == ReportStatus.SUBMITTED

        # 2. Administrator reviews report
        reviewed = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.UNDER_REVIEW,
            actor_role="administrator",
            actor_id="admin_user_1",
            reason="Initial triage by municipal control room.",
        )
        assert reviewed.status == ReportStatus.UNDER_REVIEW
        assert len(reviewed.timeline) == 2

        # 3. Administrator verifies report
        verified = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.VERIFIED,
            actor_role="administrator",
            actor_id="admin_user_1",
            reason="Cross-referenced with drainage zone map.",
        )
        assert verified.status == ReportStatus.VERIFIED

        # 4. Administrator assigns report to field contractor
        assigned = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.ASSIGNED,
            actor_role="administrator",
            actor_id="admin_user_1",
            reason="Assigned to Ward 10 Drainage Maintenance Team.",
        )
        assert assigned.status == ReportStatus.ASSIGNED

        # 5. Contractor starts work
        in_progress = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.IN_PROGRESS,
            actor_role="contractor",
            actor_id="contractor_team_4",
            reason="Excavator deployed on site.",
        )
        assert in_progress.status == ReportStatus.IN_PROGRESS

        # 6. Work completed with photographic resolution evidence
        evidence = ResolutionEvidence(
            completed_by="Ward 10 Drainage Maintenance Team",
            completion_notes="Cleared 40 meters of blocked storm drain and installed new debris grate.",
            evidence_photos=[
                PhotoMetadata(
                    photo_id="PHO-ABC12345",
                    file_name="drain_cleared_after.jpg",
                    mime_type="image/jpeg",
                    size_bytes=1024000,
                    caption="Completed drain desilting",
                )
            ],
        )
        completed = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.COMPLETED_AWAITING_VERIFICATION,
            actor_role="contractor",
            actor_id="contractor_team_4",
            reason="Remediation work fully executed.",
            evidence=evidence,
        )
        assert completed.status == ReportStatus.COMPLETED_AWAITING_VERIFICATION
        assert completed.resolution_evidence is not None
        assert completed.resolution_evidence.completed_by == "Ward 10 Drainage Maintenance Team"
        assert completed.resolution_evidence.citizen_confirmed is None

        # 7. Citizen confirms resolution
        resolved = memory_repo.verify_resolution(
            report_id=report.id,
            confirmed_resolved=True,
            feedback="Water has completely drained and road is clear. Thank you!",
            actor_id="CITIZEN-101",
        )
        assert resolved.status == ReportStatus.VERIFIED_RESOLVED
        assert resolved.verification_status == VerificationStatus.OFFICIALLY_VERIFIED
        assert resolved.resolution_evidence.citizen_confirmed is True
        assert "Thank you" in resolved.resolution_evidence.citizen_feedback
        assert len(resolved.timeline) == 7

    def test_completion_without_evidence_rejected(self, memory_repo, sample_report_payload):
        """Marking work completed awaiting verification requires valid resolution evidence."""
        report = memory_repo.create_report(sample_report_payload)
        memory_repo.update_status(report.id, ReportStatus.ASSIGNED)

        with pytest.raises(ReportValidationError) as exc:
            memory_repo.update_status(
                report_id=report.id,
                status=ReportStatus.COMPLETED_AWAITING_VERIFICATION,
                evidence=None,
            )
        assert "evidence is required" in str(exc.value).lower()

    def test_citizen_rejection_returns_to_municipal_queue(self, memory_repo, sample_report_payload):
        """When citizen reports problem remains unresolved, status moves to verification_failed."""
        report = memory_repo.create_report(sample_report_payload)
        memory_repo.update_status(report.id, ReportStatus.ASSIGNED)

        evidence = ResolutionEvidence(
            completed_by="Roads Department",
            completion_notes="Pothole patched with cold asphalt mix.",
        )
        memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.COMPLETED_AWAITING_VERIFICATION,
            evidence=evidence,
        )

        # Citizen rejects resolution
        disputed = memory_repo.verify_resolution(
            report_id=report.id,
            confirmed_resolved=False,
            feedback="Only half the pothole was patched; rainwater still pools across two lanes.",
            actor_id="CITIZEN-101",
        )
        assert disputed.status == ReportStatus.VERIFICATION_FAILED
        assert disputed.resolution_evidence.citizen_confirmed is False
        assert "rainwater still pools" in disputed.resolution_evidence.citizen_feedback

        # Municipal coordinator returns ticket to field team for re-work
        reopened = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.IN_PROGRESS,
            actor_role="administrator",
            actor_id="admin_supervisor",
            reason="Dispatched second crew to complete edge patching per citizen feedback.",
        )
        assert reopened.status == ReportStatus.IN_PROGRESS

    def test_additional_evidence_request_cycle(self, memory_repo, sample_report_payload):
        """Test cycle where reviewer requests additional information and citizen provides it."""
        report = memory_repo.create_report(sample_report_payload)

        # Admin requests info
        info_req = memory_repo.update_status(
            report_id=report.id,
            status=ReportStatus.INFO_REQUESTED,
            reason="Please provide a photo of the manhole cover location.",
        )
        assert info_req.status == ReportStatus.INFO_REQUESTED

        # Citizen provides additional photo and note
        new_photo = PhotoMetadata(
            photo_id="PHO-98765432",
            file_name="manhole_closeup.png",
            mime_type="image/png",
            size_bytes=512000,
            caption="Closeup of broken manhole rim",
        )
        updated = memory_repo.add_additional_evidence(
            report_id=report.id,
            additional_notes="Uploaded closeup showing the exact damaged rim opposite bakery.",
            photos=[new_photo],
            actor_id="CITIZEN-101",
        )
        # Should transition back to under_review automatically
        assert updated.status == ReportStatus.UNDER_REVIEW
        assert len(updated.photos) == 1
        assert "Additional Citizen Evidence" in updated.description


class TestLifecycleAPIEndpoints:
    """Tests the REST API endpoints for lifecycle transitions."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Ensure API tests run against isolated in-memory repository."""
        test_repo = CitizenReportRepository(db_path=":memory:")
        app.dependency_overrides[get_report_repository] = lambda: test_repo
        self.client = TestClient(app, headers={"X-Admin-API-Key": "urbansage-admin-dev-key"})
        self.repo = test_repo
        yield
        app.dependency_overrides.clear()
        test_repo.close()

    def test_api_status_update_and_privacy_redaction(self, sample_report_payload):
        """Test PATCH /api/reports/{id}/status and verify citizen actor_id is redacted in public response."""
        created = self.repo.create_report(sample_report_payload)

        # Update status to UNDER_REVIEW
        res = self.client.patch(
            f"/api/reports/{created.id}/status",
            json={
                "status": "under_review",
                "actor_role": "administrator",
                "actor_id": "officer_sharma",
                "reason": "Control room assigned priority 1.",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "under_review"

        # Verify timeline privacy: citizen initial submission actor_id must be None in public view
        timeline = data["timeline"]
        assert len(timeline) == 2
        citizen_log = [t for t in timeline if t["actor_role"] == "citizen"][0]
        assert citizen_log["actor_id"] is None, "Citizen actor_id must be redacted in public response"

        # Admin officer actor_id remains visible for transparency
        admin_log = [t for t in timeline if t["actor_role"] == "administrator"][0]
        assert admin_log["actor_id"] == "officer_sharma"

    def test_api_citizen_verify_endpoint(self, sample_report_payload):
        """Test POST /api/reports/{id}/verify endpoint."""
        created = self.repo.create_report(sample_report_payload)
        self.repo.update_status(created.id, ReportStatus.ASSIGNED)
        self.repo.update_status(
            created.id,
            ReportStatus.COMPLETED_AWAITING_VERIFICATION,
            evidence=ResolutionEvidence(
                completed_by="Parks Dept",
                completion_notes="Fallen branch cleared and disposed.",
            ),
        )

        # Citizen verifies resolution via API
        res = self.client.post(
            f"/api/reports/{created.id}/verify",
            json={
                "confirmed_resolved": True,
                "feedback": "Branch is gone, road is safe. Great job!",
                "actor_id": "CITIZEN-101",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "verified_resolved"
        assert body["verification_status"] == "officially_verified"
        assert body["resolution_evidence"]["citizen_confirmed"] is True

    def test_api_additional_evidence_endpoint(self, sample_report_payload):
        """Test POST /api/reports/{id}/evidence endpoint."""
        created = self.repo.create_report(sample_report_payload)
        self.repo.update_status(created.id, ReportStatus.INFO_REQUESTED)

        res = self.client.post(
            f"/api/reports/{created.id}/evidence",
            json={
                "additional_notes": "Street light number opposite the flood is SL-402.",
                "photos": [],
                "actor_id": "CITIZEN-101",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "under_review"
        assert "SL-402" in body["description"]

    def test_api_invalid_transition_returns_422(self, sample_report_payload):
        """Illegal transition via API must return HTTP 422 Unprocessable Entity."""
        created = self.repo.create_report(sample_report_payload)

        res = self.client.patch(
            f"/api/reports/{created.id}/status",
            json={
                "status": "verified_resolved",  # Illegal direct skip from submitted
                "actor_role": "administrator",
            },
        )
        assert res.status_code == 422
        assert "not permitted" in res.json()["detail"]
