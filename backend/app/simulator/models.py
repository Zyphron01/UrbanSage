"""
UrbanSage AI — Scenario Simulator Models (Stage 4)
===================================================
Pydantic data models for:
- Scenario definitions (Baseline, Budget Reduction, Extreme Rainfall, Drought, Custom).
- Hazard risk transformation specifications and audit records.
- Detailed allocation diffs (added, removed, changed, unchanged).
- Structured scenario comparison reports and explanations.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from app.engine.models import EngineConfig, PortfolioResult, PriorityWeights


class ScenarioType(str, Enum):
    """Supported scenario types for urban sustainability stress-testing."""

    BASELINE = "BASELINE"
    BUDGET_REDUCTION = "BUDGET_REDUCTION"
    EXTREME_RAINFALL = "EXTREME_RAINFALL"
    DROUGHT = "DROUGHT"
    EQUITY_POLICY_SHIFT = "EQUITY_POLICY_SHIFT"
    CUSTOM = "CUSTOM"


class TransformationRecord(BaseModel):
    """Audit trail record for a single transformed neighbourhood risk parameter."""

    neighbourhood_id: str
    neighbourhood_name: str
    field_name: str
    original_value: float
    transformed_value: float
    was_clipped: bool
    clipping_bound: float | None = None
    transformation_formula: str


class ScenarioConfig(BaseModel):
    """
    Configuration specification for a simulation scenario.
    Defines non-destructive adjustments to the municipal budget, hazard risks,
    or policy weights.
    """

    scenario_id: str = Field(..., min_length=1, description="Unique scenario identifier.")
    name: str = Field(..., min_length=1, description="Human-readable scenario title.")
    description: str = Field(..., min_length=1, description="Description of the climatic or financial shock.")
    scenario_type: ScenarioType = Field(default=ScenarioType.CUSTOM)

    # Financial and policy overrides (optional; if None, inherits baseline values)
    budget_lakh: float | None = Field(default=None, gt=0.0, description="Override capital budget in ₹ lakh.")
    equity_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override minimum high-vulnerability spend fraction."
    )
    priority_weights: PriorityWeights | None = Field(
        default=None, description="Override hazard priority weights across environmental dimensions."
    )
    equity_weight: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override objective weight for social vulnerability."
    )
    max_interventions_per_neighbourhood: int | None = Field(
        default=None, ge=1, le=4, description="Override maximum distinct intervention types per ward."
    )

    # Hazard risk transformation multipliers and absolute deltas (applied to baseline neighbourhoods)
    flood_risk_multiplier: float = Field(
        default=1.0, ge=0.0, le=3.0, description="Multiplier applied to neighbourhood baseline flood risk."
    )
    flood_risk_delta: float = Field(
        default=0.0, ge=-100.0, le=100.0, description="Absolute delta added to neighbourhood baseline flood risk."
    )

    water_stress_multiplier: float = Field(
        default=1.0, ge=0.0, le=3.0, description="Multiplier applied to neighbourhood baseline water stress."
    )
    water_stress_delta: float = Field(
        default=0.0, ge=-100.0, le=100.0, description="Absolute delta added to neighbourhood baseline water stress."
    )

    heat_risk_multiplier: float = Field(
        default=1.0, ge=0.0, le=3.0, description="Multiplier applied to neighbourhood baseline heat risk."
    )
    heat_risk_delta: float = Field(
        default=0.0, ge=-100.0, le=100.0, description="Absolute delta added to neighbourhood baseline heat risk."
    )


class AllocationDiffItem(BaseModel):
    """Granular comparison of an intervention allocation between baseline and scenario."""

    neighbourhood_id: str
    neighbourhood_name: str
    intervention_id: str
    intervention_name: str
    category: str
    is_high_vulnerability: bool
    baseline_units: int = Field(ge=0)
    scenario_units: int = Field(ge=0)
    unit_delta: int
    baseline_cost_lakh: float
    scenario_cost_lakh: float
    cost_delta_lakh: float
    change_type: Literal["ADDED", "REMOVED", "INCREASED", "DECREASED", "UNCHANGED"]


class ScenarioComparison(BaseModel):
    """
    Comprehensive structured comparison between a baseline run and a simulated scenario run.
    """

    scenario_config: ScenarioConfig
    baseline_engine_config: EngineConfig
    scenario_engine_config: EngineConfig

    baseline_result: PortfolioResult
    scenario_result: PortfolioResult

    # Granular allocation diffs
    all_allocation_diffs: list[AllocationDiffItem]
    added_allocations: list[AllocationDiffItem]
    removed_allocations: list[AllocationDiffItem]
    changed_allocations: list[AllocationDiffItem]
    unchanged_allocations: list[AllocationDiffItem]

    # Financial & capacity differences
    total_spend_delta_lakh: float
    unused_budget_scenario_lakh: float
    budget_utilization_scenario_pct: float

    # Equity differences
    hv_spend_delta_lakh: float
    hv_spend_share_baseline_pct: float
    hv_spend_share_scenario_pct: float

    # Simulated hazard reduction deltas (city-wide)
    simulated_heat_reduction_delta: float
    simulated_flood_reduction_delta: float
    simulated_water_reduction_delta: float

    # High-vulnerability group simulated reduction deltas
    hv_heat_reduction_delta: float
    hv_flood_reduction_delta: float
    hv_water_reduction_delta: float

    # Audit & explanations
    transformation_audit_log: list[TransformationRecord]
    crossover_hazard_weights_warning: str | None = None
    main_reasons: list[str] = Field(default_factory=list)
    assumptions_and_limitations: list[str] = Field(default_factory=list)
