# V1 Roadmap

## Purpose

This roadmap defines the migration path from the current Kadikoy parcel locker optimizer into a generic grid-based location optimization platform.

The goal is not to build disconnected demo features.

The goal is to build a reusable platform spine:

```text id="uxhr6r"
stable grid data
  -> editable scenario facilities
  -> modular objectives
  -> optimization
  -> benchmark reporting
  -> map sandbox
```

## Product Direction

The current system is the V0 Kadikoy parcel locker implementation.

V1 should support generic location optimization use cases such as:

* parcel lockers,
* food deserts,
* fire stations,
* police coverage,
* municipal service points,
* health access,
* logistics networks,
* other facility planning problems.

The first priority is to remove parcel-locker-specific existing-location assumptions from the core and introduce a generic scenario/facility model.

## Roadmap Principles

### 1. Preserve V0 While Migrating

The current Kadikoy parcel locker workflow is the working baseline.

Do not break it casually.

V1 work should add contracts, adapters, and migration paths before removing existing behavior.

### 2. Generalize the Core Before Adding Many Use Cases

Do not start by building many new domain demos.

First build the generic pieces:

```text id="0voao4"
facility
scenario
candidate snapping
scenario-based optimizer input
scenario-based benchmark
```

After that, adding food desert, fire station, or police demos becomes much easier.

### 3. Existing Facilities Belong in Scenarios

V1 should not treat base candidate CSV columns as the long-term source of truth for existing locations.

Preferred direction:

```text id="cqmxux"
scenario.facilities[]
```

not:

```text id="n9m2rp"
candidate_points.csv proximity/count fields
```

### 4. Do Not Leave `K` Ambiguous

Facility count semantics must be explicit:

```text id="ihm8zk"
targetNewFacilityCount
targetTotalFacilityCount
```

Use `targetNewFacilityCount` for expansion scenarios.

Use `targetTotalFacilityCount` for greenfield and same-count comparisons.

### 5. Benchmarks Must Be Scenario-Based

Reports should compare scenarios, not loose output files.

Each benchmark should know:

* scenario ID,
* candidate source,
* distance matrix source,
* demand type,
* objective bundle,
* existing ON/OFF,
* facility count semantics,
* constraints,
* coverage threshold.

## Phase 0: Stabilize Current V0 System

### Goal

Preserve the current Kadikoy parcel locker system as a reliable technical baseline.

### Tasks

* Confirm the current runtime path.
* Document runtime inputs and generated outputs.
* Protect candidate ID and distance matrix alignment.
* Clarify generated, archive, raw, and source folders.
* Ensure V0 behavior is not accidentally broken by V1 documentation or refactor work.
* Keep Java SPEA2 as the authoritative optimizer.

### Acceptance Criteria

* Agents can identify the V0 runtime path.
* Agents know which files are source, generated, raw, archive, or research artifacts.
* Candidate ID / matrix alignment is documented as non-negotiable.
* Current V0 functionality remains understandable and runnable.
* V1 work has clear guardrails.

### Do Not Do

* Do not rewrite optimizer architecture in this phase.
* Do not migrate all data files in this phase.
* Do not delete V0 artifacts casually.
* Do not run long optimizer or parameter analysis jobs unless explicitly requested.

## Phase 1: Generic Facility + Scenario Contract

### Goal

Define the generic facility and scenario model that will replace parcel-locker-specific existing-location assumptions.

This is the first major V1 milestone.

### Tasks

* Define the scenario JSON structure.
* Define facility fields:

  * `id`
  * `kind`
  * `status`
  * `facilityType`
  * `source`
  * coordinates
  * snap metadata
  * metadata
* Define allowed facility `kind` values:

  * `existing`
  * `manual`
  * `proposed`
  * `imported`
  * `reference`
* Define allowed facility `status` values:

  * `enabled`
  * `disabled`
  * `removed`
  * `draft`
  * `invalid`
* Define existing ON/OFF semantics.
* Define `targetNewFacilityCount` and `targetTotalFacilityCount`.
* Define locked and disabled candidate semantics.
* Define scenario validation checklist.
* Define how V0 `existing_locker_count` may seed a default parcel-locker scenario.

### Acceptance Criteria

* Existing facilities are conceptually scenario entities.
* `nearby_locker_count` is not used as existing facility presence.
* `locker_count > 0` is not reintroduced.
* Scenario examples can represent:

  * current network,
  * greenfield optimization,
  * expansion optimization,
  * manual scenario,
  * same-count benchmark.
