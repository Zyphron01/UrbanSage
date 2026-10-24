-- ============================================================================
-- UrbanSage AI — Supabase PostgreSQL Schema Migration (002)
-- Stage 6: Financial Accountability & Audit Portal
-- ============================================================================
-- Purpose:
--   Establishes the municipal financial accountability ledger, tracking
--   capital expenditure allocations, vendor contractual commitments,
--   implementation milestones, documentary evidence metadata, inspection
--   verification decisions, authorized payouts, automated discrepancy flags,
--   and cryptographic SHA-256 hash-chained audit trails.
-- ============================================================================

-- 1. Allocations Table: Authoritative Municipal Appropriations
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

    -- Constraints
    CONSTRAINT chk_allocation_id_format
        CHECK (allocation_id ~ '^ALC-[0-9A-F]{8}$'),
    CONSTRAINT chk_allocated_amount_positive
        CHECK (allocated_amount_lakh > 0.0),
    CONSTRAINT chk_committed_amount_non_negative
        CHECK (committed_amount_lakh >= 0.0),
    CONSTRAINT chk_disbursed_amount_non_negative
        CHECK (disbursed_amount_lakh >= 0.0),
    CONSTRAINT chk_committed_le_allocated
        CHECK (committed_amount_lakh <= allocated_amount_lakh),
    CONSTRAINT chk_disbursed_le_allocated
        CHECK (disbursed_amount_lakh <= allocated_amount_lakh),
    CONSTRAINT chk_planned_units_positive
        CHECK (planned_units > 0),
    CONSTRAINT chk_allocation_status
        CHECK (status IN ('planned', 'committed', 'in_progress', 'completed', 'frozen', 'cancelled'))
);

-- 2. Commitments Table: Vendor Contracts & Work Orders
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

    -- Constraints
    CONSTRAINT chk_commitment_id_format
        CHECK (commitment_id ~ '^CMT-[0-9A-F]{8}$'),
    CONSTRAINT chk_commitment_amount_positive
        CHECK (committed_amount_lakh > 0.0),
    CONSTRAINT chk_commitment_status
        CHECK (status IN ('draft', 'approved', 'active', 'fulfilled', 'cancelled'))
);

-- 3. Milestones Table: Physical Delivery Progress
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

    -- Constraints
    CONSTRAINT chk_milestone_id_format
        CHECK (milestone_id ~ '^MLS-[0-9A-F]{8}$'),
    CONSTRAINT chk_sequence_order_range
        CHECK (sequence_order >= 1 AND sequence_order <= 50),
    CONSTRAINT chk_percent_progress_range
        CHECK (percent_progress >= 0 AND percent_progress <= 100),
    CONSTRAINT chk_disbursement_tied_non_negative
        CHECK (disbursement_tied_amount_lakh >= 0.0),
    CONSTRAINT chk_milestone_status
        CHECK (status IN ('pending', 'in_progress', 'submitted_for_review', 'verified_complete', 'failed_verification'))
);

-- 4. Evidence Metadata Table: Documentary Proof
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

    -- Constraints
    CONSTRAINT chk_evidence_id_format
        CHECK (evidence_id ~ '^EVD-[0-9A-F]{8}$'),
    CONSTRAINT chk_file_size_bytes_positive
        CHECK (file_size_bytes > 0 AND file_size_bytes <= 50000000),
    CONSTRAINT chk_evidence_type
        CHECK (evidence_type IN ('site_photo', 'inspection_report', 'material_invoice', 'community_sign_off', 'geo_survey')),
    CONSTRAINT chk_evidence_verification_status
        CHECK (verification_status IN ('pending_review', 'verified', 'rejected'))
);

