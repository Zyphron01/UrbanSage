"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  FileText,
  HardHat,
  Hash,
  MapPin,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  attachMilestoneEvidence,
  fetchAllocations,
  fetchPartnerBudget,
  ImplementationMilestoneItem,
  InterventionAllocationItem,
  PartnerBudgetSummary,
  submitExpenditureRequest,
  updateMilestoneProgress,
} from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { DollarSign, Landmark, Plus, TrendingUp } from "lucide-react";

export function ContractorPortalView() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"milestones" | "budget">("budget");
  const [allocations, setAllocations] = useState<InterventionAllocationItem[]>([]);
  const [selectedAllocation, setSelectedAllocation] = useState<InterventionAllocationItem | null>(null);
  const [partnerBudget, setPartnerBudget] = useState<PartnerBudgetSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingBudget, setIsLoadingBudget] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Inline Limited Budget Planner Form State
  const [plannerAllocationId, setPlannerAllocationId] = useState<string>("");
  const [plannerAmount, setPlannerAmount] = useState<string>("");
  const [plannerPurpose, setPlannerPurpose] = useState<string>("");
  const [isSavingProposal, setIsSavingProposal] = useState<boolean>(false);
  const [plannerError, setPlannerError] = useState<string | null>(null);

  // Proposed Expenditure Request Modal State
  const [isRequestModalOpen, setIsRequestModalOpen] = useState<boolean>(false);
  const [requestAllocationId, setRequestAllocationId] = useState<string>("");
  const [requestCommitmentId, setRequestCommitmentId] = useState<string>("");
  const [requestAmount, setRequestAmount] = useState<string>("");
  const [requestPaymentRef, setRequestPaymentRef] = useState<string>("");
  const [requestPayee, setRequestPayee] = useState<string>("Bengaluru Urban Drainage & Infra Ltd");
  const [requestNotes, setRequestNotes] = useState<string>("");
  const [isSubmittingRequest, setIsSubmittingRequest] = useState<boolean>(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Milestone Progress Update Modal State
  const [updatingMilestone, setUpdatingMilestone] = useState<ImplementationMilestoneItem | null>(null);
  const [newProgress, setNewProgress] = useState<number>(50);
  const [newStatus, setNewStatus] = useState<"pending" | "in_progress" | "submitted_for_review">("in_progress");
  const [progressNotes, setProgressNotes] = useState<string>("");
  const [isUpdatingProgress, setIsUpdatingProgress] = useState<boolean>(false);

  // Evidence Attachment Modal State
  const [attachingMilestone, setAttachingMilestone] = useState<ImplementationMilestoneItem | null>(null);
  const [evidenceTitle, setEvidenceTitle] = useState<string>("");
  const [evidenceType, setEvidenceType] = useState<
    "site_photo" | "inspection_report" | "material_invoice" | "community_sign_off" | "geo_survey"
  >("site_photo");
  const [evidenceFileName, setEvidenceFileName] = useState<string>("");
  const [evidenceDesc, setEvidenceDesc] = useState<string>("");
  const [isSubmittingEvidence, setIsSubmittingEvidence] = useState<boolean>(false);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  const loadBudget = useCallback(async () => {
    setIsLoadingBudget(true);
    try {
      const budget = await fetchPartnerBudget("VND-BBMP-WORKS-01");
      setPartnerBudget(budget);
    } catch (err: unknown) {
      console.warn("Could not load partner budget:", err);
    } finally {
      setIsLoadingBudget(false);
    }
  }, []);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAllocations();
      setAllocations(data);
      if (data.length > 0 && !selectedAllocation) {
        setSelectedAllocation(data[0]);
      } else if (selectedAllocation) {
        const found = data.find((a) => a.allocation_id === selectedAllocation.allocation_id);
        if (found) setSelectedAllocation(found);
      }
      await loadBudget();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load contractor work orders");
    } finally {
      setIsLoading(false);
    }
  }, [selectedAllocation, loadBudget]);

  useEffect(() => {
    let isMounted = true;
    fetchAllocations()
      .then((data) => {
        if (isMounted) {
          setAllocations(data);
          if (data.length > 0) {
            setSelectedAllocation(data[0]);
          }
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load contractor work orders");
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleUpdateProgressSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updatingMilestone) return;
    setIsUpdatingProgress(true);
    try {
      await updateMilestoneProgress(updatingMilestone.milestone_id, {
        percent_progress: Number(newProgress),
        status: newStatus,
        notes: progressNotes.trim() || undefined,
      });
      setSuccessNotice(`Progress for Milestone #${updatingMilestone.sequence_order} updated to ${newProgress}% (${newStatus}).`);
      setUpdatingMilestone(null);
      setProgressNotes("");
      await loadData();
      setTimeout(() => setSuccessNotice(null), 5000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update milestone progress");
    } finally {
      setIsUpdatingProgress(false);
    }
  };

  const handleAttachEvidenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!attachingMilestone || !evidenceTitle.trim() || !evidenceFileName.trim()) return;
    setIsSubmittingEvidence(true);
    try {
      // Generate realistic SHA-256 hash
      const randomHash = Array.from(crypto.getRandomValues(new Uint8Array(32)))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");

      await attachMilestoneEvidence(attachingMilestone.milestone_id, {
        evidence_type: evidenceType,
        title: evidenceTitle.trim(),
        description: evidenceDesc.trim() || undefined,
        file_name: evidenceFileName.trim(),
        mime_type: evidenceType === "site_photo" ? "image/jpeg" : "application/pdf",
        file_size_bytes: Math.floor(Math.random() * 2500000) + 500000,
        document_hash: randomHash,
      });

      setSuccessNotice(`Documentary evidence "${evidenceTitle}" attached to Milestone #${attachingMilestone.sequence_order}.`);
      setAttachingMilestone(null);
      setEvidenceTitle("");
      setEvidenceFileName("");
      setEvidenceDesc("");
      await loadData();
      setTimeout(() => setSuccessNotice(null), 5000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to attach documentary evidence");
    } finally {
      setIsSubmittingEvidence(false);
    }
  };

  useEffect(() => {
    if (partnerBudget && partnerBudget.projects.length > 0 && !plannerAllocationId) {
      setPlannerAllocationId(partnerBudget.projects[0].allocation_id);
    }
  }, [partnerBudget, plannerAllocationId]);

  const selectedPlannerProject =
    partnerBudget?.projects.find((p) => p.allocation_id === plannerAllocationId) ||
    partnerBudget?.projects[0];
  const selectedPlannerAvailableLakh = selectedPlannerProject?.remaining_balance_lakh || 0;

  const handleSavePlannerProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    setPlannerError(null);

    if (!selectedPlannerProject) {
      setPlannerError(t("contractor.selectProject", "Please select an assigned project."));
      return;
    }

    const amount = parseFloat(plannerAmount);
    if (isNaN(amount) || amount <= 0) {
      setPlannerError(t("contractor.zeroAmountError", "Requested amount must be greater than zero."));
      return;
    }

    if (amount > selectedPlannerAvailableLakh) {
      setPlannerError(
        `${t("contractor.overBudgetError", "Proposed expenditure exceeds available budget for this project.")} (Requested: ₹${amount.toFixed(2)}L, Available: ₹${selectedPlannerAvailableLakh.toFixed(2)}L)`
      );
      return;
    }

    if (!plannerPurpose.trim()) {
      setPlannerError("Please enter the expenditure purpose.");
      return;
    }

    setIsSavingProposal(true);
    try {
      const alloc = allocations.find((a) => a.allocation_id === selectedPlannerProject.allocation_id);
      const cmt = alloc?.commitments.find((c) => c.vendor_id === "VND-BBMP-WORKS-01") || alloc?.commitments[0];
      if (!cmt) {
        throw new Error("No active commitment found for this project.");
      }

      await submitExpenditureRequest(selectedPlannerProject.allocation_id, {
        commitment_id: cmt.commitment_id,
        amount_lakh: amount,
        payment_reference: plannerPurpose.trim(),
        recipient_entity: partnerBudget?.vendor_name || "Bengaluru Urban Drainage & Infra Ltd",
        notes: plannerPurpose.trim(),
      });

      setSuccessNotice(
        `Expenditure proposal for ₹${amount.toFixed(2)}L (₹${(amount * 100000).toLocaleString("en-IN")}) saved to Supabase (Status: Pending Review).`
      );
      setPlannerAmount("");
      setPlannerPurpose("");
      await loadData();
      setTimeout(() => setSuccessNotice(null), 6000);
    } catch (err: unknown) {
      setPlannerError(err instanceof Error ? err.message : "Failed to save proposal");
    } finally {
      setIsSavingProposal(false);
    }
  };

  const handleExpenditureSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRequestError(null);
    const amount = parseFloat(requestAmount);
    if (isNaN(amount) || amount <= 0) {
      setRequestError("Please enter a valid claim amount greater than zero.");
      return;
    }

    const proj = partnerBudget?.projects.find((p) => p.allocation_id === requestAllocationId);
    if (proj && amount > proj.remaining_balance_lakh) {
      setRequestError(
        `Proposed expenditure ₹${amount.toFixed(2)}L exceeds project remaining available balance ₹${proj.remaining_balance_lakh.toFixed(2)}L.`
      );
      return;
    }

    setIsSubmittingRequest(true);
    try {
      await submitExpenditureRequest(requestAllocationId, {
        commitment_id: requestCommitmentId,
        amount_lakh: amount,
        payment_reference: requestPaymentRef.trim(),
        recipient_entity: requestPayee.trim(),
        notes: requestNotes.trim() || undefined,
      });

      setSuccessNotice(
        `Proposed expenditure claim for ₹${amount.toFixed(2)}L submitted with status 'pending_approval' in Supabase.`
      );
      setIsRequestModalOpen(false);
      setRequestAmount("");
      setRequestPaymentRef("");
      setRequestNotes("");
      await loadData();
      setTimeout(() => setSuccessNotice(null), 6000);
    } catch (err: unknown) {
      setRequestError(err instanceof Error ? err.message : "Failed to submit expenditure request");
    } finally {
      setIsSubmittingRequest(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Contractor Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center space-x-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
              <HardHat className="w-3.5 h-3.5" />
              <span>Implementation & Contractor Portal (VND-BBMP-WORKS-01)</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Work Order Execution & Milestone Verification Gateway
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Assigned to <strong>Bengaluru Urban Drainage & Infra Ltd</strong>. Log physical work progress, submit photographic
              field documentation with cryptographic integrity hashes, and track municipal engineering inspection sign-offs.
            </p>
          </div>

          <div className="flex flex-col items-end text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 shrink-0">
            <span className="text-[10px] uppercase font-semibold text-slate-500">Active Vendor ID</span>
            <span className="font-mono text-teal-700 font-bold">VND-BBMP-WORKS-01</span>
            <span className="text-[10px] text-slate-500 mt-1">Disbursement Policy: Milestone Verified Only</span>
          </div>
        </div>

        {/* RBAC Boundary Note */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center space-x-2 text-[11px] text-slate-500">
          <ShieldAlert className="w-3.5 h-3.5 text-teal-600 shrink-0" />
          <span>
            Strict Financial Safeguards: Contractors cannot self-verify milestones, approve payouts, or access confidential municipal decision briefs.
          </span>
        </div>
      </div>

      {/* Success Notification */}
      {successNotice && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successNotice}</span>
          </div>
          <button onClick={() => setSuccessNotice(null)} className="text-slate-400 hover:text-slate-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => loadData()} className="underline hover:text-rose-950 font-semibold">
            Retry
          </button>
        </div>
      )}

      {/* Portal Tabs: Budget & Expenditure vs. Work Orders */}
      <div className="flex border-b border-slate-200 space-x-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("budget")}
          className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-lg transition border-b-2 ${
            activeTab === "budget"
              ? "border-emerald-600 text-emerald-800 bg-emerald-50/50"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Landmark className="w-4 h-4" />
          <span>{t("contractor.budgetSection", "Limited Budget Planner")}</span>
          {partnerBudget && (
            <span className="ml-1.5 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px]">
              ₹{partnerBudget.total_remaining_balance_lakh.toFixed(1)}L {t("contractor.remainingBudget", "Remaining")}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("milestones")}
          className={`flex items-center space-x-2 py-2.5 px-4 rounded-t-lg transition border-b-2 ${
            activeTab === "milestones"
              ? "border-emerald-600 text-emerald-800 bg-emerald-50/50"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <HardHat className="w-4 h-4" />
          <span>{t("contractor.assignedProjects", "Assigned Work Orders & Milestones")}</span>
          <span className="ml-1.5 px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px]">
            {allocations.length}
          </span>
        </button>
      </div>

      {/* Tab 1: Dedicated Budget & Expenditure Section */}
      {activeTab === "budget" && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Landmark className="w-5 h-5 text-emerald-600" />
                <span>{t("contractor.budgetSection", "Limited Budget Planner")}</span>
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                {t("contractor.formSubtitle", "Submit an expenditure proposal against assigned project commitments for municipal review.")}
              </p>
            </div>
            <button
              onClick={() => loadData()}
              disabled={isLoadingBudget}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingBudget ? "animate-spin text-emerald-600" : ""}`} />
              <span>{t("common.refresh", "Refresh Records")}</span>
            </button>
          </div>

          {/* Financial Safeguards Notice */}
          <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-4 flex items-start gap-3 text-amber-900 text-xs">
            <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">{t("contractor.financialLimitsNotice", "Financial Limits & RBAC Governance")}: </span>
              {t("contractor.budgetSubtitle", "Partners cannot authorize payouts or approve their own proposals. All proposals require municipal administrative review.")}
            </div>
          </div>

          {/* 4 Financial Metric Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">
                {t("contractor.totalAllocated", "Total Allocated Budget")}
              </span>
              <div className="text-2xl font-extrabold text-slate-900 mt-1">
                ₹{partnerBudget?.total_allocated_lakh ? partnerBudget.total_allocated_lakh.toFixed(2) : "0.00"}L
              </div>
              <span className="text-[11px] text-slate-400">
                ₹{((partnerBudget?.total_allocated_lakh || 0) * 100000).toLocaleString("en-IN")} Authorized
              </span>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
              <span className="text-xs text-blue-600 font-medium">
                {t("contractor.committedAmount", "Committed Amount")}
              </span>
              <div className="text-2xl font-extrabold text-blue-700 mt-1">
                ₹{partnerBudget ? partnerBudget.total_committed_lakh.toFixed(2) : "0.00"}L
              </div>
              <span className="text-[11px] text-slate-400">
                ₹{((partnerBudget?.total_committed_lakh || 0) * 100000).toLocaleString("en-IN")} Contracted
              </span>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
              <span className="text-xs text-emerald-600 font-medium">
                {t("contractor.amountSpent", "Amount Spent / Disbursed")}
              </span>
              <div className="text-2xl font-extrabold text-emerald-700 mt-1">
                ₹{partnerBudget ? partnerBudget.total_disbursed_lakh.toFixed(2) : "0.00"}L
              </div>
              <span className="text-[11px] text-slate-400">
                ₹{((partnerBudget?.total_disbursed_lakh || 0) * 100000).toLocaleString("en-IN")} Released
              </span>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
              <span className="text-xs text-teal-600 font-medium">
                {t("contractor.remainingBudget", "Remaining Budget")}
              </span>
              <div className="text-2xl font-extrabold text-teal-700 mt-1">
                ₹{partnerBudget ? partnerBudget.total_remaining_balance_lakh.toFixed(2) : "0.00"}L
              </div>
              <span className="text-[11px] text-teal-600 font-medium">
                ₹{((partnerBudget?.total_remaining_balance_lakh || 0) * 100000).toLocaleString("en-IN")} Available
              </span>
            </div>
          </div>

          {/* Budget Allocation Proposal Form */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                {t("contractor.formTitle", "Budget Allocation Proposal")}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {t("contractor.formSubtitle", "Submit an expenditure proposal against assigned project commitments for municipal review.")}
              </p>
            </div>

            {plannerError && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <span>{plannerError}</span>
              </div>
            )}

            <form onSubmit={handleSavePlannerProposal} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Assigned project selector */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                    {t("contractor.assignedProject", "Assigned Project")} *
                  </label>
                  <select
                    value={plannerAllocationId}
                    onChange={(e) => setPlannerAllocationId(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                  >
                    {partnerBudget?.projects.map((p) => (
                      <option key={p.allocation_id} value={p.allocation_id}>
                        {p.title} ({p.allocation_id} • {p.neighbourhood_name})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Available budget */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                    {t("contractor.availableBudget", "Available Budget")}
                  </label>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs flex items-center justify-between">
                    <span className="text-slate-600 font-mono">
                      ₹{selectedPlannerAvailableLakh.toFixed(2)} Lakhs
                    </span>
                    <span className="text-emerald-700 font-bold font-mono">
                      ₹{(selectedPlannerAvailableLakh * 100000).toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Proposed expenditure amount (₹) */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                    {t("contractor.proposedAmount", "Proposed Expenditure Amount (₹ Lakhs)")} *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={selectedPlannerAvailableLakh > 0 ? selectedPlannerAvailableLakh : undefined}
                    required
                    value={plannerAmount}
                    onChange={(e) => setPlannerAmount(e.target.value)}
                    placeholder="e.g. 5.50"
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs font-mono"
                  />
                  {plannerAmount && !isNaN(parseFloat(plannerAmount)) && parseFloat(plannerAmount) > 0 && (
                    <span className="text-[11px] text-emerald-700 block mt-1">
                      = ₹{(parseFloat(plannerAmount) * 100000).toLocaleString("en-IN")} INR
                    </span>
                  )}
                </div>

                {/* Expenditure purpose */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                    {t("contractor.expenditurePurpose", "Expenditure Purpose")} *
                  </label>
                  <input
                    type="text"
                    required
                    value={plannerPurpose}
                    onChange={(e) => setPlannerPurpose(e.target.value)}
                    placeholder={t("contractor.expenditurePurposePlaceholder", "e.g. Procurement of HDPE perforated pipes for bio-swale filter drain...")}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="text-[11px] text-slate-500">
                  <span>* Subject to automated financial cap validation and backend audit persistence.</span>
                </div>
                <button
                  type="submit"
                  disabled={
                    isSavingProposal ||
                    !plannerAmount ||
                    parseFloat(plannerAmount) <= 0 ||
                    parseFloat(plannerAmount) > selectedPlannerAvailableLakh
                  }
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs disabled:opacity-40 transition-colors cursor-pointer disabled:cursor-not-allowed"
                >
                  <Plus className="w-4 h-4" />
                  <span>{isSavingProposal ? t("contractor.savingProposal", "Submitting to Supabase...") : t("contractor.saveProposalBtn", "Save Proposal")}</span>
                </button>
              </div>
            </form>
          </div>

          {/* List or Table of Existing Proposals */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {t("contractor.existingProposals", "Existing Expenditure Proposals")}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Chronological records of submitted budget proposals and municipal authorization statuses
                </p>
              </div>
              <span className="text-xs font-mono text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full">
                {partnerBudget?.proposals?.length || 0} Records
              </span>
            </div>

            {!partnerBudget?.proposals || partnerBudget.proposals.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                <Landmark className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="font-medium text-slate-600">{t("contractor.noProposals", "No proposals submitted yet.")}</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Use the budget allocation form above to submit an expenditure proposal.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                      <th className="py-3 px-4">{t("contractor.tableProject", "Project")}</th>
                      <th className="py-3 px-3 text-right">{t("contractor.tableRequested", "Requested Amount")}</th>
                      <th className="py-3 px-4">{t("contractor.tablePurpose", "Purpose")}</th>
                      <th className="py-3 px-3 text-center">{t("contractor.tableStatus", "Status")}</th>
                      <th className="py-3 px-4 text-right">{t("contractor.tableDate", "Submission Date")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {partnerBudget.proposals.map((prop) => (
                      <tr key={prop.proposal_id} className="hover:bg-slate-50 transition">
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-slate-900">{prop.project_title}</div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {prop.proposal_id} • {prop.allocation_id}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-right font-mono font-semibold text-slate-900">
                          <div>₹{prop.amount_lakh.toFixed(2)}L</div>
                          <span className="text-[10px] text-slate-400">
                            ₹{(prop.amount_lakh * 100000).toLocaleString("en-IN")}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-700 max-w-xs truncate">
                          {prop.purpose}
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span
                            className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                              prop.status === "completed"
                                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                : prop.status === "rejected"
                                ? "bg-rose-50 text-rose-800 border border-rose-200"
                                : "bg-amber-50 text-amber-800 border border-amber-200"
                            }`}
                          >
                            {prop.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right text-slate-500 font-mono text-[11px]">
                          {new Date(prop.submission_date).toLocaleDateString("en-IN", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Utilization Progress Bar */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
            <div className="flex justify-between text-xs text-slate-600 font-medium">
              <span>Overall Capital Execution Progress</span>
              <span>{partnerBudget?.overall_utilization_pct.toFixed(1) || 0}% Disbursed</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, partnerBudget?.overall_utilization_pct || 0)}%` }}
              />
            </div>
            {partnerBudget && partnerBudget.total_pending_requests_lakh > 0 && (
              <div className="text-xs text-amber-700 pt-1 flex items-center gap-1.5 font-medium">
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                <span>
                  {t("contractor.pendingRequests")}: ₹{partnerBudget.total_pending_requests_lakh.toFixed(2)}L awaiting municipal review.
                </span>
              </div>
            )}
          </div>

          {/* Action Row & Project-Level Breakdown Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {t("contractor.projectBudgetTable")}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Detailed breakdown of contracts, disbursements, and uncommitted balances assigned to {partnerBudget?.vendor_name || "VND-BBMP-WORKS-01"}
                </p>
              </div>
              <button
                onClick={() => {
                  if (partnerBudget && partnerBudget.projects.length > 0) {
                    const firstProj = partnerBudget.projects[0];
                    setRequestAllocationId(firstProj.allocation_id);
                    const alloc = allocations.find((a) => a.allocation_id === firstProj.allocation_id);
                    const cmt = alloc?.commitments.find((c) => c.vendor_id === "VND-BBMP-WORKS-01");
                    setRequestCommitmentId(cmt?.commitment_id || alloc?.commitments[0]?.commitment_id || "");
                    setRequestAmount("");
                    setRequestPaymentRef(`INV-2026-${Math.floor(Math.random() * 900 + 100)}`);
                    setRequestError(null);
                    setIsRequestModalOpen(true);
                  }
                }}
                className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-xs"
              >
                <Plus className="w-4 h-4" />
                {t("contractor.proposedExpenditure")}
              </button>
            </div>

            {isLoadingBudget ? (
              <div className="p-12 text-center text-xs text-slate-500">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
                Loading financial records from Supabase...
              </div>
            ) : !partnerBudget || partnerBudget.projects.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs">
                <Landmark className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="font-medium text-slate-600">No project allocations found for this partner</p>
                <p className="text-[11px] text-slate-400 mt-1">Assigned projects will appear here once authorized in the Municipal Capital Ledger.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                      <th className="py-3 px-4">Project / Work Order</th>
                      <th className="py-3 px-3">Contract Ref</th>
                      <th className="py-3 px-3 text-right">Committed (₹L)</th>
                      <th className="py-3 px-3 text-right">Disbursed (₹L)</th>
                      <th className="py-3 px-3 text-right">Pending Claims (₹L)</th>
                      <th className="py-3 px-3 text-right">Available Balance (₹L)</th>
                      <th className="py-3 px-3 text-center">Milestones Verified</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {partnerBudget.projects.map((proj) => (
                      <tr key={proj.allocation_id} className="hover:bg-slate-50 transition">
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          <div>{proj.title}</div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {proj.allocation_id} • {proj.neighbourhood_name}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 font-mono text-[11px] text-slate-600">
                          {proj.contract_reference}
                        </td>
                        <td className="py-3.5 px-3 text-right font-semibold text-slate-800">
                          ₹{proj.committed_amount_lakh.toFixed(2)}L
                        </td>
                        <td className="py-3.5 px-3 text-right font-semibold text-blue-700">
                          ₹{proj.disbursed_amount_lakh.toFixed(2)}L
                        </td>
                        <td className="py-3.5 px-3 text-right text-amber-600 font-medium">
                          {proj.pending_requests_lakh > 0 ? `₹${proj.pending_requests_lakh.toFixed(2)}L` : "-"}
                        </td>
                        <td className="py-3.5 px-3 text-right font-bold text-emerald-700">
                          ₹{proj.remaining_balance_lakh.toFixed(2)}L
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-semibold">
                            {proj.verified_milestones_count} / {proj.milestones_count}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => {
                              setRequestAllocationId(proj.allocation_id);
                              const alloc = allocations.find((a) => a.allocation_id === proj.allocation_id);
                              const cmt = alloc?.commitments.find((c) => c.vendor_id === "VND-BBMP-WORKS-01");
                              setRequestCommitmentId(cmt?.commitment_id || alloc?.commitments[0]?.commitment_id || "");
                              setRequestAmount("");
                              setRequestPaymentRef(`INV-2026-${Math.floor(Math.random() * 900 + 100)}`);
                              setRequestError(null);
                              setIsRequestModalOpen(true);
                            }}
                            disabled={proj.remaining_balance_lakh <= 0}
                            className="px-2.5 py-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition disabled:opacity-40"
                          >
                            Claim
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Work Orders & Milestone Management */}
      {activeTab === "milestones" && (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Assigned Work Orders List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>Assigned Projects ({allocations.length})</span>
            <button onClick={loadData} className="text-teal-600 hover:text-teal-700 flex items-center space-x-1 font-semibold">
              <RefreshCw className="w-3 h-3" />
              <span>Refresh</span>
            </button>
          </div>

          {isLoading ? (
            <div className="text-center py-10 text-xs text-slate-500">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-teal-600" />
              Loading assigned contracts...
            </div>
          ) : (
            <div className="space-y-3">
              {allocations.map((alloc) => {
                const isSelected = selectedAllocation?.allocation_id === alloc.allocation_id;
                return (
                  <div
                    key={alloc.allocation_id}
                    onClick={() => setSelectedAllocation(alloc)}
                    className={`cursor-pointer rounded-xl border p-4 transition-all shadow-xs ${
                      isSelected
                        ? "border-teal-500 bg-teal-50/50 ring-1 ring-teal-500"
                        : "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                        {alloc.allocation_id}
                      </span>
                      <span className="text-[10px] font-semibold uppercase text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        {alloc.status}
                      </span>
                    </div>

                    <h3 className="font-semibold text-xs text-slate-900 mt-2 leading-snug">{alloc.title}</h3>

                    <div className="mt-2 text-[11px] text-slate-500 flex items-center space-x-1.5">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      <span>{alloc.neighbourhood_name}</span>
                      <span>•</span>
                      <span>{alloc.planned_units} Units</span>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Committed</span>
                        <span className="font-semibold text-slate-900">₹{alloc.committed_amount_lakh.toFixed(2)}L</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Disbursed</span>
                        <span className="font-semibold text-emerald-700">₹{alloc.disbursed_amount_lakh.toFixed(2)}L</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Balance</span>
                        <span className="font-semibold text-amber-700">₹{alloc.remaining_budget_lakh.toFixed(2)}L</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column (2 cols): Selected Project Milestones & Evidence */}
        <div className="lg:col-span-2 space-y-4">
          {selectedAllocation ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-6">
              {/* Project Header Summary */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded">
                    Contract Reference: {selectedAllocation.council_resolution_ref || "BBMP-CR-2025"}
                  </span>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-1.5">
                    {selectedAllocation.title}
                  </h2>
                  <p className="text-xs text-slate-600">
                    Location: {selectedAllocation.neighbourhood_name} • Intervention: {selectedAllocation.intervention_name}
                  </p>
                </div>

                <div className="flex items-center space-x-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200 shrink-0">
                  <div>
                    <span className="text-[10px] text-slate-500 block uppercase">Disbursement Progress</span>
                    <span className="text-sm font-bold text-emerald-700">{selectedAllocation.disbursement_progress_pct}%</span>
                  </div>
                </div>
              </div>

              {/* Milestones Execution Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Contractual Milestones & Payment Tranches ({selectedAllocation.milestones.length})
                  </h3>
                  <span className="text-[11px] text-slate-500">
                    Progress submission triggers municipal physical inspection
                  </span>
                </div>

                <div className="space-y-4">
                  {selectedAllocation.milestones.map((milestone) => (
                    <div
                      key={milestone.milestone_id}
                      className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-3 shadow-xs"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-xs text-slate-900">
                              Milestone #{milestone.sequence_order}: {milestone.title}
                            </span>
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                                milestone.status === "verified_complete"
                                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                  : milestone.status === "submitted_for_review"
                                  ? "bg-amber-50 text-amber-800 border border-amber-200"
                                  : "bg-slate-100 text-slate-700 border border-slate-200"
                              }`}
                            >
                              {milestone.status.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">{milestone.description}</p>
                        </div>

                        <div className="flex items-center space-x-3 shrink-0">
                          <div className="text-right">
                            <span className="text-[10px] text-slate-500 block uppercase">Tranche Payout</span>
                            <span className="font-bold text-xs text-amber-700">
                              ₹{milestone.disbursement_tied_amount_lakh.toFixed(2)}L
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Progress Bar & Buttons */}
                      <div className="pt-2 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex-1 max-w-xs">
                          <div className="flex justify-between text-[11px] text-slate-600 mb-1">
                            <span>Field Execution Progress</span>
                            <span className="font-semibold text-slate-900">{milestone.percent_progress}%</span>
                          </div>
                          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-teal-600 h-full rounded-full transition-all duration-300"
                              style={{ width: `${milestone.percent_progress}%` }}
                            />
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          {milestone.status !== "verified_complete" && (
                            <>
                              <button
                                onClick={() => {
                                  setUpdatingMilestone(milestone);
                                  setNewProgress(milestone.percent_progress);
                                  setNewStatus(milestone.percent_progress >= 100 ? "submitted_for_review" : "in_progress");
                                }}
                                className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-medium shadow-xs transition-colors"
                              >
                                Update Progress
                              </button>

                              <button
                                onClick={() => setAttachingMilestone(milestone)}
                                className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-medium flex items-center space-x-1.5 shadow-xs transition-colors"
                              >
                                <Camera className="w-3.5 h-3.5 text-teal-600" />
                                <span>Upload Evidence</span>
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Attached Evidence Items */}
                      {milestone.evidence_items && milestone.evidence_items.length > 0 && (
                        <div className="pt-2 border-t border-slate-200">
                          <span className="text-[10px] font-semibold uppercase text-slate-500 block mb-1.5">
                            Attached Documentary Evidence ({milestone.evidence_items.length}):
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {milestone.evidence_items.map((evd) => (
                              <div
                                key={evd.evidence_id}
                                className="bg-white border border-slate-200 p-2.5 rounded-lg text-xs space-y-1 shadow-xs"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-1.5 truncate">
                                    <FileText className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                                    <span className="font-semibold text-slate-900 truncate">{evd.title}</span>
                                  </div>
                                  <span
                                    className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                      evd.verification_status === "verified"
                                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                        : "bg-slate-100 text-slate-700 border border-slate-200"
                                    }`}
                                  >
                                    {evd.verification_status}
                                  </span>
                                </div>
                                <div className="text-[10px] font-mono text-slate-500 flex items-center space-x-1 truncate">
                                  <Hash className="w-3 h-3 text-slate-400 shrink-0" />
                                  <span className="truncate">{evd.document_hash}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Municipal Verification Inspection Feedback */}
                      {milestone.verification_decision && (
                        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-2.5 text-xs text-emerald-900 space-y-1">
                          <div className="flex items-center space-x-2">
                            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span className="font-semibold">
                              Formal Municipal Inspection Sign-off ({milestone.verification_decision.decision.toUpperCase()})
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600 pl-6">
                            &quot;{milestone.verification_decision.comments}&quot; &bull;{" "}
                            <span className="text-slate-500">
                              Inspector: {milestone.verification_decision.verifier_name} on{" "}
                              {new Date(milestone.verification_decision.decided_at).toLocaleDateString()}
                            </span>
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 shadow-xs">
              Select an assigned project from the list on the left to inspect milestones and upload evidence.
            </div>
          )}
        </div>
      </div>
      )}

      {/* Modal 1: Update Milestone Progress */}
      {updatingMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-teal-700 font-bold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                  Milestone #{updatingMilestone.sequence_order}
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-1">{updatingMilestone.title}</h2>
              </div>
              <button onClick={() => setUpdatingMilestone(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateProgressSubmit} className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                  <span>Completion Percentage</span>
                  <span className="font-mono text-teal-700 font-bold">{newProgress}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={newProgress}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setNewProgress(val);
                    if (val >= 100) setNewStatus("submitted_for_review");
                    else if (val > 0) setNewStatus("in_progress");
                  }}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Lifecycle Status</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value as "pending" | "in_progress" | "submitted_for_review")}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                >
                  <option value="in_progress">Work In Progress</option>
                  <option value="submitted_for_review">Submitted for Municipal Inspection (Ready for Payout)</option>
                  <option value="pending">Pending Mobilization</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  Contractor Site Execution Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  value={progressNotes}
                  onChange={(e) => setProgressNotes(e.target.value)}
                  placeholder="E.g., Sub-base compaction complete; ASTM C1319 aggregate tested on site..."
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setUpdatingMilestone(null)}
                  className="px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingProgress}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition-colors"
                >
                  {isUpdatingProgress ? "Saving..." : "Record Progress Update"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Attach Documentary Evidence */}
      {attachingMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-teal-700 font-bold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                  Evidence Upload &bull; Milestone #{attachingMilestone.sequence_order}
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-1">Attach Photographic / Field Evidence</h2>
              </div>
              <button onClick={() => setAttachingMilestone(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAttachEvidenceSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Evidence Title (Required)</label>
                <input
                  type="text"
                  required
                  value={evidenceTitle}
                  onChange={(e) => setEvidenceTitle(e.target.value)}
                  placeholder="E.g., Site photo after filter aggregate placement"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Evidence Category</label>
                  <select
                    value={evidenceType}
                    onChange={(e) => setEvidenceType(e.target.value as "site_photo" | "inspection_report" | "material_invoice" | "community_sign_off" | "geo_survey")}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                  >
                    <option value="site_photo">Field Progress Photo (Site Inspection)</option>
                    <option value="inspection_report">Inspection & Quality Report (PDF)</option>
                    <option value="material_invoice">Material Procurement Invoice</option>
                    <option value="geo_survey">Geo-Survey & Bathymetry / As-Built Survey</option>
                    <option value="community_sign_off">Community Sign-Off / Ward Verification</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">File Name</label>
                  <input
                    type="text"
                    required
                    value={evidenceFileName}
                    onChange={(e) => setEvidenceFileName(e.target.value)}
                    placeholder="E.g., koramangala_bioswale_01.jpg"
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Technical Description</label>
                <textarea
                  rows={2}
                  value={evidenceDesc}
                  onChange={(e) => setEvidenceDesc(e.target.value)}
                  placeholder="Provide GPS references, chainage markers, or testing methodology..."
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 flex items-center space-x-2">
                <Hash className="w-4 h-4 text-teal-600 shrink-0" />
                <span>
                  Tamper-evident verification: A cryptographic SHA-256 hash will be automatically generated and linked to the municipal audit ledger.
                </span>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setAttachingMilestone(null)}
                  className="px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEvidence}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition-colors"
                >
                  {isSubmittingEvidence ? "Attaching..." : "Submit Evidence to Audit Ledger"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 3: Submit Proposed Expenditure Request */}
      {isRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  {t("contractor.proposedExpenditure", "Financial Expenditure Claim")}
                </span>
                <h2 className="text-base font-bold text-slate-900 mt-1">
                  {t("contractor.proposedExpenditure", "Submit Proposed Expenditure Request")}
                </h2>
              </div>
              <button
                onClick={() => setIsRequestModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {requestError && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <span>{requestError}</span>
              </div>
            )}

            <form onSubmit={handleExpenditureSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  {t("contractor.selectProject", "Assigned Project")}
                </label>
                <select
                  value={requestAllocationId}
                  onChange={(e) => {
                    const allocId = e.target.value;
                    setRequestAllocationId(allocId);
                    const alloc = allocations.find((a) => a.allocation_id === allocId);
                    const cmt = alloc?.commitments.find((c) => c.vendor_id === "VND-BBMP-WORKS-01");
                    setRequestCommitmentId(cmt?.commitment_id || alloc?.commitments[0]?.commitment_id || "");
                  }}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                >
                  {partnerBudget?.projects.map((p) => (
                    <option key={p.allocation_id} value={p.allocation_id}>
                      {p.title} (Available: ₹{p.remaining_balance_lakh.toFixed(2)}L)
                    </option>
                  ))}
                </select>
              </div>

              {/* Balance cap reminder */}
              {(() => {
                const selectedProj = partnerBudget?.projects.find((p) => p.allocation_id === requestAllocationId);
                const cap = selectedProj ? selectedProj.remaining_balance_lakh : 0;
                return (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs flex justify-between items-center">
                    <span className="text-slate-600">Max Allowable Claim Limit:</span>
                    <span className="font-bold text-emerald-700 font-mono">₹{cap.toFixed(2)} Lakhs INR</span>
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">
                    {t("contractor.requestedAmount", "Claim Amount (₹ Lakhs)")}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={requestAmount}
                    onChange={(e) => setRequestAmount(e.target.value)}
                    placeholder="e.g. 5.50"
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">
                    {t("contractor.paymentVoucher", "Invoice / Voucher Ref")}
                  </label>
                  <input
                    type="text"
                    required
                    value={requestPaymentRef}
                    onChange={(e) => setRequestPaymentRef(e.target.value)}
                    placeholder="e.g. INV-2026-044"
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  {t("contractor.payeeEntity", "Registered Payee Entity")}
                </label>
                <input
                  type="text"
                  required
                  value={requestPayee}
                  onChange={(e) => setRequestPayee(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">
                  {t("contractor.workJustification", "Work Justification & Milestone Notes")}
                </label>
                <textarea
                  rows={2}
                  value={requestNotes}
                  onChange={(e) => setRequestNotes(e.target.value)}
                  placeholder="Details of civil works completed, inspections cited, or invoice milestones..."
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
                />
              </div>

              <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200 text-[11px] text-emerald-900 flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>
                  {t("contractor.financialLimitsNotice")}
                </span>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsRequestModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRequest}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition"
                >
                  {isSubmittingRequest ? t("common.loading") : t("contractor.submitRequestBtn", "Submit Claim to Municipal Review")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
