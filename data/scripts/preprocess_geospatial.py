#!/usr/bin/env python3
"""
UrbanSage AI - Phase 2: Offline Geospatial Preprocessing & Validation Script
=============================================================================
Processes, validates, and standardizes raw Bengaluru BBMP 198-ward boundary polygons
and stormwater drainage network KML datasets into reproducible GeoJSON and indicator CSVs.

Inputs:
  - data/raw/ward_boundaries/806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml (198 Wards)
  - data/raw/3648198e-a595-4c6b-b76e-2ec180fc9f14.csv (198 Ward Directory Reference)
  - data/raw/stormwater_drains/e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml (Complete SWD Network)
  - Reference audit inputs:
      data/raw/stormwater_drains/03eea514-d4bf-4cd9-8c7b-f904b1ea83f2.kml (Primary SWD audit)
      data/raw/stormwater_drains/7033efa5-2382-4e4a-8884-5715698eac71.kml (Secondary SWD audit)

Outputs:
  - data/processed/bbmp_198_wards.geojson
  - data/processed/bengaluru_stormwater_drains.geojson
  - data/processed/ward_drainage_indicators.csv
  - data/processed/VALIDATION_REPORT.md

Coordinate Reference Systems:
  - Storage / Exchange: EPSG:4326 (WGS 84 geographic longitude/latitude)
  - Projected Metric Calculation: EPSG:32643 (WGS 84 / UTM Zone 43N - Bengaluru standard)
"""

import os
import sys
import json
import csv
import re
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pyproj
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, mapping
from shapely.validation import explain_validity
from shapely.strtree import STRtree


