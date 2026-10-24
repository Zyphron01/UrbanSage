# UrbanSage AI — Automated Test Results & Verification Log

**Last Execution Date:** October 2026  
**Environment:** Python 3.14.3 / Node.js 22.x / Next.js 16.4.2 / Windows Shell (PowerShell)

---

## 1. Backend Test Suite (`pytest`)

**Command:** `python -m pytest -q`  
**Working Directory:** `backend/`  
**Status:** PASSING (283/283 tests passed, 0 failures, 0 errors)  
**Execution Time:** ~8.13 seconds  

### Test Suite Breakdown

| Module | Test File | Cases | Status | Responsibilities Tested |
| :--- | :--- | :--- | :--- | :--- |
| Data Validation | `tests/test_schemas.py` | 47 | PASSED | Pydantic v2 schemas for wards, interventions, capacities, land, weights, config. Boundary, negative, and regex rejection. |
| Synthetic Data | `tests/test_synthetic_data.py` | 17 | PASSED | Verification of 10 synthetic Bengaluru wards, 6 intervention types, capacity linkages, and SVI distributions. |
| Scoring Engine | `tests/test_scoring.py` | 30 | PASSED | Composite hazard scoring, hazard reductions, risk calculations, mathematical edge cases. |
| Optimization Core | `tests/test_optimizer.py` | 28 | PASSED | PuLP MILP optimization, budget compliance, capacity limits, diversity limits, equity guarantees. |
| Baseline Heuristic | `tests/test_baseline.py` | 18 | PASSED | Greedy/heuristic comparison, benchmark validation against optimal allocations. |
| Optimizer Experiments | `tests/test_experiments.py` | 20 | PASSED | Sensitivity analysis, parameter variations, budget sweep experiments. |
| Scenario Simulator | `tests/test_simulator.py` | 15 | PASSED | Baseline reproduction, 30% budget cut, 1.5x flood risk perturbation, 1.4x drought perturbation, determinism. |
| Citizen Reporting | `tests/test_citizen_reports.py` | 39 | PASSED | SQLite persistence, WAL concurrency, duplicate throttling, corroboration scoring, reporter privacy. |
| Citizen REST API | `tests/test_api_reports.py` | 18 | PASSED | FastAPI routing, serialization, pagination, error status codes (404, 409, 422, 500). |
| Supabase Repository | `tests/test_supabase_repo.py` | 16 | PASSED | Supabase dual-repo factory, retry backoff, privacy redaction, SQLite-to-Supabase migration parsing. |
| Report Lifecycle | `tests/test_report_lifecycle.py` | 11 | PASSED | 14-state machine transitions, resolution evidence requirement, citizen confirmation/reopening, audit timeline logging, API endpoints. |
| Admin Intelligence (Stage 4) | `tests/test_admin_intelligence.py` | 9 | PASSED | Daily Decision Brief summary metrics, overdue active ticket classification (>48h), failed verification routing, server-side queue sorting & pagination, geographic hazard aggregations, unassigned ward handling, dual-backend consistency, privacy guarantees. |
| Decision Engine Integration (Stage 5) | `tests/test_stage5_decision_engine.py` | 15 | PASSED | Bounded need-signal engine, sub-linear saturation, duplicate spam resistance, recency decay, dispute priority boost, hard constraint preservation (budget, capacity, diversity, equity), portfolio comparator diffs, scenario simulator propagation, API endpoints, privacy. |

---

## 2. Frontend Linting & Build Suite

### Linting (`eslint`)
**Command:** `npm run lint`  
**Working Directory:** `frontend/`  
**Result:**  
```
> frontend@0.1.0 lint
> eslint

✔ No ESLint warnings or errors detected.
```

### Production Build (`next build`)
**Command:** `npm run build`  
**Working Directory:** `frontend/`  
**Result:**  
```
▲ Next.js 16.4.2 (Turbopack)
- Environments: .env.local
✓ Running next.config.ts took 221ms
- Cache Components enabled
- Partial Prefetching enabled

  Creating an optimized production build ...
✓ Compiled successfully in 1233ms
  Running TypeScript ...
  Finished TypeScript in 4.1s ...
  Collecting page data using 5 workers ...
  Generating static pages using 5 workers (4/4) in 1416ms
  Finalizing page optimization ...

Route (app)
┌ ○ /
└ ○ /_not-found

○ (Static) prerendered as static content
```

---

## 3. Verification Integrity Commitments

- **No Mocks Treated as Live:** Mocks in `test_supabase_repo.py` test the Supabase PostgREST client adapter, retry backoff logic, and query builder contracts. They are explicitly distinguished from a live cloud connection.
- **Strict Ground Truth Separation:** Citizen report records (`data_source: "CITIZEN_REPORT"`, `is_verified_measurement: False`) are tested to ensure they are never conflated with municipal sensor ground truth.
- **Privacy Enforcement:** Automated assertions verify that `reporter_contact` and internal reporter tokens are strictly omitted from `CitizenReportPublic` responses.
