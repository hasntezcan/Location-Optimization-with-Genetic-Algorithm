# Location Optimization with Genetic Algorithm

This repository currently contains the **V0 Kadikoy parcel locker optimization system** and is evolving toward **V1: a generic grid-based location optimization platform**.

The current implementation solves a bi-objective parcel locker location optimization problem for Kadikoy by selecting facility locations from a prepared candidate grid. The V1 direction generalizes this into a platform that can support multiple location-planning use cases such as parcel lockers, food deserts, fire stations, police coverage, municipal service points, health access, and logistics networks.

## Current Status

### V0: Current Working System

The current working system is the Kadikoy parcel locker use case.

It includes:

* Java SPEA2-based multi-objective genetic algorithm.
* Candidate grid and distance matrix inputs.
* Demand and POI preparation scripts.
* Archive and benchmark output generation.
* Next.js dashboard for map-based result exploration.
* Local/dev API route that can trigger Java optimization from the UI.

Current optimization objectives:

* `f1`: accessibility cost.
* `f2`: neighborhood equity cost.

Both objectives are minimized.

### V1: Target Direction

V1 turns the project into a generic location optimization platform.

Core V1 concepts:

* **Grid / Candidate**: stable spatial decision unit.
* **Facility**: existing or proposed service location.
* **Scenario**: editable planning context containing facilities, constraints, locks, objectives, and run settings.
* **Objective**: modular scoring function used by the optimizer.
* **Benchmark**: current-vs-optimized and scenario-vs-scenario comparison.
* **Map Sandbox**: interactive planning canvas, not only a result viewer.

The current Kadikoy parcel locker system remains the technical baseline while the V1 contracts are introduced.

## Start Here

For AI agents, contributors, and future development work, read these first:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/V1_ARCHITECTURE.md`](docs/V1_ARCHITECTURE.md)
3. [`docs/V1_DATA_CONTRACT.md`](docs/V1_DATA_CONTRACT.md)
4. [`docs/V1_SCENARIO_CONTRACT.md`](docs/V1_SCENARIO_CONTRACT.md)
5. [`docs/V1_OBJECTIVE_CONTRACT.md`](docs/V1_OBJECTIVE_CONTRACT.md)
6. [`docs/V1_BENCHMARKING.md`](docs/V1_BENCHMARKING.md)
7. [`docs/V1_MAP_UI_STRATEGY.md`](docs/V1_MAP_UI_STRATEGY.md)
8. [`docs/V1_ROADMAP.md`](docs/V1_ROADMAP.md)
9. [`docs/REPO_STRUCTURE.md`](docs/REPO_STRUCTURE.md)

For archived V0 implementation history, use:

* [`docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`](docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md)

This file is historical reference only. V1 architecture and current development direction are defined by `AGENTS.md` and the `docs/V1_*` files listed above.

For Claude Code specifically:

* [`CLAUDE.md`](CLAUDE.md)

## Important Development Contracts

These contracts must be protected during development:

* Candidate IDs are the stable reference across data, matrix, optimizer output, scenario data, and UI.
* The distance matrix row and column order must remain aligned with candidate IDs in ascending order.
* `nearby_locker_count` is proximity/context only. It must not be treated as an existing facility signal.
* `existing_locker_count` is the mapped physical existing locker count in the current Kadikoy V0 data, but V1 should move existing facilities into scenario data.
* Existing facilities should become explicit scenario entities, not hidden assumptions inside the base candidate CSV.
* Java SPEA2 is currently the authoritative optimization engine.
* Generated files should not be hand-edited unless the task explicitly requires it.

## Repository Overview

Main areas:

* `src/main/java`: Java SPEA2 optimizer, models, loaders, services, and app entry points.
* `scripts`: Python data preparation, plotting, validation, benchmark, and research scripts.
* `data`: candidate CSV, distance matrix, raw GIS/provenance files, and matrix alignment artifacts.
* `parcel-locker-ui`: Next.js dashboard and local/dev UI integration.
* `docs`: current V1 documentation, deployment notes, repository structure, and archived V0 references under `docs/archive`.
* `output`: generated optimizer outputs, plots, reports, and metadata.

For a detailed explanation of source, generated, archive, research, and validation folders, see:

* [`docs/REPO_STRUCTURE.md`](docs/REPO_STRUCTURE.md)

## Requirements

* Java 17
* Maven
* Python 3
* Python dependencies from `requirements.txt`
* Node.js and npm for the Next.js dashboard

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Main Runtime Inputs

Current V0 runtime inputs:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
```

Supporting matrix alignment artifacts:

```text
data/kadikoy_candidate_ids_sorted.npy
data/kadikoy_index_map.csv
data/kadikoy_ARTIFACTS_GUIDE.md
```

Important:

* Do not reorder candidate rows or modify candidate IDs casually.
* If the candidate set or coordinates change, regenerate and validate the distance matrix artifacts.
* Keep forbidden candidates in the base candidate set unless the whole runtime contract is intentionally migrated.

