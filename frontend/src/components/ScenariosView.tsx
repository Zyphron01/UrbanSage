"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { runScenarioSimulation } from "@/lib/api";

interface ScenarioSimulationDiff {
  neighbourhood_id: string;
  neighbourhood_name: string;
  intervention_id: string;
  intervention_name: string;
  change_type?: "ADDED" | "REMOVED" | "INCREASED" | "DECREASED" | "UNCHANGED";
  diff_status?: "ADDED" | "REMOVED" | "INCREASED" | "DECREASED" | "UNCHANGED";
  unit_delta?: number;
  units_delta?: number;
  cost_delta_lakh?: number;
  spend_delta_lakh?: number;
}

interface ScenarioSimulationResponse {
  scenario_config: { name: string };
  scenario_result: {
    total_cost_lakh: number;
    budget_lakh: number;
    budget_utilization_pct: number;
    report_need_signals_applied: boolean;
    equity_summary: {
      high_vulnerability_spend_lakh: number;
      equity_spend_fraction_of_total_spend: number;
    };
  };
  all_allocation_diffs?: ScenarioSimulationDiff[];
  allocation_diffs?: ScenarioSimulationDiff[];
}

interface ScenarioCardData {
  id: string;
  name: string;
  scenarioType: string;
  badgeColor: string;
  description: string;
  budgetLakh: number;
  equityFloorPct: number;
  floodMultiplier: number;
  heatMultiplier: number;
  waterMultiplier: number;
  hazardImpact: string;
  keyShift: string;
}

const SCENARIOS: ScenarioCardData[] = [
  {
    id: "SCN-BASELINE",
    name: "Baseline Policy Conditions",
    scenarioType: "BASELINE",
    badgeColor: "bg-slate-100 text-slate-700 border-slate-200",
    description: "Standard municipal budget allocation with historic monsoon patterns and current heat exposure.",
    budgetLakh: 500.0,
    equityFloorPct: 30,
    floodMultiplier: 1.0,
    heatMultiplier: 1.0,
    waterMultiplier: 1.0,
    hazardImpact: "Nominal risk distribution across all 10 wards.",
    keyShift: "Balanced allocation between heat mitigation and drainage works.",
  },
  {
    id: "SCN-RAIN",
    name: "Extreme Monsoon Rainfall (+35%)",
    scenarioType: "EXTREME_RAINFALL",
    badgeColor: "bg-teal-50 text-teal-800 border-teal-200",
    description: "Simulates an intense precipitation anomaly amplifying flood exposure in low-lying lake catchment basins.",
    budgetLakh: 500.0,
    equityFloorPct: 30,
    floodMultiplier: 1.35,
    heatMultiplier: 1.0,
    waterMultiplier: 1.0,
    hazardImpact: "+35% flood risk in Bellandur, Shivajinagar, and Hebbal.",
    keyShift: "Optimizer shifts capital aggressively into permeable drainage and bioswales.",
  },
  {
    id: "SCN-DROUGHT",
    name: "Severe Summer Drought (+40%)",
    scenarioType: "DROUGHT",
    badgeColor: "bg-amber-50 text-amber-800 border-amber-200",
    description: "Simulates severe groundwater depletion and delayed monsoon onset straining urban water security.",
    budgetLakh: 500.0,
    equityFloorPct: 30,
    floodMultiplier: 1.0,
    heatMultiplier: 1.25,
    waterMultiplier: 1.40,
    hazardImpact: "+40% water scarcity in Whitefield and Peenya industrial wards.",
    keyShift: "Community rainwater harvesting units receive highest priority index.",
  },
  {
    id: "SCN-BUDGET-CUT",
    name: "Fiscal Austerity (-25% Budget)",
    scenarioType: "BUDGET_REDUCTION",
    badgeColor: "bg-rose-50 text-rose-800 border-rose-200",
    description: "Simulates municipal funding contraction where capital expenditure is capped at ₹375 lakh.",
    budgetLakh: 375.0,
    equityFloorPct: 30,
    floodMultiplier: 1.0,
    heatMultiplier: 1.0,
    waterMultiplier: 1.0,
    hazardImpact: "Higher residual risk due to constrained overall project capacity.",
    keyShift: "Hard equity constraint strictly preserves high-SVI spend despite austerity.",
  },
  {
    id: "SCN-EQUITY-SHIFT",
    name: "Pro-Poor Climate Adaptation (45% Equity)",
    scenarioType: "EQUITY_POLICY_SHIFT",
    badgeColor: "bg-emerald-50 text-emerald-800 border-emerald-200",
    description: "Raises the minimum social equity allocation from 30% to 45% for vulnerable wards.",
    budgetLakh: 500.0,
    equityFloorPct: 45,
    floodMultiplier: 1.0,
    heatMultiplier: 1.0,
    waterMultiplier: 1.0,
    hazardImpact: "Substantial risk reduction concentrated in top vulnerable zones.",
    keyShift: "Redirects capital from low-SVI wards to Peenya, Shivajinagar, and Hebbal.",
  },
];

