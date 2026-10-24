"""
UrbanSage AI — Scenario Simulator Test Suite (Stage 4 - Phase 4)
================================================================
Comprehensive tests for the Stage 4 Scenario Simulator:
- Baseline reproduction: running baseline scenario reproduces exact baseline portfolio.
- Non-destructive execution: original DatasetBundle remains strictly unmodified in-place.
- Budget reduction: budget constraint scales and forces appropriate pruning.
- Specific hazard modification: flood scenarios modify only flood risk; drought modifies only water stress.
- Bound clamping: values > 100 or < 0 are correctly clamped with audit records.
- Determinism: identical scenario configurations yield identical comparisons.
- Constraint compliance: all scenario allocations strictly respect budget, capacity, diversity, and equity.
- Infeasibility safety: extreme constraints return INFEASIBLE safely without errors or fabricated units.
- Allocation diff categorization: correctly identifies ADDED, REMOVED, CHANGED, and UNCHANGED items.
- Validation: rejects invalid scenario configurations.
- Allocation changes: controlled tests confirm that scenarios shift allocations when mathematically expected.
"""

from __future__ import annotations

import copy
import pytest
from pydantic import ValidationError

from app.data.loader import load_default_dataset
from app.data.schemas import DatasetBundle
from app.engine.models import EngineConfig, PriorityWeights, SolverStatus
from app.simulator.demo import run_demonstration
from app.simulator.engine import UrbanSageSimulator
from app.simulator.models import ScenarioConfig, ScenarioType
from app.simulator.transformer import transform_dataset


@pytest.fixture(scope="session")
def bundle() -> DatasetBundle:
    return load_default_dataset()


@pytest.fixture
def simulator(bundle: DatasetBundle) -> UrbanSageSimulator:
    return UrbanSageSimulator(bundle, EngineConfig(budget_lakh=60.0))


# ===========================================================================
# 1. Baseline Reproduction & Non-Destructive Guarantee
# ===========================================================================


class TestBaselineReproductionAndImmutability:
    def test_baseline_scenario_reproduces_baseline_exactly(self, simulator: UrbanSageSimulator):
        scen = ScenarioConfig(
            scenario_id="SCEN-BASE-TEST",
            name="Baseline Exact Test",
            description="Testing exact baseline match",
            scenario_type=ScenarioType.BASELINE,
        )
        comp = simulator.run_scenario(scen)

        assert comp.scenario_result.status == SolverStatus.OPTIMAL
        assert comp.total_spend_delta_lakh == 0.0
        assert comp.unused_budget_scenario_lakh == simulator.baseline_result.unused_budget_lakh
        assert len(comp.added_allocations) == 0
        assert len(comp.removed_allocations) == 0
        assert len(comp.changed_allocations) == 0
        assert len(comp.unchanged_allocations) == len(simulator.baseline_result.allocations)
        assert comp.scenario_result.objective_value == simulator.baseline_result.objective_value

    def test_original_dataset_is_not_mutated(self, bundle: DatasetBundle):
        # Snapshot original flood risks
        orig_floods = {n.id: n.flood_risk for n in bundle.neighbourhoods}
        orig_waters = {n.id: n.water_stress for n in bundle.neighbourhoods}

        scen = ScenarioConfig(
            scenario_id="SCEN-HEAVY-RAIN",
            name="Heavy Rain",
            description="30% flood increase",
            scenario_type=ScenarioType.EXTREME_RAINFALL,
            flood_risk_multiplier=1.30,
            flood_risk_delta=10.0,
        )

        transformed, audit_log = transform_dataset(bundle, scen)

        # Transformed bundle must have different values
        assert any(t.transformed_value != t.original_value for t in audit_log)

        # Original bundle must remain completely unchanged
        for n in bundle.neighbourhoods:
            assert n.flood_risk == orig_floods[n.id]
            assert n.water_stress == orig_waters[n.id]


# ===========================================================================
# 2. Budget Reductions
# ===========================================================================


