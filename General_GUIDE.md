# Technical Report Source Guide: Location Optimization with Genetic Algorithm

This document is a report-oriented technical source guide for the Kadikoy parcel locker location optimization project. It explains the project objective, spatial data preparation workflow, feature engineering process, optimization methodology, software implementation, outputs, limitations, and future work.

The guide is intentionally detailed. Its purpose is to preserve the reasoning behind the project, not only the final implementation. It can be used as source material for the methodology, implementation, experimental setup, and limitations chapters of a formal project report.

Recommended report usage:

- Use Sections 1-4 for the project overview and system architecture.
- Use Section 5 for the GIS/OSM data preparation and feature engineering chapter.
- Use Sections 6-9 for the candidate dataset, demand model, distance matrix, and mathematical formulation.
- Use Sections 10-20 for the Java optimization methodology and SPEA2 implementation.
- Use Sections 21-24 for scripts, UI integration, outputs, and backend-oriented discussion.
- Use Sections 30-38 for limitations, implemented design decisions, future work, reproducibility notes, and conclusion.

## 1. Executive Summary

The project solves a multi-objective parcel locker location optimization problem for Kadikoy.

The core idea is:

- Build a finite set of candidate locker locations from a 100m x 100m grid.
- Enrich each candidate with demand, POI, public transport, existing locker, neighborhood, and feasibility attributes.
- Precompute a candidate-to-candidate distance matrix.
- Use a Java SPEA2-style multi-objective genetic algorithm to select `K` candidate IDs.
- Evaluate each selected set by accessibility and neighborhood equity.
- Export the initial and final archives.
- Visualize the final archive and map-ready locker selections in a Next.js dashboard.

The most important technical contract is:

```text
The order of candidates in the Java repository must match the row/column order of
data/kadikoy_distance_meters_nxn.npy.
```

The project enforces this by sorting candidates by ascending `id` in `CandidateRepository.finalizeRepository()`. The distance matrix was also generated using ascending candidate ID order.

If this contract breaks, the optimizer will still run, but all distance-based objective values will silently become wrong.

## 2. Project Goal

The project aims to recommend parcel locker placement locations in Kadikoy by selecting a subset of candidate grid cells.

Each optimization solution selects:

```text
K candidate locations
```

The current default value is:

```text
K = 5
```

Each solution is evaluated using two minimization objectives:

1. Accessibility cost: demand-weighted distance cost to the nearest selected locker.
2. Equity cost: inequality of accessibility quality across neighborhoods.

The problem is multi-objective because the most accessible solution is not necessarily the fairest solution. Concentrating lockers around high-demand areas may reduce global average distance but may also leave some neighborhoods underserved. Therefore, the optimizer searches for a Pareto archive rather than a single absolute optimum.

## 3. Main Technology Layers

| Layer | Directory | Role |
| --- | --- | --- |
| Java optimization engine | `src/main/java` | SPEA2-style multi-objective GA, objective functions, archive handling, selection, variation |
| Data and GIS artifacts | `data` | Candidate CSV, distance matrix, raw QGIS/GeoPackage files |
| Python scripts | `scripts` and `data/prepare_ga_inputs.py` | Demand preparation, POI weighting, distance matrix generation, archive plotting |
| Generated outputs | `output` | Archive CSVs, parameter analysis CSVs, plots |
| Web UI | `parcel-locker-ui` | Next.js dashboard, map, archive solution exploration, local/dev GA trigger |
| Backup/experimental code | `backup` | Older/experimental `Main.java` for objective-space calibration |

## 4. Project Artifacts and Implementation Structure

Important root files:

- `pom.xml`: Maven configuration. Uses Java 17. The default `exec:java` entry point is `app.Main`; the `-Panalyze` Maven profile runs `app.ParameterAnalyzer`.
- `readme.md`: Short quick-start guide.
- `guide.md`: Older shorter project guide.
- `General_GUIDE.md`: This file. It is the comprehensive report-source and technical methodology guide.
- `.gitignore`: Ignores Maven `target`, Python cache, macOS `.DS_Store`, virtual environments, and some generated output subfolders. Several current `output/*.csv` and PNG artifacts are still present in the repository as example outputs.

## 5. Full Data Preparation Methodology: QGIS/OSM to GA-Ready CSV

This section documents the spatial data preparation and feature engineering workflow used to create the final candidate dataset. It follows the logic: what was done, why it was needed, how it was performed, and what it produced.

### 5.1 Objective of the Data Preparation Workflow

The data preparation objective was to create a clean, finite, optimization-ready candidate dataset for the Kadikoy parcel locker location problem.

The dataset is designed to feed a multi-objective SPEA2 genetic algorithm. The algorithm does not search over continuous coordinates. Instead, it selects a subset of candidate IDs from a prepared candidate table.

To make the spatial search space finite, manageable, and interpretable:

- The Kadikoy study area was discretized into a 100m x 100m grid.
- The centroid of each grid cell was used as a candidate point.
- Candidate points were enriched with demand and accessibility proxy features.
- Candidate points were enriched with POI category counts.
- Candidate points were enriched with public bus stop counts.
- Candidate points were enriched with existing parcel locker proximity counts.
- Candidate feasibility was modeled through grid-level forbidden-area coverage.

This approach supports the interpretation that the GA output recommends a grid cell. The final exact locker installation point inside or near that cell can then be decided through on-site inspection and operational constraints.

### 5.2 CRS Strategy: EPSG:32635 and EPSG:4326

CRS consistency was one of the most important sources of errors during the workflow. A strict CRS policy was therefore used.

#### 5.2.1 Why EPSG:32635 Was Used

All metric GIS operations must be performed in a coordinate system whose units are meters. The project standardized metric processing in:

```text
EPSG:32635
WGS84 / UTM Zone 35N
Units: meters
```

Operations requiring EPSG:32635 include:

- 300m buffers.
- Overlay operations such as intersection, union, and dissolve.
- Area computations.
- Coverage ratio calculations.
- Counting points inside buffer polygons.
- Counting existing lockers inside candidate neighborhoods.

Using EPSG:4326 for these operations would be wrong because EPSG:4326 uses degrees, not meters. A "300m buffer" in EPSG:4326 can become a nonsensical "300 degrees buffer".

#### 5.2.2 Why EPSG:4326 Was Still Needed

While computation was performed in EPSG:32635, visualization and UI integration require geographic coordinates.

Therefore:

- Candidate tables were supplemented with longitude and latitude values.
- These longitude and latitude values are in EPSG:4326.
- GA-selected candidate IDs can be pinned on web maps using `lon` and `lat`.
- The Next.js/Leaflet UI can display selected lockers and candidate points.

#### 5.2.3 CRS Issue Encountered and Resolution

Repeated CRS-related issues occurred:

- Some layers were in EPSG:4326.
- Other layers were in EPSG:32635.
- "Zoom to layer" showed layers in different locations.
- Overlay operations produced zero intersections.
- Some geometry fixing steps appeared to move layers.

The root cause was not the geometry fix itself. The real issue was CRS mismatch, extent mismatch, or an inconsistent reprojection chain.

Resolution:

- Relevant layers were restored from backup where needed.
- All metric workflow layers were re-exported into EPSG:32635.
- Overlay and buffer operations were repeated under strict CRS consistency.
- Geographic coordinates were added later only for visualization and UI use.

### 5.3 POI Data Cleaning and Standardization

#### 5.3.1 Initial POI Problem

At the beginning, two different POI representations were observed:

- One POI layer represented POIs as point geometries.
- Another layer looked like polygon or area-like features.

The feature counts were different, confirming that these were not simple duplicates.

#### 5.3.2 Why Only Point POIs Were Kept

The intended metric was POI density as point counts inside a local neighborhood. Polygon-like POIs can distort this logic because they may:

- Represent the same real-world feature differently from point POIs.
- Create duplicate representations of the same place.
- Break the assumption that POIs are countable locations or events.
- Overweight large polygonal facilities compared to point facilities.

Therefore, the project kept point POIs for count-based POI features.

#### 5.3.3 Output of POI Cleaning