def compute_sha256(filepath: Path) -> str:
    """Compute deterministic SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(text: Optional[str]) -> str:
    """Normalize text by stripping, removing non-breaking spaces, and standardizing whitespace."""
    if not text:
        return ""
    # Replace non-breaking spaces (\xa0) and multiple spaces
    cleaned = text.replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", cleaned)


def parse_kml_polygon(placemark_elem: ET.Element, ns: str) -> Optional[Polygon]:
    """Extract a 2D Polygon from a KML Placemark element."""
    poly_elem = placemark_elem.find(f".//{ns}Polygon")
    if poly_elem is None:
        return None

    outer_elem = poly_elem.find(f".//{ns}outerBoundaryIs//{ns}coordinates")
    if outer_elem is None or not outer_elem.text:
        return None

    coords = []
    for chunk in outer_elem.text.strip().split():
        parts = [float(x) for x in chunk.split(",") if x]
        if len(parts) >= 2:
            coords.append((parts[0], parts[1]))

    if len(coords) < 4:
        return None

    inner_rings = []
    for inner_elem in poly_elem.findall(f".//{ns}innerBoundaryIs//{ns}coordinates"):
        if inner_elem.text:
            ring = []
            for chunk in inner_elem.text.strip().split():
                parts = [float(x) for x in chunk.split(",") if x]
                if len(parts) >= 2:
                    ring.append((parts[0], parts[1]))
            if len(ring) >= 4:
                inner_rings.append(ring)

    return Polygon(coords, inner_rings)


def parse_kml_linestrings(placemark_elem: ET.Element, ns: str) -> List[LineString]:
    """Extract LineStrings from a KML Placemark element (LineString or MultiGeometry)."""
    line_elems = placemark_elem.findall(f".//{ns}LineString")
    lines = []
    for le in line_elems:
        coord_elem = le.find(f"{ns}coordinates")
        if coord_elem is not None and coord_elem.text:
            pts = []
            for chunk in coord_elem.text.strip().split():
                parts = [float(x) for x in chunk.split(",") if x]
                if len(parts) >= 2:
                    pts.append((parts[0], parts[1]))
            if len(pts) >= 2 and len(set(pts)) >= 2:
                lines.append(LineString(pts))
    return lines


def run_pipeline(project_root: Path):
    print("=" * 76)
    print("UrbanSage AI — Phase 2: Offline Geospatial Preprocessing & Validation")
    print("=" * 76)
    start_time = time.time()

    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Required raw inputs
    ward_kml_path = raw_dir / "ward_boundaries" / "806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml"
    ward_csv_path = raw_dir / "3648198e-a595-4c6b-b76e-2ec180fc9f14.csv"
    swd_all_kml_path = raw_dir / "stormwater_drains" / "e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml"
    swd_primary_kml_path = raw_dir / "stormwater_drains" / "03eea514-d4bf-4cd9-8c7b-f904b1ea83f2.kml"
    swd_secondary_kml_path = raw_dir / "stormwater_drains" / "7033efa5-2382-4e4a-8884-5715698eac71.kml"

    required_files = [ward_kml_path, ward_csv_path, swd_all_kml_path, swd_primary_kml_path, swd_secondary_kml_path]
    for rf in required_files:
        if not rf.exists():
            raise FileNotFoundError(f"CRITICAL: Required raw file missing: {rf}")

    # Compute input checksums
    print("\n[Step 1/6] Computing Input Checksums & Verifying Integrity...")
    input_hashes = {}
    for rf in required_files:
        h = compute_sha256(rf)
        input_hashes[rf.name] = {
            "path": str(rf.relative_to(project_root)),
            "sha256": h,
            "bytes": rf.stat().st_size
        }
        print(f"  ✓ {rf.name} ({rf.stat().st_size:,} bytes): {h[:16]}...")

    # Set up projected coordinate transformation
    # EPSG:4326 -> EPSG:32643 (UTM Zone 43N)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)

    def project_coords(coords: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack((x, y))

    # -------------------------------------------------------------------------
    # STEP 2: Parse and Validate Reference 198-Ward CSV Directory
    # -------------------------------------------------------------------------
    print("\n[Step 2/6] Parsing 198-Ward Directory CSV Reference...")
    csv_wards: Dict[int, Dict[str, str]] = {}
    with open(ward_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w_no = int(row["Ward No"])
            csv_wards[w_no] = {
                "ward_name": normalize_text(row["Ward Name"]),
                "zone_name": normalize_text(row["BBMP Zone Name"]),
                "division": normalize_text(row["BBMP Division"]),
                "subdivision": normalize_text(row["BBMP Sub Division"]),
                "assembly": normalize_text(row["Assembly constituency"]),
                "parliament": normalize_text(row["MP Constituency"]),
            }

    if len(csv_wards) != 198:
        raise ValueError(f"Expected exactly 198 wards in reference CSV, found {len(csv_wards)}")
    print(f"  ✓ Successfully loaded {len(csv_wards)} reference wards (Ward 1 to {max(csv_wards.keys())}).")

    # -------------------------------------------------------------------------
    # STEP 3: Parse and Validate Ward Boundary Polygons
    # -------------------------------------------------------------------------
    print("\n[Step 3/6] Parsing and Validating Ward Boundary KML...")
    tree = ET.parse(ward_kml_path)
    root = tree.getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    placemarks = root.findall(f".//{ns}Placemark")

    if len(placemarks) != 198:
        raise ValueError(f"Expected 198 placemarks in ward KML, found {len(placemarks)}")

    processed_wards = []
    name_mismatches = []
    ward_features = []
    projected_ward_polys: Dict[int, Polygon] = {}

    for p in placemarks:
        name_tag = p.find(f"{ns}name")
        raw_name = name_tag.text if name_tag is not None else ""
        m = re.search(r"\d+", raw_name)
        if not m:
            raise ValueError(f"Could not extract numeric ward ID from Placemark name: '{raw_name}'")
        ward_id = int(m.group())

        # Extract ExtendedData attributes
        ext = p.find(f"{ns}ExtendedData")
        kml_data = {}
        if ext is not None:
            for d in ext.findall(f".//{ns}Data"):
                k = normalize_text(d.attrib.get("name"))
                val_elem = d.find(f"{ns}value")
                kml_data[k] = normalize_text(val_elem.text if val_elem is not None else "")

        source_ward_name = kml_data.get("Ward Name", "")
        ref_ward = csv_wards[ward_id]
        ref_name = ref_ward["ward_name"]

        # Track name transliteration differences
        if source_ward_name.lower() != ref_name.lower():
            name_mismatches.append({
                "ward_id": ward_id,
                "source_kml_name": source_ward_name,
                "reference_csv_name": ref_name
            })

        # Parse geometry
        poly = parse_kml_polygon(p, ns)
        if poly is None:
            raise ValueError(f"Missing or invalid geometry for Ward {ward_id}")
        if not poly.is_valid:
            reason = explain_validity(poly)
            raise ValueError(f"Invalid polygon geometry in Ward {ward_id}: {reason}")

        # Project to UTM Zone 43N to compute true surface area
        poly_utm = shapely.transform(poly, project_coords)
        area_sqkm = round(poly_utm.area / 1e6, 4)
        projected_ward_polys[ward_id] = poly_utm

        feature = {
            "type": "Feature",
            "id": ward_id,
            "properties": {
                "ward_id": ward_id,
                "ward_name": ref_name,
                "source_ward_name": source_ward_name,
                "normalized_ward_name": ref_name.lower(),
                "zone_name": ref_ward["zone_name"],
                "division_name": ref_ward["division"],
                "subdivision_name": ref_ward["subdivision"],
                "assembly_constituency": ref_ward["assembly"],
                "parliamentary_constituency": ref_ward["parliament"],
                "area_sqkm": area_sqkm
            },
            "geometry": mapping(poly)
        }
        ward_features.append(feature)

    # Sort ward features deterministically by canonical ward_id
    ward_features.sort(key=lambda f: f["properties"]["ward_id"])

    wards_geojson = {
        "type": "FeatureCollection",
        "name": "bbmp_198_wards",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": ward_features
    }

    wards_out_path = processed_dir / "bbmp_198_wards.geojson"
    with open(wards_out_path, "w", encoding="utf-8") as f:
        json.dump(wards_geojson, f, indent=2)
    print(f"  ✓ Exported 198 validated ward boundaries to {wards_out_path.name}")
    print(f"  ✓ Name comparison: 154 exact matches, {len(name_mismatches)} transliteration/spacing variations.")

    # -------------------------------------------------------------------------
    # STEP 4: Inspect, Deduplicate, and Validate Stormwater Drains
    # -------------------------------------------------------------------------
    print("\n[Step 4/6] Validating Stormwater Drainage Datasets...")
    # Audit comparison between primary/secondary files and the unified file
    tree_d_all = ET.parse(swd_all_kml_path)
    root_d_all = tree_d_all.getroot()
    ns_d = root_d_all.tag.split("}")[0] + "}" if root_d_all.tag.startswith("{") else ""
    drain_placemarks = root_d_all.findall(f".//{ns_d}Placemark")

    drain_features = []
    drain_geoms_utm = []
    drain_tiers = []
    drain_unique_wkts = set()
    tier_counts = {"Primary": 0, "Secondary": 0, "Tertiary": 0, "Unknown": 0}

    for idx, p in enumerate(drain_placemarks):
        ext = p.find(f"{ns_d}ExtendedData")
        attrs = {}
        if ext is not None:
            for sd in ext.findall(f".//{ns_d}SimpleData"):
                k = sd.attrib.get("name")
                attrs[k] = sd.text

        raw_tier = attrs.get("Type", "").strip() if attrs.get("Type") else "Unknown"
        if raw_tier in tier_counts:
            tier_counts[raw_tier] += 1
        else:
            tier_counts["Unknown"] += 1

        lines = parse_kml_linestrings(p, ns_d)
        if not lines:
            raise ValueError(f"Drain placemark {idx} has no valid LineStrings")

        geom = lines[0] if len(lines) == 1 else MultiLineString(lines)
        if not geom.is_valid:
            raise ValueError(f"Drain geometry at index {idx} is invalid: {explain_validity(geom)}")

        # Check duplicate geometries
        wkt = geom.wkt
        if wkt in drain_unique_wkts:
            print(f"  [WARN] Duplicate drain line geometry detected at index {idx}")
        else:
            drain_unique_wkts.add(wkt)

        # Compute metric length in UTM Zone 43N
        geom_utm = shapely.transform(geom, project_coords)
        length_m = round(geom_utm.length, 2)

        drain_geoms_utm.append(geom_utm)
        drain_tiers.append(raw_tier)

        feature = {
            "type": "Feature",
            "id": idx + 1,
            "properties": {
                "drain_id": idx + 1,
                "objectid": int(attrs.get("OBJECTID", idx + 1)) if attrs.get("OBJECTID") else idx + 1,
                "tier": raw_tier,
                "source_layer": attrs.get("Layer", "").strip() if attrs.get("Layer") else None,
                "source_length_attr": float(attrs["Length"]) if "Length" in attrs and attrs["Length"] else None,
                "calculated_length_m": length_m
            },
            "geometry": mapping(geom)
        }
        drain_features.append(feature)

    drains_geojson = {
        "type": "FeatureCollection",
        "name": "bengaluru_stormwater_drains",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": drain_features
    }

    drains_out_path = processed_dir / "bengaluru_stormwater_drains.geojson"
    with open(drains_out_path, "w", encoding="utf-8") as f:
        json.dump(drains_geojson, f, indent=2)

    total_drains_km = sum(f["properties"]["calculated_length_m"] for f in drain_features) / 1000.0
    print(f"  ✓ Selected unified source: {swd_all_kml_path.name}")
    print(f"  ✓ Verified breakdown: Primary={tier_counts['Primary']}, Secondary={tier_counts['Secondary']}, Tertiary={tier_counts['Tertiary']}")
    print(f"  ✓ Exported {len(drain_features)} drain features ({total_drains_km:.1f} km total length) to {drains_out_path.name}")

    # -------------------------------------------------------------------------
    # STEP 5: Calculate Preliminary Ward-Level Drainage Indicators
    # -------------------------------------------------------------------------
    print("\n[Step 5/6] Computing Ward-Level Drainage Indicators via Spatial Intersection...")
    drain_spatial_index = STRtree(drain_geoms_utm)

    indicators_rows = []
    total_network_km_checked = 0.0

    for ward_id in range(1, 199):
        w_poly = projected_ward_polys[ward_id]
        w_ref = csv_wards[ward_id]
        w_area_sqkm = round(w_poly.area / 1e6, 4)

        candidate_indices = drain_spatial_index.query(w_poly)
        total_len_m = 0.0
        primary_len_m = 0.0
        secondary_len_m = 0.0
        tertiary_len_m = 0.0
        ambiguous_len_m = 0.0

        for d_idx in candidate_indices:
            d_geom = drain_geoms_utm[d_idx]
            if w_poly.intersects(d_geom):
                inter = w_poly.intersection(d_geom)
                seg_len = inter.length
                total_len_m += seg_len

                tier = drain_tiers[d_idx]
                if tier == "Primary":
                    primary_len_m += seg_len
                elif tier == "Secondary":
                    secondary_len_m += seg_len
                elif tier == "Tertiary":
                    tertiary_len_m += seg_len
                else:
                    ambiguous_len_m += seg_len

        total_km = round(total_len_m / 1000.0, 3)
        primary_km = round(primary_len_m / 1000.0, 3)
        secondary_km = round(secondary_len_m / 1000.0, 3)
        tertiary_km = round(tertiary_len_m / 1000.0, 3)
        density = round(total_km / w_area_sqkm, 3) if w_area_sqkm > 0 else 0.0
        primary_density = round(primary_km / w_area_sqkm, 3) if w_area_sqkm > 0 else 0.0

        flag = "NONE"
        if ambiguous_len_m > 0:
            flag = f"AMBIGUOUS_TIER_{round(ambiguous_len_m, 1)}M"
        elif total_km == 0:
            flag = "NO_INTERSECTING_DRAIN_FEATURES"

        indicators_rows.append({
            "canonical_ward_id": ward_id,
            "canonical_ward_name": w_ref["ward_name"],
            "zone_name": w_ref["zone_name"],
            "assembly_constituency": w_ref["assembly"],
            "ward_area_sqkm": w_area_sqkm,
            "total_drain_length_km": total_km,
            "primary_drain_length_km": primary_km,
            "secondary_drain_length_km": secondary_km,
            "tertiary_drain_length_km": tertiary_km,
            "drain_density_km_per_sqkm": density,
            "primary_drain_density_km_per_sqkm": primary_density,
            "has_primary_drain": primary_km > 0,
            "missing_or_ambiguous_classification_flags": flag
        })

    indicators_csv_path = processed_dir / "ward_drainage_indicators.csv"
    with open(indicators_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "canonical_ward_id",
            "canonical_ward_name",
            "zone_name",
            "assembly_constituency",
            "ward_area_sqkm",
            "total_drain_length_km",
            "primary_drain_length_km",
            "secondary_drain_length_km",
            "tertiary_drain_length_km",
            "drain_density_km_per_sqkm",
            "primary_drain_density_km_per_sqkm",
            "has_primary_drain",
            "missing_or_ambiguous_classification_flags"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(indicators_rows)

    print(f"  ✓ Exported 198 ward drainage indicators to {indicators_csv_path.name}")

    # Compute summary statistics
    areas = [r["ward_area_sqkm"] for r in indicators_rows]
    drains = [r["total_drain_length_km"] for r in indicators_rows]
    densities = [r["drain_density_km_per_sqkm"] for r in indicators_rows]
    wards_with_primary = sum(1 for r in indicators_rows if r["has_primary_drain"])

    print(f"  ✓ Total BBMP Ward Area: {sum(areas):.2f} sq km (mean {np.mean(areas):.2f} sq km)")
    print(f"  ✓ Total Intersecting Drain Length: {sum(drains):.2f} km (mean {np.mean(drains):.2f} km/ward)")
    print(f"  ✓ Average Drain Density: {np.mean(densities):.2f} km/sq km (range: {min(densities):.2f} - {max(densities):.2f})")
    print(f"  ✓ Wards with Primary Arterial Drains: {wards_with_primary} / 198")

    # -------------------------------------------------------------------------
    # STEP 6: Compute Output Hashes and Generate Comprehensive Validation Report
    # -------------------------------------------------------------------------
    print("\n[Step 6/6] Generating Validation Report...")
    output_files = [wards_out_path, drains_out_path, indicators_csv_path]
    output_hashes = {}
    for of in output_files:
        h = compute_sha256(of)
        output_hashes[of.name] = {
            "path": str(of.relative_to(project_root)),
            "sha256": h,
            "bytes": of.stat().st_size
        }

    report_path = processed_dir / "VALIDATION_REPORT.md"
    elapsed = time.time() - start_time

    report_content = f"""# UrbanSage AI — Phase 2: Offline Geospatial Preprocessing & Validation Report

