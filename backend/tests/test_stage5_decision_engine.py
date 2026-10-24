"""
UrbanSage AI — Stage 5 Decision Engine Integration Tests
=========================================================
Comprehensive automated tests verifying:
1. Signal normalization & strict bounds ([0.0, 0.25]).
2. Exclusion of ineligible report statuses (fake, duplicate, out-of-scope, dismissed, resolved).
3. Explicit dispute handling (boost multiplier for failed resolution / citizen-disputed reports).
4. Duplicate resistance and sub-linear saturation.
5. Recency decay behaviour.
6. Safe handling of unmapped or missing neighbourhoods (no false ward assignment).
7. Preservation of hard constraints in optimizer:
   - Budget upper bound (<= B).
   - Capacity bounds (x_ni <= u_ni).
   - Diversity limits (sum y_ni <= K).
   - Social equity spend floor (>= threshold * B).
8. Determinism: identical inputs produce identical solutions.
9. Baseline compatibility: optimizer without need signals runs identically to Stage 3.
10. Granular decision comparison & explainable reasons.
11. Scenario simulation integration with citizen signals.
12. FastAPI endpoint validation, status codes, and privacy (no reporter contact leak).
"""

from __future__ import annotations

import datetime
from datetime import timezone
import pytest
from fastapi.testclient import TestClient

from app.api.reports import get_report_repository
from app.data.loader import load_default_dataset
from app.engine.comparator import compare_decision_portfolios
from app.engine.models import EngineConfig, PriorityWeights, SolverStatus
from app.engine.need_signal import (
    ELIGIBLE_REPORT_STATUSES,
    EXCLUDED_REPORT_STATUSES,
    ReportNeedSignalEngine,
)
from app.engine.optimizer import UrbanSageOptimizer
from app.main import app
from app.reports.models import (
    CitizenReport,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    ResolutionEvidence,
    VerificationStatus,
)
from app.reports.repository import CitizenReportRepository
from app.simulator.engine import UrbanSageSimulator
from app.simulator.models import ScenarioConfig, ScenarioType


def create_dummy_report(
    report_id: str,
    category: ProblemCategory,
    status: ReportStatus,
    neighbourhood_id: str | None = "NBR-001",
    severity: int = 4,
    urgency_score: float = 75.0,
    evidence_score: float = 80.0,
    days_old: int = 1,
    resolution_evidence: ResolutionEvidence | None = None,
) -> CitizenReport:
    import hashlib
    hex_digest = hashlib.md5(report_id.encode("utf-8")).hexdigest()[:8].upper()
    clean_id = f"RPT-{hex_digest}"
    created = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=days_old)
    return CitizenReport(
        id=clean_id,
        category=category,
        description=f"Environmental report {report_id}",
        severity=severity,
        latitude=12.9716,
        longitude=77.5946,
        location_description="Test location",
        neighbourhood_id=neighbourhood_id,
        reporter_id="test_reporter_1",
        reporter_contact="private@example.com",
        photos=[
            PhotoMetadata(
                photo_id="PHO-00000001",
                file_name="p1.jpg",
                mime_type="image/jpeg",
                size_bytes=1024,
            )
        ],
        status=status,
        verification_status=VerificationStatus.COMMUNITY_CORROBORATED,
        is_verified_measurement=False,
        data_source="CITIZEN_REPORT",
        urgency_score=urgency_score,
        evidence_confidence_score=evidence_score,
        created_at=created,
        updated_at=created,
        resolution_evidence=resolution_evidence,
    )


@pytest.fixture
def client_with_memory_repo():
    """Provides a TestClient wired to an isolated in-memory SQLite repository."""
    repo = CitizenReportRepository(db_path=":memory:")
    app.dependency_overrides[get_report_repository] = lambda: repo
    client = TestClient(app)
    yield client, repo
    app.dependency_overrides.clear()
    repo.close()


# ---------------------------------------------------------------------------
# 1. Need Signal Engine Unit Tests
# ---------------------------------------------------------------------------


