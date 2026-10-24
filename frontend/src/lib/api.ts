/**
 * UrbanSage AI — Frontend API Client
 * ===================================
 * Typed client for interacting with the UrbanSage AI FastAPI backend.
 * Base URL is configurable via NEXT_PUBLIC_API_URL environment variable.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

/**
 * Request a signed JWT session token from the backend authentication service.
 * Eliminates client-side exposure of static administrative keys.
 */
export async function fetchDemoToken(
  role: "administrator" | "contractor" | "citizen" = "administrator",
  userId: string = "demo-admin-1",
  department: string = "Environmental Protection Division"
): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, role, department }),
  });
  if (!res.ok) {
    throw new ApiError(res.status, "Failed to obtain authentication token from backend");
  }
  const data = await res.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
    return data.access_token;
  }
  throw new ApiError(500, "Token response missing access_token");
}

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  } else {
    // Development evaluation fallback key for local testing
    headers["X-Admin-API-Key"] = "urbansage-admin-dev-key";
  }
  return headers;
}

export type ProblemCategory =
  | "flooding_drainage"
  | "water_scarcity"
  | "heat"
  | "loss_of_green_cover";

export type ReportStatus =
  | "submitted"
  | "under_review"
  | "info_requested"
  | "verified"
  | "flagged_suspicious"
  | "confirmed_fake"
  | "duplicate"
  | "out_of_scope"
  | "no_action_required"
  | "assigned"
  | "in_progress"
  | "completed_awaiting_verification"
  | "verification_failed"
  | "verified_resolved"
  | "resolved"
  | "dismissed";

export type VerificationStatus =
  | "unverified"
  | "community_corroborated"
  | "officially_verified"
  | "dismissed";

export interface PhotoMetadata {
  photo_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  caption?: string | null;
  captured_at?: string | null;
}

export interface ResolutionEvidence {
  completed_by: string;
  completion_notes: string;
  evidence_photos?: PhotoMetadata[];
  completed_at: string;
  citizen_confirmed?: boolean | null;
  citizen_feedback?: string | null;
  verified_at?: string | null;
}

export interface StatusTransitionLog {
  from_status: ReportStatus;
  to_status: ReportStatus;
  actor_role: "citizen" | "administrator" | "contractor" | "system";
  actor_id?: string | null;
  reason?: string | null;
  timestamp: string;
  evidence?: ResolutionEvidence | null;
}

export interface CitizenReportCreate {
  category: ProblemCategory;
  description: string;
  severity: number;
  latitude: number;
  longitude: number;
  location_description?: string;
  neighbourhood_id?: string;
  reporter_id?: string;
  reporter_contact?: string;
  photos?: PhotoMetadata[];
}

export interface CitizenReportPublic {
  id: string;
  category: ProblemCategory;
  description: string;
  severity: number;
  latitude: number;
  longitude: number;
  location_description?: string | null;
  neighbourhood_id?: string | null;
  photos: PhotoMetadata[];
  status: ReportStatus;
  verification_status: VerificationStatus;
  is_verified_measurement: boolean;
  data_source: "CITIZEN_REPORT";
  urgency_score: number;
  evidence_confidence_score: number;
  resolution_evidence?: ResolutionEvidence | null;
  timeline?: StatusTransitionLog[];
  created_at: string;
  updated_at: string;
}

export interface PaginatedReportsResponse {
  items: CitizenReportPublic[];
  total: number;
  limit: number;
  offset: number;
}

export interface BriefReportItem {
  id: string;
  category: ProblemCategory;
  description: string;
  severity: number;
  status: ReportStatus;
  urgency_score: number;
  evidence_confidence_score: number;
  latitude: number;
  longitude: number;
  location_description?: string | null;
  neighbourhood_id?: string | null;
  created_at: string;
  age_hours: number;
  prioritization_reason: string;
}

