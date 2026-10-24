"use client";

import React, { useState } from "react";
import {
  Droplets,
  Leaf,
  ShieldAlert,
  TreePine,
  Waves,
} from "lucide-react";
import { SYNTHETIC_INTERVENTIONS, SyntheticIntervention } from "@/lib/syntheticData";

export function InterventionsView() {
  const [selectedIntervention, setSelectedIntervention] = useState<SyntheticIntervention>(
    SYNTHETIC_INTERVENTIONS[0]
  );

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case "urban_forest":
        return <TreePine className="w-5 h-5 text-emerald-600" />;
      case "green_roof":
        return <Leaf className="w-5 h-5 text-lime-600" />;
      case "rainwater_harvesting":
        return <Droplets className="w-5 h-5 text-blue-600" />;
      case "drainage":
        return <Waves className="w-5 h-5 text-teal-600" />;
      default:
        return <TreePine className="w-5 h-5 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Synthetic Disclaimer */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>SYNTHETIC INTERVENTION CATALOGUE:</strong> Engineering costs, implementation timeframes, and hazard attenuation factors are calibrated synthetic values.
          </span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Sustainable Urban Intervention Catalogue
            </h1>
            <span className="rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 text-[10px] font-mono font-bold">
              4 Solutions
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Nature-based solutions and ecological infrastructure options evaluated by the optimization solver.
          </p>
        </div>
      </div>

      {/* Interventions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {SYNTHETIC_INTERVENTIONS.map((item) => {
          const isSelected = selectedIntervention.id === item.id;
          return (
            <div
              key={item.id}
              onClick={() => setSelectedIntervention(item)}
              className={`cursor-pointer rounded-xl p-5 border transition-all flex flex-col justify-between ${
                isSelected
                  ? "bg-emerald-50/40 border-emerald-500 ring-1 ring-emerald-500 shadow-xs"
                  : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 shadow-xs"
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                    {getCategoryIcon(item.category)}
                  </div>
                  <span className="font-mono text-xs font-bold text-teal-700">
                    {item.id}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900">{item.name}</h3>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5 uppercase tracking-wider">
                    {item.category.replace("_", " ")}
                  </div>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
                  <div className="flex justify-between items-center text-slate-700">
                    <span className="text-slate-500 text-[11px]">Capital Cost:</span>
                    <span className="font-mono font-bold text-slate-900">₹{item.cost_lakh.toFixed(1)} L</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-700">
                    <span className="text-slate-500 text-[11px]">O&M / Year:</span>
                    <span className="font-mono text-slate-700">₹{item.maintenance_lakh.toFixed(1)} L</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-700">
                    <span className="text-slate-500 text-[11px]">Timeline:</span>
                    <span className="font-mono text-slate-700">{item.implementation_months} mo</span>
                  </div>
                </div>
              </div>

              {/* Co-Benefit Mini Badges */}
              <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-3 gap-1 text-[10px] text-center font-mono">
                <div className="bg-slate-50 rounded py-1 border border-slate-200">
                  <span className="text-amber-700 font-semibold">-{item.heat_reduction}%</span>
                  <div className="text-[8px] text-slate-500 uppercase">Heat</div>
                </div>
                <div className="bg-slate-50 rounded py-1 border border-slate-200">
                  <span className="text-teal-700 font-semibold">-{item.flood_reduction}%</span>
                  <div className="text-[8px] text-slate-500 uppercase">Flood</div>
                </div>
                <div className="bg-slate-50 rounded py-1 border border-slate-200">
                  <span className="text-blue-700 font-semibold">-{item.water_reduction}%</span>
                  <div className="text-[8px] text-slate-500 uppercase">Water</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Item Full Engineering Specification */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="text-[10px] font-mono text-teal-700 uppercase tracking-wider font-semibold">
              Engineering Specification & Co-Benefits
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">{selectedIntervention.name}</h2>
          </div>
          <div className="text-xs font-mono text-slate-700 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg shadow-xs">
            Capital Cost: <strong className="text-slate-900">₹{selectedIntervention.cost_lakh} Lakh</strong> / Unit
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
            <div className="text-slate-500 text-[11px]">Heat Mitigation Impact</div>
            <div className="text-xl font-mono font-bold text-amber-700 mt-1">
              -{selectedIntervention.heat_reduction}%
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Microclimate temperature reduction in immediate 500m radius
            </p>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
            <div className="text-slate-500 text-[11px]">Flood Inundation Attenuation</div>
            <div className="text-xl font-mono font-bold text-teal-700 mt-1">
              -{selectedIntervention.flood_reduction}%
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Peak runoff buffer during extreme precipitation events
            </p>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
            <div className="text-slate-500 text-[11px]">Water Resource Replenishment</div>
            <div className="text-xl font-mono font-bold text-blue-700 mt-1">
              -{selectedIntervention.water_reduction}%
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Groundwater aquifer recharge and potable demand offset
            </p>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
            <div className="text-slate-500 text-[11px]">Carbon Sequestration Index</div>
            <div className="text-xl font-mono font-bold text-emerald-700 mt-1">
              +{selectedIntervention.carbon_reduction} pts
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Ecological biomass accumulation and biodiversity support
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