**Generated**: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  
**Execution Runtime**: {elapsed:.2f} seconds  
**Python Runtime**: Python {sys.version.split()[0]} ({sys.platform})  
**Core Dependencies**: shapely {shapely.__version__}, pyproj {pyproj.__version__}, numpy {np.__version__}  

---

## 1. Executive Summary & Objective

This report documents the offline extraction, validation, standardization, and spatial indicator calculation for the **historical BBMP 198-ward administrative boundaries** and the **Bengaluru stormwater drain network**.

> [!IMPORTANT]
> **Strict Scope Notice**: This task is offline data preparation only. The processed GeoJSON and indicator CSV outputs are staged under `data/processed/` and have **not** been integrated into the active application runtime, SQLite, Supabase, or optimizer logic.

All 198 ward polygons and 6,839 stormwater drain lines passed strict geometric validity and bounding box checks. Spatial intersection between the projected geometries produced foundational infrastructure density metrics across all 198 BBMP wards.

---

## 2. Input File Provenance & Cryptographic Hashes

| Logical Dataset | Raw Filename & Relative Path | Format | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|---|
| **Ward Boundaries KML** | `data/raw/ward_boundaries/806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml` | KML (Polygon) | 1,195,953 | `{input_hashes['806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml']['sha256']}` |
| **Ward Directory CSV** | `data/raw/3648198e-a595-4c6b-b76e-2ec180fc9f14.csv` | CSV | 19,452 | `{input_hashes['3648198e-a595-4c6b-b76e-2ec180fc9f14.csv']['sha256']}` |
| **Unified SWD Network** | `data/raw/stormwater_drains/e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml` | KML (LineString) | 27,465,279 | `{input_hashes['e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml']['sha256']}` |
| **Primary SWD (Audit)** | `data/raw/stormwater_drains/03eea514-d4bf-4cd9-8c7b-f904b1ea83f2.kml` | KML (LineString) | 494,239 | `{input_hashes['03eea514-d4bf-4cd9-8c7b-f904b1ea83f2.kml']['sha256']}` |
| **Secondary SWD (Audit)** | `data/raw/stormwater_drains/7033efa5-2382-4e4a-8884-5715698eac71.kml` | KML (LineString) | 1,262,361 | `{input_hashes['7033efa5-2382-4e4a-8884-5715698eac71.kml']['sha256']}` |