The point-type POI layers were merged using QGIS Merge Vector Layers.

Output:

```text
pois_all_points
```

This became the standardized point-only POI layer. It was processed in EPSG:32635 for metric buffer counting.

### 5.4 Total POI Density: 300m Buffer-Based Counting

#### 5.4.1 Why 300m Buffers Were Used

A 100m x 100m grid cell is too small to represent local neighborhood activity. Counting only POIs inside a single grid cell can be unstable and uninformative.

The project therefore adopted a local neighborhood approach:

- Each candidate point represents the centroid of a 100m grid cell.
- POI features reflect a walkable local neighborhood around that candidate.
- The chosen local neighborhood radius was 300m.

This gives a more meaningful proxy for the urban activity around a candidate.

#### 5.4.2 How the Total POI Count Was Computed

Steps:

1. Generate 300m buffers around candidate points.
2. Use QGIS Count Points in Polygon.
3. Set polygons to candidate buffers.
4. Set points to `pois_all_points`.
5. Write the resulting count to a field such as `NUMPOINTS`.

Output:

```text
Candidate-level total POI count column
```

#### 5.4.3 Verifying the 300m Distance

The correctness of the 300m distance was validated by:

- Confirming the buffer layer CRS was EPSG:32635.
- Visually inspecting buffer sizes.
- Using the measurement tool where necessary.

### 5.5 POI Categorization and Multi-Column POI Features

#### 5.5.1 Why POIs Were Categorized

A single total POI count assumes each POI contributes equally to parcel locker demand. In practice, different POI types may influence demand differently.

Examples:

- Universities can generate different parcel demand patterns than ATMs.
- Transport hubs can matter differently from schools.
- Hospitals, banks, and post offices have distinct urban activity meanings.

Therefore, category-specific POI count columns were produced.

#### 5.5.2 How POI Categories Were Determined

The `amenity` values in the POI table were analyzed using QGIS tools such as:

```text
Statistics by Categories
```

Based on the observed distribution and project needs, these categories were defined:

1. Transportation, initially including NULL, `ferry_terminal`, and `bus_station`.
2. University.
3. School.
4. Hospital.
5. Bank.
6. ATM.
7. Post office.

Later, public bus stops were separated into an additional feature because they represent a different accessibility signal from major transportation hubs.

#### 5.5.3 How Category Layers Were Created

For each POI category, category-specific layers were extracted from `pois_all_points` using:

- Extract by Attribute.
- Extract by Expression.

Example category layers:

- `poi_university`
- `poi_school`
- `poi_bank`
- `poi_atm`
- `poi_hospital`
- `poi_post_office`
- `poi_transport`

#### 5.5.4 How Category Counts Were Computed

For each category layer:

1. Use the same candidate 300m buffer polygons.
2. Run Count Points in Polygon.
3. Use the category layer as points.
4. Produce a category-specific count field.

Examples:

- `poi_bank`
- `poi_school`
- `poi_atm`
- `poi_university`
- `poi_hospital`
- `poi_post_office`
- `poi_transport`

#### 5.5.5 Consolidating Category Outputs

Category counts were initially produced as separate output layers. Since all outputs were derived from the same candidate set, they had a one-to-one relationship with candidate IDs.

The category outputs were consolidated using:

```text
Join attributes by field value
```

The join was performed using consistent `id` or `fid` fields.

Output:

```text
Consolidated candidate attribute table with multiple POI category columns
```

An intermediate table such as `candidate_last_pois_joined` was later merged into the final candidate dataset.

#### 5.5.6 Mistaken Column Creation and Fix

At one point, an incorrect column was created, for example in the bank layer.

It was fixed by:

- Entering edit mode.
- Removing the field from the attribute table tools.
- Using Field Calculator or Delete Field tools where appropriate.

### 5.6 Public Bus Stop Feature

#### 5.6.1 Why Bus Stops Were Separate

The initial transportation category captured major transportation hubs such as metro, ferry, or bus station features. The project also needed ordinary public bus stop density as a distinct accessibility indicator.

Therefore, bus stops were treated separately from the broader `poi_transport` category.

#### 5.6.2 Bus Stop Collection with QuickOSM

Bus stops were collected from OpenStreetMap using QuickOSM.

Query:

```text
Key: highway
Value: bus_stop
Extent: Kadikoy boundary layer
```

Overpass API timeouts were encountered. These were mitigated by:

- Increasing timeout settings.
- Rerunning the query.

#### 5.6.3 Boundary Overshoot and Clipping

Even when using the Kadikoy extent, the query sometimes returned features outside Kadikoy.

To enforce spatial validity:

- The bus stop layer was clipped by the Kadikoy boundary.

Output:

```text
bus_stop_clipped
```

#### 5.6.4 Adding Bus Stop Counts to Candidates

The same 300m buffer framework was used:

1. Use candidate 300m buffers as polygons.
2. Count `bus_stop_clipped` points inside each buffer.
3. Join the resulting count column into the candidate table.

Output:

```text
Candidate-level bus stop count feature
```

In the final Java-readable CSV, this appears as:

```text
poi_bus_stop
```

### 5.7 Existing Parcel Locker Integration

#### 5.7.1 Data Source

Existing locker locations were provided externally as:

```text
kadikoy_lockers_final.geojson
```

This was loaded into QGIS as a point layer.

The current repository also contains a metric locker artifact:

```text
data/raw/lockers_32635.gpkg
```

#### 5.7.2 CRS Alignment

To support correct 300m neighborhood counting, the locker layer was re-exported to:

```text
EPSG:32635
```

#### 5.7.3 Existing Locker Proximity Feature

The project computed the number of existing lockers within 300m of each candidate.

Method:

1. Use candidate 300m buffers as polygons.
2. Use existing locker points as the point layer.
3. Run Count Points in Polygon.
4. Join the resulting count into the candidate table.

Final column:

```text
locker_count
```

#### 5.7.4 Interpretation of Forbidden Candidates with Nearby Existing Lockers

A candidate can be forbidden while still having nonzero existing lockers within its 300m buffer.

This means:

- The candidate cell itself is infeasible.
- The surrounding neighborhood can still contain existing lockers.
- This is useful context for demand, service coverage, or competition analysis.

### 5.8 Forbidden and Non-Installable Area Modeling

This was the most complex data preparation stage because it combined CRS, overlay, geometry, and area-ratio logic.

#### 5.8.1 Key Design Decision: Flag Instead of Delete

The feasibility rule was based on grid polygons, not candidate point centroids.

The adopted rule:

```text
A candidate should be excluded only if its entire grid cell is inside forbidden areas.
```

The project therefore switched from point-based feasibility checks to grid polygon-based feasibility checks.

Candidates were flagged rather than immediately deleted:

- `is_forbidden` remains available for future scenario testing.
- Export filters can remove forbidden candidates when needed.
- The full feasibility logic remains auditable.

#### 5.8.2 Forbidden Landuse Categories

Using the landuse layer, only fully excluded classes were selected through expression filters.

Examples of forbidden classes:

- `cemetery`
- `military`
- `construction`
- `railway`
- `industrial`
- `forest`
- `meadow`
- `brownfield`

The exact category list depends on the observed categories in the actual dataset.

#### 5.8.3 Forbidden Building Polygons

Building polygons were prepared similarly:

- Filter building polygons if needed.
- Apply Fix Geometries where required.
- Keep them in the metric CRS workflow.

#### 5.8.4 Creating a Single Forbidden Mask

Steps:

1. Merge forbidden landuse and forbidden buildings:

```text
Merge Vector Layers
Inputs: forbidden_buildings_fixed + forbidden_landuse_raw
Output: forbidden_merged
```

2. Dissolve all features:

```text
Dissolve all features
Output: forbidden_mask
```

The expected result is a single union mask feature. One output feature is correct here.

3. Optionally run Fix Geometries again for robustness.

#### 5.8.5 Why Intersection Sometimes Returned Zero

When the intersection between `grid_100m_clipped` and `forbidden_mask` returned an empty output, the cause was almost always:

- CRS mismatch.
- Layers not actually overlapping in the same coordinate space.
- Incorrect reprojection or stale layer extent.

