"""
UrbanSage AI — Mathematical Priority & Constraint Tests (Stage 3 Audit - Task 2)
================================================================================
Controlled synthetic benchmarks verifying that:
1. Flood-priority vs Water-priority weights change objective coefficients and
   shift the physical allocation when competing options are present.
2. Changing the equity floor actively shifts capital allocation from low-vulnerability
   to high-vulnerability areas.
3. The equity multiplier allows a high-vulnerability community to successfully compete
   against a lower-vulnerability community with higher physical risk.
4. Binding budget and capacity constraints correctly cap deployments.
5. Infeasible instances return SolverStatus.INFEASIBLE without silent constraint relaxation.
"""

from __future__ import annotations

import pytest
from app.data.schemas import (
    DatasetBundle,
    EffectivenessEstimate,
    InterventionCategory,
    InterventionType,
    LandAvailability,
    Neighbourhood,
    NeighbourhoodCapacity,
)
from app.engine.baseline import UrbanSageBaselineHeuristic
from app.engine.models import EngineConfig, PriorityWeights, SolverStatus
from app.engine.optimizer import UrbanSageOptimizer
from app.engine.scoring import calculate_unit_objective_value


def _create_mock_neighbourhood(
    nbr_id: str,
    name: str,
    svi: float,
    heat: float = 50.0,
    flood: float = 50.0,
    water: float = 50.0,
) -> Neighbourhood:
    return Neighbourhood(
        id=nbr_id,
        name=name,
        area_sqkm=1.0,
        population=10000,
        social_vulnerability_index=svi,
        heat_risk=heat,
        flood_risk=flood,
        water_stress=water,
        current_green_cover_pct=10.0,
        land_availability=LandAvailability(
            urban_forest_sqm=10000,
            green_roof_sqm=10000,
            rainwater_harvesting_sites=10,
            drainage_sqm=10000,
        ),
        centroid_lat=21.0,
        centroid_lon=79.0,
        description="Controlled test neighbourhood",
        data_source="SYNTHETIC",
    )


def _create_mock_intervention(
    int_id: str,
    name: str,
    cost: float,
    heat: float = 0.0,
    flood: float = 0.0,
    water: float = 0.0,
    carbon: float = 0.0,
    category: InterventionCategory = InterventionCategory.DRAINAGE,
) -> InterventionType:
    return InterventionType(
        id=int_id,
        name=name,
        category=category,
        description="Controlled test intervention",
        unit_description="1 test unit",
        cost_per_unit_lakh=cost,
        land_requirement_sqm_per_unit=500.0,
        maintenance_cost_annual_lakh=0.5,
        implementation_months=3,
        effectiveness=EffectivenessEstimate(
            heat_reduction=heat,
            flood_reduction=flood,
            water_stress_reduction=water,
            carbon_reduction=carbon,
        ),
        effectiveness_assumption_notes="Controlled test estimate",
        data_source="SYNTHETIC",
    )


class TestPriorityShifts:
    """Test 1: Priority weights shifting allocation between flood and water."""

    def test_flood_vs_water_priority_shifts_allocation(self):
        nbr = _create_mock_neighbourhood("NBR-001", "Dual-Risk Ward", svi=50.0, flood=80.0, water=80.0)

        # Two interventions with identical cost and capacity, but specializing in flood vs water
        int_flood = _create_mock_intervention(
            "INT-001", "Drainage Specialist", cost=10.0, flood=90.0, water=10.0, category=InterventionCategory.DRAINAGE
        )
        int_water = _create_mock_intervention(
            "INT-002", "RWH Specialist", cost=10.0, flood=10.0, water=90.0, category=InterventionCategory.RAINWATER_HARVESTING
        )

        caps = [
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-002", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
        ]

        bundle = DatasetBundle(neighbourhoods=[nbr], interventions=[int_flood, int_water], capacities=caps)
        optimizer = UrbanSageOptimizer(bundle)

        # Budget of 10L allows only ONE of the two interventions
        # Case A: Flood Priority (0.80 flood, 0.10 water, 0.10 heat)
        cfg_flood = EngineConfig(
            budget_lakh=10.0,
            priority_weights=PriorityWeights(heat=0.10, flood=0.80, water=0.10),
            equity_threshold=0.0,
        )
        res_flood = optimizer.solve(cfg_flood)
        assert res_flood.status == SolverStatus.OPTIMAL
        assert len(res_flood.allocations) == 1
        assert res_flood.allocations[0].intervention_id == "INT-001", "Flood priority must select Drainage Specialist"

        # Case B: Water Priority (0.10 flood, 0.80 water, 0.10 heat)
        cfg_water = EngineConfig(
            budget_lakh=10.0,
            priority_weights=PriorityWeights(heat=0.10, flood=0.10, water=0.80),
            equity_threshold=0.0,
        )
        res_water = optimizer.solve(cfg_water)
        assert res_water.status == SolverStatus.OPTIMAL
        assert len(res_water.allocations) == 1
        assert res_water.allocations[0].intervention_id == "INT-002", "Water priority must select RWH Specialist"


