# Agent Operating Guide

This is the first-read file for AI agents working in this repository.

It applies to Codex, Claude Code, ChatGPT, and any other automated coding assistant working on the project.

## Project Direction

The project is moving from a **Kadikoy parcel locker optimization implementation** into a **generic grid-based location optimization platform**.

The current Kadikoy parcel locker system is the **V0 use case and technical baseline**.

The V1 direction is broader:

```text
Generic grid-based spatial optimization platform
```

V1 should support multiple facility-planning use cases such as:

* parcel lockers
* food deserts
* fire stations
* police coverage
* municipal service points
* health access
* logistics networks
* other location optimization problems

Do not add parcel-locker-specific assumptions to the generic V1 core.

## V1 Core Concepts

Use these concepts consistently.

### Grid / Candidate

A stable spatial decision unit.

A grid or candidate can represent:

* a grid cell
* a centroid
* a parcel
* an address
* a node
* another selectable spatial unit

Candidates are referenced by stable candidate IDs.

### Facility

An existing or proposed service location.

A facility can represent:

* a locker
* store
* fire station
* police station
* clinic
* service point
* logistics node
* other domain-specific location

Core code should use generic facility language where possible.

### Scenario

An editable decision context over a stable grid.

A scenario contains:

* existing facilities
* proposed facilities
* manually added or edited facilities
* disabled facilities
* locked candidates
* disabled candidates
* objective bundle
* run settings
* benchmark assumptions

Existing facilities should live in scenario data.

### Objective

A modular scoring function used by the optimizer.

Objectives should eventually be selected by use-case configuration rather than hard-coded into UI or optimizer orchestration.

### Benchmark

A business-facing comparison between:

* current network
* optimized alternatives
* expansion scenarios
* reduced-network scenarios
* manually edited scenarios

Benchmarks should make careful claims based on stated assumptions.

### Map Sandbox

The map should evolve from a result viewer into an interactive scenario canvas.

The target experience includes:

* add facility
* import facility
* edit facility
* disable facility
* lock proposed location
* show coverage
* show heatmap
* compare scenarios

## Required Reading Order

Before editing, read the files relevant to the task.

### Always Read First

1. `AGENTS.md`

### For General V1 Work

2. `docs/V1_ARCHITECTURE.md`
3. `docs/V1_DATA_CONTRACT.md`
4. `docs/V1_SCENARIO_CONTRACT.md`
5. `docs/V1_ROADMAP.md`

### For Data, CSV, GIS, Candidate, or Matrix Work

Read:

* `docs/V1_DATA_CONTRACT.md`
* `docs/REPO_STRUCTURE.md`

Optional archived V0 reference for historical implementation details:

* `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`

### For Scenario, Existing Facility, Import, Edit, or Sandbox Work

Read:

* `docs/V1_SCENARIO_CONTRACT.md`
* `docs/V1_DATA_CONTRACT.md`
* `docs/V1_MAP_UI_STRATEGY.md`

### For Objective or Optimizer Scoring Work

Read:

* `docs/V1_OBJECTIVE_CONTRACT.md`
* `src/main/java/service/FitnessCalculator.java`
* `src/main/java/algorithm/helper/Dominance.java`
* `src/main/java/algorithm/helper/Pareto.java`

Optional archived V0 reference for historical implementation details:

* `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`

### For Benchmark or Reporting Work

Read:

* `docs/V1_BENCHMARKING.md`
* `docs/V1_SCENARIO_CONTRACT.md`
* `docs/V1_DATA_CONTRACT.md`

### For UI or Map Work

Read:

* `docs/V1_MAP_UI_STRATEGY.md`
* `docs/V1_SCENARIO_CONTRACT.md`
* `docs/REPO_STRUCTURE.md`

### For Archived V0 Technical Details

Optionally read:

* `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`

That guide documents the Kadikoy parcel locker implementation as archived V0 technical reference only. V1 architecture and contracts are authoritative for new development.

## Architecture Priority

When V0 implementation details conflict with V1 direction, do not blindly extend the V0 pattern.

Use this priority order:

```text
1. Explicit user request
2. V1 architecture and contracts
3. Current V0 behavior preservation
4. Local implementation convenience
```

Preserve current V0 behavior unless the task explicitly asks for migration, but do not introduce new V0-specific assumptions into V1 core concepts.

## Non-Negotiable Contracts

These rules must not be violated.

### Candidate ID and Distance Matrix Alignment

Protect candidate ID and distance matrix alignment.

Current runtime inputs:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

The distance matrix row and column order must stay aligned to candidate IDs in ascending order.

Do not:

* reorder candidate IDs casually
* filter candidate rows without rebuilding the matrix
* change candidate IDs without migration
* use raw row offsets as persistent identifiers
* generate optimizer outputs that cannot be mapped back to candidate IDs

Breaking this contract invalidates objective values and map outputs.

### Scenario Source of Truth for Existing Facilities

In V1, existing facilities should be scenario entities.

The source of truth should move toward:

```text
scenario.facilities
```

not:

```text
candidate_points.csv proximity/count fields
```

Current V0 data may contain mapped existing locker fields for compatibility, but new V1 work should model editable existing locations through scenario data.

### `nearby_locker_count`

`nearby_locker_count` is proximity and context only.

Do not treat:

```text
nearby_locker_count > 0
```

as an existing facility signal.

### `existing_locker_count`

`existing_locker_count` is the mapped physical existing locker count in the current Kadikoy V0 data.

It is closer to actual facility presence than nearby proximity counts, but V1 should still move existing facilities into scenario data.

Do not design new V1 workflows where the base candidate CSV is the only source of truth for existing locations.

### `locker_count`

Do not reintroduce:

```text
locker_count > 0
```

as existing facility logic.

If legacy files mention `locker_count`, treat it as historical V0 terminology and verify the current semantic contract before using it.

### Java SPEA2 Authority

Java SPEA2 is currently the authoritative optimization engine.

Do not rewrite optimizer logic in the UI, Python, or backend unless explicitly requested.

Supporting code may parse, validate, benchmark, visualize, or prepare inputs, but Java remains the current source of optimization truth.

### Objective Direction

Current Pareto and dominance logic assumes minimization.

Before introducing a maximization objective, either:

* convert it into a minimization loss or penalty, or
* update all dominance, Pareto, hypervolume, plotting, UI interpretation, and reporting logic.

Early V1 should prefer minimize-only objective values.

## Development Rules

### Scope Control

* Prefer discovery before large edits.
* Keep changes scoped to the requested files and behavior.
* Make the smallest coherent change that preserves the V1 plan.
* Do not perform opportunistic rewrites.
* Do not mix documentation, data migration, UI refactor, and optimizer changes in one task unless explicitly requested.

### V0 Preservation

* Preserve current V0 Kadikoy parcel locker behavior unless the task explicitly asks for migration.
* When migrating, keep compatibility notes or adapters where needed.
* Do not remove V0 runtime paths without a clear replacement.

### V1 Modeling

* Model new V1 concepts as explicit contracts before wiring them into runtime code.
* Prefer generic names in core layers:

  * `facility`
  * `existingFacility`
  * `proposedFacility`
  * `scenario`
  * `candidate`
  * `objective`
  * `benchmark`
* Use parcel-locker labels only in parcel-locker use-case configuration or UI display layers.

### Data Safety

Treat these as provenance, generated, or historical unless the task explicitly targets them:

* `data/raw`
* `data/archive`
* `docs/archive`
* `scripts/archive`
* `output`
* `parcel-locker-ui/.next`
* `parcel-locker-ui/public/mock`
* `sections/figures/final_results`
* Maven `target` if present

Do not mutate base data, generated artifacts, or historical archives unless the task explicitly asks for that.

### Generated Files

Do not hand-edit generated outputs unless explicitly requested.

Generated or semi-generated areas include:

```text
output/
parcel-locker-ui/.next/
parcel-locker-ui/public/mock/
target/
sections/figures/final_results/
```

If a task requires updating generated UI mock assets, clearly report that they are generated and explain which command or script produced them.

### Git Rules