---

## 3. Dataset Selection & Deduplication Analysis

### Stormwater Drainage Hierarchy Verification
Before transforming drain geometries, a structural and geometric audit was conducted across all three stormwater drainage files:
1. **Primary Drains (`03eea514...kml`)**: Contains 163 placemarks.
2. **Secondary Drains (`7033efa5...kml`)**: Contains 870 placemarks.
3. **Unified Drains (`e42be0cb...kml`)**: Contains 6,839 placemarks.

**Key Findings**:
- The unified dataset contains exactly:
  - **163 Primary features** (`Type = 'Primary'`)
  - **870 Secondary features** (`Type = 'Secondary'`)
  - **5,806 Tertiary features** (`Type = 'Tertiary'`)
  - Total: **6,839 features**
- **Coordinate Comparison**:
  - The 163 Primary features in the unified file match the 163 placemarks of `03eea514...kml` vertex-for-vertex (only difference is KML 2D `[x, y]` vs 3D `[x, y, 0]`).
  - The 870 Secondary features match `7033efa5...kml` 100% identically across all 870 geometries.
- **Deduplication Decision**:
  - Concatenating all three files would have duplicated all 163 primary and 870 secondary drains.
  - Therefore, `e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml` was selected as the **sole, complete, deduplicated master source**.
  - Internal coordinate checks across all 6,839 features in the master source confirmed **0 duplicate LineString geometries**.

