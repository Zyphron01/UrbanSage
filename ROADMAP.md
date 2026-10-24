# UrbanSage AI — Master Development Roadmap

**Tagline:** Intelligent Decisions for Sustainable Cities  
**Mission:** Build an AI-assisted urban sustainability decision platform connecting citizen reports, environmental intelligence, municipal decision-making, constrained resource optimization, public transparency, and financial accountability.

---

## Architecture Overview

UrbanSage AI connects three unified interfaces through a single shared data model, domain-driven backend, and robust role-based access boundaries:

```
[ Citizen Platform ]        [ Admin Intelligence Dashboard ]       [ Public Audit & Transparency Portal ]
         \                               |                                 /
          \                              |                                /
           +-----------------------------+-------------------------------+
                                         |
                            [ FastAPI REST Gateway ]
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
[ Citizen Reports Service ]    [ Optimization Engine ]           [ Scenario Simulator ]
(Scoring, Lifecycle, Audit)   (PuLP Mixed-Integer Linear)       (Multi-Hazard Perturbations)
     |                                   |                                   |
     +-----------------------------------+-----------------------------------+
                                         |
                          [ Repository Abstraction Layer ]
                                         |
                     +-------------------+-------------------+
                     |                                       |
          [ Supabase PostgreSQL ]                    [ SQLite Engine ]
          (Primary Production DB)                    (Isolated Local/Test)
```

---

## Development Stages & Milestones

### Stage 1: Workspace Inspection & Verification Baseline
- [x] Full workspace inspection (structure, dependencies, Git state, schemas, tests).
- [x] Run and document backend regression suite (248 tests passed).
- [x] Run and document frontend linting (0 errors, 0 warnings).
- [x] Run and document frontend production build (Static prerendering + Turbopack verified).
- [x] Establish documentation directory (`docs/`) and core tracking documents.

### Stage 2: System Baseline & Integration Audit
- [x] Data models and schemas audit (Pydantic v2 strict typing).
- [x] Persistence architecture audit (Dual Supabase / SQLite repository contracts).
- [x] Transparent scoring audit (Urgency score & Evidence completeness score).
- [x] Optimization engine mathematical audit (PuLP MILP solver, budget, land, capacity, diversity, equity).
- [x] Scenario simulator audit (Baseline, Flood, Drought, Budget Reduction).
- [x] Security and privacy audit (Redaction of private contact info in public DTOs).

### Stage 3: End-to-End Report Lifecycle & Resolution Evidence (CURRENT MILESTONE)
- [x] 14 distinct lifecycle states modeled with strict transitions.
- [x] Structured resolution evidence schema (`ResolutionEvidence`) with completion photos and actor attribution.
- [x] State transition validation machine (`validate_status_transition`) preventing illegal state skips.
- [x] Citizen verification workflow (Confirmation of resolution or rejection with reopening).
- [x] Return failed verifications back to municipal action queue.
- [x] Append-only audit logging of state transitions with actors, timestamps, and reasons.
- [x] REST endpoints: `PATCH /api/reports/{id}/status`, `POST /api/reports/{id}/verify`, `POST /api/reports/{id}/evidence`.
- [x] Unit and integration test suite for report lifecycle transitions.

### Stage 4: Administrator Intelligence Dashboard (COMPLETED)
- [x] City overview with real-time operational aggregates (`GET /api/admin/decision-brief`).
- [x] Priority review queue with server-side filtering, pagination, and stable sorting (`GET /api/admin/priority-queue`).
- [x] Daily Decision Brief identifying high-urgency actions, overdue active reports (>48h), citizen disputes, and status counts.
- [x] Geographic risk aggregation combining citizen reports with synthetic neighbourhood linkages (`GET /api/admin/geographic-risk`).
- [x] Explicit unassigned external report tracking without fabricating ward boundaries.
- [x] Connected administrator frontend dashboard with live telemetry, priority sub-tabs, review queue, and geographic breakdown.
- [x] Strict citizen privacy preservation (redacted contacts and citizen actor tokens).
- [x] Dual-backend repository consistency (SQLite and Supabase PostgreSQL).
- [x] Comprehensive automated test suite (`test_admin_intelligence.py` - 9 tests, 268 total passing).


### Stage 5: Sustainability Decision Engine Integration (COMPLETED)
- [x] Bounded, testable citizen report need-signal engine (`ReportNeedSignalEngine`) with sub-linear saturation, exponential recency decay, and dispute multipliers.
- [x] Mathematical coupling with SciPy HiGHS MILP optimizer preserving 100% baseline risk when reports are zero and capping max boost at 25%.
- [x] Preservation of hard budget constraints, physical land/capacity limits, diversity caps, and mandatory high-vulnerability equity spend floor (>= threshold * B).
- [x] Decision comparator (`compare_decision_portfolios`) producing granular allocation diffs, budget movements, equity impacts, and natural-language trade-off explanations.
- [x] Scenario simulator integration propagating citizen need signals across budget reductions, climatic shocks, and policy shifts.
- [x] REST API endpoints (`GET /api/optimizer/config`, `POST /api/optimizer/run`, `POST /api/optimizer/compare`, `POST /api/optimizer/scenarios/run`).
- [x] Connected Next.js OptimizationView & ScenariosView with live solver controls, baseline vs. integrated trade-off scoreboard, allocation diff table, and stress-testing simulations.
- [x] Complete automated test suite (`test_stage5_decision_engine.py` - 15 tests, 283 total backend tests passing).


### Stage 6: Financial Accountability & Audit Portal
- [ ] Municipal budget allocations and revisions tracking.
- [ ] Committed vs. actual expenditure per intervention.
- [ ] Milestone-based disbursement tracking tied to photographic resolution evidence.
- [ ] Anomaly detection flags for unverified disbursements or missing proof-of-work.
- [ ] Public transparency ledger showing ward-level sustainability investments.

### Stage 7: Citizen Analytics & Public Transparency
- [ ] Public-safe analytics dashboard (Resolution rate, median response times by ward).
- [ ] Citizen report tracking timeline showing stages from submission to verified resolution.
- [ ] Ward-level environmental scorecard without exposing private reporter data.
- [ ] Interactive filters by category, status, and neighbourhood.

### Stage 8: Environmental Data & Observation Ingestion
- [ ] Integration adapters for open weather and rainfall data (e.g. Open-Meteo, IMD).
- [ ] Land surface temperature and vegetation index ingestion pipelines.
- [ ] Provenance, measurement uncertainty, and data freshness tracking.
- [ ] Explicit labelling distinguishing measured sensor data from simulated predictions.

### Stage 9: Security Hardening & Production Deployment
- [ ] Supabase Row Level Security (RLS) enforcement verification on live cluster.
- [ ] Role-Based Access Control (RBAC) with JWT authentication for municipal administrators.
- [ ] Cloud object storage integration for citizen and completion photographs (S3 / Supabase Storage).
- [ ] Rate limiting and API abuse protection.
- [ ] Automated CI/CD pipeline and monitoring.
