"""
UrbanSage AI — Scenario Simulator Demonstration (Stage 4 - Phase 5)
===================================================================
Executes and compares four standardized scenarios:
1. Baseline Scenario (₹60.0L budget, balanced priorities)
2. Reduced Budget Scenario (₹40.0L budget, -33% fiscal austerity)
3. Extreme Monsoon Rainfall Scenario (+30% flood risk, elevated flood priority)
4. Severe Drought Scenario (+35% water stress, elevated water priority)

Prints structured Markdown tables and causal explanations.
"""

from __future__ import annotations

import sys
from app.data.loader import load_default_dataset
from app.engine.models import EngineConfig
from app.simulator.engine import UrbanSageSimulator
from app.simulator.models import ScenarioComparison


def run_demonstration() -> list[ScenarioComparison]:
    """Execute all four demonstration scenarios and return comparison objects."""
    bundle = load_default_dataset()
    base_cfg = EngineConfig(budget_lakh=60.0)
    sim = UrbanSageSimulator(bundle, base_cfg)

    comparisons: list[ScenarioComparison] = []

    # 1. Baseline self-comparison
    base_scen = sim.create_reduced_budget_scenario(budget_lakh=60.0)
    base_scen.scenario_id = "SCEN-BASELINE"
    base_scen.name = "Baseline Standard (₹60.0L)"
    base_scen.description = "Reference capital budget under normal climate conditions."
    comparisons.append(sim.run_scenario(base_scen))

    # 2. Reduced Budget
    scen_cut = sim.create_reduced_budget_scenario(budget_lakh=40.0)
    comparisons.append(sim.run_scenario(scen_cut))

    # 3. Extreme Rainfall
    scen_rain = sim.create_extreme_rainfall_scenario(
        flood_multiplier=1.30,
        flood_delta=15.0,
        elevated_flood_priority=True,
    )
    comparisons.append(sim.run_scenario(scen_rain))

    # 4. Severe Drought
    scen_drought = sim.create_drought_scenario(
        water_multiplier=1.35,
        water_delta=15.0,
        elevated_water_priority=True,
    )
    comparisons.append(sim.run_scenario(scen_drought))

    return comparisons


def format_demonstration_report(comparisons: list[ScenarioComparison]) -> str:
    """Format comparisons into clean Markdown tables with diagnostic commentary."""
    lines: list[str] = [
        "# UrbanSage AI — Stage 4 Scenario Simulation Demonstration\n",
        "## 1. Multi-Scenario Overview Table\n",
        "| Scenario | Budget | Spend (₹L) | Util % | HV Share | Allocations (Wards & Units) | Heat Red | Flood Red | Water Red |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for comp in comparisons:
        scen_name = comp.scenario_config.name
        b_str = f"₹{comp.scenario_engine_config.budget_lakh:.1f}L"
        s_str = f"₹{comp.scenario_result.total_cost_lakh:.1f}L"
        u_str = f"{comp.budget_utilization_scenario_pct:.1f}%"
        hv_share = f"{comp.hv_spend_share_scenario_pct:.1f}%"

        allocs = ", ".join(
            f"{a.neighbourhood_id} ({a.intervention_name}): {a.units}u"
            for a in comp.scenario_result.allocations
        ) or "None"

        es = comp.scenario_result.environmental_summary
        if es:
            h_red = f"{es.mean_heat_reduction:.2f}"
            f_red = f"{es.mean_flood_reduction:.2f}"
            w_red = f"{es.mean_water_reduction:.2f}"
        else:
            h_red, f_red, w_red = "N/A", "N/A", "N/A"

        lines.append(f"| {scen_name} | {b_str} | {s_str} | {u_str} | {hv_share} | {allocs} | {h_red} | {f_red} | {w_red} |")

    lines.append("\n## 2. Granular Scenario Analysis & Causal Drivers\n")

    for comp in comparisons:
        scen = comp.scenario_config
        lines.append(f"### {scen.name}")
        lines.append(f"- **Description**: {scen.description}")
        lines.append(
            f"- **Financial Impact**: Spend delta = ₹{comp.total_spend_delta_lakh:+.1f}L | "
            f"Unused budget = ₹{comp.unused_budget_scenario_lakh:.1f}L | "
            f"HV spend delta = ₹{comp.hv_spend_delta_lakh:+.1f}L"
        )

        # Allocation shifts
        if comp.added_allocations:
            added_str = ", ".join(f"{a.neighbourhood_id} {a.intervention_name} (+{a.scenario_units}u)" for a in comp.added_allocations)
            lines.append(f"- **Added Interventions**: {added_str}")
        if comp.removed_allocations:
            removed_str = ", ".join(f"{a.neighbourhood_id} {a.intervention_name} (-{a.baseline_units}u)" for a in comp.removed_allocations)
            lines.append(f"- **Removed Interventions**: {removed_str}")
        if comp.changed_allocations:
            changed_str = ", ".join(
                f"{a.neighbourhood_id} {a.intervention_name} ({a.baseline_units}u -> {a.scenario_units}u, delta {a.unit_delta:+d}u)"
                for a in comp.changed_allocations
            )
            lines.append(f"- **Changed Allocations**: {changed_str}")
        if not comp.added_allocations and not comp.removed_allocations and not comp.changed_allocations:
            lines.append("- **Allocations**: Identical to baseline allocation.")

        # Crossover warning if applicable
        if comp.crossover_hazard_weights_warning:
            lines.append(f"- **Scoring Comparability Warning**: {comp.crossover_hazard_weights_warning}")

        # Main reasons
        lines.append("- **Causal Explanation**:")
        for r in comp.main_reasons:
            lines.append(f"  - {r}")

        # Transformation audit stats
        if comp.transformation_audit_log:
            lines.append(f"- **Risk Transformations Applied**: {len(comp.transformation_audit_log)} neighbourhood hazard parameters modified.")
            clipped = [t for t in comp.transformation_audit_log if t.was_clipped]
            if clipped:
                lines.append(f"  - {len(clipped)} values were clipped to valid bounds [0, 100].")

        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    comps = run_demonstration()
    print(format_demonstration_report(comps))
