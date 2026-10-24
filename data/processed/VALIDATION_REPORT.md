# UrbanSage AI — Phase 2: Offline Geospatial Preprocessing & Validation Report

**Generated**: 2026-10-23T20:25:12Z  
**Execution Runtime**: 8.20 seconds  
**Python Runtime**: Python 3.14.3 (win32)  
**Core Dependencies**: shapely 2.2.0, pyproj 3.8.0, numpy 2.5.4  

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
| **Ward Boundaries KML** | `data/raw/ward_boundaries/806d6b9c-e8d9-4eb0-a3a3-b2ba68ec3cda.kml` | KML (Polygon) | 1,195,953 | `44c721814b0bcf9faab48a09f621cb1a27cf5fc081c49d5dc1ecba0c85bee4cc` |
| **Ward Directory CSV** | `data/raw/3648198e-a595-4c6b-b76e-2ec180fc9f14.csv` | CSV | 19,452 | `26b70763b5c9dcc84d86f70f9f7da399ee3acced1a3233406cd69cbc4c751dcc` |
| **Unified SWD Network** | `data/raw/stormwater_drains/e42be0cb-1bf4-4a7b-9c78-0c0dbdae3237.kml` | KML (LineString) | 27,465,279 | `f6d58112c467e6efd55a4a74e6225c68ac3d15457fa989d40faf1cc1c230865e` |
| **Primary SWD (Audit)** | `data/raw/stormwater_drains/03eea514-d4bf-4cd9-8c7b-f904b1ea83f2.kml` | KML (LineString) | 494,239 | `43063312663ee6080817bda73166ee3cb88e78a37b48869504a8751093388004` |
| **Secondary SWD (Audit)** | `data/raw/stormwater_drains/7033efa5-2382-4e4a-8884-5715698eac71.kml` | KML (LineString) | 1,262,361 | `57bbe5346eb2e482e8e611a2f4a0411468921dfe5c05dbe247c1e6a9a16550c1` |

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
| `data/processed/bbmp_198_wards.geojson` | Standardized WGS84 GeoJSON of all 198 ward polygons | 198 Features | 3,348,548 | `5c7161f6a6105d5ec10a585ee4f188dfd1a23d137acb175974542007b88689d5` |
| `data/processed/bengaluru_stormwater_drains.geojson` | Unified, deduplicated WGS84 GeoJSON of stormwater drain lines | 6,839 Features | 61,000,851 | `4a6b6fa60c8c1d5e847bc58df0369d0789eb81b9bf566e1e2c54e5c040d21a00` |
| `data/processed/ward_drainage_indicators.csv` | Preliminary ward-level infrastructure measurements | 198 Rows (+ header) | 18,718 | `108fa92e133f522f3d82d570d6be3064e0d00998255d9ea0909ed066cea68b5c` |

---

## 7. Preliminary Ward-Level Infrastructure Indicators

> [!NOTE]
> **Measurement Notice**: These indicators represent physical drainage infrastructure length and network density derived from official municipal GIS layers. They are **descriptive baseline measurements**, not validated flood risk scores or composite vulnerability ratings.

### Summary Statistics Across 198 Wards
- **Total BBMP Administrative Area**: **676.26 km²** (Mean: **3.42 km²**, Min: **0.00 km²**, Max: **26.84 km²**)
- **Total Mapped Drain Network Length**: **1848.65 km** (Mean: **9.34 km/ward**)
- **Drain Density**: Mean **2.53 km/km²** (Min: **0.00 km/km²**, Max: **8.25 km/km²**)
- **Wards with Primary (Arterial / Rajakaluve) Drains**: **138 of 198 wards** (57.1%)

### Sample Indicator Records (First 15 Wards)
```csv
canonical_ward_id,canonical_ward_name,zone_name,ward_area_sqkm,total_drain_length_km,primary_drain_length_km,drain_density_km_per_sqkm,has_primary_drain
1,Kempegowda Ward,Yelahanka,10.2392,16.989,3.642,1.659,True
2,Chowdeswari Ward,Yelahanka,7.6755,18.552,2.87,2.417,True
3,Atturu,Yelahanka,9.9006,14.143,0.0,1.428,False
4,Yelahanka Satellite Town,Yelahanka,4.9054,22.701,1.988,4.628,True
5,Jakkuru,Yelahanka,24.2118,59.336,8.088,2.451,True
6,Thanisandra,Yelahanka,10.1067,25.146,5.419,2.488,True
7,Byatarayanapura,Yelahanka,9.5816,26.43,3.116,2.758,True
8,Kodigehalli,Yelahanka,3.8415,15.175,2.726,3.95,True
9,Vidyaranyapura,Yelahanka,9.9978,25.177,0.0,2.518,False
10,Dodda Bommasandra,Yelahanka,4.2324,9.469,0.0,2.237,False
11,Kuvempu Nagar,Yelahanka,7.5427,12.156,3.102,1.612,True
12,Shettihalli,Dasarahalli,9.0995,27.997,10.536,3.077,True
13,Mallasandra,Dasarahalli,1.3153,3.808,0.899,2.895,True
14,Bagalakunte,Dasarahalli,4.4246,11.673,1.017,2.638,True
15,T Dasarahalli,Dasarahalli,0.8817,3.166,0.95,3.591,True
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