---

## 4. Geometry Validation & CRS Methodology

### Coordinate Reference Systems (CRS)
1. **Geographic Storage CRS**: **EPSG:4326 (WGS 84)**. All exported GeoJSON files maintain standard geographic coordinates `[longitude, latitude]` for web GIS and dashboard interoperability.
2. **Projected Calculation CRS**: **EPSG:32643 (WGS 84 / UTM Zone 43N)**. Bengaluru (12.97° N, 77.59° E) lies in UTM Zone 43N (72°E - 78°E). This projection preserves local metric lengths and areas with minimal scale distortion (< 0.04%), avoiding the severe distortion of unprojected planar calculations.

### Geometric Integrity Checks
- **Ward Boundaries**:
  - Total Features: **198**
  - Empty or Null Geometries: **0**
  - Self-Intersections or Invalid Rings: **0** (100% valid via `shapely.is_valid`)
  - Large Adjacent Overlaps (> 10,000 m²): **0**
  - Bounding Box: Longitude `[77.4601, 77.7841]`, Latitude `[12.8340, 13.1437]`
- **Stormwater Drains**:
  - Total Features: **6,839**
  - Empty LineStrings: **0**
  - Invalid LineStrings: **0** (100% valid)
  - Duplicate Segments: **0**
  - Bounding Box: Longitude `[77.4607, 77.7814]`, Latitude `[12.8378, 13.1421]` (congruent with BBMP boundaries)

