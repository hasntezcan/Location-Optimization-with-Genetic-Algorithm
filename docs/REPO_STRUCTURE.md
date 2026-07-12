# Repository Structure

This file describes the current repository layout for humans and AI agents. It is a static guide, not a generated tree.

## Root Files

- `readme.md`: quick-start guide for the current project.
- `AGENTS.md`: first-read operating guide for AI agents.
- `CLAUDE.md`: Claude Code specific operating guide.
- `pom.xml`: Java Maven configuration for the optimizer.
- `requirements.txt`: Python dependency list for scripts.
- `Dockerfile`, `docker-compose.yml`: local/container deployment artifacts.

## Source Folders

- `src/main/java`: Java SPEA2 optimizer, models, loaders, configuration, and app entry points.
- `parcel-locker-ui/src`: Next.js UI, dashboard components, local API route, and UI helper libraries.
- `parcel-locker-ui/src/scripts`: Python scripts used by the UI pipeline to convert optimizer outputs into UI-readable artifacts.
- `python/src/location_platform`: reusable Python package (scenario validation/seeding/optimizer-input derivation, current-network benchmark). See "Python Package" below.
- `scripts`: Python analysis, demand preparation, plotting, validation, and research scripts. `scripts/scenario/*.py` and `scripts/validation/benchmark_existing_vs_optimized.py` are thin wrappers over `python/src/location_platform`; other top-level scripts are not yet migrated.
- `data/prepare_ga_inputs.py`: data preparation entry point for candidate and matrix artifacts.

## Data Folders

- `data/candidate_points.csv`: current V0 runtime candidate source.
- `data/kadikoy_distance_meters_nxn.npy`: current V0 runtime distance matrix.
- `data/kadikoy_candidate_ids_sorted.npy`, `data/kadikoy_index_map.csv`: matrix and candidate alignment support artifacts.
- `data/raw`: provenance and raw source material. Treat as source evidence, not routine runtime state.
- `data/archive`: backups and historical data artifacts. Do not edit casually.

## Documentation Folders

- `docs`: current V1 documentation, deployment notes, and repository structure.
- `docs/archive`: older and archived reference material.
- `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`: archived V0 technical guide for the Kadikoy parcel locker implementation. Use only for historical implementation details; it is not authoritative for V1 architecture.
- `docs/DEPLOYMENT_PHASE1.md`: deployment notes for the current local/container architecture.

## Generated Folders and Files

- `output`: generated optimizer archives, plots, run metadata, and benchmark artifacts. Do not edit by hand unless explicitly requested.
- `parcel-locker-ui/.next`: generated Next.js build/dev output. Do not edit.
- `parcel-locker-ui/public/mock`: generated or copied UI data used by the dashboard. Treat as generated unless the task explicitly targets UI mock data.
- `target`: Maven build output if present. Do not edit.

## Legacy, Archive, and Research Areas

- `backup`: previously held experimental/older Java code (`(experimental)Main.java`); deleted as a confirmed-dead Tier 1 cleanup item (Phase 1G2). Git does not track empty directories, so `backup/` no longer exists in the current repository structure.
- `scripts/archive`: legacy and one-off scripts. Use as reference before copying patterns into active code.
- `scripts/archive/one_off`: one-time analysis utilities.
- `scripts/archive/legacy`: legacy scripts retained for provenance.
- `scripts/research`: research-specific scripts for report questions and figures.
- `scripts/validation`: validation and benchmark scripts.
- `sections/figures/final_results`: research/report figures and summaries.

## What Agents Should Not Touch Casually

- Do not edit `.next`.
- Do not hand-edit `output`.
- Do not mutate `data/raw` provenance files.
- Do not rewrite `data/archive`.
- Do not modify candidate IDs or reorder candidate rows without also rebuilding and validating distance matrix alignment.
- Do not infer existing facilities from `nearby_locker_count`.
- Do not reintroduce `locker_count > 0` as existing facility logic.
- Do not stage or commit unless explicitly asked.

## Current Runtime Path

```text
Next.js UI
  -> /api/run-ga
  -> parcel-locker-ui/src/lib/server/ga-runner.ts
  -> Maven / Java app.Main
  -> output archives and run metadata
  -> scripts/plot_archives.py
  -> parcel-locker-ui/src/scripts/process_ga_data.py
  -> parcel-locker-ui/public/mock
  -> dashboard and map views
```

This remains the exact path for requests without a `scenarioPath`. A second, optional path now also exists: a request that includes `scenarioPath` is routed through `parcel-locker-ui/src/lib/server/scenario-adapter.ts`, which invokes `scripts/scenario/derive_optimizer_inputs.py` to derive `k`/`fixedFacilityIds` from `data/scenarios/*.json` before continuing through the same Maven/Java/plot/process steps above (or skipping Java entirely for a `current_network` scenario). This scenario path is an explicitly **temporary** compatibility bridge, not a permanent second architecture — see `docs/ARCHITECTURE_AUDIT.md` for the full current-vs-scenario runtime diagram and `docs/PHASE_0_REPO_CLEANUP_PLAN.md` for the plan to move the reusable logic behind it into a proper Python package.

The V1 architecture should generalize this path over time, but current work should respect the existing V0 contracts unless a migration task explicitly changes them.

## Python Package (`python/src/location_platform/`)

`docs/PHASE_0_REPO_CLEANUP_PLAN.md` (Phase 0B) approved this target Python package layout, and **Phases 1A–1F implemented it.** This exists now:

```text
python/
├── pyproject.toml
├── src/
│   └── location_platform/
│       ├── common/         (parsing.py, paths.py)
│       ├── data/           (candidates.py, matrix.py)
│       ├── scenario/       (loading.py, validation.py, seed.py, optimizer_inputs.py)
│       └── benchmark/      (current_network.py, evaluation.py, reporting.py)
└── tests/                  (one test module per package module above)
```

`location_platform.spatial` and `location_platform.orchestration` remain reserved names for a possible later phase (facility import/snapping, and FastAPI/worker orchestration respectively) — they are still not created, per the Anti-Overengineering Rule (no module without at least two real consumers).

**Policy now in effect:**

```text
scripts/                             = executable entrypoints and compatibility wrappers only
python/src/location_platform/        = reusable Python product logic
```

Concretely: `scripts/scenario/generate_default_current_network_scenario.py`, `scripts/scenario/validate_scenario.py`, `scripts/scenario/derive_optimizer_inputs.py`, and `scripts/validation/benchmark_existing_vs_optimized.py` are now thin wrappers — they parse arguments, call into `location_platform`, and print/exit. The actual logic lives in the package modules listed above. **The file paths did not change** (the hard backward-compatibility requirement this migration was built around — Next.js's `scenario-adapter.ts`/`runtime-config.ts` and documented CLI commands still point at these exact same script paths). Other top-level `scripts/*.py` files (`prepare_demand.py`, `calculate_poi_weights.py`, `prepare_candidate_existing_lockers.py`, `plot_archives.py`, `statistical_analysis.py`) have **not** been migrated — they remain standalone scripts, per `docs/ARCHITECTURE_AUDIT.md`'s P1 finding.

**Verification status:** this migration has been checked only by static inspection (reading the package/wrapper code, `rg`/`git grep` reference checks) — no `pytest` run, no CLI execution against real data has been performed as part of the migration itself. See `docs/PHASE_0_REPO_CLEANUP_PLAN.md` for the exact target modules, public APIs, and migration order, and `docs/V1_ROADMAP.md` for the pending manual validation checklist.