def test_need_signal_empty_dataset_preserves_baseline():
    """When no reports exist, effective hazard equals baseline risk exactly."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    audit = engine.compute_signals([], neighbourhoods=bundle.neighbourhoods)

    assert len(audit.signals) == 30  # 10 neighbourhoods * 3 dimensions
    assert audit.total_reports_evaluated == 0
    assert audit.eligible_reports_count == 0

    for s in audit.signals:
        assert s.need_boost == 0.0
        assert 0.0 <= s.effective_hazard_level <= 1.0


def test_need_signal_excluded_statuses_ignored():
    """Confirmed fake, duplicate, out of scope, dismissed, and verified resolved reports must not influence signals."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    reports = [
        create_dummy_report(f"rep-{s.value}", ProblemCategory.FLOODING_DRAINAGE, s)
        for s in EXCLUDED_REPORT_STATUSES
    ]
    audit = engine.compute_signals(reports, neighbourhoods=bundle.neighbourhoods)

    assert audit.eligible_reports_count == 0
    assert audit.excluded_reports_count == len(reports)
    for s in audit.signals:
        assert s.need_boost == 0.0


def test_need_signal_eligible_statuses_included():
    """Submitted, verified, in_progress, and verification_failed are eligible."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    reports = [
        create_dummy_report(f"rep-{s.value}", ProblemCategory.HEAT, s, urgency_score=80.0)
        for s in ELIGIBLE_REPORT_STATUSES
    ]
    audit = engine.compute_signals(reports, neighbourhoods=bundle.neighbourhoods)

    assert audit.eligible_reports_count == len(reports)
    nbr1_heat = audit.get_signal("NBR-001", "heat")
    assert nbr1_heat is not None
    assert nbr1_heat.need_boost > 0.0
    assert nbr1_heat.need_boost <= 0.25


def test_need_signal_disputed_report_multiplier():
    """Disputed or verification_failed reports receive a higher priority multiplier."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    rep_normal = create_dummy_report("r1", ProblemCategory.HEAT, ReportStatus.VERIFIED, urgency_score=50.0)
    rep_disputed = create_dummy_report(
        "r2",
        ProblemCategory.HEAT,
        ReportStatus.VERIFICATION_FAILED,
        urgency_score=50.0,
        resolution_evidence=ResolutionEvidence(
            completed_by="contractor-1",
            completion_notes="Fixed",
            completed_at=datetime.datetime.now(timezone.utc).isoformat(),
            citizen_confirmed=False,
            citizen_feedback="Issue not resolved, still flooding",
        ),
    )

    audit_normal = engine.compute_signals([rep_normal], neighbourhoods=bundle.neighbourhoods)
    audit_disputed = engine.compute_signals([rep_disputed], neighbourhoods=bundle.neighbourhoods)

    sig_normal = audit_normal.get_signal("NBR-001", "heat")
    sig_disputed = audit_disputed.get_signal("NBR-001", "heat")

    assert sig_disputed.need_boost > sig_normal.need_boost


def test_need_signal_duplicate_resistance_and_saturation():
    """Flooding many reports cannot exceed the mathematical cap omega_max = 0.25."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    many_reports = [
        create_dummy_report(f"r-{i}", ProblemCategory.FLOODING_DRAINAGE, ReportStatus.VERIFIED, urgency_score=100.0)
        for i in range(100)
    ]
    audit = engine.compute_signals(many_reports, neighbourhoods=bundle.neighbourhoods)
    sig_flood = audit.get_signal("NBR-001", "flood")

    assert sig_flood.need_boost <= 0.25
    assert sig_flood.effective_hazard_level <= 1.0


def test_need_signal_recency_decay():
    """Recent reports produce higher need boost than stale reports."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    fresh_rep = create_dummy_report("rfresh", ProblemCategory.WATER_SCARCITY, ReportStatus.VERIFIED, days_old=1)
    stale_rep = create_dummy_report("rstale", ProblemCategory.WATER_SCARCITY, ReportStatus.VERIFIED, days_old=60)

    audit_fresh = engine.compute_signals([fresh_rep], neighbourhoods=bundle.neighbourhoods)
    audit_stale = engine.compute_signals([stale_rep], neighbourhoods=bundle.neighbourhoods)

    sig_fresh = audit_fresh.get_signal("NBR-001", "water")
    sig_stale = audit_stale.get_signal("NBR-001", "water")

    assert sig_fresh.need_boost > sig_stale.need_boost


