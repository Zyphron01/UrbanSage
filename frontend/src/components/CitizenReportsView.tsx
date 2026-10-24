"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  Droplets,
  Filter,
  Flame,
  Plus,
  RefreshCw,
  Search,
  TreePine,
  Waves,
} from "lucide-react";
import {
  CitizenReportPublic,
  ProblemCategory,
  ReportStatus,
} from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { ReportCard } from "./ReportCard";
import { ReportDetailModal } from "./ReportDetailModal";
import { ReportSubmitModal } from "./ReportSubmitModal";

interface CitizenReportsViewProps {
  reports: CitizenReportPublic[];
  total: number;
  isLoading: boolean;
  error: string | null;
  selectedCategory: ProblemCategory | undefined;
  selectedStatus: ReportStatus | undefined;
  onCategoryChange: (cat: ProblemCategory | undefined) => void;
  onStatusChange: (status: ReportStatus | undefined) => void;
  onRefresh: () => void;
  onReportCreated: (newReport: CitizenReportPublic) => void;
}

export function CitizenReportsView({
  reports,
  total,
  isLoading,
  error,
  selectedCategory,
  selectedStatus,
  onCategoryChange,
  onStatusChange,
  onRefresh,
  onReportCreated,
}: CitizenReportsViewProps) {
  const { t } = useLanguage();
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [inspectedReport, setInspectedReport] = useState<CitizenReportPublic | null>(null);

  // Category summary counts
  const floodingCount = reports.filter((r) => r.category === "flooding_drainage").length;
  const waterCount = reports.filter((r) => r.category === "water_scarcity").length;
  const heatCount = reports.filter((r) => r.category === "heat").length;
  const greenCount = reports.filter((r) => r.category === "loss_of_green_cover").length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {t("citizen.headerTitle", "Citizen Environmental Problem Reports")}
            </h1>
            <span className="rounded-full bg-teal-50 text-teal-800 border border-teal-200 px-2.5 py-0.5 text-[10px] font-mono font-bold">
              {t("overview.briefLive", "LIVE FEED")}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t("citizen.headerDesc", "Real-time citizen observations with separate operational urgency and documentary evidence completeness metrics.")}
          </p>
        </div>

        <button
          onClick={() => setIsSubmitModalOpen(true)}
          className="inline-flex items-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 text-xs font-semibold shadow-xs transition-all cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>{t("citizen.submitNewReport", "Submit Problem Report")}</span>
        </button>
      </div>

      {/* Category Metric Badges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div
          onClick={() => onCategoryChange(selectedCategory === "flooding_drainage" ? undefined : "flooding_drainage")}
          className={`cursor-pointer rounded-xl p-3 border transition-all shadow-xs ${
            selectedCategory === "flooding_drainage"
              ? "bg-cyan-50/70 border-cyan-400 ring-1 ring-cyan-400"
              : "bg-white border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500">{t("category.flooding_drainage", "Flooding & Drainage")}</span>
            <Waves className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">{floodingCount}</div>
        </div>

        <div
          onClick={() => onCategoryChange(selectedCategory === "water_scarcity" ? undefined : "water_scarcity")}
          className={`cursor-pointer rounded-xl p-3 border transition-all shadow-xs ${
            selectedCategory === "water_scarcity"
              ? "bg-blue-50/70 border-blue-400 ring-1 ring-blue-400"
              : "bg-white border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500">{t("category.water_scarcity", "Water Scarcity")}</span>
            <Droplets className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">{waterCount}</div>
        </div>

        <div
          onClick={() => onCategoryChange(selectedCategory === "heat" ? undefined : "heat")}
          className={`cursor-pointer rounded-xl p-3 border transition-all shadow-xs ${
            selectedCategory === "heat"
              ? "bg-amber-50/70 border-amber-400 ring-1 ring-amber-400"
              : "bg-white border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500">{t("category.heat", "Urban Heat")}</span>
            <Flame className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">{heatCount}</div>
        </div>

        <div
          onClick={() => onCategoryChange(selectedCategory === "loss_of_green_cover" ? undefined : "loss_of_green_cover")}
          className={`cursor-pointer rounded-xl p-3 border transition-all shadow-xs ${
            selectedCategory === "loss_of_green_cover"
              ? "bg-emerald-50/70 border-emerald-400 ring-1 ring-emerald-400"
              : "bg-white border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500">{t("category.loss_of_green_cover", "Loss of Green Cover")}</span>
            <TreePine className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">{greenCount}</div>
        </div>
      </div>

      {/* Filter and Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 border border-slate-200 p-3 rounded-xl text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 flex items-center space-x-1 font-medium">
            <Filter className="w-3.5 h-3.5" />
            <span>{t("common.filter", "Filters")}:</span>
          </span>

          {/* Category Dropdown */}
          <select
            value={selectedCategory || ""}
            onChange={(e) => onCategoryChange(e.target.value ? (e.target.value as ProblemCategory) : undefined)}
            className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
          >
            <option value="">{t("citizen.allCategories", "All Categories")}</option>
            <option value="flooding_drainage">{t("category.flooding_drainage", "Flooding & Drainage")}</option>
            <option value="water_scarcity">{t("category.water_scarcity", "Water Scarcity")}</option>
            <option value="heat">{t("category.heat", "Urban Heat")}</option>
            <option value="loss_of_green_cover">{t("category.loss_of_green_cover", "Loss of Green Cover")}</option>
          </select>

          {/* Status Dropdown */}
          <select
            value={selectedStatus || ""}
            onChange={(e) => onStatusChange(e.target.value ? (e.target.value as ReportStatus) : undefined)}
            className="rounded-lg bg-white border border-slate-300 px-2.5 py-1 text-slate-900 focus:outline-none focus:border-emerald-500 shadow-xs"
          >
            <option value="">{t("citizen.allStatuses", "All Statuses")}</option>
            <option value="submitted">{t("status.submitted", "Submitted")}</option>
            <option value="under_review">{t("status.under_review", "Under Review")}</option>
            <option value="assigned">{t("status.assigned", "Assigned")}</option>
            <option value="in_progress">{t("status.in_progress", "In Progress")}</option>
            <option value="completed_awaiting_verification">{t("status.completed_awaiting_verification", "Awaiting Verification")}</option>
            <option value="verified_resolved">{t("status.verified_resolved", "Resolved")}</option>
          </select>

          {(selectedCategory || selectedStatus) && (
            <button
              onClick={() => {
                onCategoryChange(undefined);
                onStatusChange(undefined);
              }}
              className="text-teal-600 hover:text-teal-700 font-semibold underline px-1 text-[11px]"
            >
              {t("citizen.resetFilters", "Reset Filters")}
            </button>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-slate-500 font-mono text-[11px]">
            {reports.length} / {total}
          </span>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="inline-flex items-center space-x-1 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 px-2.5 py-1 text-slate-700 shadow-xs transition-colors disabled:opacity-50"
            title="Refresh feed"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-teal-600" : ""}`} />
            <span>{t("common.refresh", "Refresh")}</span>
          </button>
        </div>
      </div>

      {/* Main Content Feed States */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-rose-950">Connection or Query Error</div>
            <p className="mt-0.5 text-rose-800">{error}</p>
            <button
              onClick={onRefresh}
              className="mt-2 rounded-lg bg-rose-600 hover:bg-rose-500 px-3 py-1 font-semibold text-white shadow-xs transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {isLoading && reports.length === 0 ? (
        /* Loading Skeleton */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-slate-200 bg-white p-4 animate-pulse space-y-3 shadow-xs"
            >
              <div className="flex justify-between items-center">
                <div className="h-4 w-24 bg-slate-200 rounded" />
                <div className="h-4 w-16 bg-slate-200 rounded" />
              </div>
              <div className="h-8 w-full bg-slate-200 rounded" />
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="h-10 bg-slate-200 rounded" />
                <div className="h-10 bg-slate-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : reports.length === 0 ? (
        /* Empty State */
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center space-y-3 shadow-xs">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 mx-auto">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">No Citizen Reports Found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {selectedCategory || selectedStatus
              ? "No reports match the currently selected filter criteria. Try clearing filters."
              : "No crowd-sourced environmental issues have been submitted yet. Be the first to report an issue."}
          </p>
          <button
            onClick={() => setIsSubmitModalOpen(true)}
            className="mt-2 inline-flex items-center space-x-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-semibold text-white transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Submit First Report</span>
          </button>
        </div>
      ) : (
        /* Report Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              onInspect={(r) => setInspectedReport(r)}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <ReportDetailModal
        report={inspectedReport}
        onClose={() => setInspectedReport(null)}
        onDecisionSubmitted={() => {
          onRefresh();
        }}
      />

      {/* Submission Modal */}
      <ReportSubmitModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onSuccess={(newReport) => {
          onReportCreated(newReport);
        }}
      />
    </div>
  );
}
