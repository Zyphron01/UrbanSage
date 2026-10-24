"""
UrbanSage AI — Mathematical Engine Package (Stage 3)
====================================================
"""

from app.engine.baseline import UrbanSageBaselineHeuristic
from app.engine.models import (
    AllocationItem,
    EngineConfig,
    EnvironmentalSummary,
    EquitySummary,
    NeighbourhoodImpact,
    PortfolioResult,
    PriorityWeights,
    RiskDimensionValues,
    SolverStatus,
)
from app.engine.optimizer import UrbanSageOptimizer
from app.engine.scoring import (
    calculate_post_intervention_risks,
    calculate_unit_environmental_benefit,
    calculate_unit_objective_value,
    evaluate_portfolio,
)

__all__ = [
    "AllocationItem",
    "EngineConfig",
    "EnvironmentalSummary",
    "EquitySummary",
    "NeighbourhoodImpact",
    "PortfolioResult",
    "PriorityWeights",
    "RiskDimensionValues",
    "SolverStatus",
    "UrbanSageBaselineHeuristic",
    "UrbanSageOptimizer",
    "calculate_post_intervention_risks",
    "calculate_unit_environmental_benefit",
    "calculate_unit_objective_value",
    "evaluate_portfolio",
]
