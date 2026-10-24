"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Droplets,
  Flame,
  Globe2,
  Layers,
  MapPin,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  TreePine,
  Waves,
  Zap,
} from "lucide-react";
import {
  BriefReportItem,
  CitizenReportPublic,
  DecisionBriefResponse,
  fetchDecisionBrief,
  fetchGeographicRisk,
  fetchPriorityQueue,
  GeographicRiskResponse,
  PriorityQueueResponse,
  ProblemCategory,
  ReportStatus,
} from "@/lib/api";
import { ReportDetailModal } from "./ReportDetailModal";
import { HeroBackground } from "@/components/ui/tweenly-hero-background";
import { useLanguage } from "@/lib/i18n";

interface OverviewViewProps {
  reports: CitizenReportPublic[];
  onNavigateToReports: (category?: ProblemCategory, status?: ReportStatus) => void;
  onNavigateToRiskMap: () => void;
  onNavigateToOptimizer: () => void;
}

export function OverviewView({
  reports,
  onNavigateToReports,
  onNavigateToRiskMap,
  onNavigateToOptimizer,
}: OverviewViewProps) {
  const { t } = useLanguage();
  // Decision Brief State
  const [brief, setBrief] = useState<DecisionBriefResponse | null>(null);
  const [briefLoading, setBriefLoading] = useState<boolean>(true);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [briefRefreshKey, setBriefRefreshKey] = useState<number>(0);
  const [activeBriefTab, setActiveBriefTab] = useState<
    "high_urgency" | "overdue" | "failed_verification" | "awaiting_verification" | "awaiting_review" | "activity"
  >("high_urgency");

  // Priority Review Queue State
  const [queueData, setQueueData] = useState<PriorityQueueResponse | null>(null);
  const [queueLoading, setQueueLoading] = useState<boolean>(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueRefreshKey, setQueueRefreshKey] = useState<number>(0);
  const [queueSortBy, setQueueSortBy] = useState<string>("urgency_desc");
  const [queueStatus, setQueueStatus] = useState<ReportStatus | undefined>(undefined);
  const [queueCategory, setQueueCategory] = useState<ProblemCategory | undefined>(undefined);
  const [queuePage, setQueuePage] = useState<number>(0);
  const pageSize = 10;

  // Geographic Risk State
  const [geoRisk, setGeoRisk] = useState<GeographicRiskResponse | null>(null);
  const [geoLoading, setGeoLoading] = useState<boolean>(true);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [geoRefreshKey, setGeoRefreshKey] = useState<number>(0);
  const [geoTimeWindow, setGeoTimeWindow] = useState<number | undefined>(undefined);
  const [geoCategory, setGeoCategory] = useState<ProblemCategory | undefined>(undefined);

  // Inspected report modal
  const [inspectedReport, setInspectedReport] = useState<CitizenReportPublic | null>(null);

  // Load Decision Brief
  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchDecisionBrief(48);
        if (!ignore) {
          setBrief(data);
          setBriefError(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load decision brief";
          setBriefError(msg);
        }
      } finally {
        if (!ignore) {
          setBriefLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [briefRefreshKey]);

  // Load Priority Review Queue
  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchPriorityQueue({
          status: queueStatus,
          category: queueCategory,
          sort_by: queueSortBy,
          limit: pageSize,
          offset: queuePage * pageSize,
        });
        if (!ignore) {
          setQueueData(data);
          setQueueError(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load priority review queue";
          setQueueError(msg);
        }
      } finally {
        if (!ignore) {
          setQueueLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [queueStatus, queueCategory, queueSortBy, queuePage, queueRefreshKey]);

  // Load Geographic Risk Summary
  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchGeographicRisk(geoTimeWindow, geoCategory);
        if (!ignore) {
          setGeoRisk(data);
          setGeoError(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load geographic risk metrics";
          setGeoError(msg);
        }
      } finally {
        if (!ignore) {
          setGeoLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [geoTimeWindow, geoCategory, geoRefreshKey]);

  const refreshAll = () => {
    setBriefLoading(true);
    setQueueLoading(true);
    setGeoLoading(true);
    setBriefRefreshKey((k) => k + 1);
    setQueueRefreshKey((k) => k + 1);
    setGeoRefreshKey((k) => k + 1);
  };

  // Convert brief item to CitizenReportPublic for modal inspection
  const inspectBriefItem = (item: BriefReportItem) => {
    const reportModel: CitizenReportPublic = {
      id: item.id,
      category: item.category,
      description: item.description,
      severity: item.severity,
      latitude: item.latitude,
      longitude: item.longitude,
      location_description: item.location_description,
      neighbourhood_id: item.neighbourhood_id,
      photos: [],
      status: item.status,
      verification_status: "unverified",
      is_verified_measurement: false,
      data_source: "CITIZEN_REPORT",
      urgency_score: item.urgency_score,
      evidence_confidence_score: item.evidence_confidence_score,
      created_at: item.created_at,
      updated_at: item.created_at,
    };
    setInspectedReport(reportModel);
  };

  // Helper formatting for category badge
  const renderCategoryBadge = (cat: ProblemCategory) => {
    switch (cat) {
      case "flooding_drainage":
        return (
          <span className="inline-flex items-center space-x-1 rounded bg-cyan-50 px-2 py-0.5 text-[10px] font-semibold text-cyan-800 border border-cyan-200">
            <Waves className="w-3 h-3 shrink-0" />
            <span>Flooding</span>
          </span>
        );
      case "water_scarcity":
        return (
          <span className="inline-flex items-center space-x-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-800 border border-blue-200">
            <Droplets className="w-3 h-3 shrink-0" />
            <span>Water Scarcity</span>
          </span>
        );
      case "heat":
        return (
          <span className="inline-flex items-center space-x-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800 border border-amber-200">
            <Flame className="w-3 h-3 shrink-0" />
            <span>Heat Island</span>
          </span>
        );
      case "loss_of_green_cover":
        return (
          <span className="inline-flex items-center space-x-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 border border-emerald-200">
            <TreePine className="w-3 h-3 shrink-0" />
            <span>Green Cover</span>
          </span>
        );
    }
  };

  // Helper for status badge
  const renderStatusBadge = (status: ReportStatus) => {
    const formatted = status.replace(/_/g, " ");
    let colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
    if (status === "submitted" || status === "under_review") {
      colorClasses = "bg-amber-50 text-amber-800 border-amber-200";
    } else if (status === "assigned" || status === "in_progress") {
      colorClasses = "bg-blue-50 text-blue-800 border-blue-200";
    } else if (status === "completed_awaiting_verification") {
      colorClasses = "bg-purple-50 text-purple-800 border-purple-200";
    } else if (status === "verification_failed") {
      colorClasses = "bg-rose-50 text-rose-800 border-rose-200";
    } else if (status === "verified_resolved" || status === "resolved") {
      colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
    }

    return (
      <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider border ${colorClasses}`}>
        {formatted}
      </span>
    );
  };

  return (
    <div className="space-y-8">
      {/* ========================================================================= */}
      {/* 0. HERO BANNER WITH TWEENLY ANIMATED BACKGROUND                            */}
      {/* ========================================================================= */}
      <section
        aria-label="UrbanSage AI Hero"
        className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-8 sm:p-12 shadow-xs"
      >
        <HeroBackground
          variant="particles"
          mask="radial"
          accent="#10b981"
          color="#0d9488"
          density={0.5}
          opacity={0.15}
          speed={0.4}
          interactive={true}
          className="absolute inset-0 z-0 pointer-events-none"
        />

        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-emerald-800">
            <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
            <span>{t("overview.heroBadge", "URBANSAGE AI")}</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-slate-900 leading-tight">
            {t("overview.heroTitle", "Intelligent Decisions for")}{" "}
            <span className="bg-gradient-to-r from-emerald-600 via-teal-600 to-teal-700 bg-clip-text text-transparent">
              {t("overview.heroHighlight", "Sustainable Cities.")}
            </span>
          </h1>

          <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
            {t("overview.heroSubtitle", "Turn environmental signals and citizen reports into transparent, equitable, data-informed urban interventions.")}
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigateToRiskMap()}
              className="inline-flex items-center space-x-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 px-5 py-2.5 text-sm font-semibold text-white shadow-xs transition-all hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
            >
              <span>{t("overview.exploreInsights", "Explore Urban Insights")}</span>
              <ArrowRight className="w-4 h-4 shrink-0" />
            </button>

            <button
              onClick={() => {
                const el = document.getElementById("decision-brief-section");
                if (el) {
                  el.scrollIntoView({ behavior: "smooth" });
                }
              }}
              className="inline-flex items-center space-x-2 rounded-xl border border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50 px-5 py-2.5 text-sm font-medium text-slate-700 shadow-xs transition-all focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer"
            >
              <span>{t("overview.viewDashboard", "View City Dashboard")}</span>
            </button>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 1. MUNICIPAL DAILY DECISION BRIEF BANNER                                   */}
      {/* ========================================================================= */}
      <section id="decision-brief-section" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-ping" />
              <h1 className="text-base font-black uppercase tracking-wider text-slate-900">
                {t("overview.briefHeader", "Municipal Administrator Intelligence • Daily Decision Brief")}
              </h1>
              <span className="rounded bg-teal-50 text-teal-800 border border-teal-200 px-2 py-0.5 text-[10px] font-mono">
                {t("overview.briefLive", "Live Data")}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated operational aggregation &bull; Overdue threshold: <strong>&gt;48 hours</strong> &bull; Generated:{" "}
              <span className="font-mono text-slate-700">
                {brief?.generated_at ? new Date(brief.generated_at).toLocaleTimeString() : "Syncing..."}
              </span>
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={refreshAll}
              disabled={briefLoading || queueLoading || geoLoading}
              className="flex items-center space-x-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 px-3 py-1.5 text-xs text-slate-700 shadow-xs transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${(briefLoading || queueLoading || geoLoading) ? "animate-spin" : ""}`} />
              <span>{t("overview.refreshTelemetry", "Refresh Telemetry")}</span>
            </button>
          </div>
        </div>

        {briefError && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{briefError}</span>
            </div>
            <button onClick={() => setBriefRefreshKey((k) => k + 1)} className="text-rose-950 underline font-semibold">
              Retry
            </button>
          </div>
        )}

        {/* Operational Metrics Ribbon */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Total Reports */}
          <div
            onClick={() => onNavigateToReports()}
            className="cursor-pointer bg-white rounded-xl p-3 border border-slate-200 hover:border-slate-300 shadow-xs transition-colors group"
          >
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.totalReports", "Total Reports")}</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="text-xl font-bold font-mono text-slate-900 mt-1">
              {brief ? brief.summary.total_reports : reports.length}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">All-time submissions</div>
          </div>

          {/* Active Reports */}
          <div
            onClick={() => onNavigateToReports(undefined, "submitted")}
            className="cursor-pointer bg-white rounded-xl p-3 border border-slate-200 hover:border-slate-300 shadow-xs transition-colors group"
          >
            <div className="text-[10px] font-semibold text-blue-700 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.activeWorkOrders", "Active Queue")}</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="text-xl font-bold font-mono text-blue-800 mt-1">
              {brief ? brief.summary.active_reports : "..."}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">In operational pipeline</div>
          </div>

          {/* High Urgency */}
          <div
            onClick={() => setActiveBriefTab("high_urgency")}
            className={`cursor-pointer rounded-xl p-3 border transition-colors shadow-xs ${
              activeBriefTab === "high_urgency"
                ? "bg-rose-50/60 border-rose-400 ring-1 ring-rose-400"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="text-[10px] font-semibold text-rose-700 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.criticalUrgency", "High Urgency")}</span>
              <Zap className="w-3.5 h-3.5 text-rose-600" />
            </div>
            <div className="text-xl font-bold font-mono text-rose-800 mt-1">
              {brief ? brief.summary.high_urgency_active_count : "..."}
            </div>
            <div className="text-[10px] text-rose-700/80 mt-0.5">Score &ge; 70 / 100</div>
          </div>

          {/* Overdue */}
          <div
            onClick={() => setActiveBriefTab("overdue")}
            className={`cursor-pointer rounded-xl p-3 border transition-colors shadow-xs ${
              activeBriefTab === "overdue"
                ? "bg-amber-50/60 border-amber-400 ring-1 ring-amber-400"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.overdue", "Overdue (>48h)")}</span>
              <Clock className="w-3.5 h-3.5 text-amber-600" />
            </div>
            <div className="text-xl font-bold font-mono text-amber-800 mt-1">
              {brief ? brief.summary.overdue_active_count : "..."}
            </div>
            <div className="text-[10px] text-amber-700/80 mt-0.5">Requires escalation</div>
          </div>

          {/* Citizen Disputed / Failed */}
          <div
            onClick={() => setActiveBriefTab("failed_verification")}
            className={`cursor-pointer rounded-xl p-3 border transition-colors shadow-xs ${
              activeBriefTab === "failed_verification"
                ? "bg-red-50/60 border-red-400 ring-1 ring-red-400"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="text-[10px] font-semibold text-red-700 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.failedSignOff", "Failed Sign-Off")}</span>
              <RotateCcw className="w-3.5 h-3.5 text-red-600" />
            </div>
            <div className="text-xl font-bold font-mono text-red-800 mt-1">
              {brief ? brief.summary.verification_failed_count : "..."}
            </div>
            <div className="text-[10px] text-red-700/80 mt-0.5">Citizen disputed fix</div>
          </div>

          {/* Awaiting Citizen Verification */}
          <div
            onClick={() => setActiveBriefTab("awaiting_verification")}
            className={`cursor-pointer rounded-xl p-3 border transition-colors shadow-xs ${
              activeBriefTab === "awaiting_verification"
                ? "bg-purple-50/60 border-purple-400 ring-1 ring-purple-400"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="text-[10px] font-semibold text-purple-700 uppercase tracking-wider flex items-center justify-between">
              <span>{t("overview.awaitingSignOff", "Awaiting Sign-Off")}</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-purple-600" />
            </div>
            <div className="text-xl font-bold font-mono text-purple-800 mt-1">
              {brief ? brief.summary.awaiting_citizen_verification_count : "..."}
            </div>
            <div className="text-[10px] text-purple-700/80 mt-0.5">Work completed</div>
          </div>
        </div>

        {/* Priority Brief Radar Items Table / Stream */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="border-b border-slate-100 bg-slate-50 px-4 py-2.5 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("overview.actionRadar", "Action Radar Priority Queue")}
              </span>
              <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-mono text-slate-700">
                {activeBriefTab.replace("_", " ")}
              </span>
            </div>

            {/* Sub-Tabs for Brief */}
            <div className="flex items-center space-x-1 text-xs">
              <button
                onClick={() => setActiveBriefTab("high_urgency")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "high_urgency"
                    ? "bg-rose-100 text-rose-800 border border-rose-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {t("overview.subtabCritical", "Critical")} ({brief?.high_urgency_items.length || 0})
              </button>
              <button
                onClick={() => setActiveBriefTab("overdue")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "overdue"
                    ? "bg-amber-100 text-amber-800 border border-amber-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {t("overview.subtabOverdue", "Overdue")} ({brief?.overdue_items.length || 0})
              </button>
              <button
                onClick={() => setActiveBriefTab("failed_verification")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "failed_verification"
                    ? "bg-red-100 text-red-800 border border-red-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {t("overview.subtabDisputed", "Disputed")} ({brief?.failed_verification_items.length || 0})
              </button>
              <button
                onClick={() => setActiveBriefTab("awaiting_verification")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "awaiting_verification"
                    ? "bg-purple-100 text-purple-800 border border-purple-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {t("overview.subtabAwaiting", "Awaiting Sign-off")} ({brief?.awaiting_citizen_verification_items.length || 0})
              </button>
              <button
                onClick={() => setActiveBriefTab("awaiting_review")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "awaiting_review"
                    ? "bg-amber-100 text-amber-800 border border-amber-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Awaiting Review ({brief?.awaiting_review_items.length || 0})
              </button>
              <button
                onClick={() => setActiveBriefTab("activity")}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  activeBriefTab === "activity"
                    ? "bg-blue-100 text-blue-800 border border-blue-300 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Audit Trail ({brief?.recent_activity.length || 0})
              </button>
            </div>
          </div>

          {/* Active Tab Content */}
          <div className="p-4">
            {briefLoading ? (
              <div className="py-8 text-center text-xs text-slate-500 animate-pulse">
                Aggregating municipal telemetry and priority items...
              </div>
            ) : activeBriefTab === "activity" ? (
              <div className="space-y-2">
                {brief?.recent_activity && brief.recent_activity.length > 0 ? (
                  brief.recent_activity.map((act, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg bg-slate-50 border border-slate-200 p-2.5 flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-900 capitalize">
                            {act.actor_role} Transition
                          </span>
                          <span className="text-slate-400">&bull;</span>
                          <span className="text-slate-600 font-mono text-[11px]">
                            {act.from_status} &rarr; {act.to_status}
                          </span>
                        </div>
                        {act.reason && <p className="text-[11px] text-slate-600">{act.reason}</p>}
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(act.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6 text-xs text-slate-500">No recent activity logs recorded.</div>
                )}
              </div>
            ) : (
              (() => {
                let itemsToShow: BriefReportItem[] = [];
                if (activeBriefTab === "high_urgency") itemsToShow = brief?.high_urgency_items || [];
                else if (activeBriefTab === "overdue") itemsToShow = brief?.overdue_items || [];
                else if (activeBriefTab === "failed_verification") itemsToShow = brief?.failed_verification_items || [];
                else if (activeBriefTab === "awaiting_verification") itemsToShow = brief?.awaiting_citizen_verification_items || [];
                else if (activeBriefTab === "awaiting_review") itemsToShow = brief?.awaiting_review_items || [];

                if (itemsToShow.length === 0) {
                  return (
                    <div className="text-center py-8 text-xs text-slate-500">
                      No reports currently match this operational triage category.
                    </div>
                  );
                }

                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {itemsToShow.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => inspectBriefItem(item)}
                        className="rounded-xl bg-white border border-slate-200 hover:border-slate-300 p-3.5 flex flex-col justify-between space-y-2.5 transition-colors cursor-pointer group shadow-xs hover:shadow-sm"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-mono text-xs font-bold text-teal-700 group-hover:underline">
                                {item.id}
                              </span>
                              {renderCategoryBadge(item.category)}
                              {renderStatusBadge(item.status)}
                            </div>
                            <p className="text-xs text-slate-800 line-clamp-2 leading-relaxed">
                              {item.description}
                            </p>
                          </div>

                          <div className="text-right shrink-0">
                            <div className="text-base font-bold font-mono text-rose-600">
                              {item.urgency_score.toFixed(1)}
                            </div>
                            <div className="text-[9px] text-slate-500 uppercase tracking-wider">
                              Urgency Score
                            </div>
                          </div>
                        </div>

                        {/* Prioritization Reason Banner */}
                        <div className="rounded-lg bg-slate-50 border border-slate-200 px-2.5 py-1.5 text-[11px] text-slate-700 flex items-center justify-between">
                          <span className="truncate pr-2">
                            <strong className="text-slate-900">Reason:</strong> {item.prioritization_reason}
                          </span>
                          <span className="shrink-0 font-mono text-[10px] text-slate-500">
                            {item.age_hours}h old
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()
            )}
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. PRIORITY REVIEW QUEUE WITH SERVER-SIDE PAGINATION & SORTING            */}
      {/* ========================================================================= */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-teal-600" />
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Priority Review Queue
              </h2>
              <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-mono text-slate-700 border border-slate-200">
                {queueData ? `${queueData.total} Total Matches` : "Loading..."}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic server-side triaging with bounded pagination and stable secondary sort keys
            </p>
          </div>

          {/* Filtering Controls */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Status Filter */}
            <select
              value={queueStatus || ""}
              onChange={(e) => {
                setQueueStatus(e.target.value ? (e.target.value as ReportStatus) : undefined);
                setQueuePage(0);
              }}
              className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
            >
              <option value="">{t("citizen.allStatuses", "All Statuses")}</option>
              <option value="submitted">{t("status.submitted", "Submitted")}</option>
              <option value="under_review">{t("status.under_review", "Under Review")}</option>
              <option value="completed_awaiting_verification">{t("status.completed_awaiting_verification", "Awaiting Verification")}</option>
              <option value="verification_failed">{t("overview.failedSignOff", "Verification Failed")}</option>
              <option value="resolved">{t("status.resolved", "Resolved")}</option>
            </select>

            {/* Category Filter */}
            <select
              value={queueCategory || ""}
              onChange={(e) => {
                setQueueCategory(e.target.value ? (e.target.value as ProblemCategory) : undefined);
                setQueuePage(0);
              }}
              className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
            >
              <option value="">{t("citizen.allCategories", "All Categories")}</option>
              <option value="flooding_drainage">{t("category.flooding_drainage", "Flooding / Drainage")}</option>
              <option value="water_scarcity">{t("category.water_scarcity", "Water Scarcity")}</option>
              <option value="heat">{t("category.heat", "Extreme Heat")}</option>
              <option value="loss_of_green_cover">{t("category.loss_of_green_cover", "Loss of Green Cover")}</option>
            </select>

            {/* Sorting Strategy */}
            <select
              value={queueSortBy}
              onChange={(e) => {
                setQueueSortBy(e.target.value);
                setQueuePage(0);
              }}
              className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-xs text-slate-900 font-medium focus:outline-none focus:border-emerald-500 shadow-xs"
            >
              <option value="urgency_desc">{t("reports.sortByUrgencyDesc", "Sort: Highest Urgency")}</option>
              <option value="urgency_asc">{t("reports.sortByUrgencyAsc", "Sort: Lowest Urgency")}</option>
              <option value="age_desc">{t("reports.sortByAgeAsc", "Sort: Oldest First")}</option>
              <option value="age_asc">{t("reports.sortByAgeDesc", "Sort: Newest First")}</option>
            </select>
          </div>
        </div>

        {/* Queue Table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          {queueLoading ? (
            <div className="py-12 text-center text-xs text-slate-500 animate-pulse">
              Loading server-side priority review queue...
            </div>
          ) : queueError ? (
            <div className="p-6 text-center text-xs text-rose-600">
              <p>{queueError}</p>
              <button onClick={() => setQueueRefreshKey((k) => k + 1)} className="mt-2 text-rose-700 underline font-semibold">
                Retry Queue
              </button>
            </div>
          ) : queueData?.items.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No reports match the selected queue filters.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {queueData?.items.map((r) => (
                <div
                  key={r.id}
                  onClick={() => setInspectedReport(r)}
                  className="p-3.5 hover:bg-slate-50 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer group"
                >
                  <div className="space-y-1 max-w-xl">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-teal-700 group-hover:underline">
                        {r.id}
                      </span>
                      {renderCategoryBadge(r.category)}
                      {renderStatusBadge(r.status)}
                      {r.neighbourhood_id ? (
                        <span className="text-[10px] text-slate-700 font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                          {r.neighbourhood_id}
                        </span>
                      ) : (
                        <span className="text-[10px] text-amber-800 font-mono bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                          Unassigned Ward
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-800 line-clamp-1">{r.description}</p>

                    <div className="flex items-center space-x-3 text-[10px] text-slate-500">
                      {r.location_description && (
                        <span className="flex items-center space-x-1">
                          <MapPin className="w-3 h-3 text-slate-400" />
                          <span className="truncate max-w-[200px]">{r.location_description}</span>
                        </span>
                      )}
                      <span>&bull;</span>
                      <span>Submitted: {new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Urgency & Completeness Pill */}
                  <div className="flex items-center space-x-4 shrink-0 sm:self-center">
                    <div className="text-right">
                      <div className="text-xs font-bold font-mono text-rose-600">
                        {r.urgency_score.toFixed(1)}{" "}
                        <span className="text-[10px] font-normal text-slate-500">/ 100</span>
                      </div>
                      <div className="text-[9px] text-slate-500 uppercase">Urgency</div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs font-bold font-mono text-teal-700">
                        {r.evidence_confidence_score.toFixed(1)}{" "}
                        <span className="text-[10px] font-normal text-slate-500">/ 100</span>
                      </div>
                      <div className="text-[9px] text-slate-500 uppercase">Evidence</div>
                    </div>

                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-teal-600 group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Queue Pagination Footer */}
          {queueData && queueData.total > pageSize && (
            <div className="border-t border-slate-100 bg-slate-50 px-4 py-2 flex items-center justify-between text-xs text-slate-500">
              <div>
                Showing page {queuePage + 1} of {Math.ceil(queueData.total / pageSize)} &bull;{" "}
                <span className="font-mono text-slate-800 font-semibold">{queueData.total}</span> reports total
              </div>
              <div className="flex items-center space-x-1.5">
                <button
                  disabled={queuePage === 0}
                  onClick={() => setQueuePage((prev) => Math.max(0, prev - 1))}
                  className="rounded px-2.5 py-1 bg-white border border-slate-200 disabled:opacity-40 hover:bg-slate-50 text-slate-700 shadow-xs transition-colors"
                >
                  Previous
                </button>
                <button
                  disabled={(queuePage + 1) * pageSize >= queueData.total}
                  onClick={() => setQueuePage((prev) => prev + 1)}
                  className="rounded px-2.5 py-1 bg-white border border-slate-200 disabled:opacity-40 hover:bg-slate-50 text-slate-700 shadow-xs transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. GEOGRAPHIC RISK AGGREGATION                                             */}
      {/* ========================================================================= */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <Globe2 className="w-4 h-4 text-emerald-600" />
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Geographic Environmental Hazard Aggregation
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Aggregated report density and urgency by synthetic neighbourhood boundaries
            </p>
          </div>

          {/* Time Window & Category Filter */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Category Filter for Geo Risk */}
            <select
              value={geoCategory || ""}
              onChange={(e) => setGeoCategory(e.target.value ? (e.target.value as ProblemCategory) : undefined)}
              className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
            >
              <option value="">All Categories</option>
              <option value="flooding_drainage">Flooding / Drainage</option>
              <option value="water_scarcity">Water Scarcity</option>
              <option value="heat">Extreme Heat</option>
              <option value="loss_of_green_cover">Loss of Green Cover</option>
            </select>

            <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200">
              <button
                onClick={() => setGeoTimeWindow(undefined)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  geoTimeWindow === undefined
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All Time
              </button>
              <button
                onClick={() => setGeoTimeWindow(30)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  geoTimeWindow === 30
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Last 30 Days
              </button>
              <button
                onClick={() => setGeoTimeWindow(7)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  geoTimeWindow === 7
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Last 7 Days
              </button>
            </div>
          </div>
        </div>

        {/* Unassigned Warning Banner */}
        {geoRisk?.unassigned && geoRisk.unassigned.total_reports > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900 flex items-start justify-between gap-4">
            <div className="flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong>Unassigned External Reports ({geoRisk.unassigned.total_reports}):</strong>{" "}
                {geoRisk.unassigned.total_reports} citizen submissions have coordinates outside registered wards or lack valid neighbourhood IDs. They are safely tracked below without synthetic fabrication.
              </div>
            </div>
            <span className="font-mono text-amber-800 font-bold shrink-0">
              Avg Urgency: {geoRisk.unassigned.average_urgency}
            </span>
          </div>
        )}

        {/* Neighbourhood Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {geoLoading ? (
            <div className="col-span-full py-12 text-center text-xs text-slate-500 animate-pulse">
              Aggregating geographic risk across neighbourhoods...
            </div>
          ) : geoError ? (
            <div className="col-span-full p-6 text-center text-xs text-rose-600">
              {geoError}
            </div>
          ) : geoRisk?.neighbourhoods.length === 0 && !geoRisk?.unassigned ? (
            <div className="col-span-full py-8 text-center text-xs text-slate-500">
              No reports found in the selected geographic time filter.
            </div>
          ) : (
            geoRisk?.neighbourhoods.map((n) => (
              <div
                key={n.neighbourhood_id}
                className="bg-white rounded-xl p-4 border border-slate-200 space-y-3 shadow-xs"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 tracking-tight">
                      {n.neighbourhood_name || n.neighbourhood_id}
                    </h3>
                    <span className="font-mono text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                      {n.neighbourhood_id}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-base font-bold font-mono text-emerald-700">
                      {n.total_reports}
                    </span>
                    <span className="block text-[9px] text-slate-500 uppercase">Reports</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-100 text-center">
                  <div className="bg-slate-50 p-2 rounded border border-slate-100">
                    <div className="text-xs font-bold font-mono text-rose-600">
                      {n.high_urgency_reports}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase">High Urg</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded border border-slate-100">
                    <div className="text-xs font-bold font-mono text-blue-700">
                      {n.active_reports}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase">Active</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded border border-slate-100">
                    <div className="text-xs font-bold font-mono text-emerald-700">
                      {n.resolved_reports}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase">Resolved</div>
                  </div>
                </div>

                {n.top_hazard_category && (
                  <div className="flex items-center justify-between text-[11px] text-slate-600 pt-1">
                    <span>Top Hazard:</span>
                    {renderCategoryBadge(n.top_hazard_category)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 4. SYNTHETIC OPTIMIZER BASELINE DISCLOSURE                                 */}
      {/* ========================================================================= */}
      <section className="space-y-4 pt-4 border-t border-slate-200">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 flex items-start justify-between gap-4">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-amber-900 flex items-center space-x-2">
                <span>SYNTHETIC URBAN MODELLING TELEMETRY</span>
                <span className="rounded bg-amber-100 text-amber-800 px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-mono border border-amber-300">
                  Simulation Baseline
                </span>
              </div>
              <p className="mt-1 text-slate-600 leading-relaxed text-[11px]">
                Ward indicators, vulnerability scores, and land availability indices are benchmark synthetic estimates derived for algorithmic optimization demonstration. They do <strong>not</strong> represent measured physical ground truth. Live citizen reports are strictly segregated as unverified observational inputs.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={onNavigateToRiskMap}
              className="rounded-lg bg-white hover:bg-slate-50 border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition-colors"
            >
              Risk Map &rarr;
            </button>
            <button
              onClick={onNavigateToOptimizer}
              className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 text-xs font-semibold shadow-xs transition-colors"
            >
              Optimizer &rarr;
            </button>
          </div>
        </div>
      </section>

      {/* Report Detail Modal */}
      {inspectedReport && (
        <ReportDetailModal
          report={inspectedReport}
          onClose={() => setInspectedReport(null)}
        />
      )}
    </div>
  );
}