-- 5. Verification Decisions Table: Formal Inspection Sign-offs
CREATE TABLE IF NOT EXISTS public.verification_decisions (
    decision_id VARCHAR(16) PRIMARY KEY,
    milestone_id VARCHAR(16) UNIQUE NOT NULL REFERENCES public.milestones(milestone_id) ON DELETE CASCADE,
    decision VARCHAR(32) NOT NULL,
    verifier_id VARCHAR(100) NOT NULL,
    verifier_name VARCHAR(150) NOT NULL,
    comments TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    passed_inspection BOOLEAN NOT NULL,

    -- Constraints
    CONSTRAINT chk_decision_id_format
        CHECK (decision_id ~ '^VDEC-[0-9A-F]{8}$'),
    CONSTRAINT chk_verification_decision_value
        CHECK (decision IN ('approved', 'rejected', 'revision_requested'))
);

-- 6. Disbursements Table: Authorized Contractor Payouts
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

    -- Constraints
    CONSTRAINT chk_disbursement_id_format
        CHECK (disbursement_id ~ '^DSB-[0-9A-F]{8}$'),
    CONSTRAINT chk_disbursement_amount_positive
        CHECK (amount_lakh > 0.0),
    CONSTRAINT chk_disbursement_status
        CHECK (status IN ('pending_approval', 'completed', 'rejected', 'reversed'))
);

-- 7. Discrepancies Table: Automated Audit Flags
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

    -- Constraints
    CONSTRAINT chk_discrepancy_id_format
        CHECK (discrepancy_id ~ '^DSC-[0-9A-F]{8}$'),
    CONSTRAINT chk_discrepancy_severity
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_discrepancy_type
        CHECK (discrepancy_type IN ('cost_overrun', 'unverified_disbursement', 'milestone_stalled', 'evidence_missing', 'budget_mismatch')),
    CONSTRAINT chk_discrepancy_status
        CHECK (status IN ('open', 'under_review', 'resolved', 'dismissed'))
);

-- 8. Audit Events Table: Cryptographically Hash-Chained Log
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

    -- Constraints
    CONSTRAINT chk_audit_event_id_format
        CHECK (event_id ~ '^AUD-[0-9A-F]{8}$'),
    CONSTRAINT chk_actor_role
        CHECK (actor_role IN ('administrator', 'contractor', 'system')),
    CONSTRAINT chk_entity_type
        CHECK (entity_type IN ('ALLOCATION', 'COMMITMENT', 'MILESTONE', 'EVIDENCE', 'DISBURSEMENT', 'DISCREPANCY'))
);

-- Indexes for High Performance Queries
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

-- Automatic updated_at trigger function (idempotent definition)
CREATE OR REPLACE FUNCTION public.set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- Row Level Security (RLS) Configuration
ALTER TABLE public.allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disbursements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discrepancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

-- 1. Service Role (Full administrative access for backend API)
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

-- 2. Public Read Access (Civic Transparency on Allocations, Milestones, and Commitments)
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

-- 3. Strict Append-Only Constraint on Audit Events (Deny UPDATE and DELETE to all non-superusers)
DROP POLICY IF EXISTS "Deny update on audit_events" ON public.audit_events;
CREATE POLICY "Deny update on audit_events" ON public.audit_events FOR UPDATE TO anon, authenticated USING (false);

DROP POLICY IF EXISTS "Deny delete on audit_events" ON public.audit_events;
CREATE POLICY "Deny delete on audit_events" ON public.audit_events FOR DELETE TO anon, authenticated USING (false);

-- 4. Permissions Grants (Discrepancies and Audit Events restricted to service_role)
GRANT SELECT ON public.allocations TO anon, authenticated;
GRANT SELECT ON public.commitments TO anon, authenticated;
GRANT SELECT ON public.milestones TO anon, authenticated;
GRANT SELECT ON public.evidence_metadata TO anon, authenticated;
GRANT SELECT ON public.verification_decisions TO anon, authenticated;
GRANT SELECT ON public.disbursements TO anon, authenticated;

GRANT ALL ON public.allocations TO service_role;
GRANT ALL ON public.commitments TO service_role;
GRANT ALL ON public.milestones TO service_role;
GRANT ALL ON public.evidence_metadata TO service_role;
GRANT ALL ON public.verification_decisions TO service_role;
GRANT ALL ON public.disbursements TO service_role;
GRANT ALL ON public.discrepancies TO service_role;
GRANT ALL ON public.audit_events TO service_role;
