# Comprehensive Project Guide

## Purpose of this guide

This guide consolidates the repository's guide and README-style documentation into one root-level reference. It preserves the current technical contracts, data preparation workflow, Java SPEA2 implementation details, Python script responsibilities, UI/backend integration notes, deployment limitations, reproducibility constraints, and future-work items documented across the project.

This file is intentionally comprehensive. It should be used as the single first-stop technical guide for continuing development, writing a report, validating experiments, or onboarding a developer or AI assistant. Existing guide files are left unchanged and are listed at the end.

## 1. Project overview

The project solves a multi-objective parcel locker location optimization problem for Kadikoy.

The core idea is:

- Build a finite set of candidate locker locations from a `100m x 100m` grid.
- Enrich each candidate with demand, POI, public transport, existing locker, neighborhood, and feasibility attributes.
- Precompute a candidate-to-candidate distance matrix.
- Use a Java SPEA2-style multi-objective genetic algorithm to select `K` candidate IDs.
- Evaluate each selected set by accessibility and neighborhood equity.
- Export initial and final archives.
- Visualize final archive solutions in a Next.js dashboard.

Each solution selects:

```text
K candidate locations
```

The current default is:

```text
K = 5
```

Each solution is evaluated by two minimization objectives:

1. `f1`: accessibility cost, based on demand-weighted distance cost to the nearest selected locker.
2. `f2`: equity cost, based on inequality of accessibility quality across neighborhoods.

The optimization is multi-objective because the most accessible solution is not necessarily the fairest one. Concentrating lockers around high-demand areas may reduce global average distance while leaving some neighborhoods underserved. The optimizer therefore searches for a Pareto archive rather than a single absolute optimum.

## 2. Main technology layers

| Layer | Directory or file | Role |
| --- | --- | --- |
| Java optimization engine | `src/main/java` | SPEA2-style multi-objective GA, objectives, archive handling, selection, variation |
| Data and GIS artifacts | `data` | Candidate CSV, distance matrix, raw QGIS/GeoPackage artifacts |
| Python scripts | `scripts`, `data/prepare_ga_inputs.py`, `parcel-locker-ui/src/scripts` | Demand preparation, POI weighting, matrix generation, archive plotting, UI JSON conversion |
| Generated outputs | `output` | Archive CSVs, run metadata, parameter analysis CSVs, plots, statistics |
| Web UI | `parcel-locker-ui` | Next.js dashboard, map, archive solution explorer, local/dev GA trigger |
| Backup/experimental code | `backup` | Older or experimental `Main.java` used for objective-space calibration ideas |

Important root files:

- `pom.xml`: Maven configuration. Uses Java 17. Default `exec:java` entry point is `app.Main`; the `-Panalyze` Maven profile runs `app.ParameterAnalyzer`.
- `readme.md`: quick-start guide.
- `guide.md`: shorter current project guide.
- `General_GUIDE.md`: detailed report-oriented technical guide.
- `COMPREHENSIVE_PROJECT_GUIDE.md`: this consolidated guide.
- `DEPLOYMENT_PHASE1.md`: local/container deployment notes for the current process-spawning UI integration.
- `Dockerfile`: one-service image containing Node, Java 17, Maven, Python, the Java project, and the UI.
- `docker-compose.yml`: local Compose runner with `data`, `output`, and UI mock mounts.
- `.env.example`: runtime variable template for local Next.js execution and `/api/run-ga`.
- `.dockerignore`: excludes local build/generated artifacts from Docker build context.
- `.gitignore`: ignores Maven `target`, Python cache, macOS `.DS_Store`, virtual environments, and some generated output subfolders. Some `output/*.csv` and PNG artifacts may still be present as example outputs.

## 3. Repository structure

The project structure documented by the guides is:

```text
Location-Optimization-with-Genetic-Algorithm
├─ .dockerignore
├─ .env.example
├─ DEPLOYMENT_PHASE1.md
├─ Dockerfile
├─ docker-compose.yml
├─ pom.xml
├─ readme.md
├─ guide.md
├─ General_GUIDE.md
├─ COMPREHENSIVE_PROJECT_GUIDE.md
├─ requirements.txt
├─ data
│  ├─ candidate_points.csv
│  ├─ kadikoy_candidate_ids_sorted.npy
│  ├─ kadikoy_distance_meters_nxn.npy
│  ├─ kadikoy_index_map.csv
│  ├─ prepare_ga_inputs.py
│  ├─ kadikoy_ARTIFACTS_GUIDE.md
│  └─ raw
│     ├─ candidate_points.gpkg
│     ├─ kadikoy_boundary.geojson
│     ├─ kadikoy.gpkg
│     ├─ Kadikoy_Base.gpkg
│     ├─ grid_100m_clipped.gpkg
│     ├─ grid_with_forbidden_area.gpkg
│     ├─ lockers_32635.gpkg
│     ├─ pois_all_points.gpkg
│     └─ small_grids_forbidden.gpkg
├─ scripts
│  ├─ calculate_poi_weights.py
│  ├─ prepare_demand.py
│  ├─ statistical_analysis.py
│  ├─ plot_analysis.py
│  ├─ plot_archives.py
│  ├─ tmp_generate_final_result_plots.py
│  └─ guide.md
├─ src/main/java
│  ├─ analyse_guide.md
│  ├─ SRC_GUIDE.MD
│  ├─ app
│  │  ├─ Main.java
│  │  ├─ ParameterAnalyzer.java
│  │  └─ backend_guide.md
│  ├─ algorithm
│  │  ├─ Evaluate.java
│  │  ├─ Selection.java
│  │  ├─ Survivor.java
│  │  ├─ Variation.java
│  │  └─ helper
│  │     ├─ Dominance.java
│  │     ├─ Pareto.java
│  │     └─ Truncation.java
│  ├─ config
│  │  ├─ GAParameters.java
│  │  ├─ GAResult.java
│  │  └─ GAState.java
│  ├─ io
│  │  ├─ CsvLoader.java
│  │  └─ DistanceMatrixLoader.java
│  ├─ model
│  │  ├─ CandidatePoint.java
│  │  ├─ CandidateRepository.java
│  │  └─ Individual.java
│  └─ service
│     ├─ FitnessCalculator.java
│     ├─ HypervolumeIndicator.java
│     ├─ ObjectiveNormalizer.java
│     └─ PopulationInitializer.java
└─ parcel-locker-ui
   ├─ README.md
   ├─ package.json
   ├─ package-lock.json
   ├─ next.config.ts
   ├─ tsconfig.json
   ├─ eslint.config.mjs
   ├─ postcss.config.mjs
   ├─ public/mock
   │  ├─ candidate-points.json
   │  ├─ candidate_points.csv
   │  ├─ ga-results.json
   │  ├─ archive_comparison_latest.png
   │  └─ kadikoy_boundary.geojson
   └─ src
      ├─ app
      │  ├─ api/run-ga/route.ts
      │  ├─ globals.css
      │  ├─ layout.tsx
      │  └─ page.tsx
      ├─ components/dashboard
      │  ├─ control-panel.tsx
      │  ├─ locker-detail-panel.tsx
      │  ├─ locker-map.tsx
      │  └─ locker-strip.tsx
      ├─ lib
      │  ├─ chart-data.ts
      │  ├─ ga-api.ts
      │  ├─ ga-mock.ts
      │  ├─ mcda.ts
      │  ├─ mock-data.ts
      │  ├─ python-runner.ts
      │  ├─ solution-utils.ts
      │  ├─ types.ts
      │  └─ server
      │     ├─ ga-runner.ts
      │     └─ runtime-config.ts
      └─ scripts
         ├─ build_candidate_json.py
         └─ process_ga_data.py
```

Some raw GIS inventory entries documented in `General_GUIDE.md` also include:

```text
data/raw/bitirme.qgz
data/raw/cand_buf_300m_lockercnt.gpkg
data/raw/candidate_points.csv
data/raw/candidate_points.qmd
data/raw/candidate_points_excel.qmd
data/raw/candidate_points_excel.xlsx
data/raw/intersect.gpkg
```

The current repository also contains root-level data support/export files:

```text
data/candidate_points_backup.csv
data/candidate_points_excel.xls
data/candidate_points.qmd
```

`data/candidate_points_backup.csv` follows the same header shape as `data/candidate_points.csv` and is useful as a CSV backup. `data/candidate_points_excel.xls` and `.qmd` files are QGIS/office/export side artifacts, not Java runtime inputs.

These raw and intermediate files are useful for reproducing or auditing QGIS work. They are not all read by the Java optimizer at runtime.

## 4. Full data flow

The current full data flow is:

```text
QGIS/OSM spatial preparation
        │
        ▼
data/candidate_points.csv
        │
        ├──► scripts/calculate_poi_weights.py
        │
        ├──► scripts/prepare_demand.py
        │         updates poi_score + demand_final in CSV
        │
        └──► data/prepare_ga_inputs.py
                  generates distance matrix artifacts
        │
        ▼
Java SPEA2 run
        │
        ├──► output/initial_archive.csv
        ├──► output/final_archive.csv
        └──► output/run_metadata.json
        │
        ├──► scripts/plot_archives.py
        │         output/archive_comparison_latest.png
        │
        └──► parcel-locker-ui/src/scripts/process_ga_data.py
                  parcel-locker-ui/public/mock/candidate-points.json
                  parcel-locker-ui/public/mock/ga-results.json

Java ParameterAnalyzer run
        │
        ├──► output/parameter_analysis_results.csv
        ├──► output/parameter_analysis_results_smoke.csv (smoke only)
        └──► output/ga_configuration_table.csv
        │
        └──► scripts/statistical_analysis.py
                  output/statistics/descriptive_by_k.csv
                  output/statistics/friedman_summary.csv
                  output/statistics/posthoc_bonferroni.csv
                  output/statistics/selected_configurations.csv
```

## 5. GIS and QGIS data preparation workflow

### 5.1 Objective

The spatial data preparation workflow creates a clean, finite, optimization-ready candidate dataset. The Java optimizer does not search over continuous coordinates. It selects a subset of candidate IDs from the prepared table.

The workflow:

- Discretizes Kadikoy into a `100m x 100m` grid.
- Uses each grid cell centroid as a candidate point.
- Adds population and demand proxies.
- Adds total and category-specific POI counts.
- Adds public bus stop counts.
- Adds existing parcel locker counts.
- Adds feasibility flags from forbidden-area coverage.
- Exports the final table as `data/candidate_points.csv`.

The GA output recommends grid cells. Exact installation points inside or near those cells still require on-site and operational inspection.

### 5.2 CRS strategy

Metric GIS operations use:

```text
EPSG:32635
WGS84 / UTM Zone 35N
Units: meters
```

Operations requiring EPSG:32635 include:

- `300m` buffers.
- Overlay operations such as intersection, union, and dissolve.
- Area computations.
- Coverage ratio calculations.
- Counting points inside buffer polygons.
- Counting existing lockers inside candidate neighborhoods.

EPSG:4326 is still needed for visualization and UI integration:

- Candidate tables include `lon` and `lat`.
- `lon` and `lat` are in EPSG:4326.
- GA-selected candidate IDs can be pinned on Leaflet/OpenStreetMap maps.

CRS issues encountered:

- Some layers were in EPSG:4326 while others were in EPSG:32635.
- "Zoom to layer" showed layers in different locations.
- Overlay operations produced zero intersections.
- Some geometry fixing steps appeared to move layers.

Resolution:

- Restore relevant layers from backup where needed.
- Re-export metric workflow layers to EPSG:32635.
- Repeat overlay and buffer operations under strict CRS consistency.
- Add geographic `lon`/`lat` later only for visualization.

### 5.3 POI cleaning and standardization

Two POI representations existed initially:

- Point geometries.
- Polygon or area-like features.

Point POIs were kept because the intended feature is a count of local activity points. Polygon-like POIs can duplicate features, overweight large facilities, or break the assumption that POIs are countable locations/events.

Point POI layers were merged in QGIS with Merge Vector Layers.

Output:

```text
pois_all_points
```

This standardized point-only POI layer was processed in EPSG:32635.

### 5.4 Total POI density with 300m buffers

A `100m x 100m` grid cell is too small to reliably represent local activity. The project uses a `300m` local neighborhood around each candidate.

Workflow:

1. Generate `300m` buffers around candidate points.
2. Use QGIS Count Points in Polygon.
3. Set polygons to candidate buffers.
4. Set points to `pois_all_points`.
5. Write the count to a field such as `NUMPOINTS`.

The `300m` distance was validated by confirming the buffer layer CRS was EPSG:32635, visually inspecting buffer sizes, and using measurement tools where needed.

### 5.5 POI categories

A single total POI count assumes equal influence from every POI type. The project therefore creates category-specific counts.

The `amenity` values were analyzed with QGIS tools such as:

```text
Statistics by Categories
```

Defined categories include:

1. Transportation, initially including NULL, `ferry_terminal`, and `bus_station`.
2. University.
3. School.
4. Hospital.
5. Bank.
6. ATM.
7. Post office.

Public bus stops were later separated because ordinary bus stops represent a different accessibility signal from major transportation hubs.

Category layers were extracted from `pois_all_points` using Extract by Attribute or Extract by Expression. Examples:

```text
poi_university
poi_school
poi_bank
poi_atm
poi_hospital
poi_post_office
poi_transport
```

For each category:

1. Use the same candidate `300m` buffer polygons.
2. Run Count Points in Polygon.
3. Use the category layer as points.
4. Produce a category-specific field such as `poi_bank`, `poi_school`, or `poi_atm`.

Separate category count outputs were consolidated with:

```text
Join attributes by field value
```

The join used consistent `id` or `fid` fields. Intermediate outputs such as `candidate_last_pois_joined` were later merged into the final candidate dataset.

If an incorrect field was created in QGIS, the documented fix was to enter edit mode and remove it with attribute table tools, Field Calculator, or Delete Field tools.

### 5.6 Public bus stop feature

Bus stops were collected from OpenStreetMap using QuickOSM:

```text
Key: highway
Value: bus_stop
Extent: Kadikoy boundary layer
```

Overpass API timeouts were mitigated by increasing timeout settings and rerunning the query.

The query sometimes returned features outside Kadikoy. The layer was clipped by the Kadikoy boundary.

Output:

```text
bus_stop_clipped
```

Candidate-level bus stop counts used the same `300m` buffer and Count Points in Polygon workflow. The final Java-readable CSV column is:

```text
poi_bus_stop
```

### 5.7 Existing parcel locker integration

Existing locker locations were provided externally as:

```text
kadikoy_lockers_final.geojson
```

The repository contains a metric locker artifact:

```text
data/raw/lockers_32635.gpkg
```

The locker layer was re-exported to EPSG:32635. Existing locker proximity was computed as the number of lockers within `300m` of each candidate:

1. Use candidate `300m` buffers as polygons.
2. Use existing locker points as the point layer.
3. Run Count Points in Polygon.
4. Join the count into the candidate table.

Final column:

```text
locker_count
```

A forbidden candidate can still have nonzero nearby lockers. That means the candidate cell itself is infeasible, while its surrounding neighborhood can contain existing lockers. This remains useful context for demand, coverage, or competition analysis.

### 5.8 Forbidden and non-installable area modeling

The feasibility rule is grid-polygon based, not point-centroid based.

Adopted rule:

```text
A candidate should be excluded only if its entire grid cell is inside forbidden areas.
```

Candidates are flagged rather than deleted so the logic remains auditable, scenario testing remains possible, and the distance matrix alignment can be preserved.

Examples of forbidden landuse classes:

- `cemetery`
- `military`
- `construction`
- `railway`
- `industrial`
- `forest`
- `meadow`
- `brownfield`

The exact list depends on the observed dataset categories.

Forbidden building polygons were filtered if needed, fixed with Fix Geometries where required, and kept in the metric CRS workflow.

Single forbidden mask workflow:

```text
Merge Vector Layers
Inputs: forbidden_buildings_fixed + forbidden_landuse_raw
Output: forbidden_merged
```

```text
Dissolve all features
Output: forbidden_mask
```

One dissolved output feature is expected. Fix Geometries can be run again for robustness.

If intersection between `grid_100m_clipped` and `forbidden_mask` returns zero rows, likely causes are CRS mismatch, non-overlap in the same coordinate space, incorrect reprojection, or stale layer extent.

Forbidden coverage ratio workflow:

```text
grid_100m_clipped intersect forbidden_mask -> grid_forbidden_intersection
```

```text
forb_area_part = $area
grid_area = $area
```

```text
Processing -> Aggregate
Group by: id
sum(forb_area_part) -> forb_area_sum
Output: grid_forbidden_sum
```

```text
Join attributes by field value
grid.id <-> sum.id
Output: grid_with_forbidden_area
```

```text
forbidden_ratio = forb_area_sum / grid_area
is_forbidden = 1 if forbidden_ratio == 1 else 0
```

Grid cells not matched in the join are normal. They had no forbidden-area intersection, so effective `forb_area_sum` is zero.

The `is_forbidden` flag is joined from grid polygons to candidate centroid points through shared grid identifiers.

Output:

```text
candidate_with_forbidden_flag
```

Runtime meaning:

```text
is_forbidden = 0 -> selectable as a locker location
is_forbidden = 1 -> kept as a demand grid point, not selectable as a locker location
```

Current `data/candidate_points.csv` contains:

```text
2717 total rows
2535 selectable rows
182 forbidden rows
```

Forbidden rows remain in the CSV and distance matrix to preserve alignment. Java excludes them only from locker selection via `CandidateRepository.getSelectableCandidateIds()`.

### 5.9 QGIS export artifacts

QGIS may create side files such as `.qmd`. They are not required by the GA. They usually store metadata or QGIS export information.

Runtime GA inputs are:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

UI inputs include:

```text
parcel-locker-ui/public/mock/kadikoy_boundary.geojson
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
parcel-locker-ui/public/mock/archive_comparison_latest.png
```

### 5.10 QGIS-side deliverables

The documented data preparation deliverables are:

- `100m` grid layer.
- Centroid candidate point layer.
- `pois_all_points`, the clean point-only POI layer.
- Candidate-level total POI count.
- Candidate-level ATM, bank, hospital, school, university, post office, and transportation counts.
- `bus_stop_clipped`.
- Candidate-level bus stop count.
- Existing locker layer in metric CRS.
- Candidate-level existing locker count.
- `forbidden_mask`.
- Grid-based `is_forbidden` computed through coverage ratio.
- Final candidate table exported as `candidate_points.csv` with `is_forbidden` preserved.

### 5.11 Status of originally planned data-preparation items

| Item | Current status |
| --- | --- |
| Generate `poi_score` | Implemented through `scripts/prepare_demand.py` using Entropy Weight Method |
| Integrate `poi_score` into final demand | Implemented as `demand_final = population_candidate * (1 + lambda * poi_score)` |
| Finalize SPEA2 objective 1 as accessibility | Implemented in `FitnessCalculator.evaluateF1()` |
| Finalize SPEA2 objective 2 as equity | Implemented in `FitnessCalculator.evaluateF2()` as neighborhood CV |
| UI automation using ID to lon/lat mapping | Partially implemented through `process_ga_data.py` and the Next.js dashboard |
| True generation playback | Not implemented in default Java `Main`; current UI explores archive solutions |

## 6. Runtime candidate CSV contract

The main candidate file is:

```text
data/candidate_points.csv
```

Current documented data status:

```text
Candidate rows: 2717
Unique neighborhoods: 21
Distance matrix shape: 2717 x 2717
Distance matrix dtype: float32
Total forbidden count: 182
Candidate ID range: 24 to 5964
Sum of demand_final: approximately 492289.09
Current committed demand model: poi_score and demand_final generated with lambda 0.5
```

Each row is used in two ways:

- As a demand grid point during objective evaluation.
- As a possible locker location only when `is_forbidden = 0`.

### 6.1 Expected columns

`CsvLoader` maps fields by column name. The expected runtime CSV header is:

```text
fid,id,left,top,right,bottom,row_index,col_index,
Mahalle_Name_Turkish,Mahalle_Name_English,population_mahalle,
poi_atm,poi_bank,poi_hospital,poi_school,poi_university,
poi_post_office,poi_transport,poi_bus_stop,
lon,lat,is_forbidden,locker_count,grid_count_by_mahalle,
population_candidate,poi_score,demand_final
```

Column mapping:

| Column | Java meaning |
| --- | --- |
| `id` | stable candidate ID |
| `Mahalle_Name_Turkish` | Turkish neighborhood name |
| `Mahalle_Name_English` | English neighborhood name |
| `population_mahalle` | neighborhood population |
| `poi_atm` | ATM count |
| `poi_bank` | bank count |
| `poi_hospital` | hospital count |
| `poi_school` | school count |
| `poi_university` | university count |
| `poi_post_office` | post office count |
| `poi_transport` | transportation hub count |
| `poi_bus_stop` | bus stop count |
| `lon` | longitude in EPSG:4326 |
| `lat` | latitude in EPSG:4326 |
| `is_forbidden` | forbidden flag |
| `locker_count` | existing locker count near candidate |
| `grid_count_by_mahalle` | number of grid cells in the neighborhood |
| `population_candidate` | population assigned to candidate |
| `poi_score` | composite POI score |
| `demand_final` | final demand score |

If `poi_score` or `demand_final` is missing, Java falls back to:

```text
poi_score = 0
demand_final = population_candidate
```

This keeps local runs from crashing, but changes the scientific demand model. It should not be treated as equivalent to the prepared dataset.

### 6.2 CSV parser limitation

`CsvLoader` currently uses simple comma splitting with empty trailing-field preservation. This works for current data because fields do not contain embedded commas.

Risk:

- Quoted CSV fields containing commas can break parsing.

Recommended future work:

- Use a real CSV parser such as OpenCSV.
- Or implement robust quoted-field parsing.
- Add schema validation that fails early when scientific demand columns are missing.

## 7. POI score and demand preparation

Main script:

```text
scripts/prepare_demand.py
```

It reads and overwrites:

```text
data/candidate_points.csv
```

Run:

```bash
python3 scripts/prepare_demand.py
```

The script:

1. Reads `data/candidate_points.csv`.
2. Finds raw POI columns with names starting with `poi_`.
3. Excludes generated columns `poi_score` and `demand_final`.
4. Fills missing POI values with zero.
5. Applies `log1p` transformation.
6. Applies min-max normalization.
7. Computes Entropy Weight Method weights.
8. Creates or updates `poi_score`.
9. Prompts for a non-negative `lambda` value.
10. Accepts both `.` and `,` as decimal separators.
11. Updates `demand_final`.
12. Writes the CSV back to the same path.

Demand formula:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

Lambda interpretation:

```text
lambda = 0.0 -> no POI influence; demand follows population_candidate
lambda = 0.5 -> balanced POI influence
lambda = 1.0 -> stronger priority for urban activity hubs
```

### 7.1 Entropy Weight Method

The Entropy Weight Method gives more weight to POI categories that carry more variation or information across candidates.

The script:

- Builds normalized POI data.
- Computes proportions by column.
- Computes entropy.
- Computes divergence as `1 - entropy`.
- Normalizes divergence values into weights.

This avoids assigning arbitrary equal weights to all POI categories.

### 7.2 Rerun safety

Both `prepare_demand.py` and `calculate_poi_weights.py` select raw POI columns using:

```python
col.startswith("poi_") and col not in {"poi_score", "demand_final"}
```

This prevents reruns on an already enriched CSV from feeding `poi_score` back into the Entropy Weight Method.

Safer workflow:

1. Start from a clean candidate CSV.
2. Keep a backup before overwriting `data/candidate_points.csv`.
3. Confirm `poi_score` and `demand_final` after recalculation.

### 7.3 Read-only POI weight inspection

Script:

```text
scripts/calculate_poi_weights.py
```

Run:

```bash
python3 scripts/calculate_poi_weights.py
```

It:

- Reads `data/candidate_points.csv`.
- Selects raw POI columns.
- Excludes `poi_score` and `demand_final`.
- Computes EWM weights.
- Prints weights sorted by descending weight.
- Does not write to the CSV.

## 8. Distance matrix generation and alignment contract

The optimizer needs candidate-to-candidate distances for:

- Nearest selected locker computation.
- Demand-weighted accessibility.
- Neighborhood-level accessibility cost.
- Coverage-style reasoning.
- Possible overlap penalties.
- Dispersion or mean-distance analysis.
- Future objective or constraint extensions.

Distances are precomputed because repeated on-the-fly distance calculation during GA evaluation would be expensive.

Main script:

```text
data/prepare_ga_inputs.py
```

Typical run:

```bash
python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy
```

Optional forbidden filtering:

```bash
python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy \
  --filter_forbidden
```

Important warning:

- Do not use `--filter_forbidden` unless the Java runtime CSV is filtered in exactly the same way.
- Otherwise repository size, candidate order, and matrix size will no longer match.

The current generated artifact guide states:

```text
Generated: 2026-04-07 15:27:17
Source CSV: candidate_points.csv
Candidate order: sorted by id ascending
Forbidden filtering applied when artifact was generated: none
N candidates: 2717
Distance matrix size: approximately 28.2 MB
```

### 8.1 Generated matrix artifacts

`data/prepare_ga_inputs.py` produces:

```text
data/kadikoy_distance_meters_nxn.npy
data/kadikoy_candidate_ids_sorted.npy
data/kadikoy_index_map.csv
data/kadikoy_ARTIFACTS_GUIDE.md
```

Artifact meanings:

| Artifact | Meaning |
| --- | --- |
| `kadikoy_distance_meters_nxn.npy` | NxN matrix where `dist[i, j]` is distance in meters between candidate matrix indexes `i` and `j` |
| `kadikoy_candidate_ids_sorted.npy` | Candidate IDs in the same order as matrix rows and columns |
| `kadikoy_index_map.csv` | Human-readable mapping with columns `idx,id,lon,lat` |
| `kadikoy_ARTIFACTS_GUIDE.md` | Explanation of the artifact contract |

The matrix stores Haversine straight-line distances in meters as `float32`.

If memory becomes a problem, the documented future option is to switch to k-NN or sparse distances.

### 8.2 `id` vs `idx`

This distinction is critical:

- `id`: stable candidate identifier from QGIS/CSV.
- `idx`: row/column index in the NxN distance matrix.

Matrix semantics:

```text
dist[idx_i, idx_j] = meters between candidates
ids[idx] = stable candidate ID
index_map[idx] = id, lon, lat
```

Current Java chromosomes store candidate IDs, not matrix indexes. Java maps IDs to matrix indexes through `CandidateRepository`.

### 8.3 Candidate ID and distance matrix alignment contract

The most important project contract is:

```text
Java sorted candidate order == distance matrix row/column order
```

Current mechanism:

- Python matrix generation sorts by candidate ID ascending.
- Java repository finalization sorts by candidate ID ascending in `CandidateRepository.finalizeRepository()`.

If this contract breaks, the optimizer can still run while all distance-based objective values silently become wrong.

If `data/candidate_points.csv` changes:

- Regenerate the distance matrix.
- Regenerate candidate ID alignment files.
- Ensure candidate IDs are unique.
- Ensure matrix size equals repository size.
- Ensure CSV rows and matrix rows represent the same candidate set.

### 8.4 Forbidden candidate handling in matrix artifacts

Current behavior:

- Forbidden candidates stay in `data/candidate_points.csv`.
- Forbidden candidates stay in `data/kadikoy_distance_meters_nxn.npy`.
- They are demand grid points during objective evaluation.
- They are excluded only from the selectable locker-location universe.

The Java filtering point is:

```text
CandidateRepository.getSelectableCandidateIds()
```

Do not regenerate the matrix with `--filter_forbidden` unless the runtime CSV is also filtered to the exact same row set.

## 9. Problem formulation

### 9.1 Candidate and chromosome representation

A solution is represented by `model.Individual`.

Chromosome:

```text
[candidate_id_1, candidate_id_2, ..., candidate_id_K]
```

The chromosome is a set-like representation. Gene order has no spatial meaning:

```text
[1, 2, 3] and [3, 2, 1] represent the same selected locker set.
```

`Individual` stores chromosomes in sorted canonical form. Preserve this unless the entire archive and duplicate-handling logic is redesigned.

Why canonicalization matters:

- Prevents permutation-equivalent solutions from becoming fake archive diversity.
- Reduces repeated copies of the same solution.
- Keeps convergence analysis meaningful.

### 9.2 Objective 1: `f1` accessibility cost

Objective 1 is minimized.

For every demand grid point:

1. Find the nearest selected locker.
2. Convert distance from meters to kilometers.
3. Apply the distance decay exponent `beta`.
4. Weight the cost by demand.
5. Average over total system demand.

Formula:

```text
f1 = sum_i (demand_i * (min_distance_km(i, selected_lockers) ^ beta)) / sum_i demand_i
```

Current `beta`:

```text
2.0
```

Implementation:

```text
src/main/java/service/FitnessCalculator.java
FitnessCalculator.evaluateF1()
FitnessCalculator.findDistanceCostToNearestLocker()
```

Distance handling:

- The matrix stores meters.
- `FitnessCalculator.findDistanceCostToNearestLocker()` converts to kilometers before applying `beta`.
- This prevents squared meter values from producing very large objective values.
- After this revision, `f1` is typically in a manageable single-digit to low-double-digit range.

### 9.3 Objective 2: `f2` neighborhood equity

Objective 2 is minimized.

It measures inequality of service quality across neighborhoods.

Steps:

1. For each demand grid point, compute the same nearest-locker distance cost used in `f1`.
2. Group demand-weighted costs by Turkish neighborhood name.
3. Compute each neighborhood's demand-weighted mean accessibility cost.
4. Compute the coefficient of variation across neighborhood means.

Formula:

```text
mahalle_mean_cost_m = sum_i_in_m (demand_i * cost_i) / sum_i_in_m demand_i
f2 = std(mahalle_mean_cost_m values) / mean(mahalle_mean_cost_m values)
```

Implementation:

```text
src/main/java/service/FitnessCalculator.java
FitnessCalculator.evaluateF2()
```

Why CV is used:

- It is dimensionless.
- It is independent of distance unit.
- It is easier to interpret than raw variance.
- It avoids squared-scale explosion.
- It usually produces values in a bounded and interpretable range, often around `0` to `2`.
- Lower values mean more even service quality across neighborhoods.

Earlier versions used variance, which created very large squared-scale values. The current CV-based `f2` is the active design.

### 9.4 Objective direction contract

All Pareto and dominance logic assumes bi-objective minimization:

```text
lower f1 is better
lower f2 is better
```

If a future objective is maximized, update:

- `src/main/java/algorithm/helper/Dominance.java`
- `src/main/java/algorithm/helper/Pareto.java`
- `src/main/java/service/HypervolumeIndicator.java`
- `scripts/plot_archives.py`
- `parcel-locker-ui/src/scripts/process_ga_data.py`
- UI labels and interpretation.

## 10. Java package and class structure

Main source directory:

```text
src/main/java
```

Packages:

```text
app
algorithm
algorithm.helper
config
io
model
service
```

### 10.1 `app.Main`

Default entry point:

```text
src/main/java/app/Main.java
```

Run:

```bash
mvn -q compile exec:java
```

Responsibilities:

- Load input data.
- Initialize core services.
- Create the first population.
- Run the SPEA2 loop.
- Print initial and final archive summaries.
- Track runtime.
- Perform final hypervolume assessment.
- Write archive CSVs and metadata.

Important current behavior:

- Reads defaults from `config.GAParameters`.
- Applies supported runtime CLI overrides.
- Accepts runtime path overrides through `--candidateCsv`, `--distanceMatrix`, and `--outputDir`.
- Accepts environment overrides through `PROJECT_ROOT`, `GA_CANDIDATE_CSV`, `GA_DISTANCE_MATRIX`, and `GA_OUTPUT_DIR`.
- Builds the selectable locker universe using `getSelectableCandidateIds()`.
- Stores generation 0 as the initial archive snapshot.
- Stores the final archive snapshot.
- Writes `output/run_metadata.json`.
- Normalizes archive exports with final-ND-based assessment bounds.
- Computes final archive hypervolume.
- Prints compact per-generation progress lines for the UI stream.

`Main` is an orchestration layer. Heavy mathematical logic should stay in `service` and `algorithm` classes.

### 10.2 `app.ParameterAnalyzer`

File:

```text
src/main/java/app/ParameterAnalyzer.java
```

Run:

```bash
mvn -q compile exec:java -Panalyze
```

Purpose:

- Run seeded hyperparameter/statistical experiments separately from the default single-run workflow.
- Compare fixed GA configurations under a constant function-evaluation budget.
- Investigate premature convergence and hypervolume sensitivity.

Outputs:

```text
output/parameter_analysis_results.csv
output/parameter_analysis_results_smoke.csv
output/ga_configuration_table.csv
```

Environment overrides:

```text
PROJECT_ROOT
GA_CANDIDATE_CSV
GA_DISTANCE_MATRIX
GA_OUTPUT_DIR
```

`ParameterAnalyzer` does not vary lambda. It uses precomputed `demand_final` from `data/candidate_points.csv` via the standard three-argument `FitnessCalculator(distanceMatrix, repository, beta)` constructor.

### 10.3 `config.GAParameters`

File:

```text
src/main/java/config/GAParameters.java
```

Central default single-run parameters:

```text
K = 5
POPULATION_SIZE = 100
ARCHIVE_SIZE = 50
MAX_GENERATIONS = 200
BETA = 2.0
CROSSOVER_RATE = 0.9
MUTATION_RATE = 0.1
REFERENCE_POINT_F1 = 1.1
REFERENCE_POINT_F2 = 1.1
```

`Main` reads these first and then applies supported CLI overrides:

```text
--k
--populationSize
--maxGenerations
--mutationRate
--crossoverRate
--archiveSize
--randomSeed
--candidateCsv
--distanceMatrix
--outputDir
```

`ParameterAnalyzer` uses `BETA` and default crossover/mutation values for calibration runs, but its grid values are defined inside `ParameterAnalyzer.java`.

### 10.4 `config.GAState` and `config.GAResult`

Files:

```text
src/main/java/config/GAState.java
src/main/java/config/GAResult.java
```

These currently exist as placeholders. They are not populated by the default optimizer or analyzer.

Future targets:

- Runtime state tracking.
- Structured backend output.
- JSON result serialization.
- Generation-level export.

### 10.5 `model.CandidatePoint`

File:

```text
src/main/java/model/CandidatePoint.java
```

Represents one candidate grid point / demand point.

Stores:

- Candidate ID.
- Turkish and English neighborhood names.
- Neighborhood population.
- POI category counts.
- Longitude and latitude.
- Forbidden flag.
- Existing locker count.
- Grid count by neighborhood.
- Candidate population.
- POI score.
- Final demand score.

This is a data model and does not implement optimization logic.

