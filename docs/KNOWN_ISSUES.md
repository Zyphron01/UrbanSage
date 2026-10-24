# UrbanSage AI — Known Issues and Technical Debt

Last Updated: October 2026

---

## 1. Environment & Infrastructure

- **No Active Git Repository in Workspace:** The workspace directory (`c:\Users\kiran\UrbanSage`) is not currently initialized as a git repository (`fatal: not a git repository`). All tracking is currently managed within the workspace filesystem and Antigravity context.
- **Supabase Cloud Unreachable Without Live Credentials:** The backend repository factory defaults to `DATABASE_BACKEND=supabase`. If `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` are unset or point to placeholders, the backend intentionally raises a clear startup exception rather than silently falling back to SQLite (as required by production integrity rules). Local testing requires either setting valid Supabase credentials or setting `DATABASE_BACKEND=sqlite`.

---

## 2. Report Lifecycle & Workflow (Addressed in Stage 3)

- **Prior Limited Status Set:** The legacy `ReportStatus` enum had only 6 states (`submitted`, `under_review`, `verified`, `assigned`, `resolved`, `dismissed`). Stage 3 expands this to the full 14-state lifecycle machine required for municipal operations.
- **Absence of Resolution Evidence Association:** Prior to Stage 3, marking a report resolved did not record who completed the work, what was done, or require citizen confirmation before reaching verified resolution.
- **One-Way Status Transitions Without Reopening:** Citizens previously lacked a structured mechanism to reject an incomplete resolution and return the ticket to the municipal queue.

---

## 3. Optimization & Simulation Integration Boundaries
- **Static Coupling to Synthetic Datasets (Resolved in Stage 5):** The optimizer (`app/engine/optimizer.py`) and scenario simulator (`app/simulator/engine.py`) are now coupled with citizen reports through `ReportNeedSignalEngine`. Bounded, spam-resistant need signals (&le; 25% boost) adjust hazard dimensions dynamically without destabilizing baseline risk models or double-counting.
- **No Human-in-the-Loop Approval for Recommendations (Scheduled for Stage 6):** The optimizer computes Pareto-optimal intervention portfolios and side-by-side decision comparisons, but formal municipal disbursement workflows and project assignment milestones will be implemented in Stage 6 (Financial Accountability & Audit Portal).

---

## 4. Media & Cloud Storage

- **Photo Metadata Only (No Cloud Blob Storage):** Attached photographs are represented by `PhotoMetadata` (file name, MIME type, byte size, caption, and EXIF timestamp). Actual image binary upload to AWS S3 or Supabase Storage is not yet implemented.

---

## 5. Security & Access Control

- **Missing Role-Based Access Control (RBAC) [Deployment Blocker]:** API endpoints (including citizen reporting `/api/reports` and administrator intelligence `/api/admin/*`) currently operate without JWT validation or user role checks. In this development stage, municipal administrator operations and review queues are open. Production deployment is strictly blocked until Supabase Auth / JWT authentication middleware and RBAC guards (distinguishing citizens, contractors, and municipal supervisors) are implemented.
- **Rate Limiting:** IP-based and user-based rate limiting on the FastAPI gateway has not yet been introduced.

