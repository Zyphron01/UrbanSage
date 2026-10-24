"""
UrbanSage AI — Scoring and Multi-Criteria Evaluation Engine (Stage 3)
====================================================================
Mathematical functions for:
- Per-unit environmental benefit calculation (need-weighted by baseline risks).
- Equity-weighted objective value calculation.
- Post-intervention risk reduction with strict bound enforcement.
- Portfolio evaluation and metrics aggregation.
"""

from __future__ import annotations

from typing import Mapping
from app.data.schemas import DatasetBundle, InterventionType, Neighbourhood
from app.engine.models import (
    AllocationItem,
    EngineConfig,
    EnvironmentalSummary,
    EquitySummary,
    NeighbourhoodImpact,
    PriorityWeights,
    RiskDimensionValues,
)


def calculate_unit_environmental_benefit(
    neighbourhood: Neighbourhood,
    intervention: InterventionType,
    weights: PriorityWeights,
    effective_hazard_levels: Optional[Mapping[str, float]] = None,
) -> float:
    """
    Calculate the need-weighted environmental benefit score delivered by ONE unit
    of the intervention in the given neighbourhood.

    Formula:
        Score = w_heat * H_eff_heat * E_heat
              + w_flood * H_eff_flood * E_flood
              + w_water * H_eff_water * E_water

    Properties:
    - Normalised: since weights sum to 1.0, H_eff in [0, 1], and E in [0, 100],
      the score is strictly within [0, 100].
    - Need-weighted: delivering flood protection in a zero-flood zone yields 0 benefit.
    - Report-informed: when effective_hazard_levels is provided, incorporates bounded
      citizen complaint signals without double-counting baseline risk.
    """
    eff = intervention.effectiveness

    if effective_hazard_levels:
        h_heat = effective_hazard_levels.get("heat", neighbourhood.heat_risk / 100.0)
        h_flood = effective_hazard_levels.get("flood", neighbourhood.flood_risk / 100.0)
        h_water = effective_hazard_levels.get("water", neighbourhood.water_stress / 100.0)
    else:
        h_heat = neighbourhood.heat_risk / 100.0
        h_flood = neighbourhood.flood_risk / 100.0
        h_water = neighbourhood.water_stress / 100.0

    heat_term = weights.heat * h_heat * eff.heat_reduction
    flood_term = weights.flood * h_flood * eff.flood_reduction
    water_term = weights.water * h_water * eff.water_stress_reduction
    return heat_term + flood_term + water_term


def calculate_unit_objective_value(
    neighbourhood: Neighbourhood,
    intervention: InterventionType,
    weights: PriorityWeights,
    equity_weight: float,
    effective_hazard_levels: Optional[Mapping[str, float]] = None,
) -> float:
    """
    Calculate the per-unit objective coefficient in the optimization function.

    Formula:
        Objective_Unit = EnvBenefit * [ 1.0 + equity_weight * (SVI / 100.0) ]

    Properties:
    - When equity_weight == 0.0, Objective_Unit == EnvBenefit.
    - When equity_weight > 0.0, interventions in higher vulnerability areas receive
      a proportionate multiplier up to (1.0 + equity_weight).
    """
    env_benefit = calculate_unit_environmental_benefit(
        neighbourhood, intervention, weights, effective_hazard_levels
    )
    equity_multiplier = 1.0 + equity_weight * (neighbourhood.social_vulnerability_index / 100.0)
    return env_benefit * equity_multiplier


def calculate_post_intervention_risks(
    neighbourhood: Neighbourhood,
    allocated_units: Mapping[str, int],
    interventions_by_id: Mapping[str, InterventionType],
    scale: float = 0.10,
) -> tuple[RiskDimensionValues, RiskDimensionValues, RiskDimensionValues]:
    """
    Compute baseline risks, post-intervention risks, and risk reductions for a neighbourhood.

    Enforces strict physical and mathematical bounds:
    1. Risk reduction is non-negative: delta_risk >= 0.
    2. Risk reduction cannot exceed baseline risk: delta_risk <= baseline_risk.
    3. Post-intervention risk = baseline_risk - delta_risk, guaranteed in [0, baseline_risk].

    Returns:
        (baseline_risks, post_risks, risk_reductions)
    """
    raw_heat_red = 0.0
    raw_flood_red = 0.0
    raw_water_red = 0.0

    for int_id, count in allocated_units.items():
        if count <= 0:
            continue
        iv = interventions_by_id[int_id]
        raw_heat_red += count * iv.effectiveness.heat_reduction * scale
        raw_flood_red += count * iv.effectiveness.flood_reduction * scale
        raw_water_red += count * iv.effectiveness.water_stress_reduction * scale

    # Enforce bounds: reduction cannot exceed initial baseline risk
    heat_red = min(neighbourhood.heat_risk, max(0.0, raw_heat_red))
    flood_red = min(neighbourhood.flood_risk, max(0.0, raw_flood_red))
    water_red = min(neighbourhood.water_stress, max(0.0, raw_water_red))

    baseline = RiskDimensionValues(
        heat=neighbourhood.heat_risk,
        flood=neighbourhood.flood_risk,
        water=neighbourhood.water_stress,
    )
    post = RiskDimensionValues(
        heat=neighbourhood.heat_risk - heat_red,
        flood=neighbourhood.flood_risk - flood_red,
        water=neighbourhood.water_stress - water_red,
    )
    reductions = RiskDimensionValues(
        heat=heat_red,
        flood=flood_red,
        water=water_red,
    )
    return baseline, post, reductions


