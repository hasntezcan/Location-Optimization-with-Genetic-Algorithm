# V1 Tech Stack

## Purpose

This document defines the target technical stack for the V1 location optimization platform.

The goal is to move from a research/prototype-style structure into a cleaner product architecture where each technology has a clear responsibility.

Current V0 stack should remain usable during migration, but future work should move toward the target architecture described here.

## Current Stack

The current project uses:

```text
Java        -> SPEA2 optimizer
Python      -> data preparation, validation, benchmark, plotting, scripts
Next.js     -> UI, dashboard, local API route
CSV/JSON    -> candidate data, scenario data, generated outputs
NumPy files -> distance matrix
```

This stack worked well for the academic Kadikoy parcel locker project.

However, as the project becomes a real generic location optimization platform, responsibilities need to be separated more clearly.

## Target Architecture Summary

```text
Next.js UI
  -> FastAPI backend
  -> Python platform package
  -> Java optimizer engine
  -> PostgreSQL/PostGIS
  -> Worker queue for long-running jobs
  -> Run-specific outputs and reports
```

## Core Technology Decisions

| Layer                        | Technology                   | Role                                                           |
| ---------------------------- | ---------------------------- | -------------------------------------------------------------- |
| Frontend                     | Next.js + TypeScript         | Map UI, scenario editor, dashboard, report viewer              |
| Map UI                       | Leaflet initially            | Scenario editing and basic map layers                          |
| Future Map Engine            | MapLibre + deck.gl if needed | High-performance layers, heatmaps, large data rendering        |
| Backend API                  | FastAPI                      | Scenario API, validation API, benchmark API, run orchestration |
| Data/Scenario/Benchmark Core | Python package               | Reusable platform logic                                        |
| Optimizer                    | Java SPEA2                   | Authoritative optimization engine for now                      |
| Database                     | PostgreSQL + PostGIS         | Scenarios, facilities, grids, layers, runs, reports            |
| Long-running Jobs            | RQ + Redis initially         | Optimizer runs, heavy imports, benchmark jobs                  |
| Deployment                   | Docker Compose initially     | Local/dev multi-service setup                                  |

## Responsibility Boundaries

## Next.js

Next.js should own the user-facing product experience.

Responsibilities:

* Map interface.
* Scenario editor.
* Dashboard.
* Benchmark and report viewer.
* API client.
* User interactions such as add, disable, edit, and compare facilities.

Next.js should not own:

* long-running optimizer execution,
* Maven or Java process orchestration,
* heavy benchmark computation,
* spatial data processing,
* distance matrix generation,
* shared output file management.

**Current exception, explicitly temporary:** `/api/run-ga` can optionally accept a `scenarioPath` and, via `parcel-locker-ui/src/lib/server/scenario-adapter.ts`, invoke a Python scenario-to-optimizer-input adapter (`scripts/scenario/derive_optimizer_inputs.py`) before continuing the existing Maven/Java orchestration. This is a stopgap compatibility bridge (see `docs/PHASE_0_REPO_CLEANUP_PLAN.md`), not a case for Next.js taking on scenario/benchmark logic long-term — that responsibility still belongs to FastAPI + the Python package once they exist.

## FastAPI

FastAPI should become the backend API layer.

Responsibilities:

* Scenario CRUD.
* Facility import endpoints.
* Scenario validation endpoints.
* Benchmark request endpoints.
* Run creation and job status endpoints.
* Communication with workers.
* Reading/writing database records.
* Returning structured results to the UI.

FastAPI should not directly run long optimizer jobs inside a normal request in production.

## Python Platform Package

Python logic should move from many standalone scripts into a reusable internal package.

> **Approved layout update (Phase 0B, see `docs/PHASE_0_REPO_CLEANUP_PLAN.md`):** the package lives under a top-level `python/` folder (`python/pyproject.toml`, `python/src/location_platform/`, `python/tests/` — "Option A"), not directly at the repo root as sketched below. The illustrative submodule list below (`data`, `scenario`, `benchmark`, `spatial`, `jobs`) is directional, not a guarantee — Phase 0C2's Anti-Overengineering Rule specifically defers `spatial`/`jobs`-style orchestration modules until a real consumer exists. **Update (Phase 1A–1F, implemented):** `python/` now exists with `common`, `data`, `scenario`, and `benchmark` populated (`spatial`/`jobs` remain deferred, per the Anti-Overengineering Rule). `scripts/scenario/*.py` and `scripts/validation/benchmark_existing_vs_optimized.py` are thin wrappers over it. This has been verified only by static inspection so far (Phase 1G audit) — see `docs/V1_ROADMAP.md`'s "Manual Validation Still Required" section before treating it as runtime-proven.

Target structure:

```text
location_platform/
  data/
    candidates.py
    matrix.py
    layers.py

  scenario/
    io.py
    validation.py
    seed.py
    snapping.py
    editing.py

  benchmark/
    current_network.py
    archive_comparison.py
    metrics.py
    reporting.py

  spatial/
    crs.py
    joins.py
    coverage.py

  jobs/
    run_optimizer.py
    run_benchmark.py
```

The `scripts/` folder should contain thin CLI wrappers only.

Example:

```text
scripts/scenario_cli.py
scripts/benchmark_cli.py
```

The real logic should live under `location_platform/`.

## Java Optimizer

Java SPEA2 should remain the authoritative optimizer engine for now.

Responsibilities:

* Optimization algorithm.
* SPEA2 execution.
* Pareto archive generation.
* Objective evaluation while V0/V1 transition is ongoing.

Java should not own:

* scenario editing,
* CSV/GIS import,
* map logic,
* business benchmark reporting,
* UI-specific formatting,
* long-term scenario storage.

Short-term integration:

```text
FastAPI / Worker
  -> calls Java optimizer as CLI or JAR
  -> reads run outputs
  -> stores run metadata and benchmark results
```

Long-term option:

* Keep Java optimizer if stable and performant.
* Only consider rewriting optimizer logic if Java becomes a maintenance bottleneck.

Do not rewrite the optimizer just to simplify the stack.

## PostgreSQL + PostGIS

A real product should not rely only on CSV and JSON files.

PostgreSQL/PostGIS should eventually store:

* users if needed,
* projects,
* scenarios,
* facilities,
* candidate grids,
* grid features,
* data layers,
* run metadata,
* benchmark outputs,
* saved reports,
* map layer metadata.

Initial migration can keep CSV/JSON files, but the target product should move toward database-backed scenario and run state.

## Worker Queue

Worker queue is for long-running or heavy tasks.

Normal API requests should be fast.

Examples of fast API tasks:

* save scenario,
* update facility status,
* fetch dashboard data,
* validate small JSON payload,
* list previous runs.

Examples of worker tasks:

* run Java SPEA2 optimizer,
* compute large benchmark comparisons,
* import and snap large CSV/GIS files,
* generate distance matrices,
* generate coverage layers,
* generate heatmaps,
* generate reports,
* process multiple scenarios.

Target flow:

```text
UI
  -> POST /runs
  -> FastAPI creates job_id
  -> Worker runs optimizer/benchmark
  -> Results saved to DB/output folder
  -> UI polls GET /runs/{job_id}
  -> UI fetches results when completed
```

Short-term:

* Worker queue is not required immediately.
* FastAPI can run small validation and benchmark tasks synchronously.

Medium-term:

* Optimizer runs should move to a queue.
* Run outputs should be isolated by `run_id`.

Long-term:

* All expensive jobs should be handled by workers.

Preferred initial queue:

```text
RQ + Redis
```

Reason:

* simpler than Celery,
* enough for early product architecture,
* easy to understand,
* suitable for optimizer and benchmark jobs.

Possible later queue:

```text
Celery + Redis/RabbitMQ
```

Use Celery only if job orchestration becomes more complex.

## Map Stack

The project should not switch map engines too early.

## Current / Near-Term

Use Leaflet.

Leaflet is enough for:

* showing candidate points,
* showing existing facilities,
* showing proposed facilities,
* adding facilities by click,
* disabling facilities,
* simple scenario layers,
* current vs optimized visualization.

## Future

Evaluate MapLibre + deck.gl only when needed for:

* large point/polygon datasets,
* GPU heatmaps,
* smooth scenario comparison layers,
* coverage surfaces,
* high-performance vector styling,
* many simultaneous map layers.

Decision:

```text
Do not migrate away from Leaflet just for aesthetics.
First make scenario state correct.
Then evaluate map modernization.
```

## File and Output Strategy

Current V0 uses shared outputs such as:

```text
output/final_archive.csv
output/run_metadata.json
```

This is acceptable for local research, but not for production.

Target V1 should use run-specific outputs:

```text
output/runs/<run_id>/
  scenario.json
  run_metadata.json
  final_archive.csv
  benchmark_summary.json
  benchmark_report.md
  map_layers/
```

This prevents:

* output overwrites,
* concurrent run conflicts,
* unclear benchmark provenance,
* mixed scenario results.

## Development Phases

## Phase 1: Current Local V1 Migration

Keep:

* Next.js UI,
* Java optimizer,
* Python scripts,
* file-based scenario JSON,
* file-based benchmark output.

Add:

* scenario JSON,
* scenario validator,
* scenario-based benchmark,
* reusable Python package foundation.

Do not add database or queue yet unless needed.

