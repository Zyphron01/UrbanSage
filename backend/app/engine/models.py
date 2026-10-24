"""
UrbanSage AI — Engine Models (Stage 3)
=======================================
Pydantic models and data structures for optimization runs, baseline evaluations,
risk summaries, and solver results.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, model_validator


class SolverStatus(str, Enum):
    """Execution status returned by optimization and baseline solvers."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    ERROR = "ERROR"


class PriorityWeights(BaseModel):
    """
    Relative importance weights across environmental dimensions.
    Must sum to 1.0 within floating point tolerance.
    """

    heat: float = Field(default=0.35, ge=0.0, le=1.0, description="Heat-island reduction priority.")
    flood: float = Field(default=0.35, ge=0.0, le=1.0, description="Flood-risk reduction priority.")
    water: float = Field(default=0.30, ge=0.0, le=1.0, description="Water-stress reduction priority.")

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> PriorityWeights:
        total = self.heat + self.flood + self.water
        if abs(total - 1.0) > 1e-5:
            raise ValueError(
                f"Priority weights must sum to 1.0; got {total:.6f} "
                f"(heat={self.heat}, flood={self.flood}, water={self.water})"
            )
        return self


class EngineConfig(BaseModel):
    """
    Configuration for an optimization or baseline evaluation run.
    """

    budget_lakh: float = Field(..., gt=0.0, description="Total capital budget in ₹ lakh.")
    equity_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Minimum fraction of budget required for high-vulnerability neighbourhoods.",
    )
    priority_weights: PriorityWeights = Field(
        default_factory=PriorityWeights,
        description="Relative weights across environmental dimensions.",
    )
    equity_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Weight on social vulnerability in the objective function.",
    )
    max_interventions_per_neighbourhood: int = Field(
        default=3,
        ge=1,
        le=4,
        description="Maximum distinct intervention categories per neighbourhood.",
    )
    high_vulnerability_svi_threshold: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="SVI threshold at or above which a neighbourhood is considered high vulnerability.",
    )
    risk_reduction_scale: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description="Calibration scaling factor mapping per-unit effectiveness to ward-scale risk reduction.",
    )
    report_need_signals: dict[tuple[str, str], float] | None = Field(
        default=None,
        description="Optional mapping from (neighbourhood_id, hazard_dimension) to effective hazard level in [0.0, 1.0].",
    )



class AllocationItem(BaseModel):
    """A single intervention allocation to a neighbourhood."""

    neighbourhood_id: str
    neighbourhood_name: str
    intervention_id: str
    intervention_name: str
    category: str
    units: int = Field(..., ge=0)
    cost_per_unit_lakh: float
    total_cost_lakh: float
    is_high_vulnerability: bool
    unit_environmental_score: float
    total_objective_contribution: float


class RiskDimensionValues(BaseModel):
    """Values across the three environmental dimensions."""

    heat: float = Field(..., ge=0.0, le=100.0)
    flood: float = Field(..., ge=0.0, le=100.0)
    water: float = Field(..., ge=0.0, le=100.0)

    @property
    def composite(self) -> float:
        return (self.heat + self.flood + self.water) / 3.0


class NeighbourhoodImpact(BaseModel):
    """Detailed impact analysis for a single neighbourhood."""

    neighbourhood_id: str
    neighbourhood_name: str
    is_high_vulnerability: bool
    social_vulnerability_index: float
    units_deployed: int
    distinct_types_count: int
    total_spend_lakh: float
    baseline_risks: RiskDimensionValues
    post_intervention_risks: RiskDimensionValues
    risk_reductions: RiskDimensionValues


class EnvironmentalSummary(BaseModel):
    """City-wide summary of environmental outcomes (simulated scores)."""

    mean_baseline_heat: float
    mean_post_heat: float
    mean_heat_reduction: float

    mean_baseline_flood: float
    mean_post_flood: float
    mean_flood_reduction: float

    mean_baseline_water: float
    mean_post_water: float
    mean_water_reduction: float

    mean_baseline_composite: float
    mean_post_composite: float
    mean_composite_reduction: float

    total_objective_score: float

    # Group-specific estimated simulated benefits (Task 3)
    hv_mean_heat_reduction: float = 0.0
    hv_mean_flood_reduction: float = 0.0
    hv_mean_water_reduction: float = 0.0

    non_hv_mean_heat_reduction: float = 0.0
    non_hv_mean_flood_reduction: float = 0.0
    non_hv_mean_water_reduction: float = 0.0


class EquitySummary(BaseModel):
    """Summary of social equity allocation outcomes."""

    high_vulnerability_spend_lakh: float
    non_high_vulnerability_spend_lakh: float
    total_spend_lakh: float
    budget_lakh: float
    equity_spend_fraction_of_budget: float
    equity_spend_fraction_of_total_spend: float
    target_threshold: float
    equity_constraint_satisfied: bool
    high_vulnerability_units_count: int
    non_high_vulnerability_units_count: int


class PortfolioResult(BaseModel):
    """
    Complete result bundle from an optimization or baseline run.
    """

    status: SolverStatus
    method: str  # "OPTIMIZER_MILP" or "HEURISTIC_BASELINE"
    objective_value: float
    total_cost_lakh: float
    budget_lakh: float
    budget_utilization_pct: float
    unused_budget_lakh: float = 0.0
    optimality_gap: float | None = None
    binding_constraints: list[str] = Field(default_factory=list)
    allocations: list[AllocationItem]
    neighbourhood_impacts: list[NeighbourhoodImpact]
    environmental_summary: EnvironmentalSummary | None = None
    equity_summary: EquitySummary | None = None
    solver_message: str
    computation_time_ms: float
    report_need_signals_applied: bool = False
    need_signal_summary: dict[str, Any] | None = None

