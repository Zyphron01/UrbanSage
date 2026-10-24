"""
UrbanSage AI — Scenario Execution and Comparison Engine (Stage 4)
==================================================================
Stress-tests urban sustainability plans against climatic and financial scenarios.

Reuses the Stage 3 UrbanSageOptimizer exclusively.
Produces structured, explainable comparisons between baseline and scenario runs.
"""

from __future__ import annotations

from typing import Mapping
from app.data.schemas import DatasetBundle, InterventionType, Neighbourhood
from app.engine.models import EngineConfig, PortfolioResult, PriorityWeights, SolverStatus
from app.engine.optimizer import UrbanSageOptimizer
from app.simulator.models import (
    AllocationDiffItem,
    ScenarioComparison,
    ScenarioConfig,
    ScenarioType,
    TransformationRecord,
)
from app.simulator.transformer import transform_dataset


class UrbanSageSimulator:
    """
    Simulation engine for stress-testing urban intervention portfolios.
    Reuses the existing mathematical optimizer without mutating baseline data.
    """

    def __init__(
        self,
        baseline_bundle: DatasetBundle,
        baseline_config: EngineConfig,
    ) -> None:
        self.baseline_bundle = baseline_bundle
        self.baseline_config = baseline_config

        # Solve baseline once using existing optimizer
        self.optimizer_baseline = UrbanSageOptimizer(self.baseline_bundle)
        self.baseline_result = self.optimizer_baseline.solve(self.baseline_config)

    def run_scenario(self, scenario_config: ScenarioConfig) -> ScenarioComparison:
        """
        Execute a simulated scenario against the baseline and produce a structured comparison.

        Parameters:
            scenario_config: Definition of climatic risk shifts, budget cuts, or policy overrides.

        Returns:
            ScenarioComparison object detailing granular allocation diffs, group impacts, and explanations.
        """
        # 1. Non-destructively transform dataset
        transformed_bundle, audit_log = transform_dataset(self.baseline_bundle, scenario_config)

        # 2. Derive scenario EngineConfig
        scenario_engine_config = EngineConfig(
            budget_lakh=(
                scenario_config.budget_lakh
                if scenario_config.budget_lakh is not None
                else self.baseline_config.budget_lakh
            ),
            equity_threshold=(
                scenario_config.equity_threshold
                if scenario_config.equity_threshold is not None
                else self.baseline_config.equity_threshold
            ),
            priority_weights=(
                scenario_config.priority_weights
                if scenario_config.priority_weights is not None
                else self.baseline_config.priority_weights
            ),
            equity_weight=(
                scenario_config.equity_weight
                if scenario_config.equity_weight is not None
                else self.baseline_config.equity_weight
            ),
            max_interventions_per_neighbourhood=(
                scenario_config.max_interventions_per_neighbourhood
                if scenario_config.max_interventions_per_neighbourhood is not None
                else self.baseline_config.max_interventions_per_neighbourhood
            ),
            high_vulnerability_svi_threshold=self.baseline_config.high_vulnerability_svi_threshold,
            risk_reduction_scale=self.baseline_config.risk_reduction_scale,
            report_need_signals=self.baseline_config.report_need_signals,
        )

        # 3. Rerun existing optimizer on transformed bundle
        scenario_optimizer = UrbanSageOptimizer(transformed_bundle)
        scenario_result = scenario_optimizer.solve(scenario_engine_config)

        # 4. Compute granular allocation diffs
        (
            all_diffs,
            added_diffs,
            removed_diffs,
            changed_diffs,
            unchanged_diffs,
        ) = self._compute_allocation_diffs(self.baseline_result, scenario_result, transformed_bundle)

        # 5. Financial & equity metrics
        spend_delta = round(scenario_result.total_cost_lakh - self.baseline_result.total_cost_lakh, 4)
        unused_budget = scenario_result.unused_budget_lakh
        util_pct = scenario_result.budget_utilization_pct

        base_hv_spend = (
            self.baseline_result.equity_summary.high_vulnerability_spend_lakh
            if self.baseline_result.equity_summary
            else 0.0
        )
        scen_hv_spend = (
            scenario_result.equity_summary.high_vulnerability_spend_lakh
            if scenario_result.equity_summary
            else 0.0
        )
        hv_spend_delta = round(scen_hv_spend - base_hv_spend, 4)

        base_hv_share = (
            self.baseline_result.equity_summary.equity_spend_fraction_of_total_spend * 100.0
            if self.baseline_result.equity_summary
            else 0.0
        )
        scen_hv_share = (
            scenario_result.equity_summary.equity_spend_fraction_of_total_spend * 100.0
            if scenario_result.equity_summary
            else 0.0
        )

        # 6. Environmental score reduction deltas
        base_env = self.baseline_result.environmental_summary
        scen_env = scenario_result.environmental_summary

        if base_env and scen_env:
            heat_red_delta = round(scen_env.mean_heat_reduction - base_env.mean_heat_reduction, 2)
            flood_red_delta = round(scen_env.mean_flood_reduction - base_env.mean_flood_reduction, 2)
            water_red_delta = round(scen_env.mean_water_reduction - base_env.mean_water_reduction, 2)

            hv_h_delta = round(scen_env.hv_mean_heat_reduction - base_env.hv_mean_heat_reduction, 2)
            hv_f_delta = round(scen_env.hv_mean_flood_reduction - base_env.hv_mean_flood_reduction, 2)
            hv_w_delta = round(scen_env.hv_mean_water_reduction - base_env.hv_mean_water_reduction, 2)
        else:
            heat_red_delta = 0.0
            flood_red_delta = 0.0
            water_red_delta = 0.0
            hv_h_delta = 0.0
            hv_f_delta = 0.0
            hv_w_delta = 0.0

        # 7. Check objective value scoring comparability
        weights_warning = None
        base_pw = self.baseline_config.priority_weights
        scen_pw = scenario_engine_config.priority_weights
        if (
            abs(base_pw.heat - scen_pw.heat) > 1e-4
            or abs(base_pw.flood - scen_pw.flood) > 1e-4
            or abs(base_pw.water - scen_pw.water) > 1e-4
        ):
            weights_warning = (
                f"Hazard priority weights differ between baseline ({base_pw.heat:.2f}H / {base_pw.flood:.2f}F / {base_pw.water:.2f}W) "
                f"and scenario ({scen_pw.heat:.2f}H / {scen_pw.flood:.2f}F / {scen_pw.water:.2f}W). "
                "Total objective values are evaluated under different scoring scales and cannot be directly compared as absolute efficiency scores."
            )

        # 8. Synthesize explanatory reasons and assumptions
        main_reasons = self._generate_explanatory_reasons(
            scenario_config,
            scenario_engine_config,
            added_diffs,
            removed_diffs,
            changed_diffs,
            spend_delta,
        )

        assumptions = [
            "All environmental outcomes are simulated indicators (0-100 scale) and do not represent empirical real-world measurements.",
            "Ward-level risk reduction utilizes uncalibrated demonstration scaling parameter gamma = 0.10 with baseline clamping.",
            "Capital expenditure is modeled as a single discrete budget allocation without multi-year phasing or cost inflation.",
            "Intervention effectiveness is treated additively without cross-intervention spatial interaction effects.",
        ]

        return ScenarioComparison(
            scenario_config=scenario_config,
            baseline_engine_config=self.baseline_config,
            scenario_engine_config=scenario_engine_config,
            baseline_result=self.baseline_result,
            scenario_result=scenario_result,
            all_allocation_diffs=all_diffs,
            added_allocations=added_diffs,
            removed_allocations=removed_diffs,
            changed_allocations=changed_diffs,
            unchanged_allocations=unchanged_diffs,
            total_spend_delta_lakh=spend_delta,
            unused_budget_scenario_lakh=unused_budget,
            budget_utilization_scenario_pct=util_pct,
            hv_spend_delta_lakh=hv_spend_delta,
            hv_spend_share_baseline_pct=round(base_hv_share, 2),
            hv_spend_share_scenario_pct=round(scen_hv_share, 2),
            simulated_heat_reduction_delta=heat_red_delta,
            simulated_flood_reduction_delta=flood_red_delta,
            simulated_water_reduction_delta=water_red_delta,
            hv_heat_reduction_delta=hv_h_delta,
            hv_flood_reduction_delta=hv_f_delta,
            hv_water_reduction_delta=hv_w_delta,
            transformation_audit_log=audit_log,
            crossover_hazard_weights_warning=weights_warning,
            main_reasons=main_reasons,
            assumptions_and_limitations=assumptions,
        )

    def _compute_allocation_diffs(
        self,
        base_res: PortfolioResult,
        scen_res: PortfolioResult,
        bundle: DatasetBundle,
    ) -> tuple[
        list[AllocationDiffItem],
        list[AllocationDiffItem],
        list[AllocationDiffItem],
        list[AllocationDiffItem],
        list[AllocationDiffItem],
    ]:
        """Compute pair-by-pair allocation differences."""
        base_map = {(a.neighbourhood_id, a.intervention_id): a for a in base_res.allocations}
        scen_map = {(a.neighbourhood_id, a.intervention_id): a for a in scen_res.allocations}

        all_keys = sorted(set(base_map.keys()) | set(scen_map.keys()))

        all_diffs: list[AllocationDiffItem] = []
        added: list[AllocationDiffItem] = []
        removed: list[AllocationDiffItem] = []
        changed: list[AllocationDiffItem] = []
        unchanged: list[AllocationDiffItem] = []

        for nbr_id, int_id in all_keys:
            base_item = base_map.get((nbr_id, int_id))
            scen_item = scen_map.get((nbr_id, int_id))

            nbr = bundle.neighbourhood_by_id(nbr_id)
            iv = bundle.intervention_by_id(int_id)

            b_units = base_item.units if base_item else 0
            s_units = scen_item.units if scen_item else 0
            u_delta = s_units - b_units

            b_cost = base_item.total_cost_lakh if base_item else 0.0
            s_cost = scen_item.total_cost_lakh if scen_item else 0.0
            c_delta = round(s_cost - b_cost, 4)

            if b_units == 0 and s_units > 0:
                chg_type = "ADDED"
            elif b_units > 0 and s_units == 0:
                chg_type = "REMOVED"
            elif s_units > b_units:
                chg_type = "INCREASED"
            elif s_units < b_units:
                chg_type = "DECREASED"
            else:
                chg_type = "UNCHANGED"

            is_hv = nbr.social_vulnerability_index >= self.baseline_config.high_vulnerability_svi_threshold

            diff_item = AllocationDiffItem(
                neighbourhood_id=nbr_id,
                neighbourhood_name=nbr.name,
                intervention_id=int_id,
                intervention_name=iv.name,
                category=iv.category.value,
                is_high_vulnerability=is_hv,
                baseline_units=b_units,
                scenario_units=s_units,
                unit_delta=u_delta,
                baseline_cost_lakh=b_cost,
                scenario_cost_lakh=s_cost,
                cost_delta_lakh=c_delta,
                change_type=chg_type,
            )

            all_diffs.append(diff_item)
            if chg_type == "ADDED":
                added.append(diff_item)
            elif chg_type == "REMOVED":
                removed.append(diff_item)
            elif chg_type in ("INCREASED", "DECREASED"):
                changed.append(diff_item)
            else:
                unchanged.append(diff_item)

        return all_diffs, added, removed, changed, unchanged

    def _generate_explanatory_reasons(
        self,
        scenario_config: ScenarioConfig,
        scenario_engine_config: EngineConfig,
        added: list[AllocationDiffItem],
        removed: list[AllocationDiffItem],
        changed: list[AllocationDiffItem],
        spend_delta: float,
    ) -> list[str]:
        """Synthesize plain-English diagnostic explanations for why allocations shifted."""
        reasons: list[str] = []

        if scenario_config.scenario_type == ScenarioType.BUDGET_REDUCTION or (
            scenario_config.budget_lakh is not None and scenario_config.budget_lakh < self.baseline_config.budget_lakh
        ):
            budget_cut = self.baseline_config.budget_lakh - scenario_engine_config.budget_lakh
            reasons.append(
                f"Capital budget was reduced by ₹{budget_cut:.1f}L (-{budget_cut/self.baseline_config.budget_lakh:.1%}), "
                f"forcing pruning of lower-priority installations to remain strictly within the reduced limit."
            )

        if scenario_config.scenario_type == ScenarioType.EXTREME_RAINFALL or scenario_config.flood_risk_multiplier > 1.0:
            reasons.append(
                f"Extreme rainfall increased flood exposure across wards (multiplier {scenario_config.flood_risk_multiplier:.2f}x "
                f"+ {scenario_config.flood_risk_delta:.1f} pts), substantially elevating the need-weighted benefit of flood mitigation."
            )

        if scenario_config.scenario_type == ScenarioType.DROUGHT or scenario_config.water_stress_multiplier > 1.0:
            reasons.append(
                f"Drought conditions elevated municipal water stress (multiplier {scenario_config.water_stress_multiplier:.2f}x "
                f"+ {scenario_config.water_stress_delta:.1f} pts), increasing the marginal utility of community rainwater storage."
            )

        if (
            scenario_config.equity_threshold is not None
            and scenario_config.equity_threshold != self.baseline_config.equity_threshold
        ):
            reasons.append(
                f"Equity floor was adjusted from {self.baseline_config.equity_threshold:.0%} to "
                f"{scenario_engine_config.equity_threshold:.0%}, altering the mandatory spend minimum for vulnerable populations."
            )

        # Allocation changes narrative
        if added:
            added_desc = ", ".join(f"{item.neighbourhood_id} ({item.intervention_name} +{item.scenario_units}u)" for item in added)
            reasons.append(f"New interventions deployed in response to scenario priorities: {added_desc}.")

        if removed:
            removed_desc = ", ".join(f"{item.neighbourhood_id} ({item.intervention_name} -{item.baseline_units}u)" for item in removed)
            reasons.append(f"Interventions de-prioritized or displaced by resource constraints: {removed_desc}.")

        if changed:
            changed_desc = ", ".join(
                f"{item.neighbourhood_id} ({item.intervention_name}: {item.baseline_units}u -> {item.scenario_units}u)"
                for item in changed
            )
            reasons.append(f"Deployment intensity scaled: {changed_desc}.")

        if not added and not removed and not changed:
            reasons.append(
                "Physical allocation remained identical to baseline despite scenario risk changes, "
                "because the top-ranked interventions retained superior cost-effectiveness ratios over alternative options."
            )

        return reasons

    # ---------------------------------------------------------------------------
    # Predefined Scenario Factories
    # ---------------------------------------------------------------------------

    @staticmethod
    def create_reduced_budget_scenario(budget_lakh: float = 40.0) -> ScenarioConfig:
        """Create a reduced capital budget scenario (e.g. ₹40L instead of ₹60L)."""
        return ScenarioConfig(
            scenario_id="SCEN-BUDGET-CUT",
            name="Reduced Capital Budget (₹40L)",
            description="Municipal fiscal austerity reducing available capital budget by 33%.",
            scenario_type=ScenarioType.BUDGET_REDUCTION,
            budget_lakh=budget_lakh,
        )

    @staticmethod
    def create_extreme_rainfall_scenario(
        flood_multiplier: float = 1.30,
        flood_delta: float = 15.0,
        elevated_flood_priority: bool = True,
    ) -> ScenarioConfig:
        """Create an extreme monsoon rainfall scenario with increased flood risk and priority."""
        weights = PriorityWeights(heat=0.15, flood=0.70, water=0.15) if elevated_flood_priority else None
        return ScenarioConfig(
            scenario_id="SCEN-EXTREME-RAIN",
            name="Extreme Monsoon Rainfall Shock",
            description="Intense precipitation event increasing ward flood risk by 30% (+15 pts) with elevated flood priority.",
            scenario_type=ScenarioType.EXTREME_RAINFALL,
            flood_risk_multiplier=flood_multiplier,
            flood_risk_delta=flood_delta,
            priority_weights=weights,
        )

    @staticmethod
    def create_drought_scenario(
        water_multiplier: float = 1.35,
        water_delta: float = 15.0,
        elevated_water_priority: bool = True,
    ) -> ScenarioConfig:
        """Create a severe dry-season drought scenario with elevated water scarcity."""
        weights = PriorityWeights(heat=0.15, flood=0.15, water=0.70) if elevated_water_priority else None
        return ScenarioConfig(
            scenario_id="SCEN-DROUGHT",
            name="Severe Dry-Season Drought",
            description="Prolonged drought increasing municipal water stress by 35% (+15 pts) with elevated water priority.",
            scenario_type=ScenarioType.DROUGHT,
            water_stress_multiplier=water_multiplier,
            water_stress_delta=water_delta,
            priority_weights=weights,
        )

    @staticmethod
    def create_equity_shift_scenario(equity_threshold: float = 0.50) -> ScenarioConfig:
        """Create a scenario testing an increased equity allocation threshold."""
        return ScenarioConfig(
            scenario_id="SCEN-EQUITY-SHIFT",
            name="Enhanced Social Equity Policy (50% Floor)",
            description="Policy mandate requiring at least 50% of capital budget dedicated to high-vulnerability neighbourhoods.",
            scenario_type=ScenarioType.EQUITY_POLICY_SHIFT,
            equity_threshold=equity_threshold,
        )
