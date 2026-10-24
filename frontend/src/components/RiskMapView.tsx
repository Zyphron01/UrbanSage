"use client";

import React, { useState } from "react";
import {
  Compass,
  Droplets,
  Flame,
  MapPin,
  ShieldAlert,
  Waves,
} from "lucide-react";
import { CitizenReportPublic } from "@/lib/api";
import { SYNTHETIC_NEIGHBOURHOODS, SyntheticNeighbourhood } from "@/lib/syntheticData";

interface RiskMapViewProps {
  reports: CitizenReportPublic[];
  onSelectReport?: (report: CitizenReportPublic) => void;
}

type HazardFilter = "heat" | "flood" | "water" | "svi";

export function RiskMapView({ reports }: RiskMapViewProps) {
  const [activeHazard, setActiveHazard] = useState<HazardFilter>("flood");
  const [selectedWard, setSelectedWard] = useState<SyntheticNeighbourhood>(
    SYNTHETIC_NEIGHBOURHOODS[0]
  );

  const getHazardValue = (w: SyntheticNeighbourhood, h: HazardFilter) => {
    switch (h) {
      case "heat":
        return w.heat_risk;
      case "flood":
        return w.flood_risk;
      case "water":
        return w.water_stress;
      case "svi":
        return w.social_vulnerability_index;
    }
  };

  const getHazardColor = (val: number) => {
    if (val >= 80) return "text-rose-800 bg-rose-50 border-rose-200";
    if (val >= 60) return "text-amber-800 bg-amber-50 border-amber-200";
    if (val >= 40) return "text-yellow-800 bg-yellow-50 border-yellow-200";
    return "text-emerald-800 bg-emerald-50 border-emerald-200";
  };

  return (
    <div className="space-y-6">
      {/* Synthetic Disclaimer */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>SYNTHETIC GEODATA BENCHMARK:</strong> Ward boundaries, centroid coordinates, and risk scores are calibrated synthetic models for decision testing.
          </span>
        </div>
      </div>

      {/* Layer Switcher Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Spatial Hazard & Vulnerability Map
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Ward-level spatial distribution across 10 synthetic Bengaluru administrative zones.
          </p>
        </div>

        {/* Hazard Layer Filter */}
        <div className="flex items-center space-x-1.5 bg-slate-100 border border-slate-200 p-1 rounded-xl text-xs">
          <button
            onClick={() => setActiveHazard("flood")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeHazard === "flood"
                ? "bg-white text-slate-900 border border-slate-200 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Waves className="w-3.5 h-3.5 text-cyan-600" />
            <span>Flood Risk</span>
          </button>

          <button
            onClick={() => setActiveHazard("heat")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeHazard === "heat"
                ? "bg-white text-slate-900 border border-slate-200 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-amber-600" />
            <span>Heat Island</span>
          </button>

          <button
            onClick={() => setActiveHazard("water")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeHazard === "water"
                ? "bg-white text-slate-900 border border-slate-200 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Droplets className="w-3.5 h-3.5 text-blue-600" />
            <span>Water Stress</span>
          </button>

          <button
            onClick={() => setActiveHazard("svi")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeHazard === "svi"
                ? "bg-white text-slate-900 border border-slate-200 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Compass className="w-3.5 h-3.5 text-rose-600" />
            <span>Social Vulnerability</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Interactive Ward Matrix + Ward Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ward Matrix (2 cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl p-5 border border-slate-200 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">
              Ward Risk Matrix ({SYNTHETIC_NEIGHBOURHOODS.length} Administrative Zones)
            </h2>
            <span className="text-[11px] text-slate-500">
              Sorted by {activeHazard.toUpperCase()} severity
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SYNTHETIC_NEIGHBOURHOODS.slice()
              .sort((a, b) => getHazardValue(b, activeHazard) - getHazardValue(a, activeHazard))
              .map((ward) => {
                const val = getHazardValue(ward, activeHazard);
                const isSelected = selectedWard.id === ward.id;
                const wardReports = reports.filter((r) => r.neighbourhood_id === ward.id);

                return (
                  <div
                    key={ward.id}
                    onClick={() => setSelectedWard(ward)}
                    className={`cursor-pointer rounded-xl p-4 border transition-all shadow-xs ${
                      isSelected
                        ? "bg-teal-50/50 border-teal-500 ring-1 ring-teal-500"
                        : "bg-white border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                          <span>{ward.name}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {ward.id} &bull; {ward.area_sqkm} km² &bull; Pop: {ward.population.toLocaleString()}
                        </div>
                      </div>

                      <div className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${getHazardColor(val)}`}>
                        {val.toFixed(0)}
                      </div>
                    </div>

                    {/* Mini Indicator Bars */}
                    <div className="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                      <div>
                        <span>Flood: </span>
                        <strong className="text-slate-800">{ward.flood_risk.toFixed(0)}</strong>
                      </div>
                      <div>
                        <span>Heat: </span>
                        <strong className="text-slate-800">{ward.heat_risk.toFixed(0)}</strong>
                      </div>
                      <div>
                        <span>Water: </span>
                        <strong className="text-slate-800">{ward.water_stress.toFixed(0)}</strong>
                      </div>
                    </div>

                    {wardReports.length > 0 && (
                      <div className="mt-2 text-[10px] text-teal-700 flex items-center space-x-1 font-medium">
                        <MapPin className="w-3 h-3" />
                        <span>{wardReports.length} citizen report(s) linked</span>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        {/* Selected Ward Inspector Detail (1 col) */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-4 shadow-xs">
          <div>
            <div className="text-[10px] font-mono text-teal-700 uppercase tracking-wider font-semibold">
              Selected Zone Detail
            </div>
            <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedWard.name}</h3>
            <div className="text-xs text-slate-500 font-mono">
              ID: {selectedWard.id} &bull; Centroid: {selectedWard.centroid_lat}°N, {selectedWard.centroid_lon}°E
            </div>
          </div>

          <div className="space-y-3 pt-2 border-t border-slate-100 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Social Vulnerability Index (SVI):</span>
              <span className="font-mono font-bold text-rose-600">
                {selectedWard.social_vulnerability_index.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Current Tree Canopy:</span>
              <span className="font-mono font-bold text-emerald-700">
                {selectedWard.current_green_cover_pct}%
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Flood Hazard Rating:</span>
              <span className="font-mono font-bold text-cyan-700">
                {selectedWard.flood_risk.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Urban Heat Rating:</span>
              <span className="font-mono font-bold text-amber-700">
                {selectedWard.heat_risk.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600">Water Scarcity Stress:</span>
              <span className="font-mono font-bold text-blue-700">
                {selectedWard.water_stress.toFixed(1)} / 100
              </span>
            </div>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-2">
            <div className="text-[11px] font-semibold text-slate-800">
              Decision Optimization Eligibility
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {selectedWard.social_vulnerability_index >= 60.0 ? (
                <span className="text-emerald-700 font-medium">
                  &#x2714; Qualifies for the 30% Equity Allocation Floor (High Vulnerability Zone).
                </span>
              ) : (
                <span className="text-slate-600">
                  Standard municipal allocation zone. Subject to general capacity & budget bounds.
                </span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