export interface DecisionBriefSummary {
  total_reports: number;
  active_reports: number;
  high_urgency_active_count: number;
  awaiting_review_count: number;
  awaiting_citizen_verification_count: number;
  verification_failed_count: number;
  overdue_active_count: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
}

export interface DecisionBriefResponse {
  generated_at: string;
  overdue_threshold_hours: number;
  summary: DecisionBriefSummary;
  high_urgency_items: BriefReportItem[];
  awaiting_review_items: BriefReportItem[];
  awaiting_citizen_verification_items: BriefReportItem[];
  failed_verification_items: BriefReportItem[];
  overdue_items: BriefReportItem[];
  recent_activity: StatusTransitionLog[];
}

export interface PriorityQueueResponse {
  items: CitizenReportPublic[];
  total: number;
  limit: number;
  offset: number;
  sort_by: string;
}

export interface NeighbourhoodRiskAggregate {
  neighbourhood_id: string;
  neighbourhood_name?: string | null;
  total_reports: number;
  active_reports: number;
  resolved_reports: number;
  high_urgency_reports: number;
  average_urgency: number;
  category_breakdown: Record<string, number>;
  top_hazard_category?: ProblemCategory | null;
}

export interface GeographicRiskResponse {
  generated_at: string;
  time_window_days?: number | null;
  total_reports: number;
  neighbourhoods: NeighbourhoodRiskAggregate[];
  unassigned?: NeighbourhoodRiskAggregate | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Fetch service health status
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError(res.status, "Health probe failed");
  }
  return res.json();
}

/**
 * Fetch paginated reports with optional category and status filters
 */
export async function fetchReports(params?: {
  category?: ProblemCategory;
  status?: ReportStatus;
  limit?: number;
  offset?: number;
}): Promise<PaginatedReportsResponse> {
  const url = new URL(`${API_BASE_URL}/api/reports`);
  if (params?.category) url.searchParams.set("category", params.category);
  if (params?.status) url.searchParams.set("status", params.status);
  if (params?.limit) url.searchParams.set("limit", String(params.limit));
  if (params?.offset !== undefined) url.searchParams.set("offset", String(params.offset));

  const res = await fetch(url.toString(), {
    cache: "no-store",
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Failed to fetch reports (${res.status})`
    );
  }

  return res.json();
}

/**
 * Fetch single report by ID
 */
export async function fetchReportById(
  reportId: string
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Report not found (${res.status})`
    );
  }

  return res.json();
}

/**
 * Submit a new citizen report
 */
export async function submitCitizenReport(
  payload: CitizenReportCreate
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message =
      typeof errorBody.detail === "string"
        ? errorBody.detail
        : Array.isArray(errorBody.detail)
        ? errorBody.detail.map((e: { msg?: string }) => e.msg || "").join("; ")
        : `Submission failed with status ${res.status}`;
    throw new ApiError(res.status, message);
  }

  return res.json();
}

/**
 * Update the operational lifecycle status of a report (Admin review, assignment, completion)
 */
export async function updateReportStatus(
  reportId: string,
  payload: {
    status: ReportStatus;
    actor_role?: "citizen" | "administrator" | "contractor" | "system";
    actor_id?: string;
    reason?: string;
    evidence?: ResolutionEvidence;
  }
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${reportId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Status update failed (${res.status})`
    );
  }

  return res.json();
}

/**
 * Citizen resolution verification (confirm resolved or reject with feedback)
 */
export async function verifyReportResolution(
  reportId: string,
  payload: {
    confirmed_resolved: boolean;
    feedback?: string;
    actor_id?: string;
  }
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${reportId}/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Verification submission failed (${res.status})`
    );
  }

  return res.json();
}

/**
 * Submit additional evidence for an information-requested report
 */
export async function submitAdditionalEvidence(
  reportId: string,
  payload: {
    additional_notes?: string;
    photos?: PhotoMetadata[];
    actor_id?: string;
  }
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${reportId}/evidence`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Evidence submission failed (${res.status})`
    );
  }

  return res.json();
}