## Quick Start: Current V0 Java Optimizer

Compile Java:

```bash
mvn -q compile
```

Run the default Java SPEA2 optimizer:

```bash
mvn -q compile exec:java
```

This writes outputs under `output/`.

Default outputs:

```text
output/initial_archive.csv
output/final_archive.csv
output/run_metadata.json
```

Generate archive comparison plot:

```bash
python3 scripts/plot_archives.py
```

This writes:

```text
output/archive_comparison_latest.png
```

## Demand Preparation

The current committed candidate CSV already contains `poi_score` and `demand_final`.

Only rerun demand preparation when candidate data or demand assumptions change:

```bash
python3 scripts/prepare_demand.py
```

Warning:

```text
scripts/prepare_demand.py overwrites data/candidate_points.csv.
```

Use this carefully and keep backups when changing scientific demand assumptions.

## Distance Matrix Generation

Regenerate matrix artifacts only if the candidate set or candidate coordinates change:

```bash
python3 data/prepare_ga_inputs.py \
  --input_csv data/candidate_points.csv \
  --out_prefix data/kadikoy
```

Do not use forbidden filtering unless the runtime CSV is filtered in exactly the same way. Otherwise, matrix alignment will break.

## Hyperparameter Analysis

Parameter grid search is long-running.

Run only when explicitly needed:

```bash
mvn -q compile exec:java -Panalyze
```

Smoke check:

```bash
mvn -q compile exec:java -Panalyze -Dexec.args="--smoke"
```

Post-process parameter analysis:

```bash
python3 scripts/statistical_analysis.py
```

Generated files may include:

```text
output/parameter_analysis_results.csv
output/parameter_analysis_results_smoke.csv
output/ga_configuration_table.csv
output/statistics/
```

## UI: Next.js Dashboard

UI directory:

```text
parcel-locker-ui
```

Install and run locally:

```bash
cd parcel-locker-ui
npm install
npm run dev
```

The UI can:

* Visualize candidate points and optimized archive solutions.
* Explore Pareto solutions.
* Run MCDA selection over Pareto solutions.
* Trigger the Java optimizer locally through `/api/run-ga`.
* Refresh generated UI mock assets.

Current UI generated/mock files:

```text
parcel-locker-ui/public/mock/candidate-points.json
parcel-locker-ui/public/mock/ga-results.json
parcel-locker-ui/public/mock/archive_comparison_latest.png
parcel-locker-ui/public/mock/kadikoy_boundary.geojson
```

Treat these as generated UI assets unless a task explicitly targets them.

## Local / Container Deployment

The current deployment model is a local/single-user development architecture.

The Next.js API route runs Maven, waits for Java, runs Python post-processing, and refreshes generated UI mock files.

See:

* [`docs/DEPLOYMENT_PHASE1.md`](docs/DEPLOYMENT_PHASE1.md)

Docker Compose:

```bash
docker compose up --build
```

Important Phase 1 limitations:

* `/api/run-ga` keeps one request open until Java and Python finish.
* Outputs are shared files, not run-ID-isolated.
* Concurrent runs are not safe.
* This is not suitable for Vercel-only deployment.
* Production deployment needs job IDs, run history, result endpoints, run-specific output folders, and concurrency control.

## Generated and Archive Areas

Do not hand-edit these casually:

* `output`
* `parcel-locker-ui/.next`
* `parcel-locker-ui/public/mock`
* `data/archive`
* `scripts/archive`
* `docs/archive`
* `sections/figures/final_results`

Use [`docs/REPO_STRUCTURE.md`](docs/REPO_STRUCTURE.md) before modifying unfamiliar folders.

## Current V1 Development Priority

The first major V1 milestone is:

```text
Generic Facility + Scenario System
```

This means:

* Existing locations become editable scenario entities.
* Users can import, add, remove, disable, and edit facilities.
* Facilities can be snapped to candidate IDs.
* Existing ON/OFF becomes scenario state.
* Current-vs-optimized comparisons become scenario-based.
* Core code should move away from parcel-locker-specific assumptions.

The long-term V1 direction is:

```text
grid data + scenario facilities + modular objectives + optimization + benchmarking + map sandbox
```

## Notes for AI Agents

Before editing this repository:

1. Read [`AGENTS.md`](AGENTS.md).
2. Read the relevant V1 docs for the task.
3. Do not run long optimizer jobs unless explicitly requested.
4. Do not run `npm run dev` unless explicitly requested.
5. Do not stage or commit unless explicitly requested.
6. Preserve V0 behavior unless the task explicitly asks for migration.
7. Do not reintroduce parcel-locker-specific logic into the generic V1 core.

After changes, report:

```text
1. Files created
2. Files updated
3. Key decisions documented
4. Assumptions made
5. Validation performed or intentionally skipped
6. Final git diff --name-status
```
