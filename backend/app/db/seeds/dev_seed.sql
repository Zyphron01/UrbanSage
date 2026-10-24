-- ============================================================================
-- UrbanSage AI — Development & Demonstration Seed Data (Supabase PostgreSQL)
-- ============================================================================
-- IMPORTANT NOTICE:
--   DO NOT EXECUTE THIS SCRIPT IN A PRODUCTION ENVIRONMENT.
--   This seed script provides calibrated demonstration records for local
--   evaluations, hackathon showcases, and staging test verification.
-- ============================================================================

-- 1. Sample Citizen Environmental Reports
INSERT INTO public.citizen_reports (
    id, category, description, severity, latitude, longitude,
    location_description, neighbourhood_id, reporter_id, reporter_contact,
    photos, status, verification_status, is_verified_measurement,
    data_source, urgency_score, evidence_confidence_score, created_at, updated_at
) VALUES
(
    'RPT-00000001',
    'flooding_drainage',
    'Severe street flooding along 80 Feet Road following pre-monsoon storm. Water depth approx 35cm blocking lane access.',
    4,
    12.9352,
    77.6245,
    '80 Feet Road, 4th Block, Koramangala',
    'NBR-001',
    'CITIZEN-DEMO-01',
    'citizen01@example.com',
    '[]'::jsonb,
    'under_review',
    'community_corroborated',
    FALSE,
    'CITIZEN_REPORT',
    78.5,
    65.0,
    NOW() - INTERVAL '6 hours',
    NOW() - INTERVAL '5 hours'
),
(
    'RPT-00000002',
    'water_scarcity',
    'Borewell yield dropped below critical threshold. Secondary commercial water tankers failing to meet domestic requirements.',
    3,
    12.9784,
    77.6408,
    '12th Main Road, HAL 2nd Stage, Indiranagar',
    'NBR-002',
    'CITIZEN-DEMO-02',
    'resident02@example.com',
    '[]'::jsonb,
    'submitted',
    'unverified',
    FALSE,
    'CITIZEN_REPORT',
    62.0,
    45.0,
    NOW() - INTERVAL '14 hours',
    NOW() - INTERVAL '14 hours'
),
(
    'RPT-00000003',
    'heat',
    'Urban heat island hotspot with zero shade canopy along arterial transport interchange. Surface temps exceeding 41C.',
    4,
    12.9698,
    77.7499,
    'ITPB Main Gate, Whitefield Corridor',
    'NBR-004',
    'CITIZEN-DEMO-03',
    'commuter03@example.com',
    '[]'::jsonb,
    'assigned',
    'officially_verified',
    FALSE,
    'CITIZEN_REPORT',
    82.0,
    90.0,
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '1 day'
)
ON CONFLICT (id) DO NOTHING;


-- 2. Sample Financial Allocations (Stage 6)
INSERT INTO public.allocations (
    allocation_id, title, neighbourhood_id, neighbourhood_name,
    intervention_id, intervention_name, category, fiscal_year,
    currency, allocated_amount_lakh, committed_amount_lakh,
    disbursed_amount_lakh, planned_units, status, authorized_by,
    council_resolution_ref, created_at, updated_at
) VALUES
(
    'ALC-00000001',
    'Koramangala Valley Stormwater Drain Desilting & Bioswales',
    'NBR-001',
    'Koramangala',
    'INT-DRAIN-01',
    'Engineered Bioswales & Silt Traps',
    'drainage',
    '2025-2026',
    'INR',
    35.0000,
    32.5000,
    25.0000,
    4,
    'in_progress',
    'MUNICIPAL_COMMISSIONER',
    'BBMP/CR/2025/ENV-042',
    NOW() - INTERVAL '30 days',
    NOW()
),
(
    'ALC-00000002',
    'Indiranagar 100ft Road Permeable Pavements & Rain Gardens',
    'NBR-002',
    'Indiranagar',
    'INT-RAIN-02',
    'Interlocking Permeable Concrete Pavement',
    'flooding_drainage',
    '2025-2026',
    'INR',
    25.0000,
    24.0000,
    8.0000,
    3,
    'in_progress',
    'MUNICIPAL_COMMISSIONER',
    'BBMP/CR/2025/ENV-049',
    NOW() - INTERVAL '20 days',
    NOW()
),
(
    'ALC-00000003',
    'Whitefield IT Corridor Micro-Forest Canopy & Miyawaki Afforestation',
    'NBR-004',
    'Whitefield',
    'INT-TREE-01',
    'High-Density Miyawaki Urban Forest',
    'urban_forest',
    '2025-2026',
    'INR',
    40.0000,
    38.0000,
    12.0000,
    2,
    'in_progress',
    'MUNICIPAL_COMMISSIONER',
    'BBMP/CR/2025/ENV-055',
    NOW() - INTERVAL '15 days',
    NOW()
)
ON CONFLICT (allocation_id) DO NOTHING;