### 10.6 `model.CandidateRepository`

File:

```text
src/main/java/model/CandidateRepository.java
```

Responsibilities:

- Store all candidate points.
- Provide lookup by ID.
- Provide all candidate IDs.
- Provide selectable candidate IDs where `is_forbidden = 0`.
- Synchronize candidate order with the distance matrix.

Maintains:

- `candidateMap`: lookup by ID.
- `idToIndexMap`: candidate ID to distance matrix index.
- `sortedCandidates`: candidates sorted by ascending ID.

Critical method:

```text
finalizeRepository()
```

It:

- Sorts all candidates by ascending ID.
- Builds ID-to-index mapping.
- Ensures Java candidate order matches Python-generated matrix order.

Forbidden rows stay in `sortedCandidates` as demand grid points and are excluded only from the selectable locker universe.

### 10.7 `model.Individual`

File:

```text
src/main/java/model/Individual.java
```

Represents one GA solution.

Stores:

- Canonical sorted chromosome.
- Raw objective values: `f1`, `f2`.
- Normalized objective values: `norm_f1`, `norm_f2`.
- SPEA2 strength.
- SPEA2 raw fitness.
- SPEA2 density.
- SPEA2 total fitness.

The chromosome is sorted in the constructor and setter. Preserve this behavior unless duplicate handling and archive semantics are redesigned.

### 10.8 `io.CsvLoader`

File:

```text
src/main/java/io/CsvLoader.java
```

Responsibilities:

- Read `data/candidate_points.csv`.
- Parse rows and map fields by header names.
- Ignore empty lines.
- Preserve empty trailing fields during splitting.
- Populate `CandidateRepository`.
- Fall back to population-only demand if `poi_score` or `demand_final` is absent.

Limitation:

- Uses simple comma splitting, not a production-grade CSV parser.

### 10.9 `io.DistanceMatrixLoader`

File:

```text
src/main/java/io/DistanceMatrixLoader.java
```

Loads NumPy `.npy` distance matrices using:

```xml
<dependency>
    <groupId>org.jetbrains.bio</groupId>
    <artifactId>npy</artifactId>
    <version>0.3.5</version>
</dependency>
```

Expects:

- A 2D matrix.
- A square matrix.
- Data payload as `float[]` or `double[]`.

Returns:

```text
double[][]
```

`Main` and `ParameterAnalyzer` validate matrix dimensions against repository size.

### 10.10 `service.FitnessCalculator`

File:

```text
src/main/java/service/FitnessCalculator.java
```

Responsibilities:

- Validate individuals.
- Compute total system demand.
- Compute nearest-locker distance cost.
- Evaluate `f1`.
- Evaluate `f2`.
- Evaluate raw objectives for a population.

Distance cost:

```text
cost = (nearest_distance_meters / 1000.0) ^ beta
```

Computational complexity per individual:

```text
O(number_of_candidates * K)
```

With current values:

```text
number_of_candidates = 2717
selectable locker candidates = 2535
K = 5
```

This is feasible for the current project size.

Demand mode:

- Active `Main` and `ParameterAnalyzer` paths use precomputed `demand_final`.
- `FitnessCalculator` also contains a dynamic lambda constructor, but the current analyzer grid does not use it.

Possible future experiments:

- Alternative equity metrics such as Gini or MAD.
- Different `beta` values.
- Different demand weighting schemes.

### 10.11 `service.PopulationInitializer`

File:

```text
src/main/java/service/PopulationInitializer.java
```

Creates generation 0 population.

For each individual:

1. Copy all selectable candidate IDs.
2. Shuffle them.
3. Take the first `K` IDs.
4. Create an `Individual`.

Current behavior:

- Default initializer uses an unseeded random generator.
- `Main` and `ParameterAnalyzer` can use `PopulationInitializer(long seed)` for deterministic runs when a seed is supplied.

### 10.12 `service.ObjectiveNormalizer`

File:

```text
src/main/java/service/ObjectiveNormalizer.java
```

Supports two conceptual uses:

1. Internal normalization for SPEA2 density and comparison support.
2. Assessment normalization for archive export and final hypervolume assessment.

Dynamic normalization is used inside `Evaluate`.

Fixed-bound normalization is used after a run so initial and final archive snapshots share one exported objective space.

Formula:

```text
norm = (value - min) / (max - min)
```

Output is clamped to:

```text
[0, 1]
```

Important rule:

```text
For final archive HV assessment, bounds are derived from the final archive non-dominated set.
Initial-to-final improvement is assessed with raw-objective ND metrics and C-metric, not initial-vs-final HV.
```

Future split idea:

- `InternalObjectiveNormalizer`
- `AssessmentObjectiveNormalizer`

### 10.13 `service.HypervolumeIndicator`

File:

```text
src/main/java/service/HypervolumeIndicator.java
```

Computes 2D hypervolume in normalized objective space.

Assumptions:

- Bi-objective minimization.
- Normalized objectives already exist.
- Reference point is outside the normalized range.

Current reference:

```text
(1.1, 1.1)
```

Procedure:

1. Extract non-dominated individuals.
2. Deduplicate by chromosome.
3. Sort by normalized `f1`.
4. Accumulate dominated rectangles to the reference point.

If a point is worse than the reference point, the method throws an error.

Known sensitivity:

- Raw-space HV is not suitable when objective magnitudes differ.
- Per-generation normalization breaks comparability.
- Global min-max can be too loose if outliers exist.
- HV interpretation depends strongly on normalization bounds and front shape.

### 10.14 `algorithm.helper.Dominance`

File:

```text
src/main/java/algorithm/helper/Dominance.java
```

Checks Pareto dominance under bi-objective minimization.

Definition:

```text
a dominates b if:
a.f1 <= b.f1
a.f2 <= b.f2
and at least one comparison is strict
```

Used by Pareto extraction, strength assignment, and raw fitness assignment.

### 10.15 `algorithm.helper.Pareto`

File:

```text
src/main/java/algorithm/helper/Pareto.java
```

Extracts the non-dominated subset from a list of individuals.

Used by:

- `Survivor`
- `HypervolumeIndicator`
- `Main`
- `ParameterAnalyzer`

Plotting and UI conversion logic conceptually mirror this minimization behavior.

### 10.16 `algorithm.helper.Truncation`

File:

```text
src/main/java/algorithm/helper/Truncation.java
```

Reduces oversized archives while preserving diversity.

Method:

- Compute sorted neighbor-distance lists in normalized objective space.
- Compare lists lexicographically.
- Remove the individual in the most crowded region.
- Repeat until archive size equals target size.

This follows the SPEA2 truncation idea.

### 10.17 `algorithm.Evaluate`

File:

```text
src/main/java/algorithm/Evaluate.java
```

Runs SPEA2 evaluation.

Input:

- Current population.
- Current archive.

Steps:

1. Merge population and archive.
2. Evaluate raw objectives.
3. Normalize objectives dynamically.
4. Assign strength.
5. Assign raw fitness.
6. Assign density.
7. Assign total fitness.

SPEA2 quantities:

```text
strength(i) = number of individuals dominated by i
rawFitness(i) = sum of strengths of individuals that dominate i
density(i) = 1 / (sigma_k + 2)
totalFitness(i) = rawFitness(i) + density(i)
```

`sigma_k` is the distance to the k-th nearest neighbor in normalized objective space.

Current neighbor index:

```text
k = floor(sqrt(merged_size))
```

`Evaluate` implements SPEA2 evaluation logic, not the problem-specific objective formulas.

### 10.18 `algorithm.Survivor`

File:

```text
src/main/java/algorithm/Survivor.java
```

Builds the next archive.

Procedure:

1. Extract non-dominated individuals.
2. Deduplicate by canonical chromosome.
3. If non-dominated count equals archive size, return it.
4. If smaller, fill with best dominated individuals by total fitness.
5. If larger, truncate it.

The archive represents elite memory, not repeated copies of the same solution.

### 10.19 `algorithm.Selection`

File:

```text
src/main/java/algorithm/Selection.java
```

Performs binary tournament parent selection from the archive.

Comparison priority:

1. Smaller `totalFitness`.
2. Smaller `rawFitness` if tied.
3. Smaller `density` if still tied.
4. First individual if still tied.

The archive cannot be empty.

### 10.20 `algorithm.Variation`

File:

```text
src/main/java/algorithm/Variation.java
```

Generates offspring from the mating pool.

Main operations:

- Crossover.
- Mutation.
- Repair.
- Chromosome uniqueness enforcement.

Crossover uses shared-gene priority recombination:

1. Collect genes present in both parents.
2. Insert shared genes into both children.
3. Pool parent-exclusive genes.
4. Shuffle the exclusive pool.
5. Fill remaining child slots.
6. Apply repair.

This preserves proven gene combinations while maintaining some diversity. It can also cause premature convergence if mutation is too low.

Mutation:

- Selects one random gene.
- Replaces it with a candidate ID not already in the chromosome.

Repair:

- Removes duplicates.
- Fills missing slots with unused candidate IDs.
- Trims extra genes.
- Ensures chromosome length is exactly `K`.

## 11. SPEA2 optimization workflow

Default single-run workflow:

1. Create the `output` directory.
2. Load `data/candidate_points.csv`.
3. Call `CandidateRepository.finalizeRepository()`.
4. Load `data/kadikoy_distance_meters_nxn.npy`.
5. Validate matrix dimensions against repository size.
6. Read defaults from `GAParameters`.
7. Apply optional CLI argument overrides.
8. Build selectable locker universe from `is_forbidden = 0` rows.
9. Initialize population from selectable candidate IDs.
10. Create an empty archive.
11. Build algorithm and service dependencies.
12. Evaluate generation 0.
13. Build generation 0 archive with `Survivor`.
14. Deep-copy the initial archive snapshot.
15. Run the evolutionary loop for `MAX_GENERATIONS`.
16. In each generation:
    - Select mating pool from archive.
    - Generate offspring through variation.
    - Evaluate offspring plus archive.
    - Build next archive.
    - Print compact progress for UI stream.
17. Deep-copy the final archive snapshot.
18. Extract final archive non-dominated set.
19. Compute ideal/nadir `f1` and `f2` bounds from the final ND set.
20. Normalize initial and final archive snapshots with final-ND bounds.
21. Write `output/initial_archive.csv`.
22. Write `output/final_archive.csv`.
23. Write `output/run_metadata.json`.
24. Compute final archive hypervolume and hypervolume ratio.
25. Compute raw-objective improvement metrics and C-metric.
26. Print HV, ND counts, CSV paths, and runtime.

What is already working:

- Candidate data loading.
- Distance matrix loading.
- Random initialization.
- Objective evaluation.
- SPEA2 strength, raw fitness, density, and total fitness.
- Non-dominated archive construction.
- Archive deduplication.
- Truncation.
- Binary tournament selection.
- Shared-gene crossover.
- Mutation and repair.
- Initial/final archive export.
- Runtime tracking.
- Final archive hypervolume in final-ND-normalized space.
- Forbidden candidate filtering for locker selection.

## 12. Running the project

### 12.1 Requirements

- Java 17.
- Maven.
- Python 3.
- Python packages from `requirements.txt`.
- Node.js and npm for the Next.js dashboard.

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

### 12.2 Optional demand preparation

The current committed CSV already contains `poi_score` and `demand_final` generated with `lambda = 0.5`. Rerun demand preparation only when candidate data or demand assumptions change.

```bash
python3 scripts/prepare_demand.py
```

Warning: this overwrites `data/candidate_points.csv`.

### 12.3 Compile Java

```bash
mvn -q compile
```

### 12.4 Run a single SPEA2 optimization

```bash
mvn -q compile exec:java
```

### 12.5 Generate archive plot

```bash
python3 scripts/plot_archives.py
```

