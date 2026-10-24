"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Coins,
  DollarSign,
  FileCheck2,
  FileText,
  Filter,
  History,
  Info,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";
import {
  AuditEventItem,
  executeDisbursement,
  fetchAccountabilitySummary,
  fetchAllocations,
  fetchAuditTrail,
  fetchDiscrepancies,
  FinancialDiscrepancyItem,
  ImplementationMilestoneItem,
  InterventionAllocationItem,
  PublicAccountabilitySummary,
  resolveDiscrepancy,
  verifyMilestone,
} from "@/lib/api";

export function AccountabilityView() {
  const [activeSubTab, setActiveSubTab] = useState<"allocations" | "discrepancies" | "audit" | "wards">("allocations");
  const [summary, setSummary] = useState<PublicAccountabilitySummary | null>(null);
  const [allocations, setAllocations] = useState<InterventionAllocationItem[]>([]);
  const [discrepancies, setDiscrepancies] = useState<FinancialDiscrepancyItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selected allocation for detailed drawer
  const [selectedAllocation, setSelectedAllocation] = useState<InterventionAllocationItem | null>(null);

  // Filter state
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Resolving discrepancy state
  const [resolvingDiscrepancy, setResolvingDiscrepancy] = useState<FinancialDiscrepancyItem | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState<string>("");
  const [isResolving, setIsResolving] = useState<boolean>(false);

  // Milestone Verification Modal State
  const [verifyingMilestone, setVerifyingMilestone] = useState<ImplementationMilestoneItem | null>(null);
  const [verificationComments, setVerificationComments] = useState<string>("");
  const [verificationDecision, setVerificationDecision] = useState<"approved" | "rejected" | "revision_requested">("approved");
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  // Disbursement Modal State
  const [disbursingAllocation, setDisbursingAllocation] = useState<InterventionAllocationItem | null>(null);
  const [disbursementAmount, setDisbursementAmount] = useState<string>("5.0");
  const [disbursementRef, setDisbursementRef] = useState<string>("");
  const [isDisbursing, setIsDisbursing] = useState<boolean>(false);

  // Toast / Alert Notice
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumData, allocData, discData, auditData] = await Promise.all([
        fetchAccountabilitySummary(),
        fetchAllocations(),
        fetchDiscrepancies().catch(() => []),
        fetchAuditTrail({ limit: 50 }).catch(() => []),
      ]);
      setSummary(sumData);
      setAllocations(allocData);
      setDiscrepancies(discData);
      setAuditEvents(auditData);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load financial accountability data";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const [sumData, allocData, discData, auditData] = await Promise.all([
          fetchAccountabilitySummary(),
          fetchAllocations(),
          fetchDiscrepancies().catch(() => []),
          fetchAuditTrail({ limit: 50 }).catch(() => []),
        ]);
        if (!ignore) {
          setSummary(sumData);
          setAllocations(allocData);
          setDiscrepancies(discData);
          setAuditEvents(auditData);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const message = err instanceof Error ? err.message : "Failed to load financial accountability data";
          setError(message);
          setIsLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingDiscrepancy || !resolutionNotes.trim()) return;

    setIsResolving(true);
    try {
      await resolveDiscrepancy(resolvingDiscrepancy.discrepancy_id, {
        resolution_notes: resolutionNotes,
        action_taken: "resolved",
      });
      setResolvingDiscrepancy(null);
      setResolutionNotes("");
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to resolve discrepancy");
    } finally {
      setIsResolving(false);
    }
  };

  const handleVerifyMilestoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyingMilestone) return;
    setIsVerifying(true);
    try {
      await verifyMilestone(verifyingMilestone.milestone_id, {
        decision: verificationDecision,
        comments: verificationComments.trim() || "Inspection complete.",
        passed_inspection: verificationDecision === "approved",
      });
      setActionNotice(`Milestone #${verifyingMilestone.sequence_order} verification recorded as ${verificationDecision.toUpperCase()}.`);
      setVerifyingMilestone(null);
      setVerificationComments("");
      await loadData();
      if (selectedAllocation) {
        // Refresh selected allocation
        const updated = await fetchAllocations();
        const found = updated.find((a) => a.allocation_id === selectedAllocation.allocation_id);
        if (found) setSelectedAllocation(found);
      }
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to record milestone verification");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDisbursementSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disbursingAllocation) return;
    setIsDisbursing(true);
    try {
      const amt = parseFloat(disbursementAmount);
      if (isNaN(amt) || amt <= 0) {
        alert("Please enter a valid disbursement amount.");
        setIsDisbursing(false);
        return;
      }
      await executeDisbursement(disbursingAllocation.allocation_id, {
        commitment_id: disbursingAllocation.commitments[0]?.commitment_id || "CMT-DEFAULT",
        milestone_id: disbursingAllocation.milestones[0]?.milestone_id || undefined,
        amount_lakh: amt,
        payment_reference: disbursementRef.trim() || `NEFT-${Math.floor(100000 + Math.random() * 900000)}`,
        recipient_entity: disbursingAllocation.commitments[0]?.vendor_name || "Contractor",
      });
      setActionNotice(`Disbursement of ₹${amt.toFixed(2)} Lakh authorized for ${disbursingAllocation.title}.`);
      setDisbursingAllocation(null);
      await loadData();
      if (selectedAllocation) {
        const updated = await fetchAllocations();
        const found = updated.find((a) => a.allocation_id === selectedAllocation.allocation_id);
        if (found) setSelectedAllocation(found);
      }
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to execute monetary disbursement");
    } finally {
      setIsDisbursing(false);
    }
  };

  const filteredAllocations = allocations.filter((a) => {
    const matchesCategory = selectedCategory === "ALL" || a.category.toLowerCase() === selectedCategory.toLowerCase();
    const matchesSearch =
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.neighbourhood_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.intervention_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header & Mission Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="rounded bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider">
              Stage 6 Operational
            </span>
            <span className="text-xs text-slate-500">Fiscal Year 2025-2026</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
            Financial Accountability & Audit Portal
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Cryptographically traceable capital budget appropriations, milestone verification, and disbursement ledger.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="inline-flex items-center space-x-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 px-3.5 py-2 text-xs font-medium text-slate-700 transition-all shadow-xs disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-emerald-600" : ""}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Synthetic Demonstration Notice Banner */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 flex items-start space-x-3">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-amber-950">Public Accountability Framework: </span>
          Capital allocations are legally distinct from mathematical optimizer recommendations.
          Demonstration datasets use calibrated municipal expenditure benchmarks. Attached evidence metadata
          records document integrity hashes without automated physical image forensics.
        </div>
      </div>

      {/* Action Success / Feedback Notice */}
      {actionNotice && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900 flex items-center justify-between shadow-xs animate-in fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{actionNotice}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="text-emerald-700 hover:text-emerald-900 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={loadData} className="underline hover:text-rose-950 font-medium">
            Retry
          </button>
        </div>
      )}

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Allocated */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Authorized Budget</span>
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
              <Coins className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              ₹{summary?.total_allocated_lakh.toFixed(2) ?? "0.00"}
            </span>
            <span className="text-xs text-slate-500">Lakhs</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            Across <span className="text-emerald-700 font-medium">{summary?.allocation_count ?? 0}</span> capital projects
          </div>
        </div>

        {/* Total Committed */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Contract Encumbrances</span>
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100">
              <FileCheck2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold tracking-tight text-teal-700 font-mono">
              ₹{summary?.total_committed_lakh.toFixed(2) ?? "0.00"}
            </span>
            <span className="text-xs text-slate-500">Lakhs</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            {summary && summary.total_allocated_lakh > 0
              ? `${((summary.total_committed_lakh / summary.total_allocated_lakh) * 100).toFixed(1)}% of budget committed`
              : "0% committed"}
          </div>
        </div>

        {/* Total Disbursed */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Disbursed Payouts</span>
            <span className="p-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-100">
              <DollarSign className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              ₹{summary?.total_disbursed_lakh.toFixed(2) ?? "0.00"}
            </span>
            <span className="text-xs text-slate-500">Lakhs</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 inline" />
            <span>{summary?.completed_milestones_count ?? 0} verified milestones completed</span>
          </div>
        </div>

        {/* Treasury Balance */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Remaining Balance</span>
            <span className="p-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-100">
              <TrendingUp className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              ₹{summary?.total_remaining_lakh.toFixed(2) ?? "0.00"}
            </span>
            <span className="text-xs text-slate-500">Lakhs</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            {summary?.open_discrepancies_count ? (
              <span className="text-rose-700 font-semibold flex items-center space-x-1">
                <AlertTriangle className="w-3.5 h-3.5 inline text-rose-600" />
                <span>{summary.open_discrepancies_count} audit flags require review</span>
              </span>
            ) : (
              <span className="text-emerald-700 font-medium">Ledger clean: 0 discrepancies</span>
            )}
          </div>
        </div>
      </div>

      {/* Sub-Tab Navigation */}
      <div className="border-b border-slate-200 flex items-center space-x-4">
        <button
          onClick={() => setActiveSubTab("allocations")}
          className={`pb-3 text-xs font-semibold flex items-center space-x-2 border-b-2 transition-all ${
            activeSubTab === "allocations"
              ? "border-emerald-600 text-emerald-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Capital Allocations & Projects ({allocations.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("discrepancies")}
          className={`pb-3 text-xs font-semibold flex items-center space-x-2 border-b-2 transition-all ${
            activeSubTab === "discrepancies"
              ? "border-rose-600 text-rose-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Discrepancy Radar ({discrepancies.length})</span>
          {discrepancies.filter((d) => d.status === "open").length > 0 && (
            <span className="ml-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 px-1.5 py-0.2 text-[10px] font-bold">
              {discrepancies.filter((d) => d.status === "open").length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab("audit")}
          className={`pb-3 text-xs font-semibold flex items-center space-x-2 border-b-2 transition-all ${
            activeSubTab === "audit"
              ? "border-teal-600 text-teal-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <History className="w-4 h-4" />
          <span>Tamper-Evident Audit Trail ({auditEvents.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("wards")}
          className={`pb-3 text-xs font-semibold flex items-center space-x-2 border-b-2 transition-all ${
            activeSubTab === "wards"
              ? "border-emerald-600 text-emerald-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <MapPin className="w-4 h-4" />
          <span>Ward-Level Equity Summary</span>
        </button>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Tab 1: Allocations & Projects */}
      {/* ----------------------------------------------------------------- */}
      {activeSubTab === "allocations" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white border border-slate-200 p-3 rounded-xl shadow-xs">
            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <Search className="w-4 h-4 text-slate-400 shrink-0" />
              <input
                type="text"
                placeholder="Filter by title, neighbourhood, or intervention..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent border-0 text-xs text-slate-900 placeholder-slate-400 focus:outline-none w-full sm:w-72"
              />
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-white text-xs text-slate-700 rounded-lg px-2.5 py-1.5 border border-slate-300 shadow-xs focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">All Categories</option>
                <option value="drainage">Drainage & Stormwater</option>
                <option value="flooding_drainage">Flooding & Permeable Infrastructure</option>
                <option value="urban_forest">Urban Forestry & Afforestation</option>
                <option value="rainwater_harvesting">Rainwater Harvesting</option>
                <option value="green_roof">Green Roofs</option>
              </select>
            </div>
          </div>

          {/* Allocations Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAllocations.map((alloc) => (
              <div
                key={alloc.allocation_id}
                onClick={() => setSelectedAllocation(alloc)}
                className="rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-md p-4 transition-all cursor-pointer flex flex-col justify-between group shadow-xs"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <span className="rounded bg-slate-100 text-slate-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider border border-slate-200">
                      {alloc.category.replace("_", " ")}
                    </span>
                    <span
                      className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                        alloc.status === "completed"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : alloc.status === "in_progress"
                          ? "bg-blue-50 text-blue-800 border-blue-200"
                          : "bg-slate-100 text-slate-700 border-slate-200"
                      }`}
                    >
                      {alloc.status.replace("_", " ")}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-900 mt-2 group-hover:text-emerald-700 transition-colors line-clamp-2">
                    {alloc.title}
                  </h3>

                  <div className="mt-2 text-xs text-slate-500 flex items-center space-x-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>{alloc.neighbourhood_name}</span>
                    <span className="text-slate-300">•</span>
                    <span>{alloc.planned_units} Units</span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-4">
                    <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                      <span>Disbursement Progress</span>
                      <span className="font-semibold text-slate-800 font-mono">{alloc.disbursement_progress_pct}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-600 h-full rounded-full transition-all duration-500"
                        style={{ width: `${alloc.disbursement_progress_pct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Bottom Ledger Mini-Stats */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">Authorized</span>
                    <span className="font-semibold text-slate-900 font-mono">₹{alloc.allocated_amount_lakh.toFixed(2)}L</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">Disbursed</span>
                    <span className="font-semibold text-emerald-700 font-mono">₹{alloc.disbursed_amount_lakh.toFixed(2)}L</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">Balance</span>
                    <span className="font-semibold text-slate-900 font-mono">₹{alloc.remaining_budget_lakh.toFixed(2)}L</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredAllocations.length === 0 && !isLoading && (
            <div className="text-center py-12 rounded-xl border border-dashed border-slate-200 bg-white text-slate-500 shadow-xs">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-40 text-slate-400" />
              <p className="text-sm font-medium text-slate-700">No allocations match your selected filters</p>
            </div>
          )}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Tab 2: Discrepancy Radar */}
      {/* ----------------------------------------------------------------- */}
      {activeSubTab === "discrepancies" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              Automated Discrepancy & Fraud Detection Monitor
            </h2>
            <span className="text-xs text-slate-500">
              Scans budget overruns, unverified disbursements, and stalled milestones
            </span>
          </div>

          <div className="space-y-3">
            {discrepancies.map((disc) => (
              <div
                key={disc.discrepancy_id}
                className={`rounded-xl border p-4 transition-all shadow-xs ${
                  disc.status === "resolved"
                    ? "border-slate-200 bg-slate-50/70 opacity-80"
                    : disc.severity === "critical"
                    ? "border-rose-200 bg-rose-50/40"
                    : disc.severity === "high"
                    ? "border-amber-200 bg-amber-50/40"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-3">
                    <div
                      className={`p-2 rounded-lg shrink-0 mt-0.5 border ${
                        disc.severity === "critical"
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : disc.severity === "high"
                          ? "bg-amber-50 text-amber-700 border-amber-200"
                          : "bg-blue-50 text-blue-700 border-blue-200"
                      }`}
                    >
                      <ShieldAlert className="w-5 h-5" />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-slate-900">{disc.title}</span>
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                            disc.severity === "critical"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : disc.severity === "high"
                              ? "bg-amber-50 text-amber-700 border-amber-200"
                              : "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {disc.severity}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">[{disc.discrepancy_id}]</span>
                      </div>

                      <p className="text-xs text-slate-600 mt-1">{disc.description}</p>

                      <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-slate-500">
                        <span>
                          Target Allocation:{" "}
                          <span className="font-mono text-emerald-700 font-semibold">{disc.allocation_id}</span>
                        </span>
                        <span>•</span>
                        <span>
                          At-Risk Amount:{" "}
                          <span className="font-semibold text-rose-700 font-mono">
                            ₹{disc.amount_involved_lakh.toFixed(2)}L
                          </span>
                        </span>
                        <span>•</span>
                        <span>Detected: {new Date(disc.detected_at).toLocaleString()}</span>
                      </div>

                      {disc.resolution_notes && (
                        <div className="mt-3 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
                          <span className="font-semibold text-emerald-800">Resolution Audit Note: </span>
                          {disc.resolution_notes}
                          <span className="text-slate-500 block text-[10px] mt-1">
                            Resolved by {disc.resolved_by} on {disc.resolved_at ? new Date(disc.resolved_at).toLocaleString() : ""}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {disc.status === "open" && (
                    <button
                      onClick={() => setResolvingDiscrepancy(disc)}
                      className="shrink-0 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 transition-all shadow-xs"
                    >
                      Resolve Flag
                    </button>
                  )}
                </div>
              </div>
            ))}

            {discrepancies.length === 0 && (
              <div className="text-center py-12 rounded-xl border border-dashed border-slate-200 bg-white text-slate-500 shadow-xs">
                <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-emerald-600 opacity-80" />
                <p className="text-sm font-medium text-slate-800">All Financial Accounts Verified</p>
                <p className="text-xs text-slate-500 mt-1">No cost overruns, unverified disbursements, or anomalies detected.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Tab 3: Tamper-Evident Audit Trail */}
      {/* ----------------------------------------------------------------- */}
      {activeSubTab === "audit" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Cryptographic Audit Log & SHA-256 Hash Chain
              </h2>
              <p className="text-xs text-slate-500">
                Every municipal appropriation, contract commitment, evidence submission, and payout produces an immutable cryptographic link.
              </p>
            </div>
            <span className="rounded bg-emerald-50 border border-emerald-200 text-emerald-800 px-2.5 py-1 text-xs font-mono font-semibold">
              Chain Integrity: VALID
            </span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden divide-y divide-slate-100 shadow-xs">
            {auditEvents.map((evt) => (
              <div key={evt.event_id} className="p-4 hover:bg-slate-50/60 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-3">
                    <div className="p-1.5 rounded-lg bg-teal-50 text-teal-700 border border-teal-100 shrink-0 mt-0.5">
                      <History className="w-4 h-4" />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold text-slate-900">{evt.summary}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 uppercase border border-slate-200">
                          {evt.event_type.replace("_", " ")}
                        </span>
                      </div>

                      <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                        <span>
                          Actor: <span className="text-emerald-700 font-medium">{evt.actor_id}</span> ({evt.actor_role})
                        </span>
                        <span>•</span>
                        <span>
                          Entity: <span className="font-mono text-slate-700">{evt.entity_id}</span>
                        </span>
                        <span>•</span>
                        <span>Timestamp: {new Date(evt.timestamp).toLocaleString()}</span>
                      </div>

                      {/* Cryptographic Hash Badge */}
                      <div className="mt-2 flex items-center space-x-2 text-[10px] font-mono text-slate-400">
                        <span className="text-slate-500 font-sans font-medium">SHA-256:</span>
                        <span className="truncate max-w-xs text-teal-700">{evt.event_hash}</span>
                      </div>
                    </div>
                  </div>

                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {evt.event_id}
                  </span>
                </div>
              </div>
            ))}

            {auditEvents.length === 0 && (
              <div className="text-center py-10 text-slate-500 text-xs">
                No audit events recorded yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Tab 4: Ward-Level Equity Summary */}
      {/* ----------------------------------------------------------------- */}
      {activeSubTab === "wards" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              Ward-Level Capital Allocation & Disbursement Distribution
            </h2>
            <span className="text-xs text-slate-500">
              Ensures public expenditure complies with municipal social vulnerability equity floors
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {summary?.by_neighbourhood.map((ward) => (
              <div
                key={ward.neighbourhood_id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">{ward.neighbourhood_name}</h3>
                  <span className="text-[10px] font-mono text-slate-400">{ward.neighbourhood_id}</span>
                </div>

                <div className="mt-3 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Capital Projects</span>
                    <span className="font-semibold text-slate-800">{ward.project_count}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Authorized Allocation</span>
                    <span className="font-semibold text-emerald-700 font-mono">₹{ward.allocated_lakh.toFixed(2)}L</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Disbursed Funds</span>
                    <span className="font-semibold text-teal-700 font-mono">₹{ward.disbursed_lakh.toFixed(2)}L</span>
                  </div>

                  {/* Progress bar */}
                  <div className="pt-2">
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-600 h-full rounded-full"
                        style={{
                          width: `${ward.allocated_lakh > 0 ? (ward.disbursed_lakh / ward.allocated_lakh) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Allocation Detail Modal Drawer */}
      {/* ----------------------------------------------------------------- */}
      {selectedAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-xl p-6">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="rounded bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 text-[10px] font-semibold uppercase">
                  {selectedAllocation.category.replace("_", " ")}
                </span>
                <h2 className="text-lg font-bold text-slate-900 mt-1">{selectedAllocation.title}</h2>
                <p className="text-xs text-slate-500">
                  {selectedAllocation.neighbourhood_name} • {selectedAllocation.allocation_id} • Resolution: {selectedAllocation.council_resolution_ref || "Standard Capital Vote"}
                </p>
              </div>

              <button
                onClick={() => setSelectedAllocation(null)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Financial Ledger Mini-Table */}
            <div className="grid grid-cols-3 gap-3 my-4 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-medium">Authorized</span>
                <span className="text-sm font-bold text-slate-900 font-mono">₹{selectedAllocation.allocated_amount_lakh.toFixed(2)}L</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-medium">Contracted</span>
                <span className="text-sm font-bold text-teal-700 font-mono">₹{selectedAllocation.committed_amount_lakh.toFixed(2)}L</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-medium">Disbursed</span>
                <span className="text-sm font-bold text-emerald-700 font-mono">₹{selectedAllocation.disbursed_amount_lakh.toFixed(2)}L</span>
              </div>
            </div>

            {/* Implementation Milestones */}
            <div className="mt-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                Implementation Milestones ({selectedAllocation.milestones.length})
              </h3>

              <div className="space-y-3">
                {selectedAllocation.milestones.map((m) => (
                  <div key={m.milestone_id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-xs text-slate-900">
                            #{m.sequence_order}: {m.title}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                              m.status === "verified_complete"
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                : "bg-slate-100 text-slate-700 border-slate-200"
                            }`}
                          >
                            {m.status.replace("_", " ")}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">{m.description}</p>
                      </div>

                      <span className="text-xs font-semibold text-slate-900 font-mono">
                        ₹{m.disbursement_tied_amount_lakh.toFixed(2)}L
                      </span>
                    </div>

                    {/* Evidence preview if attached */}
                    {m.evidence_items.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1.5">
                          Attached Evidence Metadata ({m.evidence_items.length}):
                        </span>
                        <div className="space-y-1.5">
                          {m.evidence_items.map((evd) => (
                            <div key={evd.evidence_id} className="text-xs flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200 shadow-xs">
                              <div className="flex items-center space-x-2">
                                <FileText className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                                <span className="text-slate-800">{evd.title}</span>
                              </div>
                              <span className="text-[10px] font-mono text-emerald-700 font-medium">
                                {evd.verification_status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Verification inspection note */}
                    {m.verification_decision && (
                      <div className="mt-2 text-xs text-emerald-900 bg-emerald-50 border border-emerald-200 p-2 rounded-lg">
                        <span className="font-semibold text-emerald-950">Inspection Sign-off: </span>
                        {m.verification_decision.comments} ({m.verification_decision.verifier_name})
                      </div>
                    )}

                    {/* Admin Verification Action */}
                    {m.status !== "verified_complete" && (
                      <div className="mt-2 pt-2 border-t border-slate-200 flex justify-end">
                        <button
                          onClick={() => {
                            setVerifyingMilestone(m);
                            setVerificationComments("Physical on-site inspection completed. Dimensions, grade, and materials comply with approved design.");
                            setVerificationDecision("approved");
                          }}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center space-x-1.5 shadow-xs"
                        >
                          <FileCheck2 className="w-3.5 h-3.5" />
                          <span>Municipal Verification Sign-off</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Close Button */}
            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedAllocation(null)}
                className="px-4 py-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs"
              >
                Close Project Ledger
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Milestone Verification Sign-Off Modal */}
      {/* ----------------------------------------------------------------- */}
      {verifyingMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-emerald-700 font-bold">
                  Milestone #{verifyingMilestone.sequence_order} &bull; ₹{verifyingMilestone.disbursement_tied_amount_lakh.toFixed(2)}L
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-0.5">Municipal Physical Verification Sign-off</h2>
              </div>
              <button onClick={() => setVerifyingMilestone(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleVerifyMilestoneSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Inspection Decision</label>
                <select
                  value={verificationDecision}
                  onChange={(e) => setVerificationDecision(e.target.value as "approved" | "rejected" | "revision_requested")}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                >
                  <option value="approved">Approved — Passes CPWD/Municipal Physical Inspection</option>
                  <option value="rejected">Rejected — Fails Engineering Specifications</option>
                  <option value="revision_requested">Revision Requested — Corrections Required</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  Inspector Comments & Certification Notes (Required)
                </label>
                <textarea
                  required
                  rows={3}
                  value={verificationComments}
                  onChange={(e) => setVerificationComments(e.target.value)}
                  placeholder="Record on-site inspection measurements, material test confirmation..."
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setVerifyingMilestone(null)}
                  className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium shadow-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isVerifying}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs disabled:opacity-50"
                >
                  {isVerifying ? "Certifying..." : "Authorize Official Sign-Off"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Monetary Disbursement Authorization Modal */}
      {/* ----------------------------------------------------------------- */}
      {disbursingAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-teal-700 font-bold">
                  {disbursingAllocation.allocation_id} &bull; Balance: ₹{disbursingAllocation.remaining_budget_lakh.toFixed(2)}L
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-0.5">Authorize Monetary Tranche Disbursement</h2>
              </div>
              <button onClick={() => setDisbursingAllocation(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleDisbursementSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Disbursement Amount (₹ Lakh)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max={disbursingAllocation.remaining_budget_lakh}
                    required
                    value={disbursementAmount}
                    onChange={(e) => setDisbursementAmount(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-teal-500 font-mono shadow-xs"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Banking / NEFT Ref</label>
                  <input
                    type="text"
                    required
                    value={disbursementRef}
                    onChange={(e) => setDisbursementRef(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-teal-500 font-mono shadow-xs"
                  />
                </div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600 space-y-1">
                <div className="flex justify-between">
                  <span>Vendor / Recipient:</span>
                  <span className="text-slate-900 font-semibold">{disbursingAllocation.commitments[0]?.vendor_name || "Contractor"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Remaining Project Cap:</span>
                  <span className="text-slate-900 font-mono font-bold">₹{disbursingAllocation.remaining_budget_lakh.toFixed(2)} Lakh</span>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDisbursingAllocation(null)}
                  className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium shadow-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDisbursing}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs disabled:opacity-50"
                >
                  {isDisbursing ? "Authorizing..." : "Execute Monetary Payout"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Resolve Discrepancy Modal */}
      {/* ----------------------------------------------------------------- */}
      {resolvingDiscrepancy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6">
            <h2 className="text-base font-bold text-slate-900">Resolve Financial Discrepancy Flag</h2>
            <p className="text-xs text-slate-500 mt-1">
              Provide formal municipal justification and corrective actions taken for {resolvingDiscrepancy.title}.
            </p>

            <form onSubmit={handleResolveSubmit} className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  Resolution Audit Notes & Justification (Required)
                </label>
                <textarea
                  required
                  rows={4}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Detail tender cancellation, refund receipt, or council ratification resolution..."
                  className="w-full rounded-lg bg-white border border-slate-300 p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setResolvingDiscrepancy(null)}
                  className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium shadow-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResolving}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50"
                >
                  {isResolving ? "Recording..." : "Record Official Resolution"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
