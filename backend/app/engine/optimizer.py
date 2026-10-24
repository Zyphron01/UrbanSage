"""
UrbanSage AI — Mathematical Optimization Engine (Stage 3)
==========================================================
MILP solver using SciPy HiGHS (scipy.optimize.milp).
Selects optimal integer intervention portfolios under:
- Capital budget constraint (hard upper bound).
- Neighbourhood capacity / physical land constraints.
- Social equity floor constraint (hard lower bound on high-vulnerability spend).
- Neighbourhood diversity / implementation limits (max distinct types per area).
- Integrality constraints on all deployment decisions.
"""

from __future__ import annotations

import time
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

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


class UrbanSageOptimizer:
    """
    Mixed-Integer Linear Programming (MILP) optimizer for UrbanSage AI.
    """

    def __init__(self, bundle: DatasetBundle) -> None:
        self.bundle = bundle
        self._nbrs = sorted(bundle.neighbourhoods, key=lambda n: n.id)
        self._ivs = sorted(bundle.interventions, key=lambda i: i.id)
        self._cap_map = bundle.capacity_matrix()
        self._num_nbrs = len(self._nbrs)
        self._num_ivs = len(self._ivs)
        self._num_pairs = self._num_nbrs * self._num_ivs

        # Precompute indexing lookups
        self._pair_to_idx: dict[tuple[str, str], int] = {}
        self._idx_to_pair: dict[int, tuple[str, str]] = {}
        idx = 0
        for n in self._nbrs:
            for iv in self._ivs:
                self._pair_to_idx[(n.id, iv.id)] = idx
                self._idx_to_pair[idx] = (n.id, iv.id)
                idx += 1

    def solve(self, config: EngineConfig) -> PortfolioResult:
        """
        Solve the intervention portfolio optimization problem under the given configuration.

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
                method="OPTIMIZER_MILP",
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
                method="OPTIMIZER_MILP",
                objective_value=0.0,
                total_cost_lakh=0.0,
                budget_lakh=config.budget_lakh,
                budget_utilization_pct=0.0,
                allocations=[],
                neighbourhood_impacts=[],
                solver_message=f"Equity threshold must be between 0.0 and 1.0; got {config.equity_threshold}.",
                computation_time_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Decision variable layout:
        # x[k] = integer units for pair k, where 0 <= k < num_pairs
        # y[k] = binary indicator for x[k] > 0, where num_pairs <= k < 2 * num_pairs
        total_vars = 2 * self._num_pairs

        # 1. Objective function: maximize sum(v_{n,i} * x_{n,i})
        # In scipy.optimize.milp, we minimize c^T x, so c_k = -v_{n,i}
        c = np.zeros(total_vars, dtype=np.float64)
        for idx in range(self._num_pairs):
            nbr_id, int_id = self._idx_to_pair[idx]
            nbr = self.bundle.neighbourhood_by_id(nbr_id)
            iv = self.bundle.intervention_by_id(int_id)
            
            # Check for ward-specific effective hazard levels from citizen report need signals
            eff_hazards = None
            if config.report_need_signals:
                eff_hazards = {
                    "heat": config.report_need_signals.get((nbr_id, "heat"), nbr.heat_risk / 100.0),
                    "flood": config.report_need_signals.get((nbr_id, "flood"), nbr.flood_risk / 100.0),
                    "water": config.report_need_signals.get((nbr_id, "water"), nbr.water_stress / 100.0),
                }
            
            v_val = calculate_unit_objective_value(
                nbr,
                iv,
                config.priority_weights,
                config.equity_weight,
                effective_hazard_levels=eff_hazards,
            )
            c[idx] = -v_val

        # 2. Variable bounds and integrality
        lb = np.zeros(total_vars, dtype=np.float64)
        ub = np.zeros(total_vars, dtype=np.float64)
        integrality = np.ones(total_vars, dtype=np.int32)  # All are integer/binary

        for idx in range(self._num_pairs):
            pair = self._idx_to_pair[idx]
            max_u = self._cap_map.get(pair, 0)
            lb[idx] = 0.0
            ub[idx] = float(max_u)

            # Indicator variable y[idx]
            y_idx = self._num_pairs + idx
            lb[y_idx] = 0.0
            ub[y_idx] = 1.0 if max_u > 0 else 0.0

        bounds = Bounds(lb=lb, ub=ub)

        # 3. Constraints
        # Rows to build:
        # - Budget constraint (1 row)
        # - Equity floor constraint (1 row)
        # - Linking constraints: x[k] - u[k] * y[k] <= 0 (num_pairs rows)
        # - Neighbourhood diversity: sum_i y[n, i] <= K (num_nbrs rows)
        rows: list[np.ndarray] = []
        lhs: list[float] = []
        rhs: list[float] = []

        # (a) Budget constraint: sum(cost_i * x_{n,i}) <= budget_lakh
        budget_row = np.zeros(total_vars, dtype=np.float64)
        for idx in range(self._num_pairs):
            _, int_id = self._idx_to_pair[idx]
            iv = self.bundle.intervention_by_id(int_id)
            budget_row[idx] = iv.cost_per_unit_lakh

        rows.append(budget_row)
        lhs.append(0.0)
        rhs.append(config.budget_lakh)

        # (b) Equity floor constraint: sum_{n in HV, i} (cost_i * x_{n,i}) >= equity_threshold * budget_lakh
        min_equity_spend = config.equity_threshold * config.budget_lakh
        equity_row = np.zeros(total_vars, dtype=np.float64)
        for idx in range(self._num_pairs):
            nbr_id, int_id = self._idx_to_pair[idx]
            nbr = self.bundle.neighbourhood_by_id(nbr_id)
            if nbr.social_vulnerability_index >= config.high_vulnerability_svi_threshold:
                iv = self.bundle.intervention_by_id(int_id)
                equity_row[idx] = iv.cost_per_unit_lakh

        rows.append(equity_row)
        lhs.append(min_equity_spend)
        rhs.append(np.inf)

        # (c) Linking constraints: x_{n,i} - u_{n,i} * y_{n,i} <= 0
        for idx in range(self._num_pairs):
            pair = self._idx_to_pair[idx]
            max_u = self._cap_map.get(pair, 0)
            if max_u > 0:
                link_row = np.zeros(total_vars, dtype=np.float64)
                link_row[idx] = 1.0
                link_row[self._num_pairs + idx] = -float(max_u)
                rows.append(link_row)
                lhs.append(-np.inf)
                rhs.append(0.0)

        # (d) Neighbourhood diversity constraints: sum_{i} y_{n,i} <= K
        for n_idx, nbr in enumerate(self._nbrs):
            div_row = np.zeros(total_vars, dtype=np.float64)
            for iv_idx, iv in enumerate(self._ivs):
                pair_idx = self._pair_to_idx[(nbr.id, iv.id)]
                div_row[self._num_pairs + pair_idx] = 1.0

            rows.append(div_row)
            lhs.append(-np.inf)
            rhs.append(float(config.max_interventions_per_neighbourhood))

        A = np.array(rows, dtype=np.float64)
        constraints = LinearConstraint(A, lhs, rhs)

        # 4. Execute solver
        res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)
        comp_time_ms = (time.perf_counter() - start_time) * 1000.0

        if not res.success:
            # Map solver failure reasons
            status = SolverStatus.INFEASIBLE if res.status == 2 else SolverStatus.ERROR
            return PortfolioResult(
                status=status,
                method="OPTIMIZER_MILP",
                objective_value=0.0,
                total_cost_lakh=0.0,
                budget_lakh=config.budget_lakh,
                budget_utilization_pct=0.0,
                allocations=[],
                neighbourhood_impacts=[],
                solver_message=f"MILP failed: {res.message} (status code {res.status})",
                computation_time_ms=comp_time_ms,
            )

        # 5. Extract solution
        x_sol = res.x[: self._num_pairs]
        allocations_map: dict[tuple[str, str], int] = {}
        for idx, val in enumerate(x_sol):
            units = int(np.round(val))
            if units > 0:
                pair = self._idx_to_pair[idx]
                allocations_map[pair] = units

        # 6. Evaluate full portfolio metrics
        (
            alloc_items,
            nbr_impacts,
            env_sum,
            eq_sum,
            obj_val,
            tot_cost,
        ) = evaluate_portfolio(allocations_map, self.bundle, config)

        util_pct = round((tot_cost / config.budget_lakh) * 100.0, 2) if config.budget_lakh > 0 else 0.0
        unused_budget = round(config.budget_lakh - tot_cost, 4)

        # Detect binding constraints
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

        mip_gap = getattr(res, "mip_gap", 0.0)

        # Summarize need signals if applied
        need_summary = None
        if config.report_need_signals:
            need_summary = {
                "active_signal_pairs_count": len(config.report_need_signals),
                "sample_signals": {
                    f"{n_id}:{h}": round(v, 4)
                    for (n_id, h), v in sorted(config.report_need_signals.items())[:10]
                },
            }

        return PortfolioResult(
            status=SolverStatus.OPTIMAL,
            method="OPTIMIZER_MILP",
            objective_value=obj_val,
            total_cost_lakh=tot_cost,
            budget_lakh=config.budget_lakh,
            budget_utilization_pct=util_pct,
            unused_budget_lakh=unused_budget,
            optimality_gap=round(float(mip_gap), 6) if mip_gap is not None else 0.0,
            binding_constraints=binding_constraints,
            allocations=alloc_items,
            neighbourhood_impacts=nbr_impacts,
            environmental_summary=env_sum,
            equity_summary=eq_sum,
            solver_message=res.message,
            computation_time_ms=round(comp_time_ms, 2),
            report_need_signals_applied=bool(config.report_need_signals),
            need_signal_summary=need_summary,
        )
