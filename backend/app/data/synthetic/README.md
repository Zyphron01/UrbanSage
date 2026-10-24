# UrbanSage AI — Synthetic Data Dictionary

> **⚠ SYNTHETIC DATA DISCLAIMER**
> All records in this directory are entirely synthetic.
> They were generated for modelling and demonstration purposes only.
> They do not represent any real neighbourhood, city, municipality, population, or environmental measurement.
> Every record carries `"data_source": "SYNTHETIC"` to make this status machine-readable.
> These values must not be used to make real planning, policy, or investment decisions.

---

## 1. File Inventory

| File | Records | Purpose |
|---|---|---|
| `neighbourhoods.json` | 10 | Urban neighbourhood risk profiles and land availability |
| `interventions.json` | 4 | Sustainability intervention types with costs and effectiveness |
| `capacities.json` | 40 (10 × 4) | Maximum deployable units per neighbourhood per intervention |

---

## 2. Neighbourhood Fields (`neighbourhoods.json`)

### Identifiers

| Field | Type | Example | Notes |
|---|---|---|---|
| `id` | string | `"NBR-001"` | Unique. Pattern `NBR-NNN`. Primary key. |
| `name` | string | `"Riverbank Colony"` | Human-readable label. Not geographically verified. |
| `data_source` | string | `"SYNTHETIC"` | Must be the literal string `"SYNTHETIC"`. |

### Geography

| Field | Type | Unit | Valid Range | Notes |
|---|---|---|---|---|
| `area_sqkm` | float | km² | > 0 | Total neighbourhood area. SYNTHETIC. |
| `centroid_lat` | float | decimal degrees | −90 to 90 | For map display only. Coordinates are in a fictional city context. |
| `centroid_lon` | float | decimal degrees | −180 to 180 | As above. |

### Demographics

| Field | Type | Unit | Valid Range | Notes |
|---|---|---|---|---|
| `population` | int | persons | > 0 | Estimated resident population. SYNTHETIC. Does not include floating/daytime population. |

### Environmental Risk Indicators (all on 0–100 synthetic scale)

> **Scale interpretation:** 0 = negligible risk / stress. 100 = extreme risk / stress. These are relative scores for within-model comparison, not absolute physical measurements.

| Field | Description | High-value interpretation | SYNTHETIC |
|---|---|---|---|
| `heat_risk` | Urban heat island intensity and exposure | Extreme heat island, high surface temperatures, limited shade | ✅ |
| `flood_risk` | Probability and severity of flood events | High probability of monsoon flooding, inadequate drainage | ✅ |
| `water_stress` | Imbalance between supply and demand | Severe water scarcity, unreliable supply, groundwater depletion | ✅ |
| `current_green_cover_pct` | % area under existing green cover | — (note: lower = greater need for greening interventions) | ✅ |

### Social Vulnerability

| Field | Type | Unit | Valid Range | Notes |
|---|---|---|---|---|
| `social_vulnerability_index` | float | unitless score | 0–100 | Composite indicator. Higher = more vulnerable. Derived from assumed income levels, population density, age distribution, and access to services. Not based on any census or survey data. SYNTHETIC. |

**High-vulnerability threshold:** Neighbourhoods with `social_vulnerability_index ≥ 60` are classified as high-vulnerability and are subject to the equity allocation floor constraint.

**High-vulnerability neighbourhoods in this dataset:**

| ID | Name | SVI |
|---|---|---|
| NBR-001 | Riverbank Colony | 72 |
| NBR-005 | Slum Resettlement Zone | 88 |
| NBR-008 | Eastern Floodplain | 75 |
| NBR-010 | Peripheral Settlement | 68 |

### Land Availability (nested object)

> These figures document the raw physical capacity available. The authoritative constraint for the optimiser is the `max_units` field in `capacities.json`.

| Field | Type | Unit | Notes |
|---|---|---|---|
| `urban_forest_sqm` | float | sqm | Open land suitable for tree plantation. Excludes hazardous or legally encumbered land. |
| `green_roof_sqm` | float | sqm | Flat rooftop area with assumed structural capacity. Structural survey required before deployment. |
| `rainwater_harvesting_sites` | int | site count | Number of viable locations for a 10,000-litre underground tank system. |
| `drainage_sqm` | float | sqm | Road/pavement area eligible for drainage works (approx. 500 m × 5 m per unit). |

---

## 3. Intervention Type Fields (`interventions.json`)

| Field | Type | Unit | Valid Range | Notes |
|---|---|---|---|---|
| `id` | string | — | Pattern `INT-NNN` | Unique. Primary key. |
| `name` | string | — | — | Human-readable. |
| `category` | enum | — | `urban_forest`, `green_roof`, `rainwater_harvesting`, `drainage` | Controlled vocabulary. |
| `description` | string | — | — | Full technical description. |
| `unit_description` | string | — | — | Defines what one "unit" means for this intervention type. |
| `cost_per_unit_lakh` | float | ₹ lakh | > 0 | Capital cost per unit. SYNTHETIC. Excludes maintenance. |
| `land_requirement_sqm_per_unit` | float | sqm | ≥ 0 | Physical footprint per unit. |
| `maintenance_cost_annual_lakh` | float | ₹ lakh/year | ≥ 0 | Recurring annual cost per unit. NOT included in the capital budget constraint. SYNTHETIC. |
| `implementation_months` | int | months | ≥ 1 | Typical end-to-end delivery timeline. |
| `data_source` | string | — | `"SYNTHETIC"` | Provenance tag. |

### Effectiveness Scores (nested object, all 0–100 synthetic scale)

