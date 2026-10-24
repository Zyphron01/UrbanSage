/**
 * UrbanSage AI — Synthetic Reference Data for Command Center Visualization
 * ========================================================================
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  CRITICAL NOTICE — SYNTHETIC SIMULATION ESTIMATES                   ║
 * ║  These values are calibrated benchmark models for algorithmic       ║
 * ║  decision-support simulation and planning demonstration.            ║
 * ║  They DO NOT represent physical sensor measurements or verified     ║
 * ║  real-world field surveys.                                          ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 */

export interface SyntheticNeighbourhood {
  id: string;
  name: string;
  area_sqkm: number;
  population: number;
  heat_risk: number;
  flood_risk: number;
  water_stress: number;
  social_vulnerability_index: number;
  current_green_cover_pct: number;
  centroid_lat: number;
  centroid_lon: number;
  is_synthetic: true;
}

export const SYNTHETIC_NEIGHBOURHOODS: SyntheticNeighbourhood[] = [
  {
    id: "NBR-001",
    name: "Shivajinagar Central",
    area_sqkm: 2.1,
    population: 34000,
    heat_risk: 78.5,
    flood_risk: 82.0,
    water_stress: 65.0,
    social_vulnerability_index: 68.0,
    current_green_cover_pct: 8.2,
    centroid_lat: 12.9856,
    centroid_lon: 77.6057,
    is_synthetic: true,
  },
  {
    id: "NBR-002",
    name: "Koramangala 4th Block",
    area_sqkm: 3.4,
    population: 28000,
    heat_risk: 62.0,
    flood_risk: 79.5,
    water_stress: 58.0,
    social_vulnerability_index: 42.0,
    current_green_cover_pct: 14.5,
    centroid_lat: 12.9345,
    centroid_lon: 77.6266,
    is_synthetic: true,
  },
  {
    id: "NBR-003",
    name: "Peenya Industrial Area",
    area_sqkm: 6.8,
    population: 52000,
    heat_risk: 88.0,
    flood_risk: 60.5,
    water_stress: 84.0,
    social_vulnerability_index: 76.0,
    current_green_cover_pct: 4.8,
    centroid_lat: 13.0285,
    centroid_lon: 77.5197,
    is_synthetic: true,
  },
  {
    id: "NBR-004",
    name: "Indiranagar Ward 112",
    area_sqkm: 2.8,
    population: 24500,
    heat_risk: 54.0,
    flood_risk: 45.0,
    water_stress: 60.0,
    social_vulnerability_index: 34.0,
    current_green_cover_pct: 22.1,
    centroid_lat: 12.9784,
    centroid_lon: 77.6408,
    is_synthetic: true,
  },
  {
    id: "NBR-005",
    name: "Whitefield Tech Belt",
    area_sqkm: 5.2,
    population: 41000,
    heat_risk: 76.0,
    flood_risk: 71.0,
    water_stress: 91.0,
    social_vulnerability_index: 48.0,
    current_green_cover_pct: 11.0,
    centroid_lat: 12.9698,
    centroid_lon: 77.7499,
    is_synthetic: true,
  },
  {
    id: "NBR-006",
    name: "Jayanagar 7th Block",
    area_sqkm: 3.0,
    population: 29000,
    heat_risk: 51.0,
    flood_risk: 38.0,
    water_stress: 52.0,
    social_vulnerability_index: 38.0,
    current_green_cover_pct: 26.4,
    centroid_lat: 12.9250,
    centroid_lon: 77.5838,
    is_synthetic: true,
  },
  {
    id: "NBR-007",
    name: "Bellandur Catchment",
    area_sqkm: 4.9,
    population: 47000,
    heat_risk: 72.0,
    flood_risk: 94.0,
    water_stress: 88.0,
    social_vulnerability_index: 55.0,
    current_green_cover_pct: 9.3,
    centroid_lat: 12.9260,
    centroid_lon: 77.6762,
    is_synthetic: true,
  },
  {
    id: "NBR-008",
    name: "Malleswaram Heritage",
    area_sqkm: 2.5,
    population: 31000,
    heat_risk: 58.0,
    flood_risk: 49.0,
    water_stress: 63.0,
    social_vulnerability_index: 46.0,
    current_green_cover_pct: 19.8,
    centroid_lat: 13.0031,
    centroid_lon: 77.5643,
    is_synthetic: true,
  },
  {
    id: "NBR-009",
    name: "Electronic City South",
    area_sqkm: 7.1,
    population: 46000,
    heat_risk: 81.0,
    flood_risk: 63.0,
    water_stress: 89.0,
    social_vulnerability_index: 52.0,
    current_green_cover_pct: 13.2,
    centroid_lat: 12.8452,
    centroid_lon: 77.6602,
    is_synthetic: true,
  },
  {
    id: "NBR-010",
    name: "Hebbal Lake Enclave",
    area_sqkm: 3.9,
    population: 35000,
    heat_risk: 64.0,
    flood_risk: 86.0,
    water_stress: 70.0,
    social_vulnerability_index: 61.0,
    current_green_cover_pct: 15.6,
    centroid_lat: 13.0358,
    centroid_lon: 77.5970,
    is_synthetic: true,
  },
];

export interface SyntheticIntervention {
  id: string;
  name: string;
  category: string;
  cost_lakh: number;
  maintenance_lakh: number;
  implementation_months: number;
  heat_reduction: number;
  flood_reduction: number;
  water_reduction: number;
  carbon_reduction: number;
}

export const SYNTHETIC_INTERVENTIONS: SyntheticIntervention[] = [
  {
    id: "INT-001",
    name: "Urban Miyawaki Forest",
    category: "urban_forest",
    cost_lakh: 14.5,
    maintenance_lakh: 1.2,
    implementation_months: 6,
    heat_reduction: 75,
    flood_reduction: 45,
    water_reduction: 30,
    carbon_reduction: 85,
  },
  {
    id: "INT-002",
    name: "Extensive Green Rooftop",
    category: "green_roof",
    cost_lakh: 8.2,
    maintenance_lakh: 0.8,
    implementation_months: 3,
    heat_reduction: 60,
    flood_reduction: 35,
    water_reduction: 20,
    carbon_reduction: 40,
  },
  {
    id: "INT-003",
    name: "Community Rainwater Tank (10kL)",
    category: "rainwater_harvesting",
    cost_lakh: 5.0,
    maintenance_lakh: 0.4,
    implementation_months: 2,
    heat_reduction: 10,
    flood_reduction: 55,
    water_reduction: 80,
    carbon_reduction: 15,
  },
  {
    id: "INT-004",
    name: "Bioswale & Permeable Drain",
    category: "drainage",
    cost_lakh: 11.0,
    maintenance_lakh: 0.9,
    implementation_months: 4,
    heat_reduction: 25,
    flood_reduction: 85,
    water_reduction: 40,
    carbon_reduction: 20,
  },
];
