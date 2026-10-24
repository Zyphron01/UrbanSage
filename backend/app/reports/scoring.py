"""
UrbanSage AI — Transparent Citizen Report Scoring Engine
=========================================================
Explicit, deterministic calculation of Urgency Score and Evidence Confidence Score
for citizen environmental problem reports.

Mathematical Principles & Design Safeguards:
--------------------------------------------
1. Full Transparency:
   All scoring formulas are deterministic, linear combinations with documented weights,
   explicit input domains, and bounded outputs in [0.0, 100.0].
2. Decoupled Concepts:
   Urgency Score (operational time-sensitivity) is strictly separated from
   Evidence Confidence Score (documentary completeness).
3. Anti-Inflation & Anti-Gaming:
   Duplicate submissions from the same reporter or identical device do NOT increase
   corroboration or evidence scores.
4. No False Scientific Claims:
   Evidence Confidence measures documentary auditability (photo attached, description
   length, coordinates, contact provided). It does NOT constitute scientific ground-truth
   verification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.reports.models import PhotoMetadata, ProblemCategory


# ---------------------------------------------------------------------------
# Urgency Score Parameters
#
# IMPORTANT MODELLING ASSUMPTION:
# The category acute hazard weights below are heuristic operational assumptions
# representing administrative triaging priorities (e.g. immediate mobility and contamination
# hazards from flooding vs. chronic ecological degradation from loss of green cover).
# They are NOT empirically measured physical damage functions or certified scientific hazard
# calculations, and must not be presented as validated real-world measurements.
# ---------------------------------------------------------------------------

CATEGORY_ACUTE_HAZARD_SCORES = {
    ProblemCategory.FLOODING_DRAINAGE: 90.0,  # Acute physical hazard, contamination, road cutoffs
    ProblemCategory.HEAT: 75.0,              # Heatstroke risk, elder/infant mortality exposure
    ProblemCategory.WATER_SCARCITY: 70.0,    # Basic survival resource deficit
    ProblemCategory.LOSS_OF_GREEN_COVER: 50.0,# Severe environmental harm, but lower acute casualty risk
}

URGENCY_WEIGHT_SEVERITY: float = 0.40
URGENCY_WEIGHT_ACUTE_HAZARD: float = 0.30
URGENCY_WEIGHT_VULNERABILITY: float = 0.20
URGENCY_WEIGHT_CORROBORATION: float = 0.10

NEUTRAL_WARD_SVI_FALLBACK: float = 50.0
MAX_CORROBORATION_COUNT: int = 5


def calculate_urgency_score(
    severity: int,
    category: ProblemCategory,
    ward_svi: Optional[float] = None,
    corroborating_reports_count: int = 0,
) -> float:
    """
    Calculate the operational urgency score for a citizen report.

    Parameters
    ----------
    severity : int
        Citizen-reported severity rating from 1 (minor) to 5 (emergency).
    category : ProblemCategory
        Environmental problem category.
    ward_svi : Optional[float]
        Social Vulnerability Index (0–100) of the affected ward, if linked.
        If missing or unknown, defaults safely to 50.0 (neutral baseline).
    corroborating_reports_count : int
        Count of distinct independent citizen reports in the same geographic cluster
        (e.g. within 500m within 72 hours). Capped at 5 to prevent runaway escalation.

    Returns
    -------
    float
        Urgency score strictly bounded between 0.0 and 100.0, rounded to 2 decimal places.

    Formula
    -------
        severity_score = (severity / 5.0) * 100.0
        acute_score    = CATEGORY_ACUTE_HAZARD_SCORES[category]
        svi_score      = ward_svi if ward_svi is not None else 50.0
        corrob_score   = min(corroborating_reports_count, 5) * 20.0

        urgency_score  = (0.40 * severity_score)
                       + (0.30 * acute_score)
                       + (0.20 * svi_score)
                       + (0.10 * corrob_score)
    """
    # 1. Citizen severity component (20.0 to 100.0)
    clamped_severity = max(1, min(5, int(severity)))
    severity_score = (clamped_severity / 5.0) * 100.0

    # 2. Acute hazard profile (50.0 to 90.0)
    acute_score = CATEGORY_ACUTE_HAZARD_SCORES.get(category, 50.0)

    # 3. Socio-environmental vulnerability context (0.0 to 100.0)
    if ward_svi is not None:
        svi_score = max(0.0, min(100.0, float(ward_svi)))
    else:
        svi_score = NEUTRAL_WARD_SVI_FALLBACK

    # 4. Multi-reporter corroboration bonus (0.0 to 100.0)
    # Safeguard: distinct count is capped; duplicates from the same reporter are 0
    safe_corrob_count = max(0, min(MAX_CORROBORATION_COUNT, int(corroborating_reports_count)))
    corrob_score = safe_corrob_count * 20.0

    raw_urgency = (
        (URGENCY_WEIGHT_SEVERITY * severity_score)
        + (URGENCY_WEIGHT_ACUTE_HAZARD * acute_score)
        + (URGENCY_WEIGHT_VULNERABILITY * svi_score)
        + (URGENCY_WEIGHT_CORROBORATION * corrob_score)
    )

    return round(max(0.0, min(100.0, raw_urgency)), 2)


# ---------------------------------------------------------------------------
# Evidence Confidence Score Parameters
# ---------------------------------------------------------------------------

DESC_MAX_POINTS: float = 30.0
LOC_MAX_POINTS: float = 25.0
PHOTO_MAX_POINTS: float = 30.0
CONTACT_MAX_POINTS: float = 15.0


def calculate_evidence_confidence_score(
    description: str,
    latitude: float,
    longitude: float,
    location_description: Optional[str] = None,
    photos: Optional[List[PhotoMetadata]] = None,
    reporter_contact: Optional[str] = None,
    submission_time: Optional[datetime] = None,
) -> float:
    """
    Calculate the documentary completeness and auditability score for a citizen report.

    IMPORTANT DISCLAIMER:
    ---------------------
    This score evaluates the *structural quality and completeness of evidence*
    provided by the citizen to assist municipal responders in field investigation.
    It does NOT prove real-world occurrence, scientific truth, or physical ground truth.
    Citizen-submitted photos are documentary evidence, not independent verification.

    Parameters
    ----------
    description : str
        Citizen narrative of the issue.
    latitude : float
        Latitude coordinate (-90 to +90).
    longitude : float
        Longitude coordinate (-180 to +180).
    location_description : Optional[str]
        Landmark, street address, or descriptive text.
    photos : Optional[List[PhotoMetadata]]
        List of attached photo metadata objects.
    reporter_contact : Optional[str]
        Phone or email provided for follow-up verification.
    submission_time : Optional[datetime]
        Reference timestamp for photo recency calculation (defaults to now UTC).

    Returns
    -------
    float
        Evidence confidence score strictly bounded between 0.0 and 100.0,
        rounded to 2 decimal places.

    Point Rubric (Additive, Max 100.0)
    ----------------------------------
    1. Description Richness (Max 30 pts):
       - len < 20 chars:       5.0 pts
       - 20 <= len < 60 chars: 15.0 pts
       - 60 <= len < 150 chars: 25.0 pts
       - len >= 150 chars:     30.0 pts
    2. Location Precision (Max 25 pts):
       - Valid coordinates:    15.0 pts
       - Landmark/street text: 10.0 pts (if text >= 5 chars)
    3. Supporting Photos (Max 30 pts):
       - Photo metadata present: 20.0 pts
       - Recency: captured within 48h of submission: +10.0 pts
    4. Reporter Contactability (Max 15 pts):
       - Contact channel provided (>= 5 chars): 15.0 pts
       - Anonymous / missing:  0.0 pts
    """
    score = 0.0

    # 1. Description richness (up to 30 pts)
    cleaned_desc = (description or "").strip()
    desc_len = len(cleaned_desc)
    if desc_len >= 150:
        score += 30.0
    elif desc_len >= 60:
        score += 25.0
    elif desc_len >= 20:
        score += 15.0
    elif desc_len > 0:
        score += 5.0

    # 2. Location precision (up to 25 pts)
    # Valid coordinates in bounds
    if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
        score += 15.0

    cleaned_loc = (location_description or "").strip()
    if len(cleaned_loc) >= 5:
        score += 10.0

    # 3. Photo documentation (up to 30 pts)
    photo_list = photos or []
    if len(photo_list) > 0:
        score += 20.0
        # Check recency if capture timestamp is present
        ref_time = submission_time or datetime.now(timezone.utc)
        recent_photo_found = False
        for p in photo_list:
            if p.captured_at is not None:
                # Ensure timezone aware comparison
                p_time = p.captured_at
                if p_time.tzinfo is None:
                    p_time = p_time.replace(tzinfo=timezone.utc)
                delta_hours = abs((ref_time - p_time).total_seconds()) / 3600.0
                if delta_hours <= 48.0:
                    recent_photo_found = True
                    break
        if recent_photo_found:
            score += 10.0

    # 4. Reporter contactability (up to 15 pts)
    cleaned_contact = (reporter_contact or "").strip()
    if len(cleaned_contact) >= 5:
        score += 15.0

    return round(max(0.0, min(100.0, score)), 2)
