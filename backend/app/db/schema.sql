-- ============================================================================
-- UrbanSage AI — Complete Consolidated Supabase PostgreSQL Schema
-- ============================================================================
-- Combines:
--   1. Migration 001: Citizen Environmental Reporting & Report Lifecycle
--   2. Migration 002: Financial Accountability & Audit Portal
--
-- Instructions:
--   Run this entire script in the Supabase Dashboard SQL Editor to set up
--   a fresh Supabase project. It is idempotent and safe to run multiple times.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PART 1: Citizen Environmental Problem Reporting & Operational Lifecycle
-- ----------------------------------------------------------------------------

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

-- Indexes for citizen_reports
CREATE INDEX IF NOT EXISTS idx_citizen_reports_category ON public.citizen_reports (category);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_status ON public.citizen_reports (status);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_neighbourhood ON public.citizen_reports (neighbourhood_id);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_reporter ON public.citizen_reports (reporter_id);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_created_at ON public.citizen_reports (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_throttle ON public.citizen_reports (reporter_id, category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_corroboration ON public.citizen_reports (category, created_at DESC);

-- Automatic updated_at Trigger Function
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

-- Public View for Safe External Querying (Excludes Private Contact)
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

-- Citizen Reports RLS
ALTER TABLE public.citizen_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Service role full access on citizen_reports" ON public.citizen_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Public insert citizen reports" ON public.citizen_reports;
CREATE POLICY "Public insert citizen reports" ON public.citizen_reports FOR INSERT TO anon, authenticated
    WITH CHECK (status = 'submitted' AND verification_status = 'unverified' AND is_verified_measurement = FALSE);

DROP POLICY IF EXISTS "Public read non-sensitive reports" ON public.citizen_reports;
CREATE POLICY "Public read non-sensitive reports" ON public.citizen_reports FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Deny public update on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Deny public update on citizen_reports" ON public.citizen_reports FOR UPDATE TO anon USING (false);

DROP POLICY IF EXISTS "Deny public delete on citizen_reports" ON public.citizen_reports;
CREATE POLICY "Deny public delete on citizen_reports" ON public.citizen_reports FOR DELETE TO anon USING (false);

GRANT SELECT ON public.citizen_reports_public TO anon, authenticated, service_role;
GRANT SELECT, INSERT ON public.citizen_reports TO anon, authenticated;
GRANT ALL ON public.citizen_reports TO service_role;


-- ----------------------------------------------------------------------------
-- PART 2: Stage 6 Financial Accountability & Audit Portal
-- ----------------------------------------------------------------------------

-- 1. Allocations Table
CREATE TABLE IF NOT EXISTS public.allocations (
    allocation_id VARCHAR(16) PRIMARY KEY,
    title TEXT NOT NULL,
    neighbourhood_id VARCHAR(32) NOT NULL,
    neighbourhood_name VARCHAR(100) NOT NULL,
    intervention_id VARCHAR(32) NOT NULL,
    intervention_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    fiscal_year VARCHAR(16) NOT NULL DEFAULT '2025-2026',
    currency VARCHAR(8) NOT NULL DEFAULT 'INR',
    allocated_amount_lakh NUMERIC(12, 4) NOT NULL,
    committed_amount_lakh NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    disbursed_amount_lakh NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    planned_units INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'planned',
    authorized_by VARCHAR(100) NOT NULL,
    council_resolution_ref VARCHAR(100),
    source_optimizer_run_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_allocation_id_format CHECK (allocation_id ~ '^ALC-[0-9A-F]{8}$'),
    CONSTRAINT chk_allocated_amount_positive CHECK (allocated_amount_lakh > 0.0),
    CONSTRAINT chk_committed_amount_non_negative CHECK (committed_amount_lakh >= 0.0),
    CONSTRAINT chk_disbursed_amount_non_negative CHECK (disbursed_amount_lakh >= 0.0),
    CONSTRAINT chk_committed_le_allocated CHECK (committed_amount_lakh <= allocated_amount_lakh),
    CONSTRAINT chk_disbursed_le_allocated CHECK (disbursed_amount_lakh <= allocated_amount_lakh),
    CONSTRAINT chk_planned_units_positive CHECK (planned_units > 0),
    CONSTRAINT chk_allocation_status CHECK (status IN ('planned', 'committed', 'in_progress', 'completed', 'frozen', 'cancelled'))
);

-- 2. Commitments Table
CREATE TABLE IF NOT EXISTS public.commitments (
    commitment_id VARCHAR(16) PRIMARY KEY,
    allocation_id VARCHAR(16) NOT NULL REFERENCES public.allocations(allocation_id) ON DELETE CASCADE,
    vendor_id VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(200) NOT NULL,
    contract_reference VARCHAR(100) NOT NULL,
    committed_amount_lakh NUMERIC(12, 4) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'approved',
    approved_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_commitment_id_format CHECK (commitment_id ~ '^CMT-[0-9A-F]{8}$'),
    CONSTRAINT chk_commitment_amount_positive CHECK (committed_amount_lakh > 0.0),
    CONSTRAINT chk_commitment_status CHECK (status IN ('draft', 'approved', 'active', 'fulfilled', 'cancelled'))
);

-- 3. Milestones Table
CREATE TABLE IF NOT EXISTS public.milestones (
    milestone_id VARCHAR(16) PRIMARY KEY,
    allocation_id VARCHAR(16) NOT NULL REFERENCES public.allocations(allocation_id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    sequence_order INTEGER NOT NULL,
    target_completion_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    disbursement_tied_amount_lakh NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    percent_progress SMALLINT NOT NULL DEFAULT 0,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_milestone_id_format CHECK (milestone_id ~ '^MLS-[0-9A-F]{8}$'),
    CONSTRAINT chk_sequence_order_range CHECK (sequence_order >= 1 AND sequence_order <= 50),
    CONSTRAINT chk_percent_progress_range CHECK (percent_progress >= 0 AND percent_progress <= 100),
    CONSTRAINT chk_disbursement_tied_non_negative CHECK (disbursement_tied_amount_lakh >= 0.0),
    CONSTRAINT chk_milestone_status CHECK (status IN ('pending', 'in_progress', 'submitted_for_review', 'verified_complete', 'failed_verification'))
);

-- 4. Evidence Metadata Table
CREATE TABLE IF NOT EXISTS public.evidence_metadata (
    evidence_id VARCHAR(16) PRIMARY KEY,
    milestone_id VARCHAR(16) NOT NULL REFERENCES public.milestones(milestone_id) ON DELETE CASCADE,
    evidence_type VARCHAR(32) NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    document_hash VARCHAR(64) NOT NULL,
    submitted_by VARCHAR(100) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verification_status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    verification_notes TEXT,

    CONSTRAINT chk_evidence_id_format CHECK (evidence_id ~ '^EVD-[0-9A-F]{8}$'),
    CONSTRAINT chk_file_size_bytes_positive CHECK (file_size_bytes > 0 AND file_size_bytes <= 50000000),
    CONSTRAINT chk_evidence_type CHECK (evidence_type IN ('site_photo', 'inspection_report', 'material_invoice', 'community_sign_off', 'geo_survey')),
    CONSTRAINT chk_evidence_verification_status CHECK (verification_status IN ('pending_review', 'verified', 'rejected'))
);

-- 5. Verification Decisions Table
CREATE TABLE IF NOT EXISTS public.verification_decisions (
    decision_id VARCHAR(16) PRIMARY KEY,
    milestone_id VARCHAR(16) UNIQUE NOT NULL REFERENCES public.milestones(milestone_id) ON DELETE CASCADE,
    decision VARCHAR(32) NOT NULL,
    verifier_id VARCHAR(100) NOT NULL,
    verifier_name VARCHAR(150) NOT NULL,
    comments TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    passed_inspection BOOLEAN NOT NULL,

    CONSTRAINT chk_decision_id_format CHECK (decision_id ~ '^VDEC-[0-9A-F]{8}$'),
    CONSTRAINT chk_verification_decision_value CHECK (decision IN ('approved', 'rejected', 'revision_requested'))
);

-- 6. Disbursements Table
CREATE TABLE IF NOT EXISTS public.disbursements (
    disbursement_id VARCHAR(16) PRIMARY KEY,
    allocation_id VARCHAR(16) NOT NULL REFERENCES public.allocations(allocation_id) ON DELETE CASCADE,
    commitment_id VARCHAR(16) NOT NULL REFERENCES public.commitments(commitment_id) ON DELETE CASCADE,
    milestone_id VARCHAR(16) REFERENCES public.milestones(milestone_id) ON DELETE SET NULL,
    amount_lakh NUMERIC(12, 4) NOT NULL,
    payment_reference VARCHAR(100) NOT NULL,
    recipient_entity VARCHAR(200) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    approved_by VARCHAR(100) NOT NULL,
    disbursed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_disbursement_id_format CHECK (disbursement_id ~ '^DSB-[0-9A-F]{8}$'),
    CONSTRAINT chk_disbursement_amount_positive CHECK (amount_lakh > 0.0),
    CONSTRAINT chk_disbursement_status CHECK (status IN ('pending_approval', 'completed', 'rejected', 'reversed'))
);

-- 7. Discrepancies Table
CREATE TABLE IF NOT EXISTS public.discrepancies (
    discrepancy_id VARCHAR(16) PRIMARY KEY,
    allocation_id VARCHAR(16) NOT NULL REFERENCES public.allocations(allocation_id) ON DELETE CASCADE,
    severity VARCHAR(16) NOT NULL,
    discrepancy_type VARCHAR(32) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    amount_involved_lakh NUMERIC(12, 4) NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,

    CONSTRAINT chk_discrepancy_id_format CHECK (discrepancy_id ~ '^DSC-[0-9A-F]{8}$'),
    CONSTRAINT chk_discrepancy_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_discrepancy_type CHECK (discrepancy_type IN ('cost_overrun', 'unverified_disbursement', 'milestone_stalled', 'evidence_missing', 'budget_mismatch')),
    CONSTRAINT chk_discrepancy_status CHECK (status IN ('open', 'under_review', 'resolved', 'dismissed'))
);

-- 8. Audit Events Table
CREATE TABLE IF NOT EXISTS public.audit_events (
    event_id VARCHAR(16) PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    previous_event_hash VARCHAR(64) NOT NULL,
    event_hash VARCHAR(64) NOT NULL,

    CONSTRAINT chk_audit_event_id_format CHECK (event_id ~ '^AUD-[0-9A-F]{8}$'),
    CONSTRAINT chk_actor_role CHECK (actor_role IN ('administrator', 'contractor', 'system')),
    CONSTRAINT chk_entity_type CHECK (entity_type IN ('ALLOCATION', 'COMMITMENT', 'MILESTONE', 'EVIDENCE', 'DISBURSEMENT', 'DISCREPANCY'))
);

-- Indexes for Financial Tables
CREATE INDEX IF NOT EXISTS idx_allocations_neighbourhood ON public.allocations (neighbourhood_id);
CREATE INDEX IF NOT EXISTS idx_allocations_category ON public.allocations (category);
CREATE INDEX IF NOT EXISTS idx_allocations_status ON public.allocations (status);
CREATE INDEX IF NOT EXISTS idx_commitments_allocation ON public.commitments (allocation_id);
CREATE INDEX IF NOT EXISTS idx_milestones_allocation ON public.milestones (allocation_id);
CREATE INDEX IF NOT EXISTS idx_disbursements_allocation ON public.disbursements (allocation_id);
CREATE INDEX IF NOT EXISTS idx_discrepancies_allocation ON public.discrepancies (allocation_id);
CREATE INDEX IF NOT EXISTS idx_discrepancies_status ON public.discrepancies (status);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON public.audit_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON public.audit_events (entity_type, entity_id);

-- Triggers for Financial Tables
DROP TRIGGER IF EXISTS trg_allocations_updated_at ON public.allocations;
CREATE TRIGGER trg_allocations_updated_at
BEFORE UPDATE ON public.allocations
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

DROP TRIGGER IF EXISTS trg_milestones_updated_at ON public.milestones;
CREATE TRIGGER trg_milestones_updated_at
BEFORE UPDATE ON public.milestones
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

-- Financial Tables RLS
ALTER TABLE public.allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disbursements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discrepancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

-- Service Role Policies (ALL)
DROP POLICY IF EXISTS "Service role full access on allocations" ON public.allocations;
CREATE POLICY "Service role full access on allocations" ON public.allocations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on commitments" ON public.commitments;
CREATE POLICY "Service role full access on commitments" ON public.commitments FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on milestones" ON public.milestones;
CREATE POLICY "Service role full access on milestones" ON public.milestones FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on evidence_metadata" ON public.evidence_metadata;
CREATE POLICY "Service role full access on evidence_metadata" ON public.evidence_metadata FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on verification_decisions" ON public.verification_decisions;
CREATE POLICY "Service role full access on verification_decisions" ON public.verification_decisions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on disbursements" ON public.disbursements;
CREATE POLICY "Service role full access on disbursements" ON public.disbursements FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on discrepancies" ON public.discrepancies;
CREATE POLICY "Service role full access on discrepancies" ON public.discrepancies FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on audit_events" ON public.audit_events;
CREATE POLICY "Service role full access on audit_events" ON public.audit_events FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Public Read Policies
DROP POLICY IF EXISTS "Public read on allocations" ON public.allocations;
CREATE POLICY "Public read on allocations" ON public.allocations FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read on commitments" ON public.commitments;
CREATE POLICY "Public read on commitments" ON public.commitments FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read on milestones" ON public.milestones;
CREATE POLICY "Public read on milestones" ON public.milestones FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read on evidence_metadata" ON public.evidence_metadata;
CREATE POLICY "Public read on evidence_metadata" ON public.evidence_metadata FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read on verification_decisions" ON public.verification_decisions;
CREATE POLICY "Public read on verification_decisions" ON public.verification_decisions FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "Public read on disbursements" ON public.disbursements;
CREATE POLICY "Public read on disbursements" ON public.disbursements FOR SELECT TO anon, authenticated USING (true);

-- Audit Events Immutability
DROP POLICY IF EXISTS "Deny update on audit_events" ON public.audit_events;
CREATE POLICY "Deny update on audit_events" ON public.audit_events FOR UPDATE TO anon, authenticated USING (false);

DROP POLICY IF EXISTS "Deny delete on audit_events" ON public.audit_events;
CREATE POLICY "Deny delete on audit_events" ON public.audit_events FOR DELETE TO anon, authenticated USING (false);

-- Authenticated Auditor Policy on Discrepancies
DROP POLICY IF EXISTS "Authenticated read on discrepancies" ON public.discrepancies;
CREATE POLICY "Authenticated read on discrepancies" ON public.discrepancies FOR SELECT TO authenticated USING (true);

-- Permissions Grants
GRANT SELECT ON public.allocations TO anon, authenticated;
GRANT SELECT ON public.commitments TO anon, authenticated;
GRANT SELECT ON public.milestones TO anon, authenticated;
GRANT SELECT ON public.evidence_metadata TO anon, authenticated;
GRANT SELECT ON public.verification_decisions TO anon, authenticated;
GRANT SELECT ON public.disbursements TO anon, authenticated;
GRANT SELECT ON public.discrepancies TO authenticated;
GRANT SELECT ON public.audit_events TO authenticated;

GRANT ALL ON public.allocations TO service_role;
GRANT ALL ON public.commitments TO service_role;
GRANT ALL ON public.milestones TO service_role;
GRANT ALL ON public.evidence_metadata TO service_role;
GRANT ALL ON public.verification_decisions TO service_role;
GRANT ALL ON public.disbursements TO service_role;
GRANT ALL ON public.discrepancies TO service_role;
GRANT ALL ON public.audit_events TO service_role;
