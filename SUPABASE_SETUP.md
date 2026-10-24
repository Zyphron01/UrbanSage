# UrbanSage AI — Supabase PostgreSQL Setup & Migration Guide

This guide details the procedure for provisioning, configuring, and operating the **Supabase PostgreSQL** primary database for the UrbanSage AI backend.

---

## 1. Overview & Architecture

UrbanSage AI uses **Supabase-hosted PostgreSQL** as its primary persistent database for citizen environmental problem reporting, urgency scoring, corroboration, and audit trails.

- **Primary Database**: Supabase PostgreSQL with native `JSONB`, `TIMESTAMPTZ`, and Row Level Security (RLS).
- **Backend Driver**: Official Supabase Python Client (`supabase-py` v2.33+) communicating over HTTPS PostgREST.
- **Fail-Safe Policy**: The backend defaults to Supabase. If credentials are missing or the connection fails, it raises an explicit error and logs securely. It **never silently falls back to SQLite**.
- **Offline / Local Dev Mode**: SQLite is retained *exclusively* for isolated offline unit testing or local development when explicitly configured via `DATABASE_BACKEND=sqlite`.

---

## 2. Locating Supabase Credentials

1. Navigate to your [Supabase Dashboard](https://supabase.com/dashboard) and select your UrbanSage AI project.
2. In the left navigation, click on **Project Settings** (gear icon) &rarr; **API**.
3. Locate the following values:
   - **Project URL**: Found under *Project URL* (e.g., `https://abcdefghijklmnopqrst.supabase.co`).
   - **Service Role Secret Key**: Found under *Project API keys*.
     - Modern projects: Secret key format (e.g., `sbp_...` or secret role key).
     - Legacy projects: `service_role` JWT token (starts with `eyJ...`).

> [!CAUTION]
> **CRITICAL SECURITY REQUIREMENT**
> The `SUPABASE_SECRET_KEY` (or `service_role` key) has administrative privileges and bypasses Row Level Security.
> - Store it **only** in backend environment variables (`.env`).
> - **Never** expose this key to the Next.js frontend or browser.
> - **Never** commit `.env` to Git.

---

## 3. Environment Configuration

### Backend Configuration (`backend/.env` or root `.env`)

Create a `.env` file in the project root or `backend/` directory based on `.env.example`:

```bash
# Application Environment
APP_ENV=production
LOG_LEVEL=INFO

# Backend API
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Primary Persistent Database (Supabase PostgreSQL)
DATABASE_BACKEND=supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SECRET_KEY=your-supabase-secret-key-or-service-role-key

# Offline Local Development / Testing Only (Uncomment to use SQLite locally)
# DATABASE_BACKEND=sqlite
# REPORTS_DB_PATH=urbansage_reports.db
```

---

## 4. Deploying the PostgreSQL Schema

You can deploy the schema via either the **Supabase Dashboard SQL Editor** or automated migration:

### Option A: Supabase Dashboard SQL Editor (Recommended)
1. In the Supabase Dashboard, open **SQL Editor** from the left navigation.
2. Click **New Query**.
3. Open and copy the contents of [`backend/app/db/schema.sql`](file:///c:/Users/kiran/UrbanSage/backend/app/db/schema.sql) (or migration file `001_initial_supabase_schema.sql`).
4. Paste the SQL script into the editor and click **Run**.
5. The script creates:
   - Table `public.citizen_reports` with format check constraints (`RPT-XXXXXXXX`, latitude/longitude bounds, severity bounds, valid categories).
   - Indexes (`idx_citizen_reports_category`, `idx_citizen_reports_status`, `idx_citizen_reports_throttle`, `idx_citizen_reports_corroboration`).
   - Automatic `updated_at` trigger.
   - Public view `public.citizen_reports_public` (safely excludes `reporter_contact` and `reporter_id`).
   - Row Level Security (RLS) policies enforcing least privilege.

---

## 5. Migrating Existing SQLite Records to Supabase

UrbanSage AI provides a safe, idempotent data-migration utility:

### Step 5.1: Preview Migration (Dry-Run Mode)
Verify that all existing records in `urbansage_reports.db` parse and validate against domain rules:

```powershell
cd c:\Users\kiran\UrbanSage\backend
python -m app.db.migrate_sqlite_to_supabase --dry-run
```

Expected output:
```text
[INFO] migrate: Read 3 records from SQLite database (urbansage_reports.db).
[INFO] migrate: Validated 3 records from SQLite.
[INFO] migrate: DRY-RUN SUCCESS: All 3 records validated cleanly against schema.
```

### Step 5.2: Execute Live Migration
Ensure `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are configured in your `.env`, then execute:

```powershell
cd c:\Users\kiran\UrbanSage\backend
python -m app.db.migrate_sqlite_to_supabase --force
```

**Guarantees Enforced During Migration**:
- **Idempotency**: Uses PostgreSQL `upsert` on primary key `id`. Re-running does not duplicate data or corrupt existing entries.
- **Privacy**: `reporter_contact` is preserved in the secure table, but redacted from all console and log outputs.
- **Verification**: Automatically queries Supabase after insertion to confirm that source and destination counts match and all IDs exist.

---

## 6. Running and Verifying the Backend

### Start the Backend Service
```powershell
cd c:\Users\kiran\UrbanSage\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 1. Verify Service Health & Active Database
```powershell
curl http://127.0.0.1:8000/health
```
Response:
```json
{
  "status": "healthy",
  "service": "UrbanSage AI API",
  "version": "1.0.0",
  "database_backend": "supabase",
  "timestamp": "2026-10-23T12:00:00.000000Z"
}
```

### 2. Verify Report Listing in Supabase
```powershell
curl http://127.0.0.1:8000/api/reports
```

### 3. Verify in Supabase Dashboard
1. Open the Supabase Dashboard &rarr; **Table Editor**.
2. Select table `citizen_reports`.
3. Confirm that reports appear with `RPT-XXXXXXXX` IDs, computed `urgency_score`, `evidence_confidence_score`, and `status`.

---

## 7. Troubleshooting & Common Issues

| Issue / Error | Cause | Resolution |
| :--- | :--- | :--- |
| `ReportPersistenceError: Supabase database configuration missing` | `SUPABASE_URL` or `SUPABASE_SECRET_KEY` not found in environment. | Ensure `.env` exists in `backend/` and contains valid project credentials. |
| `401 Unauthorized / JWT expired` | Invalid or expired service key. | Verify you copied the `service_role` key (or secret key), not the `anon` key. |
| `DuplicateReportError (HTTP 409)` | Same reporter submitted identical report within 30 minutes and 0.5 km. | Anti-duplicate throttle working as designed. Wait for window to expire or use distinct location/reporter. |
| `422 Unprocessable Entity` | Field validation failed (e.g. description < 10 chars, severity not 1–5). | Verify request body adheres to Pydantic schema constraints. |

---

## 8. Credential Rotation Procedure

If a secret key is compromised:
1. In the Supabase Dashboard, navigate to **Project Settings** &rarr; **API**.
2. Under *JWT Settings*, click **Generate new secret** / **Roll API Key**.
3. Immediately update `SUPABASE_SECRET_KEY` in `backend/.env`.
4. Restart the backend process:
   ```powershell
   python -m uvicorn app.main:app --port 8000
   ```
5. Previous keys become invalid immediately.

---

## 9. Running Offline Tests (Without Touching Cloud Supabase)

To run the complete automated test suite locally without network dependencies or Supabase credentials:

```powershell
cd c:\Users\kiran\UrbanSage\backend
# Runs 248 tests including isolated Supabase mocks and SQLite offline checks
python -m pytest -v
```