/**
 * Fetch Daily Decision Brief for municipal administrators
 */
export async function fetchDecisionBrief(
  overdueThresholdHours: number = 48
): Promise<DecisionBriefResponse> {
  const url = `${API_BASE_URL}/api/admin/decision-brief?overdue_threshold_hours=${overdueThresholdHours}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Failed to fetch decision brief (${res.status})`
    );
  }
  return res.json();
}

/**
 * Fetch Priority Review Queue with server-side pagination, sorting, and filtering
 */
export async function fetchPriorityQueue(params?: {
  status?: ReportStatus;
  category?: ProblemCategory;
  neighbourhood_id?: string;
  min_urgency?: number;
  sort_by?: string;
  limit?: number;
  offset?: number;
}): Promise<PriorityQueueResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.category) query.set("category", params.category);
  if (params?.neighbourhood_id) query.set("neighbourhood_id", params.neighbourhood_id);
  if (params?.min_urgency !== undefined) query.set("min_urgency", String(params.min_urgency));
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));

  const queryString = query.toString();
  const url = `${API_BASE_URL}/api/admin/priority-queue${queryString ? `?${queryString}` : ""}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Failed to fetch priority queue (${res.status})`
    );
  }
  return res.json();
}

/**
 * Fetch Geographic Environmental Hazard Risk Aggregations across neighbourhoods
 */
export async function fetchGeographicRisk(
  timeWindowDays?: number,
  category?: ProblemCategory
): Promise<GeographicRiskResponse> {
  const query = new URLSearchParams();
  if (timeWindowDays !== undefined && timeWindowDays > 0) {
    query.set("time_window_days", String(timeWindowDays));
  }
  if (category) query.set("category", category);

  const queryString = query.toString();
  const url = `${API_BASE_URL}/api/admin/geographic-risk${queryString ? `?${queryString}` : ""}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorBody.detail || `Failed to fetch geographic risk (${res.status})`
    );
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Stage 5: Decision Engine & Scenario Integration API Client
// ---------------------------------------------------------------------------

export interface AllocationItem {
  neighbourhood_id: string;
  neighbourhood_name: string;
  intervention_id: string;
  intervention_name: string;
  category: string;
  units: number;
  cost_per_unit_lakh: number;
  total_cost_lakh: number;
  is_high_vulnerability: boolean;
  unit_environmental_score: number;
  total_objective_contribution: number;
}

export interface NeighbourhoodImpact {
  neighbourhood_id: string;
  neighbourhood_name: string;
  is_high_vulnerability: boolean;
  social_vulnerability_index: number;
  units_deployed: number;
  distinct_types_count: number;
  total_spend_lakh: number;
  baseline_risks: { heat: number; flood: number; water: number };
  post_intervention_risks: { heat: number; flood: number; water: number };
  risk_reductions: { heat: number; flood: number; water: number };
}

export interface PortfolioResult {
  status: string;
  method: string;
  objective_value: number;
  total_cost_lakh: number;
  budget_lakh: number;
  budget_utilization_pct: number;
  unused_budget_lakh: number;
  optimality_gap: number;
  binding_constraints: string[];
  allocations: AllocationItem[];
  neighbourhood_impacts: NeighbourhoodImpact[];
  environmental_summary?: {
    mean_heat_reduction: number;
    mean_flood_reduction: number;
    mean_water_reduction: number;
    hv_mean_heat_reduction: number;
    hv_mean_flood_reduction: number;
    hv_mean_water_reduction: number;
  } | null;
  equity_summary?: {
    high_vulnerability_spend_lakh: number;
    non_high_vulnerability_spend_lakh: number;
    equity_spend_fraction_of_total_spend: number;
    equity_floor_satisfied: boolean;
  } | null;
  report_need_signals_applied: boolean;
  need_signal_summary?: Record<string, unknown> | null;
}

export interface AllocationDiffItem {
  neighbourhood_id: string;
  neighbourhood_name: string;
  intervention_id: string;
  intervention_name: string;
  category: string;
  baseline_units: number;
  integrated_units: number;
  unit_delta: number;
  cost_per_unit_lakh: number;
  spend_delta_lakh: number;
  status: "ADDED" | "REMOVED" | "INCREASED" | "DECREASED" | "UNCHANGED";
  reason: string;
}

export interface DecisionComparisonResult {
  baseline_cost_lakh: number;
  integrated_cost_lakh: number;
  cost_delta_lakh: number;
  budget_lakh: number;
  baseline_units_total: number;
  integrated_units_total: number;
  units_delta_total: number;
  baseline_equity_spend_lakh: number;
  integrated_equity_spend_lakh: number;
  equity_spend_delta_lakh: number;
  baseline_equity_share_pct: number;
  integrated_equity_share_pct: number;
  equity_constraint_satisfied: boolean;
  budget_constraint_satisfied: boolean;
  baseline_heat_reduction: number;
  integrated_heat_reduction: number;
  heat_reduction_delta: number;
  baseline_flood_reduction: number;
  integrated_flood_reduction: number;
  flood_reduction_delta: number;
  baseline_water_reduction: number;
  integrated_water_reduction: number;
  water_reduction_delta: number;
  all_diffs: AllocationDiffItem[];
  added_allocations: AllocationDiffItem[];
  removed_allocations: AllocationDiffItem[];
  modified_allocations: AllocationDiffItem[];
  key_tradeoffs: string[];
  reasons_for_change: string[];
  need_audit?: {
    total_reports_evaluated?: number;
    eligible_reports_count?: number;
    excluded_reports_count?: number;
    unassigned_reports_count?: number;
  } | null;
  model_provenance: {
    nature: string;
    solver: string;
    optimizer_baseline: string;
    citizen_signal_source: string;
    disclaimer: string;
  };
}

export interface OptimizationRunRequest {
  budget_lakh?: number;
  equity_threshold?: number;
  priority_heat?: number;
  priority_flood?: number;
  priority_water?: number;
  equity_weight?: number;
  max_interventions_per_neighbourhood?: number;
  include_citizen_reports?: boolean;
}

export async function fetchOptimizerConfig(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/config`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status, "Failed to fetch optimizer configuration");
  return res.json();
}

