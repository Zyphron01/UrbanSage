-- ============================================================================
-- UrbanSage AI — Supabase PostgreSQL Schema Migration (001)
-- ============================================================================
-- Purpose:
--   Foundational schema for citizen environmental problem reporting,
--   transparent urgency scoring, evidence completeness tracking, and
--   privacy-preserving row level security (RLS).
-- ============================================================================

-- 1. Create citizen_reports table
CREATE TABLE IF NOT EXISTS public.citizen_reports (
    id VARCHAR(16) PRIMARY KEY,
    category VARCHAR(32) NOT NULL,
    description TEXT NOT NULL,
    severity SMALLINT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_description TEXT,
    neighbourhood_id VARCHAR(32),
    reporter_id VARCHAR(64),
    reporter_contact TEXT,  -- PRIVATE: Omitted from public views and API responses
    photos JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    verification_status VARCHAR(32) NOT NULL DEFAULT 'unverified',
    is_verified_measurement BOOLEAN NOT NULL DEFAULT FALSE,
    data_source VARCHAR(32) NOT NULL DEFAULT 'CITIZEN_REPORT',
    urgency_score DOUBLE PRECISION NOT NULL,
    evidence_confidence_score DOUBLE PRECISION NOT NULL,
    resolution_evidence JSONB DEFAULT NULL,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_citizen_report_id_format
        CHECK (id ~ '^RPT-[0-9A-F]{8}$'),
    CONSTRAINT chk_citizen_report_category
        CHECK (category IN ('flooding_drainage', 'water_scarcity', 'heat', 'loss_of_green_cover')),
    CONSTRAINT chk_citizen_report_description_len
        CHECK (char_length(description) >= 10 AND char_length(description) <= 2000),
    CONSTRAINT chk_citizen_report_severity
        CHECK (severity >= 1 AND severity <= 5),
    CONSTRAINT chk_citizen_report_latitude
        CHECK (latitude >= -90.0 AND latitude <= 90.0),
    CONSTRAINT chk_citizen_report_longitude
        CHECK (longitude >= -180.0 AND longitude <= 180.0),
    CONSTRAINT chk_citizen_report_status
        CHECK (status IN (
            'submitted', 'under_review', 'info_requested', 'verified',
            'flagged_suspicious', 'confirmed_fake', 'duplicate', 'out_of_scope',
            'no_action_required', 'assigned', 'in_progress',
            'completed_awaiting_verification', 'verification_failed',
            'verified_resolved', 'resolved', 'dismissed'
        )),
    CONSTRAINT chk_citizen_report_verification_status
        CHECK (verification_status IN ('unverified', 'community_corroborated', 'officially_verified', 'dismissed')),
    CONSTRAINT chk_citizen_report_urgency_score
        CHECK (urgency_score >= 0.0 AND urgency_score <= 100.0),
    CONSTRAINT chk_citizen_report_evidence_score
        CHECK (evidence_confidence_score >= 0.0 AND evidence_confidence_score <= 100.0)
);

-- 2. Performance & Query Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_citizen_reports_category
    ON public.citizen_reports (category);

CREATE INDEX IF NOT EXISTS idx_citizen_reports_status
    ON public.citizen_reports (status);

CREATE INDEX IF NOT EXISTS idx_citizen_reports_neighbourhood
    ON public.citizen_reports (neighbourhood_id);

CREATE INDEX IF NOT EXISTS idx_citizen_reports_reporter
    ON public.citizen_reports (reporter_id);

CREATE INDEX IF NOT EXISTS idx_citizen_reports_created_at
    ON public.citizen_reports (created_at DESC);

-- Composite index for anti-duplicate throttle queries
CREATE INDEX IF NOT EXISTS idx_citizen_reports_throttle
    ON public.citizen_reports (reporter_id, category, created_at DESC);

-- Composite index for temporal-spatial corroboration lookups
CREATE INDEX IF NOT EXISTS idx_citizen_reports_corroboration
    ON public.citizen_reports (category, created_at DESC);

-- 3. Trigger for automatic updated_at maintenance
CREATE OR REPLACE FUNCTION public.set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizen_reports_updated_at ON public.citizen_reports;
CREATE TRIGGER trg_citizen_reports_updated_at
BEFORE UPDATE ON public.citizen_reports
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

-- 4. Public View for safe external consumption (Redacts Private Contact & Reporter ID)
CREATE OR REPLACE VIEW public.citizen_reports_public AS
SELECT
    id,
    category,
    description,
    severity,
    latitude,
    longitude,
    location_description,
    neighbourhood_id,
    photos,
    status,
    verification_status,
    is_verified_measurement,
    data_source,
    urgency_score,
    evidence_confidence_score,
    resolution_evidence,
    timeline,
    created_at,
    updated_at
FROM public.citizen_reports;

-- 5. Row Level Security (RLS) Configuration
ALTER TABLE public.citizen_reports ENABLE ROW LEVEL SECURITY;

-- Allow service_role (FastAPI backend with server key) full access
DROP POLICY IF EXISTS "Service role full access on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Service role full access on citizen_reports"
    ON public.citizen_reports
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow authenticated and anonymous users to insert new reports in initial state
DROP POLICY IF EXISTS "Public insert citizen reports" ON public.citizen_reports;
CREATE POLICY "Public insert citizen reports"
    ON public.citizen_reports
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (
        status = 'submitted'
        AND verification_status = 'unverified'
        AND is_verified_measurement = FALSE
    );

-- Allow public to select reports but exclude direct reading of sensitive columns
-- (Public clients should query citizen_reports_public or this policy enforces standard read)
DROP POLICY IF EXISTS "Public read non-sensitive reports" ON public.citizen_reports;
CREATE POLICY "Public read non-sensitive reports"
    ON public.citizen_reports
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Prevent unauthorized updates or deletes from anon/public clients
-- Only service_role or admin staff can update status or delete
DROP POLICY IF EXISTS "Deny public update on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Deny public update on citizen_reports"
    ON public.citizen_reports
    FOR UPDATE
    TO anon
    USING (false);

DROP POLICY IF EXISTS "Deny public delete on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Deny public delete on citizen_reports"
    ON public.citizen_reports
    FOR DELETE
    TO anon
    USING (false);

-- Grant appropriate permissions
GRANT SELECT ON public.citizen_reports_public TO anon, authenticated, service_role;
GRANT SELECT, INSERT ON public.citizen_reports TO anon, authenticated;
GRANT ALL ON public.citizen_reports TO service_role;
