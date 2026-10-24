"use client";

import React, { useState } from "react";
import {
  BarChart3,
  Building2,
  Layers,
  MapPin,
  MessageSquareWarning,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { CitizenReportPublic, ProblemCategory, ReportStatus } from "@/lib/api";
import { OverviewView } from "./OverviewView";
import { CitizenReportsView } from "./CitizenReportsView";
import { RiskMapView } from "./RiskMapView";
import { OptimizationView } from "./OptimizationView";
import { ScenariosView } from "./ScenariosView";
import { AccountabilityView } from "./AccountabilityView";
import { EnvironmentalIntelligenceView } from "./EnvironmentalIntelligenceView";
import { useLanguage } from "@/lib/i18n";

export type AdminTabId =
  | "environmental"
  | "overview"
  | "reports"
  | "risk_map"
  | "optimization"
  | "scenarios"
  | "accountability";

interface AdminPortalViewProps {
  reports: CitizenReportPublic[];
  totalReports: number;
  isLoadingReports: boolean;
  onRefreshReports: () => void;
  onReportCreated: (report: CitizenReportPublic) => void;
}

export function AdminPortalView({
  reports,
  totalReports,
  isLoadingReports,
  onRefreshReports,
  onReportCreated,
}: AdminPortalViewProps) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<AdminTabId>("environmental");
  const [selectedCategory, setSelectedCategory] = useState<ProblemCategory | undefined>(undefined);
  const [selectedStatus, setSelectedStatus] = useState<ReportStatus | undefined>(undefined);

  const adminNavItems: { id: AdminTabId; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: "environmental",
      label: t("admin.tabEnvIntelligence", "Environmental Intelligence & Evidence"),
      icon: <BarChart3 className="w-4 h-4 text-emerald-600" />,
    },
    {
      id: "overview",
      label: t("admin.tabOverview", "Executive Decision Brief"),
      icon: <Building2 className="w-4 h-4" />,
    },
    {
      id: "reports",
      label: t("admin.tabReports", "Priority Review Queue"),
      icon: <MessageSquareWarning className="w-4 h-4" />,
      badge: totalReports,
    },
    {
      id: "risk_map",
      label: t("admin.tabRiskMap", "Hazard Risk Map"),
      icon: <MapPin className="w-4 h-4" />,
    },
    {
      id: "optimization",
      label: t("admin.tabOptimizer", "HiGHS MILP Optimizer"),
      icon: <Sliders className="w-4 h-4" />,
    },
    {
      id: "scenarios",
      label: t("admin.tabScenarios", "Scenario Simulator"),
      icon: <Layers className="w-4 h-4" />,
    },
    {
      id: "accountability",
      label: t("admin.tabLedger", "Capital Ledger & Audit"),
      icon: <ShieldCheck className="w-4 h-4 text-emerald-500" />,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Admin Command Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center space-x-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
              <Building2 className="w-3.5 h-3.5" />
              <span>Municipal Environmental Command & Decision Support</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Urban Sustainability Decision & Governance Portal
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Synthesizing crowd-sourced incident reports, mathematical resource optimization (SciPy HiGHS MILP),
              multi-hazard climate stress scenarios, and cryptographic milestone-verified fund disbursements.
            </p>
          </div>

          <div className="flex flex-col items-end text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 shrink-0">
            <span className="text-[10px] uppercase font-semibold text-slate-500">Authenticated Role</span>
            <span className="font-mono text-teal-700 font-bold">administrator (demo-admin-1)</span>
            <span className="text-[10px] text-slate-500 mt-1">Division: Municipal Control Room</span>
          </div>
        </div>
      </div>

      {/* Admin Internal Sub-Navigation Bar */}
      <div className="flex border-b border-slate-200 space-x-1 sm:space-x-2 overflow-x-auto pb-1 text-xs font-medium">
        {adminNavItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center space-x-2 py-2 px-3 rounded-lg transition-all ${
                isActive
                  ? "bg-slate-100 text-slate-900 border border-slate-300 font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`ml-1 rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                    isActive ? "bg-emerald-100 text-emerald-800 border border-emerald-200" : "bg-slate-100 text-slate-600 border border-slate-200"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "environmental" && <EnvironmentalIntelligenceView />}

        {activeTab === "overview" && (
          <OverviewView
            reports={reports}
            onNavigateToReports={(cat, stat) => {
              if (cat) setSelectedCategory(cat);
              if (stat) setSelectedStatus(stat);
              setActiveTab("reports");
            }}
            onNavigateToRiskMap={() => setActiveTab("risk_map")}
            onNavigateToOptimizer={() => setActiveTab("optimization")}
          />
        )}

        {activeTab === "reports" && (
          <CitizenReportsView
            reports={reports}
            total={totalReports}
            isLoading={isLoadingReports}
            error={null}
            selectedCategory={selectedCategory}
            selectedStatus={selectedStatus}
            onCategoryChange={(cat) => setSelectedCategory(cat)}
            onStatusChange={(status) => setSelectedStatus(status)}
            onRefresh={onRefreshReports}
            onReportCreated={onReportCreated}
          />
        )}

        {activeTab === "risk_map" && <RiskMapView reports={reports} />}

        {activeTab === "optimization" && <OptimizationView />}

        {activeTab === "scenarios" && <ScenariosView />}

        {activeTab === "accountability" && <AccountabilityView />}
      </div>
    </div>
  );
}