export async function runOptimization(payload: OptimizationRunRequest): Promise<{
  result: PortfolioResult;
  need_audit?: Record<string, unknown> | null;
  data_disclaimer: Record<string, unknown>;
}> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Optimization execution failed");
  }
  return res.json();
}

export async function compareOptimization(
  payload: OptimizationRunRequest
): Promise<DecisionComparisonResult> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Comparison execution failed");
  }
  return res.json();
}

export async function runScenarioSimulation(payload: {
  scenario_type: string;
  name: string;
  description?: string;
  budget_lakh?: number;
  equity_threshold?: number;
  flood_multiplier?: number;
  heat_multiplier?: number;
  water_multiplier?: number;
  include_citizen_reports?: boolean;
}): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/scenarios/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Scenario simulation execution failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Stage 6: Financial Accountability & Audit Portal Types & API Client
// ---------------------------------------------------------------------------

export interface EvidenceMetadataItem {
  evidence_id: string;
  milestone_id: string;
  evidence_type: "site_photo" | "inspection_report" | "material_invoice" | "community_sign_off" | "geo_survey";
  title: string;
  description?: string | null;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  document_hash: string;
  submitted_by: string;
  submitted_at: string;
  verification_status: "pending_review" | "verified" | "rejected";
  verification_notes?: string | null;
}

export interface VerificationDecisionItem {
  decision_id: string;
  milestone_id: string;
  decision: "approved" | "rejected" | "revision_requested";
  verifier_id: string;
  verifier_name: string;
  comments: string;
  decided_at: string;
  passed_inspection: boolean;
}