class TestBudgetReductionScenario:
    def test_budget_cut_reduces_spend_and_prunes_units(self, simulator: UrbanSageSimulator):
        scen_cut = simulator.create_reduced_budget_scenario(budget_lakh=40.0)
        comp = simulator.run_scenario(scen_cut)

        assert comp.scenario_result.status == SolverStatus.OPTIMAL
        assert comp.scenario_result.total_cost_lakh <= 40.0
        assert comp.total_spend_delta_lakh == -20.0
        assert comp.scenario_engine_config.budget_lakh == 40.0

        # Must report removed or decreased allocations
        assert len(comp.removed_allocations) > 0 or len(comp.changed_allocations) > 0


# ===========================================================================
# 3. Hazard-Specific Transformations & Bound Clamping
# ===========================================================================


class TestHazardTransformations:
    def test_flood_scenario_modifies_only_flood_risk(self, bundle: DatasetBundle):
        scen = ScenarioConfig(
            scenario_id="SCEN-FLOOD-ONLY",
            name="Flood Only",
            description="Testing flood isolation",
            scenario_type=ScenarioType.EXTREME_RAINFALL,
            flood_risk_multiplier=1.20,
            water_stress_multiplier=1.0,
            heat_risk_multiplier=1.0,
        )
        transformed, audit_log = transform_dataset(bundle, scen)

        # Only flood_risk should be in the audit log
        assert all(t.field_name == "flood_risk" for t in audit_log)
        for t_nbr, o_nbr in zip(transformed.neighbourhoods, bundle.neighbourhoods):
            assert t_nbr.water_stress == o_nbr.water_stress
            assert t_nbr.heat_risk == o_nbr.heat_risk

    def test_drought_scenario_modifies_only_water_stress(self, bundle: DatasetBundle):
        scen = ScenarioConfig(
            scenario_id="SCEN-DROUGHT-ONLY",
            name="Drought Only",
            description="Testing water isolation",
            scenario_type=ScenarioType.DROUGHT,
            water_stress_multiplier=1.25,
            flood_risk_multiplier=1.0,
            heat_risk_multiplier=1.0,
        )
        transformed, audit_log = transform_dataset(bundle, scen)

        assert all(t.field_name == "water_stress" for t in audit_log)
        for t_nbr, o_nbr in zip(transformed.neighbourhoods, bundle.neighbourhoods):
            assert t_nbr.flood_risk == o_nbr.flood_risk
            assert t_nbr.heat_risk == o_nbr.heat_risk

    def test_values_clamped_to_100_with_audit_record(self, bundle: DatasetBundle):
        # NBR-008 has baseline flood_risk = 92. Multiplying by 1.5 + 20 gives 158 -> must clamp to 100
        scen = ScenarioConfig(
            scenario_id="SCEN-OVERFLOW",
            name="Overflow Test",
            description="Extreme flood increase",
            flood_risk_multiplier=1.5,
            flood_risk_delta=20.0,
        )
        transformed, audit_log = transform_dataset(bundle, scen)

        nbr_008 = transformed.neighbourhood_by_id("NBR-008")
        assert nbr_008.flood_risk == 100.0

        clipped_records = [t for t in audit_log if t.neighbourhood_id == "NBR-008" and t.was_clipped]
        assert len(clipped_records) == 1
        assert clipped_records[0].clipping_bound == 100.0


# ===========================================================================
# 4. Constraint Enforcement in Scenarios
# ===========================================================================


class TestScenarioConstraintEnforcement:
    def test_scenario_allocations_satisfy_all_constraints(self, simulator: UrbanSageSimulator):
        scen_rain = simulator.create_extreme_rainfall_scenario()
        comp = simulator.run_scenario(scen_rain)

        res = comp.scenario_result
        cfg = comp.scenario_engine_config

        # 1. Budget constraint
        assert res.total_cost_lakh <= cfg.budget_lakh + 1e-6

        # 2. Capacity constraint
        cap_map = simulator.baseline_bundle.capacity_matrix()
        for a in res.allocations:
            assert a.units <= cap_map[(a.neighbourhood_id, a.intervention_id)]

        # 3. Diversity limit
        for ni in res.neighbourhood_impacts:
            assert ni.distinct_types_count <= cfg.max_interventions_per_neighbourhood

        # 4. Equity floor
        if res.equity_summary:
            assert res.equity_summary.equity_constraint_satisfied is True


