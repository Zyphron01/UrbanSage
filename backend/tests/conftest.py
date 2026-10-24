"""
Shared pytest fixtures for UrbanSage AI test suite.

Fixtures here are available to all test modules automatically.
Session-scoped fixtures are used for expensive operations (loading the full
synthetic dataset) to avoid repeated I/O across the test session.
"""

from __future__ import annotations

import pytest

from app.data.loader import load_default_dataset
from app.data.schemas import DatasetBundle


# ---------------------------------------------------------------------------
# Dataset fixture (session-scoped — loaded once per test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def default_dataset() -> DatasetBundle:
    """
    Load the built-in synthetic dataset once per test session.

    All tests that need the full validated bundle should declare this fixture
    rather than calling load_default_dataset() directly.
    """
    return load_default_dataset()


# ---------------------------------------------------------------------------
# Valid raw-dict factories (used in test_schemas.py to build test objects)
# ---------------------------------------------------------------------------


def make_neighbourhood(**overrides) -> dict:
    """Return a valid neighbourhood dict, optionally overriding fields."""
    base = {
        "id": "NBR-099",
        "name": "Test Neighbourhood",
        "area_sqkm": 2.0,
        "population": 20000,
        "social_vulnerability_index": 50.0,
        "heat_risk": 50.0,
        "flood_risk": 50.0,
        "water_stress": 50.0,
        "current_green_cover_pct": 15.0,
        "land_availability": {
            "urban_forest_sqm": 5000.0,
            "green_roof_sqm": 3000.0,
            "rainwater_harvesting_sites": 4,
            "drainage_sqm": 6000.0,
        },
        "centroid_lat": 21.15,
        "centroid_lon": 79.10,
        "description": "A test neighbourhood for unit testing.",
        "data_source": "SYNTHETIC",
    }
    base.update(overrides)
    return base


def make_intervention(**overrides) -> dict:
    """Return a valid intervention dict, optionally overriding fields."""
    base = {
        "id": "INT-099",
        "name": "Test Intervention",
        "category": "urban_forest",
        "description": "A test intervention for unit testing.",
        "unit_description": "One test unit.",
        "cost_per_unit_lakh": 10.0,
        "land_requirement_sqm_per_unit": 500.0,
        "maintenance_cost_annual_lakh": 1.0,
        "implementation_months": 6,
        "effectiveness": {
            "heat_reduction": 50.0,
            "flood_reduction": 40.0,
            "water_stress_reduction": 30.0,
            "carbon_reduction": 45.0,
        },
        "effectiveness_assumption_notes": "Synthetic test assumptions.",
        "data_source": "SYNTHETIC",
    }
    base.update(overrides)
    return base


def make_capacity(**overrides) -> dict:
    """Return a valid capacity dict, optionally overriding fields."""
    base = {
        "neighbourhood_id": "NBR-099",
        "intervention_id": "INT-099",
        "max_units": 3,
        "feasibility_notes": "Test feasibility note.",
        "data_source": "SYNTHETIC",
    }
    base.update(overrides)
    return base
