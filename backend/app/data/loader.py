"""
UrbanSage AI — Data Loader  (Stage 2)
======================================
Loads, validates, and bundles synthetic neighbourhood and intervention datasets
from JSON files into typed Pydantic models.

All loading functions surface clear, actionable error messages so that schema
mismatches discovered during testing or live operation are immediately
diagnosable without reading Pydantic internals.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.data.schemas import (
    DatasetBundle,
    InterventionType,
    Neighbourhood,
    NeighbourhoodCapacity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default synthetic data directory
# ---------------------------------------------------------------------------

# Resolved relative to this file's location so the loader works regardless of
# the working directory when pytest or uvicorn is started.
_SYNTHETIC_DIR: Path = Path(__file__).parent / "synthetic"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_json_array(path: Path) -> list[dict]:
    """
    Read a JSON file and return its contents as a list of dicts.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file is not valid JSON or its top-level element is not an array.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            "Make sure the synthetic dataset is present under "
            "backend/app/data/synthetic/."
        )
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Expected a JSON array (list) in {path}; "
            f"got {type(data).__name__}.  "
            "Each dataset file must contain a top-level JSON array."
        )
    return data  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------


def load_neighbourhoods(path: Path | None = None) -> list[Neighbourhood]:
    """
    Load and validate neighbourhood records from a JSON file.

    Parameters
    ----------
    path:
        Path to a ``neighbourhoods.json`` file.  Defaults to the built-in
        synthetic dataset at ``app/data/synthetic/neighbourhoods.json``.

    Returns
    -------
    list[Neighbourhood]
        A list of fully validated Neighbourhood objects.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If any record fails Pydantic validation.  All errors are collected
        and reported together rather than stopping at the first failure.
    """
    resolved = path or (_SYNTHETIC_DIR / "neighbourhoods.json")
    raw_records = _load_json_array(resolved)

    validated: list[Neighbourhood] = []
    errors: list[str] = []

    for index, record in enumerate(raw_records):
        try:
            validated.append(Neighbourhood.model_validate(record))
        except ValidationError as exc:
            record_id = record.get("id", "<missing id>")
            errors.append(
                f"  Record {index} (id={record_id!r}):\n"
                + "\n".join(f"    {e['loc']} → {e['msg']}" for e in exc.errors())
            )

    if errors:
        raise ValueError(
            f"Neighbourhood validation failed with {len(errors)} error(s) in {resolved}:\n"
            + "\n".join(errors)
        )

    logger.info("Loaded %d neighbourhood records from %s", len(validated), resolved)
    return validated


def load_interventions(path: Path | None = None) -> list[InterventionType]:
    """
    Load and validate intervention type records from a JSON file.

    Parameters
    ----------
    path:
        Path to an ``interventions.json`` file.  Defaults to the synthetic dataset.

    Returns
    -------
    list[InterventionType]

    Raises
    ------
    FileNotFoundError, ValueError
        As described for :func:`load_neighbourhoods`.
    """
    resolved = path or (_SYNTHETIC_DIR / "interventions.json")
    raw_records = _load_json_array(resolved)

    validated: list[InterventionType] = []
    errors: list[str] = []

    for index, record in enumerate(raw_records):
        try:
            validated.append(InterventionType.model_validate(record))
        except ValidationError as exc:
            record_id = record.get("id", "<missing id>")
            errors.append(
                f"  Record {index} (id={record_id!r}):\n"
                + "\n".join(f"    {e['loc']} → {e['msg']}" for e in exc.errors())
            )

    if errors:
        raise ValueError(
            f"Intervention validation failed with {len(errors)} error(s) in {resolved}:\n"
            + "\n".join(errors)
        )

    logger.info("Loaded %d intervention records from %s", len(validated), resolved)
    return validated


def load_capacities(path: Path | None = None) -> list[NeighbourhoodCapacity]:
    """
    Load and validate neighbourhood–intervention capacity records from a JSON file.

    Parameters
    ----------
    path:
        Path to a ``capacities.json`` file.  Defaults to the synthetic dataset.

    Returns
    -------
    list[NeighbourhoodCapacity]

    Raises
    ------
    FileNotFoundError, ValueError
        As described for :func:`load_neighbourhoods`.
    """
    resolved = path or (_SYNTHETIC_DIR / "capacities.json")
    raw_records = _load_json_array(resolved)

    validated: list[NeighbourhoodCapacity] = []
    errors: list[str] = []

    for index, record in enumerate(raw_records):
        try:
            validated.append(NeighbourhoodCapacity.model_validate(record))
        except ValidationError as exc:
            nbr = record.get("neighbourhood_id", "?")
            inv = record.get("intervention_id", "?")
            errors.append(
                f"  Record {index} ({nbr}/{inv}):\n"
                + "\n".join(f"    {e['loc']} → {e['msg']}" for e in exc.errors())
            )

    if errors:
        raise ValueError(
            f"Capacity validation failed with {len(errors)} error(s) in {resolved}:\n"
            + "\n".join(errors)
        )

    logger.info("Loaded %d capacity records from %s", len(validated), resolved)
    return validated


def load_dataset(
    neighbourhoods_path: Path | None = None,
    interventions_path: Path | None = None,
    capacities_path: Path | None = None,
) -> DatasetBundle:
    """
    Load all three dataset components, validate each individually, then
    validate cross-collection referential integrity via ``DatasetBundle``.

    Parameters
    ----------
    neighbourhoods_path, interventions_path, capacities_path:
        Optional overrides for each file path.  Defaults to the synthetic dataset.

    Returns
    -------
    DatasetBundle
        A fully validated bundle ready to pass to the optimisation engine.

    Raises
    ------
    FileNotFoundError
        If any required file is missing.
    ValueError
        If validation fails at any stage (individual or referential).
    """
    neighbourhoods = load_neighbourhoods(neighbourhoods_path)
    interventions = load_interventions(interventions_path)
    capacities = load_capacities(capacities_path)

    try:
        bundle = DatasetBundle(
            neighbourhoods=neighbourhoods,
            interventions=interventions,
            capacities=capacities,
        )
    except ValidationError as exc:
        raise ValueError(
            f"Dataset referential integrity check failed:\n{exc}"
        ) from exc

    logger.info(
        "DatasetBundle validated: %d neighbourhoods, %d interventions, %d capacity records.",
        len(bundle.neighbourhoods),
        len(bundle.interventions),
        len(bundle.capacities),
    )
    return bundle


def load_default_dataset() -> DatasetBundle:
    """
    Convenience wrapper: load the built-in synthetic dataset with default paths.

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  SYNTHETIC DATA DISCLAIMER                                           ║
    ║  The returned DatasetBundle contains entirely synthetic data.        ║
    ║  Every record carries data_source='SYNTHETIC'.                       ║
    ║  These values must not be presented as real-world measurements or   ║
    ║  used to make real planning decisions without independent validation.║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    return load_dataset()