After restoring from backup and standardizing CRS, intersection produced correct results.

#### 5.8.6 Computing Forbidden Coverage Ratio

The project computed the fraction of each grid cell covered by forbidden areas.

Steps:

1. Intersect grid cells with the forbidden mask:

```text
grid_100m_clipped intersect forbidden_mask -> grid_forbidden_intersection
```

2. Compute area of each intersection piece:

```text
forb_area_part = $area
```

3. Compute the full grid cell area on the grid layer:

```text
grid_area = $area
```

4. Aggregate forbidden intersection areas by grid ID:

```text
Processing -> Aggregate
Group by: id
sum(forb_area_part) -> forb_area_sum
Output: grid_forbidden_sum
```

5. Join forbidden sums back to the full grid:

```text
Join attributes by field value
grid.id <-> sum.id
Output: grid_with_forbidden_area
```

6. Compute ratio and flag:

```text
forbidden_ratio = forb_area_sum / grid_area
is_forbidden = 1 if forbidden_ratio == 1 else 0
```

Grid cells not matched in the join are normal. They had no intersection with forbidden areas, so their effective `forb_area_sum` is zero.

#### 5.8.7 Propagating Forbidden Flags to Candidate Points

The `is_forbidden` flag was joined from grid polygons to candidate centroid points using shared grid identifiers.

Output:

```text
candidate_with_forbidden_flag
```

#### 5.8.8 Runtime Handling of Forbidden Candidates

The current runtime CSV keeps both feasible and forbidden candidate rows:

```text
is_forbidden = 0 -> selectable as a locker location
is_forbidden = 1 -> kept as a demand grid point, not selectable as a locker location
```

Output:

```text
candidate_points.csv
```

Current `data/candidate_points.csv` contains 2717 rows: 2535 selectable rows
and 182 forbidden rows. Keeping forbidden rows in the CSV preserves the
candidate-to-distance-matrix alignment. The Java optimizer filters the locker
selection universe through `CandidateRepository.getSelectableCandidateIds()`,
while objective evaluation still uses all rows as demand grid points.

### 5.9 CSV Export Artifacts and QGIS Side Files

When exporting from QGIS, auxiliary files such as `.qmd` may appear.

These files are not required by the GA:

- They typically store metadata or QGIS-related export information.
- The Java GA consumes the CSV and the derived binary artifacts.

Runtime GA inputs are:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

### 5.10 QGIS-Side Deliverables

The data preparation workflow produced:

- 100m grid layer.
- Centroid candidate point layer.
- `pois_all_points`, the clean point-only POI layer.
- Candidate-level total POI count.
- Candidate-level category-specific POI counts:
  - ATM.
  - Bank.
  - Hospital.
  - School.
  - University.
  - Post office.
  - Transportation.
- `bus_stop_clipped`.
- Candidate-level bus stop count.
- Existing locker layer integrated into metric CRS.
- Candidate-level existing locker count.
- `forbidden_mask`.
- Grid-based `is_forbidden` computed via coverage ratio.
- Final candidate table exported as `candidate_points.csv`, with
  `is_forbidden` preserved for runtime selection filtering.

### 5.11 Raw GIS/Data Inventory in the Repository

The repository contains raw and intermediate GIS artifacts under:

```text
data/raw
```

Current raw/intermediate files include:

```text
data/raw/Kadikoy_Base.gpkg
data/raw/bitirme.qgz
data/raw/cand_buf_300m_lockercnt.gpkg
data/raw/candidate_points.csv
data/raw/candidate_points.gpkg
data/raw/candidate_points.qmd
data/raw/candidate_points_excel.qmd
data/raw/candidate_points_excel.xlsx
data/raw/grid_100m_clipped.gpkg
data/raw/grid_with_forbidden_area.gpkg
data/raw/intersect.gpkg
data/raw/kadikoy.gpkg
data/raw/kadikoy_boundary.geojson
data/raw/lockers_32635.gpkg
data/raw/pois_all_points.gpkg
```

These files are useful for reproducing or auditing the QGIS workflow. They are not all read by the Java optimizer at runtime.

The Java runtime inputs are currently:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

The UI additionally uses:

```text
parcel-locker-ui/public/mock/kadikoy_boundary.geojson
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
```

### 5.12 Status of Items That Were Originally Planned During Data Preparation

The original data-preparation plan listed several next items. Their current status is:

| Item from data-preparation plan | Current status |
| --- | --- |
| Generate `poi_score` | Implemented through `scripts/prepare_demand.py` using Entropy Weight Method |
| Integrate `poi_score` into final demand | Implemented as `demand_final = population_candidate * (1 + lambda * poi_score)` |
| Finalize SPEA2 objective 1 as accessibility | Implemented in `FitnessCalculator.evaluateF1()` |
| Finalize SPEA2 objective 2 as equity | Implemented in `FitnessCalculator.evaluateF2()` as neighborhood CV |
| UI automation using ID to lon/lat mapping | Partially implemented through `process_ga_data.py` and the Next.js dashboard |
| True generation playback | Not implemented in default Java `Main`; current UI explores final archive solutions |

## 6. GA Runtime Candidate CSV Contract

The main runtime candidate file is:

```text
data/candidate_points.csv
```

Current data status:

- Candidate rows: `2717`
- Unique neighborhoods: `21`
- Distance matrix shape: `2717 x 2717`
- Distance matrix dtype: `float32`
- Current total forbidden count: `182`
- Candidate ID range: `24` to `5964`
- Sum of `demand_final`: approximately `492289.09`

Each candidate is used in two ways:

- As a demand grid point during objective evaluation.
- As a possible locker location only when `is_forbidden = 0`.

### 6.1 Expected CSV Columns

`CsvLoader` maps fields by column name. The expected runtime CSV header is:

```text
fid,id,left,top,right,bottom,row_index,col_index,
Mahalle_Name_Turkish,Mahalle_Name_English,population_mahalle,
poi_atm,poi_bank,poi_hospital,poi_school,poi_university,
poi_post_office,poi_transport,poi_bus_stop,
lon,lat,is_forbidden,locker_count,grid_count_by_mahalle,
population_candidate,poi_score,demand_final
```

Important mapping:

| Column | Java field |
| --- | --- |
| `id` | candidate ID |
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
| `lon` | longitude |
| `lat` | latitude |
| `is_forbidden` | forbidden flag |
| `locker_count` | existing locker count near candidate |
| `grid_count_by_mahalle` | number of grid cells in the neighborhood |
| `population_candidate` | population assigned to candidate |
| `poi_score` | composite POI score |
| `demand_final` | final demand score |

If `poi_score` or `demand_final` is missing, Java falls back to `poi_score = 0`
and `demand_final = population_candidate`. That fallback is useful for
debugging, but it changes the scientific demand model and should not be treated
as equivalent to the prepared dataset.

### 6.2 Demand and POI Score Fields

The Java optimizer uses:

```text
CandidatePoint.getDemandScore()
```

This maps to:

```text
demand_final
```

The current demand preparation method is implemented in:

```text
scripts/prepare_demand.py
```

It computes:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

This means demand is population-driven but can be increased by local POI attractiveness.

## 7. POI Score and Demand Preparation in Python

### 7.1 Main Script

Main script:

```text
scripts/prepare_demand.py
```

It reads and overwrites:

```text
data/candidate_points.csv
```

The script:

1. Reads the candidate CSV.
2. Finds raw POI columns whose names start with `poi_`, excluding generated
   columns such as `poi_score` and `demand_final`.
3. Fills missing POI values with zero.
4. Applies `log1p` transformation.
5. Applies min-max normalization.
6. Computes Entropy Weight Method weights.
7. Creates or updates `poi_score`.
8. Prompts the user for a non-negative lambda value.
9. Updates `demand_final`.
10. Writes the updated CSV back to the same path.

### 7.2 Entropy Weight Method

The Entropy Weight Method gives more weight to POI categories that carry more information or variation across candidates.

The script:

- Builds normalized POI data.
- Computes proportions by column.
- Computes entropy.
- Computes divergence as `1 - entropy`.
- Normalizes divergence values into weights.