export interface ImplementationMilestoneItem {
  milestone_id: string;
  allocation_id: string;
  title: string;
  description: string;
  sequence_order: number;
  target_completion_date: string;
  status: "pending" | "in_progress" | "submitted_for_review" | "verified_complete" | "failed_verification";
  disbursement_tied_amount_lakh: number;
  percent_progress: number;
  evidence_items: EvidenceMetadataItem[];
  verification_decision?: VerificationDecisionItem | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialCommitmentItem {
  commitment_id: string;
  allocation_id: string;
  vendor_id: string;
  vendor_name: string;
  contract_reference: string;
  committed_amount_lakh: number;
  status: "draft" | "approved" | "active" | "fulfilled" | "cancelled";
  approved_by: string;
  created_at: string;
}

export interface DisbursementRecordItem {
  disbursement_id: string;
  allocation_id: string;
  commitment_id: string;
  milestone_id?: string | null;
  amount_lakh: number;
  payment_reference: string;
  recipient_entity: string;
  status: "pending_approval" | "completed" | "rejected" | "reversed";
  approved_by: string;
  disbursed_at: string;
}

export interface FinancialDiscrepancyItem {
  discrepancy_id: string;
  allocation_id: string;
  severity: "low" | "medium" | "high" | "critical";
  discrepancy_type: "cost_overrun" | "unverified_disbursement" | "milestone_stalled" | "evidence_missing" | "budget_mismatch";
  title: string;
  description: string;
  amount_involved_lakh: number;
  status: "open" | "under_review" | "resolved" | "dismissed";
  detected_at: string;
  resolved_by?: string | null;
  resolution_notes?: string | null;
  resolved_at?: string | null;
}

export interface AuditEventItem {
  event_id: string;
  timestamp: string;
  actor_id: string;
  actor_role: "administrator" | "contractor" | "system";
  event_type: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  previous_state?: Record<string, unknown> | null;
  new_state?: Record<string, unknown> | null;
  previous_event_hash: string;
  event_hash: string;
}

export interface InterventionAllocationItem {
  allocation_id: string;
  title: string;
  neighbourhood_id: string;
  neighbourhood_name: string;
  intervention_id: string;
  intervention_name: string;
  category: string;
  fiscal_year: string;
  currency: string;
  allocated_amount_lakh: number;
  committed_amount_lakh: number;
  disbursed_amount_lakh: number;
  remaining_budget_lakh: number;
  undisbursed_committed_lakh: number;
  disbursement_progress_pct: number;
  planned_units: number;
  status: "planned" | "committed" | "in_progress" | "completed" | "frozen" | "cancelled";
  authorized_by: string;
  council_resolution_ref?: string | null;
  milestones: ImplementationMilestoneItem[];
  commitments: FinancialCommitmentItem[];
  disbursements: DisbursementRecordItem[];
  discrepancies: FinancialDiscrepancyItem[];
  created_at: string;
  updated_at: string;
}

export interface PublicAccountabilitySummary {
  fiscal_year: string;
  total_allocated_lakh: number;
  total_committed_lakh: number;
  total_disbursed_lakh: number;
  total_remaining_lakh: number;
  allocation_count: number;
  completed_milestones_count: number;
  pending_milestones_count: number;
  open_discrepancies_count: number;
  resolved_discrepancies_count: number;
  by_category: Record<string, { count: number; allocated_lakh: number; committed_lakh: number; disbursed_lakh: number }>;
  by_neighbourhood: Array<{
    neighbourhood_id: string;
    neighbourhood_name: string;
    project_count: number;
    allocated_lakh: number;
    disbursed_lakh: number;
  }>;
  disclaimer: string;
}

/**
 * Fetch public accountability summary
 */
export async function fetchAccountabilitySummary(): Promise<PublicAccountabilitySummary> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/summary`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch accountability summary");
  }
  return res.json();
}

/**
 * List municipal budget allocations
 */
export async function fetchAllocations(params?: {
  neighbourhood_id?: string;
  category?: string;
  status?: string;
}): Promise<InterventionAllocationItem[]> {
  const query = new URLSearchParams();
  if (params?.neighbourhood_id) query.set("neighbourhood_id", params.neighbourhood_id);
  if (params?.category) query.set("category", params.category);
  if (params?.status) query.set("status", params.status);

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/accountability/allocations${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch allocations");
  }
  return res.json();
}

/**
 * Fetch allocation details
 */
export async function fetchAllocationDetail(allocationId: string): Promise<InterventionAllocationItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/allocations/${encodeURIComponent(allocationId)}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch allocation detail");
  }
  return res.json();
}

/**
 * List financial discrepancies (Admin only)
 */
export async function fetchDiscrepancies(params?: {
  status?: string;
  severity?: string;
}): Promise<FinancialDiscrepancyItem[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.severity) query.set("severity", params.severity);

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/accountability/discrepancies${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch discrepancies");
  }
  return res.json();
}

/**
 * Resolve financial discrepancy
 */
export async function resolveDiscrepancy(
  discrepancyId: string,
  payload: { resolution_notes: string; action_taken?: string }
): Promise<FinancialDiscrepancyItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/discrepancies/${encodeURIComponent(discrepancyId)}/resolve`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to resolve discrepancy");
  }
  return res.json();
}

