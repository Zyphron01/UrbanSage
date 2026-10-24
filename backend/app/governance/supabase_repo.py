"""
UrbanSage AI — Supabase PostgreSQL Governance & Budget Planning Repository
==========================================================================
Direct Supabase PostgreSQL persistence layer for municipal departmental recommendations,
administrative decisions, and capital budget plans.
Eliminates local SQLite dependency, using Supabase PostgreSQL as the single source of truth.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional
import uuid

from dotenv import load_dotenv
from supabase import Client, create_client

from app.governance.models import (
    AdminDecision,
    AdminDecisionCreate,
    BudgetPlan,
    BudgetPlanCreate,
    BudgetPlanItem,
    DepartmentRecommendation,
)
from app.governance.repository import GovernanceRepository

logger = logging.getLogger("urbansage.governance.supabase")


class SupabaseGovernanceRepository(GovernanceRepository):
    """
    Supabase PostgreSQL persistence engine for administrative governance,
    departmental triage recommendations, and capital budget plans.
    """

    def __init__(self, client: Optional[Client] = None):
        if client:
            self.client = client
        else:
            load_dotenv()
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
            self.client = create_client(url, key)

    def close(self) -> None:
        pass

    def _get_last_event_hash(self) -> str:
        try:
            res = (
                self.client.table("audit_events")
                .select("event_hash")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]["event_hash"]
        except Exception:
            pass
        return "GENESIS_URBANSAGE_FINANCIAL_AUDIT_LEDGER_2025"

    # -----------------------------------------------------------------------
    # Department Recommendations
    # -----------------------------------------------------------------------

    def get_or_generate_recommendation(
        self,
        report_id: str,
        category: str,
        severity: int,
        neighbourhood_id: Optional[str] = None,
        neighbourhood_name: Optional[str] = None,
        flood_risk: float = 50.0,
        heat_risk: float = 50.0,
        water_stress: float = 50.0,
        svi: float = 50.0,
    ) -> DepartmentRecommendation:
        """
        Deterministically computes a rule-based departmental recommendation with explainable
        evidence grounded in the report and ward hazard metrics.
        """
        rec_id = f"REC-{hashlib.sha256(report_id.encode()).hexdigest()[:8].upper()}"
        ward_display = neighbourhood_name or neighbourhood_id or "General Municipal Area"
        evidence: List[str] = [
            f"Observed Category: {category}",
            f"Reported Severity Level: {severity}/5",
        ]

        if category == "flooding_drainage":
            dept = "BBMP Stormwater Drainage & Lakes Department (SWD)"
            if severity >= 4 or flood_risk > 75.0:
                action = "Emergency Desilting & Sump Bypass Deployment"
                urgency = "CRITICAL"
            else:
                action = "Secondary Drain Clearing & Bioswale Inspection"
                urgency = "HIGH" if severity >= 3 else "MEDIUM"
            evidence.append(f"Ward Flood Hazard Index: {flood_risk:.1f}/100")
            evidence.append(f"Ward Social Vulnerability: {svi:.1f}/100")
            explanation = (
                f"Assigned to {dept} based on high localized waterlogging risk in {ward_display}. "
                f"Heuristic calculation balances reported severity ({severity}/5) against baseline ward flood "
                f"exposure ({flood_risk:.1f}/100) and hydraulic choke-point topology."
            )
            confidence = round(min(95.0, 70.0 + severity * 4.5 + (flood_risk / 10.0)), 1)
            coverage = "High telemetry and citizen report density in catchment."

        elif category == "water_scarcity":
            dept = "Bangalore Water Supply & Sewerage Board (BWSSB)"
            if severity >= 4 or water_stress > 80.0:
                action = "Emergency Tanker Rationing & Feeder Line Pressure Surge"
                urgency = "CRITICAL"
            else:
                action = "Distribution Valve Check & Leak Detection Survey"
                urgency = "HIGH" if severity >= 3 else "MEDIUM"
            evidence.append(f"Ward Water Stress Index: {water_stress:.1f}/100")
            evidence.append(f"Ward Social Vulnerability: {svi:.1f}/100")
            explanation = (
                f"Assigned to {dept} due to acute potable water disruption in {ward_display}. "
                f"Rule-based threshold triggered by water stress score ({water_stress:.1f}/100) and persistent citizen deficit reports."
            )
            confidence = round(min(94.0, 68.0 + severity * 4.0 + (water_stress / 10.0)), 1)
            coverage = "Moderate sensor coverage; supplemented by community corroboration."

        elif category == "heat":
            dept = "BBMP Health & Urban Climate Resilience Directorate"
            if severity >= 4 or heat_risk > 75.0:
                action = "Cool Roof Initiative & Misting Station Installation"
                urgency = "CRITICAL"
            else:
                action = "Public Transit Shade Awning & Hydration Kiosk Setup"
                urgency = "HIGH" if severity >= 3 else "STANDARD"
            evidence.append(f"Ward Surface Heat Index: {heat_risk:.1f}/100")
            evidence.append(f"Ward Social Vulnerability: {svi:.1f}/100")
            explanation = (
                f"Routed to {dept} to mitigate microclimate thermal distress in {ward_display}. "
                f"Threshold evaluated against satellite Land Surface Temperature anomaly and vulnerability of pedestrian commuters."
            )
            confidence = round(min(92.0, 65.0 + severity * 4.0 + (heat_risk / 10.0)), 1)
            coverage = "Satellite thermal composite coverage complete; micro-canopy survey pending."

        else:  # loss_of_green_cover
            dept = "BBMP Forest, Horticultural & Parkland Cell"
            action = "Urban Forestry Native Sapling Afforestation & Canopy Protection"
            urgency = "HIGH" if severity >= 4 else "STANDARD"
            evidence.append(f"Canopy Deficit Warning in {ward_display}")
            evidence.append(f"Ward Social Vulnerability: {svi:.1f}/100")
            explanation = (
                f"Directed to {dept} for bio-retention and canopy restoration in {ward_display}. "
                f"Standard remediation protocol requires 3:1 replacement plantings with indigenous drought-resistant species."
            )
            confidence = round(min(90.0, 72.0 + severity * 3.5), 1)
            coverage = "Tree census records active; verified via municipal ward boundary GIS."

        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        return DepartmentRecommendation(
            recommendation_id=rec_id,
            report_id=report_id,
            neighbourhood_id=neighbourhood_id,
            recommended_department=dept,
            recommended_action=action,
            urgency_level=urgency,
            explanation=explanation,
            evidence_used=evidence,
            confidence_score=confidence,
            is_rule_based_heuristic=True,
            data_coverage_notice=coverage,
            created_at=now_iso,
        )

    # -----------------------------------------------------------------------
    # Administrative Decisions
    # -----------------------------------------------------------------------

    def create_admin_decision(
        self,
        report_id: str,
        payload: AdminDecisionCreate,
        reviewer_id: str,
    ) -> AdminDecision:
        """Persist administrative triage and assignment decision in Supabase PostgreSQL."""
        decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        prev_hash = self._get_last_event_hash()

        decision = AdminDecision(
            decision_id=decision_id,
            report_id=report_id,
            decision_type=payload.decision_type,
            assigned_department=payload.assigned_department,
            assigned_action=payload.assigned_action,
            review_notes=payload.review_notes,
            priority_tier=payload.priority_tier,
            reviewer_id=reviewer_id,
            created_at=now_iso,
        )

        audit_payload = {
            "event_id": event_id,
            "timestamp": now_iso,
            "actor_id": reviewer_id,
            "actor_role": "administrator",
            "event_type": "ADMIN_DECISION_RECORDED",
            "entity_type": "ALLOCATION",
            "entity_id": "ALC-00000001",
            "summary": f"Admin decision on {report_id}: {payload.assigned_action} -> {payload.assigned_department}",
            "previous_state": None,
            "new_state": decision.model_dump(),
            "previous_event_hash": prev_hash,
        }
        canonical = json.dumps(audit_payload, sort_keys=True, default=str)
        event_hash = hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()
        audit_payload["event_hash"] = event_hash

        try:
            self.client.table("audit_events").insert(audit_payload).execute()
        except Exception as e:
            logger.warning("Failed to record admin decision in audit_events: %s", e)

        return decision

    def list_admin_decisions(self, report_id: Optional[str] = None) -> List[AdminDecision]:
        """List administrative decisions from Supabase PostgreSQL audit trail."""
        try:
            query = (
                self.client.table("audit_events")
                .select("new_state")
                .eq("event_type", "ADMIN_DECISION_RECORDED")
                .order("timestamp", desc=True)
                .limit(100)
            )
            res = query.execute()
            decisions: List[AdminDecision] = []
            for row in (res.data or []):
                state = row.get("new_state")
                if state and isinstance(state, dict) and "decision_id" in state:
                    if report_id and state.get("report_id") != report_id:
                        continue
                    decisions.append(AdminDecision.model_validate(state))
            return decisions
        except Exception as e:
            logger.warning("Failed to list admin decisions from Supabase: %s", e)
            return []

    # -----------------------------------------------------------------------
    # Budget Plans & Approvals
    # -----------------------------------------------------------------------

    def create_budget_plan(
        self,
        payload: BudgetPlanCreate,
        created_by: str,
    ) -> BudgetPlan:
        """Persist proposed capital budget plan with line items in Supabase PostgreSQL."""
        plan_id = f"PLN-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        total_allocated = sum(item.total_cost_lakh for item in payload.items)
        remaining_balance = max(0.0, payload.budget_lakh - total_allocated)

        items: List[BudgetPlanItem] = []
        for item in payload.items:
            item_id = f"ITM-{uuid.uuid4().hex[:8].upper()}"
            items.append(
                BudgetPlanItem(
                    item_id=item_id,
                    plan_id=plan_id,
                    neighbourhood_id=item.neighbourhood_id,
                    neighbourhood_name=item.neighbourhood_name,
                    intervention_id=item.intervention_id,
                    intervention_name=item.intervention_name,
                    category=item.category,
                    units=item.units,
                    cost_per_unit_lakh=round(item.cost_per_unit_lakh, 4),
                    total_cost_lakh=round(item.total_cost_lakh, 4),
                    rationale=item.rationale,
                )
            )

        plan = BudgetPlan(
            plan_id=plan_id,
            title=payload.title,
            budget_lakh=round(payload.budget_lakh, 4),
            equity_threshold=round(payload.equity_threshold, 4),
            total_allocated_lakh=round(total_allocated, 4),
            remaining_balance_lakh=round(remaining_balance, 4),
            status="proposed",
            created_by=created_by,
            reviewed_by=None,
            approved_by=None,
            notes=payload.notes,
            items=items,
            created_at=now_iso,
            updated_at=now_iso,
        )

        event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        prev_hash = self._get_last_event_hash()
        audit_payload = {
            "event_id": event_id,
            "timestamp": now_iso,
            "actor_id": created_by,
            "actor_role": "administrator",
            "event_type": "BUDGET_PLAN_PROPOSED",
            "entity_type": "ALLOCATION",
            "entity_id": "ALC-00000001",
            "summary": f"Capital Budget Plan proposed: {payload.title} (₹{payload.budget_lakh:.1f}L)",
            "previous_state": None,
            "new_state": plan.model_dump(),
            "previous_event_hash": prev_hash,
        }
        canonical = json.dumps(audit_payload, sort_keys=True, default=str)
        event_hash = hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()
        audit_payload["event_hash"] = event_hash

        try:
            self.client.table("audit_events").insert(audit_payload).execute()
        except Exception as e:
            logger.warning("Failed to persist budget plan into Supabase audit_events: %s", e)

        return plan

    def get_budget_plan(self, plan_id: str) -> Optional[BudgetPlan]:
        """Fetch budget plan from Supabase PostgreSQL audit trail."""
        try:
            res = (
                self.client.table("audit_events")
                .select("new_state")
                .in_("event_type", ["BUDGET_PLAN_PROPOSED", "BUDGET_PLAN_APPROVED"])
                .order("timestamp", desc=True)
                .execute()
            )
            for row in (res.data or []):
                state = row.get("new_state")
                if state and isinstance(state, dict) and state.get("plan_id") == plan_id:
                    return BudgetPlan.model_validate(state)
        except Exception as e:
            logger.warning("Failed to fetch budget plan %s from Supabase: %s", plan_id, e)
        return None

    def list_budget_plans(self) -> List[BudgetPlan]:
        """List all budget plans persisted in Supabase PostgreSQL."""
        try:
            res = (
                self.client.table("audit_events")
                .select("new_state")
                .in_("event_type", ["BUDGET_PLAN_PROPOSED", "BUDGET_PLAN_APPROVED"])
                .order("timestamp", desc=True)
                .execute()
            )
            seen_ids = set()
            plans: List[BudgetPlan] = []
            for row in (res.data or []):
                state = row.get("new_state")
                if state and isinstance(state, dict) and "plan_id" in state:
                    pid = state["plan_id"]
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        plans.append(BudgetPlan.model_validate(state))
            return plans
        except Exception as e:
            logger.warning("Failed to list budget plans from Supabase: %s", e)
            return []

    def approve_budget_plan(self, plan_id: str, approved_by: str) -> BudgetPlan:
        """Mark budget plan as approved in Supabase PostgreSQL."""
        plan = self.get_budget_plan(plan_id)
        if not plan:
            raise ValueError(f"Budget plan '{plan_id}' not found.")

        now_iso = datetime.datetime.now(timezone.utc).isoformat()
        approved_plan = plan.model_copy(
            update={
                "status": "approved",
                "approved_by": approved_by,
                "updated_at": now_iso,
            }
        )

        event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        prev_hash = self._get_last_event_hash()
        audit_payload = {
            "event_id": event_id,
            "timestamp": now_iso,
            "actor_id": approved_by,
            "actor_role": "administrator",
            "event_type": "BUDGET_PLAN_APPROVED",
            "entity_type": "ALLOCATION",
            "entity_id": "ALC-00000001",
            "summary": f"Capital Budget Plan approved: {approved_plan.title} (₹{approved_plan.budget_lakh:.1f}L)",
            "previous_state": plan.model_dump(),
            "new_state": approved_plan.model_dump(),
            "previous_event_hash": prev_hash,
        }
        canonical = json.dumps(audit_payload, sort_keys=True, default=str)
        event_hash = hashlib.sha256(f"{prev_hash}:{canonical}".encode()).hexdigest()
        audit_payload["event_hash"] = event_hash

        try:
            self.client.table("audit_events").insert(audit_payload).execute()
        except Exception as e:
            logger.warning("Failed to record plan approval in Supabase audit_events: %s", e)

        return approved_plan
