"""
UrbanSage AI — Supabase PostgreSQL Citizen Report Persistence Layer
===================================================================
Production-grade repository managing persistence and queries for citizen
reports using Supabase PostgreSQL via the official Supabase Python client.

Design Guarantees:
------------------
1. Direct Cloud PostgreSQL Storage: Primary storage is hosted Supabase PostgreSQL.
2. Strict Privacy Protections: Sensitive contact details are never logged or leaked.
3. Pre-persistence Domain Scoring: Validates inputs via Pydantic and computes
   deterministic Urgency and Evidence Completeness metrics before insertion.
4. Anti-Duplicate Protection: Prevents rapid re-submissions by the same reporter
   from inflating operational priority or spamming the database.
5. Resilient Connection Handling: Provides configurable retries for transient
   network timeouts on safe operations, with explicit configuration enforcement.
"""

from __future__ import annotations

import logging
import math
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError
from supabase import Client, create_client

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
from app.reports.repository import (
    HIGH_URGENCY_THRESHOLD,
    _report_to_brief_item,
    _resolve_neighbourhood_name,
)
from app.reports.scoring import (
    calculate_evidence_confidence_score,
    calculate_urgency_score,
)

logger = logging.getLogger("urbansage.reports.supabase")


class SupabaseCitizenReportRepository(BaseCitizenReportRepository):
    """
    Supabase-backed repository for citizen environmental problem reporting.
    """

    TABLE_NAME = "citizen_reports"

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        client: Optional[Client] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        """
        Initialize the Supabase PostgreSQL repository.

        Parameters
        ----------
        supabase_url : Optional[str]
            Supabase project URL (e.g., https://xyzcompany.supabase.co).
            Defaults to SUPABASE_URL environment variable.
        supabase_key : Optional[str]
            Supabase server-side secret / service-role key.
            Defaults to SUPABASE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY, or SUPABASE_KEY.
        client : Optional[Client]
            Pre-configured Supabase Client instance (used for dependency injection or testing).
        max_retries : int
            Maximum number of retry attempts for transient read errors.
        retry_delay_seconds : float
            Base delay for exponential backoff on retries.
        """
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        if client is not None:
            self._client = client
        else:
            url = supabase_url or os.getenv("SUPABASE_URL")
            # Support both new secret key format and legacy service-role key
            key = (
                supabase_key
                or os.getenv("SUPABASE_SECRET_KEY")
                or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                or os.getenv("SUPABASE_KEY")
            )

            if not url or not key:
                masked_url = f"{url[:12]}..." if url else "<unset>"
                logger.error(
                    "Supabase configuration incomplete. SUPABASE_URL: %s, Secret Key set: %s",
                    masked_url,
                    bool(key),
                )
                raise ReportPersistenceError(
                    "Supabase database configuration missing: both SUPABASE_URL and SUPABASE_SECRET_KEY "
                    "(or SUPABASE_SERVICE_ROLE_KEY) must be set in the environment. "
                    "UrbanSage AI requires Supabase PostgreSQL as its primary database. "
                    "To run offline in development, explicitly set DATABASE_BACKEND=sqlite."
                )

            try:
                self._client = create_client(url, key)
            except Exception as e:
                logger.error("Failed to initialize Supabase client: %s", e)
                raise ReportPersistenceError(f"Failed to connect to Supabase: {e}") from e

    @property
    def client(self) -> Client:
        """Return the underlying Supabase client."""
        return self._client

    def health_check(self) -> bool:
        """Probe the database connection by querying 1 report record."""
        try:
            query = self._client.table(self.TABLE_NAME).select("id").limit(1)
            self._execute_with_retry(query, "health_check probe")
            return True
        except Exception as e:
            logger.error("Supabase health check probe failed: %s", e)
            return False

    def close(self) -> None:
        """Resource teardown (Supabase client uses connection pooling / HTTP)."""
        pass

    # -----------------------------------------------------------------------
    # Resilient Query Execution Helpers
    # -----------------------------------------------------------------------

    def _execute_with_retry(self, query_builder: Any, operation_desc: str) -> Any:
        """
        Execute a read query with exponential backoff on transient errors.
        Does NOT retry non-idempotent writes blindly.
        """
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return query_builder.execute()
            except Exception as e:
                last_err = e
                # Check for fatal unrecoverable errors (e.g. invalid credentials or malformed query)
                err_str = str(e).lower()
                if "401" in err_str or "unauthorized" in err_str or "permission denied" in err_str:
                    logger.critical("Authentication failure communicating with Supabase: %s", e)
                    raise ReportPersistenceError(f"Supabase authorization failed: {e}") from e

                if attempt == self.max_retries:
                    break
                sleep_time = self.retry_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error during %s (attempt %d/%d). Retrying in %.2fs: %s",
                    operation_desc,
                    attempt,
                    self.max_retries,
                    sleep_time,
                    e,
                )
                time.sleep(sleep_time)

        logger.error("%s failed after %d attempts: %s", operation_desc, self.max_retries, last_err)
        raise ReportPersistenceError(f"Supabase operation '{operation_desc}' failed: {last_err}") from last_err

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

        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(minutes=window_minutes)).isoformat()

        try:
            query = (
                self._client.table(self.TABLE_NAME)
                .select("latitude, longitude, created_at")
                .eq("reporter_id", reporter_id)
                .eq("category", category.value)
                .gte("created_at", window_start)
                .order("created_at", desc=True)
                .limit(10)
            )
            response = self._execute_with_retry(query, "is_duplicate_submission query")
            rows = response.data or []
        except ReportPersistenceError:
            raise
        except Exception as e:
            raise ReportPersistenceError(f"Failed to check duplicate submission: {e}") from e

        for row in rows:
            created_str = row.get("created_at")
            if not created_str or "latitude" not in row or "longitude" not in row:
                continue
            created_dt = datetime.fromisoformat(created_str)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            delta_mins = (now - created_dt).total_seconds() / 60.0
            if delta_mins <= window_minutes:
                # Approximate distance in km using equirectangular projection
                d_lat = (row["latitude"] - latitude) * 111.0
                d_lon = (row["longitude"] - longitude) * 111.0 * math.cos(math.radians(latitude))
                dist_km = math.sqrt(d_lat**2 + d_lon**2)
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
        Multiple reports from the same reporter do NOT artificially inflate corroboration.
        """
        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(hours=window_hours)).isoformat()

        try:
            query = (
                self._client.table(self.TABLE_NAME)
                .select("reporter_id, latitude, longitude, created_at")
                .eq("category", category.value)
                .gte("created_at", window_start)
            )
            response = self._execute_with_retry(query, "count_distinct_corroborating_reports query")
            rows = response.data or []
        except ReportPersistenceError:
            raise
        except Exception as e:
            raise ReportPersistenceError(f"Failed to query corroborating reports: {e}") from e

        distinct_reporters = set()
        anonymous_cluster_count = 0

        for row in rows:
            created_str = row.get("created_at")
            if not created_str or "latitude" not in row or "longitude" not in row:
                continue

            rep_id = row.get("reporter_id")
            if exclude_reporter_id and rep_id == exclude_reporter_id:
                continue

            created_dt = datetime.fromisoformat(created_str)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            delta_hours = (now - created_dt).total_seconds() / 3600.0
            if delta_hours > window_hours:
                continue

            d_lat = (row["latitude"] - latitude) * 111.0
            d_lon = (row["longitude"] - longitude) * 111.0 * math.cos(math.radians(latitude))
            dist_km = math.sqrt(d_lat**2 + d_lon**2)
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
        Validate, score, and persist a new citizen report into Supabase PostgreSQL.
        """
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

        # 5. Insert into Supabase PostgreSQL
        payload = {
            "id": report.id,
            "category": report.category.value,
            "description": report.description,
            "severity": report.severity,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "location_description": report.location_description,
            "neighbourhood_id": report.neighbourhood_id,
            "reporter_id": report.reporter_id,
            "reporter_contact": report.reporter_contact,
            "photos": [p.model_dump(mode="json") for p in report.photos],
            "status": report.status.value,
            "verification_status": report.verification_status.value,
            "is_verified_measurement": report.is_verified_measurement,
            "data_source": report.data_source,
            "urgency_score": report.urgency_score,
            "evidence_confidence_score": report.evidence_confidence_score,
            "resolution_evidence": None,
            "timeline": [t.model_dump(mode="json") for t in report.timeline],
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }

        try:
            res = self._client.table(self.TABLE_NAME).insert(payload).execute()
            if not res.data:
                raise ReportPersistenceError(f"Insert returned empty response for report {report_id}")
        except Exception as e:
            # Check for conflict / primary key duplicate
            err_msg = str(e)
            if "duplicate key" in err_msg.lower() or "unique constraint" in err_msg.lower():
                raise DuplicateReportError(f"Report with ID '{report_id}' already exists.") from e
            logger.error("Failed to insert report into Supabase: %s", e)
            raise ReportPersistenceError(f"Database insertion failed: {e}") from e

        return report

    def get_report(self, report_id: str) -> Optional[CitizenReport]:
        """Fetch a single report by its unique identifier."""
        try:
            query = self._client.table(self.TABLE_NAME).select("*").eq("id", report_id).maybe_single()
            res = self._execute_with_retry(query, f"get_report({report_id})")
            if not res or not res.data:
                return None
            return self._dict_to_model(res.data)
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to query report %s: %s", report_id, e)
            raise ReportPersistenceError(f"Failed to query report {report_id}: {e}") from e

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
        safe_limit = max(1, limit)
        safe_offset = max(0, offset)

        try:
            query = self._client.table(self.TABLE_NAME).select("*")

            if category is not None:
                query = query.eq("category", category.value)
            if status is not None:
                query = query.eq("status", status.value)
            if verification_status is not None:
                query = query.eq("verification_status", verification_status.value)
            if neighbourhood_id is not None:
                query = query.eq("neighbourhood_id", neighbourhood_id)

            query = (
                query.order("created_at", desc=True)
                .range(safe_offset, safe_offset + safe_limit - 1)
            )

            res = self._execute_with_retry(query, "list_reports query")
            rows = res.data or []
            return [self._dict_to_model(row) for row in rows]
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to list reports from Supabase: %s", e)
            raise ReportPersistenceError(f"Failed to list reports: {e}") from e

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

        # Build new timeline entry
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

        active_evidence = evidence or existing.resolution_evidence

        update_data: Dict[str, Any] = {
            "status": status.value,
            "updated_at": now_utc,
            "timeline": [t.model_dump(mode="json") for t in new_timeline],
            "resolution_evidence": active_evidence.model_dump(mode="json") if active_evidence else None,
        }
        if verification_status is not None:
            update_data["verification_status"] = verification_status.value

        try:
            res = (
                self._client.table(self.TABLE_NAME)
                .update(update_data)
                .eq("id", report_id)
                .execute()
            )
            if not res.data:
                raise ReportNotFoundError(report_id)
            return self._dict_to_model(res.data[0])
        except ReportNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update status for report %s: %s", report_id, e)
            raise ReportPersistenceError(f"Failed to update report {report_id}: {e}") from e

    def verify_resolution(
        self,
        report_id: str,
        confirmed_resolved: bool,
        feedback: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> CitizenReport:
        """Citizen confirms or rejects resolution of a report."""
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

        update_data: Dict[str, Any] = {
            "description": updated_description,
            "photos": [p.model_dump(mode="json") for p in updated_photos],
            "status": target_status.value,
            "updated_at": now_dt.isoformat(),
            "timeline": [t.model_dump(mode="json") for t in new_timeline],
        }

        try:
            res = (
                self._client.table(self.TABLE_NAME)
                .update(update_data)
                .eq("id", report_id)
                .execute()
            )
            if not res.data:
                raise ReportNotFoundError(report_id)
            return self._dict_to_model(res.data[0])
        except ReportNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to append evidence to report %s in Supabase: %s", report_id, e)
            raise ReportPersistenceError(f"Failed to append evidence to report {report_id}: {e}") from e

    def count_reports(
        self,
        category: Optional[ProblemCategory] = None,
        status: Optional[ReportStatus] = None,
    ) -> int:
        """Count total reports matching criteria."""
        try:
            query = self._client.table(self.TABLE_NAME).select("id", count="exact")
            if category is not None:
                query = query.eq("category", category.value)
            if status is not None:
                query = query.eq("status", status.value)

            # Limit to 1 row since we only need count metadata
            query = query.limit(1)
            res = self._execute_with_retry(query, "count_reports query")
            return res.count if res.count is not None else len(res.data or [])
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to count reports in Supabase: %s", e)
            raise ReportPersistenceError(f"Failed to count reports: {e}") from e

    def get_decision_brief(
        self,
        overdue_threshold_hours: int = 48,
    ) -> DecisionBriefResponse:
        """
        Aggregate operational metrics and priority items for municipal administrators in Supabase.
        """
        try:
            query = self._client.table(self.TABLE_NAME).select("*").order("created_at", desc=True).limit(1000)
            res = self._execute_with_retry(query, "get_decision_brief query")
            rows = res.data or []
            reports = [self._dict_to_model(row) for row in rows]
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to query decision brief from Supabase: %s", e)
            raise ReportPersistenceError(f"Failed to query decision brief: {e}") from e

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

        high_urgency_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        awaiting_review_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        awaiting_citizen_verification_items.sort(key=lambda x: (-x.age_hours, -x.urgency_score, x.id))
        failed_verification_items.sort(key=lambda x: (-x.urgency_score, -x.age_hours, x.id))
        overdue_items.sort(key=lambda x: (-x.age_hours, -x.urgency_score, x.id))
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
        Fetch paginated, stably-sorted reports for the priority review queue from Supabase.
        """
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        try:
            query = self._client.table(self.TABLE_NAME).select("*", count="exact")

            if status is not None:
                query = query.eq("status", status.value)
            if category is not None:
                query = query.eq("category", category.value)
            if neighbourhood_id is not None:
                if neighbourhood_id == "UNASSIGNED":
                    query = query.is_("neighbourhood_id", "null")
                else:
                    query = query.eq("neighbourhood_id", neighbourhood_id)
            if min_urgency is not None:
                query = query.gte("urgency_score", float(min_urgency))

            if sort_by == "urgency_asc":
                query = query.order("urgency_score", desc=False).order("created_at", desc=False).order("id", desc=False)
            elif sort_by == "age_desc":
                query = query.order("created_at", desc=False).order("urgency_score", desc=True).order("id", desc=False)
            elif sort_by == "age_asc":
                query = query.order("created_at", desc=True).order("urgency_score", desc=True).order("id", desc=False)
            else:
                query = query.order("urgency_score", desc=True).order("created_at", desc=False).order("id", desc=False)

            query = query.range(safe_offset, safe_offset + safe_limit - 1)
            res = self._execute_with_retry(query, "get_priority_queue query")

            total = res.count if res.count is not None else len(res.data or [])
            reports = [self._dict_to_model(row) for row in (res.data or [])]
            return reports, total
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to query priority queue from Supabase: %s", e)
            raise ReportPersistenceError(f"Failed to query priority queue: {e}") from e

    def get_geographic_risk_summary(
        self,
        time_window_days: Optional[int] = None,
        category: Optional[ProblemCategory] = None,
    ) -> GeographicRiskResponse:
        """
        Aggregate environmental reports and hazard metrics across neighbourhoods from Supabase.
        """
        now = datetime.now(timezone.utc)
        try:
            query = self._client.table(self.TABLE_NAME).select("*")
            if time_window_days is not None and time_window_days > 0:
                cutoff = (now - timedelta(days=time_window_days)).isoformat()
                query = query.gte("created_at", cutoff)
            if category is not None:
                query = query.eq("category", category.value)

            res = self._execute_with_retry(query, "get_geographic_risk_summary query")
            rows = res.data or []
            reports = [self._dict_to_model(row) for row in rows]
        except ReportPersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to query geographic risk from Supabase: %s", e)
            raise ReportPersistenceError(f"Failed to query geographic risk: {e}") from e

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

    def _dict_to_model(self, data: Dict[str, Any]) -> CitizenReport:
        """Convert a Supabase PostgreSQL row dictionary into a CitizenReport model."""
        photos_raw = data.get("photos") or []
        if isinstance(photos_raw, str):
            import json
            photos_raw = json.loads(photos_raw)

        photos = [PhotoMetadata.model_validate(p) for p in photos_raw]

        created_raw = data["created_at"]
        created_dt = (
            datetime.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else created_raw
        )
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        updated_raw = data["updated_at"]
        updated_dt = (
            datetime.fromisoformat(updated_raw)
            if isinstance(updated_raw, str)
            else updated_raw
        )
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)

        resolution_evidence = None
        raw_evidence = data.get("resolution_evidence")
        if raw_evidence:
            try:
                if isinstance(raw_evidence, str):
                    import json
                    raw_evidence = json.loads(raw_evidence)
                resolution_evidence = ResolutionEvidence.model_validate(raw_evidence)
            except Exception:
                resolution_evidence = None

        timeline = []
        raw_timeline = data.get("timeline")
        if raw_timeline:
            try:
                if isinstance(raw_timeline, str):
                    import json
                    raw_timeline = json.loads(raw_timeline)
                timeline = [StatusTransitionLog.model_validate(t) for t in raw_timeline]
            except Exception:
                timeline = []

        return CitizenReport(
            id=data["id"],
            category=ProblemCategory(data["category"]),
            description=data["description"],
            severity=int(data["severity"]),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            location_description=data.get("location_description"),
            neighbourhood_id=data.get("neighbourhood_id"),
            reporter_id=data.get("reporter_id"),
            reporter_contact=data.get("reporter_contact"),
            photos=photos,
            status=ReportStatus(data["status"]),
            verification_status=VerificationStatus(data["verification_status"]),
            is_verified_measurement=bool(data.get("is_verified_measurement", False)),
            data_source="CITIZEN_REPORT",
            urgency_score=float(data["urgency_score"]),
            evidence_confidence_score=float(data["evidence_confidence_score"]),
            resolution_evidence=resolution_evidence,
            timeline=timeline,
            created_at=created_dt,
            updated_at=updated_dt,
        )
