"use client";

import React from "react";
import {
  AlertTriangle,
  Camera,
  Droplets,
  Eye,
  Flame,
  MapPin,
  TreePine,
  Waves,
} from "lucide-react";
import { CitizenReportPublic, ProblemCategory, ReportStatus, VerificationStatus } from "@/lib/api";

import { useLanguage } from "@/lib/i18n";

interface ReportCardProps {
  report: CitizenReportPublic;
  onInspect: (report: CitizenReportPublic) => void;
}

export function ReportCard({ report, onInspect }: ReportCardProps) {
  const { t } = useLanguage();

  const getCategoryMeta = (cat: ProblemCategory) => {
    switch (cat) {
      case "flooding_drainage":
        return {
          label: t("category.flooding_drainage", "Flooding & Drainage"),
          color: "text-cyan-800 bg-cyan-50 border-cyan-200",
          icon: <Waves className="w-3.5 h-3.5 text-cyan-600" />,
        };
      case "water_scarcity":
        return {
          label: t("category.water_scarcity", "Water Scarcity"),
          color: "text-blue-800 bg-blue-50 border-blue-200",
          icon: <Droplets className="w-3.5 h-3.5 text-blue-600" />,
        };
      case "heat":
        return {
          label: t("category.heat", "Urban Heat"),
          color: "text-amber-800 bg-amber-50 border-amber-200",
          icon: <Flame className="w-3.5 h-3.5 text-amber-600" />,
        };
      case "loss_of_green_cover":
        return {
          label: t("category.loss_of_green_cover", "Loss of Green Cover"),
          color: "text-emerald-800 bg-emerald-50 border-emerald-200",
          icon: <TreePine className="w-3.5 h-3.5 text-emerald-600" />,
        };
      default:
        return {
          label: cat,
          color: "text-slate-700 bg-slate-100 border-slate-200",
          icon: <AlertTriangle className="w-3.5 h-3.5 text-slate-500" />,
        };
    }
  };

  const getStatusBadge = (status: ReportStatus) => {
    switch (status) {
      case "submitted":
        return { label: t("status.submitted", "Submitted"), color: "bg-slate-100 text-slate-700 border border-slate-200" };
      case "under_review":
        return { label: t("status.under_review", "Under Review"), color: "bg-amber-50 text-amber-800 border border-amber-200" };
      case "assigned":
        return { label: t("status.assigned", "Assigned"), color: "bg-teal-50 text-teal-800 border border-teal-200" };
      case "in_progress":
        return { label: t("status.in_progress", "In Progress"), color: "bg-blue-50 text-blue-800 border border-blue-200" };
      case "completed_awaiting_verification":
        return { label: t("status.completed_awaiting_verification", "Awaiting Verification"), color: "bg-indigo-50 text-indigo-800 border border-indigo-200" };
      case "verified_resolved":
        return { label: t("status.verified_resolved", "Verified Resolved"), color: "bg-emerald-50 text-emerald-800 border border-emerald-200" };
        return { label: "Verified", color: "bg-cyan-50 text-cyan-800 border border-cyan-200" };
      case "flagged_suspicious":
        return { label: "Flagged Suspicious", color: "bg-red-50 text-red-800 border border-red-200" };
      case "confirmed_fake":
        return { label: "Confirmed Fake", color: "bg-rose-50 text-rose-800 border border-rose-200" };
      case "duplicate":
        return { label: "Duplicate", color: "bg-slate-100 text-slate-600 border border-slate-200" };
      case "out_of_scope":
        return { label: "Out of Scope", color: "bg-slate-100 text-slate-600 border border-slate-200" };
      case "no_action_required":
        return { label: "No Action", color: "bg-slate-100 text-slate-600 border border-slate-200" };
      case "assigned":
        return { label: "Assigned", color: "bg-blue-50 text-blue-800 border border-blue-200" };
      case "in_progress":
        return { label: "In Progress", color: "bg-indigo-50 text-indigo-800 border border-indigo-200" };
      case "completed_awaiting_verification":
        return { label: "Awaiting Verification", color: "bg-yellow-50 text-yellow-800 border border-yellow-300" };
      case "verification_failed":
        return { label: "Verification Failed", color: "bg-orange-50 text-orange-800 border border-orange-200" };
      case "verified_resolved":
      case "resolved":
        return { label: "Verified Resolved", color: "bg-emerald-50 text-emerald-800 border border-emerald-200" };
      case "dismissed":
      default:
        return { label: "Dismissed", color: "bg-slate-100 text-slate-500 border border-slate-200" };
    }
  };

  const getVerificationBadge = (vStatus: VerificationStatus) => {
    switch (vStatus) {
      case "unverified":
        return { label: "Unverified Claim", color: "text-slate-600 border-slate-200 bg-slate-50" };
      case "community_corroborated":
        return { label: "Community Corroborated", color: "text-teal-800 border-teal-200 bg-teal-50" };
      case "officially_verified":
        return { label: "Officially Verified", color: "text-emerald-800 border-emerald-200 bg-emerald-50" };
      case "dismissed":
      default:
        return { label: "Dismissed", color: "text-slate-400 border-slate-200 bg-slate-50" };
    }
  };

  const catMeta = getCategoryMeta(report.category);
  const statusMeta = getStatusBadge(report.status);
  const verifMeta = getVerificationBadge(report.verification_status);

  // Formatting date string
  const formattedDate = new Date(report.created_at).toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs hover:shadow-md hover:border-slate-300 transition-all flex flex-col justify-between space-y-3.5">
      <div>
        {/* Top Header: ID, Category, Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
              {report.id}
            </span>
            <div
              className={`flex items-center space-x-1 rounded-md px-2 py-0.5 text-[11px] font-semibold border ${catMeta.color}`}
            >
              {catMeta.icon}
              <span>{catMeta.label}</span>
            </div>
          </div>
          <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${statusMeta.color}`}>
            {statusMeta.label}
          </span>
        </div>

        {/* Narrative Description */}
        <p className="text-xs text-slate-700 mt-2.5 line-clamp-2 leading-relaxed">
          {report.description}
        </p>

        {/* Location & Landmark */}
        <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 mt-2">
          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate">
            {report.location_description || `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}
          </span>
          {report.neighbourhood_id && (
            <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[9px] font-mono text-slate-600 border border-slate-200">
              {report.neighbourhood_id}
            </span>
          )}
        </div>
      </div>

      {/* Dual Scores: Urgency vs Evidence Completeness */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
        {/* Urgency Score */}
        <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
          <div className="flex justify-between items-center text-[10px] text-slate-600">
            <span className="font-medium">Urgency</span>
            <span className="font-mono font-bold text-rose-600">
              {report.urgency_score.toFixed(0)}
            </span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-amber-500 to-rose-500 h-full rounded-full"
              style={{ width: `${Math.min(100, report.urgency_score)}%` }}
            />
          </div>
        </div>

        {/* Evidence Completeness Score */}
        <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
          <div className="flex justify-between items-center text-[10px] text-slate-600">
            <span className="font-medium">Completeness</span>
            <span className="font-mono font-bold text-teal-600">
              {report.evidence_confidence_score.toFixed(0)}
            </span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-teal-400 to-emerald-600 h-full rounded-full"
              style={{ width: `${Math.min(100, report.evidence_confidence_score)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Card Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[10px]">
        <div className="flex items-center space-x-2">
          <span className={`border px-1.5 py-0.5 rounded-md text-[9px] font-medium ${verifMeta.color}`}>
            {verifMeta.label}
          </span>
          {report.photos && report.photos.length > 0 && (
            <span className="flex items-center space-x-1 text-slate-500">
              <Camera className="w-3 h-3 text-slate-400" />
              <span>{report.photos.length}</span>
            </span>
          )}
          <span className="text-slate-400 font-mono text-[9px] hidden sm:inline">
            {formattedDate}
          </span>
        </div>

        <button
          onClick={() => onInspect(report)}
          className="flex items-center space-x-1 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 px-2.5 py-1 text-slate-700 hover:text-slate-900 font-semibold transition-colors"
        >
          <Eye className="w-3 h-3 text-slate-500" />
          <span>Inspect</span>
        </button>
      </div>
    </div>
  );
}