### 12.6 Run parameter grid search

```bash
mvn -q compile exec:java -Panalyze
```

Smoke check:

```bash
mvn -q compile exec:java -Panalyze -Dexec.args="--smoke"
```

### 12.7 Statistical analysis of grid search

```bash
python3 scripts/statistical_analysis.py
```

Smoke post-processing:

```bash
python3 scripts/statistical_analysis.py \
  --input output/parameter_analysis_results_smoke.csv \
  --output-dir output/statistics_smoke
```

### 12.8 Run UI locally

```bash
cd parcel-locker-ui
npm install
npm run dev
```

## 13. Archive outputs and metadata

`Main` writes:

```text
output/initial_archive.csv
output/final_archive.csv
output/run_metadata.json
```

`initial_archive.csv` is the archive snapshot after generation 0.

`final_archive.csv` is the archive snapshot after the final generation.

Archive CSV columns:

```text
archive_index,chromosome,f1,f2,norm_f1,norm_f2,strength,raw_fitness,density,total_fitness
```

Column meanings:

| Column | Meaning |
| --- | --- |
| `archive_index` | Row order in archive export |
| `chromosome` | Candidate ID list separated by `|` |
| `f1` | Raw accessibility objective |
| `f2` | Raw equity objective |
| `norm_f1` | Assessment-normalized `f1` |
| `norm_f2` | Assessment-normalized `f2` |
| `strength` | SPEA2 strength |
| `raw_fitness` | SPEA2 raw fitness |
| `density` | SPEA2 density |
| `total_fitness` | `raw_fitness + density` |

`run_metadata.json` contains run parameters and estimated function evaluations, including values such as `k`, population size, archive size, max generations, rates, optional random seed, and estimated function evaluations.

Example `final_archive.csv` status from a previous validated run:

```text
Rows: 50
f1 range: approximately 0.5365 to 0.6003
f2 range: approximately 0.2085 to 0.3690
normalized f1 range: approximately 0.0455 to 1.0
normalized f2 range: approximately 0.0455 to 0.9545
```

Regenerate output before using exact ranges in a report.

## 14. Normalization and hypervolume logic

The project uses normalization in two places:

1. SPEA2 internal normalization inside `Evaluate`, where the merged set is normalized for density.
2. Run assessment normalization after `Main` finishes, where initial and final archive snapshots share final-ND-based bounds for export.

Current assessment rule:

```text
Final archive HV uses bounds derived from the final archive non-dominated set.
Initial-to-final improvement uses raw-objective ND metrics and C-metric.
```

Current `Main` behavior:

- Extract final archive non-dominated set.
- Derive ideal/nadir bounds from final ND solutions.
- Normalize both archive CSV snapshots with those bounds.
- Compute final archive hypervolume in normalized space.
- Use reference point `(1.1, 1.1)`.
- Compute initial-to-final improvement separately through raw-objective ND metrics and C-metric.

Hypervolume ratio:

```text
ratio = hypervolume / (reference_f1 * reference_f2)
```

With current reference:

```text
reference area = 1.1 * 1.1 = 1.21
```

Warnings:

- Do not compare HV values from separately normalized archives.
- Do not normalize each generation independently for HV comparison.
- A high HV ratio does not automatically prove scientific quality.
- Inspect raw objective plots, non-dominated count, best `f1`, best `f2`, and selected locker geography.

## 15. `scripts/plot_archives.py`

Script:

```text
scripts/plot_archives.py
```

Inputs:

```text
output/initial_archive.csv
output/final_archive.csv
output/run_metadata.json
```

Output:

```text
output/archive_comparison_latest.png
```

Plot panels:

- Initial Archive - Raw Objective Space.
- Final Archive - Raw Objective Space.
- Initial to Final Improvement Metrics using raw-objective ND metrics and C-metric.
- Final Archive - Hypervolume Space normalized using final-ND bounds.

The script also prints:

- Archive sizes.
- Non-dominated counts.
- Pearson and Spearman correlation between `f1` and `f2`.
- Best `f1`.
- Best `f2`.
- C-metric values.

Run:

```bash
python3 scripts/plot_archives.py
```

## 16. Parameter analysis workflow

`ParameterAnalyzer` is a Java grid-search runner for comparing fixed GA configurations under a constant function-evaluation budget. It is separate from the default `Main` workflow.

File:

```text
src/main/java/app/ParameterAnalyzer.java
```

Maven profile:

```bash
mvn -q compile exec:java -Panalyze
```

Output directory:

```text
output/
```

Outputs:

```text
output/parameter_analysis_results.csv
output/parameter_analysis_results_smoke.csv
output/ga_configuration_table.csv
```

Environment overrides:

```text
PROJECT_ROOT        base path for relative input/output overrides
GA_CANDIDATE_CSV   candidate CSV path
GA_DISTANCE_MATRIX distance matrix path
GA_OUTPUT_DIR      output directory
```

### 16.1 Experimental design

Locker counts:

```text
K_VALUES = {1, 5, 10, 15}
```

GA configuration grid:

```text
POPULATION_SIZES = {50, 100, 200}
MUTATION_RATES   = {0.10, 0.25, 0.40}
CROSSOVER_RATES  = {0.70, 0.90}
ARCHIVE_SIZE     = POPULATION_SIZE / 2
```

Each configuration gets an ID:

```text
GA1, GA2, ...
```

Full seeds:

```text
SEEDS = {1, 2, ..., 20}
```

Full grid-search size:

```text
4 K values x 18 GA configurations x 20 seeds = 1440 grid runs
```

Function-evaluation budgets:

| K | Target FE |
| --- | --- |
| `1` | `30,000` |
| `5` | `50,000` |
| `10` | `80,000` |
| `15` | `100,000` |

Generation count:

```text
maxGenerations = (targetFE / populationSize) - 1
functionEvals  = populationSize x (maxGenerations + 1)
```

This keeps comparisons fair across population sizes.

Lambda is not part of this Java grid. If demand assumptions change, rerun:

```bash
python3 scripts/prepare_demand.py
```

Then rerun the analyzer.

### 16.2 Hypervolume calibration bounds

For each K, `ParameterAnalyzer` runs calibration before grid search:

```text
CALIBRATION_POPULATION_SIZE = 100
CALIBRATION_ARCHIVE_SIZE    = 50
CALIBRATION_SEEDS           = {101, 102, 103, 104, 105}
CALIBRATION_MARGIN          = 0.02
```

Calibration procedure:

1. Run SPEA2 with calibration seeds for the active K.
2. Union final archive members.
3. Extract the non-dominated set from that union.
4. Compute min/max bounds for `f1` and `f2`.
5. Expand each range by a 2% margin.
6. Use locked bounds for all grid-search runs with that K.

`Final_HV` and `Final_HV_Ratio` are comparable within the same K. They should not be treated as directly comparable across different K values because each K uses its own calibration bounds.

### 16.3 Output CSV schemas

`parameter_analysis_results.csv` columns:

```text
Run_ID,K,Task,GA_ID,PopulationSize,ArchiveSize,MaxGenerations,TargetFE,
FunctionEvals,MutationRate,CrossoverRate,Seed,Runtime_ms,Final_HV,
Final_HV_Ratio,ND_Count,Final_ND_Archive_Ratio,Spacing_CV,
Best_f1,Best_f2,Mean_f1,Mean_f2
```

`ga_configuration_table.csv` columns:

```text
GA_ID,PopulationSize,ArchiveSize,MutationRate,CrossoverRate
```

### 16.4 Smoke mode

Run:

```bash
mvn -q compile exec:java -Panalyze -Dexec.args="--smoke"
```

Smoke mode limits:

```text
K values: first 1
GA configurations: first 2
Seeds: first 2
Target FE: 200
Calibration seeds: {101}
```

Output:

```text
output/parameter_analysis_results_smoke.csv
```

### 16.5 Statistical post-processing

Script:

```text
scripts/statistical_analysis.py
```

Default run:

```bash
python3 scripts/statistical_analysis.py
```

Default input:

```text
output/parameter_analysis_results.csv
```

Default output directory:

```text
output/statistics/
```

Generated files:

```text
descriptive_by_k.csv
friedman_summary.csv
posthoc_bonferroni.csv
selected_configurations.csv
```

What it does:

- Builds a Seed x GA_ID matrix of `Final_HV_Ratio` per K.
- Computes mean, median, standard deviation, IQR, and mean rank per configuration.
- Runs a Friedman test per K.
- Runs Bonferroni-corrected Wilcoxon post-hoc tests where Friedman is significant.
- Selects the best configuration per K with priority:

```text
HV ratio median -> HV ratio mean -> std -> ND archive ratio -> runtime -> population size
```

Smoke post-processing:

```bash
python3 scripts/statistical_analysis.py \
  --input output/parameter_analysis_results_smoke.csv \
  --output-dir output/statistics_smoke
```

### 16.6 Legacy parameter plotting

Script:

```text
scripts/plot_analysis.py
```

This is an older exploratory visualization script. It reads from:

```text
output/parameter analysis/parameter_analysis_results.csv
```

It expects older columns such as:

```text
Lambda
PopSize
MutRate
CrossRate
```

It is not the canonical post-processor for current `ParameterAnalyzer` output.

It produces five plots in:

```text
output/parameter analysis/plots_advanced/
```

Plots:

1. Population size vs Final HV boxplot.
2. Lambda vs Final HV per K pointplot.
3. Mutation x Crossover heatmaps per K.
4. MaxGen vs ND Count convergence proxy.
5. Runtime vs HV computation-cost tradeoff.

It also writes `thesis_detailed_report.txt` with champion configurations per K and per `(K, Lambda)` for the older schema.

## 17. RQ validation pipeline

No standalone file named "RQ validation" or "research question validation" exists in the reviewed guide/README set. The documented validation pipeline is distributed across the single-run assessment, parameter analysis, statistics, plotting, and UI inspection workflows.

Use the following pipeline to validate research questions or report claims:

1. Data integrity validation:
   - Confirm EPSG:32635 was used for metric GIS operations.
   - Confirm `lon` and `lat` exist in EPSG:4326 for UI mapping.
   - Confirm `data/candidate_points.csv` includes `poi_score`, `demand_final`, and `is_forbidden`.
   - Confirm candidate count matches the distance matrix size.
   - Confirm candidate IDs are unique and sorted alignment is preserved.

2. Demand model validation:
   - Use `scripts/calculate_poi_weights.py` to inspect EWM weights.
   - Use `scripts/prepare_demand.py` only when demand assumptions change.
   - Record lambda used for `demand_final`.
   - Treat population-only fallback as a different experiment.

3. Single-run optimizer validation:
   - Run `mvn -q compile exec:java`.
   - Check `output/initial_archive.csv`, `output/final_archive.csv`, and `output/run_metadata.json`.
   - Verify each chromosome contains exactly `K` IDs.
   - Verify selected IDs are non-forbidden candidates.
   - Verify `f1`, `f2`, `norm_f1`, and `norm_f2` ranges are plausible.

4. Initial-to-final improvement validation:
   - Run `python3 scripts/plot_archives.py`.
   - Use raw-objective ND metrics and C-metric for initial-to-final improvement.
   - Use final archive HV only as final-front quality indicator.

5. Hyperparameter validation:
   - Run `mvn -q compile exec:java -Panalyze`.
   - Confirm constant FE budgets per K.
   - Confirm calibration bounds are locked per K.
   - Use `Final_HV_Ratio` only within the same K.

6. Statistical validation:
   - Run `python3 scripts/statistical_analysis.py`.
   - Use Friedman test for overall configuration differences per K.
   - Use Bonferroni-corrected Wilcoxon post-hoc tests where applicable.
   - Use `selected_configurations.csv` as the documented configuration-selection output.