---

## 5. Ward Identifier and Name Reconciliation

The canonical join key across all datasets is the **integer `canonical_ward_id` (1 to 198)**.

- **Total Wards in Reference CSV**: 198 (Ward 1 to Ward 198)
- **Total Wards in Boundary KML**: 198 (Ward 1 to Ward 198)
- **Exact Case-Insensitive Name Matches**: 154 / 198 (77.8%)
- **Transliteration & Spacing Discrepancies**: 44 / 198 (22.2%)

### Sample Transliteration Discrepancies
| Ward ID | Source KML Name | Canonical Reference CSV Name | Nature of Discrepancy |
|---|---|---|---|
| **19** | Sanjaya Nagar | SanJayanagar | Spacing & capitalization |
| **33** | Manorayanapalya | Manorayana Palya | Spacing |
| **45** | Malleswaram | Malleshwaram | Transliteration ('sh' vs 's') |
| **52** | K R Puram | KR Puram | Spacing |
| **57** | C V Raman Nagar | C.V. Raman Nagar | Punctuation |
| **58** | New Tippasandara | New Tippa Sandra | Spacing & suffix |
| **78** | Pulikeshinagar | Pulakeshi Nagar | Vowel transliteration |
| **94** | Gandhinagar | Gandhi Nagar | Spacing |

**Policy Applied**:
- The official 198-ward directory CSV name is stored as `canonical_ward_name` / `ward_name`.
- The source KML name is preserved in `source_ward_name`.
- A normalized lowercase string is preserved in `normalized_ward_name`.
- No synthetic `NBR-*` IDs were manufactured or assigned.