This avoids assigning arbitrary equal weights to all POI categories.

### 7.3 Lambda Interpretation

Demand formula:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

Interpretation:

- `lambda = 0.0`: POI has no influence; demand follows candidate population.
- `lambda = 0.5`: balanced POI influence.
- `lambda = 1.0`: stronger POI influence.

The prompt accepts both comma and dot decimal separators.

### 7.4 Rerun Safety

`prepare_demand.py` and `calculate_poi_weights.py` select raw POI columns using:

```text
col.startswith("poi_") and col not in {"poi_score", "demand_final"}
```

This prevents reruns on an already enriched CSV from feeding the generated
`poi_score` column back into the Entropy Weight Method.

Safer workflow:

1. Start from a clean candidate CSV.
2. Keep a backup before overwriting `data/candidate_points.csv`.
3. Confirm `poi_score` and `demand_final` after recalculation.

### 7.5 Read-Only Weight Inspection Script

Script:

```text
scripts/calculate_poi_weights.py
```

It:

- Reads `data/candidate_points.csv`.
- Selects `poi_` columns.
- Computes EWM weights.
- Prints sorted weights.
- Does not modify the CSV.

Run:

```bash
python3 scripts/calculate_poi_weights.py
```

## 8. GA Preprocessing: Distance Matrix Generation

### 8.1 Why a Distance Matrix Is Required

Even though the GA selects from existing candidate IDs and does not generate new coordinates, each solution must be evaluated using distance-based accessibility.

The optimizer needs candidate-to-candidate distances for:

- Nearest selected locker computation.
- Coverage-style reasoning.
- Possible overlap penalties.
- Dispersion analysis.
- Mean distance analysis.
- Demand-weighted accessibility.
- Neighborhood-level accessibility cost.
- Future objective or constraint extensions.

Computing distances repeatedly during GA evaluation would be expensive. Therefore, the project precomputes a full NxN distance matrix.

### 8.2 Distance Matrix Script

Script:

```text
data/prepare_ga_inputs.py
```

It:

- Reads candidate `id`, `lon`, and `lat`.
- Optionally filters `is_forbidden == 0`.
- Sorts candidates by ascending ID.
- Computes Haversine distances in meters.
- Stores the matrix as `float32`.
- Writes alignment and documentation files.

Example:

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

If forbidden filtering is used, the Java CSV must use exactly the same filtered candidate set. Otherwise repository size and matrix size will not match.

### 8.3 Generated GA Artifacts

The script produces:

```text
data/kadikoy_distance_meters_nxn.npy
data/kadikoy_candidate_ids_sorted.npy
data/kadikoy_index_map.csv
data/kadikoy_ARTIFACTS_GUIDE.md
```

Artifact meanings:

| Artifact | Meaning |
| --- | --- |
| `kadikoy_distance_meters_nxn.npy` | NxN matrix where `dist[i, j]` is the distance in meters between candidate index `i` and candidate index `j` |
| `kadikoy_candidate_ids_sorted.npy` | Candidate IDs in the same order as matrix rows and columns |
| `kadikoy_index_map.csv` | Human-readable mapping: `idx,id,lon,lat` |
| `kadikoy_ARTIFACTS_GUIDE.md` | Explanation of the artifact contract |

### 8.4 `idx` vs `id`

This distinction is critical:

- `id`: stable candidate identifier from QGIS/CSV.
- `idx`: row/column index in the NxN distance matrix.

Matrix semantics:

```text
dist[idx_i, idx_j] = meters between candidates
```

Mapping:

```text
ids[idx] -> id
index_map[idx] -> id, lon, lat
```

The GA chromosome stores candidate IDs, not matrix indexes. Java maps IDs to matrix indexes through `CandidateRepository`.

### 8.5 Repository Integration

The matrix and mapping files are present in the repository. The current matrix is approximately 28 MB and has shape:

```text
(2717, 2717)
```

The `data/kadikoy_ARTIFACTS_GUIDE.md` file also confirms:

- Candidate order is sorted by ID ascending.
- The matrix is in meters.
- Demand is not stored in the matrix artifacts; demand comes from the CSV.

## 9. Problem Formulation Used by the Java Optimizer

### 9.1 Candidate and Solution Representation

A solution is an `Individual`.

Its chromosome is:

```text
[candidate_id_1, candidate_id_2, ..., candidate_id_K]
```

The chromosome is a set-like representation. Gene order has no spatial meaning:

```text
[1, 2, 3] and [3, 2, 1] represent the same selected locker set.
```

Therefore `model.Individual` stores chromosomes in sorted canonical form. This is essential because it prevents permutation-equivalent solutions from being treated as different archive members.

### 9.2 Objective 1: Accessibility Cost

Objective 1 is minimized.

For every demand grid point:

1. Find the nearest selected locker.
2. Convert the distance from meters to kilometers.
3. Apply the distance decay exponent `beta`.
4. Weight the cost by demand.
5. Average over total system demand.

Formula:

```text
f1 = sum_i demand_i * (min_distance_km(i, selected_lockers) ^ beta) / sum_i demand_i
```

Implementation:

```text
src/main/java/service/FitnessCalculator.java
```

Current `beta`:

```text
2.0
```

Why meters are converted to kilometers:

- The matrix stores meters.
- Squaring meter values would produce very large numbers.
- Kilometer conversion keeps f1 numerically manageable while preserving the meaning of distance decay.

### 9.3 Objective 2: Neighborhood Equity

Objective 2 is minimized.

It measures inequality of service quality across neighborhoods.

Steps:

1. For each demand grid point, compute the same nearest-locker distance cost used in f1.
2. Group demand-weighted costs by Turkish neighborhood name.
3. Compute each neighborhood's demand-weighted mean accessibility cost.
4. Compute the coefficient of variation across neighborhood means.

Formula:

```text
mahalle_mean_cost_m = sum_i_in_m demand_i * cost_i / sum_i_in_m demand_i
f2 = std(mahalle_mean_cost_m values) / mean(mahalle_mean_cost_m values)
```

Why coefficient of variation is used:

- It is dimensionless.
- It is independent of the distance unit.
- It is easier to interpret than raw variance.
- It avoids squared-scale explosion.
- Lower values mean more even service quality across neighborhoods.

### 9.4 Both Objectives Are Minimized

Every dominance and Pareto-related component assumes minimization:

- Lower f1 is better.
- Lower f2 is better.

If a future objective is maximized, `Dominance`, `Pareto`, `HypervolumeIndicator`, plotting, and UI Pareto flagging must all be updated.

## 10. Java Optimization Engine

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

## 11. `config` Package

### 11.1 `GAParameters.java`

This is the centralized static parameter file.

Current values:

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

Important current behavior:

- `Main.java` can override common parameters through CLI args such as `--k`,
  `--populationSize`, `--maxGenerations`, `--mutationRate`,
  `--crossoverRate`, `--archiveSize`, and `--randomSeed`.
- HV-space normalization bounds are derived from the final archive
  non-dominated set, not from static constants in `GAParameters`.

### 11.2 `GAState.java` and `GAResult.java`

These classes currently exist as placeholders.

They are good future targets for:

- Runtime state tracking.
- Structured backend output.
- JSON result serialization.
- Generation-level export.

They are not currently used by the main pipeline.

## 12. `model` Package

### 12.1 `CandidatePoint.java`

Represents one candidate grid point.

It stores:

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

This class is a data model. It does not implement optimization logic.

### 12.2 `CandidateRepository.java`

Stores all candidates in memory and synchronizes IDs with matrix indexes.

It maintains:

- `candidateMap`: direct candidate lookup by ID.
- `idToIndexMap`: candidate ID to distance matrix index.
- `sortedCandidates`: candidates sorted by ascending ID.
- selectable candidate IDs are derived by filtering `is_forbidden = 0`.

Critical method:

```text
finalizeRepository()
```

It must be called after loading candidates and before fitness evaluation.

What it does:

- Sorts all candidates by ascending ID.
- Builds the ID-to-index mapping.
- Ensures Java candidate order matches the Python-generated distance matrix order.