7. Spatial and decision-support validation:
   - Convert final archive to UI JSON using `process_ga_data.py`.
   - Inspect selected locker geography in the Next.js dashboard.
   - Use MCDA only as a decision-support selector among existing Pareto solutions, not as a new optimizer.

## 18. Python scripts and execution order

### 18.1 Recommended current workflow

```bash
# 1. Inspect POI weights (optional)
python3 scripts/calculate_poi_weights.py

# 2. Update demand if candidate data or demand assumptions changed
python3 scripts/prepare_demand.py

# 3. Regenerate matrix artifacts only if candidate set or coordinates changed
python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy

# 4. Run a single SPEA2 optimization
mvn -q compile exec:java

# 5. Visualize initial/final archive behavior
python3 scripts/plot_archives.py

# 6. Generate UI JSON from GA output
cd parcel-locker-ui
python3 src/scripts/process_ga_data.py
cd ..

# 7. Run parameter grid search when needed
mvn -q compile exec:java -Panalyze

# 8. Analyze parameter grid-search output
python3 scripts/statistical_analysis.py
```

### 18.2 `scripts/prepare_demand.py`

Covered in Section 7. It updates `poi_score` and `demand_final`, and overwrites `data/candidate_points.csv`.

### 18.3 `scripts/calculate_poi_weights.py`

Covered in Section 7. It is read-only and prints current EWM POI weights.

### 18.4 `data/prepare_ga_inputs.py`

Covered in Section 8. It generates distance matrix and alignment artifacts.

### 18.5 `scripts/plot_archives.py`

Covered in Section 15. It generates the four-panel archive comparison plot.

### 18.6 `scripts/statistical_analysis.py`

Covered in Section 16. It performs rigorous post-processing of `ParameterAnalyzer` output.

### 18.7 `scripts/plot_analysis.py`

Legacy exploratory script for older parameter-analysis schema. Prefer `statistical_analysis.py`.

### 18.8 `scripts/tmp_generate_final_result_plots.py`

Temporary helper used to generate final-result plots under:

```text
sections/figures/final_results/
```

It is kept for report figure regeneration, not core runtime. It contains hardcoded Windows paths, so adjust paths before running it on another machine.

Documented/generated final-report figure artifacts in the current repository include:

```text
sections/figures/final_results/selected_config_summary.csv
sections/figures/final_results/3_1_selected_hv_ratio_vs_k.png
sections/figures/final_results/3_2_best_f1_vs_k.png
sections/figures/final_results/3_3_marginal_f1_reduction.png
sections/figures/final_results/3_4_best_f2_vs_k.png
sections/figures/final_results/3_5_runtime_vs_k.png
sections/figures/final_results/3_6_mutation_rate_effect.png
sections/figures/final_results/3_7_hv_distribution_by_ga_combined.png
```

The folder also contains shorter-name variants such as `best_f1_vs_k.png`, `best_f2_vs_k.png`, `selected_hv_ratio_vs_k.png`, `runtime_vs_k.png`, `marginal_f1_reduction.png`, `mutation_rate_effect.png`, and `hv_distribution_by_ga_combined.png`.

### 18.9 `parcel-locker-ui/src/scripts/process_ga_data.py`

Main UI conversion script for current local/dev integration.

Inputs:

```text
data/candidate_points.csv
output/final_archive.csv
```

Environment-aware inputs:

```text
PROJECT_ROOT
UI_ROOT
GA_CANDIDATE_CSV
GA_OUTPUT_DIR
UI_MOCK_DIR
```

Outputs:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
```

It:

- Converts candidate CSV to map-ready JSON.
- Reads final archive chromosomes from Java output.
- Maps selected candidate IDs to coordinates and neighborhood names.
- Transfers `f1`, `f2`, `total_fitness`, `norm_f1`, and `norm_f2`.
- Recomputes Pareto flags under bi-objective minimization.
- Marks best-`f1` and best-`f2` Pareto solutions.

Manual run:

```bash
cd parcel-locker-ui
python3 src/scripts/process_ga_data.py
```

### 18.10 `parcel-locker-ui/src/scripts/build_candidate_json.py`

Older/alternate candidate JSON builder.

Input:

```text
parcel-locker-ui/public/mock/candidate_points.csv
```

Output:

```text
parcel-locker-ui/public/mock/candidate-points.json
```

It checks older field names such as:

```text
name
neighborhood
MAH_JOIN
pop_2024
```

For current real-GA-output flow, prefer `process_ga_data.py`.

## 19. Web UI and Next.js dashboard integration

UI directory:

```text
parcel-locker-ui
```

Tech stack:

- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- React Leaflet.
- Recharts.
- `lucide-react`.
- OpenStreetMap tiles.

`General_GUIDE.md` documents current versions as Next.js 16, React 19, and Tailwind CSS 4. `parcel-locker-ui/README.md` states the stack generically without version numbers.

The UI is a visual decision-support interface. It can:

- Choose locker count `K`.
- Load candidate, boundary, and final archive result data.
- Trigger a real SPEA2 run locally through `POST /api/run-ga`.
- Browse archive solutions and Pareto flags.
- Select a Pareto solution with an MCDA accessibility-vs-inequity preference.
- Explore selected locker sets on a map.
- Inspect selected locker and solution metrics.

### 19.1 UI data modes

The UI has two data paths:

1. Archive asset mode:
   - Reads generated or committed assets from `parcel-locker-ui/public/mock/`.
   - This is the default data flow.

2. Trigger real optimization mode:
   - Calls `POST /api/run-ga`.
   - Runs Java SPEA2 from the project root.
   - Generates plots.
   - Refreshes UI mock assets.

Initial data loading reads:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/kadikoy_boundary.geojson
parcel-locker-ui/public/mock/ga-results.json
parcel-locker-ui/public/mock/archive_comparison_latest.png
```

`candidate-points.json` contains potential locker locations and attributes such as neighborhood, population, POI counts, forbidden status, and metadata.

`ga-results.json`, when present, contains final archive solutions, objective values, normalized values, Pareto flags, and best-`f1`/best-`f2` markers generated from `output/final_archive.csv`.

If files cannot be loaded, the app logs an error in the browser console.

### 19.2 Archive solution explorer terminology

Some UI variables and props still use the word "generation". In the current real-data flow, the UI browses archive solutions, not true generation-by-generation optimizer history.

Interpret it as:

```text
Archive solution explorer
```

not:

```text
True GA generation playback
```

### 19.3 Locker count and advanced controls

The left control panel contains:

- Locker count `K`.
- Run Optimization.
- MCDA accessibility/inequity preference slider.
- Run MCDA action.
- Current solution slider.
- Previous/next solution.
- Auto-play.
- Playback speed.
- Population size.
- Max generations.
- Mutation rate.
- Crossover rate.
- Archive size.
- Optional random seed.

Changing `K` updates advanced defaults through `getOptimalParams(k)`.

When the user clicks Run Optimization:

- `K` is clamped between `1` and `20`.
- Runtime parameters are sent to `/api/run-ga`.
- Java writes new archive CSV outputs.
- Python regenerates `ga-results.json` and the analysis plot.
- The current solution resets to the beginning.
- Playback stops.

### 19.4 MCDA selector

The MCDA slider chooses among existing Pareto solutions.

When the user clicks Run MCDA:

- Only Pareto-flagged archive solutions are considered.
- `norm_f1` and `norm_f2` are used when available.
- Raw objective values are min-max normalized as fallback.
- The solution with the lowest weighted cost is selected.
- No Java optimization run is triggered.

This is a decision-support layer, not a separate optimizer.

### 19.5 Playback and chart behavior

Playback controls:

- Previous.
- Play/Pause.
- Next.
- Solution slider.
- Playback speed slider.

When playback reaches the final solution, it loops back to the first solution.

The right archive panel shows an `f1`/`f2` scatter chart:

- All archive solutions are plotted.
- Pareto points are highlighted.
- Best-`f1` and best-`f2` Pareto solutions have dedicated colors.
- Clicking a chart point selects the archive solution.
- Focus mode expands the map/chart layout on large screens.

The UI also displays `archive_comparison_latest.png` when it exists and opens it in a fullscreen modal when clicked.

### 19.6 Map behavior

The center panel uses React Leaflet.

Map center:

```text
[40.9833, 29.0667]
```

Layers:

- Kadikoy boundary from GeoJSON.
- Candidate points not selected in the active solution as small gray markers.
- Existing locker context aggregated into neighborhood-level markers.
- Proposed lockers as larger blue circles.
- Selected proposed locker as a dark marker.

Current color meanings:

```text
black / dark -> currently selected proposed locker
blue         -> proposed locker in current archive solution
rose         -> existing-locker context marker
gray         -> candidate point
```

Clicking a locker on the map selects it. When a locker is selected, the map automatically flies to that location.

Locker popup fields:

- Locker name.
- Neighborhood.
- Latitude.
- Longitude.
- Display order in the archive solution.

### 19.7 Locker detail panel

The right detail panel shows:

- Locker name.
- Neighborhood.
- Archive solution number.
- Latitude.
- Longitude.
- Accessibility metric `f1`.
- Equity metric `f2`.
- Fitness metric.

The metrics belong to the active archive solution, not the individual locker.

### 19.8 Locker strip and selection behavior

The top strip shows lockers in the current archive solution.

Each card shows:

- Locker order.
- Locker label.
- Neighborhood.
- Selected state.

Clicking a card changes the active selected locker.

Selection preservation:

- If the previously selected locker still exists in the new active solution, it remains selected.
- If it no longer exists, selection is cleared.

## 20. Local/dev API and backend integration

The current project includes a local/dev integration path where the UI triggers Java and refreshes UI data. A production-grade backend remains separate future work.

Current route and related files:

```text
parcel-locker-ui/src/app/api/run-ga/route.ts
parcel-locker-ui/src/lib/server/ga-runner.ts
parcel-locker-ui/src/lib/server/runtime-config.ts
parcel-locker-ui/src/lib/python-runner.ts
parcel-locker-ui/src/lib/ga-api.ts
parcel-locker-ui/src/scripts/process_ga_data.py
```

### 20.1 `/api/run-ga`

POST body example:

```json
{
  "k": 5,
  "populationSize": 100,
  "maxGenerations": 30,
  "mutationRate": 0.1,
  "crossoverRate": 0.9,
  "archiveSize": 50,
  "randomSeed": 42
}
```

Current behavior:

1. Builds Maven `-Dexec.args` from supported request fields.
2. Runs `mvn compile exec:java` in the project root.
3. Streams Java progress lines to the UI as `text/event-stream`.
4. Runs `scripts/plot_archives.py`.
5. Copies `output/archive_comparison_latest.png` to `parcel-locker-ui/public/mock/archive_comparison_latest.png`.
6. Runs `parcel-locker-ui/src/scripts/process_ga_data.py`.
7. Streams completion or error status.

Supported runtime parameters passed to Java include:

```text
k
populationSize
maxGenerations
mutationRate
crossoverRate
archiveSize
randomSeed
```

Unsupported Java parameters, such as `beta`, should remain in `GAParameters` until Java exposes a validated runtime configuration format.

### 20.2 Environment variables

The current Next.js route and child processes support:

| Variable | Purpose | Default |
| --- | --- | --- |
| `PROJECT_ROOT` | Repository root | Parent of UI cwd in API route |
| `UI_ROOT` | `parcel-locker-ui` directory | API process cwd |
| `GA_CANDIDATE_CSV` | Candidate CSV path | `data/candidate_points.csv` |
| `GA_DISTANCE_MATRIX` | Distance matrix path | `data/kadikoy_distance_meters_nxn.npy` |
| `GA_OUTPUT_DIR` | Java/Python output directory | `output` |
| `UI_MOCK_DIR` | Generated UI public mock directory | `parcel-locker-ui/public/mock` |
| `MAVEN_CMD` | Maven executable override | `mvn.cmd` on Windows, `mvn` elsewhere |
| `PYTHON_CMD` | Python executable override | detection of `py`/`python` on Windows, `python3`/`python` elsewhere |
| `GA_MAX_RUNTIME_MS` | Java GA process timeout launched by `/api/run-ga` | `900000` |