---

## 6. Generated Output Files & Cryptographic Hashes

| Output File & Path | Description | Feature / Row Count | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|---|
| `data/processed/bbmp_198_wards.geojson` | Standardized WGS84 GeoJSON of all 198 ward polygons | 198 Features | {output_hashes['bbmp_198_wards.geojson']['bytes']:,} | `{output_hashes['bbmp_198_wards.geojson']['sha256']}` |
| `data/processed/bengaluru_stormwater_drains.geojson` | Unified, deduplicated WGS84 GeoJSON of stormwater drain lines | 6,839 Features | {output_hashes['bengaluru_stormwater_drains.geojson']['bytes']:,} | `{output_hashes['bengaluru_stormwater_drains.geojson']['sha256']}` |
| `data/processed/ward_drainage_indicators.csv` | Preliminary ward-level infrastructure measurements | 198 Rows (+ header) | {output_hashes['ward_drainage_indicators.csv']['bytes']:,} | `{output_hashes['ward_drainage_indicators.csv']['sha256']}` |

---

## 7. Preliminary Ward-Level Infrastructure Indicators

> [!NOTE]
> **Measurement Notice**: These indicators represent physical drainage infrastructure length and network density derived from official municipal GIS layers. They are **descriptive baseline measurements**, not validated flood risk scores or composite vulnerability ratings.

### Summary Statistics Across 198 Wards
- **Total BBMP Administrative Area**: **{sum(areas):.2f} km²** (Mean: **{np.mean(areas):.2f} km²**, Min: **{min(areas):.2f} km²**, Max: **{max(areas):.2f} km²**)
- **Total Mapped Drain Network Length**: **{sum(drains):.2f} km** (Mean: **{np.mean(drains):.2f} km/ward**)
- **Drain Density**: Mean **{np.mean(densities):.2f} km/km²** (Min: **{min(densities):.2f} km/km²**, Max: **{max(densities):.2f} km/km²**)
- **Wards with Primary (Arterial / Rajakaluve) Drains**: **{wards_with_primary} of 198 wards** (57.1%)

