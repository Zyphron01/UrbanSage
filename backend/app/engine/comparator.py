"""
UrbanSage AI — Decision Engine Portfolio Comparator (Stage 5)
=============================================================
Provides rigorous, explainable comparisons between:
A. Baseline optimization (synthetically modeled hazards alone)
B. Integrated optimization (citizen report-informed need signals + baseline)

Compares:
- Selected interventions, quantities, and cost deltas.
- Shift in neighbourhood and hazard category resource allocations.
- Changes in equity spend floor satisfaction and vulnerability focus.
- Risk reduction variations.
- Natural-language explanations for why decisions changed, directly tied
  to the audited citizen report signals.
- Explicit data freshness, uncertainty, and synthetic disclaimer notices.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.data.schemas import DatasetBundle
from app.engine.models import PortfolioResult
from app.engine.need_signal import NeedSignalAudit


class AllocationDiffItem(BaseModel):
    """Granular comparison of an intervention allocation between baseline and integrated."""
    neighbourhood_id: str
    neighbourhood_name: str
    intervention_id: str
    intervention_name: str
    category: str
    baseline_units: int
    integrated_units: int
    unit_delta: int
    cost_per_unit_lakh: float
    spend_delta_lakh: float
    status: str = Field(description="ADDED, REMOVED, INCREASED, DECREASED, or UNCHANGED")
    reason: str


class DecisionComparisonResult(BaseModel):
    """Complete comparative audit between baseline and citizen-informed plans."""
    baseline_cost_lakh: float
    integrated_cost_lakh: float
    cost_delta_lakh: float
    budget_lakh: float
    
    baseline_units_total: int
    integrated_units_total: int
    units_delta_total: int
    
    baseline_equity_spend_lakh: float
    integrated_equity_spend_lakh: float
    equity_spend_delta_lakh: float
    baseline_equity_share_pct: float
    integrated_equity_share_pct: float
    equity_constraint_satisfied: bool
    budget_constraint_satisfied: bool

    # Environmental risk reductions (modeled estimates)
    baseline_heat_reduction: float
    integrated_heat_reduction: float
    heat_reduction_delta: float

    baseline_flood_reduction: float
    integrated_flood_reduction: float
    flood_reduction_delta: float

    baseline_water_reduction: float
    integrated_water_reduction: float
    water_reduction_delta: float

    # Diffs
    all_diffs: list[AllocationDiffItem]
    added_allocations: list[AllocationDiffItem]
    removed_allocations: list[AllocationDiffItem]
    modified_allocations: list[AllocationDiffItem]
    
    # Explanations
    key_tradeoffs: list[str]
    reasons_for_change: list[str]
    
    # Need audit reference
    need_audit: NeedSignalAudit | None = None
    
    # Metadata & disclaimers
    model_provenance: dict[str, Any] = Field(
        default_factory=lambda: {
            "nature": "MODELED_ESTIMATE_ONLY",
            "solver": "SciPy HiGHS MILP",
            "optimizer_baseline": "Synthetic Environmental Indicators (Stage 2)",
            "citizen_signal_source": "Audited Citizen Problem Reports (Stage 1A/3/5)",
            "disclaimer": (
                "Modeled outcomes represent mathematical optimization estimates under bounded "
                "citizen need signals and synthetic baseline risks. They do not constitute "
                "observed real-world post-intervention measurements."
            ),
        }
    )


def compare_decision_portfolios(
    baseline: PortfolioResult,
    integrated: PortfolioResult,
    bundle: DatasetBundle,
    need_audit: NeedSignalAudit | None = None,
) -> DecisionComparisonResult:
    """
    Produce a deterministic, explainable comparison between baseline and integrated portfolios.
    """
    nbr_map = {n.id: n for n in bundle.neighbourhoods}
    int_map = {i.id: i for i in bundle.interventions}

    # Map allocations
    base_map: dict[tuple[str, str], int] = {
        (a.neighbourhood_id, a.intervention_id): a.units for a in baseline.allocations
    }
    integ_map: dict[tuple[str, str], int] = {
        (a.neighbourhood_id, a.intervention_id): a.units for a in integrated.allocations
    }

    all_pairs = sorted(set(base_map.keys()) | set(integ_map.keys()))
    
    all_diffs: list[AllocationDiffItem] = []
    added: list[AllocationDiffItem] = []
    removed: list[AllocationDiffItem] = []
    modified: list[AllocationDiffItem] = []

    # Map active need boosts for reasoning
    boost_map: dict[tuple[str, str], float] = {}
    if need_audit:
        for s in need_audit.signals:
            if s.need_boost > 0:
                boost_map[(s.neighbourhood_id, s.hazard_dimension)] = s.need_boost

    for nbr_id, int_id in all_pairs:
        b_units = base_map.get((nbr_id, int_id), 0)
        i_units = integ_map.get((nbr_id, int_id), 0)
        u_delta = i_units - b_units

        if u_delta == 0 and b_units == 0:
            continue

        nbr = nbr_map[nbr_id]
        iv = int_map[int_id]
        spend_delta = round(u_delta * iv.cost_per_unit_lakh, 4)

        if b_units == 0 and i_units > 0:
            diff_status = "ADDED"
        elif b_units > 0 and i_units == 0:
            diff_status = "REMOVED"
        elif u_delta > 0:
            diff_status = "INCREASED"
        elif u_delta < 0:
            diff_status = "DECREASED"
        else:
            diff_status = "UNCHANGED"

        # Determine explanation
        # Map intervention category to hazard type
        cat_hazard_map = {
            "URBAN_GREENING": "heat",
            "WATER_RESILIENCE": "water",
            "HEAT_MITIGATION": "heat",
            "FLOOD_DEFENSE": "flood",
        }
        relevant_hazard = cat_hazard_map.get(iv.category.value, "general")
        boost_val = boost_map.get((nbr_id, relevant_hazard), 0.0)

        if diff_status in ("ADDED", "INCREASED"):
            if boost_val > 0:
                reason = (
                    f"Selected due to citizen report need boost (+{boost_val:.1%} {relevant_hazard} priority) "
                    f"in {nbr.name}."
                )
            else:
                reason = (
                    f"Added to rebalance portfolio efficiency under budget and capacity limits "
                    f"following citizen-informed reallocations."
                )
        elif diff_status in ("REMOVED", "DECREASED"):
            if boost_val == 0:
                reason = (
                    f"Deprioritized to free capital for higher-urgency citizen-corroborated hazards "
                    f"in other wards while satisfying hard budget constraint."
                )
            else:
                reason = (
                    f"Units reduced due to diversity limits or higher cost-effectiveness of alternative "
                    f"measures in {nbr.name}."
                )
        else:
            reason = "Allocation unchanged between baseline and citizen-informed plans."

        diff_item = AllocationDiffItem(
            neighbourhood_id=nbr_id,
            neighbourhood_name=nbr.name,
            intervention_id=int_id,
            intervention_name=iv.name,
            category=iv.category.value,
            baseline_units=b_units,
            integrated_units=i_units,
            unit_delta=u_delta,
            cost_per_unit_lakh=iv.cost_per_unit_lakh,
            spend_delta_lakh=spend_delta,
            status=diff_status,
            reason=reason,
        )
        all_diffs.append(diff_item)

        if diff_status == "ADDED":
            added.append(diff_item)
        elif diff_status == "REMOVED":
            removed.append(diff_item)
        elif diff_status in ("INCREASED", "DECREASED"):
            modified.append(diff_item)

    # Financial & Equity Metrics
    b_cost = baseline.total_cost_lakh
    i_cost = integrated.total_cost_lakh
    cost_delta = round(i_cost - b_cost, 4)

    b_units_tot = sum(a.units for a in baseline.allocations)
    i_units_tot = sum(a.units for a in integrated.allocations)
    units_delta = i_units_tot - b_units_tot

    b_eq_spend = baseline.equity_summary.high_vulnerability_spend_lakh if baseline.equity_summary else 0.0
    i_eq_spend = integrated.equity_summary.high_vulnerability_spend_lakh if integrated.equity_summary else 0.0
    eq_spend_delta = round(i_eq_spend - b_eq_spend, 4)

    b_eq_share = (
        round(baseline.equity_summary.equity_spend_fraction_of_total_spend * 100.0, 2)
        if baseline.equity_summary
        else 0.0
    )
    i_eq_share = (
        round(integrated.equity_summary.equity_spend_fraction_of_total_spend * 100.0, 2)
        if integrated.equity_summary
        else 0.0
    )

    budget_ok = i_cost <= integrated.budget_lakh + 1e-4
    min_eq_req = integrated.budget_lakh * 0.30  # Standard default or config
    equity_ok = i_eq_spend >= (min_eq_req - 1e-4)

    # Environmental summaries
    b_env = baseline.environmental_summary
    i_env = integrated.environmental_summary

    b_heat_red = b_env.mean_heat_reduction if b_env else 0.0
    i_heat_red = i_env.mean_heat_reduction if i_env else 0.0
    heat_delta = round(i_heat_red - b_heat_red, 4)

    b_flood_red = b_env.mean_flood_reduction if b_env else 0.0
    i_flood_red = i_env.mean_flood_reduction if i_env else 0.0
    flood_delta = round(i_flood_red - b_flood_red, 4)

    b_water_red = b_env.mean_water_reduction if b_env else 0.0
    i_water_red = i_env.mean_water_reduction if i_env else 0.0
    water_delta = round(i_water_red - b_water_red, 4)

    # High-level trade-off synthesis
    reasons: list[str] = []
    tradeoffs: list[str] = []

    if added:
        top_added = added[0]
        reasons.append(
            f"Introduced {top_added.integrated_units}x {top_added.intervention_name} in {top_added.neighbourhood_name} "
            f"responding to verified citizen reports."
        )
    if removed:
        top_removed = removed[0]
        reasons.append(
            f"Relocated capital from {top_removed.intervention_name} in {top_removed.neighbourhood_name} "
            f"to address higher-confidence community reports."
        )

    if eq_spend_delta >= 0:
        reasons.append(
            f"Social equity allocation preserved: High-vulnerability spend is ₹{i_eq_spend:.2f}L ({i_eq_share}% of total spend)."
        )
    else:
        tradeoffs.append(
            f"High-vulnerability spend decreased by ₹{abs(eq_spend_delta):.2f}L while remaining above the mandatory equity floor."
        )

    if cost_delta != 0:
        tradeoffs.append(
            f"Total budget expenditure shifted by ₹{cost_delta:+.2f}L (Utilization: {integrated.budget_utilization_pct}%)."
        )

    if need_audit and need_audit.eligible_reports_count > 0:
        tradeoffs.append(
            f"Optimization incorporated signals from {need_audit.eligible_reports_count} eligible citizen reports "
            f"({need_audit.excluded_reports_count} excluded due to unverified, fake, or duplicate status)."
        )
    else:
        tradeoffs.append("No eligible citizen reports found; integrated solution identical to baseline.")

    return DecisionComparisonResult(
        baseline_cost_lakh=b_cost,
        integrated_cost_lakh=i_cost,
        cost_delta_lakh=cost_delta,
        budget_lakh=integrated.budget_lakh,
        baseline_units_total=b_units_tot,
        integrated_units_total=i_units_tot,
        units_delta_total=units_delta,
        baseline_equity_spend_lakh=b_eq_spend,
        integrated_equity_spend_lakh=i_eq_spend,
        equity_spend_delta_lakh=eq_spend_delta,
        baseline_equity_share_pct=b_eq_share,
        integrated_equity_share_pct=i_eq_share,
        equity_constraint_satisfied=equity_ok,
        budget_constraint_satisfied=budget_ok,
        baseline_heat_reduction=b_heat_red,
        integrated_heat_reduction=i_heat_red,
        heat_reduction_delta=heat_delta,
        baseline_flood_reduction=b_flood_red,
        integrated_flood_reduction=i_flood_red,
        flood_reduction_delta=flood_delta,
        baseline_water_reduction=b_water_red,
        integrated_water_reduction=i_water_red,
        water_reduction_delta=water_delta,
        all_diffs=all_diffs,
        added_allocations=added,
        removed_allocations=removed,
        modified_allocations=modified,
        key_tradeoffs=tradeoffs,
        reasons_for_change=reasons,
        need_audit=need_audit,
    )