Relative paths are resolved against `PROJECT_ROOT`. For local Next.js env loading, copy `.env.example` to `parcel-locker-ui/.env.local` only when defaults need overrides.

### 20.3 Current backend reality

The Java side is a batch computation engine. It is not yet a direct API-ready service.

Current `Main` exports:

```text
output/initial_archive.csv
output/final_archive.csv
output/run_metadata.json
```

The local/dev route adds:

```text
output/archive_comparison_latest.png
parcel-locker-ui/public/mock/archive_comparison_latest.png
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
```

Backend can already parse:

- Chromosomes.
- Raw objective values.
- Normalized objective values.
- SPEA2 metrics.
- Initial vs final archive snapshots.
- Final archive map-ready solutions through candidate metadata lookup.

### 20.4 Current backend limitations

`Main` is oriented toward:

- Terminal output.
- Final archive comparison.
- Offline plotting.

It does not yet provide:

- Run IDs.
- Structured generation-by-generation export.
- Generation summary file.
- Dedicated final Pareto front CSV.
- Machine-friendly result JSON beyond run parameter metadata.
- Job queue.
- Run isolation.
- Concurrency control.
- Persistence layer.

With unchanged `Main`, backend can support:

- Initial archive exploration.
- Final archive exploration.
- Final-result map display.
- Archive table/statistics.
- Hypervolume summary.

It cannot support:

- True generation slider based on actual GA states.
- Previous/next generation playback from optimizer history.
- Map animation across real generations.

### 20.5 Recommended backend endpoints

Minimal future API:

```text
POST /runs
GET /runs/latest/initial-archive
GET /runs/latest/final-archive
GET /runs/latest/final-pareto-front
GET /runs/latest/summary
```

Possible future `POST /runs` body:

```json
{
  "k": 8,
  "populationSize": 100,
  "archiveSize": 50,
  "maxGenerations": 500,
  "beta": 2.0,
  "crossoverRate": 0.9,
  "mutationRate": 0.1
}
```

For the first backend milestone, pass only CLI args currently supported by `Main`; leave unsupported parameters in `GAParameters` until runtime config is validated.

### 20.6 Recommended backend development order

Phase 1 - file-based final-result integration:

- Trigger run.
- Parse `initial_archive.csv` and `final_archive.csv`.
- Expose archive rows.
- Expose run summary.
- Optionally show initial vs final comparison.

Phase 2 - final Pareto front endpoint:

- Derive non-dominated subset from `final_archive.csv` server-side.
- Expose `/runs/latest/final-pareto-front`.
- Support cleaner final best-solutions UI.

Phase 3 - true Java generation exports:

- Add generation summaries.
- Add generation archive members.
- Add final Pareto front CSV.
- Enable real playback and map evolution.

### 20.7 Backend work to avoid for now

Avoid:

- Rewriting optimizer logic outside Java.
- Rebuilding SPEA2 internals on the server side.
- Duplicating normalization logic in another language.
- Inferring full generation playback from only initial/final snapshots.
- Running concurrent jobs against shared output files.

The Java layer should remain the authoritative implementation of optimization logic.

### 20.8 Recommended Java-side additions later

Most valuable future Java outputs:

1. `final_pareto_front.csv`
2. `generation_summary.csv`
3. `generation_archive_members.csv`
4. Optional structured JSON export.
5. Run-specific output folders.

## 21. Phase 1 local/container deployment

Phase 1 keeps the existing local/dev architecture:

- Next.js server owns `/api/run-ga`.
- The API route spawns Maven for Java.
- After Java finishes, it runs Python plotting and UI conversion scripts.
- Generated outputs are shared files, not run-ID-isolated artifacts.

Required tools:

- Node.js and npm for `parcel-locker-ui`.
- Java 17.
- Maven.
- Python 3.
- Python packages from `requirements.txt`.

Local run:

```bash
mvn compile
python3 -m pip install -r requirements.txt
cd parcel-locker-ui
npm install
npm run dev
```

Docker Compose:

```bash
docker compose up --build
```

Compose mounts:

- `./data` read-only at `/app/data`.
- `./output` read-write at `/app/output`.
- `./parcel-locker-ui/public/mock` read-write for generated UI assets.

Container files:

| File | Role |
| --- | --- |
| `Dockerfile` | Builds a Node 20 Debian image with Java 17, Maven, Python 3, Python requirements, Maven compilation, UI dependencies, and production Next.js build |
| `docker-compose.yml` | Runs one container on port `3000` and mounts `data`, `output`, and UI mock assets |
| `.dockerignore` | Excludes local build outputs, raw GIS data, dependency folders, caches, logs, and local env files |
| `.env.example` | Documents runtime path/executable overrides |

Phase 1 limitations:

- `/api/run-ga` keeps one request open until Java and Python finish.
- Outputs are shared files, not run-ID-isolated.
- Concurrent runs are not safe.
- UI reads generated mock/public files.
- Not suitable for Vercel-only deployment because the route needs long-running process execution and writable files.
- Robust multi-user deployment needs run IDs, job status/result endpoints, per-run output folders, and concurrency control.

## 22. Output files and folders

Default Java + plotting run:

```text
output/
├── initial_archive.csv            archive snapshot after generation 0
├── final_archive.csv              archive snapshot after final generation
├── run_metadata.json              run parameters for the latest Java run
└── archive_comparison_latest.png  initial vs final archive plot
```

Parameter grid search:

```text
output/
├── parameter_analysis_results.csv        full grid-search output
├── parameter_analysis_results_smoke.csv  optional smoke-mode output
└── ga_configuration_table.csv            GA_ID to parameter mapping
```

Parameter analysis statistics:

```text
output/statistics/
├── descriptive_by_k.csv
├── friedman_summary.csv
├── posthoc_bonferroni.csv
└── selected_configurations.csv
```

UI generated assets:

```text
parcel-locker-ui/public/mock/
├── candidate-points.json
├── candidate_points.csv
├── ga-results.json
├── archive_comparison_latest.png
└── kadikoy_boundary.geojson
```

Legacy tracked examples such as `archive_comparison.png`, `objective_space_nd_points.csv`, and `objective_space_run_summary.csv` may be present in `output/`, but they are from earlier workflows and are not produced by the current analyzer.

The current working tree also contains an older parameter-analysis folder:

```text
output/parameter analysis/
├── parameter_analysis_results.csv
└── terminal.txt
```

This belongs to the legacy `scripts/plot_analysis.py` path/schema, not the current `ParameterAnalyzer` + `statistical_analysis.py` path.

Report figure outputs may exist under:

```text
sections/figures/final_results/
```

These are generated/report artifacts, not runtime inputs for the Java optimizer or UI route.

## 23. Backup experimental main

File:

```text
backup/(experimental)Main.java
```

This is not used by the default Maven run.

It was designed for objective-space calibration rather than final hypervolume assessment.

It:

- Generates run IDs and timestamps.
- Collects non-dominated snapshots every N generations.
- Writes `objective_space_run_summary.csv`.
- Writes `objective_space_nd_points.csv`.
- Writes run-specific archive CSVs.
- Helps estimate ideal/nadir objective-space bounds.

It may be useful as a reference for future generation-level exports.

## 24. Build and test status

Java version:

```text
17
```

Compile:

```bash
mvn -q compile
```

Run optimizer:

```bash
mvn -q compile exec:java
```

Run parameter analyzer:

```bash
mvn -q compile exec:java -Panalyze
```

Test status:

- There are currently no JUnit source tests.
- `src/test` is absent in the current working tree.
- `target/test-classes` may exist after a Maven compile, but it is an empty build artifact rather than real test output.

Recommended first tests:

- `Dominance` minimization cases.
- `Pareto` non-dominated extraction.
- `Individual` canonical chromosome sorting.
- `Variation` chromosome length and uniqueness.
- `ObjectiveNormalizer` clamp and degenerate bounds.
- Small synthetic distance matrix tests for `f1` and `f2`.

## 25. End-to-end workflows

### 25.1 Single-run development path

```bash
# 1. Prepare or verify QGIS candidate table.
# 2. Ensure metric GIS operations used EPSG:32635.
# 3. Ensure candidate output includes EPSG:4326 lon and lat.
# 4. Export full runtime table as data/candidate_points.csv,
#    keeping feasible and forbidden rows with is_forbidden.

python3 scripts/calculate_poi_weights.py
python3 scripts/prepare_demand.py

python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy

mvn -q compile
mvn -q compile exec:java
python3 scripts/plot_archives.py

cd parcel-locker-ui
python3 src/scripts/process_ga_data.py
npm run dev
```

Only regenerate matrix artifacts if candidate coordinates or the candidate set changed.

### 25.2 Hyperparameter grid-search path

```bash
mvn -q compile exec:java -Panalyze
python3 scripts/statistical_analysis.py
```

Selected configurations:

```text
output/statistics/selected_configurations.csv
```

## 26. Reproducibility-critical contracts

### 26.1 Candidate ID and matrix alignment

```text
Java sorted candidate order == distance matrix row/column order
```

Protect this before every experiment.

### 26.2 Chromosome set semantics

Chromosomes are unordered selected candidate sets.

Preserve:

- `Individual` canonical sorting.
- Archive deduplication by chromosome.
- Variation repair ensuring fixed length and unique genes.

### 26.3 Forbidden candidates

Current contract:

```text
is_forbidden = 0 -> selectable as locker location
is_forbidden = 1 -> kept as demand grid point, not selectable
```

Preserve CSV and matrix row-set synchronization.

### 26.4 Objective minimization

Both objectives are minimized. If direction changes, update Java dominance, Pareto, HV, plotting, UI conversion, and UI interpretation.

### 26.5 Final-ND normalization

Final archive hypervolume uses bounds derived from final archive non-dominated solutions. Hypervolume values from separately normalized archives should not be compared directly.

### 26.6 CSV schema and format

`CsvLoader` maps by header name, so column order is flexible. Required column names and simple comma-separated format remain part of the contract.

### 26.7 Demand preparation side effects

`scripts/prepare_demand.py` overwrites `data/candidate_points.csv`.

### 26.8 Local/dev API side effects

`/api/run-ga` spawns Maven and Python from the development server, writes shared outputs, and can dirty generated files.

### 26.9 Generated artifacts

Treat `output` files as generated artifacts, but also useful examples. Do not edit Maven `target`.

### 26.10 Raw GIS files

Raw files under `data/raw` are preparation sources, not Java runtime inputs.

## 27. How to interpret results

After a run:

1. Check that `final_archive.csv` row count matches archive size.
2. Check that each chromosome has exactly `K` IDs.
3. Check that selected IDs are not forbidden.
4. Check `f1` and `f2` ranges for plausibility.
5. Check non-dominated count.
6. Inspect the raw objective plot.
7. Compare initial and final archive spread.
8. Check final HV ratio and raw-objective improvement metrics.
9. Inspect selected locker geography in the UI.

Decision-making note:

- Do not select a solution only because it has best `f1`; it may be inequitable.
- Do not select a solution only because it has best `f2`; it may have poor accessibility.
- The Pareto archive exposes the accessibility-equity tradeoff.
- MCDA can help choose among Pareto solutions using explicit preferences.

## 28. Implementation traceability matrix