* Facility count semantics are not ambiguous.
* Candidate IDs remain the optimizer-facing reference.

### Do Not Do

* Do not deeply refactor Java yet.
* Do not deeply refactor UI yet.
* Do not build many use cases yet.
* Do not move existing facilities back into base grid attributes as the only source of truth.

## Phase 2: Facility Import and Candidate Snapping

### Goal

Allow users or scripts to create scenario facilities from CSV/GIS/manual inputs and map them to candidate IDs.

### Tasks

* Define CSV import expectations.
* Support coordinate column patterns:

  * `lat`, `lon`
  * `latitude`, `longitude`
  * `x`, `y`
  * `x_32635`, `y_32635`
* Require explicit CRS handling.
* Support initial CRS assumptions:

  * EPSG:4326 for display coordinates,
  * EPSG:32635 for Kadikoy metric operations.
* Snap imported or manually placed facilities to nearest valid candidate.
* Record snap metadata:

  * `candidateId`
  * `snapDistanceMeters`
  * `snapMethod`
  * `snapStatus`
* Produce import/snap audit output.
* Report invalid, ambiguous, too-far, or forbidden-candidate snaps.
* Preserve source row metadata.

### Acceptance Criteria

* Imported facilities become scenario entities.
* Manual facilities can become scenario entities.
* Snapped facilities produce candidate IDs.
* Invalid imports are reported instead of silently dropped.
* Snapping does not break candidate ID / matrix alignment.
* V0 existing locker data can be converted into a default current-network scenario.

### Do Not Do

* Do not mutate the base grid when importing facilities.
* Do not use raw row offsets as facility references.
* Do not silently assume CRS.
* Do not silently accept invalid or unsnapped optimizer-relevant facilities.

## Phase 3: Scenario-Driven Optimizer Input

### Goal

Connect scenario state to optimizer inputs without rewriting the entire optimizer core.

### Tasks

* Convert scenario facilities and constraints into optimizer-relevant candidate ID sets:

  * active existing candidate IDs,
  * locked candidate IDs,
  * disabled candidate IDs,
  * selectable candidate universe,
  * target facility count.
* Preserve V0 CLI compatibility where needed.
* Add a short-term adapter if full scenario JSON support is not ready.
* Define how existing ON/OFF affects optimizer input.
* Define how expansion optimization differs from greenfield optimization.
* Store scenario assumptions in run metadata.

### Acceptance Criteria

* Current network scenario can be evaluated.
* Greenfield optimization can ignore existing facilities.
* Expansion optimization can include existing facilities and select new proposed locations.
* Locked candidates can be forced into a result.
* Disabled candidates can be excluded.
* Run metadata records scenario assumptions.
* V0 optimizer behavior remains available.

### Do Not Do

* Do not rebuild SPEA2 outside Java.
* Do not duplicate objective logic in the UI.
* Do not leave `K` meaning ambiguous.
* Do not compare output without knowing scenario assumptions.

## Phase 4: Scenario UI Foundation

### Goal

Turn the UI state model into an editable scenario model before doing heavy map modernization.

### Tasks

* Add frontend scenario state.
* Represent:

  * existing facilities,
  * proposed facilities,
  * manual facilities,
  * disabled facilities,
  * locked candidates,
  * disabled candidates.
* Add existing ON/OFF as scenario setting.
* Add target facility count fields.
* Add scenario serialization and deserialization.
* Show scenario assumptions in UI.
* Keep current V0 result visualization working.
* Prepare UI state to send scenario JSON to backend.

### Acceptance Criteria

* UI can hold a scenario object.
* Existing ON/OFF is scenario state, not just a loose checkbox.
* Users can conceptually edit scenario facilities without mutating base candidate data.
* Scenario state can be serialized.
* UI outputs identify the scenario that produced them.
* V0 UI remains usable during transition.

### Do Not Do

* Do not build UI-only state that cannot map to scenario contract.
* Do not make visual-only facility edits that cannot affect optimizer input later.
* Do not deeply migrate to MapLibre/deck.gl before scenario state exists.

## Phase 5: Business Benchmark Metrics

### Goal

Convert optimization outputs into careful scenario-based comparisons.

### Tasks