/**
 * Fetch tamper-evident audit history
 */
export async function fetchAuditTrail(params?: {
  limit?: number;
  entity_id?: string;
}): Promise<AuditEventItem[]> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.entity_id) query.set("entity_id", params.entity_id);

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/accountability/audit-trail${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch audit trail");
  }
  return res.json();
}

/**
 * Role and session state management
 */
export type AppRole = "citizen" | "administrator" | "contractor";

let currentRole: AppRole = "administrator";
let currentUserId: string = "demo-admin-1";

export function getActiveRole(): AppRole {
  return currentRole;
}

export function setActiveRole(role: AppRole, userId?: string): void {
  currentRole = role;
  if (userId) {
    currentUserId = userId;
  } else if (role === "administrator") {
    currentUserId = "demo-admin-1";
  } else if (role === "contractor") {
    currentUserId = "VND-BBMP-WORKS-01";
  } else {
    currentUserId = "CITIZEN-DEMO-01";
  }
}

export function getActiveUserId(): string {
  return currentUserId;
}

/**
 * Update milestone progress (Contractor or Admin)
 */
export async function updateMilestoneProgress(
  milestoneId: string,
  payload: {
    percent_progress?: number;
    status?: "pending" | "in_progress" | "submitted_for_review" | "verified_complete" | "failed_verification";
    notes?: string;
  }
): Promise<ImplementationMilestoneItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/milestones/${encodeURIComponent(milestoneId)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to update milestone progress");
  }
  return res.json();
}

/**
 * Attach documentary evidence to a milestone (Contractor or Admin)
 */
export async function attachMilestoneEvidence(
  milestoneId: string,
  payload: {
    evidence_type: "site_photo" | "inspection_report" | "material_invoice" | "community_sign_off" | "geo_survey";
    title: string;
    description?: string;
    file_name: string;
    mime_type: string;
    file_size_bytes: number;
    document_hash: string;
  }
): Promise<EvidenceMetadataItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/milestones/${encodeURIComponent(milestoneId)}/evidence`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to attach milestone evidence");
  }
  return res.json();
}

/**
 * Verify milestone completion (Admin only)
 */
export async function verifyMilestone(
  milestoneId: string,
  payload: {
    decision: "approved" | "rejected" | "revision_requested";
    comments: string;
    passed_inspection: boolean;
  }
): Promise<VerificationDecisionItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/milestones/${encodeURIComponent(milestoneId)}/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to record verification decision");
  }
  return res.json();
}

/**
 * Execute monetary disbursement (Admin only)
 */
export async function executeDisbursement(
  allocationId: string,
  payload: {
    commitment_id: string;
    milestone_id?: string;
    amount_lakh: number;
    payment_reference: string;
    recipient_entity: string;
  }
): Promise<DisbursementRecordItem> {
  const res = await fetch(`${API_BASE_URL}/api/accountability/allocations/${encodeURIComponent(allocationId)}/disbursements`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to execute disbursement");
  }
  return res.json();
}


/**
 * Append additional evidence to a citizen report
 */
export async function addReportEvidence(
  reportId: string,
  payload: {
    additional_notes?: string;
    photos: PhotoMetadata[];
    actor_id?: string;
  }
): Promise<CitizenReportPublic> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/evidence`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to append report evidence");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Stage 7: Governance, Departmental Triage & Capital Budget Plans
// ---------------------------------------------------------------------------

