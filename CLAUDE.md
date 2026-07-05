# Claude Code Operating Guide

Claude Code should read this file together with `AGENTS.md`.

`AGENTS.md` is the primary operating guide. This file adds Claude Code specific workflow rules.

## First Rule

Before making edits, read:

```text id="zm4v5w"
AGENTS.md
```

Then read the V1 document relevant to the task.

Do not start implementation from local code context alone. The project is moving from a Kadikoy parcel locker optimizer into a generic grid-based location optimization platform, and small changes can easily violate the larger architecture.

## Project Direction Reminder

The current working system is the V0 Kadikoy parcel locker implementation.

The target V1 direction is:

```text id="g2rr86"
Generic grid-based location optimization platform
```

Core V1 concepts:

* grid / candidate
* facility
* scenario
* objective
* benchmark
* map sandbox

Do not add new parcel-locker-specific assumptions to the generic core.

Existing facilities should move toward scenario data, not base candidate CSV attributes.

## Required Reading by Task Type

### General Architecture or Refactor Work

Read:

```text id="kv5phv"
AGENTS.md
docs/V1_ARCHITECTURE.md
docs/V1_ROADMAP.md
docs/REPO_STRUCTURE.md
```

### Data, Candidate, CSV, GIS, or Matrix Work

Read:

```text id="bnwr2k"
AGENTS.md
docs/V1_DATA_CONTRACT.md
docs/REPO_STRUCTURE.md
```

Optional archived V0 reference for historical implementation details:

```text
docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md
```

### Scenario, Existing Facility, Import, Edit, or Sandbox Work

Read:

```text id="5q4h5g"
AGENTS.md
docs/V1_SCENARIO_CONTRACT.md
docs/V1_DATA_CONTRACT.md
docs/V1_MAP_UI_STRATEGY.md
```

### Objective, Fitness, Pareto, or Optimizer Scoring Work

Read:

```text id="eq7ihv"
AGENTS.md
docs/V1_OBJECTIVE_CONTRACT.md
```

Optional archived V0 reference for historical implementation details:

```text
docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md
```

Then inspect the relevant Java files, especially:

```text id="l99lxg"
src/main/java/service/FitnessCalculator.java
src/main/java/algorithm/helper/Dominance.java
src/main/java/algorithm/helper/Pareto.java
src/main/java/algorithm/Evaluate.java
```

### Benchmark or Reporting Work

Read:

```text id="n41puz"
AGENTS.md
docs/V1_BENCHMARKING.md
docs/V1_SCENARIO_CONTRACT.md
docs/V1_DATA_CONTRACT.md
```

### UI or Map Work

Read:

```text id="8em52n"
AGENTS.md
docs/V1_MAP_UI_STRATEGY.md
docs/V1_SCENARIO_CONTRACT.md
docs/REPO_STRUCTURE.md
```

## Operating Rules

### Discovery First

Before large edits, do a short discovery pass.

Discovery should identify:

* which files are relevant
* which contracts apply
* whether the task is V0 preservation or V1 migration
* whether generated files are involved
* whether candidate ID / distance matrix alignment could be affected
* whether scenario/facility semantics could be affected

Do not perform a broad rewrite before understanding the current file responsibilities.

### Keep Changes Scoped

Keep changes scoped to the user request.

Do not combine unrelated work such as:

```text id="jtxg2d"
UI refactor + optimizer change + data migration + generated output update
```

unless the user explicitly asks for that combined change.

Prefer small, contract-preserving steps.

### Preserve V0 Unless Migration Is Explicit

The current Kadikoy parcel locker system should remain working unless the task explicitly asks to migrate it.

When introducing V1 concepts, prefer:

```text id="jjfw38"
add contract
add adapter
add compatibility path
then migrate
```

Do not silently break V0 runtime behavior.

### V1 Core Must Stay Generic

Use generic names in core architecture:

```text id="08pkz3"
facility
existingFacility
proposedFacility
scenario
candidate
objective
benchmark
```

Use parcel-locker-specific words only in:

* V0 implementation notes
* parcel-locker use-case labels
* legacy files
* UI text that is explicitly use-case-specific

Do not add new generic-core code that assumes every facility is a locker.

## Architecture Guardrails

Stop and ask before proceeding if a task could:

* violate candidate ID and distance matrix alignment
* treat `nearby_locker_count` as an existing facility
* reintroduce `locker_count > 0` as existing facility logic
* hard-code parcel locker assumptions into the generic V1 core
* move existing facilities into base grid CSV attributes as the only source of truth
* rewrite core optimizer architecture without a clear migration task
* mutate base data, raw data, archive data, or generated files outside the requested scope
* require long-running optimizer runs
* require staging or committing changes

## Data and Scenario Rules

### Candidate IDs

Candidate IDs are stable references across:

```text id="yu87tp"
candidate CSV
distance matrix
scenario facility snapping
optimizer chromosomes
benchmark reports
UI map rendering
```

Do not change candidate IDs or candidate ordering casually.

If candidate records are filtered, reordered, or regenerated, the distance matrix alignment must be rebuilt and validated.

### Existing Facilities

For V1, existing facilities should be explicit scenario entities.

Preferred direction:

```text id="asxk4g"
scenario.facilities[]
```

Avoid designing new V1 features where existing facilities only exist as static columns inside the base candidate CSV.

### `nearby_locker_count`

`nearby_locker_count` is context/proximity only.

Never use:

```text id="k1tdtt"
nearby_locker_count > 0
```

to infer existing facility presence.

### `existing_locker_count`

`existing_locker_count` is a V0 Kadikoy mapped physical existing locker count.

It may be used to seed or validate a default parcel-locker scenario, but it should not become the long-term V1 source of truth for editable existing locations.

### Generated and Archive Files

Do not edit these casually:

```text id="xno8vw"
output/
parcel-locker-ui/.next/
parcel-locker-ui/public/mock/
data/archive/
data/raw/
docs/archive/
scripts/archive/
sections/figures/final_results/
target/
```

If the task explicitly requires generated files, state that clearly in the report.

## Command Rules

### Do Not Run Unless Explicitly Asked

Do not run these unless the user explicitly asks:

```bash id="04wtae"
mvn -q compile exec:java
mvn -q compile exec:java -Panalyze
npm run dev
docker compose up --build
python3 scripts/prepare_demand.py
python3 data/prepare_ga_inputs.py
python3 data/prepare_ga_inputs.py --filter_forbidden
```

Avoid long optimizer runs, high-K experiments, full parameter analysis, and UI dev servers unless explicitly requested.

### Usually Safe Lightweight Checks

When relevant and not forbidden, these may be used after code changes:

```bash id="5jv2kd"
mvn -q compile
```

```bash id="xuqmrr"
cd parcel-locker-ui
npm run lint
```

For documentation-only tasks, do not run code validation.

### Data-Mutating Commands

These commands may overwrite or regenerate important artifacts:

```bash id="syrtrb"
python3 scripts/prepare_demand.py
python3 data/prepare_ga_inputs.py
python3 scripts/plot_archives.py
python3 parcel-locker-ui/src/scripts/process_ga_data.py
```

Run them only when the user explicitly wants regenerated data or generated outputs.

## Editing Strategy

### For Documentation Tasks

* Do not rewrite everything if a targeted update is enough.
* Preserve useful V0 documentation.
* Mark old V0 behavior clearly when it is superseded by V1 contracts.
* Avoid adding speculative implementation details as if they are already built.

### For Code Tasks

* Identify the contract first.
* Find the smallest implementation path.
* Avoid duplicating optimizer logic outside Java.
* Keep UI features connected to scenario/objective/benchmark contracts.
* Do not create UI-only demo state that cannot later serialize into scenario data.
* Preserve compatibility unless the user asks for migration.

### For Refactor Tasks

Before changing code, provide or follow a migration sequence:

```text id="f07qzl"
1. current behavior
2. target behavior
3. compatibility plan
4. files to change
5. validation plan
6. rollback risk
```

Do not perform a big-bang refactor without explicit approval.

## Reporting Format

After changes, report:

```text id="vt3g7s"
1. Files created
2. Files updated
3. What changed
4. Key decisions
5. Assumptions made
6. Validation performed or intentionally skipped
7. Final git diff --name-status
```

If no validation was run, explain why.

Example:

```text id="p476n7"
Validation skipped because this was a documentation-only change.
```

If no files were changed, report:

```text id="5w4mgq"
No files changed.
```

## When to Ask Before Editing

Ask before editing if:

* the task is ambiguous
* multiple architecture paths are possible
* generated or raw data would need to change
* a long optimizer run seems necessary
* V0 behavior may break
* V1 contracts conflict with existing implementation
* the change would require deleting or moving many files
* the task might require commit/stage operations

## Current First V1 Milestone

The first major V1 milestone is:

```text id="h7vnxf"
Generic Facility + Scenario System
```

This milestone means:

* existing locations become editable scenario entities
* users can import existing facilities
* users can manually add, remove, disable, and edit facilities
* facilities can be snapped to candidate IDs
* existing ON/OFF becomes scenario state
* optimizer inputs can be derived from scenario state
* current-vs-optimized comparisons become scenario-based
* core code moves away from parcel-locker-specific assumptions

Do not jump directly into isolated objective or UI features if they still rely on parcel-locker-specific existing-location logic.

## Final Reminder

Every change should support the product spine:

```text id="q6mtjb"
grid data
  -> scenario facilities
  -> modular objectives
  -> optimization
  -> benchmark reporting
  -> map sandbox
```
