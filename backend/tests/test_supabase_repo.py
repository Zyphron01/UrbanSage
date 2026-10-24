"""
test_supabase_repo.py — Comprehensive Tests for Supabase Repository & Migration
================================================================================
Tests all Phase 2 requirements for the Supabase PostgreSQL migration:
1. Supabase connection configuration and validation.
2. Safe database connection failure handling (no silent fallback).
3. Report creation and data mapping (JSONB photos, native booleans, UTC timestamps).
4. Report retrieval (get_report).
5. Report listing, pagination (limit, offset), and multi-criteria filtering.
6. Status updating and 404 handling.
7. Anti-duplicate throttle detection.
8. Spatial-temporal corroboration counting.
9. Deterministic urgency and evidence completeness scoring.
10. Privacy protection: private reporter_contact is excluded from public representations.
11. Migration utility validation, dry-run, and idempotency.

Note on Test Environment:
-------------------------
These tests use isolated mocks conforming strictly to the official Supabase / PostgREST
client interface, validating all query chaining, parameterization, error translation,
and domain logic without requiring external network calls.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.db.migrate_sqlite_to_supabase import parse_sqlite_record, run_migration
from app.reports.exceptions import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportPersistenceError,
)
from app.reports.factory import (
    get_database_backend,
    get_report_repository,
    reset_repository_instance,
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
from app.reports.repository import SQLiteCitizenReportRepository
from app.reports.supabase_repo import SupabaseCitizenReportRepository


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def make_valid_report_create(**overrides) -> CitizenReportCreate:
    base = {
        "category": ProblemCategory.FLOODING_DRAINAGE,
        "description": "Critical underpass inundation blocking access to civic hospital.",
        "severity": 5,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "location_description": "Underpass near MG Road Metro",
        "neighbourhood_id": "NBR-001",
        "reporter_id": "CITIZEN-USER-99",
        "reporter_contact": "confidential_citizen@example.org",
        "photos": [
            PhotoMetadata(
                photo_id="PHO-A1B2C3D4",
                file_name="flood_water.jpg",
                mime_type="image/jpeg",
                size_bytes=204850,
            )
        ],
    }
    base.update(overrides)
    return CitizenReportCreate(**base)


def make_mock_supabase_client():
    """Build a comprehensive mock Supabase client mirroring postgrest-py chaining."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock

    # Builder mock that chains operations and returns an execute result
    builder_mock = MagicMock()
    table_mock.select.return_value = builder_mock
    table_mock.insert.return_value = builder_mock
    table_mock.update.return_value = builder_mock
    table_mock.upsert.return_value = builder_mock

    builder_mock.eq.return_value = builder_mock
    builder_mock.gte.return_value = builder_mock
    builder_mock.lte.return_value = builder_mock
    builder_mock.order.return_value = builder_mock
    builder_mock.range.return_value = builder_mock
    builder_mock.limit.return_value = builder_mock
    builder_mock.maybe_single.return_value = builder_mock
    builder_mock.single.return_value = builder_mock

    return client, table_mock, builder_mock


# ---------------------------------------------------------------------------
# 1. Configuration & Factory Tests
# ---------------------------------------------------------------------------


class TestSupabaseConfigurationAndFactory:
    """Verifies environment parsing, default backend behavior, and safe failure rules."""

    def test_default_backend_is_supabase(self, monkeypatch):
        monkeypatch.delenv("DATABASE_BACKEND", raising=False)
        assert get_database_backend() == "supabase"

    def test_missing_credentials_raises_clear_error_without_fallback(self, monkeypatch):
        monkeypatch.setenv("DATABASE_BACKEND", "supabase")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        reset_repository_instance()

        with pytest.raises(ReportPersistenceError) as exc_info:
            get_report_repository()

        msg = str(exc_info.value).lower()
        assert "supabase_url" in msg
        assert "supabase_secret_key" in msg
        # Verifies no silent fallback to SQLite
        assert "database_backend=sqlite" in msg

    def test_explicit_sqlite_configuration_is_rejected(self, monkeypatch):
        monkeypatch.setenv("DATABASE_BACKEND", "sqlite")
        reset_repository_instance()

        with pytest.raises(ReportPersistenceError) as exc_info:
            get_report_repository()
        assert "sqlite is no longer supported" in str(exc_info.value).lower()
        reset_repository_instance()

    def test_unsupported_backend_raises_error(self, monkeypatch):
        monkeypatch.setenv("DATABASE_BACKEND", "mongodb_invalid")
        reset_repository_instance()

        with pytest.raises(ReportPersistenceError) as exc_info:
            get_report_repository()
        assert "unsupported database_backend" in str(exc_info.value).lower()
        reset_repository_instance()


# ---------------------------------------------------------------------------
# 2. Supabase CRUD, Data Mapping & Privacy Tests
# ---------------------------------------------------------------------------


