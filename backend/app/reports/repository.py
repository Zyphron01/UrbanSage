"""
UrbanSage AI — Local SQLite Citizen Report Persistence Layer
============================================================
Lightweight, robust persistence for citizen environmental reports using Python's
built-in `sqlite3` engine.

Design Guarantees:
------------------
1. Pre-persistence Validation: All input payloads are validated by Pydantic before
   any SQL query executes.
2. Persistence Survival: Reports written to a file-based database survive application
   restarts and connection teardowns.
3. Safe Error Handling: Database exceptions (integrity, lock, IO) are converted to
   clean domain exceptions (ReportNotFoundError, ReportPersistenceError, DuplicateReportError).
4. Anti-Duplicate Protection: Prevents automated script spam or rapid repeat submissions
   from artificially inflating urgency or flooding the database.
5. In-Memory Support: Allows `:memory:` mode for sub-millisecond, fully isolated unit tests.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.reports.base import BaseCitizenReportRepository
from app.reports.exceptions import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportPersistenceError,
    ReportValidationError,
)
from app.reports.models import (
    ACTIVE_STATUSES,
    CLOSED_STATUSES,
    BriefReportItem,
    CitizenReport,
    CitizenReportCreate,
    DecisionBriefResponse,
    DecisionBriefSummary,
    GeographicRiskResponse,
    NeighbourhoodRiskAggregate,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    ResolutionEvidence,
    StatusTransitionLog,
    VerificationStatus,
    validate_status_transition,
)
from app.reports.scoring import (
    calculate_evidence_confidence_score,
    calculate_urgency_score,
)


HIGH_URGENCY_THRESHOLD: float = 70.0


def _resolve_neighbourhood_name(nid: Optional[str]) -> str:
    """Resolve human-readable name for a neighbourhood identifier using synthetic dataset."""
    if not nid or nid == "UNASSIGNED":
        return "Unassigned / External Region"
    try:
        from app.data.loader import load_neighbourhoods

        for n in load_neighbourhoods():
            if n.id == nid:
                return n.name
    except Exception:
        pass
    return f"Neighbourhood {nid}"


def _report_to_brief_item(r: CitizenReport, now: datetime, overdue_threshold_hours: int = 48) -> BriefReportItem:
    """Map a stored CitizenReport to a privacy-preserving BriefReportItem with deterministic reason."""
    age_hours = round(max(0.0, (now - r.created_at).total_seconds() / 3600.0), 1)

    if r.status == ReportStatus.VERIFICATION_FAILED:
        reason = "Citizen reported resolution failed; issue reopened for supervisor review."
    elif r.status == ReportStatus.COMPLETED_AWAITING_VERIFICATION:
        reason = "Remediation submitted by field team; awaiting citizen verification."
    elif r.urgency_score >= HIGH_URGENCY_THRESHOLD:
        reason = f"High-urgency hazard ({r.urgency_score:.1f}/100); requires prioritized municipal response."
    elif r.status in ACTIVE_STATUSES and age_hours > overdue_threshold_hours:
        reason = f"Active ticket overdue ({age_hours:.1f}h > {overdue_threshold_hours}h threshold); escalation recommended."
    elif r.status in (ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW):
        reason = "New submission awaiting initial triage and operational review."
    else:
        reason = f"Active {r.category.value} issue under operational handling."

    desc_snippet = r.description if len(r.description) <= 120 else r.description[:117] + "..."

    return BriefReportItem(
        id=r.id,
        category=r.category,
        description=desc_snippet,
        severity=r.severity,
        status=r.status,
        urgency_score=r.urgency_score,
        evidence_confidence_score=r.evidence_confidence_score,
        latitude=r.latitude,
        longitude=r.longitude,
        location_description=r.location_description,
        neighbourhood_id=r.neighbourhood_id,
        created_at=r.created_at,
        age_hours=age_hours,
        prioritization_reason=reason,
    )


class CitizenReportRepository(BaseCitizenReportRepository):
    """
    SQLite-backed repository managing persistence and queries for citizen reports.
    Retained for explicitly configured local development and offline unit testing.
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize the database repository.

        Parameters
        ----------
        db_path : str
            File path to the SQLite database, or ':memory:' for isolated testing.
        """
        self.db_path = db_path
        if db_path != ":memory:":
            path_obj = Path(db_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_connection()
        self._create_schema()

    def _init_connection(self) -> None:
        """Establish the database connection with WAL mode and row factory."""
        try:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            # Enable foreign keys and busy timeout
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA busy_timeout = 5000;")
            if self.db_path != ":memory:":
                # WAL mode provides better concurrency and durability for local file DBs
                self._conn.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.Error as e:
            raise ReportPersistenceError(f"Failed to connect to database at {self.db_path}: {e}") from e

    def _create_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS citizen_reports (
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
            resolution_evidence_json TEXT DEFAULT NULL,
            timeline_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reports_category ON citizen_reports(category);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON citizen_reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_neighbourhood ON citizen_reports(neighbourhood_id);
        CREATE INDEX IF NOT EXISTS idx_reports_reporter ON citizen_reports(reporter_id);
        CREATE INDEX IF NOT EXISTS idx_reports_created ON citizen_reports(created_at);
        """
        try:
            with self._conn:
                self._conn.executescript(schema_sql)
                # Check for existing table schema upgrades
                cursor = self._conn.execute("PRAGMA table_info(citizen_reports);")
                cols = {row["name"] for row in cursor.fetchall()}
                if "resolution_evidence_json" not in cols:
                    self._conn.execute("ALTER TABLE citizen_reports ADD COLUMN resolution_evidence_json TEXT DEFAULT NULL;")
                if "timeline_json" not in cols:
                    self._conn.execute("ALTER TABLE citizen_reports ADD COLUMN timeline_json TEXT NOT NULL DEFAULT '[]';")
        except sqlite3.Error as e:
            raise ReportPersistenceError(f"Failed to create schema: {e}") from e

    def close(self) -> None:
        """Close the database connection safely."""
        if self._conn:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None

    def __enter__(self) -> CitizenReportRepository:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # -----------------------------------------------------------------------
    # Anti-Duplicate & Corroboration Logic
    # -----------------------------------------------------------------------

    def is_duplicate_submission(
        self,
        reporter_id: str,
        category: ProblemCategory,
        latitude: float,
        longitude: float,
        window_minutes: int = 30,
        dist_threshold_km: float = 0.5,
    ) -> bool:
        """
        Check if the same reporter submitted an identical problem report nearby recently.
        """
        if not reporter_id:
            return False

        # Query recent reports by this reporter in this category
        query = """
        SELECT latitude, longitude, created_at
        FROM citizen_reports
        WHERE reporter_id = ? AND category = ?
        ORDER BY created_at DESC
        LIMIT 10;
        """
        try:
            cursor = self._conn.execute(query, (reporter_id, category.value))
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise ReportPersistenceError(f"Database query failed: {e}") from e

        now = datetime.now(timezone.utc)
        for row in rows:
            created_str = row["created_at"]
            created_dt = datetime.fromisoformat(created_str)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            delta_mins = (now - created_dt).total_seconds() / 60.0
            if delta_mins <= window_minutes:
                # Approximate distance in km using equirectangular projection
                d_lat = (row["latitude"] - latitude) * 111.0
                d_lon = (row["longitude"] - longitude) * 111.0 * math.cos(math.radians(latitude))
                dist_km = math.sqrt(d_lat ** 2 + d_lon ** 2)
                if dist_km <= dist_threshold_km:
                    return True
        return False

    def count_distinct_corroborating_reports(
        self,
        category: ProblemCategory,
        latitude: float,
        longitude: float,
        exclude_reporter_id: Optional[str] = None,
        radius_km: float = 0.5,
        window_hours: float = 72.0,
    ) -> int:
        """
        Count distinct independent citizen reports within radius and time window.
        Duplicates from the same reporter do NOT add to this count.
        """
        query = """
        SELECT reporter_id, latitude, longitude, created_at
        FROM citizen_reports
        WHERE category = ?
        """
        params: List[Any] = [category.value]

        try:
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise ReportPersistenceError(f"Database query failed: {e}") from e

        now = datetime.now(timezone.utc)
        distinct_reporters = set()
        anonymous_cluster_count = 0

        for row in rows:
            rep_id = row["reporter_id"]
            if exclude_reporter_id and rep_id == exclude_reporter_id:
                continue

            created_dt = datetime.fromisoformat(row["created_at"])
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            delta_hours = (now - created_dt).total_seconds() / 3600.0
            if delta_hours > window_hours:
                continue

            d_lat = (row["latitude"] - latitude) * 111.0
            d_lon = (row["longitude"] - longitude) * 111.0 * math.cos(math.radians(latitude))
            dist_km = math.sqrt(d_lat ** 2 + d_lon ** 2)
            if dist_km <= radius_km:
                if rep_id:
                    distinct_reporters.add(rep_id)
                else:
                    anonymous_cluster_count += 1

        return len(distinct_reporters) + min(anonymous_cluster_count, 2)

    # -----------------------------------------------------------------------
    # CRUD Operations
    # -----------------------------------------------------------------------

    def create_report(
        self,
        report_in: CitizenReportCreate,
        ward_svi: Optional[float] = None,
        allow_duplicate: bool = False,
    ) -> CitizenReport:
        """
        Validate, score, and persist a new citizen report.

        Parameters
        ----------
        report_in : CitizenReportCreate
            Validated input model.
        ward_svi : Optional[float]
            Ward Social Vulnerability Index (0–100) if neighbourhood context is known.
        allow_duplicate : bool
            If False (default), raises DuplicateReportError if recent identical submission exists.
        """
        with self._lock:
            # 1. Anti-spam / duplicate throttle check
            if not allow_duplicate and report_in.reporter_id:
                if self.is_duplicate_submission(
                    reporter_id=report_in.reporter_id,
                    category=report_in.category,
                    latitude=report_in.latitude,
                    longitude=report_in.longitude,
                ):
                    raise DuplicateReportError(
                        f"Duplicate report detected for reporter '{report_in.reporter_id}' "
                        f"in category '{report_in.category.value}' within the throttle window."
                    )

            # 2. Corroboration and scoring
            corrob_count = self.count_distinct_corroborating_reports(
                category=report_in.category,
                latitude=report_in.latitude,
                longitude=report_in.longitude,
                exclude_reporter_id=report_in.reporter_id,
            )

            urgency = calculate_urgency_score(
                severity=report_in.severity,
                category=report_in.category,
                ward_svi=ward_svi,
                corroborating_reports_count=corrob_count,
            )

            now_utc = datetime.now(timezone.utc)

            evidence_confidence = calculate_evidence_confidence_score(
                description=report_in.description,
                latitude=report_in.latitude,
                longitude=report_in.longitude,
                location_description=report_in.location_description,
                photos=report_in.photos,
                reporter_contact=report_in.reporter_contact,
                submission_time=now_utc,
            )

            # 3. Generate stable report ID: RPT-XXXXXXXX (8 uppercase hex)
            report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

            # 4. Construct complete domain record
            initial_log = StatusTransitionLog(
                from_status=ReportStatus.SUBMITTED,
                to_status=ReportStatus.SUBMITTED,
                actor_role="citizen",
                actor_id=report_in.reporter_id,
                reason="Initial citizen problem report submission.",
                timestamp=now_utc,
            )
            try:
                report = CitizenReport(
                    id=report_id,
                    category=report_in.category,
                    description=report_in.description,
                    severity=report_in.severity,
                    latitude=report_in.latitude,
                    longitude=report_in.longitude,
                    location_description=report_in.location_description,
                    neighbourhood_id=report_in.neighbourhood_id,
                    reporter_id=report_in.reporter_id,
                    reporter_contact=report_in.reporter_contact,
                    photos=report_in.photos,
                    status=ReportStatus.SUBMITTED,
                    verification_status=VerificationStatus.UNVERIFIED,
                    is_verified_measurement=False,
                    data_source="CITIZEN_REPORT",
                    urgency_score=urgency,
                    evidence_confidence_score=evidence_confidence,
                    resolution_evidence=None,
                    timeline=[initial_log],
                    created_at=now_utc,
                    updated_at=now_utc,
                )
            except ValidationError as e:
                raise ReportValidationError(f"Report validation failed: {e}") from e

            # 5. SQL Insert
            photos_serialized = json.dumps([p.model_dump(mode="json") for p in report.photos])
            timeline_serialized = json.dumps([t.model_dump(mode="json") for t in report.timeline])
            insert_sql = """
            INSERT INTO citizen_reports (
                id, category, description, severity, latitude, longitude,
                location_description, neighbourhood_id, reporter_id, reporter_contact,
                photos_json, status, verification_status, is_verified_measurement,
                data_source, urgency_score, evidence_confidence_score,
                resolution_evidence_json, timeline_json,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?
            );
            """
            params = (
                report.id,
                report.category.value,
                report.description,
                report.severity,
                report.latitude,
                report.longitude,
                report.location_description,
                report.neighbourhood_id,
                report.reporter_id,
                report.reporter_contact,
                photos_serialized,
                report.status.value,
                report.verification_status.value,
                1 if report.is_verified_measurement else 0,
                report.data_source,
                report.urgency_score,
                report.evidence_confidence_score,
                None,
                timeline_serialized,
                report.created_at.isoformat(),
                report.updated_at.isoformat(),
            )

            try:
                with self._conn:
                    self._conn.execute(insert_sql, params)
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to insert report {report_id}: {e}") from e

            return report

    def get_report(self, report_id: str) -> Optional[CitizenReport]:
        """Fetch a single report by its unique identifier."""
        query = "SELECT * FROM citizen_reports WHERE id = ?;"
        with self._lock:
            try:
                cursor = self._conn.execute(query, (report_id,))
                row = cursor.fetchone()
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to query report {report_id}: {e}") from e

        if not row:
            return None
        return self._row_to_model(row)

    def list_reports(
        self,
        category: Optional[ProblemCategory] = None,
        status: Optional[ReportStatus] = None,
        verification_status: Optional[VerificationStatus] = None,
        neighbourhood_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CitizenReport]:
        """
        List citizen reports with optional filtering, sorted newest first.
        """
        clauses = []
        params: List[Any] = []

        if category is not None:
            clauses.append("category = ?")
            params.append(category.value)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if verification_status is not None:
            clauses.append("verification_status = ?")
            params.append(verification_status.value)
        if neighbourhood_id is not None:
            clauses.append("neighbourhood_id = ?")
            params.append(neighbourhood_id)

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
        SELECT * FROM citizen_reports
        {where_stmt}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        params.extend([max(1, limit), max(0, offset)])

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to list reports: {e}") from e

        return [self._row_to_model(row) for row in rows]

    def update_status(
        self,
        report_id: str,
        status: ReportStatus,
        verification_status: Optional[VerificationStatus] = None,
        actor_role: str = "administrator",
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        evidence: Optional[ResolutionEvidence] = None,
        validate_transition: bool = True,
    ) -> CitizenReport:
        """
        Update report operational or verification status safely with transition validation and audit trail.
        """
        with self._lock:
            existing = self.get_report(report_id)
            if not existing:
                raise ReportNotFoundError(report_id)

            if validate_transition:
                validate_status_transition(existing.status, status, actor_role=actor_role)

            if status == ReportStatus.COMPLETED_AWAITING_VERIFICATION and evidence is None and existing.resolution_evidence is None:
                raise ReportValidationError(
                    "Resolution evidence is required when transitioning to 'completed_awaiting_verification'."
                )

            now_dt = datetime.now(timezone.utc)
            now_utc = now_dt.isoformat()

            # Record audit log
            log_entry = StatusTransitionLog(
                from_status=existing.status,
                to_status=status,
                actor_role=actor_role,
                actor_id=actor_id,
                reason=reason,
                timestamp=now_dt,
                evidence=evidence or existing.resolution_evidence,
            )
            new_timeline = list(existing.timeline)
            new_timeline.append(log_entry)
            timeline_serialized = json.dumps([t.model_dump(mode="json") for t in new_timeline])

            active_evidence = evidence or existing.resolution_evidence
            evidence_serialized = active_evidence.model_dump_json() if active_evidence else None

            v_status = verification_status.value if verification_status is not None else existing.verification_status.value

            update_sql = """
            UPDATE citizen_reports
            SET status = ?, verification_status = ?, updated_at = ?,
                resolution_evidence_json = ?, timeline_json = ?
            WHERE id = ?;
            """
            params = (status.value, v_status, now_utc, evidence_serialized, timeline_serialized, report_id)

            try:
                with self._conn:
                    self._conn.execute(update_sql, params)
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to update report {report_id}: {e}") from e

            updated = self.get_report(report_id)
            if not updated:
                raise ReportNotFoundError(report_id)
            return updated

    def verify_resolution(
        self,
        report_id: str,
        confirmed_resolved: bool,
        feedback: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> CitizenReport:
        """Citizen confirms or rejects resolution of a report."""
        with self._lock:
            existing = self.get_report(report_id)
            if not existing:
                raise ReportNotFoundError(report_id)

            now_dt = datetime.now(timezone.utc)
            if confirmed_resolved:
                new_status = ReportStatus.VERIFIED_RESOLVED
                v_status = VerificationStatus.OFFICIALLY_VERIFIED
                reason_text = feedback or "Citizen verified satisfactory problem resolution."
            else:
                new_status = ReportStatus.VERIFICATION_FAILED
                v_status = existing.verification_status
                reason_text = feedback or "Citizen rejected resolution; problem remains unresolved."

            # Update resolution evidence
            evidence = existing.resolution_evidence
            if evidence:
                evidence = evidence.model_copy(
                    update={
                        "citizen_confirmed": confirmed_resolved,
                        "citizen_feedback": feedback,
                        "verified_at": now_dt,
                    }
                )

            return self.update_status(
                report_id=report_id,
                status=new_status,
                verification_status=v_status,
                actor_role="citizen",
                actor_id=actor_id,
                reason=reason_text,
                evidence=evidence,
                validate_transition=True,
            )

    def add_additional_evidence(
        self,
        report_id: str,
        additional_notes: Optional[str] = None,
        photos: Optional[List[PhotoMetadata]] = None,
        actor_id: Optional[str] = None,
    ) -> CitizenReport:
        """Citizen submits additional information/photos when requested."""
        with self._lock:
            existing = self.get_report(report_id)
            if not existing:
                raise ReportNotFoundError(report_id)

            updated_photos = list(existing.photos)
            if photos:
                updated_photos.extend(photos)

            updated_description = existing.description
            if additional_notes:
                updated_description = f"{existing.description}\n\n[Additional Citizen Evidence]: {additional_notes}"

            now_dt = datetime.now(timezone.utc)
            photos_serialized = json.dumps([p.model_dump(mode="json") for p in updated_photos])

            # Transition from info_requested back to under_review automatically
            target_status = ReportStatus.UNDER_REVIEW if existing.status == ReportStatus.INFO_REQUESTED else existing.status

            log_entry = StatusTransitionLog(
                from_status=existing.status,
                to_status=target_status,
                actor_role="citizen",
                actor_id=actor_id,
                reason="Additional evidence provided by citizen.",
                timestamp=now_dt,
            )
            new_timeline = list(existing.timeline)
            new_timeline.append(log_entry)
            timeline_serialized = json.dumps([t.model_dump(mode="json") for t in new_timeline])

            update_sql = """
            UPDATE citizen_reports
            SET description = ?, photos_json = ?, status = ?, updated_at = ?, timeline_json = ?
            WHERE id = ?;
            """
            params = (
                updated_description,
                photos_serialized,
                target_status.value,
                now_dt.isoformat(),
                timeline_serialized,
                report_id,
            )

            try:
                with self._conn:
                    self._conn.execute(update_sql, params)
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to append evidence to report {report_id}: {e}") from e

            updated = self.get_report(report_id)
            if not updated:
                raise ReportNotFoundError(report_id)
            return updated

    def count_reports(
        self,
        category: Optional[ProblemCategory] = None,
        status: Optional[ReportStatus] = None,
    ) -> int:
        """Count total reports matching criteria."""
        clauses = []
        params: List[Any] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category.value)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT COUNT(*) FROM citizen_reports {where_stmt};"

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                return cursor.fetchone()[0]
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to count reports: {e}") from e

    def get_decision_brief(
        self,
        overdue_threshold_hours: int = 48,
    ) -> DecisionBriefResponse:
        """
        Aggregate operational metrics and priority items for municipal administrators.
        Identifies high-urgency active reports, awaiting review, awaiting verification,
        failed verifications, and overdue tickets (>48h).
        """
        with self._lock:
            try:
                cursor = self._conn.execute("SELECT * FROM citizen_reports;")
                rows = cursor.fetchall()
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to query reports for decision brief: {e}") from e

            reports = [self._row_to_model(row) for row in rows]

        now = datetime.now(timezone.utc)
        total_reports = len(reports)

        by_status: dict[str, int] = {s.value: 0 for s in ReportStatus}
        by_category: dict[str, int] = {c.value: 0 for c in ProblemCategory}

        active_reports = 0
        high_urgency_active_count = 0
        awaiting_review_count = 0
        awaiting_citizen_verification_count = 0
        verification_failed_count = 0
        overdue_active_count = 0

        high_urgency_items: list[BriefReportItem] = []
        awaiting_review_items: list[BriefReportItem] = []
        awaiting_citizen_verification_items: list[BriefReportItem] = []
        failed_verification_items: list[BriefReportItem] = []
        overdue_items: list[BriefReportItem] = []

        all_timeline_entries: list[StatusTransitionLog] = []

        for r in reports:
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
            by_category[r.category.value] = by_category.get(r.category.value, 0) + 1

            # Timeline aggregation for recent activity (with citizen actor privacy redaction)
            for entry in r.timeline:
                entry_data = entry.model_dump()
                if entry_data.get("actor_role") == "citizen":
                    entry_data["actor_id"] = None
                all_timeline_entries.append(StatusTransitionLog.model_validate(entry_data))

            is_active = r.status in ACTIVE_STATUSES
            if is_active:
                active_reports += 1
                age_hours = (now - r.created_at).total_seconds() / 3600.0

                if r.urgency_score >= HIGH_URGENCY_THRESHOLD:
                    high_urgency_active_count += 1
                    high_urgency_items.append(_report_to_brief_item(r, now, overdue_threshold_hours))

                if r.status in (ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW):
                    awaiting_review_count += 1
                    awaiting_review_items.append(_report_to_brief_item(r, now, overdue_threshold_hours))

                if r.status == ReportStatus.COMPLETED_AWAITING_VERIFICATION:
                    awaiting_citizen_verification_count += 1
                    awaiting_citizen_verification_items.append(_report_to_brief_item(r, now, overdue_threshold_hours))

                if r.status == ReportStatus.VERIFICATION_FAILED:
                    verification_failed_count += 1
                    failed_verification_items.append(_report_to_brief_item(r, now, overdue_threshold_hours))

                if age_hours > overdue_threshold_hours:
                    overdue_active_count += 1
                    overdue_items.append(_report_to_brief_item(r, now, overdue_threshold_hours))

        # Stable sorts:
        # High urgency: urgency desc, age desc, id asc
        high_urgency_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        # Awaiting review: urgency desc, age desc, id asc
        awaiting_review_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        # Awaiting verification: age desc, urgency desc, id asc
        awaiting_citizen_verification_items.sort(key=lambda x: (-x.age_hours, -x.urgency_score, x.id))
        # Failed verification: urgency desc, age desc, id asc
        failed_verification_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        # Overdue items: age desc, urgency desc, id asc
        overdue_items.sort(key=lambda x: (-x.age_hours, -x.urgency_score, x.id))

        # Recent activity: timestamp desc
        all_timeline_entries.sort(key=lambda x: x.timestamp, reverse=True)

        summary = DecisionBriefSummary(
            total_reports=total_reports,
            active_reports=active_reports,
            high_urgency_active_count=high_urgency_active_count,
            awaiting_review_count=awaiting_review_count,
            awaiting_citizen_verification_count=awaiting_citizen_verification_count,
            verification_failed_count=verification_failed_count,
            overdue_active_count=overdue_active_count,
            by_status=by_status,
            by_category=by_category,
        )

        return DecisionBriefResponse(
            generated_at=now,
            overdue_threshold_hours=overdue_threshold_hours,
            summary=summary,
            high_urgency_items=high_urgency_items[:20],
            awaiting_review_items=awaiting_review_items[:20],
            awaiting_citizen_verification_items=awaiting_citizen_verification_items[:20],
            failed_verification_items=failed_verification_items[:20],
            overdue_items=overdue_items[:20],
            recent_activity=all_timeline_entries[:15],
        )

    def get_priority_queue(
        self,
        status: Optional[ReportStatus] = None,
        category: Optional[ProblemCategory] = None,
        neighbourhood_id: Optional[str] = None,
        min_urgency: Optional[float] = None,
        sort_by: str = "urgency_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[CitizenReport], int]:
        """
        Fetch paginated, stably-sorted reports for the priority review queue.
        Supports sorting by urgency or age, with stable secondary keys.
        """
        clauses = []
        params: list[Any] = []

        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if category is not None:
            clauses.append("category = ?")
            params.append(category.value)
        if neighbourhood_id is not None:
            if neighbourhood_id == "UNASSIGNED":
                clauses.append("(neighbourhood_id IS NULL OR neighbourhood_id = '')")
            else:
                clauses.append("neighbourhood_id = ?")
                params.append(neighbourhood_id)
        if min_urgency is not None:
            clauses.append("urgency_score >= ?")
            params.append(float(min_urgency))

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        # Order selection:
        if sort_by == "urgency_asc":
            order_clause = "ORDER BY urgency_score ASC, created_at ASC, id ASC"
        elif sort_by == "age_desc":
            # Oldest first
            order_clause = "ORDER BY created_at ASC, urgency_score DESC, id ASC"
        elif sort_by == "age_asc":
            # Newest first
            order_clause = "ORDER BY created_at DESC, urgency_score DESC, id ASC"
        else:
            # Default urgency_desc: highest urgency first
            order_clause = "ORDER BY urgency_score DESC, created_at ASC, id ASC"

        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        count_sql = f"SELECT COUNT(*) FROM citizen_reports {where_stmt};"
        data_sql = f"SELECT * FROM citizen_reports {where_stmt} {order_clause} LIMIT ? OFFSET ?;"

        with self._lock:
            try:
                count_cur = self._conn.execute(count_sql, params)
                total = count_cur.fetchone()[0]

                data_params = list(params) + [safe_limit, safe_offset]
                data_cur = self._conn.execute(data_sql, data_params)
                rows = data_cur.fetchall()
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to query priority queue: {e}") from e

            return [self._row_to_model(row) for row in rows], total

    def get_geographic_risk_summary(
        self,
        time_window_days: Optional[int] = None,
        category: Optional[ProblemCategory] = None,
    ) -> GeographicRiskResponse:
        """
        Aggregate environmental reports and hazard metrics across neighbourhoods.
        Includes report counts, high-urgency counts, active/resolved counts, average urgency,
        and category breakdown. Explicitly handles unassigned reports.
        """
        clauses = []
        params: list[Any] = []
        now = datetime.now(timezone.utc)

        if time_window_days is not None and time_window_days > 0:
            cutoff = now - timedelta(days=time_window_days)
            clauses.append("created_at >= ?")
            params.append(cutoff.isoformat())
        if category is not None:
            clauses.append("category = ?")
            params.append(category.value)

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM citizen_reports {where_stmt};"

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()
            except sqlite3.Error as e:
                raise ReportPersistenceError(f"Failed to query geographic risk: {e}") from e

            reports = [self._row_to_model(row) for row in rows]

        # Group by neighbourhood
        groups: dict[str, list[CitizenReport]] = {}
        unassigned_reports: list[CitizenReport] = []

        for r in reports:
            if not r.neighbourhood_id or r.neighbourhood_id == "UNASSIGNED":
                unassigned_reports.append(r)
            else:
                groups.setdefault(r.neighbourhood_id, []).append(r)

        def _build_aggregate(nid: str, r_list: list[CitizenReport]) -> NeighbourhoodRiskAggregate:
            total = len(r_list)
            active = sum(1 for r in r_list if r.status in ACTIVE_STATUSES)
            resolved = sum(1 for r in r_list if r.status in CLOSED_STATUSES)
            high_urgency = sum(1 for r in r_list if r.urgency_score >= HIGH_URGENCY_THRESHOLD)
            avg_urg = round(sum(r.urgency_score for r in r_list) / total, 1) if total > 0 else 0.0

            cat_breakdown: dict[str, int] = {}
            for r in r_list:
                cat_breakdown[r.category.value] = cat_breakdown.get(r.category.value, 0) + 1

            top_cat = None
            if cat_breakdown:
                top_cat_str = max(cat_breakdown.items(), key=lambda kv: kv[1])[0]
                top_cat = ProblemCategory(top_cat_str)

            return NeighbourhoodRiskAggregate(
                neighbourhood_id=nid,
                neighbourhood_name=_resolve_neighbourhood_name(nid),
                total_reports=total,
                active_reports=active,
                resolved_reports=resolved,
                high_urgency_reports=high_urgency,
                average_urgency=avg_urg,
                category_breakdown=cat_breakdown,
                top_hazard_category=top_cat,
            )

        neighbourhoods_list: list[NeighbourhoodRiskAggregate] = []
        for nid in sorted(groups.keys()):
            neighbourhoods_list.append(_build_aggregate(nid, groups[nid]))

        unassigned_agg = None
        if unassigned_reports:
            unassigned_agg = _build_aggregate("UNASSIGNED", unassigned_reports)

        return GeographicRiskResponse(
            generated_at=now,
            time_window_days=time_window_days,
            total_reports=len(reports),
            neighbourhoods=neighbourhoods_list,
            unassigned=unassigned_agg,
        )

    def _row_to_model(self, row: sqlite3.Row) -> CitizenReport:
        """Convert a database row into a validated CitizenReport model."""
        photos_raw = json.loads(row["photos_json"])
        photos = [PhotoMetadata.model_validate(p) for p in photos_raw]

        created_dt = datetime.fromisoformat(row["created_at"])
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        updated_dt = datetime.fromisoformat(row["updated_at"])
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)

        resolution_evidence = None
        if "resolution_evidence_json" in row.keys() and row["resolution_evidence_json"]:
            try:
                resolution_evidence = ResolutionEvidence.model_validate_json(row["resolution_evidence_json"])
            except Exception:
                resolution_evidence = None

        timeline = []
        if "timeline_json" in row.keys() and row["timeline_json"]:
            try:
                raw_timeline = json.loads(row["timeline_json"])
                timeline = [StatusTransitionLog.model_validate(t) for t in raw_timeline]
            except Exception:
                timeline = []

        return CitizenReport(
            id=row["id"],
            category=ProblemCategory(row["category"]),
            description=row["description"],
            severity=row["severity"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            location_description=row["location_description"],
            neighbourhood_id=row["neighbourhood_id"],
            reporter_id=row["reporter_id"],
            reporter_contact=row["reporter_contact"],
            photos=photos,
            status=ReportStatus(row["status"]),
            verification_status=VerificationStatus(row["verification_status"]),
            is_verified_measurement=bool(row["is_verified_measurement"]),
            data_source="CITIZEN_REPORT",
            urgency_score=row["urgency_score"],
            evidence_confidence_score=row["evidence_confidence_score"],
            resolution_evidence=resolution_evidence,
            timeline=timeline,
            created_at=created_dt,
            updated_at=updated_dt,
        )


# Backward-compatible explicit alias
SQLiteCitizenReportRepository = CitizenReportRepository