Forbidden rows are deliberately kept in `sortedCandidates`; they are demand grid
points and must remain aligned with the distance matrix. They are excluded only
from the locker selection universe.

### 12.3 `Individual.java`

Represents one GA solution.

It stores:

- Canonical sorted chromosome.
- Raw objective values.
- Normalized objective values.
- SPEA2 strength.
- SPEA2 raw fitness.
- SPEA2 density.
- SPEA2 total fitness.

The chromosome is sorted in the constructor and setter. This behavior should be preserved unless the entire archive and duplicate-handling logic is redesigned.

## 13. `io` Package

### 13.1 `CsvLoader.java`

Loads `data/candidate_points.csv` into a `CandidateRepository`.

Important details:

- Reads and indexes the header row.
- Ignores empty lines.
- Uses simple comma splitting with empty trailing-field preservation.
- Maps fields by header names.
- Falls back to population-only demand if `poi_score` or `demand_final` is absent.

Risk:

`line.split(",")` is not a production-grade CSV parser. It works for the current data because fields do not contain embedded commas. If future CSV fields contain commas, the loader can break.

Recommended future improvement:

- Use a real CSV parser such as OpenCSV.
- Or implement robust quoted-field parsing.
- Add schema validation that fails early when scientific demand columns are missing.

### 13.2 `DistanceMatrixLoader.java`

Loads a NumPy `.npy` file using:

```text
org.jetbrains.bio:npy
```

It expects:

- A 2D matrix.
- A square matrix.
- Data payload as `float[]` or `double[]`.

It returns:

```text
double[][]
```

`Main` then validates that matrix row and column counts match the repository size.

## 14. `service` Package

### 14.1 `FitnessCalculator.java`

This is where the problem-specific objective functions live.

Responsibilities:

- Validate individuals.
- Compute total system demand.
- Compute nearest-locker distance cost.
- Evaluate f1.
- Evaluate f2.
- Evaluate a full population's raw objectives.

Distance cost:

```text
cost = (nearest_distance_meters / 1000.0) ^ beta
```

Computational complexity:

```text
O(number_of_candidates * K)
```

per individual evaluation.

With the current values:

- Number of candidates: `2717`.
- Selectable locker candidates: `2535`.
- K: `5`.

This is feasible for the current project size.

### 14.2 `PopulationInitializer.java`

Creates the initial population.

For each individual:

1. Copy all selectable candidate IDs.
2. Shuffle them.
3. Take the first `K` IDs.
4. Create an `Individual`.

Current behavior:

- The default initializer uses an unseeded random generator.
- `Main` and `ParameterAnalyzer` can use `PopulationInitializer(long seed)` for
  deterministic runs when a seed is supplied.

### 14.3 `ObjectiveNormalizer.java`

Normalizes objective values.

It supports:

1. Dynamic normalization from the current population/list.
2. Fixed-bound normalization using externally supplied min/max values.

Dynamic normalization is used inside `Evaluate` for density calculation.

Fixed-bound normalization is used in `Main` after the run to export archive
snapshots in the final archive non-dominated objective space.

Formula:

```text
norm = (value - min) / (max - min)
```

The output is clamped to:

```text
[0, 1]
```

### 14.4 `HypervolumeIndicator.java`

Computes the 2D hypervolume in normalized objective space.

Assumptions:

- Bi-objective minimization.
- Normalized objectives have already been assigned.
- Reference point is outside the normalized range.

Current reference point:

```text
(1.1, 1.1)
```

Procedure:

1. Extract non-dominated individuals.
2. Deduplicate by chromosome.
3. Sort by normalized f1.
4. Accumulate dominated rectangles to the reference point.

If a point is worse than the reference point, the method throws an error.

## 15. `algorithm.helper` Package

### 15.1 `Dominance.java`

Checks Pareto dominance under bi-objective minimization.

`a` dominates `b` if:

```text
a.f1 <= b.f1
a.f2 <= b.f2
and at least one of those comparisons is strict
```

### 15.2 `Pareto.java`

Extracts the non-dominated subset from a list of individuals.

Used by:

- `Survivor`
- `HypervolumeIndicator`
- `Main`
- `ParameterAnalyzer`
- Some plotting/UI conversion logic conceptually mirrors this behavior.

### 15.3 `Truncation.java`

Reduces an oversized archive while preserving diversity.

Method:

- Compute sorted neighbor-distance lists in normalized objective space.
- Compare lists lexicographically.
- Remove the individual in the most crowded region.
- Repeat until archive size equals target size.

This follows the SPEA2 truncation idea.

## 16. `algorithm` Package

### 16.1 `Evaluate.java`

Runs the SPEA2 evaluation pipeline.

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

The current neighbor index:

```text
k = floor(sqrt(merged_size))
```

### 16.2 `Survivor.java`

Builds the next SPEA2 archive.

Procedure:

1. Extract non-dominated individuals.
2. Deduplicate by canonical chromosome.
3. If the non-dominated set equals archive size, return it.
4. If it is smaller than archive size, fill with best dominated individuals by total fitness.
5. If it is larger than archive size, truncate it.

This class manages elitist memory.

### 16.3 `Selection.java`

Performs binary tournament parent selection from the current archive.

Comparison priority:

1. Smaller `totalFitness`.
2. If tied, smaller `rawFitness`.
3. If tied, smaller `density`.
4. If still tied, choose the first individual.

The archive cannot be empty.

### 16.4 `Variation.java`

Generates offspring from the mating pool.

Main operations:

- Crossover.
- Mutation.
- Repair.

#### Crossover

The implementation uses shared-gene priority recombination:

1. Genes present in both parents are collected as shared genes.
2. Shared genes are inserted into both children.
3. Parent-exclusive genes are pooled.
4. The exclusive pool is shuffled.
5. Remaining child slots are filled from the exclusive pool.
6. Repair is applied.

This is exploitation-oriented because it preserves genes already shared by good parents. It can also lead to premature convergence if mutation is too low.

#### Mutation

Mutation:

- Selects one random gene.
- Replaces it with a candidate ID not already in the chromosome.

#### Repair

Repair:

- Removes duplicates.
- Fills missing slots with unused candidate IDs.
- Trims extra genes.
- Ensures the chromosome length is exactly `K`.

## 17. `app.Main`: Main Optimization Workflow

Default entry point:

```text
src/main/java/app/Main.java
```

Run:

```bash
mvn -q compile exec:java
```

Actual workflow:

1. Create the `output` directory.
2. Load `data/candidate_points.csv`.
3. Finalize the repository.
4. Load `data/kadikoy_distance_meters_nxn.npy`.
5. Validate matrix dimensions against repository size.
6. Read parameters from `GAParameters`.
7. Apply optional CLI argument overrides.
8. Build the selectable locker universe from `is_forbidden = 0` rows.
9. Initialize population from selectable candidate IDs.
10. Create an empty archive.
11. Build all algorithm/service dependencies.
12. Evaluate generation 0.
13. Build generation 0 archive using `Survivor`.
14. Deep-copy the initial archive snapshot.
15. Run the evolutionary loop for `MAX_GENERATIONS`.
16. Each generation:
    - Select mating pool from archive.
    - Generate offspring through variation.
    - Evaluate offspring plus archive.
    - Build next archive.
    - Print compact progress for the UI stream.
17. Deep-copy the final archive snapshot.
18. Extract the final archive non-dominated set.
19. Compute ideal/nadir f1/f2 bounds from the final ND set.
20. Normalize initial and final archive snapshots using those final-ND bounds.
21. Write `output/initial_archive.csv`.
22. Write `output/final_archive.csv`.
23. Compute final archive hypervolume and hypervolume ratio.
24. Compute raw-objective improvement metrics and C-metric.
25. Print hypervolume, ND counts, CSV paths, and runtime.

## 18. Archive CSV Format

`Main` writes:

```text
output/initial_archive.csv
output/final_archive.csv
```

Columns:

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
| `norm_f1` | Assessment-normalized f1 |
| `norm_f2` | Assessment-normalized f2 |
| `strength` | SPEA2 strength |
| `raw_fitness` | SPEA2 raw fitness |
| `density` | SPEA2 density |
| `total_fitness` | `raw_fitness + density` |

