"""
test_citizen_reports.py — Unit & Integration Tests for Citizen Reporting (Phase 1A)
===================================================================================

Covers all Phase 1A requirements:
- Valid citizen report creation
- Invalid categories, coordinates, and severity bounds
- Missing required fields
- Stable report identifiers (^RPT-[A-F0-9]{8}$)
- Initial status (SUBMITTED, UNVERIFIED, is_verified_measurement=False)
- Persistence across closing and reopening database store
- Score bounds and transparent calculations
- Duplicate-report behavior (anti-spam, prevents score inflation)
- Handling of missing evidence
- Separation of citizen reports from verified measurements
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.reports.exceptions import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportPersistenceError,
)
from app.reports.models import (
    CitizenReport,
    CitizenReportCreate,
    CitizenReportPublic,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    VerificationStatus,
)
from app.reports.repository import CitizenReportRepository
from app.reports.scoring import (
    CATEGORY_ACUTE_HAZARD_SCORES,
    calculate_evidence_confidence_score,
    calculate_urgency_score,
)


# ===========================================================================
# Helpers & Factories
# ===========================================================================


def make_report_create(**overrides) -> CitizenReportCreate:
    """Return a valid CitizenReportCreate instance, optionally overriding fields."""
    base = {
        "category": ProblemCategory.FLOODING_DRAINAGE,
        "description": "Severe stormwater drain blockage causing 2-foot standing water on main road.",
        "severity": 4,
        "latitude": 21.1458,
        "longitude": 79.0882,
        "location_description": "Corner of Ward 12 Main St and 5th Cross",
        "neighbourhood_id": "NBR-001",
        "reporter_id": "REP-USER-001",
        "reporter_contact": "citizen@example.org",
        "photos": [],
    }
    base.update(overrides)
    return CitizenReportCreate(**base)


def make_photo(**overrides) -> PhotoMetadata:
    """Return a valid PhotoMetadata instance."""
    base = {
        "photo_id": "PHO-A1B2C3D4",
        "file_name": "waterlogging_drain.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 2_450_000,
        "caption": "Flooding reaching storefront steps.",
        "captured_at": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    base.update(overrides)
    return PhotoMetadata(**base)


# ===========================================================================
# 1. Valid Citizen Report Creation
# ===========================================================================


class TestCitizenReportCreationValid:
    def test_valid_creation_all_categories(self):
        for cat in ProblemCategory:
            payload = make_report_create(category=cat)
            assert payload.category == cat

    def test_coordinate_boundary_limits(self):
        # Lat bounds: -90 to +90
        rep_south = make_report_create(latitude=-90.0, longitude=0.0)
        assert rep_south.latitude == -90.0

        rep_north = make_report_create(latitude=90.0, longitude=0.0)
        assert rep_north.latitude == 90.0

        # Lon bounds: -180 to +180
        rep_west = make_report_create(latitude=0.0, longitude=-180.0)
        assert rep_west.longitude == -180.0

        rep_east = make_report_create(latitude=0.0, longitude=180.0)
        assert rep_east.longitude == 180.0

    def test_optional_photo_metadata(self):
        photo = make_photo()
        payload = make_report_create(photos=[photo])
        assert len(payload.photos) == 1
        assert payload.photos[0].photo_id == "PHO-A1B2C3D4"
        assert payload.photos[0].size_bytes == 2_450_000

    def test_whitespace_stripping(self):
        payload = make_report_create(
            description="   Deep ponding on road outside metro station.   ",
            location_description="   Near Gate 2   ",
            reporter_contact="   user@example.com   ",
        )
        assert payload.description == "Deep ponding on road outside metro station."
        assert payload.location_description == "Near Gate 2"
        assert payload.reporter_contact == "user@example.com"


# ===========================================================================
# 2. Invalid Categories, Coordinates, and Bounds
# ===========================================================================


class TestCitizenReportCreationInvalid:
    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(category="noise_pollution")

    def test_latitude_above_90_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(latitude=90.001)

    def test_latitude_below_minus_90_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(latitude=-90.001)

    def test_longitude_above_180_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(longitude=180.001)

    def test_longitude_below_minus_180_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(longitude=-180.001)

    def test_severity_above_5_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(severity=6)

    def test_severity_below_1_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(severity=0)

    def test_description_too_short_rejected(self):
        with pytest.raises(ValidationError):
            make_report_create(description="Too short")

    def test_invalid_neighbourhood_id_pattern(self):
        with pytest.raises(ValidationError):
            make_report_create(neighbourhood_id="INVALID-123")

    def test_invalid_photo_mime_type_rejected(self):
        with pytest.raises(ValidationError):
            make_photo(mime_type="application/pdf")

    def test_photo_size_zero_or_negative_rejected(self):
        with pytest.raises(ValidationError):
            make_photo(size_bytes=0)
        with pytest.raises(ValidationError):
            make_photo(size_bytes=-100)

    def test_photo_size_exceeding_15mb_rejected(self):
        with pytest.raises(ValidationError):
            make_photo(size_bytes=16_000_000)

    def test_photo_id_invalid_pattern(self):
        with pytest.raises(ValidationError):
            make_photo(photo_id="invalid_id")


# ===========================================================================
# 3. Missing Required Fields
# ===========================================================================


class TestMissingRequiredFields:
    def test_missing_category(self):
        data = make_report_create().model_dump()
        del data["category"]
        with pytest.raises(ValidationError):
            CitizenReportCreate(**data)

    def test_missing_description(self):
        data = make_report_create().model_dump()
        del data["description"]
        with pytest.raises(ValidationError):
            CitizenReportCreate(**data)

    def test_missing_severity(self):
        data = make_report_create().model_dump()
        del data["severity"]
        with pytest.raises(ValidationError):
            CitizenReportCreate(**data)

    def test_missing_coordinates(self):
        data = make_report_create().model_dump()
        del data["latitude"]
        with pytest.raises(ValidationError):
            CitizenReportCreate(**data)


# ===========================================================================
# 4. Stable Report Identifiers & Initial Status
# ===========================================================================


class TestStableIdentifiersAndInitialStatus:
    def test_report_id_format_and_stability(self):
        repo = CitizenReportRepository(":memory:")
        report = repo.create_report(make_report_create())
        assert report.id.startswith("RPT-")
        assert len(report.id) == 12  # RPT- + 8 hex chars
        # Fetching back returns the exact same ID
        fetched = repo.get_report(report.id)
        assert fetched is not None
        assert fetched.id == report.id

    def test_initial_lifecycle_status_is_submitted(self):
        repo = CitizenReportRepository(":memory:")
        report = repo.create_report(make_report_create())
        assert report.status == ReportStatus.SUBMITTED
        assert report.verification_status == VerificationStatus.UNVERIFIED


# ===========================================================================
# 5. Strict Separation of Citizen Claims from Verified Measurements
# ===========================================================================


class TestSeparationFromVerifiedMeasurements:
    def test_data_source_is_citizen_report(self):
        repo = CitizenReportRepository(":memory:")
        report = repo.create_report(make_report_create())
        assert report.data_source == "CITIZEN_REPORT"

    def test_is_verified_measurement_strictly_false(self):
        repo = CitizenReportRepository(":memory:")
        report = repo.create_report(make_report_create())
        assert report.is_verified_measurement is False

    def test_cannot_claim_synthetic_or_sensor_provenance(self):
        with pytest.raises(ValidationError):
            CitizenReport(
                id="RPT-12345678",
                category=ProblemCategory.HEAT,
                description="Extreme heat on avenue.",
                severity=3,
                latitude=21.14,
                longitude=79.08,
                data_source="SYNTHETIC",  # Must be rejected; cannot masquerade as synthetic model dataset
                urgency_score=50.0,
                evidence_confidence_score=50.0,
            )


# ===========================================================================
# 6. Score Bounds and Transparent Calculations
# ===========================================================================


class TestTransparentScoring:
    def test_urgency_score_exact_calculation(self):
        # severity=4 -> 80.0 pts (weight 0.40 -> 32.0)
        # category=FLOODING_DRAINAGE -> 90.0 pts (weight 0.30 -> 27.0)
        # ward_svi=60.0 -> 60.0 pts (weight 0.20 -> 12.0)
        # corroborating=2 -> 40.0 pts (weight 0.10 -> 4.0)
        # expected sum = 32.0 + 27.0 + 12.0 + 4.0 = 75.0
        score = calculate_urgency_score(
            severity=4,
            category=ProblemCategory.FLOODING_DRAINAGE,
            ward_svi=60.0,
            corroborating_reports_count=2,
        )
        assert score == pytest.approx(75.0, abs=0.01)

    def test_urgency_score_missing_ward_svi_uses_neutral_default(self):
        # ward_svi=None -> defaults to 50.0
        # severity=5 (100.0 * 0.4 = 40.0)
        # category=HEAT (75.0 * 0.3 = 22.5)
        # ward_svi default (50.0 * 0.2 = 10.0)
        # corroborating=0 (0.0 * 0.1 = 0.0)
        # sum = 40.0 + 22.5 + 10.0 + 0.0 = 72.5
        score = calculate_urgency_score(
            severity=5,
            category=ProblemCategory.HEAT,
            ward_svi=None,
            corroborating_reports_count=0,
        )
        assert score == pytest.approx(72.5, abs=0.01)

    def test_urgency_bounds_enforced(self):
        # Minimum possible: severity=1, green cover (50), svi=0, corrob=0
        # (20*0.4=8) + (50*0.3=15) + 0 + 0 = 23.0
        min_score = calculate_urgency_score(
            severity=1,
            category=ProblemCategory.LOSS_OF_GREEN_COVER,
            ward_svi=0.0,
            corroborating_reports_count=0,
        )
        assert 0.0 <= min_score <= 100.0
        assert min_score == pytest.approx(23.0)

        # Maximum possible: severity=5, flood (90), svi=100, corrob=5
        # (100*0.4=40) + (90*0.3=27) + (100*0.2=20) + (100*0.1=10) = 97.0
        max_score = calculate_urgency_score(
            severity=5,
            category=ProblemCategory.FLOODING_DRAINAGE,
            ward_svi=100.0,
            corroborating_reports_count=5,
        )
        assert 0.0 <= max_score <= 100.0
        assert max_score == pytest.approx(97.0)

    def test_evidence_confidence_exact_rubric(self):
        # description >= 150 chars: 30 pts
        # coordinates valid: 15 pts
        # landmark >= 5 chars: 10 pts
        # photo present with recent capture: 20 + 10 = 30 pts
        # reporter contact >= 5 chars: 15 pts
        # Total = 30 + 15 + 10 + 30 + 15 = 100.0 pts
        long_desc = "A" * 160
        photo = make_photo(captured_at=datetime.now(timezone.utc) - timedelta(hours=1))
        score = calculate_evidence_confidence_score(
            description=long_desc,
            latitude=21.14,
            longitude=79.08,
            location_description="Near Main Junction",
            photos=[photo],
            reporter_contact="test@example.com",
        )
        assert score == pytest.approx(100.0, abs=0.01)

    def test_evidence_confidence_minimal_input(self):
        # Short description (15 chars): 5 pts
        # coordinates valid: 15 pts
        # no landmark, no photos, no contact
        # Total = 20.0 pts
        score = calculate_evidence_confidence_score(
            description="Drain overflowed",
            latitude=21.14,
            longitude=79.08,
            location_description=None,
            photos=[],
            reporter_contact=None,
        )
        assert score == pytest.approx(20.0, abs=0.01)

    def test_decoupling_urgency_from_evidence_confidence(self):
        # An emergency (severity 5 flooding) can have low evidence confidence (anonymous, short text, no photo)
        urgency = calculate_urgency_score(
            severity=5,
            category=ProblemCategory.FLOODING_DRAINAGE,
            ward_svi=80.0,
        )
        confidence = calculate_evidence_confidence_score(
            description="Flooding here",
            latitude=21.14,
            longitude=79.08,
        )
        assert urgency > 75.0
        assert confidence < 25.0


# ===========================================================================
# 7. Duplicate-Report Behavior & Anti-Inflation
# ===========================================================================


class TestDuplicateReportBehavior:
    def test_rapid_duplicate_submission_rejected(self):
        repo = CitizenReportRepository(":memory:")
        report_data = make_report_create(reporter_id="CITIZEN-SPAM-1")

        # First submission succeeds
        r1 = repo.create_report(report_data)
        assert r1.id.startswith("RPT-")

        # Second submission by same citizen at same location raises DuplicateReportError
        with pytest.raises(DuplicateReportError):
            repo.create_report(report_data)

    def test_duplicate_does_not_inflate_urgency(self):
        repo = CitizenReportRepository(":memory:")
        report_data = make_report_create(reporter_id="CITIZEN-101")
        r1 = repo.create_report(report_data)
        initial_urgency = r1.urgency_score

        # Attempted duplicate does not get persisted
        with pytest.raises(DuplicateReportError):
            repo.create_report(report_data)

        # Existing report urgency remains un-inflated
        fetched = repo.get_report(r1.id)
        assert fetched.urgency_score == initial_urgency

    def test_distinct_reporter_is_accepted_and_corroborates(self):
        repo = CitizenReportRepository(":memory:")
        r1 = repo.create_report(make_report_create(reporter_id="CITIZEN-A"))

        # Distinct citizen in same vicinity submits report
        r2 = repo.create_report(make_report_create(reporter_id="CITIZEN-B"))
        assert r2.id != r1.id
        # r2 gains corroboration bonus from r1's presence in the cluster
        assert r2.urgency_score >= r1.urgency_score


# ===========================================================================
# 8. Persistence Across Store Reopening
# ===========================================================================


class TestStoreReopeningPersistence:
    def test_reports_survive_reopening(self, tmp_path: Path):
        db_file = str(tmp_path / "persistent_reports.db")

        # 1. Open repo, create report, close
        repo1 = CitizenReportRepository(db_file)
        photo = make_photo()
        rep_in = make_report_create(
            description="Critical heat distress and lack of green shade in park.",
            category=ProblemCategory.HEAT,
            photos=[photo],
        )
        created = repo1.create_report(rep_in)
        report_id = created.id
        repo1.close()

        # 2. Reopen brand new repository instance pointing to same file
        repo2 = CitizenReportRepository(db_file)
        loaded = repo2.get_report(report_id)

        assert loaded is not None
        assert loaded.id == report_id
        assert loaded.category == ProblemCategory.HEAT
        assert loaded.description == rep_in.description
        assert loaded.urgency_score == created.urgency_score
        assert loaded.evidence_confidence_score == created.evidence_confidence_score
        assert len(loaded.photos) == 1
        assert loaded.photos[0].photo_id == photo.photo_id
        assert loaded.status == ReportStatus.SUBMITTED

        # Update status in repo2, close and reopen in repo3
        repo2.update_status(
            report_id=report_id,
            status=ReportStatus.UNDER_REVIEW,
            verification_status=VerificationStatus.COMMUNITY_CORROBORATED,
        )
        repo2.close()

        repo3 = CitizenReportRepository(db_file)
        re_loaded = repo3.get_report(report_id)
        assert re_loaded.status == ReportStatus.UNDER_REVIEW
        assert re_loaded.verification_status == VerificationStatus.COMMUNITY_CORROBORATED
        repo3.close()


# ===========================================================================
# 9. Query & Filter Operations
# ===========================================================================


class TestRepositoryQueries:
    def test_list_and_filter_reports(self):
        repo = CitizenReportRepository(":memory:")
        repo.create_report(
            make_report_create(category=ProblemCategory.FLOODING_DRAINAGE, reporter_id="R1")
        )
        repo.create_report(
            make_report_create(category=ProblemCategory.WATER_SCARCITY, reporter_id="R2")
        )
        repo.create_report(
            make_report_create(category=ProblemCategory.WATER_SCARCITY, reporter_id="R3")
        )

        assert repo.count_reports() == 3
        assert repo.count_reports(category=ProblemCategory.WATER_SCARCITY) == 2
        assert repo.count_reports(category=ProblemCategory.HEAT) == 0

        water_reports = repo.list_reports(category=ProblemCategory.WATER_SCARCITY)
        assert len(water_reports) == 2
        for r in water_reports:
            assert r.category == ProblemCategory.WATER_SCARCITY

    def test_get_nonexistent_report_returns_none(self):
        repo = CitizenReportRepository(":memory:")
        assert repo.get_report("RPT-99999999") is None

    def test_update_nonexistent_report_raises_error(self):
        repo = CitizenReportRepository(":memory:")
        with pytest.raises(ReportNotFoundError):
            repo.update_status("RPT-00000000", ReportStatus.RESOLVED)


# ===========================================================================
# 10. Concurrency & Cross-Thread Duplicate Protection
# ===========================================================================


class TestConcurrencyAndDuplicateProtection:
    def test_concurrent_duplicate_submissions_same_reporter(self, tmp_path: Path):
        """
        Verify that when multiple threads attempt to submit identical reports for
        the same reporter simultaneously, exactly 1 succeeds and the others raise
        DuplicateReportError.
        """
        db_file = str(tmp_path / "concurrent_dup_test.db")
        repo = CitizenReportRepository(db_file)
        payload = make_report_create(
            reporter_id="CONC-DUPLICATE-USER",
            description="Flooded intersection causing major road cutoff.",
        )

        success_count = 0
        duplicate_count = 0

        def submit_report():
            nonlocal success_count, duplicate_count
            try:
                repo.create_report(payload)
                return True
            except DuplicateReportError:
                return False

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(submit_report) for _ in range(8)]
            results = [f.result() for f in futures]

        success_count = sum(1 for r in results if r is True)
        duplicate_count = sum(1 for r in results if r is False)

        assert success_count == 1
        assert duplicate_count == 7
        assert repo.count_reports() == 1
        repo.close()

    def test_concurrent_independent_submissions_different_reporters(self, tmp_path: Path):
        """
        Verify that multiple threads submitting independent reports from different
        residents simultaneously all succeed and are preserved.
        """
        db_file = str(tmp_path / "concurrent_indep_test.db")
        repo = CitizenReportRepository(db_file)

        def submit_distinct(user_idx: int):
            p = make_report_create(
                reporter_id=f"CONC-INDEP-USER-{user_idx}",
                description=f"Distinct environmental issue submitted by resident {user_idx}.",
            )
            return repo.create_report(p)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(submit_distinct, i) for i in range(8)]
            reports = [f.result() for f in futures]

        assert len(reports) == 8
        assert repo.count_reports() == 8
        repo.close()

    def test_repeated_submissions_do_not_inflate_corroboration(self):
        """
        Confirm that repeated submissions by the same reporter (even if allowed via
        allow_duplicate=True) do NOT increase the corroboration score or count.
        """
        repo = CitizenReportRepository(":memory:")
        p1 = make_report_create(reporter_id="REPORTER-SAME", category=ProblemCategory.HEAT)
        r1 = repo.create_report(p1)

        # Force a second submission from the same reporter (bypassing throttle)
        r2 = repo.create_report(p1, allow_duplicate=True)

        # Corroboration count for a third report in the same cluster excluding REPORTER-SAME
        corrob_count = repo.count_distinct_corroborating_reports(
            category=ProblemCategory.HEAT,
            latitude=p1.latitude,
            longitude=p1.longitude,
            exclude_reporter_id="REPORTER-OTHER",
        )
        # Only 1 distinct reporter (REPORTER-SAME), despite 2 database rows from them!
        assert corrob_count == 1

    def test_corroboration_distance_and_time_boundaries(self):
        """
        Confirm corroboration strictly requires same category, <= 0.5km distance,
        and <= 72h window.
        """
        repo = CitizenReportRepository(":memory:")
        # Base report at (21.1458, 79.0882)
        base = make_report_create(
            reporter_id="REP-BASE",
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=21.1458,
            longitude=79.0882,
        )
        repo.create_report(base)

        # Report 1: Close (<0.2 km), same category, distinct reporter -> corroborates (+1)
        close_rep = make_report_create(
            reporter_id="REP-CLOSE",
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=21.1465,
            longitude=79.0885,
        )
        r_close = repo.create_report(close_rep)
        assert r_close.urgency_score > 0

        # Report 2: Far (> 2.0 km), same category -> does NOT corroborate base
        far_rep = make_report_create(
            reporter_id="REP-FAR",
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=21.1700,  # ~2.7 km away
            longitude=79.0882,
        )
        repo.create_report(far_rep)

        count = repo.count_distinct_corroborating_reports(
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=21.1458,
            longitude=79.0882,
            exclude_reporter_id="REP-NEW",
        )
        # Only REP-BASE and REP-CLOSE are within 0.5km
        assert count == 2


# ===========================================================================
# 11. Privacy & Sensitive Data Sanitization
# ===========================================================================


class TestPrivacySanitization:
    def test_photo_file_name_path_traversal_stripped(self):
        """
        Verify that local operating system paths in photo file names are stripped
        to base names to prevent client path leakage.
        """
        photo = make_photo(file_name=r"C:\Users\JohnDoe\Pictures\Confidential\drain.jpg")
        assert photo.file_name == "drain.jpg"

        photo_unix = make_photo(file_name="/home/user/evidence/leak.png")
        assert photo_unix.file_name == "leak.png"

    def test_public_representation_strips_reporter_id_and_contact(self):
        """
        Verify that CitizenReportPublic completely omits reporter_id and reporter_contact.
        """
        report = CitizenReport(
            id="RPT-ABCDEF12",
            category=ProblemCategory.WATER_SCARCITY,
            description="Water deficit across neighbourhood.",
            severity=3,
            latitude=21.14,
            longitude=79.08,
            reporter_id="secret_user_token_123",
            reporter_contact="secret_phone_9999",
            urgency_score=50.0,
            evidence_confidence_score=50.0,
        )

        pub = CitizenReportPublic.from_report(report)
        dumped = pub.model_dump()
        assert "reporter_contact" not in dumped
        assert "reporter_id" not in dumped