| Field | Dimension | High-value meaning |
|---|---|---|
| `heat_reduction` | Urban heat island | Strong local microclimate cooling per unit |
| `flood_reduction` | Flood risk | Strong stormwater capture/conveyance per unit |
| `water_stress_reduction` | Water scarcity | Significant water demand reduction or recharge |
| `carbon_reduction` | Carbon / emissions | Significant sequestration or avoided energy emissions |

**Intervention catalogue summary:**

| ID | Name | Cost/unit (₹ lakh) | Primary benefit | Composite score |
|---|---|---|---|---|
| INT-001 | Urban Forest Plantation | 8.0 | Heat + carbon | 51.75 |
| INT-002 | Extensive Green Roof | 12.0 | Heat + flood | 40.75 |
| INT-003 | Community RWH System | 5.0 | Water stress | 35.0 |
| INT-004 | Permeable Drainage Improvement | 20.0 | Flood | 35.0 |

> **Note on composite score:** The composite is an unweighted average of four dimensions. It does not reflect the objective function used by the optimiser, which weights scores by neighbourhood risk profiles and the equity multiplier.

---

## 4. Capacity Matrix Fields (`capacities.json`)

| Field | Type | Valid Range | Notes |
|---|---|---|---|
| `neighbourhood_id` | string | Pattern `NBR-NNN` | Foreign key → `neighbourhoods.json`. |
| `intervention_id` | string | Pattern `INT-NNN` | Foreign key → `interventions.json`. |
| `max_units` | int | ≥ 0 | **Authoritative upper bound for the LP.** Zero = infeasible in this neighbourhood. |
| `feasibility_notes` | string | — | Documents the physical/structural rationale. Displayed in decision explanations. |
| `data_source` | string | `"SYNTHETIC"` | Provenance tag. |

**Capacity matrix summary (max_units):**

|  | INT-001 Urban Forest | INT-002 Green Roof | INT-003 RWH | INT-004 Drainage |
|---|---|---|---|---|
| **NBR-001** Riverbank Colony | 2 | 6 | 6 | 5 |
| **NBR-002** Industrial Quarter | 1 | 7 | 5 | 4 |
| **NBR-003** Green Hills | 4 | 4 | 3 | 3 |
| **NBR-004** Old Town Core | **0** | 8 | 8 | 3 |
| **NBR-005** Slum Resettlement Zone | 1 | 5 | 9 | 4 |
| **NBR-006** Tech Hub District | 3 | 8 | 4 | 6 |
| **NBR-007** Market District | **0** | 7 | 7 | 4 |
| **NBR-008** Eastern Floodplain | 3 | 6 | 8 | 7 |
| **NBR-009** University Township | 4 | 6 | 5 | 5 |
| **NBR-010** Peripheral Settlement | 5 | 3 | **10** | 5 |
| **Column total (max units)** | **23** | **60** | **65** | **46** |
| **Max cost if fully deployed (₹ lakh)** | **184** | **720** | **325** | **920** |

Total maximum cost if all capacities deployed: ₹ 2,149 lakh.
Default budget (₹ 500 lakh) is 23% of the theoretical maximum — forcing real trade-offs.

---

## 5. Optimisation Configuration (runtime, not stored)

These values are passed at runtime by the user or API and are not stored in the dataset files.

| Parameter | Default | Description |
|---|---|---|
| `budget_lakh` | — (required) | Total capital budget in ₹ lakh. |
| `equity_threshold` | 0.30 | Min fraction of budget to high-vulnerability neighbourhoods. Configurable. |
| `weights.environmental` | 0.50 | Objective weight on environmental benefit. |
| `weights.equity` | 0.30 | Objective weight on equity-weighted benefit. |
| `weights.cost_efficiency` | 0.20 | Objective weight on cost efficiency. |
| `max_interventions_per_neighbourhood` | 3 | Max distinct intervention types per neighbourhood. |
| `high_vulnerability_svi_threshold` | 60.0 | SVI threshold for equity classification. |

---

## 6. How the Dataset Supports Each Constraint (Stage 3 Preview)

| Constraint | LP formulation | Data fields used |
|---|---|---|
| **Budget** | `Σ cost_per_unit_lakh × x[n,i] ≤ budget_lakh` | `cost_per_unit_lakh`, `budget_lakh` |
| **Land / capacity** | `x[n,i] ≤ max_units[n,i]` | `max_units` in capacities |
| **Equity floor** | `Σ_{n ∈ HV, i} cost_per_unit_lakh × x[n,i] ≥ equity_threshold × budget_lakh` | `social_vulnerability_index`, `equity_threshold` |
| **Intervention type limit** | `Σ_i 𝟙(x[n,i]>0) ≤ max_interventions_per_neighbourhood` | `max_interventions_per_neighbourhood` |
| **Non-negativity & integer** | `x[n,i] ∈ ℤ≥0` | Implicit LP variable bounds |

---

## 7. Known Limitations

1. **No temporal dimension.** The dataset captures a single point-in-time snapshot. Climate change trajectories are addressed only through scenario analysis (Stage 5), not through time-series data.
2. **Synthetic effectiveness scores.** Effectiveness coefficients are relative indicators calibrated for modelling purposes. They are not derived from controlled field experiments or meta-analyses.
3. **Single intervention type per category.** The catalogue uses one intervention per category. Real-world portfolios would include intensity variants (e.g., intensive vs. extensive green roofs).
4. **No co-benefits or interactions.** Combining two interventions in the same neighbourhood may produce super- or sub-additive effects. This dataset models them as independent.
5. **No implementation risk.** Procurement delays, community resistance, and supply chain constraints are not quantified.
6. **Geography is fictional.** Coordinates are synthetic and placed in a generalised South Asian urban context for visual plausibility only.

---

*Data generated: Stage 2, UrbanSage AI. All synthetic.*
