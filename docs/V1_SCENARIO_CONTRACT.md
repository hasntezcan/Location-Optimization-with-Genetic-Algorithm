# V1 Scenario Contract

## Purpose

A scenario is an editable planning context over a stable candidate grid.

It records:

* which facilities currently exist,
* which facilities are manually added or edited,
* which candidates are locked or disabled,
* whether existing facilities are included in a run,
* which objective bundle is active,
* what facility count the optimizer should produce,
* which assumptions were used for benchmarking and reporting.

V1 should make scenarios the main place where existing facilities live.

The base grid should describe the city.
The scenario should describe the planning decision.

## Core Principle

Existing facilities are **scenario entities**, not base grid attributes.

The V1 source of truth should be:

```text
scenario.facilities[]
```

not:

```text
candidate_points.csv proximity/count columns
```

Current V0 data may contain `existing_locker_count` for Kadikoy parcel locker compatibility, but V1 should not depend on candidate CSV columns as the only representation of existing locations.

## Scenario vs Grid

The distinction is critical.

### Grid / Candidate Data

Grid data describes reusable spatial facts.

Examples:

* candidate ID
* coordinates
* neighborhood
* forbidden/selectable status
* population
* demand score
* POI features
* risk features
* cost features
* proximity/context counts

Grid data should be reusable across multiple scenarios.

### Scenario Data

Scenario data describes a specific planning setup.

Examples:

* existing facilities imported from CSV
* existing facilities manually added on the map
* disabled existing facilities
* locked candidates
* disabled candidates
* proposed facilities being tested
* selected objective bundle
* target facility count
* include-existing setting

Multiple scenarios may use the same grid.

## Facility Model

A facility is an existing, proposed, or manually added service location.

Core fields:

```json
{
  "id": "facility-001",
  "kind": "existing",
  "status": "enabled",
  "facilityType": "parcel_locker",
  "label": "Existing facility 001",
  "source": "csv_import",
  "coordinates": {
    "lat": 40.991,
    "lon": 29.025,
    "crs": "EPSG:4326"
  },
  "snap": {
    "candidateId": 123,
    "snapDistanceMeters": 18.4,
    "snapMethod": "nearest_candidate",
    "snapStatus": "snapped"
  },
  "metadata": {}
}
```

## Facility `kind`

`kind` describes the role of a facility inside the scenario.

Allowed conceptual values:

| Kind        | Meaning                                                        |
| ----------- | -------------------------------------------------------------- |
| `existing`  | A real facility that already exists in the current network     |
| `manual`    | A user-added facility used for scenario testing                |
| `proposed`  | A facility proposed by the optimizer or by a planning workflow |
| `imported`  | A facility imported from CSV/GIS before classification         |
| `reference` | A non-optimized reference point used for context only          |

Recommended rule:

* Imported real-world current locations should usually become `existing`.
* User-drawn test locations should usually become `manual`.
* Optimizer outputs should usually become `proposed`.
* Context-only points should not automatically affect optimization.

## Facility `status`

`status` describes whether and how the facility participates in the scenario.

Allowed conceptual values:

| Status     | Meaning                                                                   |
| ---------- | ------------------------------------------------------------------------- |
| `enabled`  | Active in the scenario                                                    |
| `disabled` | Kept in scenario history but excluded from active calculations            |
| `removed`  | Marked as removed from the scenario; retained for audit/history if needed |
| `draft`    | Created but not yet validated or snapped                                  |
| `invalid`  | Failed validation or cannot be used until corrected                       |

Recommended rule:

Only `enabled` facilities should affect optimization and benchmarking unless a task explicitly says otherwise.

## Facility Type

`facilityType` is use-case-specific.

Examples:

```text
parcel_locker
grocery_store
fire_station
police_station
clinic
pharmacy
school
municipal_service_point
logistics_node
```

Core scenario logic should not assume every facility is a parcel locker.

Use-case labels may translate the generic facility into domain wording:

| Use case      | Generic facility label        |
| ------------- | ----------------------------- |
| Parcel locker | locker / parcel locker        |
| Food desert   | grocery access point / market |
| Fire station  | fire station                  |
| Police        | station / patrol point        |
| Health access | clinic / pharmacy             |

## Source

`source` explains where the facility came from.

Suggested values:

| Source              | Meaning                                                      |
| ------------------- | ------------------------------------------------------------ |
| `csv_import`        | Imported from a CSV file                                     |
| `gis_import`        | Imported from a GIS file such as GeoJSON or GeoPackage       |
| `manual_map_click`  | Added manually through map interaction                       |
| `manual_form`       | Added manually through a form                                |
| `optimizer_output`  | Created by an optimizer run                                  |
| `seed_from_v0_data` | Derived from current V0 data such as `existing_locker_count` |
| `system`            | Created by the system for internal workflow                  |

Source should be preserved for audit and reporting.

## Candidate Snapping

The optimizer operates on candidate IDs.

If a facility is imported or drawn at arbitrary coordinates, it must be snapped to a candidate before it can be used as a fixed or locked optimizer input.

Snapping metadata should include:

```json
{
  "candidateId": 123,
  "snapDistanceMeters": 18.4,
  "snapMethod": "nearest_candidate",
  "snapStatus": "snapped"
}
```

Suggested `snapStatus` values:

| Status                | Meaning                                                             |
| --------------------- | ------------------------------------------------------------------- |
| `snapped`             | Successfully matched to a candidate                                 |
| `unsnapped`           | Not yet snapped                                                     |
| `ambiguous`           | Multiple candidate matches require review                           |
| `too_far`             | Nearest candidate is beyond accepted snap threshold                 |
| `invalid_geometry`    | Coordinates or geometry could not be parsed                         |
| `candidate_forbidden` | Nearest candidate is forbidden; needs review or alternate snap rule |

Snapping must preserve candidate ID and distance matrix alignment.

Do not store raw row offsets as optimizer references. Use stable candidate IDs.

## Existing ON/OFF Semantics

Scenarios must support running with existing facilities enabled or disabled.

### Existing ON

Existing ON means:

```text
enabled existing facilities participate in the scenario
```

Depending on run type, this can mean:

* current network benchmark,
* expansion optimization,
* fixed existing coverage,
* optimizer selects additional facilities around existing network.

### Existing OFF

Existing OFF means:

```text
existing facilities are ignored for the optimization run
```

This represents a greenfield scenario.

The existing facilities can remain in the scenario file for reference, but they should not affect the active optimizer or benchmark calculation when `includeExistingFacilities = false`.

## Facility Count Semantics

Facility count must be explicit. Do not use ambiguous `K` semantics in scenario data.

Use these fields instead:

```json
{
  "targetNewFacilityCount": 5,
  "targetTotalFacilityCount": null
}
```

### `targetNewFacilityCount`

The number of new facilities the optimizer should select.

Example:

```text
Existing ON + targetNewFacilityCount = 5
```

means:

```text
keep active existing facilities and select 5 additional proposed facilities
```

### `targetTotalFacilityCount`

The desired total number of active facilities in the final scenario.

Example:

```text
Existing OFF + targetTotalFacilityCount = 27
```

means:

```text
select 27 proposed facilities from scratch
```

Example:

```text
Existing ON + targetTotalFacilityCount = 30
```

means:

```text
final active network should contain 30 total facilities, including enabled existing facilities
```

If both fields are present, the backend must validate that they do not conflict.

Recommended rule:

* Use `targetNewFacilityCount` for expansion scenarios.
* Use `targetTotalFacilityCount` for greenfield or same-K comparisons.
* Do not use a bare `k` field in long-term scenario contracts unless its meaning is explicitly documented.

## Scenario Run Types

A scenario can represent different planning questions.

Suggested `runType` values:

