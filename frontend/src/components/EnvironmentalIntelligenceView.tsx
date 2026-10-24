"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Droplets,
  FileText,
  Flame,
  Info,
  Layers,
  MapPin,
  RefreshCw,
  Shield,
  Sun,
  Trees,
  Waves,
} from "lucide-react";
import {
  EnvironmentalIntelligenceData,
  fetchEnvironmentalIntelligence,
} from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

export function EnvironmentalIntelligenceView() {
  const { t, language } = useLanguage();
  const [data, setData] = useState<EnvironmentalIntelligenceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEnvironmentalIntelligence();
      setData(res);
    } catch (err: unknown) {
      let msg = err instanceof Error ? err.message : "Failed to load environmental intelligence";
      if (msg.toLowerCase().includes("failed to fetch")) {
        msg = t("env.networkError", "Unable to connect to the backend server. Please verify the API is running at http://localhost:8000.");
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getCategoryIcon = (key: string) => {
    switch (key) {
      case "flooding_drainage":
        return <Waves className="w-5 h-5 text-blue-600" />;
      case "extreme_heat":
      case "heat":
        return <Sun className="w-5 h-5 text-amber-500" />;
      case "water_scarcity":
        return <Droplets className="w-5 h-5 text-cyan-600" />;
      case "loss_of_green_cover":
        return <Trees className="w-5 h-5 text-emerald-600" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-rose-500" />;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
            <Shield className="w-3.5 h-3.5 text-emerald-600" />
            {t("env.badge")}
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            {t("env.title")}
          </h2>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            {t("env.subtitle")}
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          {t("common.refresh")}
        </button>
      </div>

      {/* Data Type Transparency Notice */}
      <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-4 flex items-start gap-3 text-amber-900 text-xs">
        <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">{t("common.disclaimer")}: </span>
          {t("env.dataTypeNotice")}
        </div>
      </div>

      {loading && !data ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 shadow-sm">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-emerald-600 mb-3" />
          <p className="text-sm font-medium">{t("common.loading")}</p>
        </div>
      ) : error ? (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-800 text-sm">
          <p className="font-semibold mb-1">{t("env.loadError", "Failed to load data")}</p>
          <p className="text-xs text-rose-700">{error}</p>
          <button
            onClick={loadData}
            className="mt-3 px-3 py-1.5 bg-rose-600 text-white rounded-md text-xs font-medium hover:bg-rose-700 transition"
          >
            {t("common.retry", "Retry")}
          </button>
        </div>
      ) : data ? (
        <>
          {/* Key Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <span className="text-xs text-slate-500 font-medium">
                {t("env.citizenReportsLabel")}
              </span>
              <div className="text-3xl font-extrabold text-slate-900 mt-1">
                {data.total_reports}
              </div>
              <span className="text-[11px] text-slate-500">Live Supabase Database</span>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <span className="text-xs text-amber-600 font-medium">
                {t("env.highUrgencyLabel")}
              </span>
              <div className="text-3xl font-extrabold text-amber-600 mt-1">
                {data.high_urgency_reports}
              </div>
              <span className="text-[11px] text-slate-500">Urgency Score &gt;= 60</span>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <span className="text-xs text-blue-600 font-medium">
                {t("env.hazardComparison")}
              </span>
              <div className="text-3xl font-extrabold text-slate-900 mt-1">
                {data.categories.length}
              </div>
              <span className="text-[11px] text-slate-500">Monitored Domains</span>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <span className="text-xs text-emerald-600 font-medium">
                {t("env.wardDistribution")}
              </span>
              <div className="text-3xl font-extrabold text-slate-900 mt-1">
                {data.wards.length}
              </div>
              <span className="text-[11px] text-slate-500">Metropolitan Wards</span>
            </div>
          </div>

          {/* Four Hazard Categories Detailed Cards */}
          <div>
            <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-600" />
              {t("env.hazardComparison")}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.categories.map((cat) => (
                <div
                  key={cat.category}
                  className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                        {getCategoryIcon(cat.category)}
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-900 text-sm">
                          {t(`category.${cat.category}`, cat.category_name)}
                        </h4>
                        <span className="text-[11px] text-slate-500">
                          {cat.affected_wards.length > 0
                            ? `Active in: ${cat.affected_wards.join(", ")}`
                            : "No active ward reports"}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                      {cat.citizen_reports_count} {t("env.citizenReportsLabel")}
                    </span>
                  </div>

                  {/* Metrics Bar Comparison */}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-center">
                    <div className="bg-slate-50 rounded-lg p-2">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wide block">
                        {t("env.baselineRiskLabel")}
                      </span>
                      <span className="text-sm font-bold text-slate-800">
                        {cat.baseline_risk_score} / 100
                      </span>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wide block">
                        {t("env.avgUrgencyLabel")}
                      </span>
                      <span className="text-sm font-bold text-amber-700">
                        {cat.avg_urgency_score} / 100
                      </span>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wide block">
                        {t("common.severity")} (1-5)
                      </span>
                      <span className="text-sm font-bold text-rose-700">
                        {cat.avg_severity}
                      </span>
                    </div>
                  </div>

                  {/* Severity Distribution 1 to 5 visual bar */}
                  <div className="space-y-1 pt-1">
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>{t("env.severityBreakdown")}</span>
                      <span>1 (Minor) → 5 (Critical)</span>
                    </div>
                    <div className="flex h-3 w-full rounded-full overflow-hidden bg-slate-100 gap-0.5">
                      {[1, 2, 3, 4, 5].map((lvl) => {
                        const count = cat.severity_distribution[`severity_${lvl}`] || 0;
                        const pct = cat.citizen_reports_count > 0 ? (count / cat.citizen_reports_count) * 100 : 0;
                        const colors = [
                          "bg-emerald-400",
                          "bg-teal-400",
                          "bg-amber-400",
                          "bg-orange-500",
                          "bg-rose-600",
                        ];
                        return (
                          <div
                            key={lvl}
                            style={{ width: `${pct}%` }}
                            className={`${colors[lvl - 1]} h-full transition-all`}
                            title={`Severity ${lvl}: ${count} reports (${pct.toFixed(0)}%)`}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Geographic Breakdown by Ward */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-emerald-600" />
                  {t("env.wardDistribution")}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Comparison of citizen complaints versus baseline environmental vulnerability per ward
                </p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-3 px-4">Ward ID & Name</th>
                    <th className="py-3 px-3">Population</th>
                    <th className="py-3 px-3">SVI Index</th>
                    <th className="py-3 px-3">Flood Risk</th>
                    <th className="py-3 px-3">Heat Risk</th>
                    <th className="py-3 px-3">Water Stress</th>
                    <th className="py-3 px-3">Canopy %</th>
                    <th className="py-3 px-3 text-right">Citizen Reports</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.wards.map((w) => (
                    <tr key={w.neighbourhood_id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        <div>{w.name}</div>
                        <span className="text-[10px] text-slate-400">{w.neighbourhood_id}</span>
                      </td>
                      <td className="py-3 px-3 text-slate-600">{w.population.toLocaleString()}</td>
                      <td className="py-3 px-3 font-semibold text-purple-700">{w.social_vulnerability_index}</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${w.flood_risk > 70 ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
                          {w.flood_risk}/100
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${w.heat_risk > 70 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>
                          {w.heat_risk}/100
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${w.water_stress > 70 ? "bg-cyan-100 text-cyan-800" : "bg-slate-100 text-slate-600"}`}>
                          {w.water_stress}/100
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${w.green_cover_pct < 10 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                          {w.green_cover_pct}%
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-900">
                        {w.citizen_reports_count}
                        {w.high_urgency_reports_count > 0 && (
                          <span className="text-[10px] text-rose-600 block">
                            ({w.high_urgency_reports_count} urgent)
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Official Environmental Intelligence Report Sections */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-6">
            <div className="border-b border-slate-200 pb-4">
              <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-600" />
                {t("env.title")}
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Formal municipal intelligence briefing compiled for executive review
              </p>
            </div>

            {/* 1. Executive Summary */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {t("env.execSummaryTitle")}
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 border border-slate-200 rounded-lg p-4">
                {data.report.executive_summary}
              </p>
            </div>

            {/* 2. Key Concerns */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                {t("env.mainConcernsTitle")}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.report.main_concerns.map((concern, idx) => (
                  <div key={idx} className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700">
                    {concern}
                  </div>
                ))}
              </div>
            </div>

            {/* 3. Geographic Distribution */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                {t("env.geoDistTitle")}
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 border border-slate-200 rounded-lg p-4">
                {data.report.geographic_distribution}
              </p>
            </div>

            {/* 4. Data Coverage & Limitations */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-600" />
                {t("env.dataLimitsTitle")}
              </h4>
              <div className="bg-purple-50/60 border border-purple-200 rounded-lg p-4 space-y-2 text-xs text-purple-950">
                <div>
                  <span className="font-bold">Geographic Coverage: </span>
                  {data.report.data_coverage_and_limitations.geographic_coverage}
                </div>
                <div>
                  <span className="font-bold">Participatory Intake: </span>
                  {data.report.data_coverage_and_limitations.participatory_coverage}
                </div>
                <div>
                  <span className="font-bold">Physical Sensors: </span>
                  {data.report.data_coverage_and_limitations.telemetry_status}
                </div>
                <div className="pt-1 text-purple-900 border-t border-purple-200/60 leading-relaxed">
                  <span className="font-bold">Honest Methodological Limits: </span>
                  {data.report.data_coverage_and_limitations.analytical_limitations}
                </div>
              </div>
            </div>

            {/* 5. Recommended Interventions */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {t("env.recommendationsTitle")}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {data.report.recommended_interventions.map((rec, idx) => (
                  <div key={idx} className="bg-emerald-50/60 border border-emerald-200 rounded-lg p-4 text-xs space-y-2">
                    <span className="font-bold text-emerald-900 block text-sm">
                      {rec.hazard}: {rec.recommendation}
                    </span>
                    <p className="text-slate-700 leading-relaxed">
                      <span className="font-semibold text-slate-900">Evidence Justification: </span>
                      {rec.justification}
                    </p>
                    <span className="inline-block px-2 py-0.5 bg-emerald-100 text-emerald-800 font-semibold rounded text-[10px]">
                      Lead: {rec.lead_department}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 6. Budget Implications */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-700" />
                {t("env.budgetImplicationsTitle")}
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 border border-slate-200 rounded-lg p-4">
                {data.report.budget_implications}
              </p>
            </div>
          </div>

          {/* Data Provenance & Traceability Ledger Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                {t("env.provenanceTitle")}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {t("env.provenanceSubtitle")}
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-3 px-4">Ref ID</th>
                    <th className="py-3 px-4">Data Layer</th>
                    <th className="py-3 px-4">Source & Storage</th>
                    <th className="py-3 px-3">Classification</th>
                    <th className="py-3 px-3">Period & Update</th>
                    <th className="py-3 px-4">Aggregation Method</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.provenance.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-mono font-semibold text-slate-600">{p.id}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{p.layer}</td>
                      <td className="py-3 px-4 text-slate-700">{p.source}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {p.data_type}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-500">
                        <div>{p.reporting_period}</div>
                        <span className="text-[10px] text-slate-400">{p.last_updated}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-600">{p.aggregation_method}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
