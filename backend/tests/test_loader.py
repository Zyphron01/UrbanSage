"""
test_loader.py — Integration tests for the UrbanSage AI data loader  (Stage 2)

Tests cover:
- Loading the default synthetic dataset end-to-end
- Record counts (10 neighbourhoods, 4 interventions, 40 capacities)
- Data provenance tags (all records must be SYNTHETIC)
- High-vulnerability neighbourhood classification
- Capacity matrix completeness (all 10×4 combinations present)
- Error handling for missing files, invalid JSON, and invalid records
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data.loader import (
    load_capacities,
    load_dataset,
    load_default_dataset,
    load_interventions,
    load_neighbourhoods,
)
from app.data.schemas import DatasetBundle, InterventionCategory


# ===========================================================================
# Default dataset — end-to-end loading
# ===========================================================================


class TestLoadDefaultDataset:
    def test_load_succeeds(self, default_dataset: DatasetBundle):
        """The synthetic dataset loads without raising an exception."""
        assert default_dataset is not None

    def test_returns_dataset_bundle(self, default_dataset: DatasetBundle):
        assert isinstance(default_dataset, DatasetBundle)

    def test_ten_neighbourhoods(self, default_dataset: DatasetBundle):
        assert len(default_dataset.neighbourhoods) == 10

    def test_four_interventions(self, default_dataset: DatasetBundle):
        assert len(default_dataset.interventions) == 4

    def test_forty_capacity_records(self, default_dataset: DatasetBundle):
        """Exactly 10 neighbourhoods × 4 interventions = 40 capacity records."""
        assert len(default_dataset.capacities) == 40

    def test_all_neighbourhood_data_sources_synthetic(self, default_dataset: DatasetBundle):
        for n in default_dataset.neighbourhoods:
            assert n.data_source == "SYNTHETIC", (
                f"Neighbourhood {n.id} has data_source={n.data_source!r}"
            )

    def test_all_intervention_data_sources_synthetic(self, default_dataset: DatasetBundle):
        for iv in default_dataset.interventions:
            assert iv.data_source == "SYNTHETIC", (
                f"Intervention {iv.id} has data_source={iv.data_source!r}"
            )

    def test_all_capacity_data_sources_synthetic(self, default_dataset: DatasetBundle):
        for cap in default_dataset.capacities:
            assert cap.data_source == "SYNTHETIC"

    def test_neighbourhood_ids_unique(self, default_dataset: DatasetBundle):
        ids = [n.id for n in default_dataset.neighbourhoods]
        assert len(ids) == len(set(ids))

    def test_intervention_ids_unique(self, default_dataset: DatasetBundle):
        ids = [iv.id for iv in default_dataset.interventions]
        assert len(ids) == len(set(ids))

    def test_neighbourhood_ids_follow_pattern(self, default_dataset: DatasetBundle):
        import re
        pattern = re.compile(r"^NBR-\d{3}$")
        for n in default_dataset.neighbourhoods:
            assert pattern.match(n.id), f"Unexpected neighbourhood ID: {n.id}"

    def test_intervention_ids_follow_pattern(self, default_dataset: DatasetBundle):
        import re
        pattern = re.compile(r"^INT-\d{3}$")
        for iv in default_dataset.interventions:
            assert pattern.match(iv.id), f"Unexpected intervention ID: {iv.id}"


# ===========================================================================
# Neighbourhood content checks
# ===========================================================================


class TestNeighbourhoodData:
    def test_four_high_vulnerability_neighbourhoods(self, default_dataset: DatasetBundle):
        """
        NBR-001 (SVI 72), NBR-005 (SVI 88), NBR-008 (SVI 75), NBR-010 (SVI 68)
        should all be classified as high-vulnerability.
        """
        hv_ids = default_dataset.high_vulnerability_neighbourhood_ids
        assert len(hv_ids) == 4

    def test_expected_high_vulnerability_ids(self, default_dataset: DatasetBundle):
        hv_ids = default_dataset.high_vulnerability_neighbourhood_ids
        expected = {"NBR-001", "NBR-005", "NBR-008", "NBR-010"}
        assert hv_ids == expected

    def test_all_risk_scores_in_range(self, default_dataset: DatasetBundle):
        for n in default_dataset.neighbourhoods:
            assert 0 <= n.heat_risk <= 100, f"{n.id}: heat_risk out of range"
            assert 0 <= n.flood_risk <= 100, f"{n.id}: flood_risk out of range"
            assert 0 <= n.water_stress <= 100, f"{n.id}: water_stress out of range"
            assert 0 <= n.social_vulnerability_index <= 100, f"{n.id}: SVI out of range"

    def test_all_populations_positive(self, default_dataset: DatasetBundle):
        for n in default_dataset.neighbourhoods:
            assert n.population > 0

    def test_all_areas_positive(self, default_dataset: DatasetBundle):
        for n in default_dataset.neighbourhoods:
            assert n.area_sqkm > 0

    def test_composite_risk_within_range(self, default_dataset: DatasetBundle):
        for n in default_dataset.neighbourhoods:
            assert 0.0 <= n.composite_risk <= 100.0

    def test_old_town_core_has_zero_urban_forest(self, default_dataset: DatasetBundle):
        """NBR-004 (Old Town Core) should have zero urban forest land availability."""
        nbr = default_dataset.neighbourhood_by_id("NBR-004")
        assert nbr.land_availability.urban_forest_sqm == 0

    def test_market_district_has_zero_urban_forest(self, default_dataset: DatasetBundle):
        """NBR-007 (Market District) should have zero urban forest land availability."""
        nbr = default_dataset.neighbourhood_by_id("NBR-007")
        assert nbr.land_availability.urban_forest_sqm == 0

    def test_slum_zone_highest_svi(self, default_dataset: DatasetBundle):
        """NBR-005 (Slum Resettlement Zone) should have the highest SVI."""
        svs = {n.id: n.social_vulnerability_index for n in default_dataset.neighbourhoods}
        assert max(svs, key=svs.get) == "NBR-005"


# ===========================================================================
# Intervention content checks
# ===========================================================================


class TestInterventionData:
    def test_one_intervention_per_category(self, default_dataset: DatasetBundle):
        """All four InterventionCategory values must be represented exactly once."""
        categories = {iv.category for iv in default_dataset.interventions}
        assert categories == set(InterventionCategory)

    def test_all_costs_positive(self, default_dataset: DatasetBundle):
        for iv in default_dataset.interventions:
            assert iv.cost_per_unit_lakh > 0

    def test_all_effectiveness_scores_in_range(self, default_dataset: DatasetBundle):
        for iv in default_dataset.interventions:
            e = iv.effectiveness
            for score, label in [
                (e.heat_reduction, "heat"),
                (e.flood_reduction, "flood"),
                (e.water_stress_reduction, "water_stress"),
                (e.carbon_reduction, "carbon"),
            ]:
                assert 0 <= score <= 100, (
                    f"{iv.id}: {label} effectiveness score {score} out of range"
                )

    def test_drainage_has_highest_flood_reduction(self, default_dataset: DatasetBundle):
        """INT-004 (Drainage) should have the highest flood reduction score."""
        scores = {
            iv.id: iv.effectiveness.flood_reduction
            for iv in default_dataset.interventions
        }
        assert max(scores, key=scores.get) == "INT-004"

    def test_rwh_has_highest_water_stress_reduction(self, default_dataset: DatasetBundle):
        """INT-003 (RWH) should have the highest water stress reduction score."""
        scores = {
            iv.id: iv.effectiveness.water_stress_reduction
            for iv in default_dataset.interventions
        }
        assert max(scores, key=scores.get) == "INT-003"

    def test_all_implementation_months_positive(self, default_dataset: DatasetBundle):
        for iv in default_dataset.interventions:
            assert iv.implementation_months >= 1

    def test_assumption_notes_non_empty(self, default_dataset: DatasetBundle):
        for iv in default_dataset.interventions:
            assert len(iv.effectiveness_assumption_notes) > 20, (
                f"{iv.id}: effectiveness_assumption_notes is too short"
            )


# ===========================================================================
# Capacity matrix checks
# ===========================================================================


class TestCapacityMatrix:
    def test_all_neighbourhood_intervention_pairs_present(
        self, default_dataset: DatasetBundle
    ):
        """Every neighbourhood must have a capacity record for every intervention."""
        nbr_ids = {n.id for n in default_dataset.neighbourhoods}
        int_ids = {iv.id for iv in default_dataset.interventions}
        matrix = default_dataset.capacity_matrix()

        for nbr_id in nbr_ids:
            for int_id in int_ids:
                assert (nbr_id, int_id) in matrix, (
                    f"Missing capacity record for ({nbr_id}, {int_id})"
                )

    def test_all_max_units_non_negative(self, default_dataset: DatasetBundle):
        for cap in default_dataset.capacities:
            assert cap.max_units >= 0

    def test_old_town_core_zero_urban_forest_capacity(self, default_dataset: DatasetBundle):
        matrix = default_dataset.capacity_matrix()
        assert matrix[("NBR-004", "INT-001")] == 0

    def test_market_district_zero_urban_forest_capacity(
        self, default_dataset: DatasetBundle
    ):
        matrix = default_dataset.capacity_matrix()
        assert matrix[("NBR-007", "INT-001")] == 0

    def test_peripheral_settlement_highest_rwh_capacity(
        self, default_dataset: DatasetBundle
    ):
        """NBR-010 (Peripheral Settlement) should have max RWH capacity (10 units)."""
        matrix = default_dataset.capacity_matrix()
        rwh_capacities = {
            nbr_id: matrix.get((nbr_id, "INT-003"), 0)
            for nbr_id in {n.id for n in default_dataset.neighbourhoods}
        }
        assert max(rwh_capacities, key=rwh_capacities.get) == "NBR-010"
        assert rwh_capacities["NBR-010"] == 10

    def test_all_capacity_notes_non_empty(self, default_dataset: DatasetBundle):
        for cap in default_dataset.capacities:
            assert len(cap.feasibility_notes) > 10, (
                f"Feasibility notes too short for ({cap.neighbourhood_id}, {cap.intervention_id})"
            )


# ===========================================================================
# Error handling
# ===========================================================================


class TestLoaderErrorHandling:
    def test_missing_neighbourhoods_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_neighbourhoods(tmp_path / "nonexistent.json")

    def test_missing_interventions_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_interventions(tmp_path / "nonexistent.json")

    def test_missing_capacities_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_capacities(tmp_path / "nonexistent.json")

    def test_invalid_json_raises_value_error(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ this is not valid json }", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_neighbourhoods(bad_file)

    def test_non_list_json_raises_value_error(self, tmp_path: Path):
        # JSON object at top level instead of array
        bad_file = tmp_path / "object.json"
        bad_file.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        with pytest.raises(ValueError, match="JSON array"):
            load_neighbourhoods(bad_file)

    def test_neighbourhood_with_invalid_field_raises_value_error(self, tmp_path: Path):
        invalid_record = [{"id": "NBR-001", "heat_risk": 999}]  # missing fields + out of range
        bad_file = tmp_path / "invalid_nbr.json"
        bad_file.write_text(json.dumps(invalid_record), encoding="utf-8")
        with pytest.raises(ValueError):
            load_neighbourhoods(bad_file)

    def test_intervention_with_invalid_category_raises_value_error(self, tmp_path: Path):
        invalid_record = [{"id": "INT-001", "category": "wind_turbine"}]
        bad_file = tmp_path / "invalid_int.json"
        bad_file.write_text(json.dumps(invalid_record), encoding="utf-8")
        with pytest.raises(ValueError):
            load_interventions(bad_file)

    def test_capacity_with_negative_max_units_raises_value_error(self, tmp_path: Path):
        invalid_record = [
            {
                "neighbourhood_id": "NBR-001",
                "intervention_id": "INT-001",
                "max_units": -1,
                "feasibility_notes": "test",
                "data_source": "SYNTHETIC",
            }
        ]
        bad_file = tmp_path / "invalid_cap.json"
        bad_file.write_text(json.dumps(invalid_record), encoding="utf-8")
        with pytest.raises(ValueError):
            load_capacities(bad_file)

    def test_empty_array_loads_without_error(self, tmp_path: Path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]", encoding="utf-8")
        result = load_neighbourhoods(empty_file)
        assert result == []

    def test_load_dataset_with_mismatched_paths(self, tmp_path: Path):
        """load_dataset raises FileNotFoundError when any component file is missing."""
        with pytest.raises(FileNotFoundError):
            load_dataset(
                neighbourhoods_path=tmp_path / "missing_nbr.json",
                interventions_path=tmp_path / "missing_int.json",
                capacities_path=tmp_path / "missing_cap.json",
            )