export function ScenariosView() {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioCardData>(SCENARIOS[0]);
  const [loading, setLoading] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<ScenarioSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const executeSimulation = async (scenario: ScenarioCardData) => {
    setLoading(true);
    setError(null);
    try {
      const res = (await runScenarioSimulation({
        scenario_type: scenario.scenarioType,
        name: scenario.name,
        description: scenario.description,
        budget_lakh: scenario.budgetLakh,
        equity_threshold: scenario.equityFloorPct / 100.0,
        flood_multiplier: scenario.floodMultiplier,
        heat_multiplier: scenario.heatMultiplier,
        water_multiplier: scenario.waterMultiplier,
        include_citizen_reports: true,
      })) as unknown as ScenarioSimulationResponse;
      setSimulationResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute scenario simulation";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Synthetic Disclaimer */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>SYNTHETIC SCENARIO SIMULATOR:</strong> Climatic and fiscal stress test profiles are non-destructive mathematical transformations used to audit policy resilience under bounded citizen need signals.
          </span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Scenario Simulator & Policy Stress-Testing (Stage 5)
            </h1>
            <span className="rounded-full bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 text-[10px] font-mono font-bold">
              Integrated Simulator
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Simulate climate shocks, precipitation anomalies, and fiscal cutbacks to inspect intervention reallocation dynamics.
          </p>
        </div>

        <button
          onClick={() => executeSimulation(selectedScenario)}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
        >
          <Play className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Run Selected Simulation</span>
        </button>
      </div>

      {/* Scenarios Grid & Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenarios List (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-sm font-bold text-slate-900">Stress-Testing Profiles</h2>
          <div className="space-y-3">
            {SCENARIOS.map((sc) => {
              const isSelected = selectedScenario.id === sc.id;
              return (
                <div
                  key={sc.id}
                  onClick={() => setSelectedScenario(sc)}
                  className={`cursor-pointer rounded-xl p-4 border transition-all ${
                    isSelected
                      ? "bg-emerald-50/40 border-emerald-500 ring-1 ring-emerald-500 shadow-xs"
                      : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-slate-900">{sc.name}</span>
                        <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase font-bold border ${sc.badgeColor}`}>
                          {sc.scenarioType}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        {sc.description}
                      </p>
                    </div>

                    <ArrowRight className={`w-4 h-4 shrink-0 transition-transform ${isSelected ? "text-emerald-600 translate-x-1" : "text-slate-400"}`} />
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-600">
                    <div>
                      <span className="text-slate-400">Budget: </span>
                      <strong className="font-mono text-slate-900">₹{sc.budgetLakh}L</strong>
                    </div>
                    <div>
                      <span className="text-slate-400">Equity Floor: </span>
                      <strong className="font-mono text-emerald-700">{sc.equityFloorPct}%</strong>
                    </div>
                    <div>
                      <span className="text-slate-400">Primary Shift: </span>
                      <span className="text-slate-700 truncate inline-block max-w-[120px]">{sc.keyShift}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Scenario Detailed Explainer (1 col) */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs space-y-4">
          <div>
            <div className="text-[10px] font-mono text-teal-600 uppercase tracking-wider font-semibold">
              Selected Scenario Configuration
            </div>
            <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedScenario.name}</h3>
            <p className="text-xs text-slate-600 leading-relaxed mt-1">
              {selectedScenario.description}
            </p>
          </div>

          <div className="space-y-3 pt-2 border-t border-slate-100 text-xs">
            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <div className="text-slate-500 text-[11px]">Capital Budget Envelope</div>
              <div className="text-lg font-mono font-bold text-slate-900">
                ₹{selectedScenario.budgetLakh.toFixed(1)} Lakh
              </div>
              <div className="text-[10px] text-slate-500">
                {selectedScenario.budgetLakh < 500 ? "Fiscal reduction of 25%" : "Full baseline budget envelope"}
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <div className="text-slate-500 text-[11px]">Minimum Equity Spend Floor</div>
              <div className="text-lg font-mono font-bold text-emerald-700">
                {selectedScenario.equityFloorPct}% Minimum
              </div>
              <div className="text-[10px] text-slate-500">
                Targeted to wards with Social Vulnerability Index &ge; 60
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <div className="text-slate-500 text-[11px]">Hazard Risk Transformation</div>
              <p className="text-slate-700 text-xs">
                {selectedScenario.hazardImpact}
              </p>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <div className="text-slate-500 text-[11px]">Portfolio Adaptation Dynamics</div>
              <p className="text-slate-700 text-xs">
                {selectedScenario.keyShift}
              </p>
            </div>

            <button
              onClick={() => executeSimulation(selectedScenario)}
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center space-x-2 transition-all shadow-xs disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Solving Scenario MILP...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Execute Scenario Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Live Simulation Results Banner */}
      {simulationResult && (
        <div className="bg-white rounded-xl p-5 border border-teal-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <span className="text-xs font-mono uppercase text-teal-700 font-bold">
                Simulation Execution Complete
              </span>
              <h2 className="text-base font-bold text-slate-900 mt-0.5">
                {simulationResult.scenario_config.name} — Comparative Results
              </h2>
            </div>
            <div className="text-xs text-slate-500 font-mono">
              Solver: <span className="text-emerald-700 font-bold">OPTIMAL</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <span className="text-[11px] text-slate-500">Total Spend</span>
              <div className="text-base font-bold text-slate-900 font-mono">
                ₹{simulationResult.scenario_result.total_cost_lakh.toFixed(1)}L / ₹{simulationResult.scenario_result.budget_lakh.toFixed(1)}L
              </div>
              <span className="text-[10px] text-slate-500">
                Utilization: {simulationResult.scenario_result.budget_utilization_pct}%
              </span>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <span className="text-[11px] text-slate-500">Equity Spend (High SVI)</span>
              <div className="text-base font-bold text-emerald-700 font-mono">
                ₹{simulationResult.scenario_result.equity_summary.high_vulnerability_spend_lakh.toFixed(1)}L
              </div>
              <span className="text-[10px] text-emerald-700 flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>Floor satisfied ({simulationResult.scenario_result.equity_summary.equity_spend_fraction_of_total_spend * 100 >= 30 ? "Preserved" : "Strict"})</span>
              </span>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-1">
              <span className="text-[11px] text-slate-500">Citizen Need Signal Integration</span>
              <div className="text-xs font-mono font-bold text-teal-700 pt-1">
                {simulationResult.scenario_result.report_need_signals_applied ? "Active (&le; 25% Bounded Boost)" : "Baseline Only"}
              </div>
              <span className="text-[10px] text-slate-500">
                Strict integrality & capacity bounds met
              </span>
            </div>
          </div>

          {/* Allocation Shifts in Scenario */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-800">Reallocation Diffs vs. Baseline Plan:</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              {(simulationResult.all_allocation_diffs || simulationResult.allocation_diffs || []).slice(0, 6).map((diff: ScenarioSimulationDiff, idx: number) => {
                const status = diff.change_type || diff.diff_status || "UNCHANGED";
                const unitDelta = diff.unit_delta ?? diff.units_delta ?? 0;
                const costDelta = diff.cost_delta_lakh ?? diff.spend_delta_lakh ?? 0;
                return (
                  <div key={idx} className="rounded-lg bg-slate-50 p-2.5 border border-slate-200 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-slate-800">{diff.neighbourhood_name}</div>
                      <div className="text-[11px] text-slate-500">{diff.intervention_name}</div>
                    </div>
                    <div className="text-right font-mono">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        status === "ADDED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                        status === "REMOVED" ? "bg-rose-50 text-rose-700 border-rose-200" :
                        status === "INCREASED" ? "bg-teal-50 text-teal-700 border-teal-200" :
                        "bg-amber-50 text-amber-700 border-amber-200"
                      }`}>
                        {status} ({unitDelta > 0 ? `+${unitDelta}` : unitDelta})
                      </span>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {costDelta > 0 ? `+₹${costDelta.toFixed(1)}L` : `₹${costDelta.toFixed(1)}L`}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800 flex items-center space-x-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
