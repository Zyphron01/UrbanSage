"""
UrbanSage AI — Bounded Citizen Report Need Signal Engine (Stage 5)
=================================================================
Transforms raw citizen environmental reports into bounded, audit-traceable
need indicators that dynamically inform municipal resource optimization.

Mathematical Principles & Design Safeguards:
--------------------------------------------
1. Explicit Status Eligibility:
   Only active, valid operational reports influence resource allocation.
   Excluded statuses: CONFIRMED_FAKE, DUPLICATE, OUT_OF_SCOPE, NO_ACTION_REQUIRED,
   DISMISSED, RESOLVED, VERIFIED_RESOLVED.
2. Disputed Resolution Prioritization:
   Reports marked VERIFICATION_FAILED (where a citizen confirmed remediation failed)
   receive a documented priority boost (1.25x) to ensure municipal accountability.
3. Sub-linear Saturation (Anti-Gaming & Anti-Spam):
   Multiple complaints in the same ward and hazard dimension are aggregated using
   a smooth saturation function: sigma = S / (S + kappa). This guarantees that
   coordinated spam campaigns or high reporting density cannot arbitrarily dominate
   the objective function.
4. Strictly Bounded Maximum Need Adjustment:
   The citizen need signal adds at most `max_signal_boost` (default 0.25) to the
   normalized hazard dimension, ensuring baseline environmental vulnerability
   is never overridden.
5. Baseline Preservation:
   Absence of citizen reports in a neighbourhood is NEVER interpreted as absence
   of hazard. Wards with zero reports retain 100% of their synthetic baseline risk.
6. Separation of Concerns:
   Operational urgency (time-sensitivity) and evidence completeness (documentary auditability)
   are tracked as distinct components.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from pydantic import BaseModel, Field

from app.data.schemas import Neighbourhood
from app.reports.models import CitizenReport, ProblemCategory, ReportStatus

# Statuses permitted to contribute to municipal need signals
ELIGIBLE_REPORT_STATUSES: set[ReportStatus] = {
    ReportStatus.SUBMITTED,
    ReportStatus.UNDER_REVIEW,
    ReportStatus.INFO_REQUESTED,
    ReportStatus.VERIFIED,
    ReportStatus.ASSIGNED,
    ReportStatus.IN_PROGRESS,
    ReportStatus.COMPLETED_AWAITING_VERIFICATION,
    ReportStatus.VERIFICATION_FAILED,
}

# Explicitly excluded statuses that must NEVER influence optimization
EXCLUDED_REPORT_STATUSES: set[ReportStatus] = {
    ReportStatus.CONFIRMED_FAKE,
    ReportStatus.DUPLICATE,
    ReportStatus.OUT_OF_SCOPE,
    ReportStatus.NO_ACTION_REQUIRED,
    ReportStatus.DISMISSED,
    ReportStatus.RESOLVED,
    ReportStatus.VERIFIED_RESOLVED,
}

# Mapping from Citizen ProblemCategory to optimizer hazard dimension
CATEGORY_TO_HAZARD_DIMENSION: dict[ProblemCategory, str] = {
    ProblemCategory.HEAT: "heat",
    ProblemCategory.FLOODING_DRAINAGE: "flood",
    ProblemCategory.WATER_SCARCITY: "water",
    ProblemCategory.LOSS_OF_GREEN_COVER: "heat",  # Contributes to microclimate heat/cooling
}


class NeighbourhoodNeedSignal(BaseModel):
    """
    Audit-traceable need signal for a single neighbourhood and hazard dimension.
    """

    neighbourhood_id: str
    neighbourhood_name: str
    hazard_dimension: str  # "heat", "flood", "water"
    baseline_risk: float = Field(..., ge=0.0, le=100.0)
    baseline_hazard_ratio: float = Field(..., ge=0.0, le=1.0)
    eligible_reports_count: int = Field(..., ge=0)
    raw_weighted_score_sum: float = Field(..., ge=0.0)
    saturation_ratio: float = Field(..., ge=0.0, le=1.0)
    need_boost: float = Field(..., ge=0.0, le=1.0)
    effective_hazard_level: float = Field(..., ge=0.0, le=1.0)
    contributing_report_ids: list[str] = Field(default_factory=list)
    explanation: str


class NeedSignalAudit(BaseModel):
    """
    City-wide audit bundle of report-derived need signals across all neighbourhoods.
    """

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    as_of: datetime
    total_reports_evaluated: int = Field(..., ge=0)
    eligible_reports_count: int = Field(..., ge=0)
    excluded_reports_count: int = Field(..., ge=0)
    unassigned_reports_count: int = Field(..., ge=0)
    max_signal_boost: float = Field(default=0.25, ge=0.0, le=0.50)
    saturation_constant: float = Field(default=5.0, gt=0.0)
    recency_half_life_days: float = Field(default=30.0, gt=0.0)
    signals: list[NeighbourhoodNeedSignal] = Field(default_factory=list)

    def to_signal_map(self) -> dict[tuple[str, str], float]:
        """
        Export dictionary mapping (neighbourhood_id, hazard_dimension) -> effective_hazard_level in [0.0, 1.0].
        Used directly by the MILP optimizer.
        """
        return {
            (sig.neighbourhood_id, sig.hazard_dimension): sig.effective_hazard_level
            for sig in self.signals
        }

    def get_signal(self, neighbourhood_id: str, hazard_dimension: str) -> Optional[NeighbourhoodNeedSignal]:
        """Look up signal for a specific ward and hazard dimension."""
        for s in self.signals:
            if s.neighbourhood_id == neighbourhood_id and s.hazard_dimension == hazard_dimension:
                return s
        return None


class ReportNeedSignalEngine:
    """
    Deterministic engine for computing bounded, audit-traceable citizen need signals.
    """

    def __init__(
        self,
        max_signal_boost: float = 0.25,
        saturation_constant: float = 5.0,
        recency_half_life_days: float = 30.0,
        disputed_resolution_multiplier: float = 1.25,
        min_evidence_floor: float = 0.50,
    ) -> None:
        """
        Initialize the need signal calculation engine.

        Parameters:
            max_signal_boost: Maximum additive boost to hazard level [0.0, 0.35]. Default 0.25.
            saturation_constant: Saturation parameter kappa in S / (S + kappa). Default 5.0.
            recency_half_life_days: Half-life tau in days for exponential recency decay. Default 30.0.
            disputed_resolution_multiplier: Multiplier for citizen-disputed reports. Default 1.25.
            min_evidence_floor: Minimum weight floor for reports with low evidence confidence. Default 0.50.
        """
        if not (0.0 <= max_signal_boost <= 0.50):
            raise ValueError(f"max_signal_boost must be between 0.0 and 0.50; got {max_signal_boost}")
        if saturation_constant <= 0.0:
            raise ValueError(f"saturation_constant must be positive; got {saturation_constant}")
        if recency_half_life_days <= 0.0:
            raise ValueError(f"recency_half_life_days must be positive; got {recency_half_life_days}")

        self.max_signal_boost = max_signal_boost
        self.saturation_constant = saturation_constant
        self.recency_half_life_days = recency_half_life_days
        self.disputed_resolution_multiplier = disputed_resolution_multiplier
        self.min_evidence_floor = min_evidence_floor

    def compute_signals(
        self,
        reports: Sequence[CitizenReport],
        neighbourhoods: Sequence[Neighbourhood],
        as_of: Optional[datetime] = None,
    ) -> NeedSignalAudit:
        """
        Compute bounded citizen need signals for all neighbourhoods across hazard dimensions.

        Parameters:
            reports: Collection of citizen reports to evaluate.
            neighbourhoods: Collection of valid municipal neighbourhoods.
            as_of: Evaluation reference timestamp (defaults to current UTC).

        Returns:
            NeedSignalAudit containing structured signals and component breakdowns.
        """
        ref_time = as_of or datetime.now(timezone.utc)
        known_neighbourhood_ids = {n.id: n for n in neighbourhoods}

        total_evaluated = len(reports)
        eligible_count = 0
        excluded_count = 0
        unassigned_count = 0

        # Group valid reports: (neighbourhood_id, hazard_dimension) -> list[(report, weight)]
        buckets: dict[tuple[str, str], list[tuple[CitizenReport, float]]] = {}
        for nid in known_neighbourhood_ids:
            for dim in ("heat", "flood", "water"):
                buckets[(nid, dim)] = []

        for r in reports:
            # 1. Status Filter: Exclude ineligible statuses
            if r.status in EXCLUDED_REPORT_STATUSES or r.status not in ELIGIBLE_REPORT_STATUSES:
                excluded_count += 1
                continue

            # 2. Location Filter: Handle unassigned or unknown neighbourhoods explicitly
            if not r.neighbourhood_id or r.neighbourhood_id == "UNASSIGNED" or r.neighbourhood_id not in known_neighbourhood_ids:
                unassigned_count += 1
                continue

            # 3. Hazard Dimension Mapping
            dimension = CATEGORY_TO_HAZARD_DIMENSION.get(r.category)
            if not dimension:
                continue

            # 4. Compute Report Weight Components:
            # (a) Urgency component: normalized to [0.0, 1.0]
            urgency_factor = min(1.0, max(0.0, r.urgency_score / 100.0))

            # (b) Evidence confidence factor: mapped to [min_evidence_floor, 1.0]
            conf_norm = min(1.0, max(0.0, r.evidence_confidence_score / 100.0))
            evidence_factor = self.min_evidence_floor + (1.0 - self.min_evidence_floor) * conf_norm

            # (c) Recency decay: exponential decay with half-life tau
            age_seconds = max(0.0, (ref_time - r.created_at).total_seconds())
            age_days = age_seconds / 86400.0
            decay_factor = math.exp(-1.0 * (age_days * math.log(2.0)) / self.recency_half_life_days)
            # Ensure a minimal floor of 0.10 for older open tickets so chronic issues aren't erased
            recency_factor = max(0.10, decay_factor)

            # (d) Status policy multiplier
            if r.status == ReportStatus.VERIFICATION_FAILED:
                status_multiplier = self.disputed_resolution_multiplier
            elif r.status == ReportStatus.COMPLETED_AWAITING_VERIFICATION:
                status_multiplier = 0.75  # Under citizen review
            else:
                status_multiplier = 1.0

            # Combined individual report contribution
            report_weight = urgency_factor * evidence_factor * recency_factor * status_multiplier
            buckets[(r.neighbourhood_id, dimension)].append((r, report_weight))
            eligible_count += 1

        # Build signals for each (neighbourhood, dimension)
        signal_list: list[NeighbourhoodNeedSignal] = []

        for n in sorted(neighbourhoods, key=lambda x: x.id):
            for dim in ("heat", "flood", "water"):
                baseline_val = getattr(n, f"{dim}_risk" if dim != "water" else "water_stress")
                baseline_ratio = baseline_val / 100.0

                matching_reports = buckets.get((n.id, dim), [])
                report_count = len(matching_reports)
                raw_sum = sum(weight for _, weight in matching_reports)
                report_ids = [r.id for r, _ in matching_reports]

                # Sub-linear saturation
                if raw_sum > 0.0:
                    sat_ratio = raw_sum / (raw_sum + self.saturation_constant)
                    boost = round(self.max_signal_boost * sat_ratio, 4)
                else:
                    sat_ratio = 0.0
                    boost = 0.0

                effective_hazard = min(1.0, round(baseline_ratio + boost, 4))

                # Human-readable audit explanation
                if report_count == 0:
                    explanation = (
                        f"No eligible citizen reports for {dim} in {n.name}. "
                        f"Retains 100% baseline risk ({baseline_val:.1f}/100)."
                    )
                else:
                    disputed_count = sum(1 for r, _ in matching_reports if r.status == ReportStatus.VERIFICATION_FAILED)
                    disputed_note = f" (including {disputed_count} disputed resolution)" if disputed_count > 0 else ""
                    explanation = (
                        f"{n.name} ({n.id}): +{boost * 100:.1f}% {dim} need boost derived from "
                        f"{report_count} citizen reports{disputed_note} "
                        f"(raw weight sum {raw_sum:.2f}, saturation {sat_ratio * 100:.1f}%). "
                        f"Effective hazard elevated from {baseline_ratio * 100:.1f}% to {effective_hazard * 100:.1f}%."
                    )

                signal_list.append(
                    NeighbourhoodNeedSignal(
                        neighbourhood_id=n.id,
                        neighbourhood_name=n.name,
                        hazard_dimension=dim,
                        baseline_risk=baseline_val,
                        baseline_hazard_ratio=round(baseline_ratio, 4),
                        eligible_reports_count=report_count,
                        raw_weighted_score_sum=round(raw_sum, 4),
                        saturation_ratio=round(sat_ratio, 4),
                        need_boost=boost,
                        effective_hazard_level=effective_hazard,
                        contributing_report_ids=report_ids,
                        explanation=explanation,
                    )
                )

        return NeedSignalAudit(
            as_of=ref_time,
            total_reports_evaluated=total_evaluated,
            eligible_reports_count=eligible_count,
            excluded_reports_count=excluded_count,
            unassigned_reports_count=unassigned_count,
            max_signal_boost=self.max_signal_boost,
            saturation_constant=self.saturation_constant,
            recency_half_life_days=self.recency_half_life_days,
            signals=signal_list,
        )
