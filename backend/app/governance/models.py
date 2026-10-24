"""
UrbanSage AI — Municipal Governance, Recommendations & Budget Plans Models
==========================================================================
Data structures for evidence-based departmental recommendations, persistent
administrative decisions, and multi-stage capital budget planning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class DepartmentRecommendation(BaseModel):
    """
    Transparent, rule-based departmental recommendation for an environmental issue.
    Explicitly distinguishes deterministic heuristic analysis from unverified AI.
    """
    recommendation_id: str = Field(..., description="Unique recommendation ID, e.g. REC-XXXXXXXX")
    report_id: str = Field(..., description="Target citizen report ID")
    neighbourhood_id: Optional[str] = Field(None, description="Linked municipal ward ID")
    recommended_department: str = Field(..., description="Authoritative municipal division")
    recommended_action: str = Field(..., description="Actionable field remediation procedure")
    urgency_level: str = Field(..., description="CRITICAL | HIGH | MEDIUM | STANDARD")
    explanation: str = Field(..., description="Detailed rationale explaining why this action was selected")
    evidence_used: List[str] = Field(default_factory=list, description="Specific metrics, reports, and indicators referenced")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Evidence certainty score")
    is_rule_based_heuristic: bool = Field(True, description="Always true; states transparently this is deterministic GIS/rule logic")
    data_coverage_notice: str = Field(..., description="Statement of data completeness or gaps in the ward")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdminDecisionCreate(BaseModel):
    """Payload to record an administrative review or assignment decision."""
    decision_type: str = Field(default="ASSIGN_DEPARTMENT", description="ASSIGN_DEPARTMENT | ESCALATE | REQUEST_FIELD_SURVEY | SCHEDULE_WORK | DISMISS")
    assigned_department: str = Field(..., min_length=2, description="Target municipal department or agency")
    assigned_action: str = Field(..., min_length=3, description="Specific municipal order or action to execute")
    review_notes: str = Field(..., min_length=5, description="Administrative rationale or special instructions")
    priority_tier: str = Field(default="P2_ELEVATED", description="P1_IMMEDIATE | P2_ELEVATED | P3_ROUTINE")


class AdminDecision(BaseModel):
    """Persisted administrative decision record with full accountability audit."""
    decision_id: str
    report_id: str
    decision_type: str
    assigned_department: str
    assigned_action: str
    review_notes: str
    priority_tier: str
    reviewer_id: str
    created_at: str


class BudgetPlanItemCreate(BaseModel):
    """Proposed intervention line item within a budget plan."""
    neighbourhood_id: str
    neighbourhood_name: str
    intervention_id: str
    intervention_name: str
    category: str
    units: int = Field(..., gt=0)
    cost_per_unit_lakh: float = Field(..., gt=0)
    total_cost_lakh: float = Field(..., gt=0)
    rationale: str = Field(default="")


class BudgetPlanItem(BudgetPlanItemCreate):
    """Persisted line item with unique ID and plan foreign key."""
    item_id: str
    plan_id: str


class BudgetPlanCreate(BaseModel):
    """Payload to persist an interactive HiGHS optimization result as a proposed budget plan."""
    title: str = Field(default="Municipal Sustainability Capital Budget Plan FY 2026-27")
    budget_lakh: float = Field(..., gt=0)
    equity_threshold: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
    items: List[BudgetPlanItemCreate] = Field(default_factory=list)


class BudgetPlan(BaseModel):
    """
    Persisted municipal budget plan tracking the lifecycle from proposed to approved.
    Distinguishes proposed, reviewed, and approved allocations.
    """
    plan_id: str
    title: str
    budget_lakh: float
    equity_threshold: float
    total_allocated_lakh: float
    remaining_balance_lakh: float
    status: str = Field(default="proposed", description="'proposed' | 'reviewed' | 'approved'")
    created_by: str
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    items: List[BudgetPlanItem] = Field(default_factory=list)
    created_at: str
    updated_at: str