## Phase 2: Python Package Cleanup

Move logic from standalone scripts into:

```text
location_platform/
```

Keep scripts as CLI wrappers.

Goal:

```text
scripts are entrypoints,
location_platform is the product logic.
```

## Phase 3: FastAPI Backend

Add FastAPI as the backend service.

Move API responsibilities out of Next.js API routes.

FastAPI should expose endpoints such as:

```text
GET  /health
POST /scenarios
GET  /scenarios/{id}
POST /scenarios/{id}/validate
POST /runs
GET  /runs/{id}
GET  /runs/{id}/results
POST /imports/facilities
```

## Phase 4: Run Isolation

Introduce:

* `run_id`,
* run-specific output folders,
* run metadata,
* scenario snapshot per run,
* benchmark snapshot per run.

This should happen before multi-user behavior.

## Phase 5: Worker Queue

Move long-running jobs to workers:

* optimizer run,
* heavy benchmark,
* CSV/GIS import,
* coverage layer generation,
* report generation.

Use:

```text
RQ + Redis
```

unless the project clearly needs Celery-level complexity.

## Phase 6: Database

Introduce PostgreSQL/PostGIS for:

* scenarios,
* facilities,
* candidate grids,
* data layers,
* runs,
* reports.

JSON files can remain useful for import/export, but should not be the only product state.

## Phase 7: Map Modernization Evaluation

Only after scenario editing and run management are stable, evaluate whether Leaflet should remain or MapLibre/deck.gl should be introduced.

## Recommended Target Repo Shape

> **See the approved-layout note above:** `location_platform/` below should be read as `python/src/location_platform/` per Phase 0B's Option A decision, and `spatial/`/`jobs/` are reserved, not guaranteed, submodules.

```text
repo/
  location_platform/
    data/
    scenario/
    benchmark/
    spatial/
    jobs/

  scripts/
    scenario_cli.py
    benchmark_cli.py
    data_cli.py

  src/main/java/
    app/
    algorithm/
    model/
    service/

  parcel-locker-ui/
    src/
      app/
      components/
      features/
      lib/

  api/
    app/
      main.py
      routes/
      services/

  data/
    candidate_points.csv
    kadikoy_distance_meters_nxn.npy
    scenarios/

  output/
    runs/

  docs/
    V1_ARCHITECTURE.md
    V1_DATA_CONTRACT.md
    V1_SCENARIO_CONTRACT.md
    V1_OBJECTIVE_CONTRACT.md
    V1_BENCHMARKING.md
    V1_MAP_UI_STRATEGY.md
    V1_ROADMAP.md
    V1_TECH_STACK.md
```

This shape can evolve gradually.

Do not attempt a big-bang migration.

## Key Product Rule

Technology should follow responsibility boundaries.

Bad pattern:

```text
Next.js API route runs Maven, Python scripts, writes shared files, and blocks until everything finishes.
```

Better pattern:

```text
Next.js UI
  -> FastAPI API
  -> queue job
  -> worker runs optimizer/benchmark
  -> results stored by run_id
  -> UI displays completed results
```

## What Should Happen Next

Immediate next steps:

1. Keep current V0 behavior working. [ONGOING — V0 CLI paths and Java `--includeExistingLockers` flow unchanged]
2. Create `location_platform/` package. [DONE — `python/src/location_platform/`]
3. Move scenario validation logic into reusable module. [DONE — `location_platform.scenario.validation`]
4. Move scenario seed logic into reusable module. [DONE — `location_platform.scenario.seed`]
5. Move current-network benchmark logic into reusable module. [DONE — `location_platform.benchmark.current_network`/`.evaluation`/`.reporting`]
6. Keep existing scripts as compatibility wrappers. [DONE — all four scenario/benchmark scripts are now thin wrappers at their original paths]
7. Add tests or static validation for scenario and benchmark logic. [DONE — `python/tests/`; written and statically reviewed, **not yet executed** — see `docs/V1_ROADMAP.md`'s "Manual Validation Still Required"]
8. Only then move toward FastAPI. [NOT STARTED — correctly deferred; also blocked on manual validation of steps 2–7 passing first]

## Final Decision

The current stack is not wrong.

The problem is not Java + Python + Next.js.

The problem is unclear responsibility boundaries.

The target V1 stack should be:

```text
Next.js = UI
FastAPI = backend API
Python package = data, scenario, benchmark, spatial logic
Java = optimizer engine
PostgreSQL/PostGIS = persistent spatial/product data
RQ/Redis = long-running jobs
Leaflet now, MapLibre/deck.gl later if needed
```

This keeps the working optimizer, uses Python where spatial/data logic is strongest, keeps the UI modern, and gives the project a realistic path toward a product-grade architecture.
