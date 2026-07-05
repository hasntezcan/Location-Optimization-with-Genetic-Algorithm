# V1 Data Contract

## Purpose

This document defines the data contract for the V1 generic grid-based location optimization platform.

The goal is to separate:

```text id="lzl4g8"
base spatial data
scenario decision state
objective input features
optimizer runtime inputs
benchmark/reporting outputs
```

The current Kadikoy parcel locker dataset remains the V0 runtime implementation, but V1 should move toward a generic, layered, scenario-aware data model.

## Core Principle

The base grid describes the city.

The scenario describes the planning decision.

The optimizer selects candidate IDs.

The benchmark explains the scenario outcome.

Do not mix these responsibilities into one uncontrolled wide CSV.

## Main Data Concepts

### Grid / Candidate

A grid or candidate is the stable spatial unit used by the optimizer.

It can represent:

* a grid cell,
* a centroid,
* a parcel,
* an address,
* a road/network node,
* or another selectable spatial unit.

Every candidate must have a stable candidate ID.

Candidate IDs connect:

```text id="izjrie"
candidate feature table
distance matrix
scenario facility snapping
optimizer chromosomes
benchmark reports
UI rendering
```

### Facility

A facility is an existing, proposed, imported, or manually added service location.

Facilities should live in scenario data, not as hidden assumptions inside the base grid.

Examples:

* parcel locker,
* grocery store,
* fire station,
* police station,
* clinic,
* pharmacy,
* logistics node,
* municipal service point.

### Scenario

A scenario is an editable planning context over a stable grid.

It contains:

* existing facilities,
* proposed facilities,
* manually added facilities,
* disabled facilities,
* locked candidates,
* disabled candidates,
* objective bundle,
* run settings,
* benchmark assumptions.

The same base grid can support many scenarios.

### Layer

A layer is a source of spatial or tabular information that can enrich the candidate grid.

Examples:

* population,
* POIs,
* transit,
* traffic,
* crime/risk,
* costs,
* restrictions,
* existing service context,
* business demand proxy.

### Objective Feature

An objective feature is a candidate/grid attribute required by an objective.

Examples:

* `demand_score`,
* `population`,
* `risk_score`,
* `cost_score`,
* `travel_time`,
* `is_forbidden`.

Objectives must declare which fields they require.

## V0 Runtime Data

The current active V0 runtime inputs are:

```text id="wog1o2"
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

Supporting alignment artifacts:

```text id="uw7ao3"
data/kadikoy_candidate_ids_sorted.npy
data/kadikoy_index_map.csv
data/kadikoy_ARTIFACTS_GUIDE.md
```

These files are specific to the Kadikoy parcel locker implementation.

V1 work must preserve the current V0 runtime behavior unless a task explicitly asks for migration.

## Current `candidate_points.csv` Role

`data/candidate_points.csv` is the current V0 runtime candidate source.

It contains:

* candidate IDs,
* grid/cell bounds,
* coordinates,
* neighborhood names,
* POI counts,
* bus stop count,
* forbidden/selectable status,
* population,
* demand score,
* V0 locker-related context fields.

For V1, treat this file as:

```text id="i0mox2"
the current Kadikoy grid implementation
```

not:

```text id="jmbpu4"
the final generic platform schema
```

Do not mutate it casually.

Any migration must preserve or explicitly rebuild the candidate ID and distance matrix alignment contract.

## Future `grid_features.csv` Direction

V1 may introduce a more generic runtime feature table such as:

```text id="a2zvmw"
data/features/grid_features.csv
```

or an equivalent database-backed table.

A future generic feature table should contain:

* stable candidate IDs,
* geometry or coordinate references,
* selectability/restriction fields,
* generic objective feature columns,
* source/version metadata,
* use-case-neutral column names where possible.

Example conceptual fields:

```text id="4j2j62"
candidate_id
lat
lon
x
y
display_crs
metric_crs
zone_name
is_selectable
is_forbidden
population
demand_score
risk_score
cost_score
poi_score
transit_access_score
```

The exact schema should be finalized through a migration plan.

Until then:

```text id="xpclys"
data/candidate_points.csv remains the active V0 runtime source.
```

## Minimum Candidate Fields

A candidate record must include:

| Field                             | Requirement                                   |
| --------------------------------- | --------------------------------------------- |
| stable ID                         | Required                                      |
| coordinate or geometry reference  | Required                                      |
| selectability or forbidden status | Required                                      |
| objective input fields            | Required depending on active objective bundle |
| display coordinates               | Required for UI map rendering                 |
| matrix alignment                  | Required for optimizer distance lookup        |

Recommended generic fields:

```text id="dudmwd"
candidate_id
lat
lon
x_metric
y_metric
display_crs
metric_crs
zone_name
is_forbidden
is_selectable
```

V0 may still use:

```text id="1mlkpc"
id
lon
lat
is_forbidden
Mahalle_Name_Turkish
Mahalle_Name_English
```

## Candidate ID Contract

Candidate IDs are the most important data contract.

Rules:

* Candidate IDs must be stable.
* Candidate IDs must be unique.
* Candidate IDs must not be reused for different locations.
* Optimizer chromosomes should store candidate IDs, not row offsets.
* UI selections should resolve through candidate IDs.
* Scenario facility snapping should produce candidate IDs.
* Benchmark outputs should reference candidate IDs when listing selected facilities.

Do not treat CSV row number as a stable ID.

## Distance Matrix Alignment Contract

The distance matrix row/column order must align to candidate IDs.

Current V0 contract:

```text id="455lh7"
distance matrix rows/columns = candidate IDs sorted ascending
```

Current runtime matrix:

```text id="04zm0o"
data/kadikoy_distance_meters_nxn.npy
```

Current supporting ordered ID artifact:

```text id="oq4lvs"
data/kadikoy_candidate_ids_sorted.npy
```

Rules:

* Do not reorder candidates without rebuilding matrix artifacts.
* Do not filter candidates without rebuilding matrix artifacts and runtime loaders.
* Do not use `--filter_forbidden` unless the runtime CSV is filtered in exactly the same way.
* Do not produce scenario candidate IDs that are absent from the candidate universe.
* Do not use matrix index as an external API value.

Breaking this contract invalidates objective values and map outputs.

## Coordinate and CRS Contract

V1 must handle coordinates explicitly.

### Display CRS

For map rendering, use:

```text id="c3fnlt"
EPSG:4326
```

Typical fields:

```text id="25dx2i"
lat
lon
```

### Metric CRS

For distance, buffering, snapping, area, and GIS operations, use an appropriate metric CRS.

For Kadikoy V0, the metric CRS is:

```text id="xy6bbo"
EPSG:32635
```

Typical fields may include:

```text id="hblchw"
x_32635
y_32635
```

or generic:

```text id="1vi1d7"
x_metric
y_metric
metric_crs
```

### CRS Rules

* Every imported spatial source should declare its CRS.
* CSV imports with `lat/lon` should be interpreted as EPSG:4326 unless explicitly configured otherwise.
* CSV imports with `x/y` must declare CRS or use a configured default.
* Snapping distance should be computed in a metric CRS.
* UI display should use EPSG:4326.
* Do not mix CRS assumptions silently.

## Layered Data Model

V1 should move toward layered data.

### Base Grid Layer

Owns:

* candidate IDs,
* geometry,
* coordinates,
* candidate bounds,
* restrictions,
* selectability,
* zone/neighborhood references.

### Feature Layers

Own candidate attributes used by objectives and reports.

Examples:

* population,
* demand proxy,
* POI counts,
* transit access,
* risk score,
* traffic score,
* cost score,
* underserved score,
* forbidden/restriction features.

### Scenario Layer

Owns editable decision state.

Examples:

* existing facilities,
* imported facilities,
* manually added facilities,
* disabled facilities,
* locked candidates,
* disabled candidates,
* objective bundle,
* run settings.

### Output Layer

Owns optimizer and benchmark results.

Examples:

* selected candidate IDs,
* objective values,
* Pareto flags,
* benchmark metrics,
* coverage summaries,
* reporting metadata,
* run metadata.

## Grid Attributes vs Scenario Entities

This distinction is non-negotiable.

### Grid Attributes

Grid attributes describe the candidate itself or contextual facts around it.

Examples:

* population,
* demand proxy,
* POI score,
* risk score,
* cost score,
* forbidden/selectable status,
* neighborhood,
* proximity/context counts.

### Scenario Entities

Scenario entities describe facilities and decisions in a specific planning run.

Examples:

* existing facility at candidate 123,
* imported facility snapped to candidate 456,
* manually added facility,
* disabled existing facility,
* locked candidate,
* disabled candidate,
* proposed optimizer output.

### Rule

Do not model editable planning decisions as permanent base grid attributes.

A user editing a scenario should not mutate the base grid.

## Existing Facility Semantics

V1 should represent existing facilities as scenario entities.

Preferred source of truth:

```text id="h3u58h"
scenario.facilities[]
```

not:

```text id="r3qyt7"
candidate_points.csv proximity/count fields
```

This allows:

* current network benchmarks,
* greenfield scenarios,
* expansion scenarios,
* manual corrections,
* CSV/GIS imports,
* add/remove/edit workflows,
* scenario comparison,
* auditability.

## `nearby_locker_count` Meaning

`nearby_locker_count` is proximity and context only.

It may indicate how many lockers are near a candidate within a buffer or neighborhood.

It can be useful for:

* overlap analysis,
* cannibalization proxy,
* context display,
* competition/service saturation signal.

It must not be used as the source of existing facility entities.

Incorrect:

```text id="a79p46"
nearby_locker_count > 0 means this candidate is an existing facility
```

Correct:

```text id="br2trf"
nearby_locker_count is a proximity/context signal
```

## `existing_locker_count` Meaning

`existing_locker_count` is the mapped physical existing locker count in the current Kadikoy V0 data.

It is closer to actual facility presence than proximity counts.

However, in V1 it should usually be used only to:

* seed a default parcel-locker scenario,
* validate current V0 existing facility mapping,
* support backward compatibility during migration.

Long-term editable existing locations should live in scenario data.

## Legacy `locker_count`

Older files or documentation may mention:

```text id="regptx"
locker_count
```

Do not reintroduce:

```text id="i8vqem"
locker_count > 0
```

as existing facility logic.

If a legacy file contains `locker_count`, verify whether it means:

* old proximity count,
* mapped physical count,
* or another historical export field.

Do not assume its meaning without checking the current contract.

## Forbidden and Selectable Candidates

Current V0 behavior:

* forbidden candidates remain in the CSV,
* forbidden candidates remain in the distance matrix,
* forbidden candidates still act as demand grid points,
* forbidden candidates are excluded from selectable facility locations.

V1 should preserve this conceptual separation:

```text id="x41oky"
demand/evaluation universe
```

may be larger than:

```text id="ass0ge"
selectable facility universe
```

Rules:

* Do not delete forbidden candidates casually.
* Do not filter them out of the matrix unless the entire runtime contract is rebuilt.
* Scenario disabled candidates are different from base forbidden candidates.
* A candidate can be physically forbidden but still useful as a demand/reference point.

## Scenario Facility Snapping

Scenario facilities may come from:

* CSV import,
* GIS import,
* map click,
* form entry,
* V0 seed data,
* optimizer output.

If a facility has arbitrary coordinates, it must be snapped to a candidate before it can be used by the optimizer.

Snapping output should include:

```text id="hq5i84"
candidateId
snapDistanceMeters
snapMethod
snapStatus
```

Snap status examples:

```text id="tqfgov"
snapped
unsnapped
ambiguous
too_far
invalid_geometry
candidate_forbidden
```

Rules:

* Snapping must produce candidate IDs, not row offsets.
* Snap distance should be computed in metric CRS.
* Unsnapped or invalid optimizer-relevant facilities must not silently enter optimization.
* Snap audit data should be preserved for reporting and debugging.

## CSV Import Expectations

CSV imports should be explicit and validated.

Potential coordinate column patterns:

```text id="8ljah4"
lat, lon
latitude, longitude
x, y
x_32635, y_32635
```

Expected import behavior:

1. Read CSV.
2. Detect or map coordinate columns.
3. Determine CRS.
4. Validate coordinates.
5. Assign scenario facility IDs if importing facilities.
6. Preserve source row metadata.
7. Snap to candidate IDs if needed.
8. Report invalid or ambiguous rows.
9. Store imported records in scenario state or layer output.

Do not silently drop invalid rows without a report.

## GIS Import Expectations

GIS import may later support:

* GeoJSON,
* GeoPackage,
* shapefile,
* other spatial formats.

Expected behavior:

* detect geometry type,
* validate CRS,
* reproject if needed,
* preserve source metadata,
* join or snap to candidate grid,
* produce import audit output.

GIS import should not mutate raw provenance files.

## Layer Join Methods

V1 layer ingestion may support multiple join methods.

Possible methods:

| Method                  | Meaning                                               |
| ----------------------- | ----------------------------------------------------- |
| `direct_candidate_join` | Join by candidate ID                                  |
| `nearest_candidate`     | Assign each source point to nearest candidate         |
| `within_grid`           | Assign points/polygons within candidate cell          |
| `buffer_count`          | Count points within a buffer around candidate         |
| `buffer_sum`            | Sum attribute values within a buffer                  |
| `buffer_mean`           | Average attribute values within a buffer              |
| `weighted_intersection` | Allocate polygon attributes by overlap area           |
| `network_catchment`     | Assign values through walking/road network catchments |

Each layer should declare:

* source path,
* source CRS,
* geometry type,
* join method,
* output columns,
* assumptions,
* refresh/update frequency if known.

## Layer Metadata

Every derived feature layer should preserve metadata.

Suggested metadata fields:

```json id="fnao0l"
{
  "layerName": "population",
  "sourcePath": "data/layers/population.csv",
  "sourceType": "csv",
  "sourceCrs": "EPSG:4326",
  "joinMethod": "weighted_intersection",
  "outputColumns": ["population"],
  "createdAt": null,
  "createdBy": "script",
  "assumptions": [],
  "notes": []
}
```

Layer metadata helps agents and humans avoid guessing where columns came from.

## Objective Input Validation

Before optimization, the selected objective bundle must declare and validate required fields.

Example:

```json id="h93kvb"
{
  "objectiveId": "accessibility_cost",
  "requiredCandidateFields": ["demand_score"],
  "requiredScenarioFields": [],
  "requiredMatrix": true
}
```

Validation should fail early if required fields are missing.

Do not silently fall back to another demand model unless that behavior is documented and reported.

## Data Versioning and Provenance

Every run should preserve enough metadata to reproduce or explain results.

Recommended run metadata:

* candidate source path,
* candidate source version or hash where available,
* distance matrix source path,
* candidate ID order,
* scenario ID,
* objective bundle,
* layer versions,
* import sources,
* CRS assumptions,
* created timestamp where available.

Benchmark claims should reference this metadata.

## Generated Outputs

Generated outputs should not be treated as source data.

Examples:

```text id="a1ijjk"
output/
parcel-locker-ui/public/mock/
sections/figures/final_results/
```

Generated files may be useful for demos and reports, but source-of-truth data contracts should come from:

* base grid,
* feature layers,
* scenario definitions,
* objective configs,
* run metadata.

## Schema Validation Checklist

Before runtime use, validate:

### Candidate/Grid

* required ID column exists,
* candidate IDs are unique,
* candidate IDs are stable,
* coordinate fields exist,
* coordinates are parseable,
* CRS is known,
* selectability/forbidden fields are valid,
* candidate count matches matrix dimensions,
* candidate ID order matches matrix contract.

### Matrix

* matrix exists,
* matrix is square,
* matrix dimension equals candidate count,
* candidate ID order is known,
* matrix units are documented,
* matrix distance type is documented.

### Scenario

* scenario ID exists,
* schema version is supported,
* all facility IDs are unique,
* facility kinds are valid,
* facility statuses are valid,
* enabled optimizer-relevant facilities have snapped candidate IDs,
* snapped candidate IDs exist,
* locked candidate IDs exist,
* disabled candidate IDs exist,
* locked and disabled sets do not conflict,
* facility count semantics are unambiguous.

### Objective Bundle

* objective IDs are valid,
* objective directions are supported,
* required candidate fields exist,
* required scenario fields exist,
* required matrix is available,
* output units are known.

### Reporting/Benchmark

* demand type is stated,
* compared scenarios use compatible candidate universe,
* K/facility count semantics are explicit,
* existing ON/OFF assumptions are explicit,
* proxy vs calibrated demand is clear.

## Migration Rules

During V0 to V1 migration:

* preserve V0 runtime path unless explicitly changing it,
* do not delete old fields before adapters exist,
* add scenario contracts before wiring UI editing deeply,
* use `existing_locker_count` only as a possible seed for scenario facilities,
* do not infer existing facilities from `nearby_locker_count`,
* avoid hard-coding parcel locker terms in generic layers,
* record compatibility decisions in docs and metadata.

A reasonable migration path:

```text id="qdacuz"
V0 candidate_points.csv
  -> generated default parcel-locker scenario
  -> editable scenario facilities
  -> scenario-driven optimizer inputs
  -> generic grid_features.csv or database table
```

## Non-Negotiable Rules

* Do not break candidate ID and matrix alignment.
* Do not use row offsets as persistent IDs.
* Do not infer existing facilities from `nearby_locker_count`.
* Do not reintroduce `locker_count > 0` as existing facility logic.
* Do not mutate the base grid when editing a scenario.
* Do not silently mix CRS assumptions.
* Do not compare scenarios without checking candidate universe and data version.
* Do not create objective outputs without documenting required input fields.
* Do not hide data source assumptions from benchmark reports.

## Summary

The V1 data model should support this spine:

```text id="1c8jb4"
stable candidate grid
  -> layered feature data
  -> editable scenario facilities
  -> objective input validation
  -> optimization over candidate IDs
  -> benchmark/report output
  -> map sandbox visualization
```

The current Kadikoy `candidate_points.csv` and distance matrix are the V0 implementation of this idea, not the final generic platform schema.