| Run type                  | Meaning                                                               |
| ------------------------- | --------------------------------------------------------------------- |
| `current_network`         | Evaluate only the enabled existing facilities                         |
| `greenfield_optimization` | Ignore existing facilities and optimize from scratch                  |
| `expansion_optimization`  | Keep existing facilities and optimize additional facilities           |
| `reduction_analysis`      | Find fewer facilities that preserve a target coverage level           |
| `manual_scenario`         | Evaluate user-edited facilities without necessarily running optimizer |
| `scenario_comparison`     | Compare two or more saved scenarios                                   |

## Locked and Disabled Candidates

Scenario constraints may include:

```json
{
  "lockedCandidateIds": [123],
  "disabledCandidateIds": [456]
}
```

### Locked Candidates

Locked candidates must be included in the optimized result.

Use cases:

* user wants to force a location,
* existing facility must remain,
* policy requires a facility in a zone,
* planner wants to test a specific site.

### Disabled Candidates

Disabled candidates cannot be selected.

Use cases:

* planner rejects a location,
* site is infeasible,
* temporary constraint,
* scenario-specific exclusion.

Constraints must be validated before optimization.

Validation should ensure:

* all candidate IDs exist,
* locked candidates are selectable unless explicitly allowed,
* disabled candidates are not also locked,
* locked candidate count does not exceed target count,
* scenario constraints do not violate run type semantics.

## Manual Add, Remove, and Edit

The scenario model should support user edits.

Required interactions:

* add facility,
* remove facility,
* disable facility,
* re-enable facility,
* edit facility label,
* edit facility type,
* edit facility source,
* move facility,
* re-snap facility to candidate,
* lock or unlock candidate,
* disable or enable candidate.

Every edit should update scenario state, not mutate the base grid.

## CSV and GIS Import

Facility imports should support CSV first and GIS formats later.

Expected CSV import behavior:

1. Read source file.
2. Detect or map coordinate columns.
3. Validate coordinates.
4. Assign stable scenario facility IDs.
5. Preserve source row metadata.
6. Snap to candidate IDs where required.
7. Report invalid, ambiguous, or unmatched records.
8. Store imported facilities in scenario state.

Possible coordinate formats:

* `lat`, `lon`
* `latitude`, `longitude`
* `x`, `y`
* `x_32635`, `y_32635`
* geometry column if supported later

Supported CRS should be explicit.

Initial expected CRS values:

```text
EPSG:4326
EPSG:32635
```

Any imported CRS must be converted or interpreted consistently before snapping.

## Scenario JSON Example

This is the recommended conceptual structure for V1 scenario data.

```json
{
  "schemaVersion": "v1",
  "scenarioId": "kadikoy-parcel-locker-current-plus-expansion",
  "name": "Kadikoy current network plus optimized expansion",
  "description": "Existing parcel locker network with five additional optimized facilities.",
  "useCase": "parcel_locker",
  "grid": {
    "candidateSource": "data/candidate_points.csv",
    "distanceMatrixSource": "data/kadikoy_distance_meters_nxn.npy",
    "candidateIdOrder": "ascending",
    "crs": {
      "display": "EPSG:4326",
      "metric": "EPSG:32635"
    }
  },
  "settings": {
    "runType": "expansion_optimization",
    "includeExistingFacilities": true,
    "targetNewFacilityCount": 5,
    "targetTotalFacilityCount": null,
    "objectiveBundle": "parcel_locker_business_default"
  },
  "facilities": [
    {
      "id": "existing-001",
      "kind": "existing",
      "status": "enabled",
      "facilityType": "parcel_locker",
      "label": "Existing locker 001",
      "source": "csv_import",
      "coordinates": {
        "lat": 40.991,
        "lon": 29.025,
        "crs": "EPSG:4326"
      },
      "snap": {
        "candidateId": 123,
        "snapDistanceMeters": 18.4,
        "snapMethod": "nearest_candidate",
        "snapStatus": "snapped"
      },
      "metadata": {
        "sourceFile": "existing_lockers_32635.csv"
      }
    }
  ],
  "constraints": {
    "lockedCandidateIds": [],
    "disabledCandidateIds": []
  },
  "objectives": [
    {
      "id": "accessibility_cost",
      "direction": "minimize"
    },
    {
      "id": "uncovered_demand_loss",
      "direction": "minimize"
    }
  ],
  "benchmark": {
    "demandType": "proxy",
    "coverageThresholdMeters": 500,
    "compareAgainstScenarioId": "kadikoy-current-network"
  },
  "metadata": {
    "createdBy": "user",
    "createdAt": null,
    "notes": []
  }
}
```