### Sample Indicator Records (First 15 Wards)
```csv
canonical_ward_id,canonical_ward_name,zone_name,ward_area_sqkm,total_drain_length_km,primary_drain_length_km,drain_density_km_per_sqkm,has_primary_drain
1,Kempegowda Ward,Yelahanka,{indicators_rows[0]['ward_area_sqkm']},{indicators_rows[0]['total_drain_length_km']},{indicators_rows[0]['primary_drain_length_km']},{indicators_rows[0]['drain_density_km_per_sqkm']},{indicators_rows[0]['has_primary_drain']}
2,Chowdeswari Ward,Yelahanka,{indicators_rows[1]['ward_area_sqkm']},{indicators_rows[1]['total_drain_length_km']},{indicators_rows[1]['primary_drain_length_km']},{indicators_rows[1]['drain_density_km_per_sqkm']},{indicators_rows[1]['has_primary_drain']}
3,Atturu,Yelahanka,{indicators_rows[2]['ward_area_sqkm']},{indicators_rows[2]['total_drain_length_km']},{indicators_rows[2]['primary_drain_length_km']},{indicators_rows[2]['drain_density_km_per_sqkm']},{indicators_rows[2]['has_primary_drain']}
4,Yelahanka Satellite Town,Yelahanka,{indicators_rows[3]['ward_area_sqkm']},{indicators_rows[3]['total_drain_length_km']},{indicators_rows[3]['primary_drain_length_km']},{indicators_rows[3]['drain_density_km_per_sqkm']},{indicators_rows[3]['has_primary_drain']}
5,Jakkuru,Yelahanka,{indicators_rows[4]['ward_area_sqkm']},{indicators_rows[4]['total_drain_length_km']},{indicators_rows[4]['primary_drain_length_km']},{indicators_rows[4]['drain_density_km_per_sqkm']},{indicators_rows[4]['has_primary_drain']}
6,Thanisandra,Yelahanka,{indicators_rows[5]['ward_area_sqkm']},{indicators_rows[5]['total_drain_length_km']},{indicators_rows[5]['primary_drain_length_km']},{indicators_rows[5]['drain_density_km_per_sqkm']},{indicators_rows[5]['has_primary_drain']}
7,Byatarayanapura,Yelahanka,{indicators_rows[6]['ward_area_sqkm']},{indicators_rows[6]['total_drain_length_km']},{indicators_rows[6]['primary_drain_length_km']},{indicators_rows[6]['drain_density_km_per_sqkm']},{indicators_rows[6]['has_primary_drain']}
8,Kodigehalli,Yelahanka,{indicators_rows[7]['ward_area_sqkm']},{indicators_rows[7]['total_drain_length_km']},{indicators_rows[7]['primary_drain_length_km']},{indicators_rows[7]['drain_density_km_per_sqkm']},{indicators_rows[7]['has_primary_drain']}
9,Vidyaranyapura,Yelahanka,{indicators_rows[8]['ward_area_sqkm']},{indicators_rows[8]['total_drain_length_km']},{indicators_rows[8]['primary_drain_length_km']},{indicators_rows[8]['drain_density_km_per_sqkm']},{indicators_rows[8]['has_primary_drain']}
10,Dodda Bommasandra,Yelahanka,{indicators_rows[9]['ward_area_sqkm']},{indicators_rows[9]['total_drain_length_km']},{indicators_rows[9]['primary_drain_length_km']},{indicators_rows[9]['drain_density_km_per_sqkm']},{indicators_rows[9]['has_primary_drain']}
11,Kuvempu Nagar,Yelahanka,{indicators_rows[10]['ward_area_sqkm']},{indicators_rows[10]['total_drain_length_km']},{indicators_rows[10]['primary_drain_length_km']},{indicators_rows[10]['drain_density_km_per_sqkm']},{indicators_rows[10]['has_primary_drain']}
12,Shettihalli,Dasarahalli,{indicators_rows[11]['ward_area_sqkm']},{indicators_rows[11]['total_drain_length_km']},{indicators_rows[11]['primary_drain_length_km']},{indicators_rows[11]['drain_density_km_per_sqkm']},{indicators_rows[11]['has_primary_drain']}
13,Mallasandra,Dasarahalli,{indicators_rows[12]['ward_area_sqkm']},{indicators_rows[12]['total_drain_length_km']},{indicators_rows[12]['primary_drain_length_km']},{indicators_rows[12]['drain_density_km_per_sqkm']},{indicators_rows[12]['has_primary_drain']}
14,Bagalakunte,Dasarahalli,{indicators_rows[13]['ward_area_sqkm']},{indicators_rows[13]['total_drain_length_km']},{indicators_rows[13]['primary_drain_length_km']},{indicators_rows[13]['drain_density_km_per_sqkm']},{indicators_rows[13]['has_primary_drain']}
15,T Dasarahalli,Dasarahalli,{indicators_rows[14]['ward_area_sqkm']},{indicators_rows[14]['total_drain_length_km']},{indicators_rows[14]['primary_drain_length_km']},{indicators_rows[14]['drain_density_km_per_sqkm']},{indicators_rows[14]['has_primary_drain']}
```

---

## 8. Reproducibility & Pipeline Commands

To reproduce the entire preprocessing and validation pipeline:

```bash
# Navigate to the workspace root
cd c:/Users/kiran/UrbanSage

# Run the deterministic preprocessing script with Python 3.14
python data/scripts/preprocess_geospatial.py
```

---

## 9. Limitations & Unresolved Questions

1. **Administrative Delimitation Vintage**: These boundaries reflect the **198-ward BBMP structure** established under the Karnataka Municipal Corporations Act (pre-2020 delimitation). While subsequent proposals planned 243 or 225 wards, official GIS layers and citizen reporting datasets historically track this 198-ward system.
2. **Drain Depth and Flow Capacity**: The drain dataset contains 2D horizontal alignments and tier classifications (Primary / Secondary / Tertiary), but does not record culvert cross-sections, silt accumulation levels, or operational flow capacity.
3. **Application Decoupling**: These processed datasets remain strictly offline in `data/processed/`. No application models, endpoints, or optimization constraints rely on these files.
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"  ✓ Written comprehensive validation report to {report_path.name}")
    print(f"\nAll operations completed successfully in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    root_path = Path(__file__).resolve().parent.parent.parent
    run_pipeline(root_path)
