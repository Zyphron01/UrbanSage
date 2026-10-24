"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AlertCircle,
  Building2,
  Camera,
  CheckCircle2,
  Compass,
  FileCheck2,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  AdminDecision,
  CitizenReportPublic,
  DepartmentRecommendation,
  fetchAdminDecisions,
  fetchReportRecommendation,
  submitAdminDecision,
} from "@/lib/api";

interface ReportDetailModalProps {
  report: CitizenReportPublic | null;
  onClose: () => void;
  onDecisionSubmitted?: () => void;
}

export function ReportDetailModal({ report, onClose, onDecisionSubmitted }: ReportDetailModalProps) {
  const [recommendation, setRecommendation] = useState<DepartmentRecommendation | null>(null);
  const [loadingRec, setLoadingRec] = useState<boolean>(false);
  const [recError, setRecError] = useState<string | null>(null);

  const [decisions, setDecisions] = useState<AdminDecision[]>([]);
  const [loadingDecisions, setLoadingDecisions] = useState<boolean>(false);

  // Form State
  const [decisionType, setDecisionType] = useState<string>("ASSIGN_DEPARTMENT");
  const [assignedDept, setAssignedDept] = useState<string>("");
  const [assignedAction, setAssignedAction] = useState<string>("");
  const [priorityTier, setPriorityTier] = useState<string>("P1_URGENT");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadRecommendationAndDecisions = useCallback(async (reportId: string) => {
    setLoadingRec(true);
    setRecError(null);
    setLoadingDecisions(true);

    try {
      const rec = await fetchReportRecommendation(reportId);
      setRecommendation(rec);
      setAssignedDept(rec.recommended_department);
      setAssignedAction(rec.recommended_action);
      if (rec.urgency_level === "CRITICAL") setPriorityTier("P1_URGENT");
      else if (rec.urgency_level === "HIGH") setPriorityTier("P2_STANDARD");
      else setPriorityTier("P3_DEFERRED");
    } catch (err: unknown) {
      setRecError(err instanceof Error ? err.message : "Failed to load recommendation");
    } finally {
      setLoadingRec(false);
    }

    try {
      const decs = await fetchAdminDecisions(reportId);
      setDecisions(decs);
    } catch {
      // Non-fatal
    } finally {
      setLoadingDecisions(false);
    }
  }, []);

  useEffect(() => {
    if (report?.id) {
      loadRecommendationAndDecisions(report.id);
    } else {
      setRecommendation(null);
      setDecisions([]);
      setSubmitSuccess(null);
      setSubmitError(null);
    }
  }, [report?.id, loadRecommendationAndDecisions]);

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!report?.id || !assignedDept.trim() || !assignedAction.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const decision = await submitAdminDecision(report.id, {
        decision_type: decisionType,
        assigned_department: assignedDept.trim(),
        assigned_action: assignedAction.trim(),
        review_notes: reviewNotes.trim() || "Administrative triage decision recorded.",
        priority_tier: priorityTier,
      });

      setSubmitSuccess(`Decision recorded and persisted in Supabase: Assigned to ${decision.assigned_department}.`);
      setDecisions((prev) => [decision, ...prev]);
      setReviewNotes("");
      if (onDecisionSubmitted) {
        onDecisionSubmitted();
      }
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit administrative decision");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!report) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-xl p-6 my-8 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="font-mono text-sm font-bold text-teal-700 bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
              {report.id}
            </div>
            <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
              Citizen Report & Administrative Triage
            </span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="py-4 space-y-4">
          {/* Provenance Notice */}
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-[11px] text-amber-900 flex items-start space-x-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong>Provenance Notice:</strong> This report is persisted in <strong>Supabase PostgreSQL</strong>.
              Departmental triage recommendations are computed using transparent, explainable <strong>rule-based heuristics</strong> grounded in Bangalore municipal ward hazard indices.
            </div>
          </div>

          {/* Description & Core Metrics */}
          <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase font-bold text-slate-500">
                Observation Claim &bull; Severity {report.severity}/5
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono bg-teal-50 text-teal-800 border border-teal-200">
                {report.status}
              </span>
            </div>
            <p className="text-xs text-slate-800 leading-relaxed font-medium">
              {report.description}
            </p>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold">Ward / Neighbourhood</span>
                <div className="font-semibold text-slate-900">{report.neighbourhood_id || "Unlinked Area"}</div>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold">Urgency Score</span>
                <div className="font-mono font-bold text-rose-700">{report.urgency_score.toFixed(1)} / 100</div>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold">Evidence Score</span>
                <div className="font-mono font-bold text-teal-700">{report.evidence_confidence_score.toFixed(1)} / 100</div>
              </div>
            </div>
          </div>

          {/* Departmental Triage Recommendation */}
          <div className="rounded-xl bg-white border border-teal-200 p-4 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-teal-700" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Recommended Department & Action
                </h3>
              </div>
              <span className="rounded-full bg-teal-50 text-teal-800 border border-teal-200 px-2 py-0.5 text-[10px] font-mono font-bold">
                Rule-Based Ground Truth
              </span>
            </div>

            {loadingRec ? (
              <div className="py-4 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-600" />
                <span>Evaluating ward telemetry & departmental routing rules...</span>
              </div>
            ) : recError ? (
              <div className="text-xs text-rose-700 bg-rose-50 p-2.5 rounded border border-rose-200 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{recError}</span>
              </div>
            ) : recommendation ? (
              <div className="space-y-2.5 text-xs">
                <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 text-[10px] uppercase font-bold">Target Department</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                      recommendation.urgency_level === "CRITICAL" ? "bg-rose-50 text-rose-800 border-rose-200" :
                      recommendation.urgency_level === "HIGH" ? "bg-amber-50 text-amber-800 border-amber-200" :
                      "bg-slate-100 text-slate-700 border-slate-200"
                    }`}>
                      Urgency: {recommendation.urgency_level}
                    </span>
                  </div>
                  <div className="font-bold text-slate-900 text-sm">
                    {recommendation.recommended_department}
                  </div>
                  <div className="text-teal-800 font-medium">
                    Action: {recommendation.recommended_action}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Reasoning & Evidence Grounding</span>
                  <p className="text-slate-700 text-xs leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-100">
                    {recommendation.explanation}
                  </p>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                    {recommendation.evidence_used.map((ev, i) => (
                      <li key={i} className="rounded bg-teal-50/60 border border-teal-100 px-2.5 py-1 text-[11px] text-teal-900 flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0" />
                        <span>{ev}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>

          {/* Administrative Decision Recording Form */}
          <form onSubmit={handleDecisionSubmit} className="rounded-xl bg-white border border-slate-200 p-4 space-y-3 shadow-xs">
            <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
              <FileCheck2 className="w-4 h-4 text-emerald-600" />
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Record Administrative Decision & Assignment
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-600">Decision Type</label>
                <select
                  value={decisionType}
                  onChange={(e) => setDecisionType(e.target.value)}
                  className="w-full rounded-lg bg-white border border-slate-300 p-2 text-slate-900 focus:outline-none focus:border-emerald-500"
                >
                  <option value="ASSIGN_DEPARTMENT">Assign Department & Dispatch</option>
                  <option value="SCHEDULE_WORK">Schedule Capital Work</option>
                  <option value="REQUEST_INFO">Request Additional Citizen Info</option>
                  <option value="DISMISS">Dismiss as Out of Scope</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-600">Priority Tier</label>
                <select
                  value={priorityTier}
                  onChange={(e) => setPriorityTier(e.target.value)}
                  className="w-full rounded-lg bg-white border border-slate-300 p-2 text-slate-900 focus:outline-none focus:border-emerald-500"
                >
                  <option value="P1_URGENT">P1 — Urgent / Choke Point</option>
                  <option value="P2_STANDARD">P2 — Standard Remediation</option>
                  <option value="P3_DEFERRED">P3 — Deferred / Monitoring</option>
                </select>
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Assigned Department</label>
                <input
                  type="text"
                  value={assignedDept}
                  onChange={(e) => setAssignedDept(e.target.value)}
                  required
                  placeholder="e.g. BBMP Stormwater Drainage & Lakes Department (SWD)"
                  className="w-full rounded-lg bg-white border border-slate-300 p-2 text-slate-900 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Assigned Action</label>
                <input
                  type="text"
                  value={assignedAction}
                  onChange={(e) => setAssignedAction(e.target.value)}
                  required
                  placeholder="e.g. Emergency Desilting & Sump Bypass Deployment"
                  className="w-full rounded-lg bg-white border border-slate-300 p-2 text-slate-900 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Review Notes & Reasoning</label>
                <textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  rows={2}
                  placeholder="Add administrative review rationale for the permanent municipal audit ledger..."
                  className="w-full rounded-lg bg-white border border-slate-300 p-2 text-slate-900 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            {submitSuccess && (
              <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{submitSuccess}</span>
              </div>
            )}

            {submitError && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !assignedDept.trim()}
              className="inline-flex items-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
            >
              {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              <span>{isSubmitting ? "Persisting in Supabase..." : "Persist Decision & Assign Department"}</span>
            </button>
          </form>

          {/* Decision History (Audit Trail) */}
          {decisions.length > 0 && (
            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-2.5">
              <span className="text-[10px] font-mono uppercase font-bold text-slate-500">
                Persisted Decision History ({decisions.length})
              </span>
              <div className="space-y-2">
                {decisions.map((dec) => (
                  <div key={dec.decision_id} className="rounded-lg bg-white p-3 border border-slate-200 text-xs space-y-1 shadow-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-teal-700 font-bold">{dec.decision_id}</span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {new Date(dec.created_at).toLocaleDateString()} {new Date(dec.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-900">{dec.assigned_department}</div>
                    <div className="text-slate-600 text-[11px]">{dec.assigned_action}</div>
                    {dec.review_notes && (
                      <div className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-100">
                        &quot;{dec.review_notes}&quot;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-3 border-t border-slate-100">
          <button
            onClick={onClose}
            className="rounded-lg bg-white hover:bg-slate-50 border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
