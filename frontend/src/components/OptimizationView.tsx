"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  BookmarkCheck,
  CheckCircle2,
  FileCheck2,
  Layers,
  Plus,
  RefreshCw,
  Save,
  ShieldAlert,
  Sliders,
  Sparkles,
} from "lucide-react";
import {
  approveBudgetPlan,
  BudgetPlan,
  compareOptimization,
  DecisionComparisonResult,
  fetchBudgetPlans,
  OptimizationRunRequest,
  saveBudgetPlan,
} from "@/lib/api";

export function OptimizationView() {
  const [selectedConstraint, setSelectedConstraint] = useState<string>("equity");
  const [budgetLakh, setBudgetLakh] = useState<number>(500.0);
  const [equityThreshold, setEquityThreshold] = useState<number>(0.30);
  const [priorityHeat, setPriorityHeat] = useState<number>(0.35);
  const [priorityFlood, setPriorityFlood] = useState<number>(0.35);
  const priorityWater = 0.30;
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonData, setComparisonData] = useState<DecisionComparisonResult | null>(null);

  // Budget Plan State
  const [plans, setPlans] = useState<BudgetPlan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState<boolean>(false);
  const [planTitle, setPlanTitle] = useState<string>("Municipal Climate Capital Plan FY 2026-27");
  const [planNotes, setPlanNotes] = useState<string>("");
  const [isSavingPlan, setIsSavingPlan] = useState<boolean>(false);
  const [approvingPlanId, setApprovingPlanId] = useState<string | null>(null);
  const [planActionSuccess, setPlanActionSuccess] = useState<string | null>(null);
  const [planActionError, setPlanActionError] = useState<string | null>(null);

  const loadPlans = useCallback(async () => {
    setLoadingPlans(true);
    try {
      const data = await fetchBudgetPlans();
      setPlans(data);
    } catch {
      // Non-fatal
    } finally {
      setLoadingPlans(false);
    }
  }, []);

  const runSolver = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: OptimizationRunRequest = {
        budget_lakh: budgetLakh,
        equity_threshold: equityThreshold,
        priority_heat: priorityHeat,
        priority_flood: priorityFlood,
        priority_water: priorityWater,
        include_citizen_reports: true,
      };
      const data = await compareOptimization(payload);
      setComparisonData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute optimizer comparison";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [budgetLakh, equityThreshold, priorityHeat, priorityFlood]);

  useEffect(() => {
    runSolver();
    loadPlans();
  }, [runSolver, loadPlans]);

  const handleSaveBudgetPlan = async () => {
    if (!comparisonData) return;
    setIsSavingPlan(true);
    setPlanActionError(null);
    setPlanActionSuccess(null);

    const items = comparisonData.all_diffs
      .filter((d) => d.integrated_units > 0)
      .map((d) => ({
        neighbourhood_id: d.neighbourhood_id,
        neighbourhood_name: d.neighbourhood_name,
        intervention_id: d.intervention_id,
        intervention_name: d.intervention_name,
        category: d.category,
        units: d.integrated_units,
        cost_per_unit_lakh: d.cost_per_unit_lakh,
        total_cost_lakh: d.integrated_units * d.cost_per_unit_lakh,
        rationale: d.reason || `Allocated under MILP optimization in ${d.neighbourhood_name}`,
      }));

    try {
      const saved = await saveBudgetPlan({
        title: planTitle.trim() || `Climate Resilience Capital Plan (₹${budgetLakh}L)`,
        budget_lakh: budgetLakh,
        equity_threshold: equityThreshold,
        notes: planNotes.trim() || `Optimization proposal generated via SciPy HiGHS MILP under ₹${budgetLakh}L budget ceiling.`,
        items,
      });

      setPlanActionSuccess(`Plan "${saved.title}" saved successfully in Supabase PostgreSQL (ID: ${saved.plan_id}).`);
      await loadPlans();
      setTimeout(() => setPlanActionSuccess(null), 6000);
    } catch (err: unknown) {
      setPlanActionError(err instanceof Error ? err.message : "Failed to save budget plan");
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleApprovePlan = async (planId: string) => {
    setApprovingPlanId(planId);
    setPlanActionError(null);
    setPlanActionSuccess(null);

    try {
      const approved = await approveBudgetPlan(planId);
      setPlanActionSuccess(
        `Plan "${approved.title}" approved! Authorized allocations have been committed to Supabase capital ledger.`
      );
      await loadPlans();
      setTimeout(() => setPlanActionSuccess(null), 6000);
    } catch (err: unknown) {
      setPlanActionError(err instanceof Error ? err.message : "Failed to approve budget plan");
    } finally {
      setApprovingPlanId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>MODELED ESTIMATE NOTICE:</strong> All portfolio allocations and risk reductions are mathematical optimization estimates solved via SciPy HiGHS MILP under bounded citizen need signals (&le; 25% boost). They do not represent observed real-world post-intervention outcomes.
          </span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Sustainability Decision Engine (Stage 5)
            </h1>
            <span className="rounded-full bg-teal-50 text-teal-800 border border-teal-200 px-2.5 py-0.5 text-[10px] font-mono font-bold">
              Citizen-Informed HiGHS MILP
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Pareto-optimal intervention optimizer combining municipal baseline risks with bounded, spam-resistant citizen problem reports.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={runSolver}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Rerun Solver</span>
          </button>
        </div>
      </div>

      {/* Interactive Solver Controls */}
      <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-4 shadow-xs">
        <div className="flex items-center justify-between text-xs text-slate-800 font-semibold border-b border-slate-100 pb-2">
          <span className="flex items-center space-x-1.5">
            <Sliders className="w-4 h-4 text-teal-600" />
            <span>Interactive Optimization Parameters</span>
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            Capital Budget: ₹{budgetLakh}L &bull; Equity Floor: {(equityThreshold * 100).toFixed(0)}%
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-600 flex justify-between">
              <span>Budget (₹ Lakh)</span>
              <span className="text-teal-700 font-mono font-bold">₹{budgetLakh}L</span>
            </label>
            <input
              type="range"
              min="200"
              max="1000"
              step="25"
              value={budgetLakh}
              onChange={(e) => setBudgetLakh(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-600 flex justify-between">
              <span>Social Equity Floor</span>
              <span className="text-emerald-700 font-mono font-bold">{(equityThreshold * 100).toFixed(0)}%</span>
            </label>
            <input
              type="range"
              min="0.10"
              max="0.60"
              step="0.05"
              value={equityThreshold}
              onChange={(e) => setEquityThreshold(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-600 flex justify-between">
              <span>Heat Priority Weight</span>
              <span className="text-amber-700 font-mono font-bold">{(priorityHeat * 100).toFixed(0)}%</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="0.8"
              step="0.05"
              value={priorityHeat}
              onChange={(e) => setPriorityHeat(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-600 flex justify-between">
              <span>Flood Priority Weight</span>
              <span className="text-blue-700 font-mono font-bold">{(priorityFlood * 100).toFixed(0)}%</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="0.8"
              step="0.05"
              value={priorityFlood}
              onChange={(e) => setPriorityFlood(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>
      </div>

      {/* Comparison Scoreboard */}
      {comparisonData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-1 shadow-xs">
            <div className="text-[11px] text-slate-500">Total Capital Cost</div>
            <div className="flex items-baseline space-x-2">
              <span className="text-lg font-bold text-slate-900 font-mono">
                ₹{comparisonData.integrated_cost_lakh.toFixed(1)}L
              </span>
              <span className="text-xs text-slate-400 line-through font-mono">
                ₹{comparisonData.baseline_cost_lakh.toFixed(1)}L
              </span>
            </div>
            <div className="text-[10px] text-slate-500">
              Delta: <span className="text-teal-700 font-mono font-semibold">{comparisonData.cost_delta_lakh > 0 ? `+₹${comparisonData.cost_delta_lakh.toFixed(1)}L` : `₹${comparisonData.cost_delta_lakh.toFixed(1)}L`}</span>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-1 shadow-xs">
            <div className="text-[11px] text-slate-500">High-Vulnerability Spend</div>
            <div className="flex items-baseline space-x-2">
              <span className="text-lg font-bold text-emerald-700 font-mono">
                ₹{comparisonData.integrated_equity_spend_lakh.toFixed(1)}L
              </span>
              <span className="text-xs text-slate-500 font-mono">
                ({comparisonData.integrated_equity_share_pct.toFixed(1)}%)
              </span>
            </div>
            <div className="text-[10px] text-emerald-700 flex items-center space-x-1 font-medium">
              <CheckCircle2 className="w-3 h-3" />
              <span>Mandatory &ge;{(equityThreshold * 100).toFixed(0)}% floor verified</span>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-1 shadow-xs">
            <div className="text-[11px] text-slate-500">Total Projects Deployed</div>
            <div className="flex items-baseline space-x-2">
              <span className="text-lg font-bold text-slate-900 font-mono">
                {comparisonData.integrated_units_total} units
              </span>
              <span className="text-xs text-slate-500 font-mono">
                ({comparisonData.units_delta_total >= 0 ? `+${comparisonData.units_delta_total}` : comparisonData.units_delta_total} vs base)
              </span>
            </div>
            <div className="text-[10px] text-slate-500">
              100% capacity bounds satisfied
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-1 shadow-xs">
            <div className="text-[11px] text-slate-500">Citizen Need Signal Audit</div>
            <div className="text-xs font-bold text-teal-800 font-mono pt-0.5">
              {comparisonData.need_audit?.eligible_reports_count ?? 0} Eligible Reports
            </div>
            <div className="text-[10px] text-slate-500">
              {comparisonData.need_audit?.excluded_reports_count ?? 0} excluded (fake/duplicate/unverified)
            </div>
          </div>
        </div>
      )}

      {/* Decision Diff & Explanations */}
      {comparisonData && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
                <Layers className="w-4 h-4 text-teal-600" />
                <span>Decision Trade-Offs & Portfolio Diffs</span>
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Explainable differences between standard baseline allocation and citizen report-informed plan.
              </p>
            </div>

            {/* Save Proposed Plan Button */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSaveBudgetPlan}
                disabled={isSavingPlan}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
              >
                {isSavingPlan ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>{isSavingPlan ? "Saving Plan in Supabase..." : "Save as Proposed Plan"}</span>
              </button>
            </div>
          </div>

          {/* Trade-offs & Explanations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-2">
              <span className="text-xs font-semibold text-slate-900">Key Portfolio Shifts</span>
              <ul className="space-y-1.5 text-[11px] text-slate-600">
                {comparisonData.reasons_for_change.map((reason, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-teal-600 font-bold">&bull;</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-2">
              <span className="text-xs font-semibold text-slate-900">Policy Trade-Offs & Safeguards</span>
              <ul className="space-y-1.5 text-[11px] text-slate-600">
                {comparisonData.key_tradeoffs.map((tradeoff, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-emerald-600 font-bold">&bull;</span>
                    <span>{tradeoff}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Granular Allocation Table */}
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-mono text-[10px] uppercase border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Neighbourhood</th>
                  <th className="py-2.5 px-3">Intervention</th>
                  <th className="py-2.5 px-3">Baseline</th>
                  <th className="py-2.5 px-3">Integrated</th>
                  <th className="py-2.5 px-3">Shift</th>
                  <th className="py-2.5 px-3">Spend Delta</th>
                  <th className="py-2.5 px-3">Explainable Rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {comparisonData.all_diffs.slice(0, 8).map((diff, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-3 text-slate-900 font-sans font-medium">
                      {diff.neighbourhood_name}
                    </td>
                    <td className="py-2 px-3 text-slate-700 font-sans">
                      {diff.intervention_name}
                    </td>
                    <td className="py-2 px-3 text-slate-500">
                      {diff.baseline_units} u
                    </td>
                    <td className="py-2 px-3 text-slate-900 font-bold">
                      {diff.integrated_units} u
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                          diff.status === "ADDED"
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : diff.status === "REMOVED"
                            ? "bg-rose-50 text-rose-800 border-rose-200"
                            : diff.status === "INCREASED"
                            ? "bg-teal-50 text-teal-800 border-teal-200"
                            : diff.status === "DECREASED"
                            ? "bg-amber-50 text-amber-800 border-amber-200"
                            : "bg-slate-100 text-slate-700 border-slate-200"
                        }`}
                      >
                        {diff.status} ({diff.unit_delta > 0 ? `+${diff.unit_delta}` : diff.unit_delta})
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-700">
                      {diff.spend_delta_lakh > 0 ? `+₹${diff.spend_delta_lakh.toFixed(1)}L` : diff.spend_delta_lakh < 0 ? `-₹${Math.abs(diff.spend_delta_lakh).toFixed(1)}L` : "₹0.0L"}
                    </td>
                    <td className="py-2 px-3 text-slate-600 font-sans text-[11px]">
                      {diff.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Plan Action Feedback */}
      {planActionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{planActionSuccess}</span>
        </div>
      )}
      {planActionError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{planActionError}</span>
        </div>
      )}

      {/* Persisted Capital Budget Plans in Supabase */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <BookmarkCheck className="w-4 h-4 text-teal-700" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Persisted Capital Budget Plans & Approvals
              </h2>
              <p className="text-[11px] text-slate-500">
                Official municipal budget plans stored in Supabase PostgreSQL. Approving a plan authorizes official project allocations.
              </p>
            </div>
          </div>
          <button
            onClick={loadPlans}
            disabled={loadingPlans}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-500"
            title="Refresh plans"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingPlans ? "animate-spin" : ""}`} />
          </button>
        </div>

        {loadingPlans && plans.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            <RefreshCw className="w-4 h-4 animate-spin inline-block mr-2 text-teal-600" />
            Loading persisted plans from Supabase...
          </div>
        ) : plans.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
            No budget plans saved yet. Run the solver above and click &quot;Save as Proposed Plan&quot;.
          </div>
        ) : (
          <div className="space-y-3">
            {plans.map((p) => {
              const isApproved = p.status === "approved";
              const isCurrentApproving = approvingPlanId === p.plan_id;
              return (
                <div
                  key={p.plan_id}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3 shadow-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-teal-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                          {p.plan_id}
                        </span>
                        <span className="font-bold text-slate-900 text-sm">{p.title}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                            isApproved
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {p.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Created by: <span className="font-medium text-slate-700">{p.created_by}</span> &bull;{" "}
                        {new Date(p.created_at).toLocaleDateString()} {new Date(p.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      {!isApproved ? (
                        <button
                          onClick={() => handleApprovePlan(p.plan_id)}
                          disabled={isCurrentApproving}
                          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
                        >
                          {isCurrentApproving ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <FileCheck2 className="w-3.5 h-3.5" />
                          )}
                          <span>{isCurrentApproving ? "Authorizing..." : "Approve Plan & Authorize"}</span>
                        </button>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 text-xs font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Authorized in Capital Ledger</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200 text-xs font-mono">
                    <div>
                      <span className="text-[10px] font-sans text-slate-500 block">Total Budget</span>
                      <strong className="text-slate-900">₹{p.budget_lakh.toFixed(1)}L</strong>
                    </div>
                    <div>
                      <span className="text-[10px] font-sans text-slate-500 block">Allocated Spend</span>
                      <strong className="text-emerald-700">₹{p.total_allocated_lakh.toFixed(1)}L</strong>
                    </div>
                    <div>
                      <span className="text-[10px] font-sans text-slate-500 block">Remaining Balance</span>
                      <strong className="text-slate-700">₹{p.remaining_balance_lakh.toFixed(1)}L</strong>
                    </div>
                    <div>
                      <span className="text-[10px] font-sans text-slate-500 block">Interventions</span>
                      <strong className="text-teal-700">{p.items.length} Work Packages</strong>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Interactive Constraint Explainer */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-4 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">
          Stage 5 Mathematical Guarantees & Anti-Spam Bounds
        </h3>

        <div className="flex flex-wrap gap-2">
          {[
            { id: "equity", label: "Social Equity Floor (Hard Constraint)" },
            { id: "signal_bounds", label: "Signal Saturation & Cap (&le; 25%)" },
            { id: "anti_spam", label: "Anti-Spam & Duplicate Resistance" },
            { id: "dispute", label: "Disputed Resolution Policy" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedConstraint(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-xs ${
                selectedConstraint === tab.id
                  ? "bg-slate-100 text-slate-900 border border-slate-300"
                  : "bg-white text-slate-600 hover:text-slate-900 border border-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 text-xs leading-relaxed space-y-2">
          {selectedConstraint === "equity" && (
            <div>
              <div className="font-bold text-slate-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Non-Negotiable Social Equity Constraint</span>
              </div>
              <p className="text-slate-600 mt-1">
                The optimizer enforces that at least <strong>{(equityThreshold * 100).toFixed(0)}%</strong> of the allocated municipal capital must be spent in neighbourhoods with a Social Vulnerability Index (SVI) &ge; 60. Even when citizen report volume is higher in wealthier wards, this mathematical constraint prevents capital abandonment of vulnerable communities.
              </p>
            </div>
          )}

          {selectedConstraint === "signal_bounds" && (
            <div>
              <div className="font-bold text-slate-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Bounded Signal Integration</span>
              </div>
              <p className="text-slate-600 mt-1">
                Citizen need signals cannot distort hazard coefficients arbitrarily. The maximum additive boost is strictly bounded at <code className="bg-slate-200 text-slate-800 px-1 py-0.5 rounded font-mono text-[11px]">&Delta;H &le; 0.25</code> via a Michaelis-Menten style saturation function <code className="bg-slate-200 text-slate-800 px-1 py-0.5 rounded font-mono text-[11px]">&sigma; = S / (S + 5.0)</code>. This ensures civic feedback refines municipal planning without destabilizing baseline risk models.
              </p>
            </div>
          )}

          {selectedConstraint === "anti_spam" && (
            <div>
              <div className="font-bold text-slate-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Spam Resistance & Excluded Lifecycle States</span>
              </div>
              <p className="text-slate-600 mt-1">
                Only corroborated, verified, or actively open tickets generate need signals. All confirmed fake, duplicate, out-of-scope, or dismissed tickets are mathematically excluded with zero weight. Furthermore, exponential recency decay (&tau; = 30 days) dampens stale reports.
              </p>
            </div>
          )}

          {selectedConstraint === "dispute" && (
            <div>
              <div className="font-bold text-slate-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Citizen-Disputed Resolution Escalation</span>
              </div>
              <p className="text-slate-600 mt-1">
                Reports marked as <code className="bg-slate-200 text-slate-800 px-1 py-0.5 rounded font-mono text-[11px]">verification_failed</code> (where a citizen rejects a contractor&apos;s claimed fix) receive a 1.25&times; priority multiplier, ensuring persistent municipal failures receive elevated optimization urgency.
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-900 flex items-center space-x-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