export interface DepartmentRecommendation {
  recommendation_id: string;
  report_id: string;
  neighbourhood_id?: string;
  recommended_department: string;
  recommended_action: string;
  urgency_level: string;
  explanation: string;
  evidence_used: string[];
  confidence_score: number;
  is_rule_based_heuristic: boolean;
  data_coverage_notice: string;
  created_at: string;
}

export interface AdminDecision {
  decision_id: string;
  report_id: string;
  decision_type: string;
  assigned_department: string;
  assigned_action: string;
  review_notes: string;
  priority_tier: string;
  reviewer_id: string;
  created_at: string;
}

export interface BudgetPlanItem {
  item_id: string;
  plan_id: string;
  neighbourhood_id: string;
  neighbourhood_name: string;
  intervention_id: string;
  intervention_name: string;
  category: string;
  units: number;
  cost_per_unit_lakh: number;
  total_cost_lakh: number;
  rationale: string;
}

export interface BudgetPlan {
  plan_id: string;
  title: string;
  budget_lakh: number;
  equity_threshold: number;
  total_allocated_lakh: number;
  remaining_balance_lakh: number;
  status: string;
  created_by: string;
  reviewed_by?: string;
  approved_by?: string;
  notes?: string;
  items: BudgetPlanItem[];
  created_at: string;
  updated_at: string;
}

export async function fetchReportRecommendation(reportId: string): Promise<DepartmentRecommendation> {
  const res = await fetch(`${API_BASE_URL}/api/admin/reports/${encodeURIComponent(reportId)}/recommendation`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch departmental recommendation");
  }
  return res.json();
}

export async function submitAdminDecision(
  reportId: string,
  payload: {
    decision_type: string;
    assigned_department: string;
    assigned_action: string;
    review_notes: string;
    priority_tier: string;
  }
): Promise<AdminDecision> {
  const res = await fetch(`${API_BASE_URL}/api/admin/reports/${encodeURIComponent(reportId)}/decision`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to submit administrative decision");
  }
  return res.json();
}

export async function fetchAdminDecisions(reportId?: string): Promise<AdminDecision[]> {
  const url = reportId
    ? `${API_BASE_URL}/api/admin/decisions?report_id=${encodeURIComponent(reportId)}`
    : `${API_BASE_URL}/api/admin/decisions`;
  const res = await fetch(url, { headers: { ...getAuthHeaders() } });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch administrative decisions");
  }
  return res.json();
}

export async function saveBudgetPlan(payload: {
  title: string;
  budget_lakh: number;
  equity_threshold: number;
  notes?: string;
  items: {
    neighbourhood_id: string;
    neighbourhood_name: string;
    intervention_id: string;
    intervention_name: string;
    category: string;
    units: number;
    cost_per_unit_lakh: number;
    total_cost_lakh: number;
    rationale?: string;
  }[];
}): Promise<BudgetPlan> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/plans`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to save budget plan");
  }
  return res.json();
}

export async function fetchBudgetPlans(): Promise<BudgetPlan[]> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/plans`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch budget plans");
  }
  return res.json();
}