class TestEquityFloorShifts:
    """Test 2: Changing the equity floor actively redirects capital."""

    def test_equity_floor_forces_capital_to_vulnerable_ward(self):
        # NBR-Low (affluent, SVI=20) has high environmental cost-effectiveness
        nbr_low = _create_mock_neighbourhood("NBR-001", "Affluent Ward", svi=20.0, heat=90.0)
        # NBR-High (vulnerable, SVI=80) has lower environmental risk
        nbr_high = _create_mock_neighbourhood("NBR-002", "Vulnerable Ward", svi=80.0, heat=50.0)

        int_unit = _create_mock_intervention("INT-001", "Forest", cost=10.0, heat=80.0, category=InterventionCategory.URBAN_FOREST)

        caps = [
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-001", max_units=2, feasibility_notes="", data_source="SYNTHETIC"),
            NeighbourhoodCapacity(neighbourhood_id="NBR-002", intervention_id="INT-001", max_units=2, feasibility_notes="", data_source="SYNTHETIC"),
        ]

        bundle = DatasetBundle(neighbourhoods=[nbr_low, nbr_high], interventions=[int_unit], capacities=caps)
        optimizer = UrbanSageOptimizer(bundle)

        # Budget = 20L allows 2 units
        # Case A: 0% Equity Floor -> pure efficiency puts all 20L in NBR-Low
        cfg_0 = EngineConfig(budget_lakh=20.0, equity_threshold=0.0, equity_weight=0.0)
        res_0 = optimizer.solve(cfg_0)
        assert res_0.status == SolverStatus.OPTIMAL
        allocs_0 = {a.neighbourhood_id: a.units for a in res_0.allocations}
        assert allocs_0.get("NBR-001") == 2
        assert "NBR-002" not in allocs_0

        # Case B: 50% Equity Floor -> forces at least 10L to NBR-High
        cfg_50 = EngineConfig(budget_lakh=20.0, equity_threshold=0.50, equity_weight=0.0)
        res_50 = optimizer.solve(cfg_50)
        assert res_50.status == SolverStatus.OPTIMAL
        allocs_50 = {a.neighbourhood_id: a.units for a in res_50.allocations}
        assert allocs_50.get("NBR-001") == 1
        assert allocs_50.get("NBR-002") == 1

        # Case C: 100% Equity Floor -> forces all 20L to NBR-High
        cfg_100 = EngineConfig(budget_lakh=20.0, equity_threshold=1.00, equity_weight=0.0)
        res_100 = optimizer.solve(cfg_100)
        assert res_100.status == SolverStatus.OPTIMAL
        allocs_100 = {a.neighbourhood_id: a.units for a in res_100.allocations}
        assert "NBR-001" not in allocs_100
        assert allocs_100.get("NBR-002") == 2


