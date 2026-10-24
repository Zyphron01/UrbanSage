"use client";
import React, { useEffect, useState } from "react";
import {
  BarChart3,
  Layers,
  MapPin,
  MessageSquareWarning,
  Sliders,
  TreePine,
  ShieldCheck,
} from "lucide-react";
import { fetchHealth, HealthResponse } from "@/lib/api";

export type TabId =
  | "overview"
  | "reports"
  | "risk_map"
  | "optimization"
  | "scenarios"
  | "interventions"
  | "accountability";

interface NavbarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  reportCount?: number;
}

export function Navbar({ activeTab, onTabChange, reportCount = 0 }: NavbarProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const data = await fetchHealth();
        if (mounted) {
          setHealth(data);
          setIsOnline(true);
        }
      } catch {
        if (mounted) {
          setIsOnline(false);
        }
      }
    };

    check();
    const interval = setInterval(check, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems: { id: TabId; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: "overview", label: "Overview", icon: <BarChart3 className="w-4 h-4" /> },
    {
      id: "reports",
      label: "Citizen Reports",
      icon: <MessageSquareWarning className="w-4 h-4" />,
      badge: reportCount,
    },
    { id: "risk_map", label: "Risk Map", icon: <MapPin className="w-4 h-4" /> },
    { id: "optimization", label: "Optimization", icon: <Sliders className="w-4 h-4" /> },
    { id: "scenarios", label: "Scenarios", icon: <Layers className="w-4 h-4" /> },
    { id: "interventions", label: "Interventions", icon: <TreePine className="w-4 h-4" /> },
    { id: "accountability", label: "Audit & Finance", icon: <ShieldCheck className="w-4 h-4 text-emerald-400" /> },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-xs">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand & Mission Tag */}
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 shadow-xs">
            <TreePine className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold tracking-tight text-slate-900 text-lg">
                UrbanSage<span className="text-teal-700"> AI</span>
              </span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700 uppercase tracking-wider border border-slate-200">
                Phase 1
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              Sustainable Urban Decision Support
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center space-x-2 rounded-lg px-3 py-2 text-xs font-semibold transition-all ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800 shadow-xs border border-emerald-200"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`ml-1.5 rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                      isActive
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-slate-100 text-slate-600 border border-slate-200"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Live Backend Telemetry Indicator */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 rounded-full bg-slate-50 border border-slate-200 px-3 py-1 text-xs shadow-xs">
            {isOnline === true ? (
              <>
                <span className="h-2 w-2 rounded-full bg-emerald-500 pulse-active" />
                <span className="text-slate-700 font-mono text-[11px]">
                  API: {health?.version ? `v${health.version}` : "Online"}
                </span>
              </>
            ) : isOnline === false ? (
              <>
                <span className="h-2 w-2 rounded-full bg-rose-500" />
                <span className="text-rose-700 font-mono text-[11px]">API: Offline</span>
              </>
            ) : (
              <>
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="text-slate-500 font-mono text-[11px]">Probing...</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Navigation Scrollbar */}
      <div className="md:hidden flex overflow-x-auto border-t border-slate-200 px-2 py-2 space-x-1 bg-white">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={`flex items-center space-x-1.5 whitespace-nowrap rounded px-2.5 py-1.5 text-xs font-semibold ${
              activeTab === item.id
                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </header>
  );
}