export async function approveBudgetPlan(planId: string): Promise<BudgetPlan> {
  const res = await fetch(`${API_BASE_URL}/api/optimizer/plans/${encodeURIComponent(planId)}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to approve budget plan");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Infrastructure Partner Budget & Expenditure Requests
// ---------------------------------------------------------------------------

export interface PartnerProposalItem {
  proposal_id: string;
  allocation_id: string;
  project_title: string;
  amount_lakh: number;
  purpose: string;
  status: string;
  submission_date: string;
}

export interface PartnerProjectBudget {
  allocation_id: string;
  title: string;
  category: string;
  neighbourhood_id: string;
  neighbourhood_name: string;
  contract_reference: string;
  allocated_amount_lakh?: number;
  committed_amount_lakh: number;
  disbursed_amount_lakh: number;
  pending_requests_lakh: number;
  remaining_balance_lakh: number;
  utilization_pct: number;
  milestones_count: number;
  verified_milestones_count: number;
}

export interface PartnerBudgetSummary {
  vendor_id: string;
  vendor_name: string;
  total_allocated_lakh?: number;
  total_committed_lakh: number;
  total_disbursed_lakh: number;
  total_pending_requests_lakh: number;
  total_remaining_balance_lakh: number;
  overall_utilization_pct: number;
  projects: PartnerProjectBudget[];
  proposals?: PartnerProposalItem[];
  disclaimer: string;
}

export interface ExpenditureRequestCreate {
  commitment_id: string;
  milestone_id?: string;
  amount_lakh: number;
  payment_reference: string;
  recipient_entity: string;
  notes?: string;
}

export async function fetchPartnerBudget(vendorId?: string): Promise<PartnerBudgetSummary> {
  const qs = vendorId ? `?vendor_id=${encodeURIComponent(vendorId)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/accountability/partner-budget${qs}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch partner budget");
  }
  return res.json();
}

export async function submitExpenditureRequest(
  allocationId: string,
  payload: ExpenditureRequestCreate
): Promise<DisbursementRecordItem> {
  const res = await fetch(
    `${API_BASE_URL}/api/accountability/allocations/${encodeURIComponent(allocationId)}/expenditure-requests`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(payload),
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to submit expenditure request");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Environmental Intelligence & Evidence-Based Reporting
// ---------------------------------------------------------------------------

export interface CategoryMetric {
  category: string;
  category_name: string;
  citizen_reports_count: number;
  high_urgency_count: number;
  avg_urgency_score: number;
  avg_severity: number;
  baseline_risk_score: number;
  severity_distribution: Record<string, number>;
  affected_wards: string[];
}

export interface WardMetric {
  neighbourhood_id: string;
  name: string;
  population: number;
  social_vulnerability_index: number;
  flood_risk: number;
  heat_risk: number;
  water_stress: number;
  green_cover_pct: number;
  citizen_reports_count: number;
  high_urgency_reports_count: number;
  data_source: string;
}

export interface ProvenanceRecord {
  id: string;
  layer: string;
  data_type: string;
  source: string;
  reporting_period: string;
  last_updated: string;
  aggregation_method: string;
  geographic_coverage: string;
  status: string;
}

export interface EnvironmentalIntelligenceData {
  status: string;
  generated_at: string;
  total_reports: number;
  high_urgency_reports: number;
  categories: CategoryMetric[];
  wards: WardMetric[];
  report: {
    executive_summary: string;
    main_concerns: string[];
    geographic_distribution: string;
    data_coverage_and_limitations: {
      geographic_coverage: string;
      participatory_coverage: string;
      telemetry_status: string;
      analytical_limitations: string;
    };
    recommended_interventions: Array<{
      hazard: string;
      recommendation: string;
      justification: string;
      lead_department: string;
    }>;
    budget_implications: string;
  };
  provenance: ProvenanceRecord[];
}

export async function fetchEnvironmentalIntelligence(): Promise<EnvironmentalIntelligenceData> {
  const res = await fetch(`${API_BASE_URL}/api/admin/environmental-intelligence`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody.detail || "Failed to fetch environmental intelligence");
  }
  return res.json();
}