-- 3. Sample Financial Commitments
INSERT INTO public.commitments (
    commitment_id, allocation_id, vendor_id, vendor_name,
    contract_reference, committed_amount_lakh, status, approved_by, created_at
) VALUES
(
    'CMT-00000001',
    'ALC-00000001',
    'VND-BBMP-WORKS-01',
    'Bengaluru Urban Drainage & Infra Ltd',
    'CNT-2025-BLR-0114',
    32.5000,
    'active',
    'FINANCE_OFFICER_01',
    NOW() - INTERVAL '28 days'
),
(
    'CMT-00000002',
    'ALC-00000002',
    'VND-ECO-INFRA-02',
    'GreenGrid Urban Solutions Pvt Ltd',
    'CNT-2025-BLR-0205',
    24.0000,
    'active',
    'FINANCE_OFFICER_01',
    NOW() - INTERVAL '18 days'
)
ON CONFLICT (commitment_id) DO NOTHING;


-- 4. Sample Milestones
INSERT INTO public.milestones (
    milestone_id, allocation_id, title, description,
    sequence_order, target_completion_date, status,
    disbursement_tied_amount_lakh, percent_progress, completed_at, created_at, updated_at
) VALUES
(
    'MLS-00000001',
    'ALC-00000001',
    'Site Survey, Bathymetry & Sediment Cleansing',
    'Initial sediment profiling, boundary demarcations and heavy machinery mobilization.',
    1,
    CURRENT_DATE + INTERVAL '30 days',
    'verified_complete',
    10.0000,
    100,
    NOW() - INTERVAL '20 days',
    NOW() - INTERVAL '28 days',
    NOW() - INTERVAL '20 days'
),
(
    'MLS-00000002',
    'ALC-00000001',
    'Bioswale Channel Shaping & Native Vetiver Planting',
    'Grading channel edges to 3:1 slopes and planting vetiver roots for natural filtration.',
    2,
    CURRENT_DATE + INTERVAL '60 days',
    'verified_complete',
    15.0000,
    100,
    NOW() - INTERVAL '10 days',
    NOW() - INTERVAL '28 days',
    NOW() - INTERVAL '10 days'
),
(
    'MLS-00000003',
    'ALC-00000001',
    'Perimeter Overflow Weir & Monitoring Telemetry Installation',
    'Reinforced concrete overflow spillway and automated ultrasonic level sensors.',
    3,
    CURRENT_DATE + INTERVAL '90 days',
    'in_progress',
    7.5000,
    60,
    NULL,
    NOW() - INTERVAL '28 days',
    NOW()
)
ON CONFLICT (milestone_id) DO NOTHING;


-- 5. Sample Disbursements
INSERT INTO public.disbursements (
    disbursement_id, allocation_id, commitment_id, milestone_id,
    amount_lakh, payment_reference, recipient_entity, status, approved_by, disbursed_at
) VALUES
(
    'DSB-00000001',
    'ALC-00000001',
    'CMT-00000001',
    'MLS-00000001',
    10.0000,
    'NEFT-BBMP-2025-00101',
    'Bengaluru Urban Drainage & Infra Ltd',
    'completed',
    'FINANCE_SECRETARY',
    NOW() - INTERVAL '19 days'
),
(
    'DSB-00000002',
    'ALC-00000001',
    'CMT-00000001',
    'MLS-00000002',
    15.0000,
    'NEFT-BBMP-2025-00102',
    'Bengaluru Urban Drainage & Infra Ltd',
    'completed',
    'FINANCE_SECRETARY',
    NOW() - INTERVAL '9 days'
)
ON CONFLICT (disbursement_id) DO NOTHING;


-- 6. Genesis Audit Event
INSERT INTO public.audit_events (
    event_id, timestamp, actor_id, actor_role, event_type,
    entity_type, entity_id, summary, previous_state, new_state,
    previous_event_hash, event_hash
) VALUES
(
    'AUD-00000001',
    NOW() - INTERVAL '30 days',
    'MUNICIPAL_COMMISSIONER',
    'administrator',
    'allocation_created',
    'ALLOCATION',
    'ALC-00000001',
    'Demonstration seed genesis allocation authorized.',
    NULL,
    '{"allocated_amount_lakh": 35.0, "status": "in_progress"}'::jsonb,
    'GENESIS',
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
)
ON CONFLICT (event_id) DO NOTHING;