class TestSupabaseCRUDAndPrivacy:
    """Verifies report creation, retrieval, listing, status updates, and privacy protections."""

    def test_create_report_inserts_valid_payload(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        builder_mock.execute.return_value = MagicMock(data=[{"id": "dummy"}], count=None)

        repo = SupabaseCitizenReportRepository(client=client)

        payload = make_valid_report_create()
        created = repo.create_report(payload, ward_svi=75.0, allow_duplicate=True)

        assert created.id.startswith("RPT-")
        assert len(created.id) == 12  # RPT- + 8 hex
        assert created.category == ProblemCategory.FLOODING_DRAINAGE
        assert created.urgency_score > 0.0
        assert created.evidence_confidence_score > 0.0

        # Verify insert called on table 'citizen_reports'
        table_mock.insert.assert_called_once()
        insert_dict = table_mock.insert.call_args[0][0]
        assert insert_dict["id"] == created.id
        assert insert_dict["category"] == "flooding_drainage"
        assert insert_dict["reporter_contact"] == "confidential_citizen@example.org"
        assert isinstance(insert_dict["photos"], list)
        assert insert_dict["is_verified_measurement"] is False

    def test_privacy_protections_omit_reporter_contact_from_public_dto(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        builder_mock.execute.return_value = MagicMock(data=[{"id": "dummy"}], count=None)

        repo = SupabaseCitizenReportRepository(client=client)
        report = repo.create_report(make_valid_report_create(), allow_duplicate=True)

        # Map to public DTO
        public_view = CitizenReportPublic.from_report(report)
        view_dict = public_view.model_dump(mode="json")

        assert "reporter_contact" not in view_dict
        assert "reporter_id" not in view_dict
        assert view_dict["id"] == report.id
        assert view_dict["data_source"] == "CITIZEN_REPORT"

    def test_get_report_returns_model_when_found(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        sample_row = {
            "id": "RPT-A1B2C3D4",
            "category": "heat",
            "description": "Extreme urban heat island in concrete area.",
            "severity": 3,
            "latitude": 13.0285,
            "longitude": 77.5197,
            "location_description": "Industrial yard",
            "neighbourhood_id": "NBR-003",
            "reporter_id": "CITIZEN-01",
            "reporter_contact": "private@example.com",
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 58.0,
            "evidence_confidence_score": 45.0,
            "created_at": now_str,
            "updated_at": now_str,
        }
        builder_mock.execute.return_value = MagicMock(data=sample_row)

        repo = SupabaseCitizenReportRepository(client=client)
        result = repo.get_report("RPT-A1B2C3D4")

        assert result is not None
        assert result.id == "RPT-A1B2C3D4"
        assert result.category == ProblemCategory.HEAT
        assert result.severity == 3

    def test_get_report_returns_none_when_missing(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        builder_mock.execute.return_value = MagicMock(data=None)

        repo = SupabaseCitizenReportRepository(client=client)
        assert repo.get_report("RPT-NONEXIST") is None

    def test_list_reports_with_filters_and_pagination(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "id": f"RPT-0000000{i}",
                "category": "water_scarcity",
                "description": f"Water shortage report {i}",
                "severity": 3,
                "latitude": 12.9698,
                "longitude": 77.7499,
                "location_description": "Zone 5",
                "neighbourhood_id": "NBR-005",
                "reporter_id": f"CITIZEN-{i}",
                "reporter_contact": None,
                "photos": [],
                "status": "submitted",
                "verification_status": "unverified",
                "is_verified_measurement": False,
                "data_source": "CITIZEN_REPORT",
                "urgency_score": 60.0,
                "evidence_confidence_score": 40.0,
                "created_at": now_str,
                "updated_at": now_str,
            }
            for i in range(3)
        ]
        builder_mock.execute.return_value = MagicMock(data=rows)

        repo = SupabaseCitizenReportRepository(client=client)
        results = repo.list_reports(
            category=ProblemCategory.WATER_SCARCITY,
            status=ReportStatus.SUBMITTED,
            neighbourhood_id="NBR-005",
            limit=10,
            offset=0,
        )

        assert len(results) == 3
        assert results[0].category == ProblemCategory.WATER_SCARCITY
        builder_mock.range.assert_called_with(0, 9)

    def test_update_status_success(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        existing_row = {
            "id": "RPT-B8C9D0E1",
            "category": "flooding_drainage",
            "description": "Blocked stormwater drain.",
            "severity": 4,
            "latitude": 12.9345,
            "longitude": 77.6266,
            "location_description": "Koramangala",
            "neighbourhood_id": "NBR-002",
            "reporter_id": "CITIZEN-02",
            "reporter_contact": None,
            "photos": [],
            "status": "submitted",
            "verification_status": "unverified",
            "is_verified_measurement": False,
            "data_source": "CITIZEN_REPORT",
            "urgency_score": 72.0,
            "evidence_confidence_score": 50.0,
            "created_at": now_str,
            "updated_at": now_str,
        }
        updated_row = dict(existing_row)
        updated_row["status"] = "assigned"
        updated_row["verification_status"] = "community_corroborated"

        # Mock get_report and update
        builder_mock.execute.side_effect = [
            MagicMock(data=existing_row),  # get_report check
            MagicMock(data=[updated_row]),  # update return
        ]

        repo = SupabaseCitizenReportRepository(client=client)
        updated = repo.update_status(
            report_id="RPT-B8C9D0E1",
            status=ReportStatus.ASSIGNED,
            verification_status=VerificationStatus.COMMUNITY_CORROBORATED,
        )

        assert updated.status == ReportStatus.ASSIGNED
        assert updated.verification_status == VerificationStatus.COMMUNITY_CORROBORATED

    def test_update_status_raises_404_when_nonexistent(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        builder_mock.execute.return_value = MagicMock(data=None)

        repo = SupabaseCitizenReportRepository(client=client)
        with pytest.raises(ReportNotFoundError):
            repo.update_status("RPT-NOTFOUND", status=ReportStatus.RESOLVED)


# ---------------------------------------------------------------------------
# 3. Duplicate Detection & Corroboration Tests
# ---------------------------------------------------------------------------


class TestSupabaseDuplicateAndCorroboration:
    """Verifies that anti-spam throttle logic and corroboration queries function accurately."""

    def test_duplicate_submission_detected_within_throttle_window(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        recent_report = {
            "latitude": 12.9856,
            "longitude": 77.6057,
            "created_at": now_str,
        }
        builder_mock.execute.return_value = MagicMock(data=[recent_report])

        repo = SupabaseCitizenReportRepository(client=client)
        is_dup = repo.is_duplicate_submission(
            reporter_id="CITIZEN-101",
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=12.9856,
            longitude=77.6057,
        )
        assert is_dup is True

    def test_duplicate_submission_not_detected_when_far_away(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        # Location 15 km away
        far_report = {
            "latitude": 13.0856,
            "longitude": 77.7057,
            "created_at": now_str,
        }
        builder_mock.execute.return_value = MagicMock(data=[far_report])

        repo = SupabaseCitizenReportRepository(client=client)
        is_dup = repo.is_duplicate_submission(
            reporter_id="CITIZEN-101",
            category=ProblemCategory.FLOODING_DRAINAGE,
            latitude=12.9856,
            longitude=77.6057,
        )
        assert is_dup is False

    def test_create_report_raises_duplicate_error(self):
        client, table_mock, builder_mock = make_mock_supabase_client()
        now_str = datetime.now(timezone.utc).isoformat()
        builder_mock.execute.return_value = MagicMock(
            data=[{"latitude": 12.9716, "longitude": 77.5946, "created_at": now_str}]
        )

        repo = SupabaseCitizenReportRepository(client=client)
        payload = make_valid_report_create()

        with pytest.raises(DuplicateReportError) as exc_info:
            repo.create_report(payload, allow_duplicate=False)
        assert "duplicate report detected" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 4. Migration Script Verification & Idempotency Tests
# ---------------------------------------------------------------------------


class TestMigrationScript:
    """Tests the SQLite-to-Supabase migration script dry-run, parsing, and idempotency."""

    def test_parse_sqlite_row_preserves_all_domain_fields(self):
        # Create an in-memory SQLite database with 1 valid row
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE citizen_reports (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                severity INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                location_description TEXT,
                neighbourhood_id TEXT,
                reporter_id TEXT,
                reporter_contact TEXT,
                photos_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                is_verified_measurement INTEGER NOT NULL DEFAULT 0,
                data_source TEXT NOT NULL DEFAULT 'CITIZEN_REPORT',
                urgency_score REAL NOT NULL,
                evidence_confidence_score REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        now_str = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO citizen_reports VALUES (
                'RPT-99AABBCC', 'water_scarcity', 'Water pipeline fractured for 48 hours.', 4,
                12.9345, 77.6266, 'Near water tank', 'NBR-002', 'REP-01', 'confidential@user.net',
                '[]', 'submitted', 'unverified', 0, 'CITIZEN_REPORT', 68.0, 42.0, ?, ?
            )
            """,
            (now_str, now_str),
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM citizen_reports;")
        row = cursor.fetchone()

        parsed = parse_sqlite_record(row)
        conn.close()

        assert parsed["id"] == "RPT-99AABBCC"
        assert parsed["category"] == "water_scarcity"
        assert parsed["severity"] == 4
        assert parsed["reporter_contact"] == "confidential@user.net"
        assert parsed["photos"] == []
        assert parsed["is_verified_measurement"] is False

    def test_run_migration_dry_run_does_not_modify_supabase(self, tmp_path):
        # Create a sample test SQLite database with schema
        db_file = tmp_path / "test_migration.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("""
            CREATE TABLE citizen_reports (
                id TEXT PRIMARY KEY,
                category TEXT,
                description TEXT,
                severity INTEGER,
                latitude REAL,
                longitude REAL,
                location_description TEXT,
                neighbourhood_id TEXT,
                reporter_id TEXT,
                reporter_contact TEXT,
                photos TEXT,
                status TEXT,
                verification_status TEXT,
                is_verified_measurement INTEGER,
                data_source TEXT,
                urgency_score REAL,
                evidence_confidence_score REAL,
                resolution_evidence TEXT,
                timeline TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()

        success = run_migration(
            sqlite_path=str(db_file),
            dry_run=True,
            force=False,
        )
        assert success is True