| Desired change | Start here |
| --- | --- |
| Change `f1` or `f2` | `src/main/java/service/FitnessCalculator.java` |
| Change GA parameters | `src/main/java/config/GAParameters.java` |
| Change SPEA2 strength/raw/density | `src/main/java/algorithm/Evaluate.java` |
| Change archive selection | `src/main/java/algorithm/Survivor.java` |
| Change truncation | `src/main/java/algorithm/helper/Truncation.java` |
| Change parent selection | `src/main/java/algorithm/Selection.java` |
| Change crossover/mutation | `src/main/java/algorithm/Variation.java` |
| Change CSV mapping | `src/main/java/io/CsvLoader.java` |
| Change NPY matrix loading | `src/main/java/io/DistanceMatrixLoader.java` |
| Change hypervolume | `src/main/java/service/HypervolumeIndicator.java` |
| Change archive export format | `src/main/java/app/Main.java` |
| Change grid search | `src/main/java/app/ParameterAnalyzer.java` |
| Change grid search statistical analysis | `scripts/statistical_analysis.py` |
| Change demand model | `scripts/prepare_demand.py` |
| Change matrix generation | `data/prepare_ga_inputs.py` |
| Change archive plot | `scripts/plot_archives.py` |
| Change UI JSON conversion | `parcel-locker-ui/src/scripts/process_ga_data.py` |
| Change UI local GA trigger | `parcel-locker-ui/src/app/api/run-ga/route.ts` |
| Change UI GA process orchestration | `parcel-locker-ui/src/lib/server/ga-runner.ts` |
| Change UI runtime path/env config | `parcel-locker-ui/src/lib/server/runtime-config.ts` |
| Change UI optimization stream client | `parcel-locker-ui/src/lib/ga-api.ts` |
| Change UI solution helpers | `parcel-locker-ui/src/lib/solution-utils.ts` |
| Change UI chart data shaping | `parcel-locker-ui/src/lib/chart-data.ts` |
| Change MCDA solution selection | `parcel-locker-ui/src/lib/mcda.ts` |
| Change dashboard layout | `parcel-locker-ui/src/app/page.tsx` and `parcel-locker-ui/src/components/dashboard/*` |

## 29. Limitations and technical debt

### 29.1 No automated tests

There is no real automated test suite. See Section 24 for recommended first tests.

### 29.2 Fragile CSV parsing

`CsvLoader` uses simple comma splitting. Replace it with a robust CSV parser before introducing fields that may contain commas.

### 29.3 POI column selection

Demand scripts exclude generated columns from raw POI selection. If new derived POI columns are added, consider an explicit raw POI allow-list.

### 29.4 Forbidden candidate handling

Current handling is implemented and intentional:

```text
is_forbidden = 0 -> 2535 rows
is_forbidden = 1 -> 182 rows
```

Forbidden cells remain demand points, cannot be selected as lockers, and preserve CSV/matrix row synchronization.

### 29.5 UI API route spawns local processes

The local API route spawns Maven and Python from the Next.js server.

Recommended future work:

- Introduce runtime configuration.
- Add CLI or JSON config input for Java.
- Create run-specific output folders.

### 29.6 No true generation-level export

Default `Main` exports only initial and final archive snapshots.

For true generation playback, Java should export:

- `generation_summary.csv`
- `generation_archive_members.csv`
- `generation_best_front.csv`
- Or structured JSON equivalent.

### 29.7 ParameterAnalyzer is long-running

`ParameterAnalyzer` seeds `PopulationInitializer`, `Selection`, and `Variation` for deterministic seeded configurations. The full grid is long-running and writes a single `output/parameter_analysis_results.csv`.

Recommended future work:

- Add resume/checkpoint support.
- Write run-specific or timestamped analysis outputs when preserving multiple experiments matters.

### 29.8 Haversine distance is not network distance

The current matrix uses Haversine straight-line distances. A future realism improvement is walking or road-network distance.

### 29.9 Hypervolume interpretation is sensitive

Interpret HV together with:

- Raw Pareto plot.
- Non-dominated count.
- Best `f1`.
- Best `f2`.
- Spatial distribution of selected lockers.

### 29.10 Production backend missing

No production backend service exists yet. The current system is a batch optimizer plus a local/development UI bridge.

## 30. Future work

### 30.1 Short-term hardening

1. Add automated tests.
2. Add schema validation for `candidate_points.csv`.
3. Replace `CsvLoader` with robust quoted-field CSV parsing.
4. Add explicit POI column allow-list if the feature set grows.
5. Add performance tests for fitness evaluation.

### 30.2 Backend readiness

1. Move orchestration from `Main` into reusable `GARunner` or `OptimizerService`.
2. Add production-grade runtime config validation.
3. Populate `GAState` and `GAResult`.
4. Add run-specific output folders.
5. Produce structured JSON output.
6. Add job isolation and concurrency control.

### 30.3 True UI generation playback

1. Export per-generation archive snapshots from Java.
2. Distinguish archive solutions from generation snapshots in UI schema.
3. Add real generation slider data.
4. Animate map evolution from real optimizer states.

### 30.4 Scientific and methodological improvements

1. Test network distance instead of Haversine distance.
2. Run sensitivity analysis for lambda in demand generation.
3. Compare POI weighting methods:
   - Entropy Weight Method.
   - AHP.
   - Equal weights.
   - Expert-defined weights.
4. Test alternative equity metrics:
   - Gini.
   - Mean absolute deviation.
   - Max-min fairness.
   - Percentile gap.
5. Add quality indicators:
   - Spacing.
   - Spread.
   - Epsilon indicator.
   - Archive uniqueness.

### 30.5 Hypervolume and assessment

If archive quality is still not distinguishable enough after objective scaling fixes, refine the assessment normalization window. Keep final-ND-based assessment and raw-objective improvement metrics conceptually separate.

## 31. Possible inconsistencies / version differences

This section keeps differences rather than deleting them.

1. `scripts/plot_analysis.py` vs current `ParameterAnalyzer`:
   - `plot_analysis.py` expects an older path and schema: `output/parameter analysis/parameter_analysis_results.csv` with columns such as `Lambda`, `PopSize`, `MutRate`, and `CrossRate`.
   - Current canonical post-processing uses `scripts/statistical_analysis.py` on `output/parameter_analysis_results.csv`.

2. UI terminology:
   - Some UI names still say "generation".
   - Current real-data UI flow is archive solution browsing, not true generation-by-generation optimizer playback.

3. Backend request examples:
   - Backend guide examples include future fields such as `beta`.
   - Current local/dev `/api/run-ga` should pass only runtime fields supported by `Main`; unsupported parameters remain in `GAParameters`.

4. Output artifacts:
   - Older files such as `archive_comparison.png`, `objective_space_nd_points.csv`, and `objective_space_run_summary.csv` may exist as tracked or generated examples.
   - The current working tree also contains `output/parameter analysis/parameter_analysis_results.csv` and an empty `output/parameter analysis/terminal.txt` from the older plotting workflow.
   - Report figure artifacts exist under `sections/figures/final_results/`.
   - Current `ParameterAnalyzer` writes only `parameter_analysis_results.csv`, optional smoke output, and `ga_configuration_table.csv`.

5. Raw GIS inventory:
   - `readme.md` and `General_GUIDE.md` list overlapping but not identical raw/intermediate artifacts under `data/raw`.
   - The actual root `data` directory also contains `candidate_points_backup.csv`, `candidate_points_excel.xls`, and `candidate_points.qmd`.
   - Treat `data/raw` as an audit/reproduction inventory rather than a fixed runtime input list.

6. Tech stack version detail:
   - `parcel-locker-ui/README.md` lists the UI stack generically.
   - `General_GUIDE.md` documents Next.js 16, React 19, and Tailwind CSS 4.

7. Demand model fallback:
   - Guides state Java falls back to population-only demand when `poi_score` or `demand_final` is absent.
   - This is a debugging fallback, not scientifically equivalent to the prepared demand model.

8. Hypervolume comparison:
   - Earlier workflows explored broader objective-space calibration.
   - Current `Main` uses final-ND-based archive export normalization and final archive HV only; initial-to-final improvement is not official initial-HV vs final-HV.

## 32. Recommended source review order

For report writing, auditing, or continued development:

1. `COMPREHENSIVE_PROJECT_GUIDE.md`
2. `General_GUIDE.md`
3. `readme.md`
4. `src/main/java/app/Main.java`
5. `src/main/java/service/FitnessCalculator.java`
6. `src/main/java/algorithm/Evaluate.java`
7. `src/main/java/algorithm/Survivor.java`
8. `src/main/java/algorithm/Variation.java`
9. `src/main/java/config/GAParameters.java`
10. `scripts/prepare_demand.py`
11. `data/prepare_ga_inputs.py`
12. `scripts/plot_archives.py`
13. `src/main/java/app/ParameterAnalyzer.java`
14. `scripts/statistical_analysis.py`
15. `scripts/plot_analysis.py`
16. `parcel-locker-ui/src/app/api/run-ga/route.ts`
17. `parcel-locker-ui/src/lib/server/ga-runner.ts`
18. `parcel-locker-ui/src/lib/server/runtime-config.ts`
19. `parcel-locker-ui/src/lib/ga-api.ts`
20. `parcel-locker-ui/src/lib/solution-utils.ts`
21. `parcel-locker-ui/src/lib/chart-data.ts`
22. `parcel-locker-ui/src/lib/mcda.ts`
23. `parcel-locker-ui/src/scripts/process_ga_data.py`
24. `parcel-locker-ui/src/app/page.tsx`

## 33. Current technical status

Working:

- Candidate CSV loading.
- Distance matrix loading.
- Initial population generation.
- `f1` and `f2` evaluation.
- SPEA2 strength/raw/density/total fitness.
- Archive survivor selection.
- Archive duplicate handling.
- Truncation.
- Binary tournament selection.
- Shared-gene crossover.
- Mutation and repair.
- Initial/final archive export.
- Shared normalized assessment.
- Forbidden candidate filtering for locker selection.
- Hypervolume computation.
- Parameter grid search.
- Archive plotting.
- UI archive solution explorer.
- Local/dev UI-triggered Java run.
- UI JSON generation from final archive.

Missing or incomplete:

- Automated tests.
- Production backend.
- Production-grade runtime config validation and service wrapper.
- Generation-level export.
- Robust CSV parsing.
- Production-grade CSV schema validation.
- Network-distance matrix.
- True generation playback in the UI.

## 34. Final summary

This project is a multi-objective SPEA2 optimization system for selecting parcel locker locations in Kadikoy. It uses `2717` candidate grid centroids from a QGIS/OSM workflow; `2535` are selectable locker candidates and `182` are forbidden rows kept as demand grid points. Each candidate has spatial, neighborhood, POI, bus stop, existing locker, population, and demand attributes.

The Java optimizer is the authoritative implementation of the optimization methodology. Python scripts prepare demand values, generate matrix artifacts, plot archive outputs, and process analysis results. The Next.js UI visualizes final archive solutions and can locally trigger Java, but that trigger is a development bridge rather than a production backend.

The contracts to protect first are:

1. Candidate ID to matrix index alignment.
2. Chromosome set semantics.
3. Selectable-vs-demand handling for forbidden candidates.
4. Final-ND-based normalization for final archive hypervolume assessment.

The highest-value next engineering improvements are tests, runtime configuration, schema validation, robust CSV parsing, run-specific outputs, and generation-level exports for the UI.

## Source files reviewed

The following guide/README files were reviewed and consolidated:

- `readme.md`
- `guide.md`
- `General_GUIDE.md`
- `DEPLOYMENT_PHASE1.md`
- `data/kadikoy_ARTIFACTS_GUIDE.md`
- `scripts/guide.md`
- `src/main/java/SRC_GUIDE.MD`
- `src/main/java/analyse_guide.md`
- `src/main/java/app/backend_guide.md`
- `parcel-locker-ui/README.md`