Do not stage or commit changes unless the user explicitly asks.

Do not run destructive git commands.

Avoid commands such as:

```bash
git reset --hard
git clean -fd
git checkout -- .
```

unless the user explicitly requests them and the scope is clear.

## Command and Validation Rules

Match validation to the scope of the change.

### Documentation-Only Tasks

For documentation-only tasks:

* static review is enough
* do not run Java optimizer
* do not run UI
* do not run long scripts

### Allowed Lightweight Validation

When relevant and not forbidden by the user, lightweight checks may include:

```bash
mvn -q compile
```

```bash
cd parcel-locker-ui
npm run lint
```

Use these only when the task touches Java or UI code and the user has not forbidden validation.

### Commands That Require Explicit Permission

Do not run these unless the user explicitly asks:

```bash
mvn -q compile exec:java
mvn -q compile exec:java -Panalyze
npm run dev
docker compose up --build
python3 scripts/prepare_demand.py
python3 data/prepare_ga_inputs.py --filter_forbidden
```

Also avoid long K optimization runs, full parameter analysis, and anything that may take many minutes.

### Data-Mutating Commands

These require explicit permission because they overwrite or regenerate important artifacts:

```bash
python3 scripts/prepare_demand.py
python3 data/prepare_ga_inputs.py
python3 parcel-locker-ui/src/scripts/process_ga_data.py
python3 scripts/plot_archives.py
```

Run them only when the task explicitly requires regenerated outputs.

### If Validation Is Skipped

If validation is intentionally skipped, report why.

Example:

```text
Validation skipped because this was a documentation-only change and the task forbade code execution.
```

## Stop Conditions

Stop and ask before continuing if a task would:

* break candidate ID and distance matrix alignment
* treat `nearby_locker_count` as an existing facility
* reintroduce `locker_count > 0` as existing facility logic
* hard-code Kadikoy parcel locker assumptions into a generic V1 layer
* move existing facilities back into base grid CSV attributes as the only source of truth
* mutate base data or generated artifacts outside the requested scope
* run long optimizer tests when not explicitly requested
* run UI dev servers when not explicitly requested
* require staging or commits when not explicitly requested
* require a broad architecture rewrite without a clear migration plan
* require deleting files from archive/raw/generated folders without explicit confirmation

## Required Report Format After Changes

After making changes, report:

1. Files created
2. Files updated
3. Key decisions documented
4. Assumptions made
5. Validation performed or intentionally skipped
6. Final `git diff --name-status`

If no files were changed, report:

```text
No files changed.
```

## Common Mistakes to Avoid

Avoid these mistakes:

* Treating `nearby_locker_count` as existing facility presence.
* Reintroducing `locker_count > 0` logic.
* Assuming all future use cases are parcel locker problems.
* Adding parcel-locker terms into generic core contracts.
* Editing `.next` or generated UI mock files directly.
* Running full optimizer or parameter-analysis jobs for small changes.
* Changing candidate IDs without regenerating and validating the matrix.
* Comparing benchmark scenarios without checking that they use the same candidate universe and data version.
* Claiming real-world business improvement from proxy demand without stating assumptions.
* Building UI-only features that are not connected to scenario, objective, or benchmark contracts.
* Copying legacy scripts into active workflows without checking current contracts.

## Current First V1 Milestone

The first major V1 milestone is:

```text
Generic Facility + Scenario System
```

This means:

* existing locations become editable scenario entities
* users can import existing facilities
* users can manually add, remove, disable, and edit facilities
* facilities can be snapped to candidate IDs
* existing ON/OFF becomes scenario state
* optimizer inputs can be derived from scenario state
* current-vs-optimized comparisons become scenario-based
* core code moves away from parcel-locker-specific assumptions

Do not skip this milestone by jumping directly into isolated UI features or isolated objective changes that still depend on parcel-locker-specific existing-location logic.

## Final Principle

The project should not become a collection of unrelated demo features.

Every change should support this product spine:

```text
grid data
  -> scenario facilities
  -> modular objectives
  -> optimization
  -> benchmark reporting
  -> map sandbox
```
