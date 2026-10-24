"use client";

import React, { useEffect, useState } from "react";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  HardHat,
  ShieldAlert,
  UserCheck,
} from "lucide-react";
import {
  CitizenReportPublic,
  fetchDemoToken,
  fetchReports,
  setActiveRole,
} from "@/lib/api";
import { PortalHeader } from "@/components/PortalHeader";
import { CitizenPortalView } from "@/components/CitizenPortalView";
import { AdminPortalView } from "@/components/AdminPortalView";
import { ContractorPortalView } from "@/components/ContractorPortalView";
import { HeroBackground } from "@/components/ui/tweenly-hero-background";

import { useLanguage } from "@/lib/i18n";
import { supabase } from "@/lib/supabaseClient";
import { UnifiedAuthModal } from "@/components/UnifiedAuthModal";

export default function MasterGatewayPage() {
  const { t } = useLanguage();
  const [activePortal, setActivePortal] = useState<"gateway" | "citizen" | "admin" | "contractor">("gateway");
  const [reports, setReports] = useState<CitizenReportPublic[]>([]);
  const [totalReports, setTotalReports] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [intendedPortal, setIntendedPortal] = useState<"admin" | "contractor" | null>(null);

  const fetchReportsData = async () => {
    try {
      const data = await fetchReports({ limit: 50, offset: 0 });
      setReports(data.items);
      setTotalReports(data.total);
    } catch {
      // Graceful fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const data = await fetchReports({ limit: 50, offset: 0 });
        if (!ignore) {
          setReports(data.items);
          setTotalReports(data.total);
          setIsLoading(false);
        }
      } catch {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  const handleReportCreated = (newReport: CitizenReportPublic) => {
    setReports((prev) => [newReport, ...prev]);
    setTotalReports((prev) => prev + 1);
  };

  const selectPortal = async (portal: "citizen" | "admin" | "contractor") => {
    if (portal === "citizen") {
      setActivePortal("citizen");
      return;
    }

    // For privileged portals, check verified session
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      setIntendedPortal(portal);
      setIsAuthModalOpen(true);
      return;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/auth/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const profile = await res.json();
        if (portal === "admin") {
          if (profile.role === "administrator") {
            setActivePortal("admin");
            return;
          }
        } else if (portal === "contractor") {
          if (profile.role === "contractor" || profile.role === "administrator") {
            setActivePortal("contractor");
            return;
          }
        }
      }
    } catch {
      // Session verification failed
    }

    // If not authorized for this role, prompt sign in
    setIntendedPortal(portal);
    setIsAuthModalOpen(true);
  };

  const handleAuthSuccess = (role: "citizen" | "admin" | "contractor") => {
    if (role === "admin") {
      setActivePortal("admin");
    } else if (role === "contractor") {
      setActivePortal("contractor");
    } else {
      setActivePortal("citizen");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-emerald-100 selection:text-emerald-900">
      {/* Sticky Global Navigation */}
      <PortalHeader currentPortal={activePortal} onSwitchPortal={(p) => setActivePortal(p)} />

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {/* ========================================================= */}
        {/* VIEW 1: PUBLIC LANDING PAGE & MASTER PORTAL GATEWAY        */}
        {/* ========================================================= */}
        {activePortal === "gateway" && (
          <div className="space-y-16 pb-12">
            {/* Hero Section with Tweenly Animated Background */}
            <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl">
              <HeroBackground
                variant="flow"
                color="#059669"
                accent="#0d9488"
                density={0.8}
                speed={0.6}
                interaction="repel"
                mask="radial"
                className="py-16 sm:py-24 px-6 sm:px-12"
              >
                <div className="relative z-10 max-w-4xl mx-auto text-center space-y-6">
                  {/* Badge */}
                  <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-1.5 text-xs font-semibold text-emerald-800 shadow-xs backdrop-blur-md">
                    <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                    <span>Intelligent Urban Decision Support & Civic Action Platform</span>
                  </div>

                  {/* Main Hero Headline */}
                  <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-tight">
                    Smart Environmental Action. <br />
                    <span className="bg-gradient-to-r from-emerald-600 to-teal-700 bg-clip-text text-transparent">
                      Accountable Urban Decisions.
                    </span>
                  </h1>

                  {/* Subtitle */}
                  <p className="text-sm sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
                    UrbanSage AI bridges the gap between <strong>crowd-sourced citizen problem reporting</strong>,{" "}
                    <strong>SciPy HiGHS mathematical resource optimization</strong>, and{" "}
                    <strong>cryptographic milestone-verified civic execution</strong>.
                  </p>

                  {/* Quick CTAs to 3 Portals */}
                  <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
                    <button
                      onClick={() => selectPortal("citizen")}
                      className="flex items-center space-x-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 px-5 py-3 text-xs sm:text-sm font-bold text-white shadow-xs transition-all hover:scale-105 active:scale-95"
                    >
                      <UserCheck className="w-4 h-4" />
                      <span>Launch Citizen Portal</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => selectPortal("admin")}
                      className="flex items-center space-x-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 px-5 py-3 text-xs sm:text-sm font-bold text-slate-800 shadow-xs transition-all hover:scale-105 active:scale-95"
                    >
                      <Building2 className="w-4 h-4 text-teal-700" />
                      <span>Municipal Admin Portal</span>
                    </button>

                    <button
                      onClick={() => selectPortal("contractor")}
                      className="flex items-center space-x-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 px-5 py-3 text-xs sm:text-sm font-bold text-slate-800 shadow-xs transition-all hover:scale-105 active:scale-95"
                    >
                      <HardHat className="w-4 h-4 text-slate-700" />
                      <span>Contractor Portal</span>
                    </button>
                  </div>
                </div>
              </HeroBackground>
            </div>

            {/* Three Portals Entry Cards */}
            <div className="space-y-4">
              <div className="text-center max-w-2xl mx-auto space-y-1">
                <span className="text-xs font-bold uppercase tracking-widest text-emerald-700">Tailored User Experiences</span>
                <h2 className="text-2xl font-bold text-slate-900">Three Portals, One Integrated Platform</h2>
                <p className="text-xs text-slate-500">
                  Select your role to explore the dedicated interface built for your specific operational responsibility.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
                {/* 1. Citizen Portal Card */}
                <div
                  onClick={() => selectPortal("citizen")}
                  className="cursor-pointer group rounded-2xl border border-slate-200 bg-white p-6 shadow-xs transition-all hover:border-emerald-500 hover:shadow-md flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <UserCheck className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Public Access
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                      Citizen Portal
                    </h3>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Report localized environmental hazards (flooding, waterlogging, heat stress, fallen trees) with photo evidence and GPS coordinates.
                      Track ticket progress and independently verify physical resolution.
                    </p>

                    <ul className="text-xs text-slate-600 space-y-1.5 pt-2">
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span>Incident intake with urgency & confidence scoring</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span>Citizen sign-off & dispute resolution power</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span>Public green expenditure ledger</span>
                      </li>
                    </ul>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700 group-hover:text-emerald-800">
                    <span>Enter Citizen Portal</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>

                {/* 2. Municipal Admin Portal Card */}
                <div
                  onClick={() => selectPortal("admin")}
                  className="cursor-pointer group rounded-2xl border border-slate-200 bg-white p-6 shadow-xs transition-all hover:border-teal-500 hover:shadow-md flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Building2 className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                        Admin Only
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
                      Municipal Administration
                    </h3>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Operational decision briefs, priority review queues with 48h SLA triage, SciPy HiGHS MILP sustainability optimization,
                      and milestone-locked fund disbursements.
                    </p>

                    <ul className="text-xs text-slate-600 space-y-1.5 pt-2">
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                        <span>HiGHS MILP solver with 30% equity floor</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                        <span>Climate shock scenario stress testing</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                        <span>Disbursement execution & audit chain</span>
                      </li>
                    </ul>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-teal-700 group-hover:text-teal-800">
                    <span>Enter Municipal Portal</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>

                {/* 3. Contractor Portal Card */}
                <div
                  onClick={() => selectPortal("contractor")}
                  className="cursor-pointer group rounded-2xl border border-slate-200 bg-white p-6 shadow-xs transition-all hover:border-slate-400 hover:shadow-md flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <HardHat className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        Implementation
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-slate-900 group-hover:text-slate-700 transition-colors">
                      Contractor Portal
                    </h3>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      Field remediation teams manage assigned civic work orders, record physical progress percentages, and upload
                      photographic documentation with cryptographic SHA-256 hashes for payment sign-off.
                    </p>

                    <ul className="text-xs text-slate-600 space-y-1.5 pt-2">
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                        <span>Assigned BBMP green infrastructure contracts</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                        <span>Milestone execution slider (0-100%)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                        <span>Documentary photo metadata with SHA-256</span>
                      </li>
                    </ul>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-slate-800 group-hover:text-slate-900">
                    <span>Enter Contractor Portal</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </div>
            </div>

            {/* 4-Stage Operational Architecture Loop */}
            <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-xs space-y-6">
              <div className="text-center max-w-xl mx-auto space-y-1">
                <span className="text-xs font-bold uppercase tracking-widest text-teal-700">Closed-Loop Civic Tech</span>
                <h2 className="text-xl font-bold text-slate-900">The 4-Stage Operational Loop</h2>
                <p className="text-xs text-slate-500">
                  How UrbanSage AI converts citizen reports into audited physical urban resilience.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                  <div className="text-xs font-bold font-mono text-emerald-700">STAGE 01</div>
                  <h4 className="text-sm font-semibold text-slate-900">Citizen Observation</h4>
                  <p className="text-xs text-slate-600">
                    Crowd-sourced hazard reporting with GPS geolocation and automated urgency/evidence completeness scoring.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                  <div className="text-xs font-bold font-mono text-teal-700">STAGE 02</div>
                  <h4 className="text-sm font-semibold text-slate-900">Municipal Optimization</h4>
                  <p className="text-xs text-slate-600">
                    SciPy HiGHS MILP solver optimizes ₹50L capital allocations under land, budget, and 30% social equity floors.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                  <div className="text-xs font-bold font-mono text-slate-700">STAGE 03</div>
                  <h4 className="text-sm font-semibold text-slate-900">Contractor Execution</h4>
                  <p className="text-xs text-slate-600">
                    Vendors execute work, track milestones, and submit field photographs stamped with SHA-256 hashes.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                  <div className="text-xs font-bold font-mono text-amber-700">STAGE 04</div>
                  <h4 className="text-sm font-semibold text-slate-900">Verification & Payout</h4>
                  <p className="text-xs text-slate-600">
                    Superintending engineer physical inspection sign-off unlocks tranche payout on a tamper-evident audit ledger.
                  </p>
                </div>
              </div>
            </div>

            {/* Scientific Disclosures & Data Governance Notice */}
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-xs text-amber-900 space-y-2">
              <div className="flex items-center space-x-2 font-bold text-amber-950">
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Scientific Disclosures & Data Governance Notice</span>
              </div>
              <p className="text-slate-700 leading-relaxed text-xs">
                <strong>1. Synthetic Optimization Baseline:</strong> Ward sustainability indices, SVI values, and intervention effectiveness metrics are synthetic benchmarks calibrated for mathematical optimization and demonstration. They do not constitute uncalibrated empirical sensor telemetry.
              </p>
              <p className="text-slate-700 leading-relaxed text-xs">
                <strong>2. Citizen Privacy Isolation:</strong> Reporter contact information (phone, email) is permanently excluded from public schemas and public views.
              </p>
              <p className="text-slate-700 leading-relaxed text-xs">
                <strong>3. Geospatial Dataset Segregation:</strong> Preprocessed BBMP 198-ward boundary polygons and stormwater drain shapefiles in <code>data/processed/</code> remain decoupled from the active solver runtime.
              </p>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* VIEW 2: CITIZEN PORTAL                                     */}
        {/* ========================================================= */}
        {activePortal === "citizen" && <CitizenPortalView />}

        {/* ========================================================= */}
        {/* VIEW 3: MUNICIPAL ADMINISTRATION PORTAL                    */}
        {/* ========================================================= */}
        {activePortal === "admin" && (
          <AdminPortalView
            reports={reports}
            totalReports={totalReports}
            isLoadingReports={isLoading}
            onRefreshReports={fetchReportsData}
            onReportCreated={handleReportCreated}
          />
        )}

        {/* ========================================================= */}
        {/* VIEW 4: CONTRACTOR PORTAL                                  */}
        {/* ========================================================= */}
        {activePortal === "contractor" && <ContractorPortalView />}
      </main>

      {/* Global Command Center Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-800">UrbanSage AI</span>
            <span>&bull;</span>
            <span>Intelligent Decisions for Sustainable Cities</span>
            <span>&bull;</span>
            <span className="text-emerald-700 font-medium">Phase 1 & Phase 2 Verified</span>
          </div>

          <div className="flex items-center space-x-4 text-[11px] font-mono text-slate-500">
            <span>FastAPI REST Gateway</span>
            <span>&bull;</span>
            <span>SciPy HiGHS MILP Engine</span>
            <span>&bull;</span>
            <span>Supabase / SQLite Dual Persistence</span>
          </div>
        </div>
      </footer>

      {/* Unified Supabase Auth Modal for Gateway Actions */}
      <UnifiedAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginSuccess={handleAuthSuccess}
        initialMode="signin"
      />
    </div>
  );
}