## Backend / Optimizer Flow

The eventual flow should be:

```text
UI scenario state
  -> backend scenario validation
  -> coordinate validation and candidate snapping
  -> constraint resolution
  -> optimizer input generation
  -> Java optimizer execution
  -> run metadata
  -> benchmark/report output
  -> UI scenario comparison
```

The optimizer should receive candidate IDs, not arbitrary map coordinates.

Scenario facilities should be converted into optimizer-relevant sets such as:

```text
activeExistingCandidateIds
lockedCandidateIds
disabledCandidateIds
candidateUniverse
targetNewFacilityCount
targetTotalFacilityCount
objectiveBundle
```

## Current V0 Compatibility

The current Kadikoy V0 implementation may still use files such as:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

and may still contain V0 locker-related fields.

Compatibility rule:

* V0 behavior may continue during migration.
* New V1 features should not depend on `nearby_locker_count` as existing facility presence.
* `existing_locker_count` may be used to seed a default scenario.
* Long-term editable existing locations should live in scenario data.

A reasonable migration step is:

```text
existing_locker_count in V0 data
  -> generated default scenario facilities
  -> editable scenario state
  -> optimizer fixed/locked candidate input
```

## Scenario Validation Checklist

Before a scenario is used for optimization or benchmarking, validate:

* `scenarioId` exists.
* `schemaVersion` is supported.
* candidate source exists.
* distance matrix source exists.
* candidate ID order is known.
* all facility IDs are unique.
* all enabled facilities have valid kind/status values.
* all enabled optimizer-relevant facilities have snapped candidate IDs.
* snapped candidate IDs exist in the candidate universe.
* locked candidate IDs exist.
* disabled candidate IDs exist.
* locked and disabled candidate sets do not conflict.
* target facility count semantics are valid.
* objective bundle exists.
* required objective input fields exist in candidate/grid data.
* benchmark demand type is stated.
* scenario assumptions are recorded in run metadata.

## Run Metadata Requirements

Every run produced from a scenario should preserve:

* scenario ID,
* scenario schema version,
* use case,
* candidate source,
* distance matrix source,
* objective bundle,
* run type,
* include-existing setting,
* target facility count semantics,
* active existing candidate IDs,
* locked candidate IDs,
* disabled candidate IDs,
* data version or file hashes where available,
* timestamp where available.

This is necessary for reproducibility and careful benchmark claims.

## Reporting Requirements

Scenario-based reports should state:

* which scenario was evaluated,
* which scenario it was compared against,
* whether demand is proxy or calibrated real demand,
* facility count assumptions,
* whether existing facilities were included,
* which objective bundle was used,
* what candidate universe was available,
* what constraints were applied.

Avoid reporting optimization results without scenario assumptions.

## Non-Negotiable Rules

* Do not infer existing facilities from `nearby_locker_count`.
* Do not reintroduce `locker_count > 0` as existing facility logic.
* Do not mutate the base grid when a user edits scenario facilities.
* Do not use raw row offsets as optimizer references.
* Do not leave `K` ambiguous in scenario contracts.
* Do not hard-code parcel locker semantics into generic scenario logic.
* Do not compare scenarios unless their assumptions and data sources are clear.

## Summary

A scenario is the editable bridge between base spatial data and optimization.

The V1 planning spine is:

```text
stable grid
  -> editable scenario facilities
  -> objective bundle
  -> optimization
  -> benchmark report
  -> map sandbox
```

The first major V1 milestone should be a reliable Generic Facility + Scenario System before deeper objective, benchmark, or map modernization work.
