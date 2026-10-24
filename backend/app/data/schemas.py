"""
UrbanSage AI — Data Schemas  (Stage 2)
=======================================
All Pydantic v2 models for neighbourhoods, interventions, capacity constraints,
and optimisation configuration.

Design principles
-----------------
* Every field carries a unit, a valid range, and a description.
* All data that originates from synthetic estimates is tagged with
  ``data_source: Literal["SYNTHETIC"]``.  This field must be present on every
  stored record so that downstream code can never silently treat synthetic
  values as real measurements.
* Computed properties (``is_high_vulnerability``, ``composite_risk``, etc.) are
  kept on the model so business logic does not leak into the API layer.
* ``DatasetBundle`` validates referential integrity across the three collections
  so the optimisation engine always receives a self-consistent input.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Sentinel type — every stored record must carry this tag
# ---------------------------------------------------------------------------

SYNTHETIC = Literal["SYNTHETIC"]

# Default SVI threshold for classifying a neighbourhood as "high vulnerability".
# Exposed as a constant so tests and the optimiser both reference the same value.
HIGH_VULNERABILITY_SVI_DEFAULT: float = 60.0


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class InterventionCategory(str, Enum):
    """
    The four supported sustainability intervention categories.

    Adding a new category here requires corresponding updates to:
    - ``LandAvailability`` (new capacity field)
    - The synthetic dataset JSON files
    - The optimisation engine (Stage 3)
    """

    URBAN_FOREST = "urban_forest"
    GREEN_ROOF = "green_roof"
    RAINWATER_HARVESTING = "rainwater_harvesting"
    DRAINAGE = "drainage"


# ---------------------------------------------------------------------------
# Nested / sub-models
# ---------------------------------------------------------------------------


class EffectivenessEstimate(BaseModel):
    """
    Per-unit environmental effectiveness scores for a single intervention type.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  IMPORTANT — SYNTHETIC ESTIMATES                                     ║
    ║  These scores are relative effectiveness indicators on a 0–100 scale ║
    ║  derived from published urban sustainability literature and adjusted  ║
    ║  for modelling purposes.  They do NOT represent measured outcomes    ║
    ║  from deployed interventions and must not be presented as such.      ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Each score represents the effectiveness of *one unit* of the intervention
    in reducing the corresponding environmental stress.  A score of 100 would
    mean the intervention completely eliminates that stress within its
    deployment footprint, which is never realistic; actual values are
    intentionally conservative.
    """

    heat_reduction: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Relative heat-island reduction benefit per unit (0–100 scale). "
            "Higher values indicate greater cooling effect on the local microclimate."
        ),
    )
    flood_reduction: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Relative flood-risk reduction benefit per unit (0–100 scale). "
            "Reflects stormwater retention, infiltration, or conveyance improvement."
        ),
    )
    water_stress_reduction: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Relative water-stress reduction benefit per unit (0–100 scale). "
            "Reflects harvesting, reuse, or groundwater recharge."
        ),
    )
    carbon_reduction: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Relative carbon-sequestration / emissions-reduction benefit per unit "
            "(0–100 scale).  Includes direct sequestration and indirect energy savings."
        ),
    )

    @property
    def composite(self) -> float:
        """Unweighted average across all four environmental dimensions."""
        return (
            self.heat_reduction
            + self.flood_reduction
            + self.water_stress_reduction
            + self.carbon_reduction
        ) / 4.0


class LandAvailability(BaseModel):
    """
    Estimated available land or infrastructure capacity for each intervention
    category within a neighbourhood.

    These figures inform the upper bounds in ``NeighbourhoodCapacity`` but are
    stored separately so that non-technical users can inspect them without
    reading the full capacity matrix.
    """

    urban_forest_sqm: float = Field(
        ...,
        ge=0,
        description=(
            "Open land area (sqm) identified as suitable for urban forestry. "
            "Excludes land with structural constraints, flood hazard, or tenure issues. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    green_roof_sqm: float = Field(
        ...,
        ge=0,
        description=(
            "Flat rooftop area (sqm) structurally capable of supporting a green roof. "
            "A structural survey is required before deployment. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    rainwater_harvesting_sites: int = Field(
        ...,
        ge=0,
        description=(
            "Number of viable sites for community rainwater-harvesting tank installation. "
            "Each site supports one 10,000-litre system. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    drainage_sqm: float = Field(
        ...,
        ge=0,
        description=(
            "Road and pavement area (sqm) eligible for drainage improvement works "
            "including permeable pavement and bioswale installation. "
            "SYNTHETIC ESTIMATE."
        ),
    )


# ---------------------------------------------------------------------------
# Primary models
# ---------------------------------------------------------------------------


class Neighbourhood(BaseModel):
    """
    A single urban neighbourhood record containing risk indicators,
    demographic data, and land-capacity information.

    Risk indicators (``heat_risk``, ``flood_risk``, ``water_stress``) and the
    ``social_vulnerability_index`` are all on a 0–100 synthetic scoring scale.
    They are modelling inputs, not real-world measurements.

    Constraint mapping (Stage 3 reference)
    ---------------------------------------
    * ``social_vulnerability_index`` → identifies high-vulnerability
      neighbourhoods for the equity floor constraint.
    * ``land_availability`` → informs upper bounds in ``NeighbourhoodCapacity``.
    * ``heat_risk``, ``flood_risk``, ``water_stress`` → priority weights in the
      objective function (higher risk → higher marginal benefit of intervention).
    """

    id: str = Field(
        ...,
        pattern=r"^NBR-\d{3}$",
        description="Unique neighbourhood identifier.  Format: NBR-NNN (e.g. NBR-001).",
    )
    name: str = Field(..., min_length=1, description="Human-readable neighbourhood name.")
    area_sqkm: float = Field(
        ...,
        gt=0,
        description="Total neighbourhood area in square kilometres.",
    )
    population: int = Field(
        ...,
        gt=0,
        description="Estimated resident population (SYNTHETIC ESTIMATE).",
    )
    social_vulnerability_index: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Composite social vulnerability score (0–100). "
            "Higher = greater vulnerability. "
            "Derived from income levels, population density, age distribution, "
            "and access-to-services indicators. "
            "SYNTHETIC ESTIMATE — not a real census measurement."
        ),
    )
    heat_risk: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Urban heat-island risk score (0–100). "
            "Higher = greater heat exposure and urban heat island intensity. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    flood_risk: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Flood exposure risk score (0–100). "
            "Higher = greater probability and severity of flood events. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    water_stress: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Water scarcity and supply-stress score (0–100). "
            "Higher = greater imbalance between supply and demand. "
            "SYNTHETIC ESTIMATE."
        ),
    )
    current_green_cover_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Estimated percentage of neighbourhood area currently under green cover "
            "(parks, trees, grass, etc.).  SYNTHETIC ESTIMATE."
        ),
    )
    land_availability: LandAvailability = Field(
        ...,
        description=(
            "Estimated land and infrastructure capacity for each intervention type. "
            "Authoritative upper bounds are in NeighbourhoodCapacity."
        ),
    )
    centroid_lat: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude of neighbourhood centroid for map display (decimal degrees).",
    )
    centroid_lon: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude of neighbourhood centroid for map display (decimal degrees).",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Plain-English summary of the neighbourhood's characteristics.",
    )
    data_source: SYNTHETIC = Field(
        ...,
        description=(
            "Must be the literal string 'SYNTHETIC'. "
            "Confirms that this record originates from synthetic data generation, "
            "not from real-world measurement or official survey."
        ),
    )

    # ------------------------------------------------------------------
    # Computed properties (not stored; derived at runtime)
    # ------------------------------------------------------------------

    @property
    def is_high_vulnerability(self) -> bool:
        """
        Returns True when ``social_vulnerability_index`` is at or above the
        ``HIGH_VULNERABILITY_SVI_DEFAULT`` threshold (60.0).

        Used by the optimisation engine to identify neighbourhoods subject to
        the equity allocation floor constraint.
        """
        return self.social_vulnerability_index >= HIGH_VULNERABILITY_SVI_DEFAULT

    @property
    def composite_risk(self) -> float:
        """
        Unweighted average of heat, flood, and water-stress risk scores.

        Provides a single priority signal for the objective function.
        Range: 0.0–100.0.
        """
        return (self.heat_risk + self.flood_risk + self.water_stress) / 3.0

    @property
    def population_density_per_sqkm(self) -> float:
        """Estimated population density (persons per km²)."""
        return self.population / self.area_sqkm


class InterventionType(BaseModel):
    """
    A single sustainability intervention type — its cost, land requirements,
    and estimated environmental effectiveness per unit deployed.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  IMPORTANT — SYNTHETIC COST AND EFFECTIVENESS ESTIMATES              ║
    ║  All monetary values are in Indian Rupees lakh (₹ lakh).            ║
    ║  Effectiveness scores are synthetic relative indicators on a 0–100  ║
    ║  scale.  They are modelling assumptions, not measured outcomes.     ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Constraint mapping (Stage 3 reference)
    ---------------------------------------
    * ``cost_per_unit_lakh`` → budget constraint coefficients.
    * ``land_requirement_sqm_per_unit`` → land capacity validation.
    * ``effectiveness`` → objective function benefit coefficients.
    """

    id: str = Field(
        ...,
        pattern=r"^INT-\d{3}$",
        description="Unique intervention identifier.  Format: INT-NNN (e.g. INT-001).",
    )
    name: str = Field(..., min_length=1)
    category: InterventionCategory = Field(
        ...,
        description="One of the four supported intervention categories.",
    )
    description: str = Field(..., min_length=1)
    unit_description: str = Field(
        ...,
        description="Plain-English definition of what one 'unit' of this intervention represents.",
    )
    cost_per_unit_lakh: float = Field(
        ...,
        gt=0,
        description=(
            "Capital implementation cost per unit in ₹ lakh. "
            "Excludes annual maintenance.  SYNTHETIC ESTIMATE."
        ),
    )
    land_requirement_sqm_per_unit: float = Field(
        ...,
        ge=0,
        description=(
            "Land or rooftop area consumed per unit (sqm). "
            "Zero for interventions with negligible footprint."
        ),
    )
    maintenance_cost_annual_lakh: float = Field(
        ...,
        ge=0,
        description=(
            "Recurring annual maintenance cost per deployed unit in ₹ lakh. "
            "SYNTHETIC ESTIMATE.  Not included in the capital budget constraint."
        ),
    )
    implementation_months: int = Field(
        ...,
        ge=1,
        description="Typical end-to-end implementation timeline in months.",
    )
    effectiveness: EffectivenessEstimate = Field(
        ...,
        description="Estimated environmental effectiveness scores per unit.",
    )
    effectiveness_assumption_notes: str = Field(
        ...,
        min_length=1,
        description=(
            "Documents the basis, assumptions, and limitations of the effectiveness "
            "estimates.  Must be surfaced in any public-facing explanation."
        ),
    )
    data_source: SYNTHETIC


class NeighbourhoodCapacity(BaseModel):
    """
    Maximum number of units of a given intervention that can be deployed
    in a specific neighbourhood, constrained by land, structural, and policy limits.

    This is the *authoritative* capacity source for the optimisation engine.
    A ``max_units`` value of 0 means the intervention is infeasible in that
    neighbourhood and the LP variable will be effectively fixed to zero.

    Constraint mapping (Stage 3 reference)
    ---------------------------------------
    * ``max_units`` → upper bound on the LP decision variable x[neighbourhood, intervention].
    """

    neighbourhood_id: str = Field(
        ...,
        pattern=r"^NBR-\d{3}$",
        description="Foreign key to Neighbourhood.id.",
    )
    intervention_id: str = Field(
        ...,
        pattern=r"^INT-\d{3}$",
        description="Foreign key to InterventionType.id.",
    )
    max_units: int = Field(
        ...,
        ge=0,
        description=(
            "Maximum deployable units.  "
            "0 = intervention is not feasible in this neighbourhood."
        ),
    )
    feasibility_notes: str = Field(
        ...,
        description=(
            "Rationale for the capacity limit, documenting physical, structural, "
            "or policy constraints.  Surfaced in decision explanations."
        ),
    )
    data_source: SYNTHETIC


# ---------------------------------------------------------------------------
# Configuration models (runtime — not stored in the synthetic dataset)
# ---------------------------------------------------------------------------


class OptimisationWeights(BaseModel):
    """
    Relative importance weights for the three components of the objective
    function.  The three values must sum to exactly 1.0.

    The weighted objective is:
        maximise Σ (w_env · benefit_env + w_eq · equity_bonus − w_cost · cost) · x

    Default values reflect a bias towards environmental outcomes and equity,
    with cost efficiency as a secondary consideration.
    """

    environmental: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight on total environmental benefit score (default 0.5).",
    )
    equity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Weight on benefit delivered to high-vulnerability neighbourhoods "
            "(default 0.3).  Acts as an equity multiplier in the objective."
        ),
    )
    cost_efficiency: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description=(
            "Weight on cost efficiency — lower cost for equivalent benefit is favoured "
            "(default 0.2).  Applied as a penalty term."
        ),
    )

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> OptimisationWeights:
        total = self.environmental + self.equity + self.cost_efficiency
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Optimisation weights must sum to exactly 1.0; got {total:.6f}. "
                f"(environmental={self.environmental}, equity={self.equity}, "
                f"cost_efficiency={self.cost_efficiency})"
            )
        return self


class OptimisationConfig(BaseModel):
    """
    Runtime configuration supplied by the user or API for a single optimisation
    run.  This model is NOT stored in the synthetic dataset files.

    All thresholds and weights are configurable so that scenario analysis can
    vary them without touching the data layer.
    """

    budget_lakh: float = Field(
        ...,
        gt=0,
        description="Total available capital budget in ₹ lakh for this optimisation run.",
    )
    equity_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum fraction of the total budget that must be allocated to "
            "interventions in high-vulnerability neighbourhoods.  "
            "Default is 0.30 (30 %).  Configurable per scenario."
        ),
    )
    weights: OptimisationWeights = Field(
        default_factory=OptimisationWeights,
        description="Objective function weights.",
    )
    max_interventions_per_neighbourhood: int = Field(
        default=3,
        ge=1,
        le=4,
        description=(
            "Maximum number of distinct intervention types that can be deployed "
            "in any single neighbourhood.  Prevents unrealistic stacking of all "
            "four types in one area.  Range: 1–4."
        ),
    )
    high_vulnerability_svi_threshold: float = Field(
        default=HIGH_VULNERABILITY_SVI_DEFAULT,
        ge=0.0,
        le=100.0,
        description=(
            "SVI score at or above which a neighbourhood is classified as "
            "'high vulnerability' for equity constraint purposes.  "
            f"Default is {HIGH_VULNERABILITY_SVI_DEFAULT}."
        ),
    )


# ---------------------------------------------------------------------------
# Dataset bundle — validated collection ready for the optimisation engine
# ---------------------------------------------------------------------------


class DatasetBundle(BaseModel):
    """
    Complete, validated dataset passed to the optimisation engine.

    Validates:
    - No duplicate neighbourhood IDs.
    - No duplicate intervention IDs.
    - Every capacity record references a known neighbourhood and intervention.
    - No duplicate (neighbourhood_id, intervention_id) pairs in capacities.

    Provides convenience accessors used by the optimiser:
    - ``high_vulnerability_neighbourhood_ids``
    - ``capacity_matrix()``
    """

    neighbourhoods: list[Neighbourhood]
    interventions: list[InterventionType]
    capacities: list[NeighbourhoodCapacity]

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> DatasetBundle:
        nbr_ids = [n.id for n in self.neighbourhoods]
        int_ids = [i.id for i in self.interventions]

        # --- Duplicate neighbourhood IDs ---
        if len(nbr_ids) != len(set(nbr_ids)):
            duplicates = sorted({x for x in nbr_ids if nbr_ids.count(x) > 1})
            raise ValueError(f"Duplicate neighbourhood IDs detected: {duplicates}")

        # --- Duplicate intervention IDs ---
        if len(int_ids) != len(set(int_ids)):
            duplicates = sorted({x for x in int_ids if int_ids.count(x) > 1})
            raise ValueError(f"Duplicate intervention IDs detected: {duplicates}")

        nbr_id_set = set(nbr_ids)
        int_id_set = set(int_ids)

        # --- Referential integrity in the capacity matrix ---
        bad_nbr = [
            c.neighbourhood_id
            for c in self.capacities
            if c.neighbourhood_id not in nbr_id_set
        ]
        if bad_nbr:
            raise ValueError(
                f"Capacity records reference unknown neighbourhood IDs: {sorted(set(bad_nbr))}. "
                f"Valid IDs: {sorted(nbr_id_set)}"
            )

        bad_int = [
            c.intervention_id
            for c in self.capacities
            if c.intervention_id not in int_id_set
        ]
        if bad_int:
            raise ValueError(
                f"Capacity records reference unknown intervention IDs: {sorted(set(bad_int))}. "
                f"Valid IDs: {sorted(int_id_set)}"
            )

        # --- Duplicate (neighbourhood, intervention) pairs ---
        cap_pairs = [(c.neighbourhood_id, c.intervention_id) for c in self.capacities]
        if len(cap_pairs) != len(set(cap_pairs)):
            seen: set[tuple[str, str]] = set()
            dups = sorted({p for p in cap_pairs if p in seen or seen.add(p)})  # type: ignore[func-returns-value]
            raise ValueError(
                f"Duplicate (neighbourhood_id, intervention_id) pairs in capacities: {dups}"
            )

        return self

    @property
    def high_vulnerability_neighbourhood_ids(self) -> set[str]:
        """IDs of neighbourhoods whose SVI meets the default high-vulnerability threshold."""
        return {n.id for n in self.neighbourhoods if n.is_high_vulnerability}

    def capacity_matrix(self) -> dict[tuple[str, str], int]:
        """
        Returns a flat lookup: ``{(neighbourhood_id, intervention_id): max_units}``.

        Used by the optimisation engine to set per-variable upper bounds.
        """
        return {
            (c.neighbourhood_id, c.intervention_id): c.max_units
            for c in self.capacities
        }

    def intervention_by_id(self, intervention_id: str) -> InterventionType:
        """Look up an intervention by ID.  Raises KeyError if not found."""
        for iv in self.interventions:
            if iv.id == intervention_id:
                return iv
        raise KeyError(f"Intervention '{intervention_id}' not found in dataset.")

    def neighbourhood_by_id(self, neighbourhood_id: str) -> Neighbourhood:
        """Look up a neighbourhood by ID.  Raises KeyError if not found."""
        for nb in self.neighbourhoods:
            if nb.id == neighbourhood_id:
                return nb
        raise KeyError(f"Neighbourhood '{neighbourhood_id}' not found in dataset.")
