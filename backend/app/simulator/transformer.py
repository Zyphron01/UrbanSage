"""
UrbanSage AI — Non-Destructive Dataset Transformer (Stage 4)
=============================================================
Applies explicit, deterministic, and non-destructive transformations to
neighbourhood risk inputs based on scenario parameters.

Guarantees:
- Never mutates the original DatasetBundle in-place.
- Strict bound validation: all transformed risks are clamped to [0.0, 100.0].
- Comprehensive audit log tracking every transformed field and whether clipping occurred.
"""

from __future__ import annotations

from app.data.schemas import DatasetBundle, Neighbourhood
from app.simulator.models import ScenarioConfig, TransformationRecord


def transform_dataset(
    original_bundle: DatasetBundle,
    scenario_config: ScenarioConfig,
) -> tuple[DatasetBundle, list[TransformationRecord]]:
    """
    Produce a new, independent DatasetBundle with hazard risks adjusted according
    to the scenario configuration.

    The original_bundle is guaranteed to remain completely untouched.

    Parameters:
        original_bundle: The baseline DatasetBundle (loaded from synthetic data).
        scenario_config: The scenario configuration defining hazard multipliers/deltas.

    Returns:
        (transformed_bundle, transformation_audit_log)
    """
    audit_log: list[TransformationRecord] = []
    transformed_neighbourhoods: list[Neighbourhood] = []

    for orig_nbr in original_bundle.neighbourhoods:
        # Create a deep copy of the neighbourhood model
        nbr_dict = orig_nbr.model_dump()

        # Transform Flood Risk
        orig_flood = orig_nbr.flood_risk
        raw_flood = (orig_flood * scenario_config.flood_risk_multiplier) + scenario_config.flood_risk_delta
        clamped_flood = max(0.0, min(100.0, raw_flood))
        was_flood_clipped = abs(clamped_flood - raw_flood) > 1e-5
        clip_bound_flood = 100.0 if raw_flood > 100.0 else (0.0 if raw_flood < 0.0 else None)

        if abs(clamped_flood - orig_flood) > 1e-5:
            audit_log.append(
                TransformationRecord(
                    neighbourhood_id=orig_nbr.id,
                    neighbourhood_name=orig_nbr.name,
                    field_name="flood_risk",
                    original_value=round(orig_flood, 2),
                    transformed_value=round(clamped_flood, 2),
                    was_clipped=was_flood_clipped,
                    clipping_bound=clip_bound_flood,
                    transformation_formula=(
                        f"({orig_flood:.1f} * {scenario_config.flood_risk_multiplier:.2f}) + "
                        f"{scenario_config.flood_risk_delta:.1f} = {raw_flood:.2f} -> {clamped_flood:.2f}"
                    ),
                )
            )
        nbr_dict["flood_risk"] = clamped_flood

        # Transform Water Stress
        orig_water = orig_nbr.water_stress
        raw_water = (orig_water * scenario_config.water_stress_multiplier) + scenario_config.water_stress_delta
        clamped_water = max(0.0, min(100.0, raw_water))
        was_water_clipped = abs(clamped_water - raw_water) > 1e-5
        clip_bound_water = 100.0 if raw_water > 100.0 else (0.0 if raw_water < 0.0 else None)

        if abs(clamped_water - orig_water) > 1e-5:
            audit_log.append(
                TransformationRecord(
                    neighbourhood_id=orig_nbr.id,
                    neighbourhood_name=orig_nbr.name,
                    field_name="water_stress",
                    original_value=round(orig_water, 2),
                    transformed_value=round(clamped_water, 2),
                    was_clipped=was_water_clipped,
                    clipping_bound=clip_bound_water,
                    transformation_formula=(
                        f"({orig_water:.1f} * {scenario_config.water_stress_multiplier:.2f}) + "
                        f"{scenario_config.water_stress_delta:.1f} = {raw_water:.2f} -> {clamped_water:.2f}"
                    ),
                )
            )
        nbr_dict["water_stress"] = clamped_water

        # Transform Heat Risk
        orig_heat = orig_nbr.heat_risk
        raw_heat = (orig_heat * scenario_config.heat_risk_multiplier) + scenario_config.heat_risk_delta
        clamped_heat = max(0.0, min(100.0, raw_heat))
        was_heat_clipped = abs(clamped_heat - raw_heat) > 1e-5
        clip_bound_heat = 100.0 if raw_heat > 100.0 else (0.0 if raw_heat < 0.0 else None)

        if abs(clamped_heat - orig_heat) > 1e-5:
            audit_log.append(
                TransformationRecord(
                    neighbourhood_id=orig_nbr.id,
                    neighbourhood_name=orig_nbr.name,
                    field_name="heat_risk",
                    original_value=round(orig_heat, 2),
                    transformed_value=round(clamped_heat, 2),
                    was_clipped=was_heat_clipped,
                    clipping_bound=clip_bound_heat,
                    transformation_formula=(
                        f"({orig_heat:.1f} * {scenario_config.heat_risk_multiplier:.2f}) + "
                        f"{scenario_config.heat_risk_delta:.1f} = {raw_heat:.2f} -> {clamped_heat:.2f}"
                    ),
                )
            )
        nbr_dict["heat_risk"] = clamped_heat

        transformed_neighbourhoods.append(Neighbourhood.model_validate(nbr_dict))

    # Deep copies of interventions and capacities
    interventions_copy = [iv.model_copy(deep=True) for iv in original_bundle.interventions]
    capacities_copy = [cap.model_copy(deep=True) for cap in original_bundle.capacities]

    transformed_bundle = DatasetBundle(
        neighbourhoods=transformed_neighbourhoods,
        interventions=interventions_copy,
        capacities=capacities_copy,
    )

    return transformed_bundle, audit_log