* Define and compute current network metrics.
* Define same-K / same effective facility count comparisons.
* Define same coverage with fewer facilities.
* Define expansion metrics.
* Add coverage thresholds such as 300m, 500m, and 700m where appropriate.
* Add metrics:

  * covered demand,
  * uncovered demand,
  * average weighted distance,
  * median distance,
  * 90th percentile distance,
  * equity gap,
  * worst-served zone,
  * demand per facility,
  * cost per covered demand when cost data exists,
  * marginal gain.
* Preserve benchmark metadata.
* Distinguish proxy demand from calibrated real demand.
* Generate scenario-based benchmark reports.

### Acceptance Criteria

* Reports can compare current vs optimized scenarios.
* Reports do not rely only on F1/F2.
* Reports state candidate universe, demand type, existing ON/OFF, objective bundle, and facility count semantics.
* Same-K and same-coverage comparisons are clearly labeled.
* Claim language is careful and assumption-aware.

### Do Not Do

* Do not claim real-world business improvement without data assumptions.
* Do not compare incompatible scenarios silently.
* Do not infer current network from `nearby_locker_count`.
* Do not present proxy demand as observed demand.

## Phase 6: Objective Engine Refactor

### Goal

Move from hard-coded objective pairs toward modular objective bundles.

This phase should come after scenario/facility semantics are stable enough to support generic use cases.

### Tasks

* Define objective metadata:

  * `id`
  * label
  * direction
  * required candidate fields
  * required scenario fields
  * reporting unit
  * normalization
* Keep early V1 objectives minimize-only.
* Map current F1/F2 into generic objective concepts:

  * accessibility cost,
  * equity cost.
* Add or prepare objective concepts:

  * demand coverage loss,
  * cost efficiency,
  * response time,
  * risk coverage,
  * cannibalization/overlap penalty.
* Define objective bundles by use case.
* Validate required objective inputs before optimization.

### Acceptance Criteria

* Current F1/F2 remain understandable as V0 baseline logic.
* Objective bundles can be described without rewriting the whole optimizer.
* Objectives declare required inputs.
* Objective outputs are named and unit-aware.
* Generic objective code does not assume parcel lockers unless explicitly use-case-specific.

### Do Not Do

* Do not introduce maximization without converting to loss or updating all dominance logic.
* Do not mix objective math with UI labels.
* Do not hard-code parcel locker assumptions into generic objective infrastructure.
* Do not refactor objective code without tests or validation plan.

## Phase 7: Map Layer System and Scenario Sandbox

### Goal

Make the map a scenario canvas rather than only a result viewer.

### Tasks

* Define map layers explicitly:

  * base map,
  * candidate grid,
  * forbidden candidates,
  * disabled candidates,
  * existing facilities,
  * manual facilities,
  * proposed facilities,
  * locked facilities,
  * optimized solution,
  * coverage layer,
  * demand/risk heatmap,
  * scenario comparison layer.
* Add layer visibility state.
* Add hover/click behavior linked to candidate IDs and facility IDs.
* Support scenario interactions:

  * add facility,
  * disable facility,
  * remove facility,
  * lock proposed location,
  * show coverage,
  * show heatmap,
  * compare scenarios.
* Keep current Leaflet viewer working until migration is justified.

### Acceptance Criteria

* Map layers are explicit and documented.
* Scenario editing remains candidate-ID aware.
* Map interactions update scenario state.
* Existing/proposed/manual/locked/disabled facilities are visually distinct.
* Current V0 result visualization is not broken.

### Do Not Do

* Do not migrate map engine just for aesthetics.
* Do not create visual interactions that cannot serialize into scenario state.
* Do not break candidate ID linkage.
* Do not edit generated mock files manually unless explicitly requested.

## Phase 8: Map Modernization Evaluation

### Goal

Evaluate whether Leaflet should be replaced or supplemented for V1 scenario editing and large-layer rendering.

### Tasks

* Evaluate current Leaflet limitations.
* Prototype MapLibre and deck.gl only if needed.
* Compare:

  * rendering smoothness,
  * large point dataset performance,
  * polygon layer performance,
  * heatmap support,
  * coverage layer support,
  * scenario editing interactions,
  * integration complexity.
* Use a separate prototype route or feature flag if possible.
* Keep migration incremental.

### Acceptance Criteria

* Map engine decision is based on real V1 interaction needs.
* Prototype does not break current dashboard.
* Candidate IDs and scenario facility IDs remain traceable.
* Map modernization supports the scenario sandbox roadmap.