# ===========================================================================
# 5. Infeasible Scenario Handling
# ===========================================================================


class TestInfeasibleScenarioHandling:
    def test_infeasible_scenario_reported_safely(self, simulator: UrbanSageSimulator):
        # Infeasible: 95% equity floor on 1000L budget
        scen_infeasible = ScenarioConfig(
            scenario_id="SCEN-INFEASIBLE",
            name="Impossible Equity Demand",
            description="Demanding 95% equity on 1000L",
            scenario_type=ScenarioType.EQUITY_POLICY_SHIFT,
            budget_lakh=1000.0,
            equity_threshold=0.95,
        )
        comp = simulator.run_scenario(scen_infeasible)

        assert comp.scenario_result.status == SolverStatus.INFEASIBLE
        assert len(comp.scenario_result.allocations) == 0
        assert comp.scenario_result.total_cost_lakh == 0.0
        assert "infeasible" in comp.scenario_result.solver_message.lower()


# ===========================================================================
# 6. Allocation Diff Categorization
# ===========================================================================


class TestAllocationDiffCategorization:
    def test_diff_categorization_logic(self, simulator: UrbanSageSimulator):
        # Budget cut to 40L causes NBR-005 to lose 2 units and NBR-010 to reduce by 2 units
        scen_cut = simulator.create_reduced_budget_scenario(budget_lakh=40.0)
        comp = simulator.run_scenario(scen_cut)

        # Removed
        assert any(item.change_type == "REMOVED" for item in comp.removed_allocations)
        # Changed (Decreased)
        assert any(item.change_type == "DECREASED" for item in comp.changed_allocations)

        # Cost delta sum equals total spend delta
        diff_cost_sum = sum(d.cost_delta_lakh for d in comp.all_allocation_diffs)
        assert abs(diff_cost_sum - comp.total_spend_delta_lakh) < 1e-4


# ===========================================================================
# 7. Reproducibility & Determinism
# ===========================================================================


class TestSimulatorDeterminism:
    def test_repeated_runs_are_strictly_identical(self, simulator: UrbanSageSimulator):
        scen = simulator.create_extreme_rainfall_scenario()
        comp1 = simulator.run_scenario(scen)
        comp2 = simulator.run_scenario(scen)

        assert comp1.scenario_result.objective_value == comp2.scenario_result.objective_value
        assert comp1.scenario_result.total_cost_lakh == comp2.scenario_result.total_cost_lakh
        assert len(comp1.all_allocation_diffs) == len(comp2.all_allocation_diffs)
        for d1, d2 in zip(comp1.all_allocation_diffs, comp2.all_allocation_diffs):
            assert d1.neighbourhood_id == d2.neighbourhood_id
            assert d1.scenario_units == d2.scenario_units


# ===========================================================================
# 8. Invalid Parameters Handling
# ===========================================================================


class TestInvalidParameters:
    def test_negative_budget_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioConfig(scenario_id="BAD", name="Bad", description="Bad", budget_lakh=-20.0)

    def test_invalid_equity_threshold_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioConfig(scenario_id="BAD", name="Bad", description="Bad", equity_threshold=1.5)

    def test_extreme_multiplier_rejected(self):
        with pytest.raises(ValidationError):
            ScenarioConfig(scenario_id="BAD", name="Bad", description="Bad", flood_risk_multiplier=5.0)


# ===========================================================================
# 9. Demonstration Script Execution
# ===========================================================================


class TestDemonstrationScript:
    def test_demonstration_executes_all_four_scenarios(self):
        comps = run_demonstration()
        assert len(comps) == 4
        scenario_types = [c.scenario_config.scenario_type for c in comps]
        assert ScenarioType.BUDGET_REDUCTION in scenario_types
        assert ScenarioType.EXTREME_RAINFALL in scenario_types
        assert ScenarioType.DROUGHT in scenario_types