class TestEquityMultiplierCompetition:
    """Test 3: High-vulnerability ward competing with lower-vulnerability ward via multiplier."""

    def test_equity_multiplier_flips_allocation(self):
        # NBR-Low has higher physical risk (80 vs 60), but low SVI (10 vs 85)
        nbr_low = _create_mock_neighbourhood("NBR-001", "Low SVI Ward", svi=10.0, heat=80.0)
        nbr_high = _create_mock_neighbourhood("NBR-002", "High SVI Ward", svi=85.0, heat=60.0)

        int_unit = _create_mock_intervention("INT-001", "Cooling Unit", cost=10.0, heat=80.0, category=InterventionCategory.URBAN_FOREST)

        caps = [
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
            NeighbourhoodCapacity(neighbourhood_id="NBR-002", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
        ]

        bundle = DatasetBundle(neighbourhoods=[nbr_low, nbr_high], interventions=[int_unit], capacities=caps)
        optimizer = UrbanSageOptimizer(bundle)

        # Budget allows only 1 unit. Equity floor is 0% to isolate the multiplier effect.
        weights = PriorityWeights(heat=1.0, flood=0.0, water=0.0)

        # Case A: Without equity multiplier (equity_weight=0.0) -> NBR-Low wins on raw risk need (80 > 60)
        cfg_raw = EngineConfig(budget_lakh=10.0, priority_weights=weights, equity_weight=0.0, equity_threshold=0.0)
        res_raw = optimizer.solve(cfg_raw)
        assert res_raw.status == SolverStatus.OPTIMAL
        assert res_raw.allocations[0].neighbourhood_id == "NBR-001"

        # Case B: With equity multiplier (equity_weight=0.60)
        # NBR-Low: 0.80 * 80 * (1 + 0.60 * 0.10) = 64 * 1.06 = 67.84
        # NBR-High: 0.60 * 80 * (1 + 0.60 * 0.85) = 48 * 1.51 = 72.48
        # NBR-High flips to win!
        cfg_equity = EngineConfig(budget_lakh=10.0, priority_weights=weights, equity_weight=0.60, equity_threshold=0.0)
        res_equity = optimizer.solve(cfg_equity)
        assert res_equity.status == SolverStatus.OPTIMAL
        assert res_equity.allocations[0].neighbourhood_id == "NBR-002"


class TestBindingConstraintsAndInfeasibility:
    """Test 4 & 5: Binding constraints and explicit infeasibility reporting."""

    def test_binding_capacity_spills_over_to_next_best(self):
        nbr_a = _create_mock_neighbourhood("NBR-001", "Top Ward", svi=70.0, heat=90.0)
        nbr_b = _create_mock_neighbourhood("NBR-002", "Second Ward", svi=70.0, heat=70.0)

        int_unit = _create_mock_intervention("INT-001", "Forest", cost=10.0, heat=80.0, category=InterventionCategory.URBAN_FOREST)

        # NBR-A has capacity 1, NBR-B has capacity 1
        caps = [
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
            NeighbourhoodCapacity(neighbourhood_id="NBR-002", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
        ]

        bundle = DatasetBundle(neighbourhoods=[nbr_a, nbr_b], interventions=[int_unit], capacities=caps)
        optimizer = UrbanSageOptimizer(bundle)

        # Budget of 20L allows 2 units. Even though NBR-A has higher value, capacity caps it at 1.
        cfg = EngineConfig(budget_lakh=20.0, priority_weights=PriorityWeights(heat=1.0, flood=0.0, water=0.0))
        res = optimizer.solve(cfg)

        assert res.status == SolverStatus.OPTIMAL
        assert len(res.allocations) == 2
        alloc_map = {a.neighbourhood_id: a.units for a in res.allocations}
        assert alloc_map["NBR-001"] == 1
        assert alloc_map["NBR-002"] == 1
        assert any("Capacity: NBR-001" in b for b in res.binding_constraints)

    def test_explicit_infeasibility_when_equity_floor_impossible(self):
        # Only 1 HV ward with max capacity 1 (cost 10L)
        nbr_hv = _create_mock_neighbourhood("NBR-001", "HV Ward", svi=80.0)
        nbr_non_hv = _create_mock_neighbourhood("NBR-002", "Non-HV Ward", svi=20.0)

        int_unit = _create_mock_intervention("INT-001", "Forest", cost=10.0, heat=80.0, category=InterventionCategory.URBAN_FOREST)

        caps = [
            NeighbourhoodCapacity(neighbourhood_id="NBR-001", intervention_id="INT-001", max_units=1, feasibility_notes="", data_source="SYNTHETIC"),
            NeighbourhoodCapacity(neighbourhood_id="NBR-002", intervention_id="INT-001", max_units=5, feasibility_notes="", data_source="SYNTHETIC"),
        ]

        bundle = DatasetBundle(neighbourhoods=[nbr_hv, nbr_non_hv], interventions=[int_unit], capacities=caps)
        optimizer = UrbanSageOptimizer(bundle)

        # Budget = 30L. Equity threshold = 60% requires at least 18L in HV.
        # But max possible HV capacity is 1 unit = 10L. Impossible!
        cfg = EngineConfig(budget_lakh=30.0, equity_threshold=0.60)
        res = optimizer.solve(cfg)

        assert res.status == SolverStatus.INFEASIBLE
        assert len(res.allocations) == 0
        assert "infeasible" in res.solver_message.lower()