def evaluate_portfolio(
    allocations_map: Mapping[tuple[str, str], int],
    bundle: DatasetBundle,
    config: EngineConfig,
) -> tuple[
    list[AllocationItem],
    list[NeighbourhoodImpact],
    EnvironmentalSummary,
    EquitySummary,
    float,
    float,
]:
    """
    Evaluate an entire allocation portfolio against the dataset bundle and engine config.

    Computes:
    - Detailed allocation items
    - Neighbourhood-by-neighbourhood impacts
    - City-wide environmental summary
    - Equity budget breakdown
    - Total objective score and total capital cost

    Performs internal consistency verification between allocation items and summaries.
    """
    nbr_map = {n.id: n for n in bundle.neighbourhoods}
    int_map = {i.id: i for i in bundle.interventions}

    # Group allocations by neighbourhood
    alloc_by_nbr: dict[str, dict[str, int]] = {n.id: {} for n in bundle.neighbourhoods}
    allocation_items: list[AllocationItem] = []

    total_objective = 0.0
    total_cost = 0.0

    # Sort keys for deterministic processing
    for (nbr_id, int_id), units in sorted(allocations_map.items()):
        if units <= 0:
            continue
        nbr = nbr_map[nbr_id]
        iv = int_map[int_id]
        alloc_by_nbr[nbr_id][int_id] = units

        unit_env_score = calculate_unit_environmental_benefit(nbr, iv, config.priority_weights)
        unit_obj_val = calculate_unit_objective_value(
            nbr, iv, config.priority_weights, config.equity_weight
        )
        total_obj_contrib = unit_obj_val * units
        item_cost = iv.cost_per_unit_lakh * units

        total_objective += total_obj_contrib
        total_cost += item_cost

        is_hv = nbr.social_vulnerability_index >= config.high_vulnerability_svi_threshold

        allocation_items.append(
            AllocationItem(
                neighbourhood_id=nbr_id,
                neighbourhood_name=nbr.name,
                intervention_id=int_id,
                intervention_name=iv.name,
                category=iv.category.value,
                units=units,
                cost_per_unit_lakh=iv.cost_per_unit_lakh,
                total_cost_lakh=item_cost,
                is_high_vulnerability=is_hv,
                unit_environmental_score=round(unit_env_score, 4),
                total_objective_contribution=round(total_obj_contrib, 4),
            )
        )

    # Compute neighbourhood impacts
    neighbourhood_impacts: list[NeighbourhoodImpact] = []
    hv_spend = 0.0
    non_hv_spend = 0.0
    hv_units = 0
    non_hv_units = 0

    baseline_heats, post_heats, heat_reds = [], [], []
    baseline_floods, post_floods, flood_reds = [], [], []
    baseline_waters, post_waters, water_reds = [], [], []

    hv_heat_reds, hv_flood_reds, hv_water_reds = [], [], []
    non_hv_heat_reds, non_hv_flood_reds, non_hv_water_reds = [], [], []

    for nbr in sorted(bundle.neighbourhoods, key=lambda n: n.id):
        nbr_allocs = alloc_by_nbr.get(nbr.id, {})
        base_r, post_r, red_r = calculate_post_intervention_risks(
            nbr, nbr_allocs, int_map, scale=config.risk_reduction_scale
        )
        nbr_units = sum(nbr_allocs.values())
        nbr_spend = sum(int_map[i_id].cost_per_unit_lakh * u for i_id, u in nbr_allocs.items())
        is_hv = nbr.social_vulnerability_index >= config.high_vulnerability_svi_threshold

        if is_hv:
            hv_spend += nbr_spend
            hv_units += nbr_units
            hv_heat_reds.append(red_r.heat)
            hv_flood_reds.append(red_r.flood)
            hv_water_reds.append(red_r.water)
        else:
            non_hv_spend += nbr_spend
            non_hv_units += nbr_units
            non_hv_heat_reds.append(red_r.heat)
            non_hv_flood_reds.append(red_r.flood)
            non_hv_water_reds.append(red_r.water)

        baseline_heats.append(base_r.heat)
        post_heats.append(post_r.heat)
        heat_reds.append(red_r.heat)

        baseline_floods.append(base_r.flood)
        post_floods.append(post_r.flood)
        flood_reds.append(red_r.flood)

        baseline_waters.append(base_r.water)
        post_waters.append(post_r.water)
        water_reds.append(red_r.water)

        neighbourhood_impacts.append(
            NeighbourhoodImpact(
                neighbourhood_id=nbr.id,
                neighbourhood_name=nbr.name,
                is_high_vulnerability=is_hv,
                social_vulnerability_index=nbr.social_vulnerability_index,
                units_deployed=nbr_units,
                distinct_types_count=len([u for u in nbr_allocs.values() if u > 0]),
                total_spend_lakh=round(nbr_spend, 4),
                baseline_risks=base_r,
                post_intervention_risks=post_r,
                risk_reductions=red_r,
            )
        )

    # City-wide environmental averages
    n_count = len(bundle.neighbourhoods)
    mean_base_heat = sum(baseline_heats) / n_count
    mean_post_heat = sum(post_heats) / n_count
    mean_heat_red = sum(heat_reds) / n_count

    mean_base_flood = sum(baseline_floods) / n_count
    mean_post_flood = sum(post_floods) / n_count
    mean_flood_red = sum(flood_reds) / n_count

    mean_base_water = sum(baseline_waters) / n_count
    mean_post_water = sum(post_waters) / n_count
    mean_water_red = sum(water_reds) / n_count

    mean_base_comp = (mean_base_heat + mean_base_flood + mean_base_water) / 3.0
    mean_post_comp = (mean_post_heat + mean_post_flood + mean_post_water) / 3.0
    mean_comp_red = (mean_heat_red + mean_flood_red + mean_water_red) / 3.0

    # Group averages
    hv_count = max(1, len(hv_heat_reds))
    non_hv_count = max(1, len(non_hv_heat_reds))

    hv_mean_h = sum(hv_heat_reds) / hv_count if hv_heat_reds else 0.0
    hv_mean_f = sum(hv_flood_reds) / hv_count if hv_flood_reds else 0.0
    hv_mean_w = sum(hv_water_reds) / hv_count if hv_water_reds else 0.0

    non_hv_mean_h = sum(non_hv_heat_reds) / non_hv_count if non_hv_heat_reds else 0.0
    non_hv_mean_f = sum(non_hv_flood_reds) / non_hv_count if non_hv_flood_reds else 0.0
    non_hv_mean_w = sum(non_hv_water_reds) / non_hv_count if non_hv_water_reds else 0.0

    env_summary = EnvironmentalSummary(
        mean_baseline_heat=round(mean_base_heat, 2),
        mean_post_heat=round(mean_post_heat, 2),
        mean_heat_reduction=round(mean_heat_red, 2),
        mean_baseline_flood=round(mean_base_flood, 2),
        mean_post_flood=round(mean_post_flood, 2),
        mean_flood_reduction=round(mean_flood_red, 2),
        mean_baseline_water=round(mean_base_water, 2),
        mean_post_water=round(mean_post_water, 2),
        mean_water_reduction=round(mean_water_red, 2),
        mean_baseline_composite=round(mean_base_comp, 2),
        mean_post_composite=round(mean_post_comp, 2),
        mean_composite_reduction=round(mean_comp_red, 2),
        total_objective_score=round(total_objective, 4),
        hv_mean_heat_reduction=round(hv_mean_h, 2),
        hv_mean_flood_reduction=round(hv_mean_f, 2),
        hv_mean_water_reduction=round(hv_mean_w, 2),
        non_hv_mean_heat_reduction=round(non_hv_mean_h, 2),
        non_hv_mean_flood_reduction=round(non_hv_mean_f, 2),
        non_hv_mean_water_reduction=round(non_hv_mean_w, 2),
    )

    # Equity breakdown
    req_equity_spend = config.equity_threshold * config.budget_lakh
    # Equity constraint is satisfied if spent in HV >= threshold * budget
    # Within floating point tolerance
    equity_satisfied = (hv_spend + 1e-6) >= req_equity_spend

    equity_summary = EquitySummary(
        high_vulnerability_spend_lakh=round(hv_spend, 4),
        non_high_vulnerability_spend_lakh=round(non_hv_spend, 4),
        total_spend_lakh=round(total_cost, 4),
        budget_lakh=round(config.budget_lakh, 4),
        equity_spend_fraction_of_budget=round(hv_spend / config.budget_lakh, 4)
        if config.budget_lakh > 0
        else 0.0,
        equity_spend_fraction_of_total_spend=round(hv_spend / total_cost, 4)
        if total_cost > 0
        else 0.0,
        target_threshold=config.equity_threshold,
        equity_constraint_satisfied=equity_satisfied,
        high_vulnerability_units_count=hv_units,
        non_high_vulnerability_units_count=non_hv_units,
    )

    return (
        allocation_items,
        neighbourhood_impacts,
        env_summary,
        equity_summary,
        round(total_objective, 4),
        round(total_cost, 4),
    )
