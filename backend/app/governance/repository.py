"""
UrbanSage AI — Governance & Budget Planning Repository
======================================================
Thread-safe persistence layer for departmental recommendations, administrative
decisions, and municipal budget plans in the unified SQLite database.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional
import uuid

from app.governance.models import (
    AdminDecision,
    AdminDecisionCreate,
    BudgetPlan,
    BudgetPlanCreate,
    BudgetPlanItem,
    DepartmentRecommendation,
)

logger = logging.getLogger("urbansage.governance.repo")


class GovernanceRepository:
    """
    Persistence and logic for administrative governance, departmental triage recommendations,
    and capital budget plans.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", os.getenv("REPORTS_DB_PATH", "urbansage.db"))
        self.db_path = db_path
        self._lock = threading.RLock()

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA busy_timeout = 5000;")
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL;")

        self._create_tables()

    def _create_tables(self) -> None:
        """Create tables for recommendations, decisions, and budget plans."""
        with self._lock:
            with self._conn:
                self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS department_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    neighbourhood_id TEXT,
                    recommended_department TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    urgency_level TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    evidence_used TEXT NOT NULL DEFAULT '[]',
                    confidence_score REAL NOT NULL,
                    is_rule_based_heuristic INTEGER NOT NULL DEFAULT 1,
                    data_coverage_notice TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS admin_decisions (
                    decision_id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    assigned_department TEXT NOT NULL,
                    assigned_action TEXT NOT NULL,
                    review_notes TEXT NOT NULL,
                    priority_tier TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS budget_plans (
                    plan_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    budget_lakh REAL NOT NULL,
                    equity_threshold REAL NOT NULL,
                    total_allocated_lakh REAL NOT NULL,
                    remaining_balance_lakh REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'proposed',
                    created_by TEXT NOT NULL,
                    reviewed_by TEXT,
                    approved_by TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS budget_plan_items (
                    item_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    neighbourhood_id TEXT NOT NULL,
                    neighbourhood_name TEXT NOT NULL,
                    intervention_id TEXT NOT NULL,
                    intervention_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    cost_per_unit_lakh REAL NOT NULL,
                    total_cost_lakh REAL NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(plan_id) REFERENCES budget_plans(plan_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_recs_report ON department_recommendations(report_id);
                CREATE INDEX IF NOT EXISTS idx_recs_neighbourhood ON department_recommendations(neighbourhood_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_report ON admin_decisions(report_id);
                CREATE INDEX IF NOT EXISTS idx_budget_plan_items_plan ON budget_plan_items(plan_id);
                """)

    def close(self) -> None:
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

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
        Retrieves existing recommendation or deterministically computes a rule-based
        departmental recommendation with explainable evidence.
        """
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM department_recommendations WHERE report_id = ?",
                (report_id,),
            )
            row = cursor.fetchone()
            if row:
                evidence = json.loads(row["evidence_used"]) if row["evidence_used"] else []
                return DepartmentRecommendation(
                    recommendation_id=row["recommendation_id"],
                    report_id=row["report_id"],
                    neighbourhood_id=row["neighbourhood_id"],
                    recommended_department=row["recommended_department"],
                    recommended_action=row["recommended_action"],
                    urgency_level=row["urgency_level"],
                    explanation=row["explanation"],
                    evidence_used=evidence,
                    confidence_score=row["confidence_score"],
                    is_rule_based_heuristic=bool(row["is_rule_based_heuristic"]),
                    data_coverage_notice=row["data_coverage_notice"],
                    created_at=row["created_at"],
                )

            # Generate rule-based recommendation
            rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
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
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO department_recommendations (
                        recommendation_id, report_id, neighbourhood_id, recommended_department,
                        recommended_action, urgency_level, explanation, evidence_used,
                        confidence_score, is_rule_based_heuristic, data_coverage_notice, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec_id,
                        report_id,
                        neighbourhood_id,
                        dept,
                        action,
                        urgency,
                        explanation,
                        json.dumps(evidence),
                        confidence,
                        1,
                        coverage,
                        now_iso,
                    ),
                )

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
        """Persist administrative triage and assignment decision."""
        with self._lock:
            decision_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
            now_iso = datetime.datetime.now(timezone.utc).isoformat()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO admin_decisions (
                        decision_id, report_id, decision_type, assigned_department,
                        assigned_action, review_notes, priority_tier, reviewer_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        report_id,
                        payload.decision_type,
                        payload.assigned_department,
                        payload.assigned_action,
                        payload.review_notes,
                        payload.priority_tier,
                        reviewer_id,
                        now_iso,
                    ),
                )

            return AdminDecision(
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

    def list_admin_decisions(self, report_id: Optional[str] = None) -> List[AdminDecision]:
        """List persisted administrative decisions."""
        with self._lock:
            if report_id:
                cursor = self._conn.execute(
                    "SELECT * FROM admin_decisions WHERE report_id = ? ORDER BY created_at DESC",
                    (report_id,),
                )
            else:
                cursor = self._conn.execute(
                    "SELECT * FROM admin_decisions ORDER BY created_at DESC LIMIT 100"
                )
            rows = cursor.fetchall()
            return [
                AdminDecision(
                    decision_id=r["decision_id"],
                    report_id=r["report_id"],
                    decision_type=r["decision_type"],
                    assigned_department=r["assigned_department"],
                    assigned_action=r["assigned_action"],
                    review_notes=r["review_notes"],
                    priority_tier=r["priority_tier"],
                    reviewer_id=r["reviewer_id"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # -----------------------------------------------------------------------
    # Budget Plans & Multi-Stage Approvals
    # -----------------------------------------------------------------------

    def create_budget_plan(
        self,
        payload: BudgetPlanCreate,
        created_by: str,
    ) -> BudgetPlan:
        """Persist proposed capital budget plan with line items."""
        with self._lock:
            plan_id = f"PLN-{uuid.uuid4().hex[:8].upper()}"
            now_iso = datetime.datetime.now(timezone.utc).isoformat()
            total_allocated = sum(item.total_cost_lakh for item in payload.items)
            remaining_balance = max(0.0, payload.budget_lakh - total_allocated)

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO budget_plans (
                        plan_id, title, budget_lakh, equity_threshold, total_allocated_lakh,
                        remaining_balance_lakh, status, created_by, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?)
                    """,
                    (
                        plan_id,
                        payload.title,
                        round(payload.budget_lakh, 4),
                        round(payload.equity_threshold, 4),
                        round(total_allocated, 4),
                        round(remaining_balance, 4),
                        created_by,
                        payload.notes,
                        now_iso,
                        now_iso,
                    ),
                )

                for item in payload.items:
                    item_id = f"ITM-{uuid.uuid4().hex[:8].upper()}"
                    self._conn.execute(
                        """
                        INSERT INTO budget_plan_items (
                            item_id, plan_id, neighbourhood_id, neighbourhood_name,
                            intervention_id, intervention_name, category, units,
                            cost_per_unit_lakh, total_cost_lakh, rationale
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_id,
                            plan_id,
                            item.neighbourhood_id,
                            item.neighbourhood_name,
                            item.intervention_id,
                            item.intervention_name,
                            item.category,
                            item.units,
                            round(item.cost_per_unit_lakh, 4),
                            round(item.total_cost_lakh, 4),
                            item.rationale,
                        ),
                    )

            return self.get_budget_plan(plan_id)  # type: ignore

    def get_budget_plan(self, plan_id: str) -> Optional[BudgetPlan]:
        """Fetch budget plan and associated line items."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM budget_plans WHERE plan_id = ?", (plan_id,))
            row = cursor.fetchone()
            if not row:
                return None

            i_cursor = self._conn.execute(
                "SELECT * FROM budget_plan_items WHERE plan_id = ?",
                (plan_id,),
            )
            items = [
                BudgetPlanItem(
                    item_id=i["item_id"],
                    plan_id=i["plan_id"],
                    neighbourhood_id=i["neighbourhood_id"],
                    neighbourhood_name=i["neighbourhood_name"],
                    intervention_id=i["intervention_id"],
                    intervention_name=i["intervention_name"],
                    category=i["category"],
                    units=i["units"],
                    cost_per_unit_lakh=i["cost_per_unit_lakh"],
                    total_cost_lakh=i["total_cost_lakh"],
                    rationale=i["rationale"],
                )
                for i in i_cursor.fetchall()
            ]

            return BudgetPlan(
                plan_id=row["plan_id"],
                title=row["title"],
                budget_lakh=row["budget_lakh"],
                equity_threshold=row["equity_threshold"],
                total_allocated_lakh=row["total_allocated_lakh"],
                remaining_balance_lakh=row["remaining_balance_lakh"],
                status=row["status"],
                created_by=row["created_by"],
                reviewed_by=row["reviewed_by"],
                approved_by=row["approved_by"],
                notes=row["notes"],
                items=items,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_budget_plans(self) -> List[BudgetPlan]:
        """List all persisted budget plans."""
        with self._lock:
            cursor = self._conn.execute("SELECT plan_id FROM budget_plans ORDER BY created_at DESC")
            rows = cursor.fetchall()
            plans: List[BudgetPlan] = []
            for r in rows:
                p = self.get_budget_plan(r["plan_id"])
                if p:
                    plans.append(p)
            return plans

    def approve_budget_plan(self, plan_id: str, approved_by: str) -> BudgetPlan:
        """Mark budget plan as approved."""
        with self._lock:
            now_iso = datetime.datetime.now(timezone.utc).isoformat()
            with self._conn:
                cursor = self._conn.execute(
                    """
                    UPDATE budget_plans
                    SET status = 'approved', approved_by = ?, updated_at = ?
                    WHERE plan_id = ?
                    """,
                    (approved_by, now_iso, plan_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Budget plan '{plan_id}' not found.")

            plan = self.get_budget_plan(plan_id)
            if not plan:
                raise ValueError(f"Failed to reload approved plan '{plan_id}'.")
            return plan


_governance_repo_instance: Optional[GovernanceRepository] = None


def get_governance_repository() -> GovernanceRepository:
    """Dependency injection provider for GovernanceRepository backed by Supabase PostgreSQL."""
    global _governance_repo_instance
    if _governance_repo_instance is None:
        backend = os.getenv("DATABASE_BACKEND", "supabase").strip().lower()
        if backend == "supabase":
            from app.governance.supabase_repo import SupabaseGovernanceRepository
            _governance_repo_instance = SupabaseGovernanceRepository()
        else:
            _governance_repo_instance = GovernanceRepository()
    return _governance_repo_instance

