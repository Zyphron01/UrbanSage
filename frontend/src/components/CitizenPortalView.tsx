"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  Compass,
  FileCheck2,
  MapPin,
  MessageSquareWarning,
  PlusCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  TreePine,
  UserCheck,
  X,
} from "lucide-react";
import {
  CitizenReportPublic,
  fetchAccountabilitySummary,
  fetchReports,
  ProblemCategory,
  PublicAccountabilitySummary,
  ReportStatus,
  verifyReportResolution,
} from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { ReportCard } from "./ReportCard";
import { ReportDetailModal } from "./ReportDetailModal";
import { ReportSubmitModal } from "./ReportSubmitModal";
import { RiskMapView } from "./RiskMapView";

export function CitizenPortalView() {
  const { t, language } = useLanguage();
  const [activeTab, setActiveTab] = useState<"track" | "verify" | "heatmap" | "public_ledger">("track");
  const [reports, setReports] = useState<CitizenReportPublic[]>([]);
  const [totalReports, setTotalReports] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<ProblemCategory | undefined>(undefined);
  const [selectedStatus, setSelectedStatus] = useState<ReportStatus | undefined>(undefined);

  // Modals
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(false);
  const [inspectedReport, setInspectedReport] = useState<CitizenReportPublic | null>(null);

  // Verification action modal state
  const [verifyingReport, setVerifyingReport] = useState<CitizenReportPublic | null>(null);
  const [verificationFeedback, setVerificationFeedback] = useState<string>("");
  const [isSubmittingVerification, setIsSubmittingVerification] = useState<boolean>(false);
  const [verificationSuccessMsg, setVerificationSuccessMsg] = useState<string | null>(null);

  // Public ledger summary
  const [publicLedger, setPublicLedger] = useState<PublicAccountabilitySummary | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState<boolean>(false);

  const loadReports = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchReports({
        category: selectedCategory,
        status: selectedStatus,
        limit: 50,
        offset: 0,
      });
      setReports(data.items);
      setTotalReports(data.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load reports from backend");
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, selectedStatus]);

  useEffect(() => {
    let isMounted = true;
    fetchReports({
      category: selectedCategory,
      status: selectedStatus,
      limit: 50,
      offset: 0,
    })
      .then((data) => {
        if (isMounted) {
          setReports(data.items);
          setTotalReports(data.total);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load reports from backend");
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [selectedCategory, selectedStatus]);

  useEffect(() => {
    if (activeTab === "public_ledger" && !publicLedger) {
      let isMounted = true;
      fetchAccountabilitySummary()
        .then((data) => {
          if (isMounted) {
            setPublicLedger(data);
            setLedgerLoading(false);
          }
        })
        .catch(() => {
          if (isMounted) {
            setLedgerLoading(false);
          }
        });
      return () => {
        isMounted = false;
      };
    }
  }, [activeTab, publicLedger]);

  const handleReportCreated = (newReport: CitizenReportPublic) => {
    setReports((prev) => [newReport, ...prev]);
    setTotalReports((prev) => prev + 1);
    setIsSubmitModalOpen(false);
  };

  const handleVerifySubmit = async (confirmedResolved: boolean) => {
    if (!verifyingReport) return;
    setIsSubmittingVerification(true);
    try {
      const updated = await verifyReportResolution(verifyingReport.id, {
        confirmed_resolved: confirmedResolved,
        feedback: verificationFeedback.trim() || undefined,
        actor_id: "CITIZEN-VERIFIER",
      });
      setVerificationSuccessMsg(
        confirmedResolved
          ? `Thank you! Resolution for ${updated.id} confirmed and officially marked as verified.`
          : `Dispute logged for ${updated.id}. Report returned to municipal queue under review.`
      );
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setVerifyingReport(null);
      setVerificationFeedback("");
      setTimeout(() => setVerificationSuccessMsg(null), 6000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to submit verification");
    } finally {
      setIsSubmittingVerification(false);
    }
  };

  const filteredReports = reports.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.id.toLowerCase().includes(q) ||
      r.description.toLowerCase().includes(q) ||
      (r.location_description && r.location_description.toLowerCase().includes(q))
    );
  });

  const awaitingVerificationReports = reports.filter(
    (r) => r.status === "completed_awaiting_verification" || r.status === "in_progress" || r.status === "assigned"
  );

  return (
    <div className="space-y-6">
      {/* Citizen Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
              <UserCheck className="w-3.5 h-3.5" />
              <span>{t("citizen.publicBadge", "Public Citizen Portal")}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {t("citizen.bannerTitle", "Report Issues, Track Progress & Verify Resolution")}
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {t("citizen.bannerSubtitle", "Empowering Bengaluru residents to report flooding, heat hotspots, water scarcity, and tree canopy loss. Every submission is scored transparently for operational urgency and monitored until you confirm physical resolution.")}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Link
              href="/citizen/report"
              className="flex items-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <PlusCircle className="w-4 h-4" />
              <span>{t("citizen.reportIssueBtn", "Report an Issue")}</span>
            </Link>
            <button
              onClick={() => setActiveTab("track")}
              className="flex items-center space-x-2 rounded-xl bg-white hover:bg-slate-50 px-4 py-2.5 text-xs font-medium text-slate-700 border border-slate-300 transition-colors shadow-xs"
            >
              <Search className="w-4 h-4 text-teal-600" />
              <span>{t("citizen.trackTicketsBtn", "Track Tickets")}</span>
            </button>
            <Link
              href="/citizen/login"
              className="flex items-center space-x-1.5 rounded-xl bg-white hover:bg-slate-50 px-3.5 py-2.5 text-xs font-medium text-emerald-700 border border-slate-300 hover:border-emerald-500 transition-colors shadow-xs"
            >
              <UserCheck className="w-4 h-4" />
              <span>{t("nav.signIn", "Sign In")}</span>
            </Link>
          </div>
        </div>

        {/* Privacy & Provenance Disclosure */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-4 text-[11px] text-slate-500">
          <div className="flex items-center space-x-1.5 text-emerald-700 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{t("citizen.privacyGuaranteed", "Privacy Guaranteed: Contact details are permanently redacted from public views.")}</span>
          </div>
          <span>•</span>
          <div className="flex items-center space-x-1.5 text-amber-700">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>{t("citizen.telemetryIsolation", "Citizen observations are isolated from municipal telemetry until field audit.")}</span>
          </div>
        </div>
      </div>

      {/* Success Notification */}
      {verificationSuccessMsg && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{verificationSuccessMsg}</span>
          </div>
          <button onClick={() => setVerificationSuccessMsg(null)} className="text-slate-400 hover:text-slate-700">
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
          <button onClick={() => loadReports()} className="underline hover:text-rose-950 font-semibold">
            Retry
          </button>
        </div>
      )}

      {/* Citizen Tab Navigation */}
      <div className="flex border-b border-slate-200 space-x-2 sm:space-x-4 overflow-x-auto pb-1 text-xs font-medium">
        <button
          onClick={() => setActiveTab("track")}
          className={`flex items-center space-x-2 py-2 px-3 rounded-lg transition-all ${
            activeTab === "track"
              ? "bg-slate-100 text-slate-900 border border-slate-300 font-semibold shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <Search className="w-4 h-4 text-teal-600" />
          <span>{t("citizen.tabBrowse", "Browse & Track Reports")} ({totalReports})</span>
        </button>

        <button
          onClick={() => setActiveTab("verify")}
          className={`flex items-center space-x-2 py-2 px-3 rounded-lg transition-all ${
            activeTab === "verify"
              ? "bg-slate-100 text-slate-900 border border-slate-300 font-semibold shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <FileCheck2 className="w-4 h-4 text-amber-600" />
          <span>{t("citizen.tabVerify", "Resolution Sign-Off")} ({awaitingVerificationReports.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("heatmap")}
          className={`flex items-center space-x-2 py-2 px-3 rounded-lg transition-all ${
            activeTab === "heatmap"
              ? "bg-slate-100 text-slate-900 border border-slate-300 font-semibold shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <Compass className="w-4 h-4 text-emerald-600" />
          <span>{t("citizen.tabMap", "City Environmental Map")}</span>
        </button>

        <button
          onClick={() => setActiveTab("public_ledger")}
          className={`flex items-center space-x-2 py-2 px-3 rounded-lg transition-all ${
            activeTab === "public_ledger"
              ? "bg-slate-100 text-slate-900 border border-slate-300 font-semibold shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          <TreePine className="w-4 h-4 text-emerald-600" />
          <span>{t("citizen.tabLedger", "Public Green Spending")}</span>
        </button>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* TAB 1: BROWSE & TRACK REPORTS                                 */}
      {/* ------------------------------------------------------------- */}
      {activeTab === "track" && (
        <div className="space-y-4">
          {/* Search & Category Filter Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <div className="relative sm:col-span-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("citizen.searchPlaceholder", "Search ticket ID or landmark...")}
                className="w-full bg-white border border-slate-300 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
              />
            </div>

            <div>
              <select
                value={selectedCategory || ""}
                onChange={(e) => setSelectedCategory(e.target.value ? (e.target.value as ProblemCategory) : undefined)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
              >
                <option value="">{t("citizen.allCategories", "All Problem Categories")}</option>
                <option value="flooding_drainage">{t("category.flooding_drainage", "Flooding & Drainage")}</option>
                <option value="water_scarcity">{t("category.water_scarcity", "Water Scarcity")}</option>
                <option value="heat">{t("category.heat", "Urban Heat Island")}</option>
                <option value="loss_of_green_cover">{t("category.loss_of_green_cover", "Loss of Green Cover")}</option>
              </select>
            </div>

            <div>
              <select
                value={selectedStatus || ""}
                onChange={(e) => setSelectedStatus(e.target.value ? (e.target.value as ReportStatus) : undefined)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
              >
                <option value="">{t("citizen.allStatuses", "All Lifecycle Statuses")}</option>
                <option value="submitted">{t("status.submitted", "Submitted (Pending Triage)")}</option>
                <option value="under_review">{t("status.under_review", "Under Municipal Review")}</option>
                <option value="assigned">{t("status.assigned", "Assigned to Contractor")}</option>
                <option value="in_progress">{t("status.in_progress", "Work In Progress")}</option>
                <option value="completed_awaiting_verification">{t("status.completed_awaiting_verification", "Awaiting Citizen Verification")}</option>
                <option value="verified_resolved">{t("status.verified_resolved", "Verified & Resolved")}</option>
              </select>
            </div>
          </div>

          {/* Report Feed Cards */}
          {isLoading ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
              {t("common.loading", "Loading citizen reports...")}
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="text-center py-12 rounded-xl border border-dashed border-slate-200 bg-white text-slate-500">
              <MessageSquareWarning className="w-8 h-8 mx-auto mb-2 text-slate-400" />
              <p className="text-sm font-medium text-slate-700">{t("citizen.noReportsMatching", "No reports matching your criteria")}</p>
              <button
                onClick={() => setIsSubmitModalOpen(true)}
                className="mt-3 text-xs text-emerald-600 hover:text-emerald-700 hover:underline font-semibold"
              >
                + {t("citizen.submitNewReport", "Submit the first report for this category")}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredReports.map((report) => (
                <div key={report.id} onClick={() => setInspectedReport(report)} className="cursor-pointer">
                  <ReportCard report={report} onInspect={(r) => setInspectedReport(r)} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* TAB 2: RESOLUTION SIGN-OFF & CITIZEN AUDIT                    */}
      {/* ------------------------------------------------------------- */}
      {activeTab === "verify" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
            <h3 className="font-bold flex items-center space-x-2 text-sm text-amber-800 mb-1">
              <FileCheck2 className="w-4 h-4 text-amber-600" />
              <span>{t("citizen.signOffBannerTitle", "Independent Citizen Sign-Off Power")}</span>
            </h3>
            <p className="text-slate-600 text-xs leading-relaxed">
              {t("citizen.signOffBannerDesc", "Contractors cannot declare a project complete unilaterally. When work is finished, the ticket enters Completed Awaiting Verification. Citizens must review the work notes and photos to either confirm satisfactory remediation or dispute it back to the municipal queue.")}
            </p>
          </div>

          <div className="space-y-3">
            {awaitingVerificationReports.map((report) => (
              <div
                key={report.id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded">{report.id}</span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                        report.status === "completed_awaiting_verification"
                          ? "bg-amber-50 text-amber-800 border border-amber-200"
                          : "bg-slate-100 text-slate-700 border border-slate-200"
                      }`}
                    >
                      {report.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-slate-800 font-medium">{report.description}</p>
                  <div className="text-[11px] text-slate-500 flex items-center space-x-2">
                    <MapPin className="w-3 h-3 text-slate-400" />
                    <span>{report.location_description || `${report.latitude.toFixed(4)}°, ${report.longitude.toFixed(4)}°`}</span>
                    <span>•</span>
                    <span>{t("citizen.urgencyScore", "Urgency")}: {report.urgency_score.toFixed(1)}/100</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => setInspectedReport(report)}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium border border-slate-200 transition-colors"
                  >
                    {t("common.viewDetails", "View Details")}
                  </button>
                  {report.status === "completed_awaiting_verification" && (
                    <button
                      onClick={() => setVerifyingReport(report)}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs transition-colors"
                    >
                      {t("citizen.tabVerify", "Sign Off / Dispute")}
                    </button>
                  )}
                </div>
              </div>
            ))}

            {awaitingVerificationReports.length === 0 && (
              <div className="text-center py-10 rounded-xl border border-dashed border-slate-200 bg-white text-slate-500 text-xs">
                {t("citizen.noAwaitingTickets", "No tickets currently awaiting citizen sign-off.")}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* TAB 3: CITY ENVIRONMENTAL RISK HEATMAP                        */}
      {/* ------------------------------------------------------------- */}
      {activeTab === "heatmap" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                {t("citizen.mapTitle", "Public Ward Environmental Vulnerability Heatmap")}
              </h2>
              <p className="text-xs text-slate-600">
                {t("citizen.mapSubtitle", "Transparent risk baselines across flooding, heat islands, water stress, and green deficit.")}
              </p>
            </div>
          </div>
          <RiskMapView reports={reports} />
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* TAB 4: PUBLIC GREEN LEDGER (TRANSPARENCY SUMMARY)             */}
      {/* ------------------------------------------------------------- */}
      {activeTab === "public_ledger" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <h3 className="font-bold text-sm text-emerald-900 mb-1">
              {t("citizen.ledgerTitle", "Public Sustainability Expenditure Transparency")}
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              {t("citizen.ledgerSubtitle", "UrbanSage AI ensures complete fiscal transparency. Citizens can track how municipal capital is allocated to bioswales, Miyawaki forests, permeable pavements, and flood prevention projects across Bengaluru wards.")}
            </p>
          </div>

          {ledgerLoading ? (
            <div className="text-center py-10 text-xs text-slate-500">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-600" />
              {t("common.loading", "Loading public financial ledger...")}
            </div>
          ) : publicLedger ? (
            <div className="space-y-6">
              {/* Top KPI Ribbon */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <span className="text-[10px] font-semibold uppercase text-slate-500 block">{t("citizen.totalAuthorized", "Total Authorized")}</span>
                  <span className="text-xl font-bold font-mono text-slate-900 mt-1 block">
                    ₹{publicLedger.total_allocated_lakh.toFixed(2)}L
                  </span>
                  <span className="text-[10px] text-slate-500">{t("citizen.fiscalYear", "Fiscal Year")} {publicLedger.fiscal_year}</span>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <span className="text-[10px] font-semibold uppercase text-slate-500 block">{t("citizen.fundsDisbursed", "Funds Disbursed")}</span>
                  <span className="text-xl font-bold font-mono text-emerald-700 mt-1 block">
                    ₹{publicLedger.total_disbursed_lakh.toFixed(2)}L
                  </span>
                  <span className="text-[10px] text-emerald-600">{t("citizen.tiedMilestones", "Tied to verified milestones")}</span>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <span className="text-[10px] font-semibold uppercase text-slate-500 block">{t("citizen.remainingCapital", "Remaining Capital")}</span>
                  <span className="text-xl font-bold font-mono text-teal-700 mt-1 block">
                    ₹{publicLedger.total_remaining_lakh.toFixed(2)}L
                  </span>
                  <span className="text-[10px] text-slate-500">{t("citizen.lockedPending", "Locked pending completion")}</span>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <span className="text-[10px] font-semibold uppercase text-slate-500 block">{t("citizen.verifiedMilestones", "Verified Milestones")}</span>
                  <span className="text-xl font-bold font-mono text-amber-700 mt-1 block">
                    {publicLedger.completed_milestones_count} / {publicLedger.completed_milestones_count + publicLedger.pending_milestones_count}
                  </span>
                  <span className="text-[10px] text-slate-500">{t("citizen.physicallyInspected", "Physically inspected by engineers")}</span>
                </div>
              </div>

              {/* Breakdown by Neighborhood */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {t("citizen.wardAllocations", "Ward-Level Green Infrastructure Allocations")}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {publicLedger.by_neighbourhood.map((ward) => (
                    <div key={ward.neighbourhood_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-slate-900">{ward.neighbourhood_name}</span>
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{ward.neighbourhood_id}</span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-600">
                        <span>Projects:</span>
                        <span className="font-semibold text-slate-900">{ward.project_count}</span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-600">
                        <span>Authorized Capital:</span>
                        <span className="font-semibold text-emerald-700">₹{ward.allocated_lakh.toFixed(2)}L</span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-600">
                        <span>Disbursed Payout:</span>
                        <span className="font-semibold text-teal-700">₹{ward.disbursed_lakh.toFixed(2)}L</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Citizen Resolution Verification / Dispute Modal */}
      {verifyingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="font-mono text-xs text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">{verifyingReport.id}</span>
                <h2 className="text-base font-bold text-slate-900 mt-1">{t("citizen.modalSignOffTitle", "Citizen Resolution Sign-Off")}</h2>
              </div>
              <button onClick={() => setVerifyingReport(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              The municipal contractor has marked the issue at{" "}
              <strong>{verifyingReport.location_description || "the reported location"}</strong> as complete.
              Please inspect the physical site and indicate whether the condition has been resolved satisfactorily.
            </p>

            <div>
              <label className="text-xs font-medium text-slate-700 block mb-1">
                Citizen Feedback or Site Observations (Optional)
              </label>
              <textarea
                rows={3}
                value={verificationFeedback}
                onChange={(e) => setVerificationFeedback(e.target.value)}
                placeholder={t("citizen.feedbackPlaceholder", "E.g., Drain desilted cleanly; water no longer accumulates on road...")}
                className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-100">
              <button
                type="button"
                disabled={isSubmittingVerification}
                onClick={() => handleVerifySubmit(false)}
                className="px-3.5 py-2 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 text-xs font-semibold disabled:opacity-50 transition-colors"
              >
                {t("citizen.disputeProblemPersists", "Dispute (Problem Persists)")}
              </button>
              <button
                type="button"
                disabled={isSubmittingVerification}
                onClick={() => handleVerifySubmit(true)}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition-colors"
              >
                {isSubmittingVerification ? "Recording..." : t("citizen.confirmSatisfied", "Confirm Resolution Satisfied")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Submit Modal */}
      <ReportSubmitModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onSuccess={handleReportCreated}
      />

      {/* Report Detail Modal */}
      <ReportDetailModal
        report={inspectedReport}
        onClose={() => setInspectedReport(null)}
      />
    </div>
  );
}