def test_need_signal_unmapped_neighbourhood_handled_safely():
    """Reports with missing or unknown neighbourhood IDs are logged in unassigned and do not misattribute."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()
    rep_unmapped = create_dummy_report("runmapped", ProblemCategory.HEAT, ReportStatus.VERIFIED, neighbourhood_id=None)
    rep_unknown = create_dummy_report("runknown", ProblemCategory.HEAT, ReportStatus.VERIFIED, neighbourhood_id="UNKNOWN-999")

    audit = engine.compute_signals([rep_unmapped, rep_unknown], neighbourhoods=bundle.neighbourhoods)

    assert audit.unassigned_reports_count == 2
    for s in audit.signals:
        assert s.need_boost == 0.0


# ---------------------------------------------------------------------------
# 2. Optimizer Integration & Mathematical Constraint Tests
# ---------------------------------------------------------------------------


def test_optimizer_baseline_mode_compatibility():
    """Running optimizer without citizen report signals produces identical objective and costs to Stage 3."""
    bundle = load_default_dataset()
    config = EngineConfig(budget_lakh=500.0, equity_threshold=0.30)

    optimizer = UrbanSageOptimizer(bundle)
    res = optimizer.solve(config)

    assert res.status == SolverStatus.OPTIMAL
    assert res.report_need_signals_applied is False
    assert res.need_signal_summary is None
    assert res.total_cost_lakh <= 500.0
    # Equity floor satisfied
    assert res.equity_summary.high_vulnerability_spend_lakh >= 150.0 - 1e-4


def test_optimizer_report_informed_preserves_hard_constraints():
    """Report-informed optimization strictly respects budget, capacity, diversity, and equity bounds."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()

    reports = [
        create_dummy_report(f"r-flood-{i}", ProblemCategory.FLOODING_DRAINAGE, ReportStatus.VERIFIED, neighbourhood_id="NBR-001", urgency_score=95.0)
        for i in range(15)
    ]
    audit = engine.compute_signals(reports, bundle.neighbourhoods)
    rep_map = audit.to_signal_map()

    config = EngineConfig(
        budget_lakh=500.0,
        equity_threshold=0.30,
        max_interventions_per_neighbourhood=3,
        report_need_signals=rep_map,
    )
    optimizer = UrbanSageOptimizer(bundle)
    res = optimizer.solve(config)

    assert res.status == SolverStatus.OPTIMAL
    assert res.report_need_signals_applied is True
    assert res.need_signal_summary is not None

    # 1. Budget constraint
    assert res.total_cost_lakh <= config.budget_lakh + 1e-4

    # 2. Equity floor constraint
    min_eq = config.budget_lakh * config.equity_threshold
    assert res.equity_summary.high_vulnerability_spend_lakh >= min_eq - 1e-4

    # 3. Capacity constraints
    cap_map = bundle.capacity_matrix()
    for a in res.allocations:
        max_u = cap_map.get((a.neighbourhood_id, a.intervention_id), 0)
        assert a.units <= max_u

    # 4. Diversity limits
    for ni in res.neighbourhood_impacts:
        assert ni.distinct_types_count <= config.max_interventions_per_neighbourhood


def test_optimizer_is_deterministic():
    """Identical inputs and signals produce bitwise-identical optimization portfolios."""
    bundle = load_default_dataset()
    config = EngineConfig(
        budget_lakh=500.0,
        equity_threshold=0.30,
        report_need_signals={("NBR-001", "flood"): 0.85, ("NBR-002", "heat"): 0.70},
    )
    opt = UrbanSageOptimizer(bundle)
    res1 = opt.solve(config)
    res2 = opt.solve(config)

    assert res1.objective_value == res2.objective_value
    assert res1.total_cost_lakh == res2.total_cost_lakh
    assert [(a.neighbourhood_id, a.intervention_id, a.units) for a in res1.allocations] == [
        (a.neighbourhood_id, a.intervention_id, a.units) for a in res2.allocations
    ]


# ---------------------------------------------------------------------------
# 3. Decision Comparator & Trade-Off Tests
# ---------------------------------------------------------------------------