Example `final_archive.csv` status from a previous validated run:

- Rows: `50`
- f1 range: approximately `0.5365` to `0.6003`
- f2 range: approximately `0.2085` to `0.3690`
- normalized f1 range: approximately `0.0455` to `1.0`
- normalized f2 range: approximately `0.0455` to `0.9545`

Regenerate the optimizer output before using exact ranges in a report.

## 19. Hypervolume and Assessment Logic

Hypervolume is used to summarize the quality of a Pareto archive. It captures both:

- Proximity to better objective values.
- Spread across the objective front.

The project computes hypervolume in normalized objective space, not raw objective space.

Reason:

- f1 and f2 have different meanings and scales.
- f1 is distance-cost based.
- f2 is a coefficient of variation.
- Raw multiplication of objective ranges would make interpretation unstable.

Correct assessment rule:

```text
Final archive HV uses bounds derived from the final archive non-dominated set.
Initial-to-final improvement uses raw-objective ND metrics and C-metric.
```

If each archive or each generation is normalized separately, hypervolume
comparisons become mathematically misleading. The current project therefore
does not use initial-vs-final HV as the official improvement metric.

Current `Main` behavior:

- Build ideal/nadir bounds from the final archive non-dominated set.
- Normalize both exported archive snapshots with those final-ND bounds.
- Compute final archive hypervolume with reference point `(1.1, 1.1)`.
- Compute initial-to-final improvement separately in raw objective space.

Hypervolume ratio:

```text
ratio = hypervolume / (reference_f1 * reference_f2)
```

With the current reference:

```text
reference area = 1.1 * 1.1 = 1.21
```

Interpretation warning:

- A high HV ratio does not automatically prove that the solution is scientifically ideal.
- HV depends strongly on normalization bounds and front shape.
- Always inspect raw objective plots, non-dominated count, best f1, best f2, and solution geography.

## 20. `ParameterAnalyzer`

File:

```text
src/main/java/app/ParameterAnalyzer.java
```

Run:

```bash
mvn -q compile exec:java -Panalyze
```

Output:

```text
output/parameter_analysis_results.csv
```

Purpose:

- Perform a full-factorial parameter grid search.
- Compare configurations under a constant evaluation budget.
- Investigate premature convergence and hypervolume sensitivity.

Grid:

```text
K_VALUES = {3, 6, 10}
LAMBDA_VALUES = {0.4, 0.5, 0.6}
MUTATION_RATES = {0.05, 0.10, 0.20, 0.30, 0.40}
CROSSOVER_RATES = {0.7, 0.9}
POPULATION_SIZES = {50, 100, 200}
SEEDS = {42, 123, 7}
```

Archive size:

```text
archiveSize = populationSize / 2
```

Evaluation budget:

```text
K=3  -> TARGET_FE = 30000
K=6  -> TARGET_FE = 50000
K=10 -> TARGET_FE = 80000
```

Generation formula:

```text
maxGenerations = (TARGET_FE / populationSize) - 1
```

CSV columns:

```text
K,Lambda,PopSize,ArchiveSize,MaxGen,MutRate,CrossRate,
FunctionEvals,Runtime_ms,ND_Count,Best_f1,Best_f2,
Mean_f1,Mean_f2,Final_HV
```

Current reproducibility behavior:

- `PopulationInitializer`, `Selection`, and `Variation` are all seeded inside
  analyzer runs.
- Calibration bounds are locked per `(K, Lambda)` group using a calibration
  phase before the grid-search runs.

## 21. Python Utility Scripts

### 21.1 `scripts/prepare_demand.py`

Updates `poi_score` and `demand_final`.

Run:

```bash
python3 scripts/prepare_demand.py
```

Warning:

It overwrites `data/candidate_points.csv`.

### 21.2 `scripts/calculate_poi_weights.py`

Read-only POI weight inspection script.

Run:

```bash
python3 scripts/calculate_poi_weights.py
```

### 21.3 `scripts/plot_archives.py`

Reads:

```text
output/initial_archive.csv
output/final_archive.csv
```

Writes:

```text
output/archive_comparison_latest.png
```

It plots four panels:

- Initial archive in raw objective space.
- Final archive in raw objective space.
- Initial-to-final improvement metrics.
- Final archive in hypervolume space.

It also prints:

- Archive sizes.
- Pearson correlation between f1 and f2.
- Spearman correlation between f1 and f2.
- Non-dominated count in raw space.
- Non-dominated count in normalized HV space.
- Best f1.
- Best f2.

### 21.4 `data/prepare_ga_inputs.py`

Generates the distance matrix and alignment artifacts. See Section 8.

## 22. Web UI

UI directory:

```text
parcel-locker-ui
```

Stack:

- Next.js 16.
- React 19.
- TypeScript.
- Tailwind CSS 4.
- React Leaflet.
- Recharts.
- `lucide-react` is installed, although not all controls currently use it.

Run:

```bash
cd parcel-locker-ui
npm install
npm run dev
```

### 22.1 UI Data Files

The UI reads:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/kadikoy_boundary.geojson
parcel-locker-ui/public/mock/ga-results.json
parcel-locker-ui/public/mock/archive_comparison_latest.png
```

Current data:

- `candidate-points.json` contains `2717` candidates.
- `ga-results.json` and `archive_comparison_latest.png` are generated after a
  Java run and are tolerated as missing by the UI before the first local run.

### 22.2 `src/app/page.tsx`

The main dashboard page:

- Loads candidate JSON.
- Loads Kadikoy boundary GeoJSON.
- Loads GA archive result JSON.
- Displays archive solutions one by one.
- Displays selected solution lockers on a map.
- Displays selected locker details.
- Displays an f1/f2 scatter chart using Recharts.
- Draws Pareto points and best f1/best f2 markers.
- Displays the static archive comparison plot.
- Calls `/api/run-ga` when the user clicks Run Optimization.

Important terminology note:

Some UI variables and props still use the word "generation". In the current real-data flow, the UI is mainly browsing final archive solutions, not true generation-by-generation optimizer history.

So the current UI should be understood as:

```text
Archive solution explorer
```

not:

```text
True GA generation playback
```

### 22.3 `src/app/api/run-ga/route.ts`

This is a local/development integration endpoint.

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

1. Builds Maven `-Dexec.args` from the request body.
2. Runs `mvn compile exec:java` in the project root.
3. Streams Java progress lines back to the UI.
4. Runs `scripts/plot_archives.py`.
5. Copies `output/archive_comparison_latest.png` into the UI public mock folder.
6. Runs `parcel-locker-ui/src/scripts/process_ga_data.py`.
7. Streams completion or error status.

Important warning:

This is not a production backend design.

Why:

- It runs shell commands from a web route.
- It passes supported runtime parameters to Java through Maven `-Dexec.args`.
- It is not concurrency-safe.
- It can dirty the Git working tree.
- It does not isolate run outputs.

Future backend should use validated runtime configuration and run-specific output directories.

### 22.4 Dashboard Components

#### `control-panel.tsx`

Left-side control panel.

Controls:

- Locker count `K`.
- Run Optimization.
- Current solution slider.
- Previous/next solution.
- Auto-play.
- Playback speed.
- Population size.
- Max generations.
- Mutation rate.

Current advanced controls:

- Population size.
- Max generations.
- Mutation rate.
- Crossover rate.
- Archive size.
- Optional random seed.

#### `locker-map.tsx`

React Leaflet map.

Layers:

- OpenStreetMap tiles.
- Kadikoy boundary.
- Candidate points as small gray markers.
- Active lockers as larger markers.
- Selected locker marker.

Map center:

```text
[40.9833, 29.0667]
```

#### `locker-detail-panel.tsx`

Shows selected locker and solution metrics:

- Neighborhood.
- Archive index.
- Latitude.
- Longitude.
- Accessibility f1.
- Equity f2.
- Total fitness.

#### `locker-strip.tsx`

Top horizontal strip of lockers for the current archive solution. Clicking a locker changes the active selection.

### 22.5 UI Data Processing Scripts

#### `src/scripts/process_ga_data.py`

Main conversion script for real GA output.

Inputs:

```text
data/candidate_points.csv
output/final_archive.csv
```

Outputs:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
```

