"""
UrbanSage AI — Abstract Citizen Report Repository Interface
===========================================================
Defines the standard persistence and query contract for citizen environmental reports.
All database backends (Supabase PostgreSQL, SQLite) implement this abstract base class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from app.reports.models import (
    CitizenReport,
    CitizenReportCreate,
    DecisionBriefResponse,
    GeographicRiskResponse,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    ResolutionEvidence,
    VerificationStatus,
)


class BaseCitizenReportRepository(ABC):
    """
    Abstract interface for citizen report storage, queries, and deduplication.
    """

    @abstractmethod
    def create_report(
        self,
        report_in: CitizenReportCreate,
        ward_svi: Optional[float] = None,
        allow_duplicate: bool = False,
    ) -> CitizenReport:
        """Validate, score, and persist a new citizen report."""
        ...

    @abstractmethod
    def get_report(self, report_id: str) -> Optional[CitizenReport]:
        """Retrieve a single report by its unique ID (RPT-XXXXXXXX)."""
        ...

    @abstractmethod
    def list_reports(
        self,
        category: Optional[ProblemCategory] = None,
        status: Optional[ReportStatus] = None,
        verification_status: Optional[VerificationStatus] = None,
        neighbourhood_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CitizenReport]:
        """List citizen reports matching criteria, sorted newest first."""
        ...

    @abstractmethod
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
        """Update report operational or verification status safely with audit trail."""
        ...

    @abstractmethod
    def verify_resolution(
        self,
        report_id: str,
        confirmed_resolved: bool,
        feedback: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> CitizenReport:
        """Citizen confirms or rejects resolution of a report."""
        ...

    @abstractmethod
    def add_additional_evidence(
        self,
        report_id: str,
        additional_notes: Optional[str] = None,
        photos: Optional[List[PhotoMetadata]] = None,
        actor_id: Optional[str] = None,
    ) -> CitizenReport:
        """Citizen submits additional information/photos when requested."""
        ...

    @abstractmethod
    def count_reports(
        self,
        category: Optional[ProblemCategory] = None,
        status: Optional[ReportStatus] = None,
    ) -> int:
        """Count total reports matching criteria."""
        ...

    @abstractmethod
    def is_duplicate_submission(
        self,
        reporter_id: str,
        category: ProblemCategory,
        latitude: float,
        longitude: float,
        window_minutes: int = 30,
        dist_threshold_km: float = 0.5,
    ) -> bool:
        """Check if identical report was submitted recently by the same reporter."""
        ...

    @abstractmethod
    def count_distinct_corroborating_reports(
        self,
        category: ProblemCategory,
        latitude: float,
        longitude: float,
        exclude_reporter_id: Optional[str] = None,
        radius_km: float = 0.5,
        window_hours: float = 72.0,
    ) -> int:
        """Count distinct independent reports within spatio-temporal radius."""
        ...

    @abstractmethod
    def get_decision_brief(
        self,
        overdue_threshold_hours: int = 48,
    ) -> DecisionBriefResponse:
        """Aggregate operational metrics and priority items for municipal administrators."""
        ...

    @abstractmethod
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
        """Fetch paginated, stably-sorted reports for the priority review queue."""
        ...

    @abstractmethod
    def get_geographic_risk_summary(
        self,
        time_window_days: Optional[int] = None,
        category: Optional[ProblemCategory] = None,
    ) -> GeographicRiskResponse:
        """Aggregate environmental reports and hazard metrics across neighbourhoods."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close database connection or release resources."""
        ...

    def __enter__(self) -> BaseCitizenReportRepository:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
