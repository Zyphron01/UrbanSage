"""
test_schemas.py — Unit tests for UrbanSage AI data schemas  (Stage 2)

Tests cover:
- Valid inputs pass validation
- Field-level constraints (range, pattern, type)
- Cross-field constraints (weight sum)
- DatasetBundle referential integrity
- Computed properties
- Synthetic data tag enforcement
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.data.schemas import (
    DatasetBundle,
    EffectivenessEstimate,
    InterventionCategory,
    InterventionType,
    LandAvailability,
    Neighbourhood,
    NeighbourhoodCapacity,
    OptimisationConfig,
    OptimisationWeights,
    HIGH_VULNERABILITY_SVI_DEFAULT,
)
from tests.conftest import make_capacity, make_intervention, make_neighbourhood


# ===========================================================================
# Neighbourhood — valid baseline
# ===========================================================================


class TestNeighbourhoodValid:
    def test_valid_neighbourhood_passes(self):
        n = Neighbourhood.model_validate(make_neighbourhood())
        assert n.id == "NBR-099"
        assert n.name == "Test Neighbourhood"

    def test_data_source_is_synthetic(self):
        n = Neighbourhood.model_validate(make_neighbourhood())
        assert n.data_source == "SYNTHETIC"

    def test_is_high_vulnerability_true_at_threshold(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(social_vulnerability_index=HIGH_VULNERABILITY_SVI_DEFAULT)
        )
        assert n.is_high_vulnerability is True

    def test_is_high_vulnerability_true_above_threshold(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(social_vulnerability_index=75.0)
        )
        assert n.is_high_vulnerability is True

    def test_is_high_vulnerability_false_below_threshold(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(social_vulnerability_index=59.9)
        )
        assert n.is_high_vulnerability is False

    def test_composite_risk_calculation(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(heat_risk=60.0, flood_risk=90.0, water_stress=30.0)
        )
        assert abs(n.composite_risk - 60.0) < 1e-9

    def test_composite_risk_all_zeros(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(heat_risk=0.0, flood_risk=0.0, water_stress=0.0)
        )
        assert n.composite_risk == 0.0

    def test_composite_risk_all_max(self):
        n = Neighbourhood.model_validate(
            make_neighbourhood(heat_risk=100.0, flood_risk=100.0, water_stress=100.0)
        )
        assert n.composite_risk == 100.0

    def test_population_density_positive(self):
        n = Neighbourhood.model_validate(make_neighbourhood())
        assert n.population_density_per_sqkm > 0


# ===========================================================================
# Neighbourhood — invalid inputs
# ===========================================================================


class TestNeighbourhoodInvalid:
    def test_invalid_id_pattern_short(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(id="NBR-1"))

    def test_invalid_id_pattern_prefix(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(id="NB-001"))

    def test_invalid_id_pattern_letters_in_number(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(id="NBR-ABC"))

    def test_heat_risk_above_100(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(heat_risk=100.1))

    def test_heat_risk_below_0(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(heat_risk=-1.0))

    def test_flood_risk_above_100(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(flood_risk=101))

    def test_water_stress_below_0(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(water_stress=-0.1))

    def test_svi_above_100(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(
                make_neighbourhood(social_vulnerability_index=100.1)
            )

    def test_svi_below_0(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(
                make_neighbourhood(social_vulnerability_index=-5.0)
            )

    def test_population_zero(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(population=0))

    def test_population_negative(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(population=-100))

    def test_area_zero(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(area_sqkm=0.0))

    def test_area_negative(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(area_sqkm=-1.0))

    def test_green_cover_above_100(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(current_green_cover_pct=101))

    def test_data_source_not_synthetic(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(data_source="REAL"))

    def test_data_source_wrong_case(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(data_source="synthetic"))

    def test_missing_required_field_name(self):
        data = make_neighbourhood()
        del data["name"]
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(data)

    def test_missing_land_availability(self):
        data = make_neighbourhood()
        del data["land_availability"]
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(data)

    def test_centroid_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(centroid_lat=91.0))

    def test_centroid_lon_out_of_range(self):
        with pytest.raises(ValidationError):
            Neighbourhood.model_validate(make_neighbourhood(centroid_lon=-181.0))


# ===========================================================================
# LandAvailability — field constraints
# ===========================================================================


class TestLandAvailability:
    def test_valid_land_availability(self):
        la = LandAvailability(
            urban_forest_sqm=5000,
            green_roof_sqm=3000,
            rainwater_harvesting_sites=4,
            drainage_sqm=6000,
        )
        assert la.urban_forest_sqm == 5000

    def test_zero_sqm_allowed(self):
        # Zero capacity is valid (e.g., fully built-up neighbourhood)
        la = LandAvailability(
            urban_forest_sqm=0,
            green_roof_sqm=0,
            rainwater_harvesting_sites=0,
            drainage_sqm=0,
        )
        assert la.urban_forest_sqm == 0

    def test_negative_sqm_rejected(self):
        with pytest.raises(ValidationError):
            LandAvailability(
                urban_forest_sqm=-1,
                green_roof_sqm=3000,
                rainwater_harvesting_sites=4,
                drainage_sqm=6000,
            )

    def test_negative_sites_rejected(self):
        with pytest.raises(ValidationError):
            LandAvailability(
                urban_forest_sqm=5000,
                green_roof_sqm=3000,
                rainwater_harvesting_sites=-1,
                drainage_sqm=6000,
            )


# ===========================================================================
# EffectivenessEstimate
# ===========================================================================


class TestEffectivenessEstimate:
    def test_valid_effectiveness(self):
        e = EffectivenessEstimate(
            heat_reduction=70,
            flood_reduction=30,
            water_stress_reduction=40,
            carbon_reduction=60,
        )
        assert e.composite == pytest.approx(50.0)

    def test_composite_all_zeros(self):
        e = EffectivenessEstimate(
            heat_reduction=0, flood_reduction=0, water_stress_reduction=0, carbon_reduction=0
        )
        assert e.composite == 0.0

    def test_composite_all_100(self):
        e = EffectivenessEstimate(
            heat_reduction=100, flood_reduction=100, water_stress_reduction=100, carbon_reduction=100
        )
        assert e.composite == 100.0

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            EffectivenessEstimate(
                heat_reduction=101,
                flood_reduction=50,
                water_stress_reduction=50,
                carbon_reduction=50,
            )

    def test_score_below_0_rejected(self):
        with pytest.raises(ValidationError):
            EffectivenessEstimate(
                heat_reduction=-1,
                flood_reduction=50,
                water_stress_reduction=50,
                carbon_reduction=50,
            )


# ===========================================================================
# InterventionType
# ===========================================================================


class TestInterventionTypeValid:
    def test_valid_intervention(self):
        iv = InterventionType.model_validate(make_intervention())
        assert iv.id == "INT-099"
        assert iv.category == InterventionCategory.URBAN_FOREST

    def test_all_categories_valid(self):
        for cat in ("urban_forest", "green_roof", "rainwater_harvesting", "drainage"):
            iv = InterventionType.model_validate(make_intervention(category=cat))
            assert iv.category.value == cat


class TestInterventionTypeInvalid:
    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(id="INT-1"))

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(category="solar_panels"))

    def test_cost_zero_rejected(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(cost_per_unit_lakh=0.0))

    def test_cost_negative_rejected(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(cost_per_unit_lakh=-5.0))

    def test_maintenance_negative_rejected(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(
                make_intervention(maintenance_cost_annual_lakh=-0.1)
            )

    def test_implementation_months_zero_rejected(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(implementation_months=0))

    def test_data_source_not_synthetic(self):
        with pytest.raises(ValidationError):
            InterventionType.model_validate(make_intervention(data_source="REAL"))


# ===========================================================================
# NeighbourhoodCapacity
# ===========================================================================


class TestNeighbourhoodCapacity:
    def test_valid_capacity(self):
        c = NeighbourhoodCapacity.model_validate(make_capacity())
        assert c.max_units == 3

    def test_zero_max_units_allowed(self):
        # Zero is valid — it signals infeasibility for the LP
        c = NeighbourhoodCapacity.model_validate(make_capacity(max_units=0))
        assert c.max_units == 0

    def test_negative_max_units_rejected(self):
        with pytest.raises(ValidationError):
            NeighbourhoodCapacity.model_validate(make_capacity(max_units=-1))

    def test_invalid_neighbourhood_id_pattern(self):
        with pytest.raises(ValidationError):
            NeighbourhoodCapacity.model_validate(
                make_capacity(neighbourhood_id="N-001")
            )

    def test_invalid_intervention_id_pattern(self):
        with pytest.raises(ValidationError):
            NeighbourhoodCapacity.model_validate(
                make_capacity(intervention_id="I-001")
            )

    def test_data_source_must_be_synthetic(self):
        with pytest.raises(ValidationError):
            NeighbourhoodCapacity.model_validate(make_capacity(data_source="measured"))


# ===========================================================================
# OptimisationWeights
# ===========================================================================


class TestOptimisationWeights:
    def test_default_weights_sum_to_one(self):
        w = OptimisationWeights()
        assert abs(w.environmental + w.equity + w.cost_efficiency - 1.0) < 1e-9

    def test_custom_valid_weights(self):
        w = OptimisationWeights(environmental=0.6, equity=0.3, cost_efficiency=0.1)
        assert w.environmental == 0.6

    def test_weights_not_summing_to_one_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            OptimisationWeights(environmental=0.5, equity=0.5, cost_efficiency=0.5)
        assert "sum" in str(exc_info.value).lower() or "1.0" in str(exc_info.value)

    def test_weights_summing_to_less_than_one_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationWeights(environmental=0.2, equity=0.2, cost_efficiency=0.2)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationWeights(environmental=-0.1, equity=0.6, cost_efficiency=0.5)

    def test_weight_above_one_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationWeights(environmental=1.1, equity=0.0, cost_efficiency=-0.1)


# ===========================================================================
# OptimisationConfig
# ===========================================================================


class TestOptimisationConfig:
    def test_default_config_valid(self):
        cfg = OptimisationConfig(budget_lakh=500.0)
        assert cfg.equity_threshold == pytest.approx(0.30)
        assert cfg.max_interventions_per_neighbourhood == 3
        assert cfg.high_vulnerability_svi_threshold == pytest.approx(60.0)

    def test_budget_zero_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationConfig(budget_lakh=0.0)

    def test_budget_negative_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationConfig(budget_lakh=-100.0)

    def test_equity_threshold_above_one_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationConfig(budget_lakh=500.0, equity_threshold=1.1)

    def test_max_interventions_above_four_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationConfig(budget_lakh=500.0, max_interventions_per_neighbourhood=5)

    def test_max_interventions_zero_rejected(self):
        with pytest.raises(ValidationError):
            OptimisationConfig(budget_lakh=500.0, max_interventions_per_neighbourhood=0)

    def test_custom_equity_threshold(self):
        cfg = OptimisationConfig(budget_lakh=500.0, equity_threshold=0.50)
        assert cfg.equity_threshold == pytest.approx(0.50)


# ===========================================================================
# DatasetBundle — referential integrity
# ===========================================================================


def _minimal_bundle():
    """Return dicts for a self-consistent 1-neighbourhood, 1-intervention bundle."""
    nbr = make_neighbourhood()
    inv = make_intervention()
    cap = make_capacity(neighbourhood_id="NBR-099", intervention_id="INT-099")
    return nbr, inv, cap


class TestDatasetBundle:
    def test_valid_bundle_passes(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        assert len(bundle.neighbourhoods) == 1
        assert len(bundle.interventions) == 1
        assert len(bundle.capacities) == 1

    def test_duplicate_neighbourhood_ids_rejected(self):
        nbr = Neighbourhood.model_validate(make_neighbourhood())
        inv = InterventionType.model_validate(make_intervention())
        cap = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-099", intervention_id="INT-099")
        )
        with pytest.raises(ValidationError) as exc_info:
            DatasetBundle(
                neighbourhoods=[nbr, nbr],  # duplicate
                interventions=[inv],
                capacities=[cap],
            )
        assert "Duplicate neighbourhood" in str(exc_info.value)

    def test_duplicate_intervention_ids_rejected(self):
        nbr = Neighbourhood.model_validate(make_neighbourhood())
        inv = InterventionType.model_validate(make_intervention())
        cap = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-099", intervention_id="INT-099")
        )
        with pytest.raises(ValidationError) as exc_info:
            DatasetBundle(
                neighbourhoods=[nbr],
                interventions=[inv, inv],  # duplicate
                capacities=[cap],
            )
        assert "Duplicate intervention" in str(exc_info.value)

    def test_capacity_referencing_unknown_neighbourhood_rejected(self):
        nbr = Neighbourhood.model_validate(make_neighbourhood())
        inv = InterventionType.model_validate(make_intervention())
        bad_cap = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-999", intervention_id="INT-099")
        )
        with pytest.raises(ValidationError) as exc_info:
            DatasetBundle(
                neighbourhoods=[nbr],
                interventions=[inv],
                capacities=[bad_cap],
            )
        assert "NBR-999" in str(exc_info.value)

    def test_capacity_referencing_unknown_intervention_rejected(self):
        nbr = Neighbourhood.model_validate(make_neighbourhood())
        inv = InterventionType.model_validate(make_intervention())
        bad_cap = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-099", intervention_id="INT-999")
        )
        with pytest.raises(ValidationError) as exc_info:
            DatasetBundle(
                neighbourhoods=[nbr],
                interventions=[inv],
                capacities=[bad_cap],
            )
        assert "INT-999" in str(exc_info.value)

    def test_duplicate_capacity_pairs_rejected(self):
        nbr = Neighbourhood.model_validate(make_neighbourhood())
        inv = InterventionType.model_validate(make_intervention())
        cap = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-099", intervention_id="INT-099")
        )
        with pytest.raises(ValidationError) as exc_info:
            DatasetBundle(
                neighbourhoods=[nbr],
                interventions=[inv],
                capacities=[cap, cap],  # duplicate pair
            )
        assert "Duplicate" in str(exc_info.value)

    def test_high_vulnerability_ids_computed_correctly(self):
        nbr_high = Neighbourhood.model_validate(
            make_neighbourhood(id="NBR-001", social_vulnerability_index=75.0)
        )
        nbr_low = Neighbourhood.model_validate(
            make_neighbourhood(id="NBR-002", social_vulnerability_index=40.0)
        )
        inv = InterventionType.model_validate(make_intervention())
        cap1 = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-001", intervention_id="INT-099")
        )
        cap2 = NeighbourhoodCapacity.model_validate(
            make_capacity(neighbourhood_id="NBR-002", intervention_id="INT-099")
        )
        bundle = DatasetBundle(
            neighbourhoods=[nbr_high, nbr_low],
            interventions=[inv],
            capacities=[cap1, cap2],
        )
        hv_ids = bundle.high_vulnerability_neighbourhood_ids
        assert "NBR-001" in hv_ids
        assert "NBR-002" not in hv_ids

    def test_capacity_matrix_returns_correct_lookup(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        matrix = bundle.capacity_matrix()
        assert matrix[("NBR-099", "INT-099")] == 3

    def test_intervention_by_id_found(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        found = bundle.intervention_by_id("INT-099")
        assert found.name == "Test Intervention"

    def test_intervention_by_id_not_found_raises_key_error(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        with pytest.raises(KeyError):
            bundle.intervention_by_id("INT-999")

    def test_neighbourhood_by_id_found(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        found = bundle.neighbourhood_by_id("NBR-099")
        assert found.name == "Test Neighbourhood"

    def test_neighbourhood_by_id_not_found_raises_key_error(self):
        nbr, inv, cap = _minimal_bundle()
        bundle = DatasetBundle(
            neighbourhoods=[Neighbourhood.model_validate(nbr)],
            interventions=[InterventionType.model_validate(inv)],
            capacities=[NeighbourhoodCapacity.model_validate(cap)],
        )
        with pytest.raises(KeyError):
            bundle.neighbourhood_by_id("NBR-999")
