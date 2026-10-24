"""
UrbanSage AI — Tests for Optimization Engine and Baseline Heuristic (Stage 3)
=============================================================================
Comprehensive test suite covering:
- Feasible baseline case (optimizer & heuristic)
- Budget constraint enforcement across multiple budget levels
- Capacity and land requirement enforcement (including 0-capacity sites)
- Equity floor constraint enforcement across thresholds
- Invalid inputs handling (negative budget, invalid threshold, invalid weights)
- Infeasible problem handling (explicit INFEASIBLE status, no silent relaxation)
- Solver status handling
- Correct objective calculations (manual verification against formula)
- Consistent, deterministic results for identical inputs
- Strict internal agreement between reported metrics and selected allocations
- Bounds enforcement on post-intervention risk reductions
- Comparison of optimizer vs heuristic baseline
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.data.loader import load_default_dataset
from app.data.schemas import DatasetBundle, InterventionCategory
from app.engine.baseline import UrbanSageBaselineHeuristic
from app.engine.experiments import run_all_experiments, format_results_table
from app.engine.models import (
    EngineConfig,
    PortfolioResult,
    PriorityWeights,
    SolverStatus,
)
from app.engine.optimizer import UrbanSageOptimizer
from app.engine.scoring import (
    calculate_post_intervention_risks,
    calculate_unit_environmental_benefit,
    calculate_unit_objective_value,
    evaluate_portfolio,
)


@pytest.fixture(scope="session")
def bundle() -> DatasetBundle:
    """Load default synthetic dataset once for the test session."""
    return load_default_dataset()


@pytest.fixture
def optimizer(bundle: DatasetBundle) -> UrbanSageOptimizer:
    return UrbanSageOptimizer(bundle)


@pytest.fixture
def baseline(bundle: DatasetBundle) -> UrbanSageBaselineHeuristic:
    return UrbanSageBaselineHeuristic(bundle)


# ===========================================================================
# 1. Feasible baseline cases
# ===========================================================================


class TestFeasibleRuns:
    def test_optimizer_feasible_default(self, optimizer: UrbanSageOptimizer):
        cfg = EngineConfig(budget_lakh=60.0)
        res = optimizer.solve(cfg)

        assert res.status == SolverStatus.OPTIMAL
        assert res.total_cost_lakh <= 60.0
        assert res.objective_value > 0.0
        assert len(res.allocations) > 0
        assert res.environmental_summary is not None
        assert res.equity_summary is not None
        assert res.budget_utilization_pct > 0.0

    def test_baseline_feasible_default(self, baseline: UrbanSageBaselineHeuristic):
        cfg = EngineConfig(budget_lakh=60.0)
        res = baseline.solve(cfg)

        assert res.status == SolverStatus.FEASIBLE
        assert res.total_cost_lakh <= 60.0
        assert res.objective_value > 0.0
        assert len(res.allocations) > 0
        assert res.environmental_summary is not None
        assert res.equity_summary is not None


# ===========================================================================
# 2. Budget enforcement
# ===========================================================================


class TestBudgetEnforcement:
    @pytest.mark.parametrize("budget", [15.0, 40.0, 60.0, 100.0, 200.0])
    def test_cost_never_exceeds_budget_optimizer(self, optimizer: UrbanSageOptimizer, budget: float):
        cfg = EngineConfig(budget_lakh=budget, equity_threshold=0.20)
        res = optimizer.solve(cfg)

        if res.status == SolverStatus.OPTIMAL:
            assert res.total_cost_lakh <= budget + 1e-6
            alloc_cost_sum = sum(a.total_cost_lakh for a in res.allocations)
            assert abs(alloc_cost_sum - res.total_cost_lakh) < 1e-4

    @pytest.mark.parametrize("budget", [15.0, 40.0, 60.0, 100.0])
    def test_cost_never_exceeds_budget_baseline(self, baseline: UrbanSageBaselineHeuristic, budget: float):
        cfg = EngineConfig(budget_lakh=budget, equity_threshold=0.20)
        res = baseline.solve(cfg)

        if res.status == SolverStatus.FEASIBLE:
            assert res.total_cost_lakh <= budget + 1e-6


# ===========================================================================
# 3. Capacity, land, and diversity enforcement
# ===========================================================================


class TestCapacityAndLandEnforcement:
    def test_capacity_limits_respected(self, optimizer: UrbanSageOptimizer, bundle: DatasetBundle):
        cfg = EngineConfig(budget_lakh=200.0, equity_threshold=0.20)
        res = optimizer.solve(cfg)

        cap_map = bundle.capacity_matrix()
        for item in res.allocations:
            pair = (item.neighbourhood_id, item.intervention_id)
            max_allowed = cap_map.get(pair, 0)
            assert item.units <= max_allowed, (
                f"Allocated {item.units} units of {pair} but max allowed is {max_allowed}"
            )

    def test_zero_capacity_never_allocated(self, optimizer: UrbanSageOptimizer):
        # NBR-004 and NBR-007 have 0 capacity for INT-001 (urban forest)
        cfg = EngineConfig(budget_lakh=150.0, equity_threshold=0.20)
        res = optimizer.solve(cfg)

        for item in res.allocations:
            if item.intervention_id == "INT-001":
                assert item.neighbourhood_id not in ("NBR-004", "NBR-007")

    def test_max_interventions_per_neighbourhood(self, optimizer: UrbanSageOptimizer):
        cfg = EngineConfig(budget_lakh=200.0, max_interventions_per_neighbourhood=2, equity_threshold=0.20)
        res = optimizer.solve(cfg)

        for impact in res.neighbourhood_impacts:
            assert impact.distinct_types_count <= 2


# ===========================================================================
# 4. Equity floor enforcement
# ===========================================================================


class TestEquityEnforcement:
    @pytest.mark.parametrize("threshold", [0.10, 0.20, 0.30, 0.40])
    def test_equity_floor_enforced_optimizer(self, optimizer: UrbanSageOptimizer, threshold: float):
        cfg = EngineConfig(budget_lakh=60.0, equity_threshold=threshold)
        res = optimizer.solve(cfg)

        assert res.status == SolverStatus.OPTIMAL
        assert res.equity_summary is not None
        assert res.equity_summary.equity_constraint_satisfied is True
        required_spend = threshold * 60.0
        assert res.equity_summary.high_vulnerability_spend_lakh >= required_spend - 1e-6

    def test_high_vulnerability_neighbourhood_svi(self, optimizer: UrbanSageOptimizer, bundle: DatasetBundle):
        cfg = EngineConfig(budget_lakh=60.0, equity_threshold=0.30, high_vulnerability_svi_threshold=60.0)
        res = optimizer.solve(cfg)

        for item in res.allocations:
            nbr = bundle.neighbourhood_by_id(item.neighbourhood_id)
            if item.is_high_vulnerability:
                assert nbr.social_vulnerability_index >= 60.0
            else:
                assert nbr.social_vulnerability_index < 60.0


# ===========================================================================
# 5. Invalid inputs handling
# ===========================================================================


class TestInvalidInputs:
    def test_negative_budget_optimizer(self, optimizer: UrbanSageOptimizer):
        with pytest.raises(ValidationError):
            EngineConfig(budget_lakh=-50.0)

    def test_invalid_equity_threshold(self):
        with pytest.raises(ValidationError):
            EngineConfig(budget_lakh=50.0, equity_threshold=1.5)
        with pytest.raises(ValidationError):
            EngineConfig(budget_lakh=50.0, equity_threshold=-0.1)

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValidationError):
            PriorityWeights(heat=0.5, flood=0.5, water=0.5)

    def test_weights_negative_rejected(self):
        with pytest.raises(ValidationError):
            PriorityWeights(heat=-0.2, flood=0.7, water=0.5)


# ===========================================================================
# 6. Infeasible cases and status handling
# ===========================================================================


class TestInfeasibleAndStatusHandling:
    def test_infeasible_extreme_equity_threshold(self, optimizer: UrbanSageOptimizer):
        # At budget = 1000L and 95% equity, required spend is 950L in HV neighbourhoods.
        # But total theoretical max capacity in HV is INT-001 (11*8=88) + INT-002 (20*12=240)
        # + INT-003 (33*5=165) + INT-004 (21*20=420) = 913L < 950L.
        cfg = EngineConfig(budget_lakh=1000.0, equity_threshold=0.95)
        res = optimizer.solve(cfg)

        assert res.status == SolverStatus.INFEASIBLE
        assert len(res.allocations) == 0
        assert "infeasible" in res.solver_message.lower()

    def test_baseline_handles_infeasible_equity(self, baseline: UrbanSageBaselineHeuristic):
        cfg = EngineConfig(budget_lakh=1000.0, equity_threshold=0.95)
        res = baseline.solve(cfg)

        assert res.status == SolverStatus.INFEASIBLE
        assert len(res.allocations) == 0
        assert "could not satisfy equity threshold" in res.solver_message.lower()


# ===========================================================================
# 7. Correct objective calculations
# ===========================================================================


class TestObjectiveCalculations:
    def test_unit_environmental_benefit_formula(self, bundle: DatasetBundle):
        nbr = bundle.neighbourhood_by_id("NBR-001")  # heat=62, flood=88, water=32
        iv = bundle.intervention_by_id("INT-001")   # heat_red=72, flood_red=32, water_red=38
        weights = PriorityWeights(heat=0.35, flood=0.35, water=0.30)

        expected = (
            0.35 * (62.0 / 100.0) * 72.0
            + 0.35 * (88.0 / 100.0) * 32.0
            + 0.30 * (32.0 / 100.0) * 38.0
        )
        calculated = calculate_unit_environmental_benefit(nbr, iv, weights)
        assert abs(calculated - expected) < 1e-6

    def test_unit_objective_value_formula(self, bundle: DatasetBundle):
        nbr = bundle.neighbourhood_by_id("NBR-001")  # SVI = 72
        iv = bundle.intervention_by_id("INT-001")
        weights = PriorityWeights(heat=0.35, flood=0.35, water=0.30)
        equity_weight = 0.30

        env_score = calculate_unit_environmental_benefit(nbr, iv, weights)
        expected_obj = env_score * (1.0 + 0.30 * (72.0 / 100.0))

        calculated_obj = calculate_unit_objective_value(nbr, iv, weights, equity_weight)
        assert abs(calculated_obj - expected_obj) < 1e-6

    def test_total_objective_equals_sum_of_items(self, optimizer: UrbanSageOptimizer):
        cfg = EngineConfig(budget_lakh=60.0)
        res = optimizer.solve(cfg)

        item_sum = sum(a.total_objective_contribution for a in res.allocations)
        assert abs(item_sum - res.objective_value) < 1e-3


# ===========================================================================
# 8. Determinism (consistent results for identical inputs)
# ===========================================================================


class TestDeterminism:
    def test_optimizer_deterministic(self, optimizer: UrbanSageOptimizer):
        cfg = EngineConfig(budget_lakh=60.0, equity_threshold=0.30)
        res1 = optimizer.solve(cfg)
        res2 = optimizer.solve(cfg)

        assert res1.objective_value == res2.objective_value
        assert res1.total_cost_lakh == res2.total_cost_lakh
        assert len(res1.allocations) == len(res2.allocations)
        for a1, a2 in zip(res1.allocations, res2.allocations):
            assert a1.neighbourhood_id == a2.neighbourhood_id
            assert a1.intervention_id == a2.intervention_id
            assert a1.units == a2.units

    def test_baseline_deterministic(self, baseline: UrbanSageBaselineHeuristic):
        cfg = EngineConfig(budget_lakh=60.0, equity_threshold=0.30)
        res1 = baseline.solve(cfg)
        res2 = baseline.solve(cfg)

        assert res1.objective_value == res2.objective_value
        assert res1.total_cost_lakh == res2.total_cost_lakh


# ===========================================================================
# 9. Agreement between reported metrics and selected interventions
# ===========================================================================


class TestMetricsAgreement:
    def test_internal_consistency(self, optimizer: UrbanSageOptimizer):
        cfg = EngineConfig(budget_lakh=60.0)
        res = optimizer.solve(cfg)

        # 1. Total cost agreement
        assert abs(sum(a.total_cost_lakh for a in res.allocations) - res.total_cost_lakh) < 1e-4

        # 2. Total units agreement
        total_units_alloc = sum(a.units for a in res.allocations)
        total_units_impacts = sum(ni.units_deployed for ni in res.neighbourhood_impacts)
        assert total_units_alloc == total_units_impacts

        # 3. Spend agreement by neighbourhood
        for ni in res.neighbourhood_impacts:
            expected_spend = sum(
                a.total_cost_lakh for a in res.allocations if a.neighbourhood_id == ni.neighbourhood_id
            )
            assert abs(ni.total_spend_lakh - expected_spend) < 1e-4

        # 4. Risk bounds: post = baseline - reduction
        for ni in res.neighbourhood_impacts:
            assert abs(ni.post_intervention_risks.heat - (ni.baseline_risks.heat - ni.risk_reductions.heat)) < 1e-4
            assert abs(ni.post_intervention_risks.flood - (ni.baseline_risks.flood - ni.risk_reductions.flood)) < 1e-4
            assert abs(ni.post_intervention_risks.water - (ni.baseline_risks.water - ni.risk_reductions.water)) < 1e-4

            # Post-risk never below zero
            assert ni.post_intervention_risks.heat >= 0.0
            assert ni.post_intervention_risks.flood >= 0.0
            assert ni.post_intervention_risks.water >= 0.0

            # Reduction never exceeds baseline
            assert ni.risk_reductions.heat <= ni.baseline_risks.heat + 1e-6
            assert ni.risk_reductions.flood <= ni.baseline_risks.flood + 1e-6
            assert ni.risk_reductions.water <= ni.baseline_risks.water + 1e-6


# ===========================================================================
# 10. Optimizer vs baseline comparative test
# ===========================================================================


class TestOptimizerVsBaseline:
    def test_optimizer_at_least_as_good_as_baseline(
        self, optimizer: UrbanSageOptimizer, baseline: UrbanSageBaselineHeuristic
    ):
        # On complex knapsack with 150L budget
        cfg = EngineConfig(budget_lakh=150.0, equity_threshold=0.30)
        res_opt = optimizer.solve(cfg)
        res_base = baseline.solve(cfg)

        assert res_opt.status == SolverStatus.OPTIMAL
        assert res_base.status == SolverStatus.FEASIBLE
        # MILP must be >= heuristic on objective
        assert res_opt.objective_value >= res_base.objective_value - 1e-4


# ===========================================================================
# 11. Controlled experiments runner test
# ===========================================================================


class TestExperimentsRunner:
    def test_run_all_experiments(self):
        results = run_all_experiments()
        assert len(results) == 7

        table = format_results_table(results)
        assert "Exp 1: Budget ₹60 Lakh" in table
        assert "Exp 2: Budget ₹40 Lakh" in table
        assert "Exp 3: Flood Priority" in table
        assert "Exp 4: Water Priority" in table
        assert "Exp 7: Equity Floor 40%" in table
        assert "Optimizer (MILP)" in table
        assert "Baseline (Greedy)" in table