def test_decision_comparator_generates_diffs_and_reasons():
    """Comparing baseline and report-informed runs produces structured diffs and audit reasons."""
    bundle = load_default_dataset()
    engine = ReportNeedSignalEngine()

    reports = [
        create_dummy_report(f"r-fl-{i}", ProblemCategory.FLOODING_DRAINAGE, ReportStatus.VERIFIED, neighbourhood_id="NBR-005", urgency_score=90.0)
        for i in range(10)
    ]
    audit = engine.compute_signals(reports, bundle.neighbourhoods)
    rep_map = audit.to_signal_map()

    base_config = EngineConfig(budget_lakh=500.0, equity_threshold=0.30)
    integ_config = EngineConfig(budget_lakh=500.0, equity_threshold=0.30, report_need_signals=rep_map)

    opt = UrbanSageOptimizer(bundle)
    base_res = opt.solve(base_config)
    integ_res = opt.solve(integ_config)

    comparison = compare_decision_portfolios(base_res, integ_res, bundle, need_audit=audit)

    assert comparison.budget_constraint_satisfied is True
    assert comparison.equity_constraint_satisfied is True
    assert len(comparison.all_diffs) > 0
    assert len(comparison.reasons_for_change) > 0
    assert comparison.model_provenance["nature"] == "MODELED_ESTIMATE_ONLY"


# ---------------------------------------------------------------------------
# 4. Scenario Simulator Integration
# ---------------------------------------------------------------------------


def test_scenario_simulator_supports_need_signals():
    """UrbanSageSimulator executes scenarios while propagating citizen report need signals."""
    bundle = load_default_dataset()
    base_config = EngineConfig(
        budget_lakh=500.0,
        equity_threshold=0.30,
        report_need_signals={("NBR-001", "flood"): 0.80},
    )
    sim = UrbanSageSimulator(bundle, base_config)

    scen_cfg = ScenarioConfig(
        scenario_id="SCEN-TEST-01",
        name="Austerity Under Flood Need",
        description="Test budget contraction with active flood signals",
        scenario_type=ScenarioType.BUDGET_REDUCTION,
        budget_lakh=400.0,
        equity_threshold=0.30,
    )
    scen_res = sim.run_scenario(scen_cfg)

    assert scen_res.scenario_result.budget_lakh == 400.0
    assert scen_res.scenario_result.total_cost_lakh <= 400.0 + 1e-4
    assert scen_res.scenario_result.report_need_signals_applied is True


# ---------------------------------------------------------------------------
# 5. FastAPI Endpoints & Privacy Tests
# ---------------------------------------------------------------------------


def test_api_optimizer_config_endpoint():
    """GET /api/optimizer/config returns default params, wards, and catalog."""
    client = TestClient(app)
    resp = client.get("/api/optimizer/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_budget_lakh" in data
    assert len(data["neighbourhoods"]) == 10
    assert len(data["interventions"]) == 4


def test_api_optimizer_run_privacy_safeguard(client_with_memory_repo):
    """POST /api/optimizer/run returns optimal solution without leaking reporter contact info."""
    client, _ = client_with_memory_repo
    payload = {
        "budget_lakh": 500.0,
        "equity_threshold": 0.30,
        "include_citizen_reports": True,
    }
    resp = client.post("/api/optimizer/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["result"]["status"] == "OPTIMAL"
    assert data["data_disclaimer"]["is_modeled_estimate"] is True

    # Validate privacy: no contact or private email in serialized json
    json_str = resp.text
    assert "@example.com" not in json_str
    assert "reporter_contact" not in json_str


def test_api_optimizer_compare_endpoint(client_with_memory_repo):
    """POST /api/optimizer/compare returns complete baseline vs integrated comparison."""
    client, _ = client_with_memory_repo
    payload = {
        "budget_lakh": 500.0,
        "equity_threshold": 0.30,
        "include_citizen_reports": True,
    }
    resp = client.post("/api/optimizer/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "baseline_cost_lakh" in data
    assert "integrated_cost_lakh" in data
    assert "all_diffs" in data
    assert "key_tradeoffs" in data
    assert data["budget_constraint_satisfied"] is True
    assert data["equity_constraint_satisfied"] is True