### Do Not Do

* Do not rewrite the whole UI just to change map library.
* Do not abandon Leaflet before scenario state is stable.
* Do not hard-code Kadikoy parcel locker assumptions into the new map layer model.

## Phase 9: Additional Use-Case Demo

### Goal

Prove that the platform is generic beyond parcel lockers.

### Recommended Order

After the scenario/facility model, benchmark layer, and objective structure are stable, add a second use case.

Good candidates:

1. Food desert / grocery access
2. Fire station response coverage
3. Police response or risk coverage

### Tasks

* Select one second use case.
* Define required grid features.
* Define scenario facility type.
* Define objective bundle.
* Define benchmark metrics.
* Prepare or mock compatible data.
* Avoid copying the parcel locker implementation.
* Use generic scenario and objective concepts.

### Acceptance Criteria

* The second demo uses the same platform spine.
* No new core parcel-locker assumptions are added.
* Use-case labels can change without changing generic core code.
* Benchmark output is understandable to the target domain.
* The second demo proves reusability, not just duplicated code.

### Do Not Do

* Do not build many shallow demos at once.
* Do not make use-case-specific hacks in generic layers.
* Do not fake generality by copying parcel locker code and renaming labels.

## Phase 10: Production Hardening

### Goal

Prepare the platform for reliable multi-user or production-style deployment.

### Tasks

* Add run-specific output folders.
* Add run IDs.
* Add job status and result endpoints.
* Add run history.
* Add schema validation.
* Add scenario provenance.
* Add data versioning or file hashes.
* Add better error messages.
* Add concurrency control.
* Move long-running optimization out of the interactive request path when needed.
* Consider backend service separation if required.

### Acceptance Criteria

* Runs are traceable to data, scenario, objective, and code versions.
* Shared output files no longer overwrite important runs.
* Long-running optimization jobs are managed safely.
* Errors are actionable for users and agents.
* Production constraints are documented.

### Do Not Do

* Do not claim production readiness while `/api/run-ga` still spawns long Maven jobs synchronously as the only execution path.
* Do not allow concurrent jobs to overwrite shared outputs.
* Do not hide failed validation behind generic errors.

## Milestone Summary

## M0: V0 Stabilized

Result:

```text id="3yom88"
Current Kadikoy parcel locker system is documented and protected.
```

## M1: Generic Facility + Scenario System

Result:

```text id="oqo84k"
Existing locations can be represented, imported, edited, enabled/disabled, snapped, and serialized as scenario entities.
```

This is the most important first V1 milestone.

## M2: Scenario-Driven Optimization

Result:

```text id="dj891t"
Optimizer input can be derived from scenario state.
```

## M3: Scenario-Based Benchmarking

Result:

```text id="swvldm"
Current, optimized, expansion, reduced, and manual scenarios can be compared with careful metrics and claims.
```

## M4: Scenario Sandbox UI

Result:

```text id="c34v9c"
UI can edit and compare planning scenarios, not only visualize optimizer outputs.
```

## M5: Modular Objective Foundation

Result:

```text id="gvo2xs"
Use cases can select objective bundles without rewriting the optimizer core.
```

## M6: Second Use-Case Demo

Result:

```text id="12k12g"
The platform demonstrates generality beyond parcel lockers.
```

## M7: Production-Ready Core Direction

Result:

```text id="efhpwm"
Runs are traceable, validated, isolated, and suitable for stronger demos or pilot discussions.
```

## Recommended Immediate Work Order

The next implementation work should follow this order:

```text id="glxc4y"
1. Finalize scenario contract.
2. Finalize data contract.
3. Create default current-network scenario from V0 existing_locker_count.
4. Add facility CSV import and candidate snapping.
5. Add scenario serialization in UI/backend.
6. Convert scenario to optimizer fixed/disabled/locked candidate inputs.
7. Add scenario-based benchmark report.
8. Refactor objective engine.
9. Expand map sandbox interactions.
10. Add second use-case demo.
```

## Final Rule

Do not skip the generic scenario/facility foundation.

If V1 features are built directly on parcel-locker-specific existing-location logic, the platform will become harder to generalize later.

The first real V1 product capability is:

```text id="8uidmv"
User-defined, editable, importable existing/proposed facility scenarios over a stable candidate grid.
```