It:

- Converts candidate CSV to JSON.
- Maps archive chromosomes to candidate coordinates.
- Transfers f1, f2, total fitness, normalized f1, and normalized f2.
- Recomputes Pareto flags under minimization.
- Marks best f1 and best f2 solutions among Pareto solutions.

#### `src/scripts/build_candidate_json.py`

Older or alternate candidate JSON builder.

It reads:

```text
parcel-locker-ui/public/mock/candidate_points.csv
```

It checks some older field names such as:

- `name`
- `neighborhood`
- `MAH_JOIN`
- `pop_2024`

For the current real-output flow, `process_ga_data.py` is more relevant.

## 23. Output Files

Files produced by the default Java/plotting flow, plus older tracked analysis
artifacts, include:

```text
output/initial_archive.csv
output/final_archive.csv
output/archive_comparison_latest.png
output/archive_comparison.png
output/parameter_analysis_results.csv
output/objective_space_nd_points.csv
output/objective_space_run_summary.csv
```

Meanings:

- `initial_archive.csv`: archive snapshot after generation 0.
- `final_archive.csv`: archive snapshot after the final generation.
- `archive_comparison_latest.png`: initial vs final archive plot summary.
- `parameter_analysis_results.csv`: hyperparameter grid-search output.
- `objective_space_*`: older/experimental objective-space calibration outputs from the backup Main workflow.

## 24. Current Backend Integration Contract

There is no production backend service yet. The current project should be understood as a batch optimizer plus a local development UI integration.

### 24.1 Current File-Based Contract

Input side:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
src/main/java/config/GAParameters.java
```

Output side:

```text
output/initial_archive.csv
output/final_archive.csv
output/archive_comparison_latest.png
```

UI conversion side:

```text
parcel-locker-ui/src/scripts/process_ga_data.py
```

Converted UI outputs:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
parcel-locker-ui/public/mock/archive_comparison_latest.png
```

The current local `/api/run-ga` route automates these steps by passing runtime
arguments to Maven and spawning Maven/Python processes. That is acceptable for
local experiments only.

### 24.2 Recommended First Backend Endpoints

A future backend can start with a file-based batch contract before redesigning the optimizer.

Recommended minimal endpoints:

```text
POST /runs
GET /runs/latest/initial-archive
GET /runs/latest/final-archive
GET /runs/latest/final-pareto-front
GET /runs/latest/summary
```

Recommended `POST /runs` request fields:

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

In the first backend milestone, the backend can still run the Java batch optimizer and parse its CSV outputs. In a later milestone, Java should expose runtime configuration without source-file edits.

### 24.3 Current Backend Scope Exclusions

At the current stage, the backend layer should avoid the following responsibilities:

- Reimplement SPEA2 outside Java.
- Duplicate objective formulas in another language.
- Recompute normalization independently unless Java exports enough metadata.
- Infer real generation playback from only initial/final archives.
- Run concurrent jobs against the same output files without run-specific directories.

The Java layer should remain the authoritative implementation of the optimization logic.

## 25. Backup Experimental Main

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

It can be useful as a reference for future generation-level exports.

## 26. Maven, Build, and Tests

Java version:

```text
17
```

Main Java dependency:

```xml
<dependency>
    <groupId>org.jetbrains.bio</groupId>
    <artifactId>npy</artifactId>
    <version>0.3.5</version>
</dependency>
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
- `src/test` does not contain real test source files.
- `target/test-classes` exists only as a build artifact.

## 27. End-to-End Workflow

Recommended full workflow from data to UI:

1. Prepare or verify the QGIS candidate table.
2. Ensure all metric GIS operations used EPSG:32635.
3. Ensure candidate output includes EPSG:4326 `lon` and `lat`.
4. Export feasible candidates as `data/candidate_points.csv`.
5. Inspect POI weights:

```bash
python3 scripts/calculate_poi_weights.py
```

6. Generate or update `poi_score` and `demand_final`:

```bash
python3 scripts/prepare_demand.py
```

7. If candidate coordinates or candidate set changed, regenerate distance artifacts:

```bash
python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy
```

8. Compile Java:

```bash
mvn -q compile
```

9. Run the optimizer:

```bash
mvn -q compile exec:java
```

10. Generate plots:

```bash
python3 scripts/plot_archives.py
```

11. Generate UI JSON from GA output:

```bash
cd parcel-locker-ui
python3 src/scripts/process_ga_data.py
```

12. Run the UI:

```bash
npm run dev
```

## 28. Recommended Source Review Order

For report writing, project auditing, or continued development, the most useful file review order is:

1. `General_GUIDE.md`
2. `readme.md`
3. `src/main/java/app/Main.java`
4. `src/main/java/service/FitnessCalculator.java`
5. `src/main/java/algorithm/Evaluate.java`
6. `src/main/java/algorithm/Survivor.java`
7. `src/main/java/algorithm/Variation.java`
8. `src/main/java/config/GAParameters.java`
9. `scripts/prepare_demand.py`
10. `data/prepare_ga_inputs.py`
11. `scripts/plot_archives.py`
12. `parcel-locker-ui/src/app/api/run-ga/route.ts`
13. `parcel-locker-ui/src/scripts/process_ga_data.py`
14. `parcel-locker-ui/src/app/page.tsx`

## 29. Reproducibility-Critical Technical Contracts

### 29.1 Candidate ID and Matrix Index Contract

The most important contract:

```text
Java sorted candidate order == distance matrix row/column order
```

Current mechanism:

- Python matrix generation sorts by candidate ID ascending.
- Java repository finalization sorts by candidate ID ascending.

If candidate CSV changes:

- Regenerate the distance matrix.
- Regenerate candidate ID alignment files.
- Ensure candidate IDs are unique.
- Ensure matrix size equals repository size.

### 29.2 Chromosome Set Semantics

Chromosomes represent unordered selected candidate sets.

Therefore:

- `Individual` canonical sorting must be preserved.
- Archive deduplication by chromosome must be preserved.
- Variation repair must ensure unique genes and fixed length.

### 29.3 Both Objectives Are Minimization Objectives

All dominance logic assumes minimization.

If objective direction changes, update:

- `Dominance`
- `Pareto`
- `HypervolumeIndicator`
- `scripts/plot_archives.py`
- `parcel-locker-ui/src/scripts/process_ga_data.py`
- UI labeling and interpretation

### 29.4 Final-ND Assessment Normalization

Final archive hypervolume uses normalization bounds derived from the final
archive non-dominated set.

Hypervolume values from separately normalized archives should not be compared
directly. Initial-to-final improvement should be read from raw-objective
improvement metrics and C-metric.

### 29.5 CSV Column Names and Format

`CsvLoader` maps fields by header name, so the column order is flexible. The
required column names and simple CSV format are still part of the contract:
current parsing uses comma splitting and does not support quoted fields that
contain embedded commas.

## 30. Additions Integrated in This Report-Oriented Version

The earlier project guide was technically useful but incomplete for formal report writing. The following additional details have now been integrated:

- Full QGIS/OSM CSV preparation methodology.
- CRS policy and EPSG:32635 vs EPSG:4326 rationale.
- Point-only POI cleaning decision.
- 300m buffer rationale and counting workflow.
- POI category extraction and joining workflow.
- Public bus stop QuickOSM workflow and clipping.
- Existing locker layer integration.
- Forbidden mask and grid-level coverage ratio logic.
- `.qmd` export artifact explanation.
- `idx` vs `id` explanation for matrix artifacts.
- Clarification that current UI explores final archive solutions, not true generation history.
- Clarification that `Main` uses final-ND-based post-hoc assessment bounds.
- Clarification that `/api/run-ga` is a local/dev process-spawning bridge that passes CLI args to Java.

The implementation state documented here is based on the repository as inspected.

## 31. Limitations and Technical Debt

### 31.1 No Automated Tests

There is no real automated test suite.

Recommended first tests:

- `Dominance` minimization cases.
- `Pareto` non-dominated extraction.
- `Individual` canonical chromosome sorting.
- `Variation` chromosome length and uniqueness.
- `ObjectiveNormalizer` clamp and degenerate bounds.
- Small synthetic distance matrix tests for f1 and f2.

### 31.2 Fragile CSV Parsing

`CsvLoader` uses simple comma splitting. This is fragile if future CSV fields contain commas.

Recommended improvement:

- Use a real CSV parser.
- Keep header-name mapping while replacing the low-level line splitter.

### 31.3 POI Column Selection in Demand Script

`prepare_demand.py` and `calculate_poi_weights.py` now exclude generated
columns (`poi_score`, `demand_final`) when selecting raw POI columns.

Recommended improvement:

- Add an explicit raw POI column allow-list if new POI-derived columns are added.

### 31.4 Forbidden Candidate Handling

The current candidate CSV includes both feasible and forbidden rows:

```text
is_forbidden = 0 -> 2535 rows
is_forbidden = 1 -> 182 rows
```

Implemented behavior:

- forbidden cells remain demand points
- forbidden cells cannot be selected as locker locations
- CSV and matrix row sets stay synchronized

### 31.5 UI API Route Spawns Local Processes

The local API route spawns Maven and Python processes from the Next.js server.

Recommended improvement:

- Introduce runtime configuration.
- Add CLI arguments or JSON config input for Java.
- Create run-specific output folders.

### 31.6 No True Generation-Level Export

Current default `Main` exports only initial and final archive snapshots.

For true generation playback, Java should export:

- `generation_summary.csv`
- `generation_archive_members.csv`
- `generation_best_front.csv`
- or a structured JSON equivalent

### 31.7 ParameterAnalyzer Is Long-Running

`ParameterAnalyzer` seeds `PopulationInitializer`, `Selection`, and `Variation`
for each run, so repeated seeded configurations are deterministic. The main
operational limitation is that the full grid search is long-running and writes a
single `output/parameter_analysis_results.csv` file.

Recommended improvement:

- Add resume/checkpoint support for interrupted grid searches.
- Write run-specific or timestamped analysis outputs when preserving multiple
  experiments matters.

### 31.8 Haversine Distance Is Not Network Distance

The current matrix uses Haversine straight-line distance.

This should be stated clearly in reports. A future realism improvement would use walking or road-network distance.

### 31.9 Hypervolume Interpretation Is Sensitive

Hypervolume depends on normalization bounds and reference point choice.

It should be interpreted together with:

- Raw Pareto plot.
- Non-dominated count.
- Best f1.
- Best f2.
- Spatial distribution of selected lockers.

## 32. Implemented Code-Level Design Decisions

The current project state includes several important code-side design decisions and improvements. These are relevant for the implementation chapter of the report:

- `GAParameters` centralizes core GA constants.
- `Individual` canonicalizes chromosomes by sorting them.
- f1 converts matrix distances from meters to kilometers before applying `beta`.
- f2 uses coefficient of variation rather than raw variance.
- `Survivor` deduplicates archive candidates by chromosome.
- `Variation` uses shared-gene priority crossover plus mutation and repair.
- `Main` exports both initial and final archive snapshots.
- `Main` normalizes archive exports using bounds derived from the final archive non-dominated set.
- `HypervolumeIndicator` computes 2D normalized-space hypervolume.
- `ParameterAnalyzer` performs seeded constant-evaluation-budget grid search.
- The UI `/api/run-ga` route can trigger a local Java run and refresh UI assets.
- `process_ga_data.py` converts final archive CSV rows into map-ready UI JSON.

## 33. Future Work

### 33.1 Short-Term Hardening

1. Add automated tests.
2. Add schema validation for `candidate_points.csv`.
3. Replace `CsvLoader` with robust quoted-field CSV parsing.
4. Add an explicit POI column allow-list if the feature set grows.
5. Add performance tests for fitness evaluation.

### 33.2 Backend Readiness

1. Move orchestration from `Main` into a reusable `GARunner` or `OptimizerService`.
2. Add production-grade runtime config validation.
3. Populate `GAState` and `GAResult`.
4. Add run-specific output folders.
5. Produce structured JSON output.
6. Add job isolation and concurrency control.

### 33.3 True UI Generation Playback

1. Export per-generation archive snapshots from Java.
2. Distinguish archive solutions from generation snapshots in UI schema.
3. Add real generation slider data.
4. Animate map evolution from real optimizer states.

### 33.4 Scientific and Methodological Improvements

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
5. Add additional quality indicators:
   - Spacing.
   - Spread.
   - Epsilon indicator.
   - Archive uniqueness.

## 34. Implementation Traceability Matrix

| Desired change | Start here |
| --- | --- |
| Change f1 or f2 | `src/main/java/service/FitnessCalculator.java` |
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
| Change demand model | `scripts/prepare_demand.py` |
| Change matrix generation | `data/prepare_ga_inputs.py` |
| Change archive plot | `scripts/plot_archives.py` |
| Change UI JSON conversion | `parcel-locker-ui/src/scripts/process_ga_data.py` |
| Change UI local GA trigger | `parcel-locker-ui/src/app/api/run-ga/route.ts` |
| Change dashboard layout | `parcel-locker-ui/src/app/page.tsx` and `src/components/dashboard/*` |

## 35. How to Interpret Outputs

After a run:

1. Check that `final_archive.csv` row count matches archive size.
2. Check that each chromosome has exactly `K` IDs.
3. Check that f1 and f2 ranges are plausible.
4. Check non-dominated count.
5. Inspect the raw objective plot.
6. Compare initial and final archive spread.
7. Check final hypervolume ratio and raw-objective improvement metrics.
8. Inspect selected locker geography in the UI.

For decision-making, a solution should not be selected only because it has the best f1. The best f1 solution may be unfair across neighborhoods. Similarly, a solution should not be selected only because it has the best f2, because the best f2 solution may have poor accessibility. The Pareto archive exists to expose this trade-off and support informed selection among competing alternatives.

## 36. Reproducibility and Data Integrity Notes

The following notes are important for reproducibility and safe continuation of the project:

- Data files should not be overwritten unless the workflow explicitly requires it.
- Remember that `scripts/prepare_demand.py` overwrites `data/candidate_points.csv`.
- Remember that `/api/run-ga` spawns Maven and Python processes from the local
  development server.
- Treat `output` files as generated artifacts, but also as useful example outputs.
- `target` should not be edited because it is Maven build output.
- Raw GIS files under `data/raw` are data preparation sources, not Java runtime inputs.
- Candidate CSV and distance matrix files should not be changed independently.
- Preserve candidate ID and matrix index alignment.
- Preserve chromosome set semantics unless redesigning the algorithm.

## 37. Current Technical Status

Working:

- Candidate CSV loading.
- Distance matrix loading.
- Initial population generation.
- f1 and f2 evaluation.
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

## 38. Final Report Summary

This project is a multi-objective SPEA2 optimization system for selecting parcel locker locations in Kadikoy. It uses 2717 candidate grid centroids derived from a QGIS/OSM workflow; 2535 are selectable locker candidates and 182 are forbidden rows kept as demand grid points. Each candidate has spatial, neighborhood, POI, bus stop, existing locker, population, and demand attributes. The Java optimizer selects `K` non-forbidden candidate IDs and evaluates them with two minimization objectives: demand-weighted accessibility and neighborhood equity.

The Java code is the authoritative implementation of the optimization methodology. Python scripts prepare demand values, generate matrix artifacts, and plot archive outputs. The Next.js UI visualizes final archive solutions on a map and can locally trigger the Java optimizer, but that trigger is a development shortcut rather than a production backend.

The first contract to protect is candidate ID to matrix index alignment. The second contract is chromosome set semantics. The third contract is selectable-vs-demand handling for forbidden candidates. The fourth contract is final-ND-based normalization for final archive hypervolume assessment.

The next most valuable engineering improvements are tests, production-grade runtime configuration, schema validation, robust CSV parsing, performance improvements in fitness evaluation, and generation-level exports for the UI.
