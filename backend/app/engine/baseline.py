"""
UrbanSage AI — Heuristic Baseline Algorithm (Stage 3)
=====================================================
A transparent, greedy cost-effectiveness heuristic that respects the EXACT same
feasibility constraints as the mathematical optimizer:
- Total cost does not exceed capital budget.
- Individual intervention capacities are respected.
- Equity budget floor for high-vulnerability neighbourhoods is enforced.
- Diversity limit (max distinct intervention types per neighbourhood) is respected.

Enables an apples-to-apples benchmark to evaluate how much value the MILP
formulation adds over intuitive greedy municipal planning.
"""

from __future__ import annotations

import time
from app.data.schemas import DatasetBundle
from app.engine.models import (
    EngineConfig,
    PortfolioResult,
    SolverStatus,
)
from app.engine.scoring import (
    calculate_unit_objective_value,
    evaluate_portfolio,
)


class UrbanSageBaselineHeuristic:
    """
    Greedy Cost-Effectiveness Heuristic with Equity Enforcement.
    """

    def __init__(self, bundle: DatasetBundle) -> None:
        self.bundle = bundle
        self._nbrs = sorted(bundle.neighbourhoods, key=lambda n: n.id)
        self._ivs = sorted(bundle.interventions, key=lambda i: i.id)
        self._cap_map = bundle.capacity_matrix()

    def solve(self, config: EngineConfig) -> PortfolioResult:
        """
        Execute the greedy heuristic under the specified constraints.

        Parameters:
            config: EngineConfig containing budget, equity threshold, weights, and limits.

        Returns:
            PortfolioResult containing status, objective value, costs, allocations, and impacts.
        """
        start_time = time.perf_counter()

        # Validate inputs
        if config.budget_lakh <= 0:
            return PortfolioResult(
                status=SolverStatus.ERROR,
                method="HEURISTIC_BASELINE",
                objective_value=0.0,
                total_cost_lakh=0.0,
                budget_lakh=config.budget_lakh,
                budget_utilization_pct=0.0,
                allocations=[],
                neighbourhood_impacts=[],
                solver_message=f"Budget must be positive; got {config.budget_lakh} lakh.",
                computation_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        if not (0.0 <= config.equity_threshold <= 1.0):
            return PortfolioResult(
                status=SolverStatus.ERROR,
                method="HEURISTIC_BASELINE",
                objective_value=0.0,
                total_cost_lakh=0.0,
                budget_lakh=config.budget_lakh,
                budget_utilization_pct=0.0,
                allocations=[],
                neighbourhood_impacts=[],
                solver_message=f"Equity threshold must be between 0.0 and 1.0; got {config.equity_threshold}.",
                computation_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # 1. Compute candidate options: (nbr_id, int_id, unit_val, cost, ratio, is_hv)
        candidates: list[dict[str, any]] = []
        for nbr in self._nbrs:
            is_hv = nbr.social_vulnerability_index >= config.high_vulnerability_svi_threshold
            for iv in self._ivs:
                max_u = self._cap_map.get((nbr.id, iv.id), 0)
                if max_u > 0:
                    v_val = calculate_unit_objective_value(
                        nbr, iv, config.priority_weights, config.equity_weight
                    )
                    cost = iv.cost_per_unit_lakh
                    ratio = v_val / cost if cost > 0 else 0.0
                    candidates.append(
                        {
                            "nbr_id": nbr.id,
                            "int_id": iv.id,
                            "unit_val": v_val,
                            "cost": cost,
                            "ratio": ratio,
                            "is_hv": is_hv,
                            "max_u": max_u,
                        }
                    )

        # Track state
        current_alloc: dict[tuple[str, str], int] = {}
        nbr_distinct_types: dict[str, set[str]] = {n.id: set() for n in self._nbrs}
        current_spend = 0.0
        current_hv_spend = 0.0
        min_equity_spend = config.equity_threshold * config.budget_lakh

        def can_add(cand: dict[str, any]) -> bool:
            pair = (cand["nbr_id"], cand["int_id"])
            curr_u = current_alloc.get(pair, 0)
            if curr_u >= cand["max_u"]:
                return False
            if current_spend + cand["cost"] > config.budget_lakh + 1e-6:
                return False
            # Check diversity limit
            types = nbr_distinct_types[cand["nbr_id"]]
            if cand["int_id"] not in types and len(types) >= config.max_interventions_per_neighbourhood:
                return False
            return True

        def do_add(cand: dict[str, any]) -> None:
            nonlocal current_spend, current_hv_spend
            pair = (cand["nbr_id"], cand["int_id"])
            current_alloc[pair] = current_alloc.get(pair, 0) + 1
            nbr_distinct_types[cand["nbr_id"]].add(cand["int_id"])
            current_spend += cand["cost"]
            if cand["is_hv"]:
                current_hv_spend += cand["cost"]

        # Phase 1: Equity floor fulfillment
        # Greedily allocate to highest ratio candidates in high-vulnerability neighbourhoods
        hv_candidates = sorted(
            [c for c in candidates if c["is_hv"]],
            key=lambda c: (c["ratio"], c["unit_val"]),
            reverse=True,
        )

        while current_hv_spend < min_equity_spend - 1e-6:
            progress = False
            for cand in hv_candidates:
                if can_add(cand):
                    do_add(cand)
                    progress = True
                    break
            if not progress:
                # Cannot satisfy equity constraint
                return PortfolioResult(
                    status=SolverStatus.INFEASIBLE,
                    method="HEURISTIC_BASELINE",
                    objective_value=0.0,
                    total_cost_lakh=round(current_spend, 4),
                    budget_lakh=config.budget_lakh,
                    budget_utilization_pct=0.0,
                    allocations=[],
                    neighbourhood_impacts=[],
                    solver_message=(
                        f"Heuristic could not satisfy equity threshold {config.equity_threshold:.0%}: "
                        f"achieved ₹{current_hv_spend:.2f}L of required ₹{min_equity_spend:.2f}L."
                    ),
                    computation_time_ms=(time.perf_counter() - start_time) * 1000.0,
                )

        # Phase 2: Allocate remaining budget greedily across all neighbourhoods
        all_candidates = sorted(
            candidates,
            key=lambda c: (c["ratio"], c["unit_val"]),
            reverse=True,
        )

        improved = True
        while improved:
            improved = False
            for cand in all_candidates:
                if can_add(cand):
                    do_add(cand)
                    improved = True
                    break

        comp_time_ms = (time.perf_counter() - start_time) * 1000.0

        # Evaluate final portfolio
        (
            alloc_items,
            nbr_impacts,
            env_sum,
            eq_sum,
            obj_val,
            tot_cost,
        ) = evaluate_portfolio(current_alloc, self.bundle, config)

        util_pct = round((tot_cost / config.budget_lakh) * 100.0, 2) if config.budget_lakh > 0 else 0.0
        unused_budget = round(config.budget_lakh - tot_cost, 4)

        # Detect binding constraints for baseline
        binding_constraints: list[str] = []
        if unused_budget < 1e-4:
            binding_constraints.append(f"Budget (100% utilized: ₹{tot_cost:.2f}L of ₹{config.budget_lakh:.2f}L)")
        elif unused_budget < 5.0:
            binding_constraints.append(f"Budget-tight (unused remainder ₹{unused_budget:.2f}L < ₹5.0L min unit cost)")

        min_equity_spend = config.equity_threshold * config.budget_lakh
        if eq_sum and abs(eq_sum.high_vulnerability_spend_lakh - min_equity_spend) < 1e-4 and min_equity_spend > 0:
            binding_constraints.append(
                f"Equity Floor (exact match: ₹{eq_sum.high_vulnerability_spend_lakh:.2f}L == ₹{min_equity_spend:.2f}L)"
            )

        cap_map = self.bundle.capacity_matrix()
        for item in alloc_items:
            max_u = cap_map.get((item.neighbourhood_id, item.intervention_id), 0)
            if item.units == max_u and max_u > 0:
                binding_constraints.append(
                    f"Capacity: {item.neighbourhood_id} {item.intervention_name} ({item.units}/{max_u} units)"
                )

        for ni in nbr_impacts:
            if ni.distinct_types_count == config.max_interventions_per_neighbourhood:
                binding_constraints.append(
                    f"Diversity Limit: {ni.neighbourhood_id} ({ni.distinct_types_count}/{config.max_interventions_per_neighbourhood} types)"
                )

        return PortfolioResult(
            status=SolverStatus.FEASIBLE,
            method="HEURISTIC_BASELINE",
            objective_value=obj_val,
            total_cost_lakh=tot_cost,
            budget_lakh=config.budget_lakh,
            budget_utilization_pct=util_pct,
            unused_budget_lakh=unused_budget,
            optimality_gap=None,  # Not defined for heuristic
            binding_constraints=binding_constraints,
            allocations=alloc_items,
            neighbourhood_impacts=nbr_impacts,
            environmental_summary=env_sum,
            equity_summary=eq_sum,
            solver_message="Greedy cost-effectiveness heuristic completed successfully.",
            computation_time_ms=round(comp_time_ms, 2),
        )
