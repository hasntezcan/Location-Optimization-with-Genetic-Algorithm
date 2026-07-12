# Phase 0 — Architecture Audit and Repository Cleanup

> **Update (Phase 1G2 — Tier 1 Cleanup, dated after this document was written):** the following paths referenced below as existing repository contents have since been deleted as confirmed-dead Tier 1 cleanup items: `.graphify-codeonly/`, `graphify-out/`, `parcel-locker-ui/src/scripts/build_candidate_json.py`, `scripts/guide.md`, `src/main/java/SRC_GUIDE.MD`, `src/main/java/analyse_guide.md`, `src/main/java/app/backend_guide.md`, and `backup/(experimental)Main.java`. The inventory tables below (Folder Classification, Active Python Script Inventory, Current Source/Runtime/Generated/Raw/Archive Boundaries) are a frozen Phase 0A snapshot and are intentionally **not** rewritten to remove these rows — treat any mention of the paths above in the tables below as historical record, not current disk state. See `docs/V1_ROADMAP.md`'s "Manual Validation Still Required" section and this repo's Tier 2/3 cleanup candidates (still explicitly deferred, not evaluated as safe) for what remains open.

## Phase 0A Objective

Phase 0A is a discovery and inventory pass only. It records, with evidence from the repository as it stands today, what currently exists, how it currently runs, and where the known problems are — without deciding a target folder structure, without a migration map, and without moving or renaming anything. Phase 0B will make the target-structure decision using this inventory; Phase 0C will execute a migration plan. No runtime, application, data, or generated file was changed to produce this document.

## Current Change Inventory

All currently modified/untracked items in `git status --short`, classified:

| Path | Git state | Classification | Notes |
| --- | --- | --- | --- |
| `.gitignore` | Modified | Pre-existing unrelated change | Predates this session's work; adds `graphify-out/` and `.graphify-codeonly/` ignore entries. Not touched by any scenario/adapter task. |
| `.graphifyignore` | Untracked | Graphify/tooling | Code-only Graphify scan config, created in an earlier discovery-tooling task. Not part of product architecture. |
| `docs/ARCHITECTURE_AUDIT.md` | Untracked | Documentation | Full architecture audit produced earlier this session; documents the same P0 gap (scenario not wired to optimizer) that the scenario-adapter and runtime-bridge work below then closed. |
| `docs/V1_TECH_STACK.md` | Untracked | Documentation | Pre-existing V1 doc (present on disk, not yet committed); defines the target stack (Next.js/FastAPI/Python package/Java/Postgres/RQ) referenced throughout this inventory. |
| `scripts/scenario/derive_optimizer_inputs.py` | Untracked | Scenario adapter | New: translates `scenario.facilities[]`/`settings`/`constraints` into Java-CLI-compatible `k`/`fixedFacilityIds`. Never reads `nearby_locker_count`; never reads `existing_locker_count`. |
| `scripts/validation/benchmark_existing_vs_optimized.py` | Modified | Benchmark | Predates the adapter work (already scenario-aware before this session started); the diff on disk reflects the "Existing Locker Integration" commit, not new work from this task chain. |
| `parcel-locker-ui/src/lib/server/scenario-adapter.ts` | Untracked | Scenario runtime bridge | New: repository-relative path-safety validation (`resolveScenarioPath`) + typed invocation of `derive_optimizer_inputs.py` from Node. |
| `parcel-locker-ui/src/lib/server/ga-runner.ts` | Modified | Scenario runtime bridge | Adds an optional scenario-resolution branch ahead of the existing Java/plot/process pipeline; V0 behavior (no `scenarioPath`) is unchanged. |
| `parcel-locker-ui/src/lib/server/runtime-config.ts` | Modified | Scenario runtime bridge | Adds `scenarioAdapterScriptPath` and `scenariosDir` to the existing config object; no other fields changed. |
| `parcel-locker-ui/src/app/api/run-ga/route.ts` | Modified | Scenario runtime bridge | Adds validation for `scenarioPath`/`forceExistingOff`/`targetTotalFacilityCount`; only relaxes the `k` requirement when `scenarioPath` is present. |

No item in this inventory falls into "unknown/requires review" — every current change traces to a specific, already-reported prior task in this session.

## Current Runtime Architecture

### V0 Runtime Path

This path runs whenever the request body has no `scenarioPath`. It is byte-identical to the pre-scenario-work behavior.

```text
UI (dashboard components, e.g. control-panel.tsx)
  -> POST /api/run-ga  { k, fixedFacilityIds?, includeExistingLockers?, ... }
  -> parcel-locker-ui/src/app/api/run-ga/route.ts
       - validates k (1-30), fixedFacilityIds shape, includeExistingLockers type
  -> parcel-locker-ui/src/lib/server/ga-runner.ts : runGaPipeline()
       -> runJavaGa(): spawns `mvn compile exec:java -Dexec.args=...` synchronously,
          streaming stdout as Server-Sent Events for the whole run
       -> src/main/java/app/Main.java
            - reads data/candidate_points.csv, data/kadikoy_distance_meters_nxn.npy
            - if --includeExistingLockers: derives existing candidates directly from
              existing_locker_count via CandidateRepository (V0-only path)
            - writes output/initial_archive.csv, output/final_archive.csv,
              output/run_metadata.json (global, shared, overwritten every run)
       -> runPythonScript(scripts/plot_archives.py)
            - reads output/final_archive.csv -> writes output/archive_comparison_latest.png
       -> copies output/archive_comparison_latest.png -> parcel-locker-ui/public/mock/
       -> runPythonScript(parcel-locker-ui/src/scripts/process_ga_data.py)
            - reads output/*.csv -> writes parcel-locker-ui/public/mock/ga-results.json
  -> UI reads parcel-locker-ui/public/mock/* for map/dashboard rendering
```

Java remains the sole optimization authority throughout. Python is invoked twice, both times as a post-processing/conversion step (plotting, UI-JSON shaping), never as an optimizer. Outputs are global/shared files (`output/final_archive.csv`, `output/run_metadata.json`) — a run has no run ID and no isolated output folder; a second run overwrites the first.

### Scenario Compatibility Path

This path runs only when the request body includes `scenarioPath`. It was added as a **temporary backward-compatible compatibility bridge** — it does not replace the V0 path above, it sits in front of it.

```text
UI or manual request
  -> POST /api/run-ga  { scenarioPath, forceExistingOff?, targetTotalFacilityCount? }
  -> route.ts
       - validates scenarioPath is a non-empty string (deep path-safety check happens later)
       - validates forceExistingOff (boolean) / targetTotalFacilityCount (positive integer) if present
       - does NOT require k when scenarioPath is present
  -> ga-runner.ts : runGaPipeline()
       -> scenario-adapter.ts : resolveScenarioPath()
            - rejects absolute paths, `..` segments, and anything outside data/scenarios/
       -> scenario-adapter.ts : deriveOptimizerInputsFromScenario()
            -> runPythonScript(scripts/scenario/derive_optimizer_inputs.py,
                 --scenario <resolved path> --candidate-csv data/candidate_points.csv
                 [--force-existing-off] [--override-target-total-facility-count N])
                 - reads scenario JSON: facilities[], settings, constraints
                 - resolves activeExistingCandidateIds from scenario.facilities[]
                   (kind=existing, status=enabled, snap.snapStatus=snapped) —
                   NEVER from existing_locker_count or nearby_locker_count
                 - resolves lockedCandidateIds/disabledCandidateIds from constraints
                 - resolves k from targetNewFacilityCount (expansion) or
                   targetTotalFacilityCount (greenfield/same-count), minus fixed count
                 - returns JSON on stdout (parsed by scenario-adapter.ts)
       -> branch A: runType == "current_network" (or no k could be resolved)
            - sends a "Completed" SSE event with optimizerRunRequired: false and
              scenario counts (physicalFacilityCount, effectiveFacilityLocationCount,
              activeExistingCandidateCount, disabledCandidateCount, adapterWarnings)
            - Java/Maven is never invoked
       -> branch B: optimizer run required
            - overwrites k := derived k, fixedFacilityIds := effectiveFixedCandidateIds,
              includeExistingLockers := false (forced), then proceeds through the
              *same* runJavaGa() / plot_archives.py / process_ga_data.py steps as V0
            - after Java completes, mergeScenarioMetadataIntoRunMetadata() does a
              read-merge-write on output/run_metadata.json to add a `scenario` key
              (best-effort; logs and continues if the file is missing/unreadable)
```

Key architectural facts about this bridge:

- It reuses the V0 path's Java invocation, plotting, and UI-conversion steps verbatim once `k`/`fixedFacilityIds` are resolved — it does not duplicate or bypass them.
- `--includeExistingLockers` is never sent in scenario mode; scenario-derived existing/locked candidate IDs are folded into `--fixedFacilityIds` instead. This is the one behavioral difference from V0 at the Java-CLI-argument level, and it is intentional: it is what makes `scenario.facilities[]` (not `existing_locker_count`) the source of truth for a scenario-driven run.
- `constraints.disabledCandidateIds` is derived and reported (and surfaced in `adapterWarnings`) but is **not enforced** — Java's CLI has no flag to exclude a candidate from the selectable pool, only `--fixedFacilityIds` to force-include one. This is a known, explicitly out-of-scope gap, not an oversight.
- Global/shared output files (`output/final_archive.csv`, `output/run_metadata.json`) are unchanged in this path too; no run-ID isolation was introduced.
- This entire path exists to prove that scenario data *can* drive a real Java run without touching Java or duplicating optimizer logic in Python/TypeScript. It is documented here, per this task's instruction, as a temporary bridge — not a finished FastAPI-style backend boundary, and not the final V1 scenario-to-optimizer contract.

## Folder Classification

| Folder | Current role | Ownership/category | Important contents | Known side effects | Generated/source/raw/archive status | Current concern |
| --- | --- | --- | --- | --- | --- | --- |
| `src/main/java/` | SPEA2 optimizer engine | runtime source | `app/` (2 files: `Main.java`, `ParameterAnalyzer.java`), `algorithm/` (4) + `algorithm/helper/` (3), `config/` (1), `io/` (2), `model/` (3), `service/` (4) | Writes `output/*.csv`, `output/run_metadata.json` | source | Still V0/locker-coupled by design (matches current roadmap phase); no scenario-facing adapter inside Java itself. |
| `parcel-locker-ui/src/` | Next.js UI, dashboard, API route | runtime source | `app/api/run-ga/route.ts`, `components/dashboard/*` (11 files, locker-specific naming), `lib/*` (8 files: `ga-api.ts`, `mcda.ts`, `types.ts`, etc.) | Reads `public/mock/*`; triggers Java/Python via the API route | source | No scenario UI state yet (no `scenario.ts` in `lib/`) — expected, Phase 4 not started. |
| `parcel-locker-ui/src/lib/server/` | Server-only orchestration + scenario bridge | runtime source | `ga-runner.ts`, `runtime-config.ts`, `scenario-adapter.ts` (new) | Spawns Maven/Python child processes; merges scenario metadata into `run_metadata.json` | source | Owns long-running orchestration that `V1_TECH_STACK.md` says should move to FastAPI/worker queue; currently the single most Next.js-coupled piece of the runtime. |
| `parcel-locker-ui/src/scripts/` | Python scripts invoked by the UI pipeline | UI-adjacent conversion | `process_ga_data.py` (converts optimizer output to UI JSON), `build_candidate_json.py` (converts `public/mock/candidate_points.csv` to `candidate-points.json`) | Writes into `parcel-locker-ui/public/mock/` | source (scripts) / output they produce is generated | Two conversion scripts with overlapping purpose (both produce mock JSON from CSV); not yet inventoried together anywhere else. |
| `scripts/` (top level) | Mixed data-prep, plotting, stats scripts | mixed: reusable product logic + CLI/wrapper | `prepare_demand.py`, `calculate_poi_weights.py`, `prepare_candidate_existing_lockers.py`, `plot_archives.py`, `statistical_analysis.py` | See Python Script Inventory below | source | No naming/location convention separates "safe to rerun" from "mutates CSV in place" scripts. |
| `scripts/scenario/` | Scenario generation/validation/derivation | reusable product logic | `generate_default_current_network_scenario.py`, `validate_scenario.py`, `derive_optimizer_inputs.py` (new) | Reads/writes `data/scenarios/*.json`; reads `data/candidate_points.csv` (id column only, in the adapter) | source | Best-organized subfolder in the repo; no package (`__init__.py`) yet, so nothing here is importable as a module by another script. |
| `scripts/validation/` | Scenario-based benchmarking | benchmark/reporting | `benchmark_existing_vs_optimized.py` | Writes `output/validation/*` (global, not run-scoped) | source (script) / its output is generated | Only one benchmark type implemented (current-network vs. one archive); same-K/expansion/reduction types from `V1_BENCHMARKING.md` don't exist yet. |
| `scripts/research/` | Report-specific one-off analyses | research-only | `rq1_k5_baseline_analysis.py`, `rq1_k5_dumbbell_plot.py`, `rq3_k5_equity_accessibility_validation.py` | Read existing CSV/NPY only; self-documented as not touching Java/GA | source (research) | Explicitly self-scoped ("does NOT run Java/GA") in their own docstrings; low reuse priority, correctly separated from product scripts already. |
| `scripts/archive/` | Legacy/one-off scripts | archive/legacy | `legacy/`, `one_off/` subfolders | None (not run in current workflows) | archive | Already correctly isolated per `docs/REPO_STRUCTURE.md`; no action needed. |
| `data/` (root files) | V0 runtime candidate/matrix source | runtime input | `candidate_points.csv`, `kadikoy_distance_meters_nxn.npy`, `kadikoy_candidate_ids_sorted.npy`, `kadikoy_index_map.csv`, `kadikoy_ARTIFACTS_GUIDE.md`, `prepare_ga_inputs.py` | `prepare_ga_inputs.py` regenerates the matrix artifacts; `prepare_demand.py` (in `scripts/`) overwrites `candidate_points.csv` in place | runtime input (CSV/NPY) + source (the one script living here) | `existing_locker_count` still lives as a column on this CSV and is still read directly by Java (`CandidateRepository`) when `--includeExistingLockers` is used in the V0 path — matches documented V0-compatibility status, not a new problem. |
| `data/scenarios/` | V1 scenario JSON | scenario source | `kadikoy_parcel_locker_current_network.json` (one file) | Read by `validate_scenario.py`, `derive_optimizer_inputs.py`, `benchmark_existing_vs_optimized.py` | source (new, V1) | Only one scenario exists; no CSV/GIS import path for *new* facilities yet (only the V0-seed generation path). |
| `data/raw/` | Provenance/raw GIS/CSV sources | raw/provenance data | `.gpkg`, `.qgz`, `.geojson`, `existing_lockers_32635.csv`, etc. (not enumerated further per task's "avoid scanning data/raw/ contents" instruction) | None from current pipeline | raw/provenance | None new; correctly excluded from active workflows. |
| `data/archive/` | Backups/historical data artifacts | archive/legacy | `.qmd`, `.csv`, `.xls`/`.xlsx` backups (not enumerated further, per instruction to avoid scanning contents) | None | archive | None new. |
| `output/` | Global/shared generated optimizer + benchmark artifacts | generated output | `final_archive.csv`, `initial_archive.csv`, `run_metadata.json`, `archive_comparison_latest.png`, `objective_space_*.csv`, `archives/`, `data_audit/`, `parameter analysis/` (note: literal space in this directory name), `validation/` | Overwritten on every optimizer/benchmark run; not run-ID isolated | generated | Still fully global/shared (no `output/runs/<run_id>/` yet); `output/parameter analysis/` has a space in its name, a shell-scripting hazard if ever referenced unquoted. |
| `sections/` | Report figures | archive/legacy (report artifacts) | `sections/figures/final_results/` (plots, summary CSV) | None | generated/archive | Unchanged; correctly treated as report output, not source. |
| `backup/` | Experimental older Java code | archive/legacy | `(experimental)Main.java` (one file, non-standard filename with parentheses and no package) | None (not compiled/run) | archive | Filename contains parentheses, which is unusual for a `.java` file and would not compile as a public class entry point; harmless as long as it stays outside `src/main/java` (confirmed — it does). |
| `docs/` | Current V1 documentation | documentation | `V1_ARCHITECTURE.md`, `V1_DATA_CONTRACT.md`, `V1_SCENARIO_CONTRACT.md`, `V1_OBJECTIVE_CONTRACT.md`, `V1_BENCHMARKING.md`, `V1_MAP_UI_STRATEGY.md`, `V1_ROADMAP.md`, `V1_TECH_STACK.md`, `REPO_STRUCTURE.md`, `DEPLOYMENT_PHASE1.md`, `ARCHITECTURE_AUDIT.md` | None | documentation | All mutually consistent (confirmed in the prior architecture audit); no stale contradictions found. |
| `docs/archive/` | Archived V0 reference docs | archive/legacy (documentation) | `COMPREHENSIVE_PROJECT_GUIDE_old.md` (3,414 lines), `General_GUIDE.md`, `guide.md` | None | archive | Consistently marked non-authoritative everywhere it's referenced (readme, AGENTS.md, REPO_STRUCTURE.md). |

## Active Python Script Inventory

| Script | Purpose | Classification | Inputs | Outputs | Side effects | Mutates runtime/source data | Reusable logic present | CLI logic present | Likely future responsibility | Compatibility sensitivity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/prepare_demand.py` | Generate `poi_score`/`demand_final` columns | dangerous in-place mutation | `data/candidate_points.csv` | `data/candidate_points.csv` (same file) | **Overwrites its own input CSV in place** | Yes — the base grid CSV itself | Yes | Minimal (no argparse; fixed `INPUT_FILE`/`OUTPUT_FILE` constants) | `location_platform/data/` | High — any bug here corrupts the single committed runtime candidate source; already flagged with a warning in `readme.md`. |
| `scripts/calculate_poi_weights.py` | Entropy-based POI column weighting | reusable product logic | `data/candidate_points.csv` | Returns/prints weights (does not appear to write files based on its docstring and size) | None observed beyond read | No | Yes | `location_platform/data/` | Low |
| `scripts/prepare_candidate_existing_lockers.py` | Map physical existing lockers to nearest candidates; split `locker_count` into `nearby_locker_count`/`existing_locker_count` | reusable product logic + migration utility | `data/candidate_points.csv`, `data/raw/existing_lockers_32635.csv` | `data/candidate_points.csv` (adds/renames columns), `output/data_audit/*` (audit report) | Mutates the base grid CSV (adds columns); writes an audit trail | Yes — the base grid CSV | Yes | Yes (uses `argparse`-free but structured CLI-ish flow; not confirmed argparse) | `location_platform/data/` + `location_platform/scenario/seed.py` | High — this is the script that produces the `existing_locker_count`/`nearby_locker_count` distinction every downstream script and the non-negotiable rules depend on. Correctly implements the documented rename/split logic (verified in the earlier architecture audit). |
| `scripts/plot_archives.py` | Plot initial-vs-final archive comparison | CLI/wrapper candidate (mixed with logic) | `output/final_archive.csv`, `output/initial_archive.csv` (and related) | `output/archive_comparison_latest.png` (+ `archive_comparison.png`) | Writes to global `output/` | No (reads generated files, writes generated files) | Partially (568 lines mixing plotting, methodology commentary, and I/O) | Minimal | `location_platform/benchmark/` (plotting) + thin `scripts/*_cli.py` wrapper | Low-medium — invoked directly by `ga-runner.ts` in both runtime paths, so its CLI contract (no-arg invocation, fixed output filename) is load-bearing for the UI pipeline. |
| `scripts/statistical_analysis.py` | Statistics for SPEA2 parameter-grid experiments | benchmark/reporting | `output/parameter_analysis_results*.csv` | `output/statistics*/` | Writes to global `output/` | No | Yes | `location_platform/benchmark/` | Low — only used for the `-Panalyze` hyperparameter workflow, not the main run path. |
| `scripts/scenario/generate_default_current_network_scenario.py` | Seed a V1 scenario from `existing_locker_count` | reusable product logic | `data/candidate_points.csv` | `data/scenarios/kadikoy_parcel_locker_current_network.json` | Writes a new scenario file (does not mutate the CSV) | No | Yes | `location_platform/scenario/seed.py` | Medium — sole generator of the one scenario file the rest of the system (validator, adapter, benchmark) all depend on. |
| `scripts/scenario/validate_scenario.py` | Validate a scenario JSON against grid/matrix | validation tool | `data/scenarios/*.json`, `data/candidate_points.csv`, `data/kadikoy_distance_meters_nxn.npy` | Console report only (no file output) | None | No | Yes | `location_platform/scenario/validation.py` | Medium — the only automated check that scenario facility counts match the V0 seed; used as an allowed lightweight validation command in prior tasks. |
| `scripts/scenario/derive_optimizer_inputs.py` | Translate scenario JSON into Java CLI inputs | reusable product logic | `data/scenarios/*.json`, `data/candidate_points.csv` (id column only) | JSON to stdout (optionally also to `--output` file) | None (read-only) | No | Yes | `location_platform/scenario/` | High — now the sole path by which `scenario-adapter.ts` derives `k`/`fixedFacilityIds`; its stdout JSON shape is a de facto contract with the TypeScript layer. |
| `scripts/validation/benchmark_existing_vs_optimized.py` | Scenario-based current-network vs. optimized-archive benchmark | benchmark/reporting | `data/scenarios/*.json`, `data/candidate_points.csv`, `data/kadikoy_distance_meters_nxn.npy`, `output/final_archive.csv`, `output/run_metadata.json` | `output/validation/*.{json,csv,md}` | Writes to global (not run-scoped) `output/validation/` | No | Yes | `location_platform/benchmark/current_network.py` | Medium — already scenario-aware and explicitly documents that `nearby_locker_count`/`existing_locker_count` are not facility sources of truth. |
| `scripts/research/rq1_k5_baseline_analysis.py` | RQ1 K=5 baseline vs. SPEA2 comparison | research-only | Existing CSV/NPY outputs | Comparison CSV/plot | None beyond research output | No | No (self-contained analysis) | No | Stays as research script | Low |
| `scripts/research/rq1_k5_dumbbell_plot.py` | Dumbbell plot for RQ1 | research-only | `output/rq1_k5_random_baseline_comparison.csv` | `final_results/rq1_k5_random_baseline_vs_spea2_dumbbell.png` | None; explicitly documented as not running Java/GA | No | No | No | Stays as research script | Low |
| `scripts/research/rq3_k5_equity_accessibility_validation.py` | RQ3 K=5 equity/accessibility baseline | research-only | Existing CSV/NPY outputs | Comparison CSV/plot | None; explicitly documented as not running Java/GA | No | No | No | Stays as research script | Low |
| `parcel-locker-ui/src/scripts/process_ga_data.py` | Convert optimizer output into UI-consumable JSON | UI-adjacent conversion | `output/*.csv` | `parcel-locker-ui/public/mock/ga-results.json` | Writes into UI's generated mock directory | No (writes generated UI assets, not source) | Minimal | Minimal | Stays UI-adjacent; not a `location_platform/` candidate | Medium — invoked by `ga-runner.ts` at the end of both runtime paths; still reads `nearby_locker_count`/`locker_count` as a fallback pair for a UI-only `nearbyLockerCount` display field (context-only, confirmed non-facility use in the earlier audit). |
| `parcel-locker-ui/src/scripts/build_candidate_json.py` | Convert `public/mock/candidate_points.csv` into `candidate-points.json` | UI-adjacent conversion | `parcel-locker-ui/public/mock/candidate_points.csv` | `parcel-locker-ui/public/mock/candidate-points.json` | Writes into UI's generated mock directory | No | Minimal | No | Stays UI-adjacent | Low — not observed to be invoked from `ga-runner.ts`'s pipeline; likely a standalone/manual refresh script (not confirmed further in this pass). |
| `data/prepare_ga_inputs.py` | Generate distance matrix + candidate ID alignment artifacts | migration utility (data-mutating) | `data/candidate_points.csv` | `data/kadikoy_distance_meters_nxn.npy`, `data/kadikoy_candidate_ids_sorted.npy`, `data/kadikoy_index_map.csv` | Regenerates the runtime distance matrix and its alignment artifacts | Yes — regenerates the matrix contract, which every optimizer/benchmark/scenario script depends on | Yes | Yes (`argparse`: `--input_csv`, `--out_prefix`, `--filter_forbidden`) | `location_platform/data/matrix.py` | Highest — this is the one script that can silently break candidate ID / distance matrix alignment for the entire repository if run incorrectly (e.g., with `--filter_forbidden` against an unfiltered runtime CSV), per the non-negotiable rules in every V1 doc. |

## Confirmed Current Architectural Problems

### Problem: Python script sprawl with no location-based convention

**Evidence:** `scripts/` top level mixes `prepare_demand.py`, `calculate_poi_weights.py`, `prepare_candidate_existing_lockers.py` (data prep), `plot_archives.py` (plotting), `statistical_analysis.py` (stats) with no subfolder distinguishing them, while `scripts/scenario/` and `scripts/validation/` (newer additions) already use focused subfolders.
**Why it matters:** `docs/V1_TECH_STACK.md` already defines a target `location_platform/` package; every new top-level script without that structure makes the eventual migration larger.
**Urgency:** Low — does not block current work, but grows with every new script.
**Input needed for Phase 0B:** Decide whether `location_platform/` migration starts now or after more scenario work lands, and which of the two "shapes" already in the repo (`scripts/scenario/` vs. top-level `scripts/`) becomes the template.

### Problem: Logic mixed with CLI/file I/O in several scripts

**Evidence:** `scripts/plot_archives.py` (568 lines) mixes plotting logic, methodology commentary, and file I/O in one file; `scripts/prepare_candidate_existing_lockers.py` mixes CSV mapping logic with audit-report generation.
**Why it matters:** Makes these harder to unit test or reuse as a library once `location_platform/` exists; matches `V1_TECH_STACK.md`'s stated concern about "scripts are organized by when they were written."
**Urgency:** Low — functions correctly today.
**Input needed for Phase 0B:** Decide split boundaries (e.g., pure plotting function vs. CLI entry point) before or during package migration.

### Problem: Shared/global output files, not run-scoped

**Evidence:** `output/final_archive.csv`, `output/run_metadata.json`, `output/validation/*`, `output/data_audit/*` are all fixed paths overwritten on every run; confirmed by reading `Main.java`'s `outputDirectory.resolve(...)` calls and the default `--output-dir`/`--archive`/`--metadata` values in `benchmark_existing_vs_optimized.py`.
**Why it matters:** `V1_BENCHMARKING.md` and `V1_TECH_STACK.md` both call run-specific output folders (`output/runs/<run_id>/...`) a prerequisite for trustworthy multi-scenario comparison; today, running the optimizer twice silently overwrites the previous benchmark baseline.
**Urgency:** Medium — becomes actively harmful once more than one scenario/run is compared regularly; not harmful for single-run, single-scenario use today.
**Input needed for Phase 0B:** Decide whether run-ID isolation is introduced before or after the Python package migration (they are independent but related).

### Problem: Next.js owns long-running orchestration

**Evidence:** `ga-runner.ts`'s `runJavaGa()` spawns `mvn compile exec:java` synchronously and streams SSE for the entire run; confirmed unchanged in both the V0 and scenario paths documented above.
**Why it matters:** `V1_TECH_STACK.md` explicitly calls this the "bad pattern" to move away from (Next.js should not own Maven/Python process orchestration in production).
**Urgency:** Low for now — known, documented (`docs/DEPLOYMENT_PHASE1.md`), and acceptable for local/single-user use; becomes urgent only when FastAPI/worker-queue work begins.
**Input needed for Phase 0B:** None yet — explicitly deferred until FastAPI work is scoped (not part of this repo-cleanup phase).

### Problem: The scenario compatibility bridge is temporary by design and duplicates a small amount of validation logic

**Evidence:** `scenario-adapter.ts`'s `resolveScenarioPath` re-implements path-safety checks in TypeScript; `derive_optimizer_inputs.py` re-implements a subset of the field/shape checks already present in `validate_scenario.py` (e.g., checking `constraints.lockedCandidateIds`/`disabledCandidateIds` against candidate IDs).
**Why it matters:** Two scripts (`validate_scenario.py` and `derive_optimizer_inputs.py`) both validate scenario shape independently; a future schema change must be applied in both places or validation will silently diverge.
**Urgency:** Low today (both are small and currently consistent) but should be resolved before the scenario schema changes again.
**Input needed for Phase 0B:** Decide whether `derive_optimizer_inputs.py` should call `validate_scenario.py`'s validation functions directly (requires `scripts/scenario/` becoming an importable package) rather than duplicating checks.

### Problem: Data/source/generated ambiguity around `existing_locker_count`

**Evidence:** `existing_locker_count` is a column inside `data/candidate_points.csv` (a source file) but represents facility-presence data that `V1_DATA_CONTRACT.md`/`V1_SCENARIO_CONTRACT.md` say belongs in scenario data. Java's V0 path (`--includeExistingLockers`) still reads it directly from the CSV; the scenario path deliberately avoids this by reading `scenario.facilities[]` instead.
**Why it matters:** As long as both code paths exist side by side (V0 direct-CSV-read vs. scenario-facilities-read), there are two different ways to determine "which candidates currently have a locker," and they must be kept manually in sync (today, via `generate_default_current_network_scenario.py`'s seed step and `validate_scenario.py --expect-current-network-seed`).
**Urgency:** Medium — already has a working, tested reconciliation mechanism (the seed + validate step), but every future edit to `existing_locker_count` risks silently desynchronizing the two paths if the seed script isn't rerun.
**Input needed for Phase 0B:** Decide whether the V0 `--includeExistingLockers` CLI path should be deprecated/removed once the scenario bridge is proven, or kept indefinitely for backward compatibility.

### Problem: Dangerous in-place data mutation in two scripts

**Evidence:** `scripts/prepare_demand.py` (`INPUT_FILE == OUTPUT_FILE == data/candidate_points.csv`) and `scripts/prepare_candidate_existing_lockers.py` (writes back into the same CSV) both overwrite the single committed runtime candidate source in place, with no automatic backup step beyond what a human might do manually before running them.
**Why it matters:** A partial write or an unexpected exception mid-write could corrupt the one file every other script, Java, and the UI depend on; `readme.md` already warns about this for `prepare_demand.py`.
**Urgency:** Low under normal, careful operation (these are already flagged as "run with explicit permission only" commands in `AGENTS.md`), but worth tracking as a specific risk for Phase 0B/0C to decide whether to add an automatic backup-before-write step.
**Input needed for Phase 0B:** Decide whether to add a mandatory backup/versioning step to these two scripts as part of the cleanup, or leave the existing "ask before running" guardrail as sufficient.

### Problem: Two UI-adjacent Python conversion scripts with overlapping purpose

**Evidence:** `parcel-locker-ui/src/scripts/process_ga_data.py` and `parcel-locker-ui/src/scripts/build_candidate_json.py` both convert a CSV into a JSON file for `parcel-locker-ui/public/mock/`, but only `process_ga_data.py` is confirmed invoked by `ga-runner.ts`.
**Why it matters:** Unclear whether `build_candidate_json.py` is still actively used (e.g., via a separate manual step or npm script) or is a leftover from an earlier UI data-loading approach.
**Urgency:** Low — does not block anything today.
**Input needed for Phase 0B:** Confirm whether `build_candidate_json.py` has an active caller (e.g., check `package.json` scripts or other UI code not reviewed in this pass) before deciding its fate.

### Problem: `output/parameter analysis/` contains a literal space in its directory name

**Evidence:** `find output -maxdepth 1` shows `output/parameter analysis` (with a space), alongside every other `output/` subdirectory using underscores.
**Why it matters:** A space in a path is a common shell-scripting hazard (breaks unquoted path usage in scripts/CI); purely a hygiene issue, not a functional bug today.
**Urgency:** Low.
**Input needed for Phase 0B:** Decide whether to rename it to `output/parameter_analysis/` as part of the output-directory cleanup, and who/what currently writes to that path (not confirmed in this pass — likely `mvn exec:java -Panalyze` based on `readme.md`'s documented outputs).

## Current Source / Runtime / Generated / Raw / Archive Boundaries

| Category | Paths |
| --- | --- |
| **Source (code)** | `src/main/java/`, `parcel-locker-ui/src/` (all of it, including `lib/server/`), `scripts/` (excluding `scripts/archive/`), `data/prepare_ga_inputs.py` |
| **Runtime input (data, not code)** | `data/candidate_points.csv`, `data/kadikoy_distance_meters_nxn.npy`, `data/kadikoy_candidate_ids_sorted.npy`, `data/kadikoy_index_map.csv` |
| **Scenario source (V1, data)** | `data/scenarios/*.json` |
| **Generated output** | `output/` (all subfolders), `parcel-locker-ui/.next/`, `parcel-locker-ui/public/mock/`, `sections/figures/final_results/`, `target/` (if present), `graphify-out/` |
| **Raw/provenance data** | `data/raw/` |
| **Archive/legacy** | `data/archive/`, `docs/archive/`, `scripts/archive/`, `backup/` |
| **Documentation** | `docs/` (excluding `docs/archive/`), `readme.md`, `AGENTS.md`, `CLAUDE.md` |
| **Dependency/build/cache** | `node_modules/`, `.next/`, `target/`, `__pycache__/`, Graphify cache (`graphify-out/cache/`) |

This table matches what `docs/REPO_STRUCTURE.md` and `AGENTS.md` already declare; this pass found no folder whose actual on-disk contents contradict their documented category.

## Open Questions for Phase 0B

1. Should `scripts/scenario/` and `scripts/validation/` become the first real `location_platform/` package modules now, or should Phase 0B wait for more scenario work (e.g., facility import) before finalizing package boundaries?
2. Should `derive_optimizer_inputs.py` and `validate_scenario.py` share validation code (requiring `scripts/scenario/` to become an importable package), or is duplicated validation acceptable long-term?
3. Should the V0 `--includeExistingLockers` CLI path in `Main.java` be deprecated once the scenario bridge is proven reliable, or kept indefinitely as a fallback?
4. ~~Is `parcel-locker-ui/src/scripts/build_candidate_json.py` still actively used by any current workflow, or is it a candidate for archival?~~ **Resolved (Phase 1G2):** no active caller was found (not referenced by `ga-runner.ts`, `package.json`, or any other current script); deleted as a confirmed-dead Tier 1 cleanup item.
5. Should run-ID output isolation (`output/runs/<run_id>/`) be scoped as part of this repository cleanup, or deferred entirely to a separate benchmarking-focused phase?
6. Should `output/parameter analysis/` be renamed to remove the space, and if so, what currently writes to it (needs confirmation beyond this pass)?
7. Should the two data-mutating-in-place scripts (`prepare_demand.py`, `prepare_candidate_existing_lockers.py`) gain an automatic backup step as part of cleanup, or is the existing "ask before running" guardrail sufficient long-term?
8. What should the final home for `scripts/research/*.py` be — do they stay permanently outside any package (as pure one-off report scripts), or do they eventually need a `research/` designation inside the target structure?

## Phase 0A Acceptance Checklist

- [x] All current relevant changes are classified (see Current Change Inventory).
- [x] Both runtime paths are documented accurately (V0 Runtime Path, Scenario Compatibility Path), based on direct reading of `route.ts`, `ga-runner.ts`, `scenario-adapter.ts`, `Main.java`, and `derive_optimizer_inputs.py`.
- [x] All important folders are classified (see Folder Classification).
- [x] All active Python scripts are inventoried (14 scripts, including the two newly-noticed `data/prepare_ga_inputs.py` and `parcel-locker-ui/src/scripts/build_candidate_json.py`).
- [x] Side effects and in-place mutations are identified (`prepare_demand.py`, `prepare_candidate_existing_lockers.py`, `data/prepare_ga_inputs.py` all flagged).
- [x] Source/generated/raw/archive boundaries are recorded (see boundary table) and confirmed consistent with `docs/REPO_STRUCTURE.md`.
- [x] Current problems are evidence-based (each cites the specific file/behavior observed, not speculation).
- [x] Questions requiring a Phase 0B decision are listed (8 open questions above).
- [x] No runtime, application, data, or generated file was changed to produce this document — only `docs/PHASE_0_REPO_CLEANUP_PLAN.md` was created.

---

## Phase 0B Objective

Phase 0B makes the structural decisions Phase 1 needs before any file is moved: where reusable Python logic will live, how it will be packaged and imported, what `scripts/` is allowed to contain, and which component owns each responsibility going forward. This is a decision record, not a migration plan — no file-by-file mapping is produced here (that is Phase 0C), and no file was moved, renamed, or refactored to produce it.

## Target Architecture Decision Summary

| Decision | Outcome |
| --- | --- |
| 1. Python package location | **Option A** — `python/pyproject.toml` + `python/src/location_platform/` + `python/tests/`, installed editable. |
| 2. Target repository structure | Approved with adjustments: `spatial/` and `orchestration/` are reserved names, not created empty in Phase 1; `scripts/validation/` is retargeted to `scripts/benchmark/` naming; `data/prepare_ga_inputs.py`'s wrapper target is `scripts/data/`. |
| 3. Python module boundaries | `common`, `data`, `scenario`, `benchmark` get real Phase 1 content; `spatial`, `orchestration` deferred until concrete callers exist (Phase 2 / FastAPI phase). |
| 4. `scripts/` policy | Executable entrypoints and compatibility wrappers only; old script paths remain as thin wrappers around package functions; no `python -m` invocation and no console-script entry points yet. |
| 5. Responsibility ownership | Java stays the sole optimizer; scenario-adapter.ts/ga-runner.ts stay a temporary bridge; scenario/benchmark rules live in Python only. |
| 6. Phase 0A open questions | All 8 resolved or explicitly deferred — see below. |
| 7. Frozen runtime paths | Candidate CSV, matrix artifacts, `data/scenarios/`, `src/main/java/`, `parcel-locker-ui/`, current `output/` paths, and the `scripts/` entrypoint file paths Next.js already invokes. |

## Python Package Layout Decision

**Selected option: Option A** (`python/pyproject.toml`, `python/src/location_platform/`, `python/tests/`).

**Reasons:**

- The repository already separates its other two engines by a dedicated top-level folder with its own build/config file: `src/main/java/` + root `pom.xml` for Java, `parcel-locker-ui/` + its own `package.json` for Next.js. Python currently has no analogous single top-level home — its code is split across `scripts/`, `data/prepare_ga_inputs.py`, and `parcel-locker-ui/src/scripts/`, with dependencies declared only in a root `requirements.txt`. A `python/` folder with its own `pyproject.toml` gives Python the same first-class, self-contained status the other two engines already have, without disturbing `pom.xml` or `package.json` at the root.
- A `src/` layout inside `python/` (`python/src/location_platform/`) is the standard, tool-recommended way to avoid the classic flat-layout footgun where `import location_platform` accidentally resolves to an uninstalled working-directory copy instead of the installed package — relevant here because `scripts/` will keep executing as plain file paths (see `scripts/` policy below), and those files' working directory (repo root) must not accidentally shadow the installed package.
- `requirements.txt` at the repo root keeps meaning what it means today (dependencies needed to *run* the existing scripts/UI-triggered pipeline); `python/pyproject.toml` is additive and describes a separate, installable library. No existing documented command (`python3 -m pip install -r requirements.txt`) needs to change.

**Tradeoffs:**

- Requires one new one-time setup step (an editable install) beyond what `readme.md` documents today; this must be added to setup docs in Phase 1, not this phase.
- A `python/tests/` suite run from repo root needs either `cd python && pytest` or a root `pytest.ini`/`pyproject.toml` `testpaths` pointer — a minor, well-understood configuration detail, not a structural risk.

**Installation/import strategy:**

- One-time setup: an editable install (`python -m pip install -e ./python` / `py -m pip install -e ./python`, chosen by resolving which interpreter the runtime actually spawns — see the corrected procedure in "Corrected Interpreter Installation Rule" below), run once per environment, exactly analogous to the existing `python3 -m pip install -r requirements.txt` step in `readme.md`.
- This registers `location_platform` in the active environment's import path via standard packaging metadata — **no `sys.path` manipulation, no relative-import hacks, and no dependency on the caller's current working directory.**
- Any script anywhere in the repo — a `scripts/` wrapper, a future `python/tests/` test, a future FastAPI route, a future RQ worker task — can do a plain `import location_platform` (or `from location_platform.scenario import ...`) as long as the same environment is active. This is the concrete way Decision 1 avoids "fragile path manipulation," satisfying the preference for Option A stated in the task.

**How repository-root scripts will import it:**

`scripts/scenario/derive_optimizer_inputs.py` (and its siblings) become thin wrapper files at their **current paths** whose entire body is: parse CLI args (or reuse `argparse` boilerplate), `import location_platform.scenario as scenario_pkg` (or the specific submodule), call the package's function, print/return its result. The wrapper owns only argument parsing and process exit code; all decision logic (candidate resolution, validation, JSON shaping) lives in the package.

**How Next.js subprocess calls remain compatible:**

`runtime-config.ts`'s `scenarioAdapterScriptPath`, `plotScriptPath`, and `processScriptPath` continue to point at the exact same file paths (`scripts/scenario/derive_optimizer_inputs.py`, `scripts/plot_archives.py`, `parcel-locker-ui/src/scripts/process_ga_data.py`). `python-runner.ts`'s `runPythonScript(scriptPath, args, {cwd: projectRoot})` keeps invoking `python <scriptPath> <args>` exactly as it does today. **No TypeScript file needs to change for this decision** — the package-location choice is invisible to the Node/Next.js layer by design, because the wrapper scripts absorb the difference between "invoke as a file path" and "import as a package."

## Approved Target Repository Structure

Adjusted from the proposed diagram, with reasons given per area:

```text
Location-Optimization-with-Genetic-Algorithm/
├── src/main/java/                # unchanged — Java optimizer
├── parcel-locker-ui/              # unchanged — Next.js UI + temporary server bridge
├── python/
│   ├── pyproject.toml
│   ├── src/
│   │   └── location_platform/
│   │       ├── common/            # Phase 1: shared helpers (path/display/parsing utils)
│   │       ├── data/              # Phase 1: candidate/matrix/demand logic
│   │       ├── scenario/          # Phase 1: seed, validate, derive-optimizer-input logic
│   │       ├── benchmark/         # Phase 1: current-network + archive comparison logic
│   │       ├── spatial/           # RESERVED — not created until Phase 2 (facility import/snapping)
│   │       └── orchestration/     # RESERVED — not created until FastAPI/worker phase needs it
│   └── tests/
├── scripts/                       # thin CLI/compatibility entrypoints only
│   ├── data/                      # target for prepare_demand.py, calculate_poi_weights.py,
│   │                              #   prepare_candidate_existing_lockers.py, prepare_ga_inputs.py
│   ├── scenario/                  # unchanged location; wrappers around location_platform.scenario
│   ├── benchmark/                 # target rename of scripts/validation/ (see below)
│   ├── research/                  # unchanged — stays outside the package entirely
│   └── archive/                   # unchanged — legacy/one-off, never migrated
├── data/
│   ├── scenarios/                 # unchanged
│   ├── raw/                       # unchanged
│   ├── archive/                   # unchanged
│   └── candidate_points.csv, kadikoy_*.npy/csv  # unchanged, frozen (see Decision 7)
├── output/                        # unchanged in Phase 1 — generated only
├── docs/                          # unchanged
└── ...
```

Deviations from the originally proposed tree, and why:

- **`spatial/` and `orchestration/` are not created as empty Phase 1 stubs.** No current script maps cleanly to either today: existing-locker snapping logic lives inside `prepare_candidate_existing_lockers.py` (classified as `data/` work today), and there is no orchestration logic in Python at all — orchestration currently lives entirely in `ga-runner.ts` (Next.js) and will move to FastAPI/a worker queue, not to a Python-package `orchestration` module, when that phase begins. Creating these two modules empty now would violate "do not create empty speculative modules merely for symmetry." They remain **reserved names** in this document so Phase 0C/Phase 2 doesn't have to re-litigate what they're for.
- **`scripts/validation/` is retargeted to `scripts/benchmark/`.** The current folder name (`validation`) predates the `location_platform.benchmark` module name being decided here; `benchmark_existing_vs_optimized.py` is benchmark/reporting logic per the Phase 0A inventory, and V1_BENCHMARKING.md consistently uses "benchmark" terminology. This is a **decision**, not an action — the actual rename is Phase 0C/1 execution.
- **`data/prepare_ga_inputs.py`'s wrapper target is `scripts/data/`, not `data/`.** Phase 0A's boundary table already flagged that a script living directly inside `data/` blurs the "runtime input" vs. "source code" boundary; moving its thin wrapper to `scripts/data/` (with the reusable matrix-generation logic in `location_platform.data`) resolves that inconsistency. Again, a decision for Phase 0C/1 to execute, not performed here.

For every approved top-level area:

| Area | Owner | Responsibility | What belongs there | What must not belong there | Migration timing |
| --- | --- | --- | --- | --- | --- |
| `src/main/java/` | Java optimizer | SPEA2 execution, Pareto/dominance, fitness evaluation | Optimizer algorithm code, CLI arg parsing for the optimizer | Scenario editing, CSV/GIS import, benchmark reporting, UI formatting | Not migrated — untouched by Phase 1 |
| `parcel-locker-ui/` | Next.js UI + temporary bridge | UI, dashboard, API route, local orchestration | UI components, API routes, `lib/server/*` bridge code | Scenario/benchmark business rules (must call into Python, not reimplement) | Not migrated — untouched by Phase 1 |
| `python/` | Python package | All reusable data/scenario/benchmark/spatial logic | Anything currently duplicated across 2+ scripts (confirmed: `display_path` alone is duplicated across 4 scripts today) | CLI argument parsing (that's `scripts/`'s job), SPEA2 objective math (that's Java's job) | Created in Phase 1 |
| `scripts/` | Thin entrypoints | Executable wrappers, backward-compatible file paths | `argparse` setup, calling into `location_platform`, printing results | Business logic, validation rules, anything reused by more than one entrypoint | Wrapper conversion is Phase 1; folder itself already exists |
| `data/` (runtime files) | Runtime input | Candidate CSV, distance matrix, matrix-alignment artifacts, scenario JSON | Nothing else — no scripts, no logic | Any script file (see `prepare_ga_inputs.py` deviation above) | Frozen in Phase 1 (see Decision 7) |
| `output/` | Generated output | Optimizer/benchmark artifacts | Nothing hand-maintained | Source data, scripts | Frozen in Phase 1; run-isolation is a later, separate decision |
| `docs/` | Documentation | V1 contracts, architecture records | Docs only | Implementation code | Not migrated |

## Python Package Responsibility Boundaries

### `location_platform.common`

- **Responsibilities:** Shared, side-effect-free helpers used by 2+ other modules — path display/resolution helpers, numeric parsing/validation helpers (`finite_float`, `nonnegative_integer`-style checks), shared error types.
- **Allowed dependencies:** Standard library only (or `pathlib`/`typing`); no dependency on `data`, `scenario`, or `benchmark`.
- **Forbidden responsibilities:** Any domain logic (candidate loading, scenario validation, objective math) — if a function needs domain knowledge of candidates/scenarios/facilities, it does not belong here.
- **Known current scripts that may contribute:** `display_path`/`resolve_path` helpers duplicated in `scripts/scenario/derive_optimizer_inputs.py`, `generate_default_current_network_scenario.py`, `validate_scenario.py`, and `scripts/validation/benchmark_existing_vs_optimized.py` (confirmed via direct grep); `finite_float`/`nonnegative_integer`-style helpers in `benchmark_existing_vs_optimized.py` and `prepare_candidate_existing_lockers.py`.

### `location_platform.data`

- **Responsibilities:** Load and validate candidate/grid records, generate/validate the distance matrix and its alignment artifacts, compute POI/demand scores, map physical existing lockers to candidates.
- **Allowed dependencies:** `common`; `numpy`/`pandas`.
- **Forbidden responsibilities:** Must not silently mutate runtime inputs — any function that currently overwrites `data/candidate_points.csv` in place must make that an explicit, named operation (e.g., `regenerate_demand_scores(path, ...)`), never an implicit side effect of "loading" data. Must not decide scenario facility membership (that is `scenario`'s job) even though it currently produces the `existing_locker_count`/`nearby_locker_count` split that `scenario` seeds from.
- **Known current scripts:** `scripts/prepare_demand.py`, `scripts/calculate_poi_weights.py`, `scripts/prepare_candidate_existing_lockers.py`, `data/prepare_ga_inputs.py`.

### `location_platform.scenario`

- **Responsibilities:** Scenario JSON schema, seeding a default scenario from V0 data, validating scenario shape/candidate-ID/matrix alignment, and deriving optimizer-relevant inputs (`k`, `fixedFacilityIds`, active/locked/disabled candidate sets) from a scenario.
- **Allowed dependencies:** `common`, `data` (for candidate ID / matrix existence checks only, not for facility decisions).
- **Forbidden responsibilities:** Must not select or score optimizer facilities (that's Java's job — this module prepares Java's *input*, it does not run or approximate the optimizer). Must not duplicate benchmark metric computation. **Scenario validation must exist in exactly one place in this module** — both the current `validate_scenario.py` and `derive_optimizer_inputs.py` re-implement overlapping shape/ID checks today; Phase 1 must have `derive_optimizer_inputs`'s package equivalent call the same validation function `validate_scenario`'s package equivalent uses, not a second copy.
- **Known current scripts:** `scripts/scenario/generate_default_current_network_scenario.py`, `scripts/scenario/validate_scenario.py`, `scripts/scenario/derive_optimizer_inputs.py`.

### `location_platform.benchmark`

- **Responsibilities:** Compute current-network and optimized-archive metrics (F1/F2 and future coverage/equity/business metrics), compare scenarios, produce benchmark reports.
- **Allowed dependencies:** `common`, `data`, `scenario` (to read `scenario.facilities[]` — read-only, never to re-derive or re-validate it independently).
- **Forbidden responsibilities:** **Must not select optimizer facilities** — it evaluates candidate sets it is given (existing baseline or an archive's chromosomes), it never decides which candidates should be fixed/locked/disabled; that is exclusively `scenario`'s output, consumed here as an input.
- **Known current scripts:** `scripts/validation/benchmark_existing_vs_optimized.py`, `scripts/statistical_analysis.py`, plotting logic currently inside `scripts/plot_archives.py`.

### `location_platform.spatial` (reserved, not created in Phase 1)

- **Responsibilities (future):** Generic CRS handling, candidate snapping, buffer/join operations for facility import — the part of `V1_DATA_CONTRACT.md`'s "Layer Join Methods" and "Scenario Facility Snapping" sections that isn't yet built.
- **Allowed dependencies (future):** `common`, `data`.
- **Forbidden responsibilities:** Must not become a second place scenario facilities get serialized or persisted — snapping computes a `candidateId`/`snapDistanceMeters`/`snapStatus` result; `scenario` decides what to do with that result.
- **Known current scripts that may eventually contribute:** The snapping logic currently embedded in `scripts/prepare_candidate_existing_lockers.py` (nearest-candidate-center mapping) is the closest existing precedent, but it stays classified under `data` until it's genuinely reused by a second caller (e.g., new facility import in Phase 2), per "do not create empty speculative modules."

### `location_platform.orchestration` (reserved, not created in Phase 1)

- **Responsibilities (future):** Job/run lifecycle concerns once a worker queue exists — invoking the Java optimizer, tracking run status, run-ID-scoped output management. This is the eventual home for logic like `jobs/run_optimizer.py`/`jobs/run_benchmark.py` from `V1_TECH_STACK.md`'s sketch.
- **Allowed dependencies (future):** `common`, `data`, `scenario`, `benchmark` — but never the reverse (no other module should depend on `orchestration`).
- **Forbidden responsibilities:** **Must never contain SPEA2 objective logic** — it invokes the Java process and manages its lifecycle; it does not re-implement or approximate what Java computes. Must not become a second scenario-to-CLI-args translator (that's `scenario`'s job, already implemented in `derive_optimizer_inputs.py`).
- **Known current scripts that may eventually contribute:** None yet — today this responsibility lives entirely in `ga-runner.ts` (Next.js), which is explicitly a temporary bridge, not a Python package concern until FastAPI/worker infrastructure exists.

## `scripts/` Policy

**Rule:** `scripts/` contains only executable entrypoints and backward-compatible wrappers. All reusable logic — anything called from more than one place, or anything that isn't pure argument-parsing/process-exit-code handling — lives in `python/src/location_platform/`.

Concrete decisions:

- **Old paths remain as wrappers: yes.** Every script path Next.js's `runtime-config.ts` currently hardcodes (`scripts/scenario/derive_optimizer_inputs.py`, `scripts/plot_archives.py`) and every path `readme.md`/`AGENTS.md` currently documents (`python3 scripts/prepare_demand.py`, `python3 data/prepare_ga_inputs.py`, etc.) must keep working at the same path after Phase 1, as thin wrappers. This is a hard backward-compatibility requirement, not a preference.
- **`python -m` vs. imported main functions: imported main functions.** `runPythonScript(scriptPath, args, {cwd})` in `python-runner.ts` invokes `python <scriptPath> <args>` — a file path, not a module name. Switching to `python -m location_platform.scenario.derive_optimizer_inputs` would require changing `runtime-config.ts` and every documented command, which this phase is not scoped to do. Wrappers therefore stay plain `.py` files that `import` the package and call a function.
- **Console scripts (`[project.scripts]` in `pyproject.toml`): not introduced now.** There is no current caller that would use a pip-installed console command instead of a file path; adding one now would be a third, currently-unused invocation method. Revisit only if/when FastAPI or a worker process wants a clean CLI surface.
- **One-off migration scripts:** belong in the already-existing `scripts/archive/one_off/` — no new folder is needed for this purpose.
- **Research scripts:** stay in `scripts/research/`, permanently outside `location_platform`. They are already self-documented as not touching Java/GA and have no reuse value beyond their specific report question.
- **Archive scripts:** stay in `scripts/archive/`, never migrated into the package — treated purely as historical/legacy reference, consistent with Phase 0A's classification.

## Component Ownership Matrix

| Component | Owns | Does not own |
| --- | --- | --- |
| Java optimizer (`src/main/java/`) | SPEA2 execution, Pareto/dominance, fitness math | Scenario editing, scenario JSON validation, benchmark reporting, CSV/GIS import |
| Python package (`python/src/location_platform/`) | Scenario schema/seed/validation/derivation, data loading/validation, benchmark metrics, (future) spatial snapping, (future) job orchestration | SPEA2 objective computation, UI rendering, HTTP routing |
| `scripts/` | Argument parsing, calling into the package, exit codes | Any logic reused by more than one entrypoint |
| Next.js UI (`parcel-locker-ui/src/app`, `components`) | Map/dashboard rendering, user interaction, API client calls | Scenario/benchmark business rules, optimizer invocation details |
| Next.js temporary server bridge (`parcel-locker-ui/src/lib/server/*`) | **Temporary** local process orchestration (`ga-runner.ts`), scenario-path validation and adapter invocation (`scenario-adapter.ts`), runtime path config (`runtime-config.ts`) | Any new domain/business logic — `ga-runner.ts` must not grow additional scenario/benchmark rules beyond what `derive_optimizer_inputs.py` already returns; it is confirmed temporary, not the final backend |
| Future FastAPI | Scenario CRUD, facility import endpoints, run creation/status endpoints | Anything already correctly owned by the Python package — FastAPI calls into `location_platform`, it does not reimplement its logic |
| Future worker queue (RQ/Redis) | Long-running optimizer/benchmark job execution, run isolation | Scenario/benchmark decision logic (calls into `location_platform.orchestration`, which calls `data`/`scenario`/`benchmark`) |
| `data/` | Runtime candidate/matrix/scenario source files | Any script or logic file (see `prepare_ga_inputs.py` deviation) |
| `data/scenarios/` | Scenario JSON source | Anything derived (derived optimizer inputs, benchmark output) |
| `output/` | Generated optimizer/benchmark artifacts | Anything hand-maintained or treated as source |
| Documentation (`docs/`) | V1 contracts, architecture records, this cleanup plan | Implementation code |

Explicit decisions restated per the task's required list:

- `scenario-adapter.ts` **remains temporary** — it is the compatibility bridge documented in Phase 0A, not a permanent architectural component.
- `ga-runner.ts` **may preserve local V0 orchestration**, but must not gain additional domain/business logic; any new scenario/benchmark rule belongs in the Python package, called from a wrapper script, not written directly into `ga-runner.ts`.
- `derive_optimizer_inputs.py`'s logic **moves to `location_platform.scenario` in Phase 1**; the file at its current path becomes a thin wrapper.
- **Java does not own** scenario editing or scenario JSON validation — those stay in Python, upstream of the Java CLI call.
- **Next.js does not duplicate** Python scenario or benchmark rules — `scenario-adapter.ts` only validates path safety and shapes a subprocess call; it must never re-implement candidate/facility resolution logic itself.
- **FastAPI and workers are deferred** until the `python/` package boundary exists and is proven by at least the scenario/benchmark modules being real (not just wrappers around scripts).

## Resolved Phase 0A Architecture Questions

1. **Package migration timing/template** — Resolved: Option A (`python/`), with `scripts/scenario/` and `scripts/validation/` (renamed target: `scripts/benchmark/`) as the first modules ported, since they are already the best-organized, most self-contained existing code (confirmed in Phase 0A's Folder Classification).
2. **Shared vs. duplicated scenario validation** — Resolved: **one shared implementation.** `location_platform.scenario`'s validation function is the single source of truth; both the `validate_scenario.py` wrapper and the `derive_optimizer_inputs.py` wrapper call it. No second copy of candidate-ID/constraint-shape checking is permitted.
3. **Deprecate V0 `--includeExistingLockers`?** — Resolved: **remains temporarily supported.** No repository evidence yet justifies removing it (the scenario path exists alongside it, not as a forced replacement); revisit only after the scenario-driven path has been exercised more than the handful of adapter tests run so far.
4. **`scripts/research/` final home** — Resolved: **stays permanently outside the package.** These scripts are self-documented as not touching Java/GA and have no confirmed reuse beyond their specific report question.
5. **`build_candidate_json.py` active-caller uncertainty** — Originally resolved as "remains UI-adjacent temporarily, alongside `process_ga_data.py`." **Superseded (Phase 1G2):** no active caller was ever confirmed, and the file has since been deleted as a Tier 1 cleanup item. `process_ga_data.py` is unaffected and remains UI-adjacent (it has a confirmed caller in `ga-runner.ts`).
6. **`output/parameter analysis/` rename** — Resolved: **deferred.** No script ownership was confirmed beyond a likely link to `mvn exec:java -Panalyze`; renaming without confirming every writer/reader risks breaking an untouched workflow for a cosmetic fix.
7. **Backup step for in-place-mutating scripts** — Resolved: **deferred alongside the scripts themselves.** Since `prepare_demand.py`, `prepare_candidate_existing_lockers.py`, and `data/prepare_ga_inputs.py` are explicitly not in the first migration batch (see below), the backup-step design question is deferred to whenever they are migrated, not decided prematurely.
8. **Run-specific output isolation timing** — Resolved: **deferred, not part of Phase 1.** Phase 1 is a Python logic/package migration; run-ID isolation is a separate, `output/`-focused concern that can be scoped independently once it's actually needed (i.e., once multiple scenarios/runs are compared regularly, per the Phase 0A problem list).

## Deferred Decisions

These are intentionally not decided in Phase 0B:

- Whether `location_platform.spatial` and `location_platform.orchestration` are created at all, versus folded permanently into `data`/an eventual FastAPI layer — deferred until Phase 2 (facility import/snapping) or the FastAPI/worker phase produces a concrete first caller.
- Exact file names within each Phase 1 package module (e.g., whether `location_platform.scenario` has one `validation.py` or splits into `schema.py` + `validation.py`) — deferred to Phase 0C's file-by-file migration map.
- Whether `pyproject.toml` uses `setuptools` or `hatchling` as its build backend — a Phase 0C/implementation detail with no architectural consequence.
- Console-script CLI entry points — deferred until a concrete consumer (FastAPI, worker) needs them.
- Run-specific output isolation (`output/runs/<run_id>/`) design — deferred, tracked as a known future need in Phase 0A's problem list, not scoped here.
- Whether `scripts/validation/` → `scripts/benchmark/` and `data/prepare_ga_inputs.py` → `scripts/data/prepare_ga_inputs.py` are executed in the same Phase 1 batch as the package creation, or as a follow-up rename pass — left to Phase 0C sequencing.
- A backup/versioning strategy for the in-place-mutating data scripts — deferred alongside those scripts' migration (see Resolved Question 7).

## Paths Frozen During Phase 1

Phase 1 is a Python logic/package migration, not a runtime-data or UI/Java relocation. The following must not move, rename, or change shape during Phase 1:

```text
data/candidate_points.csv
data/kadikoy_distance_meters_nxn.npy
data/kadikoy_candidate_ids_sorted.npy
data/kadikoy_index_map.csv
data/kadikoy_ARTIFACTS_GUIDE.md
data/scenarios/                          (directory and its current contents)
src/main/java/                            (entire tree)
parcel-locker-ui/                         (entire tree, including lib/server/*)
output/                                    (existing paths and shapes; no run-isolation restructuring)
```

Additionally frozen as a consequence of the `scripts/` policy above (Next.js and documented commands depend on these exact paths):

```text
scripts/scenario/derive_optimizer_inputs.py   (path stays; internals become a thin wrapper)
scripts/plot_archives.py                       (path stays; internals may thin out over time)
parcel-locker-ui/src/scripts/process_ga_data.py
requirements.txt                               (root; unaffected by python/pyproject.toml)
```

## Inputs Required for Phase 0C

Phase 0C needs the following, all now available from this document:

- Approved package location (`python/src/location_platform/`) and its four Phase 1 modules (`common`, `data`, `scenario`, `benchmark`).
- The two retargeted paths (`scripts/validation/` → `scripts/benchmark/`, `data/prepare_ga_inputs.py` → `scripts/data/prepare_ga_inputs.py`) that Phase 0C must sequence.
- The explicit list of scripts excluded from the first migration batch (research scripts, archive scripts, the three in-place-mutating data scripts, `build_candidate_json.py`/`process_ga_data.py`).
- The frozen-paths list above, to check against before any move.
- The one-shared-validation requirement for `location_platform.scenario`, so Phase 0C's migration map doesn't accidentally port `validate_scenario.py` and `derive_optimizer_inputs.py` as two independent modules with duplicated logic.

Phase 0C should now produce the exact file-by-file migration map (old path → new path, what becomes a wrapper vs. what becomes package code) using this document as its architectural constraint set.

## Phase 0B Acceptance Checklist

- [x] Option A or Option B is selected clearly (Option A).
- [x] The target top-level repository structure is approved, with adjustments justified by repository-specific evidence (deferred `spatial`/`orchestration`, retargeted `scripts/validation/` and `data/prepare_ga_inputs.py`).
- [x] Each Python package area has a clear responsibility, allowed/forbidden dependencies, and known contributing scripts.
- [x] `scripts/` has a strict policy (wrappers only, imported-main-function pattern, no `python -m`, no console scripts yet).
- [x] Component ownership boundaries are explicit (Component Ownership Matrix, including all six task-mandated explicit decisions).
- [x] All 8 architecture-level Phase 0A questions are resolved or intentionally deferred.
- [x] Runtime/data paths frozen for Phase 1 are listed.
- [x] Phase 0C has enough input to build an exact migration map (see Inputs Required for Phase 0C).
- [x] No runtime or code file was changed — only `docs/PHASE_0_REPO_CLEANUP_PLAN.md` was updated.

---

## Phase 0C1 Objective

Phase 0B chose the package location (`python/src/location_platform/`) and the `scripts/`-stays-as-wrappers rule. Phase 0C1 turns that into an exact, file-by-file migration map for the **first** Phase 1 batch only — the four scenario/benchmark scripts already identified as the best-organized, most self-contained code in the repository. It decomposes each script's current responsibilities, names exact target package modules and their public functions, defines what stays behind as a thin wrapper, resolves every duplicate-logic area found across the four scripts, and orders the migration so nothing is built before its dependency exists. No file was moved, no package was created, and no code was written or changed to produce this document.

## First Phase 1 Migration Batch

Scope: exactly the four scripts named in the task. `prepare_demand.py`, `calculate_poi_weights.py`, `prepare_candidate_existing_lockers.py`, `plot_archives.py`, `statistical_analysis.py`, all `scripts/research/*.py`, and the two UI conversion scripts are explicitly **not** part of this batch (per Phase 0B's deferral decisions).

| Current path | Target module | Reusable logic moved | Wrapper logic retained | Shared dependencies | Existing command preserved | Migration order | Risk level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/scenario/generate_default_current_network_scenario.py` | `location_platform.scenario.seed` | `load_existing_facility_rows` → `load_existing_facility_seed_rows`; `build_facility` → `build_facility_from_seed_row`; `build_scenario` → `build_current_network_scenario`; `write_scenario` → calls shared `common.io.write_json_file` | `parse_args()`; `main()`'s call sequence; final summary `print()` lines | `location_platform.data.candidates`, `location_platform.common.paths`, `location_platform.common.parsing`, `location_platform.common.io` | Yes — `python scripts/scenario/generate_default_current_network_scenario.py --candidate-csv ... --output ...` unchanged | 4 (after common/data primitives + scenario.loading are ready; deliberately after `scenario.validation` so its output can be immediately re-validated with the migrated validator as a sanity check) | Low — no external caller depends on this script's exact stdout shape (only its written JSON file, whose shape is unchanged) |
| `scripts/scenario/validate_scenario.py` | `location_platform.scenario.validation` | `add_missing_fields_errors`, `is_integer`, `is_numeric`, `parse_csv_int`/`parse_csv_float` (superseded by `common.parsing`), `load_json` (superseded by `scenario.loading`), `load_candidate_csv` (superseded by `data.candidates`), `validate_distance_matrix` (superseded by `data.matrix`), `validate_constraints`, `validate_grid_and_settings`, `validate_facilities`, `validate_current_network_seed` → `validate_current_network_seed_match`, `validate_scenario()` orchestrator | `parse_args()`; `main()`'s call sequence; `print_warnings()`; pass/fail summary printing; exit-code mapping (1 on errors) | `location_platform.scenario.loading`, `location_platform.data.candidates`, `location_platform.data.matrix`, `location_platform.common.errors`, `location_platform.common.parsing` | Yes — `python scripts/scenario/validate_scenario.py --scenario ... --candidate-csv ... --distance-matrix ... [--expect-current-network-seed]` unchanged | 3 (after common/data primitives; before seed/derive/benchmark since it establishes the shared `scenario.loading` contract those three lean on) | Medium — largest of the four scripts (583 lines) with the most internal validation branches; must preserve every current error/warning message text exactly, since some are likely referenced by users reading validator output |
| `scripts/scenario/derive_optimizer_inputs.py` | `location_platform.scenario.optimizer_inputs` | `require_mapping` (superseded by `common.errors`), `resolve_active_existing_candidate_ids`, `resolve_constraint_ids`, `resolve_facility_count`, `build_java_cli_args`, `derive()` | `parse_args()`; `main()`'s call sequence; stdout JSON printing; `--output` file write (via `common.io.write_json_file`); stderr warning/error printing; exit-code mapping | `location_platform.scenario.loading`, `location_platform.data.candidates`, `location_platform.common.errors` | Yes — `python scripts/scenario/derive_optimizer_inputs.py --scenario ... --candidate-csv ... [--force-existing-off] [--override-target-total-facility-count N] [--output ...]` unchanged | 5 (after `scenario.loading`/`data.candidates` exist; independent of `scenario.validation`/`scenario.seed` — confirmed by reading the script, it calls neither) | **Highest** — `parcel-locker-ui/src/lib/server/scenario-adapter.ts`'s `deriveOptimizerInputsFromScenario()` does `JSON.parse(stdout)` on this script's entire stdout today; the wrapper must print **exactly** the same JSON to stdout and nothing else, or the TypeScript scenario-compatibility bridge silently breaks |
| `scripts/validation/benchmark_existing_vs_optimized.py` | `location_platform.benchmark.current_network` | `resolve_path` (superseded by `common.paths`), `display_path` (superseded), `finite_float`/`nonnegative_integer` (superseded by `common.parsing`), `load_candidates` (superseded by `data.candidates`), `companion_id_artifact`/`load_and_validate_matrix` (superseded by `data.matrix`), `evaluate_facilities`, `parse_chromosome`, `improvement_percent`, `load_metadata`, `load_scenario` (superseded by `scenario.loading`), `require_mapping` (superseded by `common.errors`), `load_current_network_from_scenario`, `validate_v0_seed_match`, `evaluate_archive`, `clean_solution_for_json`, `write_outputs` → `write_benchmark_outputs` | `parse_args()`; `main()`'s call sequence; console summary printing | `location_platform.data.candidates`, `location_platform.data.matrix`, `location_platform.scenario.loading`, `location_platform.common.paths`, `location_platform.common.parsing`, `location_platform.common.errors` | Yes — `python scripts/validation/benchmark_existing_vs_optimized.py --candidate-csv ... --distance-matrix ... --scenario ... --archive ... --metadata ... --output-dir ... [--validate-v0-seed-match]` unchanged, **at its current path** (Phase 0B's decision to retarget this folder to `scripts/benchmark/` is a separate, not-yet-scheduled rename — see Items Explicitly Deferred) | 6 (last domain module — largest script at ~758 lines, most output surface: JSON+CSV+Markdown report; independent of `scenario.optimizer_inputs`/`scenario.validation` — confirmed neither is called today) | Medium-high — the Turkish-language Markdown report template and exact CSV column ordering must be preserved verbatim; the strict/raising style of `load_current_network_from_scenario` must **not** be softened to match the adapter's lenient style (see Shared Logic Extraction Decisions) |

## Script Responsibility Decomposition

### `generate_default_current_network_scenario.py`

| Responsibility | Functions | Classification |
| --- | --- | --- |
| Argument parsing | `parse_args()` | CLI-only |
| Path resolution/formatting | `display_path()` | Reusable package logic (duplicate across all four scripts) |
| File loading | `load_existing_facility_rows()` (CSV read portion) | Reusable package logic |
| Numeric parsing | `parse_int()`, `parse_float()` | Reusable package logic (duplicate pattern) |
| Business/domain logic | `load_existing_facility_rows()` (existing_locker_count>0 filter + sort), `build_facility()`, `build_scenario()` | Reusable package logic — this *is* the V0-seed business rule, not CLI plumbing |
| Report/file writing | `write_scenario()` | Reusable package logic (JSON-write convention shared with the adapter's `--output`) |
| CLI orchestration + printing | `main()` | CLI-only |

Compatibility note: the `existing_locker_count > 0` filter here is the one place in the whole repository that is *supposed* to read `existing_locker_count` directly — it is the seed generator itself. This must not be "fixed" to read `scenario.facilities[]` (there would be nothing to seed from).

### `validate_scenario.py`

| Responsibility | Functions | Classification |
| --- | --- | --- |
| Argument parsing | `parse_args()` | CLI-only |
| Path resolution/formatting | `display_path()` | Reusable package logic (duplicate) |
| File loading | `load_json()`, `load_candidate_csv()` (I/O portion), `validate_distance_matrix()` (I/O portion) | Reusable package logic |
| Schema/model parsing | `add_missing_fields_errors()`, `is_integer()`, `is_numeric()`, `parse_csv_int()`, `parse_csv_float()` | Reusable package logic |
| Validation (business/domain logic) | `validate_constraints()`, `validate_grid_and_settings()`, `validate_facilities()`, `validate_current_network_seed()`, `validate_scenario()` | Reusable package logic — this is the schema/contract enforcement, not CLI plumbing |
| Compatibility behavior | The entire `--expect-current-network-seed` code path (`validate_current_network_seed()`, `CURRENT_NETWORK_SCENARIO_ID` constant) | Temporary V0 compatibility behavior — only meaningful for the one seeded scenario; should not expand to assume every future scenario has a V0 seed to check against |
| Output formatting | `print_warnings()` | CLI-only |
| CLI exit-code handling | `main()`'s `return 1` / `return 0` | CLI-only |

### `derive_optimizer_inputs.py`

| Responsibility | Functions | Classification |
| --- | --- | --- |
| Argument parsing | `parse_args()` | CLI-only |
| Path resolution/formatting | `display_path()` | Reusable package logic (duplicate) |
| File loading | `load_json()`, `load_candidate_ids()` | Reusable package logic |
| Schema/model parsing | `require_mapping()` | Reusable package logic (exact duplicate of `benchmark_existing_vs_optimized.py`'s function of the same name) |
| Business/domain logic | `resolve_active_existing_candidate_ids()`, `resolve_constraint_ids()`, `resolve_facility_count()`, `build_java_cli_args()`, `derive()` | Reusable package logic — this is the core scenario-to-CLI translation, the reason the module exists |
| Output formatting | JSON assembly inside `derive()` (the `result` dict), `main()`'s `json.dumps(...)` call | Split: the `result` dict shape is reusable package logic (it's the module's actual return contract); the `print()`/stdout call itself is CLI-only |
| CLI exit-code handling | `main()`'s `return 1` / `return 0` | CLI-only |

Compatibility note: this script's stdout-JSON-only contract (see risk note in the migration table) makes its CLI-only layer unusually thin and unusually load-bearing — the wrapper must not add any extra `print()` call ahead of the JSON dump.

### `benchmark_existing_vs_optimized.py`

| Responsibility | Functions | Classification |
| --- | --- | --- |
| Argument parsing | `parse_args()` | CLI-only |
| Path resolution/formatting | `resolve_path()`, `display_path()` | Reusable package logic (duplicate pattern, `resolve_path` has a project-root-relative twist not present elsewhere) |
| File loading | `load_candidates()` (I/O portion), `load_and_validate_matrix()` (I/O portion), `load_metadata()`, `load_scenario()` | Reusable package logic |
| Schema/model parsing | `finite_float()`, `nonnegative_integer()`, `require_mapping()`, `parse_chromosome()` | Reusable package logic |
| Validation (business/domain logic) | `load_candidates()` (uniqueness/blank checks), `load_and_validate_matrix()` (shape/companion-ID checks), `load_current_network_from_scenario()`, `validate_v0_seed_match()` | Reusable package logic — note `load_current_network_from_scenario` is strict/raising by design, not a validation-with-warnings style |
| Business/domain logic (benchmark math) | `evaluate_facilities()`, `improvement_percent()`, `evaluate_archive()` | Reusable package logic — `evaluate_facilities()` in particular is the one truly benchmark-exclusive computation (F1/F2) in this entire batch |
| Compatibility behavior | `validate_v0_seed_match()`, the `--validate-v0-seed-match` flag | Temporary V0 compatibility behavior — same status as `validate_scenario.py`'s `--expect-current-network-seed` |
| Report writing | `clean_solution_for_json()`, `write_outputs()` (the Turkish-language Markdown report generation) | Reusable package logic — but should move as a near-verbatim unit; the Markdown template text itself is a reporting artifact, not logic worth restructuring during this migration |
| CLI orchestration + printing | `main()` | CLI-only |

## Exact Target Modules

Per the "expected direction," confirmed correct and unchanged for the four primary targets, plus the shared modules justified by concrete duplication evidence (each used by 2 or more of the four first-batch scripts):

```text
python/src/location_platform/scenario/seed.py               (generate_default_current_network_scenario.py)
python/src/location_platform/scenario/validation.py          (validate_scenario.py)
python/src/location_platform/scenario/optimizer_inputs.py    (derive_optimizer_inputs.py)
python/src/location_platform/benchmark/current_network.py    (benchmark_existing_vs_optimized.py)

python/src/location_platform/scenario/loading.py              -- shared by 3 of 4: derive_optimizer_inputs.py,
                                                                   validate_scenario.py, benchmark_existing_vs_optimized.py
                                                                   (each has its own scenario-JSON-loading function today)
python/src/location_platform/data/candidates.py                -- shared by all 4: every script independently reads
                                                                   data/candidate_points.csv with its own column subset
python/src/location_platform/data/matrix.py                     -- shared by 2 of 4: validate_scenario.py and
                                                                   benchmark_existing_vs_optimized.py both load/validate
                                                                   the distance matrix, with benchmark's check strictly
                                                                   stronger (companion-ID cross-check)
python/src/location_platform/common/paths.py                   -- shared by all 4: display_path() is duplicated
                                                                   verbatim in every script (confirmed by grep)
python/src/location_platform/common/parsing.py                 -- shared by 3 of 4: generate_default_current_network_scenario.py,
                                                                   validate_scenario.py, benchmark_existing_vs_optimized.py
                                                                   each implement int/float coercion with error context
python/src/location_platform/common/errors.py                  -- shared by 2 of 4: derive_optimizer_inputs.py and
                                                                   benchmark_existing_vs_optimized.py both define an
                                                                   identically-named, identically-behaved require_mapping()
python/src/location_platform/common/io.py                      -- shared by 2 of 4 (borderline, see Work 5/Shared Logic
                                                                   Extraction Decisions): scenario JSON writing with the
                                                                   same indent=2 + trailing-newline convention appears in
                                                                   generate_default_current_network_scenario.py's
                                                                   write_scenario() and derive_optimizer_inputs.py's
                                                                   --output handling
```

No module is created without at least two first-batch scripts needing it. `location_platform.spatial` and `location_platform.orchestration` remain reserved per Phase 0B and are **not** touched by this batch — none of the four scripts need them.

## Proposed Public APIs

### `location_platform.common.paths`

- `display_path(path: Path) -> str` — POSIX-style path string for messages/output; no filesystem access.
- `resolve_path(value: str, project_root: Path) -> Path` — resolves a possibly-relative path string against `project_root`; absolute inputs pass through unchanged (matches `benchmark_existing_vs_optimized.py`'s current `resolve_path`).

Inputs: `Path`/`str`, optional root `Path`. Returns: `str` / `Path`. Raises: nothing (pure functions).
Must not own: CLI parsing, printing, process exit handling, any domain validation.

### `location_platform.common.parsing`

- `parse_int(value: Any, field: str, context: str) -> int` — raises `ValueError` with a contextual message on failure.
- `parse_float(value: Any, field: str, context: str) -> float` — raises `ValueError`.
- `finite_float(value: Any, label: str) -> float` — raises `ValueError` if not finite.
- `nonnegative_integer(value: Any, label: str) -> int` — raises `ValueError` if negative or non-integer.

Inputs: raw value + label/context strings for error messages. Returns: parsed `int`/`float`. Raises: `ValueError` always on invalid input — this module never silently collects errors; callers that want error-collection (like `scenario.validation`) wrap these calls in their own try/except and append to their own error list, preserving each caller's current UX without duplicating the coercion logic itself.
Must not own: CSV iteration, field-requirement business rules (which fields are required is a caller decision).

### `location_platform.common.errors`

- `require_mapping(value: Any, label: str) -> dict` — returns the dict if valid, raises `TypeError` otherwise.

Inputs: arbitrary value, label. Returns: `dict`. Raises: `TypeError` on non-dict input.
Must not own: any scenario-specific field knowledge — it only ever checks "is this a mapping," nothing about what keys a scenario/facility/settings object should have.

### `location_platform.common.io`

- `write_json_file(path: Path, data: Any, *, indent: int = 2, ensure_ascii: bool = False) -> None` — serializes with a trailing newline, creating parent directories as needed (matches both current writers' conventions).

Inputs: output path, JSON-serializable data. Returns: nothing. Raises: `OSError` on write failure (uncaught, same as today).
Must not own: deciding what data to write (that's the caller's business logic).

### `location_platform.data.candidates`

- `load_candidate_rows(csv_path: Path, *, columns: Sequence[str]) -> list[dict]` — reads with `utf-8-sig`, validates the requested columns exist, coerces requested numeric columns via `common.parsing`, returns rows in file order.
- `load_candidate_ids(csv_path: Path) -> set[int]` — thin convenience wrapper (today's `derive_optimizer_inputs.py` need: id-only).
- `validate_candidate_uniqueness(rows: list[dict]) -> None` — raises `ValueError` on duplicate `id` values.

Inputs: CSV path, required column list. Returns: `list[dict]` / `set[int]`. Raises: `FileNotFoundError`, `ValueError` (missing columns, parse errors, duplicate IDs, blank required fields).
Must not own: which rows "count" for a business purpose (e.g., "existing" filtering by `existing_locker_count > 0` stays in `scenario.seed`, since it's a seed-specific rule, not a generic loading concern).

### `location_platform.data.matrix`

- `load_matrix(matrix_path: Path) -> np.ndarray` — loads via `np.load(matrix_path, mmap_mode="r")`.
- `validate_matrix_shape(matrix: np.ndarray, candidate_count: int) -> tuple[int, tuple[int, int]]` — checks 2D, square, dimension equals `candidate_count`; returns `(dimension, shape)`.
- `validate_matrix_candidate_id_alignment(matrix_path: Path, sorted_candidate_ids: list[int]) -> str` — locates the companion `*_candidate_ids_sorted.npy` artifact and cross-checks it against `sorted_candidate_ids`; returns a human-readable alignment description. **This is `benchmark_existing_vs_optimized.py`'s stricter check; `validate_scenario.py` currently only calls the equivalent of `validate_matrix_shape`.** Both remain available as distinct functions — `validate_scenario.py`'s migrated wrapper is not required to start calling the stricter function unless a later task decides to strengthen it.

Inputs: matrix path, candidate count/sorted IDs. Returns: `np.ndarray` / shape tuple / description string. Raises: `FileNotFoundError`, `ValueError` (wrong shape, dimension mismatch, ID mismatch), `ImportError` (if NumPy is missing, matching `validate_scenario.py`'s current explicit check).
Must not own: candidate CSV loading (takes already-loaded candidate data/IDs as input); benchmark math.

### `location_platform.scenario.loading`

- `load_scenario_json(path: Path) -> dict` — raising variant: parses JSON, checks the root is an object. This is the **one** shared implementation; `derive_optimizer_inputs.py`'s and `benchmark_existing_vs_optimized.py`'s wrappers call it directly (both already raise on failure today), and `validate_scenario.py`'s wrapper calls it inside its own try/except to convert a raised exception into a single entry in its `errors` list — preserving its "collect everything, then report" UX without a second loader implementation.

Inputs: scenario JSON path. Returns: `dict`. Raises: `FileNotFoundError`, `json.JSONDecodeError`, `ValueError` (root not an object).
Must not own: schema-level field/enum validation (that's `scenario.validation`'s job) — this module only knows "is this parseable JSON shaped like an object."

### `location_platform.scenario.seed`

- `load_existing_facility_seed_rows(candidate_csv: Path) -> list[dict]` — calls `data.candidates.load_candidate_rows(...)`, filters to `existing_locker_count > 0`, sorts by candidate ID.
- `build_facility_from_seed_row(index: int, row: dict) -> dict` — constructs one `existing`-kind scenario facility dict.
- `build_current_network_scenario(candidate_csv: Path, facility_rows: list[dict]) -> dict` — constructs the full scenario dict (`schemaVersion`, `grid`, `settings`, `facilities`, `constraints`, `benchmark`, `metadata`).

Inputs: candidate CSV path, facility rows. Returns: scenario `dict`. Raises: `FileNotFoundError`, `ValueError` (missing columns, no qualifying rows).
Must not own: writing the file (that's `common.io.write_json_file`, called from the wrapper); scenario validation (does not self-check its own output — `validate_scenario` remains a separate, explicit step, exactly as today).

### `location_platform.scenario.validation`

- `validate_scenario(scenario: dict, candidate_data: dict, *, expect_current_network_seed: bool) -> tuple[dict, list[str], list[str]]` — the current orchestrator; returns `(facility_data, errors, warnings)`.
- `validate_current_network_seed_match(scenario: dict, candidate_data: dict, facility_data: dict) -> list[str]` — returns a list of errors (functional style) rather than appending to a passed-in list.
- `load_and_validate_scenario_file(scenario_path: Path, candidate_csv_path: Path, distance_matrix_path: Path, *, expect_current_network_seed: bool) -> tuple[dict, list[str], list[str]]` — convenience bundler matching the current script's `main()` sequence: loads scenario (catching `scenario.loading`'s raise into an error-list entry), loads candidates (`data.candidates`), loads/validates the matrix (`data.matrix`), then calls `validate_scenario`.

Inputs: scenario dict/paths, candidate/matrix data, flags. Returns: `(facility_data, errors, warnings)`. Raises: nothing by design — every failure becomes an entry in the returned `errors` list, matching this module's current "collect everything" contract exactly.
Must not own: CLI parsing/printing/exit codes; optimizer-input derivation (must not duplicate `scenario.optimizer_inputs`'s active-facility resolution — see Shared Logic Extraction Decisions for why these stay separate).

### `location_platform.scenario.optimizer_inputs`

- `derive_optimizer_inputs(scenario: dict, candidate_ids: set[int], *, force_existing_off: bool = False, override_target_total_facility_count: int | None = None) -> tuple[dict, list[str], list[str]]` — the current `derive()` function, unchanged signature and behavior.
- `resolve_active_existing_candidate_ids(facilities: list[Any], candidate_ids: set[int]) -> tuple[list[int], int, list[str]]` — the current **lenient** resolver (skips invalid facilities with a warning, keeps going).

Inputs: scenario dict, candidate ID set, override flags. Returns: `(result_dict, errors, warnings)`. Raises: nothing (matches today's non-raising `derive()`; only the wrapper's calls to `scenario.loading`/`data.candidates` can raise, exactly as in the current `main()`).
Must not own: CLI parsing/printing/exit codes; full scenario schema validation (this module's checks are a narrower, purpose-built subset — it is not a substitute for `scenario.validation` and must not attempt to become one).

### `location_platform.benchmark.current_network`

- `load_current_network_from_scenario(scenario: dict, candidates: list[dict]) -> tuple[list[dict], list[int], int, dict]` — the current **strict/raising** resolver (raises `ValueError` on the first invalid facility). Kept as a distinct function from `scenario.optimizer_inputs`'s lenient resolver — see Shared Logic Extraction Decisions.
- `evaluate_facilities(facility_ids: list[int], candidates: list[dict], matrix: np.ndarray, beta: float) -> tuple[float, float]` — the F1/F2 computation.
- `evaluate_archive(archive_path: Path, metadata_path: Path, candidates: list[dict], matrix: np.ndarray, beta: float, baseline_f1: float, baseline_f2: float, physical_existing_count: int) -> dict` — archive evaluation + representative-solution selection.
- `validate_v0_seed_match(scenario_existing_ids: list[int], scenario_physical_count: int, candidates: list[dict]) -> dict` — the benchmark script's own V0-seed cross-check.
- `write_benchmark_outputs(...) -> list[Path]` — the JSON/CSV/Markdown report writer, moved as a near-verbatim unit including the Turkish-language report template.

Inputs: scenario dict, candidate rows, matrix, archive/metadata paths, beta. Returns: baseline F1/F2 floats, archive evaluation dict, written output paths. Raises: `ValueError`/`FileNotFoundError` throughout — this module's fail-fast style is preserved exactly, not converted to error-list style, since that would be a behavior change beyond "move code."
Must not own: optimizer facility selection (only ever evaluates a given candidate set, never chooses one); scenario schema validation (delegates to `scenario.loading`/`data.candidates`/`data.matrix`).

## Compatibility Wrapper Map

All four existing command paths are **permanent** wrapper locations (not a temporary bridge — Phase 0B already decided `scripts/` paths, especially this one Next.js directly depends on, stay indefinitely as the CLI contract).

| Existing command | Wrapper retains | Package call sequence | Permanent or temporary |
| --- | --- | --- | --- |
| `python scripts/scenario/generate_default_current_network_scenario.py --candidate-csv ... --output ...` | `parse_args()`; final summary `print()` lines | `scenario.seed.load_existing_facility_seed_rows()` → `scenario.seed.build_facility_from_seed_row()` (per row, inside `build_current_network_scenario`) → `scenario.seed.build_current_network_scenario()` → `common.io.write_json_file()` | Permanent |
| `python scripts/scenario/validate_scenario.py --scenario ... --candidate-csv ... --distance-matrix ... [--expect-current-network-seed]` | `parse_args()`; `print_warnings()`; pass/fail summary printing; `return 1`/`return 0` | `scenario.validation.load_and_validate_scenario_file()` | Permanent |
| `python scripts/scenario/derive_optimizer_inputs.py --scenario ... --candidate-csv ... [--force-existing-off] [--override-target-total-facility-count N] [--output ...]` | `parse_args()`; stdout JSON `print()` (exact, first and only stdout write); stderr warning/error printing; optional `--output` write via `common.io.write_json_file()`; `return 1`/`return 0` | `scenario.loading.load_scenario_json()` + `data.candidates.load_candidate_ids()` → `scenario.optimizer_inputs.derive_optimizer_inputs()` | Permanent — **and the single highest-priority compatibility target**, because `scenario-adapter.ts` parses this script's stdout as JSON today |
| `python scripts/validation/benchmark_existing_vs_optimized.py --candidate-csv ... --distance-matrix ... --scenario ... --archive ... --metadata ... --output-dir ... [--validate-v0-seed-match]` | `parse_args()`; console summary `print()` lines | `data.candidates.load_candidate_rows()` → `data.matrix.load_matrix()` + `validate_matrix_shape()` + `validate_matrix_candidate_id_alignment()` → `scenario.loading.load_scenario_json()` → `benchmark.current_network.load_current_network_from_scenario()` → `benchmark.current_network.validate_v0_seed_match()` (if flag set) → `benchmark.current_network.evaluate_facilities()` (baseline) → `benchmark.current_network.evaluate_archive()` → `benchmark.current_network.write_benchmark_outputs()` | Permanent at its **current path** for this batch; a folder rename to `scripts/benchmark/` was decided in principle in Phase 0B but is not scheduled by this task (see Items Explicitly Deferred) |

## Shared Logic Extraction Decisions

| Duplicate area | Found in | Decision | Reasoning |
| --- | --- | --- | --- |
| Candidate CSV loading | All 4 scripts, each with a different column subset and a different error style (raise vs. collect) | **Shared package module** (`data.candidates.load_candidate_rows`) | The CSV-reading mechanics (utf-8-sig, column-existence checks, numeric coercion, uniqueness) are identical low-level work repeated four times; each caller's business use of the result (seed-filtering, benchmark columns, id-only set) stays local to its own module |
| Candidate ID parsing | Generate, validate, benchmark scripts | **Shared** (`common.parsing`) | Pure mechanical numeric coercion with contextual error messages; no domain knowledge |
| Candidate uniqueness validation | `validate_scenario.py`, `benchmark_existing_vs_optimized.py` | **Shared** (`data.candidates.validate_candidate_uniqueness`) | Identical check ("no duplicate `id` values"), no semantic difference between the two call sites |
| Matrix loading | `validate_scenario.py`, `benchmark_existing_vs_optimized.py` | **Shared module, two distinct functions preserved** (`data.matrix.validate_matrix_shape` weaker, `validate_matrix_candidate_id_alignment` stricter) | The two current checks are genuinely different strength; collapsing them to the stronger one would silently change `validate_scenario.py`'s behavior, which this migration must not do |
| Candidate/matrix alignment validation | Same as above | Folded into `data.matrix`, same two-function split | Same reasoning |
| Scenario JSON loading | All 3 scenario-facing scripts (generate script does not load a scenario file — it produces one) | **Shared, one implementation** (`scenario.loading.load_scenario_json`), always raising | `derive_optimizer_inputs.py` and `benchmark_existing_vs_optimized.py` already raise on failure; `validate_scenario.py`'s error-collection style is preserved by catching the raise at its own call site, not by adding a second, non-raising loader implementation |
| Scenario facility filtering ("active existing candidates") | `derive_optimizer_inputs.py` (lenient: skip-and-warn) vs. `benchmark_existing_vs_optimized.py` (strict: raise on first invalid facility) | **Do not merge — two distinct public functions, both in their respective modules** (`scenario.optimizer_inputs.resolve_active_existing_candidate_ids` vs. `benchmark.current_network.load_current_network_from_scenario`) | This is the one area where the two implementations' *contracts* genuinely differ on purpose: a UI-driven optimizer run should surface warnings and keep going; a benchmark computing baseline F1/F2 numbers must not silently proceed with a wrong candidate set. Per the task's explicit instruction not to merge superficially similar logic with differing contracts, these stay separate — extracting only the shared low-level field-reading mechanics (parsing `kind`/`status`/`snap`/`metadata.physicalCount` off one facility dict) would be possible but is not required for this batch, since it duplicates only a small, low-risk parsing loop |
| V0 seed-match checking | `validate_scenario.py`'s `validate_current_network_seed`/`--expect-current-network-seed` vs. `benchmark_existing_vs_optimized.py`'s `validate_v0_seed_match`/`--validate-v0-seed-match` | **Remain separate, both moved as-is** (`scenario.validation.validate_current_network_seed_match` vs. `benchmark.current_network.validate_v0_seed_match`) | Same reasoning as above — one is error-collecting (schema validator style), one is raising (benchmark style); both are already narrow, V0-compatibility-specific checks that should not become a third shared abstraction just because their *purpose* (compare scenario against `existing_locker_count` seed rows) sounds similar |
| Warnings structure | `derive_optimizer_inputs.py`, `validate_scenario.py` (both plain `list[str]`) | **Remain local, not extracted** | A list of strings is not complex enough to warrant a shared abstraction; a "shared warnings module" would be overhead without payoff |
| Path defaults (`DEFAULT_SCENARIO`, `DEFAULT_CANDIDATE_CSV`, `DEFAULT_DISTANCE_MATRIX`) | 3 of 4 scripts declare the same string literals independently | **Shared, low-priority** — module-level constants in whichever package module owns the concept (e.g., `scenario.loading.DEFAULT_SCENARIO_PATH`) | Trivial to fix, but genuinely duplicated literals that could drift if the default scenario path ever changes; include in the same batch since it's nearly free |
| `require_mapping` | `derive_optimizer_inputs.py`, `benchmark_existing_vs_optimized.py` — identical name, identical implementation | **Shared, exact duplicate** (`common.errors.require_mapping`) | Confirmed byte-for-byte identical purpose in both scripts; the strongest single piece of evidence for a `common.errors` module |
| JSON serialization (write with `indent=2` + trailing newline) | `generate_default_current_network_scenario.py`'s `write_scenario`, `derive_optimizer_inputs.py`'s `--output` handling | **Shared, low-priority** (`common.io.write_json_file`) | Borderline (only 2 call sites, both trivial), but the trailing-newline convention is a real repeated detail worth capturing once rather than twice |

## Phase 1 Dependency Order

Adjusted from the task's recommended pattern with one repository-specific refinement: `scenario.seed` is placed **after** `scenario.validation` rather than in parallel, because seed's output is exactly what validation's `--expect-current-network-seed` mode checks — having the validator ready first means the migrated seed script's output can be immediately re-validated with the migrated validator as a live sanity check during the migration itself, not just in a separate later test pass.

```text
1. Package skeleton + packaging metadata (python/pyproject.toml, src/location_platform/__init__.py, editable install)
     -> no dependencies; must exist before anything else

2. common/* + data/* primitives
     common.paths, common.parsing, common.errors, common.io   (no intra-batch dependencies beyond stdlib)
     data.candidates, data.matrix                              (depend on common.parsing, common.errors)
     -> everything else in this batch depends on this step

3. scenario.loading
     -> depends only on step 2 (common.errors for the "is this an object" check)
     -> establishes the one shared scenario-JSON-loading contract used by steps 4-6

4. scenario.validation
     -> depends on scenario.loading, data.candidates, data.matrix, common.errors, common.parsing
     -> independent of scenario.seed, scenario.optimizer_inputs, benchmark.current_network

5. scenario.seed
     -> depends on data.candidates, common.io, common.paths, common.parsing
     -> deliberately sequenced after step 4 (see refinement above), not because of a real code dependency
     -> independent of scenario.optimizer_inputs, benchmark.current_network

6. scenario.optimizer_inputs
     -> depends on scenario.loading, data.candidates, common.errors
     -> independent of scenario.validation and scenario.seed (confirmed: derive_optimizer_inputs.py calls neither today)
     -> HIGHEST-RISK step due to the scenario-adapter.ts stdout-JSON dependency; migrate and verify this module's
        wrapper output byte-for-byte before moving on, even though its package-level dependencies are simple

7. benchmark.current_network
     -> depends on data.candidates, data.matrix, scenario.loading
     -> independent of scenario.optimizer_inputs and scenario.validation (confirmed: benchmark_existing_vs_optimized.py
        calls neither today — it has its own load_current_network_from_scenario and validate_v0_seed_match)
     -> largest single module (report writer + Turkish-language template); last domain module for that reason

8. Thin wrappers, converted in the same order their package modules landed
     (validate_scenario.py's wrapper first, then generate_default_current_network_scenario.py's, then
      derive_optimizer_inputs.py's, then benchmark_existing_vs_optimized.py's)
     -> each wrapper can be smoke-tested immediately after its dependency module is ready, rather than
        waiting for all four package modules before touching any wrapper

9. Tests and compatibility validation
     -> python/tests/ unit tests per module
     -> python scripts/scenario/validate_scenario.py --expect-current-network-seed (already an allowed,
        documented lightweight check) re-run against the migrated wrapper
     -> byte-for-byte diff of derive_optimizer_inputs.py's stdout JSON, before vs. after migration, for the
        shipped scenario file — the concrete way to guarantee scenario-adapter.ts sees zero change
```

Modules that can be built in any relative order to each other once their shared dependencies exist: `scenario.validation`, `scenario.seed`, `scenario.optimizer_inputs`, and `benchmark.current_network` do not call one another. The only real ordering constraints are "common/data before everything" and "scenario.loading before the three scenario-facing/benchmark modules."

## Items Explicitly Deferred

- **`scripts/validation/` → `scripts/benchmark/` folder rename.** Phase 0B decided this in principle (to match the `location_platform.benchmark` module name) but explicitly left its sequencing to "Phase 0C/1 execution." This task does not schedule it — the migration table above places the benchmark script's wrapper at its **current** path (`scripts/validation/benchmark_existing_vs_optimized.py`) for this batch. The rename, if and when it happens, is a separate, low-risk follow-up that does not require touching any package module.
- **`data/prepare_ga_inputs.py` → `scripts/data/prepare_ga_inputs.py` retarget.** Also a Phase 0B decision, also out of scope — `prepare_ga_inputs.py` is not one of the four first-batch scripts.
- Exact file layout inside each target module beyond the public functions listed above (e.g., whether `scenario/validation.py` is one file or splits into `validation/schema.py` + `validation/seed_match.py`) — an implementation-time decision, not an architectural one.
- Whether `common.io`'s trailing-newline convention is formalized as a documented project-wide standard, or stays an implementation detail of the two current callers.
- Any second-batch script (`prepare_demand.py`, `prepare_candidate_existing_lockers.py`, `plot_archives.py`, `statistical_analysis.py`, research scripts, UI conversion scripts) — entirely out of scope per the task.
- Whether `scenario.optimizer_inputs.resolve_active_existing_candidate_ids` and `benchmark.current_network.load_current_network_from_scenario` should eventually share a low-level field-parsing helper (see Shared Logic Extraction Decisions) — flagged as possible but not required, left for a future cleanup pass once both modules exist and their real-world usage patterns are clearer.

## Inputs Required for Phase 0C2

- This document's exact target-module list and public API signatures, to write actual implementation code against.
- The dependency order above, to sequence pull requests/commits so nothing imports a module that doesn't exist yet.
- The Compatibility Wrapper Map, to know exactly what each wrapper script's post-migration body must contain (and, for `derive_optimizer_inputs.py`, the explicit instruction to verify stdout byte-for-byte before considering that wrapper done).
- The Shared Logic Extraction Decisions table, so Phase 0C2 does not "simplify" the two facility-filtering resolvers or the two seed-match checkers into one function each — both pairs are intentionally kept separate.
- Confirmation (not yet obtained, and not needed for this document) of which Python packaging backend (`setuptools` vs. `hatchling`) Phase 0C2 will use for `python/pyproject.toml` — flagged in Phase 0B as a deferred implementation detail.
- A concrete plan for validating the `derive_optimizer_inputs.py` wrapper's stdout equivalence (e.g., run both old and new versions against `data/scenarios/kadikoy_parcel_locker_current_network.json` and diff), since this is the single highest-risk compatibility point identified in this batch.

## Phase 0C1 Acceptance Checklist

- [x] All four scripts have exact target modules (`scenario.seed`, `scenario.validation`, `scenario.optimizer_inputs`, `benchmark.current_network`, plus the justified shared modules).
- [x] Reusable logic and CLI logic are separated conceptually for every one of the four scripts (see Script Responsibility Decomposition).
- [x] Proposed public APIs are explicit for all eight target modules (four primary + four shared), including inputs, returns, raises, and "must not own" boundaries.
- [x] Existing CLI paths remain supported — every current command is listed unchanged in the Compatibility Wrapper Map, with the `derive_optimizer_inputs.py` stdout-JSON contract flagged as the highest-priority compatibility risk.
- [x] Duplicate logic has one agreed owner for every area checked, including the two areas explicitly **not** merged (facility filtering, seed-match checking) with reasoning for why they stay separate.
- [x] Migration dependency order is clear, including which modules are independent of each other and which have a real (vs. merely suggested) dependency.
- [x] Later scripts (`prepare_demand.py`, `calculate_poi_weights.py`, `prepare_candidate_existing_lockers.py`, `plot_archives.py`, `statistical_analysis.py`, research scripts, UI conversion scripts) are explicitly excluded from this batch.
- [x] No code or runtime file was changed — only `docs/PHASE_0_REPO_CLEANUP_PLAN.md` was updated.

---

## Phase 0C2 Objective

Phase 0C1 named the first migration batch's exact target modules and public APIs. Phase 0C2 defines exactly how Phase 1 will carry out that migration **without breaking anything that currently works** — the packaging bootstrap, interpreter compatibility, an explicit compatibility contract per script, a safe copy-then-switch migration method, a concrete validation matrix with real numbers pulled from this repository, parity criteria, a rollback plan that does not depend on git history, hard stop conditions, and an anti-overengineering check applied retroactively to Phase 0C1's proposed shared modules. No package was created, no file was moved, and no code was changed to produce this document — every number below was obtained by reading already-committed files or re-running already-existing, already-allowed lightweight commands (`validate_scenario.py --expect-current-network-seed`, reading `output/validation/existing_vs_optimized_benchmark_summary.json`), never by regenerating data or running Java/GA.

## Packaging Bootstrap Decision

**Build backend: `setuptools`.** A basic `setuptools`-based `pyproject.toml` is sufficient — `[build-system] requires = ["setuptools>=68"]`, `build-backend = "setuptools.build_meta"`, with `[tool.setuptools.packages.find] where = ["src"]` to support the `python/src/location_platform/` src-layout Phase 0B already chose. `hatchling`/`poetry`/`flit` are explicitly rejected: none is already used anywhere in this repository, and the task's own instruction ("prefer a minimal standard solution," "do not add unnecessary packaging tools") is best satisfied by the backend every Python developer already has via `pip`.

**Minimum supported Python version: 3.10** (`requires-python = ">=3.10"`). Reasoning, not a guess: all four first-batch scripts already use `from __future__ import annotations` plus PEP 604 union syntax (`int | None`, `tuple[int, ...] | None`, etc.) in their type hints — a style that already assumes a 3.10-oriented mental model even though the deferred-annotation import keeps the *source* parseable on somewhat older interpreters too. The interpreter actually present on this machine is 3.13.2 (confirmed: `python --version` → `Python 3.13.2`). No script anywhere in the repository pins an older floor. Declaring `>=3.10` in `python/pyproject.toml` makes an assumption the code already silently makes into an explicit, checked constraint.

**Package (distribution) name: `location-platform`** — the PEP 503 normalized/hyphenated form of the import name `location_platform` that Phase 0B already selected. This is standard packaging convention (distribution name uses hyphens for `pip`/PyPI-style tooling; the importable name uses underscores), not a new naming decision.

**Editable-install command — corrected rule (Phase 0D1): resolve-then-install, not a single unconditionally "canonical" command.**

An earlier version of this section stated `python -m pip install -e .\python` was always sufficient. That is not reliably true and is corrected here: what matters is that the package is installed using **the same interpreter Next.js will actually spawn**, not whichever of `python`/`py` a developer happens to type first. `parcel-locker-ui/src/lib/python-runner.ts`'s `detectPythonCommand()` resolves, in order, `process.env.PYTHON_CMD` → `py` → `python` (Windows) — and this repository has confirmed PATH ambiguity today: `where.exe python` resolves **two** distinct executables (`C:\Program Files\Python313\python.exe` and a Windows-Store-alias stub under `...\WindowsApps\python.exe`), plus a separate `py.exe` launcher. Installing under whichever command "feels canonical" without checking which one `detectPythonCommand()` will actually pick risks a silent `ModuleNotFoundError` at runtime even though the install itself reported success.

The canonical **procedure** (not a single canonical command) is:

```text
1. Resolve the interpreter used by the current runtime — i.e., replicate what
   detectPythonCommand() would pick: check $env:PYTHON_CMD first; if unset,
   the first of `py` / `python` (in that order, on Windows) that responds to
   `--version` is the one that will actually be spawned.
2. Verify its sys.executable:
       <resolved-python-command> -c "import sys; print(sys.executable)"
3. Install with that same interpreter:
       <resolved-python-command> -m pip install -e .\python
4. Verify location_platform imports through that same interpreter:
       <resolved-python-command> -c "import location_platform; print(location_platform.__file__)"
```

Both forms remain valid **examples**, but neither is chosen blindly — the one that matches step 1's resolution is the one to use for a given machine/environment:

```powershell
py -m pip install -e .\python
python -m pip install -e .\python
```

On this machine, both `py --version` and `python --version` currently report the same interpreter (`3.13.2`), so either happens to work today — but that is a property of this machine's current PATH state, not a guarantee, and must not be assumed on a machine with more than one Python version registered. This task does not change `runtime-config.ts`/`python-runner.ts` or introduce a new environment variable to make this fully automatic — that remains a later implementation decision, consistent with Phase 0C2's Python Interpreter Compatibility Plan.

**Test runner: `pytest`.** No test runner or test folder exists anywhere in the repository today (confirmed: no `pytest.ini`, `conftest.py`, or existing test directory was found in any discovery pass across Phase 0A/0B/0C1). `pytest` should be declared as a `python/pyproject.toml` optional/dev dependency (e.g., `[project.optional-dependencies] test = ["pytest"]`), not added to the root `requirements.txt`, since it is a package-development tool, not a runtime dependency of the scripts/UI pipeline.

**Runtime dependencies for `python/pyproject.toml` (first batch only) — confirmed by direct import inspection:** only `numpy`. `generate_default_current_network_scenario.py` and `derive_optimizer_inputs.py` import nothing beyond the standard library (`argparse`, `csv`, `json`, `sys`, `pathlib`, `typing`). `validate_scenario.py` imports `numpy` lazily, inside `validate_distance_matrix()`, with an explicit `ImportError` catch if it's missing. `benchmark_existing_vs_optimized.py` imports `numpy` at module level (required). **`pandas` is not imported by any of the four first-batch scripts** — it is only used by later-batch scripts (`prepare_demand.py`, `calculate_poi_weights.py`). `python/pyproject.toml`'s first-batch dependency list should therefore declare `numpy` only, not the full `requirements.txt` set.

**Whether `requirements.txt` remains authoritative temporarily: yes.** It continues to describe what the *existing* scripts/UI-triggered pipeline needs (`pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn` — none of which have version pins today, confirmed by reading the file). `python/pyproject.toml` is additive, not a replacement; whether the two should eventually be unified (e.g., `requirements.txt` becomes `pip install -e ./python[full]` or similar) is a later decision, not made here.

## Python Interpreter Compatibility Plan

**Current Python command resolution** (from `parcel-locker-ui/src/lib/python-runner.ts`'s `detectPythonCommand()`, read but not modified): checks `process.env.PYTHON_CMD` first (confirmed blank by default — `.env.example` has `PYTHON_CMD=` with no value); if unset, tries `py` then `python` on Windows (verified via a `--version` spawn probe), using whichever responds first.

**Confirmed Windows PATH ambiguity (concrete evidence from this environment, not a hypothetical):**

```text
where.exe python  ->  C:\Program Files\Python313\python.exe
                      C:\Users\sezow\AppData\Local\Microsoft\WindowsApps\python.exe
where.exe py       ->  C:\Windows\py.exe
python --version   ->  Python 3.13.2
py --version       ->  Python 3.13.2
```

Three distinct resolvable executables exist on PATH today. On *this* machine they currently agree (all report 3.13.2), so there is no live skew — but this is exactly the mechanism by which "the interpreter that installed `location_platform`" and "the interpreter `runPythonScript` spawns" could diverge on a machine with more than one Python version registered (e.g., a developer manually running `pip install -e ./python` under a `python3.11` alias while `py`/`python` on PATH default to 3.13).

**How to identify the actual interpreter in use** (confirmed working on this machine):

```powershell
python -c "import sys; print(sys.executable)"
```

Ran during this task: prints `C:\Program Files\Python313\python.exe`.

**How editable installation is verified in that interpreter** (using the package name decided above):

```powershell
python -c "import location_platform; print(location_platform.__file__)"
python -m pip show location-platform
```

Both commands were dry-run during this task against the *current, unmigrated* repository: `python -m pip show location-platform` correctly reports `WARNING: Package(s) not found: location-platform` (exit code 1) — confirming the diagnostic command behaves as expected before the package exists, which is the negative-control check this plan needs.

**What environment/configuration mismatch causes `ModuleNotFoundError`:** running the editable install under `py -m pip install -e .\python` (which resolves via the Python Launcher's own version-selection rules) while `runPythonScript` on a given machine actually spawns a *different* registered interpreter than the launcher's default — or a developer manually installing under an explicit interpreter path while `PYTHON_CMD` is set to a different one in `.env`/the process environment. Both are named, concrete failure modes, not generic caveats.

**No new environment variables or runtime configuration are introduced by this task.** If Phase 1 implementation later decides a dedicated `LOCATION_PLATFORM_PYTHON`-style override (mirroring `PYTHON_CMD`) is warranted to pin exactly which interpreter runs `location_platform`, that is explicitly marked as a **later implementation decision** — not decided, and not implemented, here.

## Backward Compatibility Contracts

| Script | File path | CLI flags | Default paths | stdout | stderr | Exit codes | Generated files | JSON/report schema | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `generate_default_current_network_scenario.py` | Stable, permanent | `--candidate-csv`, `--output` — stable | `data/candidate_points.csv`, `data/scenarios/kadikoy_parcel_locker_current_network.json` — stable | Human-readable summary lines only (not machine-parsed by any known caller) | Not currently used for diagnostics (script has no separate stderr path today) | Implicit 0 on success; exceptions propagate uncaught (unchanged) | The written scenario JSON's field names/shape — stable | `schemaVersion`, `scenarioId`, `grid`, `settings`, `facilities[]`, `constraints`, `benchmark`, `metadata` — all stable | N/A (script has no warnings mechanism today) |
| `validate_scenario.py` | Stable, permanent | `--scenario`, `--candidate-csv`, `--distance-matrix`, `--expect-current-network-seed` — stable | `data/scenarios/kadikoy_parcel_locker_current_network.json`, `data/candidate_points.csv`, `data/kadikoy_distance_meters_nxn.npy` — stable | Pass/fail summary + counts (human-readable; no known machine consumer) | Not separately used (all output goes to stdout today) | `1` on validation errors, `0` on success — stable | None (validator writes no files) | N/A (no JSON output) | `print_warnings()` output — semantic content (which check produced a warning) must be preserved; exact wording may evolve |
| `derive_optimizer_inputs.py` | Stable, permanent — **highest-priority path**, hardcoded in `runtime-config.ts`'s `scenarioAdapterScriptPath` | `--scenario`, `--candidate-csv`, `--output`, `--force-existing-off`, `--override-target-total-facility-count` — stable | `data/scenarios/kadikoy_parcel_locker_current_network.json`, `data/candidate_points.csv` — stable | **Machine-readable JSON only — see dedicated contract below** | Warnings (`warning: ...`) and errors (`error: ...`) — human-readable, consumed today only by a human reading a terminal, not parsed by `scenario-adapter.ts` | `1` on derivation errors, `0` on success — stable, and directly observed by `scenario-adapter.ts`'s subprocess-exit handling via `runPythonScript` | Optional `--output` file, same JSON shape as stdout — stable | Every key currently in the `result` dict (`scenarioId`, `runType`, `existingEnabled`, `facilityCountMode`, `optimizerRunRequired`, `targetNewFacilityCount`, `targetTotalFacilityCount`, `resolvedK`, `activeExistingCandidateIds`, `lockedCandidateIds`, `disabledCandidateIds`, `effectiveFixedCandidateIds`, `physicalFacilityCount`, `effectiveFacilityLocationCount`, `javaCliArgs`, `dataSemantics`, `metadata`, `warnings`, `scenarioPath`) — **all must remain present**; new keys may be added | `result["warnings"]` (a `list[str]`) — read by `ga-runner.ts`'s `buildScenarioSummary()` as `adapterWarnings`; must remain a list of strings |
| `benchmark_existing_vs_optimized.py` | Stable, permanent at its **current path** (`scripts/validation/`) for this batch — the `scripts/benchmark/` rename is a separate, deferred action (Phase 0B) | `--candidate-csv`, `--distance-matrix`, `--scenario`, `--archive`, `--metadata`, `--output-dir`, `--validate-v0-seed-match` — stable | `data/candidate_points.csv`, `data/kadikoy_distance_meters_nxn.npy`, `data/scenarios/kadikoy_parcel_locker_current_network.json`, `output/final_archive.csv`, `output/run_metadata.json`, `output/validation/` — stable | Console summary (human-readable; no known machine consumer) | Not separately used today | Implicit 0 on success; exceptions propagate uncaught (unchanged) | `existing_vs_optimized_benchmark_summary.{json,csv}`, `existing_vs_optimized_benchmark_report.md`, `existing_current_placement_ids.csv` — filenames and column/field layout stable, including the Turkish-language Markdown report template text | Same JSON/CSV field names as today (`baseline.f1`, `baseline.f2`, `scenarioMetadata.*`, `optimizedArchive.*`, etc.) | N/A (this script raises on problems rather than collecting warnings) |

**Rule for all four wrappers:** none may rely on fragile repository-relative `sys.path` modification (e.g., `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python" / "src"))`) as the *normal* operating mechanism. The correct mechanism is the editable pip install described above — a wrapper that only works because it manually manipulates `sys.path` is a sign the packaging bootstrap is broken, not a valid permanent pattern (this directly extends Phase 0B's "avoiding sys.path hacks" requirement from the package-location decision to the wrapper layer as well).

### `derive_optimizer_inputs.py`'s stdout contract (dedicated, non-negotiable)

Because `parcel-locker-ui/src/lib/server/scenario-adapter.ts`'s `deriveOptimizerInputsFromScenario()` does `JSON.parse(stdout)` on this script's **entire** stdout stream today (confirmed by reading the current TypeScript source), the migrated wrapper's contract is:

- stdout contains **machine-readable JSON only** — one `json.dumps(...)` call, nothing else, ever printed to stdout;
- all diagnostics/logging (warnings, errors, progress messages) go to **stderr**, exactly as today (`warning: ...` / `error: ...` prefixes may stay or be revisited, but must not migrate to stdout);
- every JSON key currently present in the `result` dict remains present (listed exhaustively in the table above) — keys may be **added**, never silently removed or renamed;
- exit-code behavior remains stable: `0` on success (valid JSON on stdout), `1` on any derivation error (no JSON printed to stdout in that case — matching today's `if errors: ... return 1` path, which never reaches the `print(output_json)` line);
- **no extra text before or after the JSON** — no banner, no trailing newline-plus-message, nothing that would make `JSON.parse` fail or silently parse a truncated fragment.

## Safe Migration Method

**Copy-then-switch is the appropriate pattern here**, for a concrete, repository-specific reason: zero automated tests exist today for any of the four scripts (confirmed across every prior discovery pass), and one of them (`derive_optimizer_inputs.py`) has a live, real TypeScript consumer. With no existing test suite as a safety net, the only trustworthy way to know a migrated module behaves identically is to run the **old** implementation and the **new** package-backed wrapper side by side and compare — which requires the old implementation to still physically exist (in code, not just in git history) until that comparison passes. Migrating all four wrappers in a single unverified change would mean discovering a regression only after everything has already changed, with no cheap way to isolate which of the four broke it.

Applying the general 7-step pattern to Phase 0C1's dependency order, in five implementation batches:

```text
Batch 1 — Package bootstrap + shared primitives
  - python/pyproject.toml, src/location_platform/__init__.py, editable install
  - common.paths, common.parsing, data.candidates, data.matrix (post-consolidation set — see
    Anti-Overengineering Rule below)
  - Package-level unit tests only; no wrapper touched yet; no existing script's behavior changes

Batch 2 — Scenario loading and validation
  - scenario.loading, scenario.validation
  - Convert validate_scenario.py's wrapper; keep its original function bodies present but
    unreferenced until Validation Matrix row 3 passes; only then remove the duplicate

Batch 3 — Scenario seed
  - scenario.seed
  - Convert generate_default_current_network_scenario.py's wrapper; validate against a
    temporary --output path (never the committed data/scenarios/ file — see Validation Matrix
    row 6); only then remove the duplicate

Batch 4 — Optimizer-input derivation (highest risk — isolated as its own batch)
  - scenario.optimizer_inputs
  - Convert derive_optimizer_inputs.py's wrapper; run every synthetic case from Phase 0C1
    (expansion, greenfield, force-existing-off, locked/disabled conflict, malformed scenario)
    plus a byte-for-byte stdout diff against the pre-migration script for the shipped scenario;
    only then remove the duplicate; only then is scenario-adapter.ts's dependency considered safe

Batch 5 — Benchmark logic
  - benchmark.current_network
  - Convert benchmark_existing_vs_optimized.py's wrapper; validate against the already-committed
    output/final_archive.csv within numeric tolerance (see Validation Matrix row 7); only then
    remove the duplicate
```

This preserves Phase 0C1's dependency order exactly (package → common/data → scenario.loading → scenario.validation → scenario.seed → scenario.optimizer_inputs → benchmark.current_network → wrappers → tests), merely grouping it into five checkpoint batches instead of nine finer steps, since Batches 2-5 each already end with "convert this one wrapper and verify it" as their own internal checkpoint.

## Validation Matrix

| Migration unit | Behavior to preserve | Command/check | Expected result | Forbidden expensive check | Failure severity |
| --- | --- | --- | --- | --- | --- |
| Package bootstrap | `location_platform` importable from the editable install | `python -c "import location_platform; print(location_platform.__file__)"` | Path resolves under `python/src/location_platform/` | None needed — already minimal | Blocking — nothing downstream can proceed |
| Common/data primitives | New helpers produce identical values to today's inline implementations | `pytest python/tests/test_common.py python/tests/test_data.py` (new unit tests against known fixture values, e.g. candidate ID 672's row) | All assertions pass | Do not reload the full 2,717-row CSV/matrix repeatedly in a tight loop — one load per test session is enough | Blocking for downstream modules only |
| Scenario validation | Exact printed counts | `python scripts/scenario/validate_scenario.py --expect-current-network-seed` | Confirmed via direct execution this session: `candidate count: 2717`, `facility count: 26`, `physical facility count: 27`, `matrix dimension: 2717`, `warnings: 0`, exit code `0` | Do not regenerate the distance matrix or candidate CSV "to double check" — read-only validation against the already-committed files is sufficient | Blocking — any count mismatch means the migrated validator disagrees with the committed scenario/grid |
| Optimizer-input adapter — current network | Exact JSON shape and resolved values for the shipped scenario | `python scripts/scenario/derive_optimizer_inputs.py --scenario data/scenarios/kadikoy_parcel_locker_current_network.json --candidate-csv data/candidate_points.csv` | Confirmed via direct execution this session: `physicalFacilityCount: 27`, `effectiveFacilityLocationCount: 26`, `activeExistingCandidateIds` length `26`, `optimizerRunRequired: false`, `facilityCountMode: "current_network"`, `resolvedK: null`, `javaCliArgs: null` | Do not invoke Java/Maven to "confirm" the derived `k`/`fixedFacilityIds` would run correctly — this checks derivation only | **Blocking, highest priority** — this exact JSON is parsed by `scenario-adapter.ts` |
| Optimizer-input adapter — synthetic modes | Same resolution logic across every branch, not just the default scenario | Re-run the same synthetic scratch-scenario JSON cases already exercised during the adapter's original build this session: expansion (existing ON + `targetNewFacilityCount=5` → `k=5`), greenfield (existing OFF + `targetTotalFacilityCount=27` → `k=27`, no fixed ids), `--force-existing-off` on the shipped scenario (→ empty active set), locked==disabled==672 (→ exit 1 conflict), a scenario missing `facilities` (→ exit 1, clear message) | Identical behavior to the pre-migration adapter's already-recorded outputs for each case | Do not run Java/GA for any synthetic case — these test derivation logic only | Blocking for expansion/greenfield/conflict (core contract); the malformed-scenario case is blocking only on "exits non-zero with a clear message," not exact wording |
| Scenario seed generator | Same facility count/candidate IDs/schema as the committed scenario, without overwriting it | `python scripts/scenario/generate_default_current_network_scenario.py --candidate-csv data/candidate_points.csv --output <scratch path outside the repo, e.g. this session's scratchpad>`, then diff for semantic equality against the committed `data/scenarios/kadikoy_parcel_locker_current_network.json` | `26` effective facility locations, `27` physical facilities, identical sorted candidate ID list to the committed scenario | **Never** point `--output` at the committed `data/scenarios/` path during validation — that would silently overwrite committed scenario data | Blocking — any divergence means either the migration broke something or `candidate_points.csv` changed since the scenario was seeded; either way, stop and investigate |
| Benchmark | Same F1/F2 baseline within tolerance, same physical/effective counts | Run against the already-committed `output/final_archive.csv`/`output/run_metadata.json`, writing to a **scratch `--output-dir`**, not `output/validation/` | Confirmed by reading the already-committed `output/validation/existing_vs_optimized_benchmark_summary.json` this session: `physicalExistingLockerCount: 27`, `effectiveExistingCandidateCount: 26`, baseline `f1: 0.6650755521778244`, baseline `f2: 1.1419211244863716` — numeric tolerance: absolute difference ≤ `1e-9` (a pure code relocation should reproduce identical floating-point results; anything larger indicates an actual behavioral change) | Do not regenerate `output/final_archive.csv` via a real optimizer run "for a fresh comparison" — the already-committed archive is sufficient evidence for a code-migration parity check | Blocking — any drift beyond tolerance, or any count drift, must stop the migration immediately |
| Wrapper behavior (all four) | Same exit codes, same stdout/stderr split, same generated file paths/schema, parseable `--help` | `python scripts/<...>.py --help` for each of the four; re-run each script's normal invocation and diff exit code | Identical `--help` text (argparse-generated from unchanged flag definitions) and identical exit codes to pre-migration | None — inherently lightweight | Non-blocking for `--help` wording cosmetics; blocking for exit-code changes |
| TypeScript integration | `scenario-adapter.ts` still invokes the same wrapper path and still successfully parses its stdout | `cd parcel-locker-ui && npm run lint`, plus a manual read of `scenario-adapter.ts`/`runtime-config.ts` confirming `scenarioAdapterScriptPath` is unchanged | Lint exits `0`; `runtime-config.ts`/`scenario-adapter.ts` require **zero** code changes (the wrapper's file path was never touched) | Do not run `npm run dev` or POST to `/api/run-ga` — that starts a server, forbidden by this and every prior task's scope | Blocking if either TS file needed to change at all — by design, they should not |

## Behavioral Parity Criteria

- **JSON structural equality:** same top-level keys present with the same value types in `derive_optimizer_inputs.py`'s and the benchmark's JSON outputs. Key **order** is not part of the contract — `scenario-adapter.ts` accesses fields by name (`JSON.parse` then property access), never positionally.
- **Candidate ID set equality:** for `activeExistingCandidateIds`/`effectiveFixedCandidateIds`/similar lists, both **set equality and list ordering** matter — today's code deliberately calls `sorted(...)` on these, so ascending order is an intentional, documented behavior, not an accident of insertion order.
- **Facility count equality:** exact integer match, no tolerance — these are counts, never floating point.
- **Warning equality:** semantic, not string-for-string — the same *conditions* must produce a warning and the same conditions must not; exact wording may be polished as long as meaning is preserved.
- **Exit-code equality:** exact match (`0` vs. `1`), no tolerance.
- **Generated scenario semantic equality:** same facility set/count/candidate IDs; any future timestamp-like field (none exist today) would be explicitly excluded from comparison, same principle as not requiring byte-for-byte equality where formatting legitimately differs.
- **Benchmark numeric tolerance:** absolute difference ≤ `1e-9` for `f1`/`f2` — tight, because this is a pure code relocation, not an algorithm change; a larger drift is evidence of a real behavioral change, not acceptable floating-point noise.
- **Metadata field preservation:** every field currently present in a JSON/report metadata block must still be present after migration; fields may be **added** without breaking parity, never silently removed or renamed, since `scenario-adapter.ts`/`ga-runner.ts` access specific named fields today.
- **File-path preservation:** all four wrapper script paths, `output/validation/*`'s filenames, and `data/scenarios/*.json` (read-only during validation, never written by a validation run) stay exactly where they are.
- **For `derive_optimizer_inputs.py` specifically:** stdout schema (key presence) and parseability (valid, complete, standalone JSON) are **blocking, non-negotiable requirements** — a hard gate that must pass before that wrapper is considered migrated at all, not merely one more parity criterion among equals.

Do not require byte-for-byte equality anywhere JSON indentation, key order, or (for future additions) timestamps legitimately differ — those are schema/semantic equality concerns, not exact-stdout-contract concerns, except for `derive_optimizer_inputs.py`'s stdout, where "valid standalone JSON with the required keys" is the exact bar (not byte-for-byte, since indentation/key order still don't matter even there — `JSON.parse` doesn't care about either).

## Rollback Plan

The rollback plan does not depend on git history being available or consulted mid-task — it is a workflow discipline for how Phase 1 implementation physically keeps old and new code side by side until proven safe, not a "just `git revert`" instruction.

- **Preserve the original script until wrapper parity passes.** Before converting any of the four wrappers, that script's current function bodies stay present in the codebase (e.g., retained as internal, unreferenced logic inside the same file, or in a clearly-marked local working copy) until the corresponding Validation Matrix row passes. The duplicate is removed **only** in the same step that proves parity — never before, never "to save a step."
- **Migrate one script at a time**, in Batch order (2 → 3 → 4 → 5). Never let more than one wrapper's call-site behavior change within a single unverified step.
- **If parity fails for a given migration unit:** restore that script's original body and leave the new package module's code unreferenced by any wrapper (the package code itself is not deleted — it may still be useful once the specific issue is understood — but nothing calls into it until the failure is root-caused and fixed).
- **Do not change runtime callers** (`scenario-adapter.ts`, `ga-runner.ts`, `runtime-config.ts`) until wrapper compatibility is proven for the one script those callers actually depend on (`derive_optimizer_inputs.py`; the other three have no TypeScript caller today).
- **Do not create backup files in the repository.** Preserving the "old" version during a batch is a local working-copy/editor-history concern for whoever implements Phase 1, not a committed `*_old.py`/`*.bak` file — the repository should never contain two tracked copies of the same logic at once.

Named responses for each failure mode in the task's list:

| Failure | Rollback response |
| --- | --- |
| Editable import fails (`ModuleNotFoundError`) | Do not touch any wrapper yet — this blocks Batch 1 entirely. Fix the packaging/install step using the diagnostics above; do not work around it in a wrapper. |
| Next.js uses a different Python interpreter than the one `location_platform` was installed into | Same as above — a Batch-1-blocking environment issue, not a code bug. Re-run the editable install under the exact interpreter `runPythonScript` resolves (confirmed via `sys.executable`), never by adding `sys.path` hacks. |
| Wrapper output changes | Revert that specific wrapper to its preserved original body; leave its package module in place but unused; do not proceed to the next batch until root-caused. |
| Benchmark values change beyond tolerance | Revert `benchmark_existing_vs_optimized.py`'s wrapper immediately — the most consequential rollback, since benchmark numbers may already be referenced outside this repository. |
| Scenario validation counts change | Revert `validate_scenario.py`'s wrapper immediately — treat as equally severe to a candidate-ID/matrix-alignment break, since this validator is the last line of defense for that non-negotiable contract. |
| JSON stdout becomes polluted | Revert `derive_optimizer_inputs.py`'s wrapper **before** any other diagnostic step — a polluted stdout breaks `scenario-adapter.ts`'s `JSON.parse` with a confusing error far from the actual cause; don't spend time diagnosing downstream symptoms first. |
| Circular imports appear | This is a Batch-ordering violation, not a design flaw — fix which module imports which per Phase 0C1's already-documented dependency graph, rather than adopting lazy/deferred imports as a permanent workaround. |
| Package tests pass but the old CLI fails | Evidence the test suite is insufficiently faithful to the wrapper's actual invocation (missing an argparse default, a CWD-relative path assumption, an environment variable) — add the missing test case; do not conclude the wrapper is "mostly fine." |

## Stop Conditions

Phase 1 implementation must stop immediately if any of the following occur. Each is backed by concrete evidence gathered in this or prior phases, not a generic caution:

1. **Candidate ID or matrix alignment changes** — non-negotiable per every V1 doc; matrix dimension confirmed `2717` today via live execution.
2. **Current-network count changes from 26 effective / 27 physical** — confirmed exact today via `validate_scenario.py --expect-current-network-seed`'s live output this session.
3. **Benchmark baseline changes outside the documented ±1e-9 tolerance** — confirmed exact today (`f1: 0.6650755521778244`, `f2: 1.1419211244863716`) via the committed benchmark summary artifact.
4. **`derive_optimizer_inputs.py` stdout is not valid standalone JSON** — breaks `scenario-adapter.ts`'s `JSON.parse`, confirmed as a live dependency by reading the TypeScript source.
5. **Existing CLI path or required flag stops working** — breaks documented commands in `readme.md`/`AGENTS.md` and/or `runtime-config.ts`'s hardcoded script paths.
6. **Next.js-spawned interpreter cannot import `location_platform`** — confirmed real risk given the two-`python.exe`-plus-`py.exe` PATH ambiguity measured on this machine.
7. **New `sys.path` hacks are required** — signals the editable install isn't working as intended, directly contradicting Phase 0B's explicit "avoid fragile path manipulation" decision.
8. **Scenario validation logic remains duplicated after migration** — directly contradicts Phase 0C1's Shared Logic Extraction Decision that scenario validation must have exactly one implementation.
9. **A shared helper changes strict/lenient behavior unintentionally** — directly contradicts Phase 0C1's explicit decision to keep the lenient (`optimizer_inputs`) and strict (`benchmark.current_network`) facility resolvers separate.
10. **Runtime data or committed scenario files are modified unexpectedly** — `data/candidate_points.csv`, `data/scenarios/*.json`, and the matrix `.npy` files are frozen per Phase 0B; this is exactly why the Validation Matrix above insists on scratch/temporary output paths for the seed generator and benchmark checks.
11. **Java/GA execution becomes necessary just to validate package migration** — if this ever seems required, the validation approach has drifted from "confirm code produces the same values" into "confirm the whole system still works," which is out of scope for a Python-logic migration; flag back to Phase 0B/0C for rescoping rather than running Java to work around it.

Repository-specific additions, backed by this task's own findings:

12. **A path Phase 0B explicitly deferred gets touched as an incidental side effect** — e.g., `output/parameter analysis/`'s literal space, or the `scripts/validation/` → `scripts/benchmark/` rename happening "along the way" during a wrapper conversion instead of as its own separately-decided step.
13. **`requirements.txt` is modified to remove or replace an existing dependency** instead of `python/pyproject.toml` being added alongside it — this task decided `requirements.txt` stays authoritative for the existing pipeline; editing it during a package migration is scope creep into dependency-management restructuring.

## Anti-Overengineering Rule

**Rule:** a shared module is created only when it has at least two real consumers, a coherent responsibility, and enough logic to justify a separate module. Small helpers may remain together in a single cohesive module; a shared module should not exist merely to match a previously planned tree.

Applying this rule retroactively to Phase 0C1's seven proposed shared modules (Phase 0C1's module list and public APIs remain the record of what each function does; this section only revises **how many files** they live in):

| Phase 0C1 proposal | Consumers | Verdict | Reasoning |
| --- | --- | --- | --- |
| `common.paths` (`display_path`) | 4 of 4 scripts | **Keep as its own module** | Clear majority reuse, coherent single responsibility (path display formatting) |
| `common.paths` (`resolve_path`, originally implied separate) | 1 of 4 scripts today (`benchmark_existing_vs_optimized.py` only) | **Fold into `common.paths` alongside `display_path`**, not its own file | Only one real first-batch consumer; too small to justify a separate module on its own, but coherent enough (both are path-handling helpers) to sit in the same file as `display_path` |
| `common.parsing` | 3 of 4 scripts | **Keep as its own module** | Clear majority reuse, coherent responsibility (numeric coercion with error context), enough logic (4 functions) to justify a file |
| `common.errors` (`require_mapping`) | 2 of 4 scripts | **Consolidate into `common.parsing`**, not a separate file | Passes the "two consumers" bar but is a single function — not enough logic on its own to justify a dedicated module; `common.parsing` is the closest existing coherent home (both are "is this input shaped the way I expect" checks) |
| `common.io` (`write_json_file`) | 2 of 4 scripts (`generate_default_current_network_scenario.py`'s writer, `derive_optimizer_inputs.py`'s `--output`) | **Consolidate into `common.paths`**, not a separate file | Same shape as `common.errors` — two consumers, one function; folding it alongside `display_path`/`resolve_path` keeps `common` at two files instead of four without losing any function |
| `data.candidates` | 4 of 4 scripts | **Keep as its own module** | Clear majority reuse, substantial logic (CSV parsing, column validation, uniqueness checks) |
| `data.matrix` | 2 of 4 scripts | **Keep as its own module** | Two consumers, but real, non-trivial logic (shape validation **and** a genuinely stronger companion-ID alignment check that must both remain available as distinct functions) |
| `scenario.loading` (`load_scenario_json`) | 3 of 4 scripts | **Keep as its own module**, despite being one function | Distinguishing factor from `common.errors`/`common.io`: this is the single most-reused function in the entire batch (3 of 4 consumers, the highest of any borderline case) **and** it anchors the `scenario` package's public loading contract that `scenario.validation` explicitly wraps (catching its raise into an error-list entry) — a domain-anchoring role the `common.*` helpers don't have |

**Revised Phase 1 shared-module count: 5, not 7** (`common.paths`, `common.parsing`, `data.candidates`, `data.matrix`, `scenario.loading`) — `common.errors` and `common.io` are folded into `common.parsing` and `common.paths` respectively. This supersedes only the *file count* from Phase 0C1's "Exact Target Modules" section; every function Phase 0C1 named still exists with the same public API, just co-located differently. No function was invented or dropped by this consolidation.

## Inputs Required for Phase 0D

- The revised 5-module shared-module set (superseding Phase 0C1's 7-module list) as the actual file layout to implement.
- The five-batch migration sequence and its per-batch validation checkpoint, ready to drive real implementation work.
- The confirmed first-batch runtime dependency (`numpy` only) for `python/pyproject.toml`.
- The rollback/stop-condition tables, to be operationalized as an implementation checklist (e.g., a PR template checkbox list) during actual Phase 1 work.
- The exact numeric baselines confirmed in this task (candidate count 2717, effective 26, physical 27, matrix dimension 2717, warnings 0, F1 0.6650755521778244, F2 1.1419211244863716) as the concrete pass/fail values Phase 0D's implementation must reproduce.
- A decision (not made here) on whether Phase 0D is the actual Phase 1 implementation kickoff or another planning increment — this document treats Phase 1 implementation as the next concrete step, but scheduling it is outside this task's scope.

## Phase 0C2 Acceptance Checklist

- [x] The packaging bootstrap is decided (setuptools, Python ≥3.10, `location-platform` distribution name, `numpy`-only first-batch dependency, `pytest` as a dev/optional dependency).
- [x] The editable-install procedure is documented (resolve the runtime's interpreter first, then install and verify with that same interpreter — corrected in Phase 0D1 from an earlier, overly-unconditional statement; see "Corrected Interpreter Installation Rule").
- [x] Interpreter identity and import diagnostics are documented and dry-run-verified on this machine (`sys.executable`, `import location_platform`, `pip show location-platform`).
- [x] All four old CLI paths have explicit compatibility contracts (Backward Compatibility Contracts table).
- [x] The `derive_optimizer_inputs.py` stdout JSON contract is explicit and marked non-negotiable (dedicated subsection).
- [x] The migration is divided into five safe implementation batches, each ending in its own wrapper-conversion-and-verify checkpoint.
- [x] The validation matrix contains exact commands and expected results, backed by numbers obtained by actually running/reading files in this repository this session, not invented placeholders.
- [x] Parity rules are explicit and distinguish semantic equality, schema equality, exact-stdout contract, and numeric tolerance.
- [x] Rollback works without relying on a git commit (working-copy preservation discipline, not `git revert`).
- [x] Stop conditions are explicit, including three repository-specific additions beyond the task's base list.
- [x] The anti-overengineering rule is documented and applied retroactively to Phase 0C1's seven proposed modules, with two justified consolidations.
- [x] No runtime or code file was changed — only `docs/PHASE_0_REPO_CLEANUP_PLAN.md` was updated.

---

## Phase 0D1 Objective

Phase 0A–0C2 produced the inventory, target architecture, migration map, and compatibility/validation/rollback plan. Phase 0D1 does two things: (1) synchronizes the other authoritative docs (`docs/ARCHITECTURE_AUDIT.md`, `docs/V1_ROADMAP.md`, `docs/REPO_STRUCTURE.md`, `docs/V1_TECH_STACK.md`, `readme.md`) so they no longer contain statements this planning work has made stale — most importantly, several documents still said the scenario-to-optimizer adapter "does not exist," when it was built and wired into `/api/run-ga` in the tasks between Phase 0C2 and this one; (2) corrects an overstated claim in this document's own Phase 0C2 section (an editable-install command presented as unconditionally "canonical" when it actually depends on which interpreter the runtime resolves). No migration was implemented, no file was moved, and no package was created to produce this update.

## Documentation Synchronization Summary

| File | Stale/missing statement found | Correction made |
| --- | --- | --- |
| `docs/ARCHITECTURE_AUDIT.md` | Executive Summary and Current Architecture Snapshot diagram said the scenario system "is not yet wired into the optimizer's actual runtime path" / showed `X <-- NOT YET CONNECTED -->` | Diagram updated to show both the V0 path and the now-existing temporary scenario bridge; Executive Summary updated with a status note |
| `docs/ARCHITECTURE_AUDIT.md` | P0 finding said the adapter "does not yet... get called by `/api/run-ga`" | Marked resolved for the scenario-driven path; V0 bare-`k` path explicitly noted as intentionally retained, not an oversight |
| `docs/ARCHITECTURE_AUDIT.md` | P1 finding (bare `k` ambiguity) presented as fully open | Marked resolved for scenario requests; remaining gap folded into the UI-scenario-selection item |
| `docs/ARCHITECTURE_AUDIT.md` | P3 finding ("no scenario-facing adapter layer at all") presented as fully open | Marked resolved — `derive_optimizer_inputs.py` is exactly the described module |
| `docs/ARCHITECTURE_AUDIT.md` | Responsibility Boundaries table said scenario→optimizer translation "**Does not exist**" | Updated to show it's implemented via a temporary bridge, not yet packaged |
| `docs/ARCHITECTURE_AUDIT.md` | UI/Backend Boundary Review didn't mention the route's new optional `scenarioPath` | Added; also added the explicit "no UI scenario-selection control exists yet" statement the task required |
| `docs/ARCHITECTURE_AUDIT.md` | Suggested Next Tasks still listed "wire the adapter into `/api/run-ga`" as open | Marked done; added a UI-scenario-selection-control task and a pointer to this document's Phase 1 implementation plan |
| `docs/ARCHITECTURE_AUDIT.md` | Open Questions still posed "should the adapter be Python or Java?" as unresolved | Marked resolved (Python, subprocess-invoked) |
| `docs/V1_ROADMAP.md` | No section distinguished the broader product roadmap from actual execution status | Added "Current Implementation Track" section (Completed/Current/Next) without renumbering or removing the Phase 0–10 roadmap |
| `docs/V1_ROADMAP.md` | "Recommended Immediate Work Order" listed 10 items with no status, several already done | Annotated each item in place with `[DONE]`/`[PARTIAL]`/`[NOT STARTED]`; list itself preserved unchanged as historical record |
| `docs/REPO_STRUCTURE.md` | "Current Runtime Path" showed only the V0 path | Added the scenario-driven path as a documented addition, explicitly marked temporary |
| `docs/REPO_STRUCTURE.md` | No mention of the approved future `python/` package layout | Added an "Approved Future Structure (Not Yet Implemented)" section, explicit that the folder doesn't exist yet, plus the `scripts/` vs. `python/src/location_platform/` policy |
| `docs/V1_TECH_STACK.md` | "Python Platform Package"/"Recommended Target Repo Shape" showed `location_platform/` at repo root, not inside `python/` | Added callout notes pointing to the Phase 0B "Option A" decision; illustrative submodule list marked non-guaranteed |
| `docs/V1_TECH_STACK.md` | No mention that Next.js currently has a scenario-adapter exception to its "should not own orchestration" rule | Added an explicit, clearly-labeled temporary exception under the Next.js responsibilities section |
| `readme.md` | "Start Here" list didn't reference this planning document | Added item 10, one line, no rewritten installation instructions |

## Corrected Interpreter Installation Rule

**What was wrong:** the Phase 0C2 "Packaging Bootstrap Decision" section stated `python -m pip install -e .\python` as a single, unconditionally "canonical" command, with `py -m pip install -e .\python` framed only as an alternative for a particular workflow style. That framing implied one command is always correct, when the actually-correct requirement is narrower and environment-dependent: **the package must be installed using the same interpreter `parcel-locker-ui/src/lib/python-runner.ts`'s `detectPythonCommand()` will spawn at runtime**, and that resolution (`PYTHON_CMD` → `py` → `python` on Windows) can pick a different executable than whichever command a developer happens to type first — confirmed as a real possibility on this machine, where `where.exe python` resolves two distinct executables and a separate `py.exe` launcher also exists.

**Corrected rule, now reflected in-place in the "Packaging Bootstrap Decision" and "Python Package Layout Decision" sections above:**

```text
1. Resolve the interpreter used by the current runtime (replicate detectPythonCommand()'s
   own resolution: $env:PYTHON_CMD, else the first of `py`/`python` that responds to --version).
2. Verify its sys.executable.
3. Install with that same interpreter: <resolved-command> -m pip install -e .\python
4. Verify location_platform imports through that same interpreter.
```

Both `py -m pip install -e .\python` and `python -m pip install -e .\python` remain valid **examples** — neither is chosen blindly; the one matching step 1's resolution is the one to use. This does not introduce any new environment variable or change any runtime configuration file; a future `LOCATION_PLATFORM_PYTHON`-style override remains a later implementation decision, exactly as Phase 0C2 already noted.

## Phase 0 Completion Review

- **Phase 0A** (current-state inventory): all current changes classified, both runtime paths documented, all important folders classified, all 14 active Python scripts inventoried, side effects/in-place mutations identified, source/generated/raw/archive boundaries recorded, problems evidence-based, open questions listed. Confirmed still accurate after this pass — no Phase 0A finding was contradicted by anything found while synchronizing the other docs.
- **Phase 0B** (target architecture): package location decided (Option A), target repo structure approved with justified adjustments, module boundaries defined, `scripts/` policy defined, component ownership matrix defined, all 8 Phase 0A open questions resolved or deferred, frozen paths listed. Confirmed still accurate; this pass's `docs/V1_TECH_STACK.md`/`docs/REPO_STRUCTURE.md` updates make Phase 0B's decision visible outside this one document for the first time, which is a synchronization gap this task closes, not a Phase 0B defect.
- **Phase 0C1** (migration map): four-script batch, exact target modules, public APIs, wrapper responsibilities, shared-logic decisions, dependency order. Confirmed still accurate.
- **Phase 0C2** (compatibility/validation/rollback): packaging bootstrap, interpreter compatibility (now corrected — see above), CLI compatibility contracts (including the `derive_optimizer_inputs.py` stdout contract), five-batch safe migration method, validation matrix with real numbers, parity criteria, rollback plan, 13 stop conditions, anti-overengineering consolidation (7 → 5 shared modules). Confirmed accurate other than the one corrected interpreter-install overstatement.
- **Phase 0D1** (this task): documentation synchronized; one self-correction applied; Phase 0 completion assessed below.

## Remaining Phase 0D2 Hygiene Items

Explicitly out of scope for this task and not evaluated for blocking status — these are repository-hygiene cleanups, separate from Phase 0 planning completeness:

- `.gitignore` review/cleanup (untouched in this task).
- `.graphifyignore` review/cleanup (untouched in this task; unrelated to the Python migration).
- `output/parameter analysis/`'s literal space — rename deferred (Phase 0B decision, restated in Phase 0C2's stop conditions; still not actioned).
- Any file deletion or move — none performed or scheduled by Phase 0D1.
- The `scripts/validation/` → `scripts/benchmark/` and `data/prepare_ga_inputs.py` → `scripts/data/` retargets — decided in principle (Phase 0B) and referenced again in Phase 0C1/0C2, but sequencing remains a Phase 0D2/implementation-time decision, not resolved here.

None of these block Phase 1 entry (see below) — they are optional cleanup that may happen before, after, or interleaved with the Phase 1 package migration, at whoever's discretion picks up that work next.

## Phase 0 Final Acceptance Checklist

| Item | Status | Evidence |
| --- | --- | --- |
| Current runtime paths documented | **Complete** | Phase 0A's V0/scenario-path documentation, now also reflected in `docs/ARCHITECTURE_AUDIT.md` and `docs/REPO_STRUCTURE.md` after this task's sync |
| All important folders classified | **Complete** | Phase 0A Folder Classification table |
| All active Python scripts inventoried | **Complete** | Phase 0A Active Python Script Inventory (14 scripts) |
| Package layout selected | **Complete** | Phase 0B Decision 1 (Option A) |
| Component ownership defined | **Complete** | Phase 0B Component Ownership Matrix |
| First migration batch selected | **Complete** | Phase 0C1 (four scripts, unchanged since) |
| Target modules/public APIs mapped | **Complete** | Phase 0C1 Exact Target Modules + Proposed Public APIs, revised in Phase 0C2's Anti-Overengineering Rule (5 shared modules) |
| CLI compatibility contracts defined | **Complete** | Phase 0C2 Backward Compatibility Contracts, including the dedicated `derive_optimizer_inputs.py` stdout contract |
| Interpreter compatibility defined | **Complete** | Phase 0C2 Python Interpreter Compatibility Plan, **corrected** in this task (see above) |
| Validation matrix defined | **Complete** | Phase 0C2 Validation Matrix, with real numbers from this repository |
| Rollback strategy defined | **Complete** | Phase 0C2 Rollback Plan |
| Stop conditions defined | **Complete** | Phase 0C2 Stop Conditions (11 base + 3 repository-specific) |
| Runtime/data paths frozen | **Complete** | Phase 0B Paths Frozen During Phase 1 |
| No migration implemented prematurely | **Complete** | Confirmed across every Phase 0 task: no package created, no file moved/renamed, no wrapper written |

**No item is incomplete or blocked.** Phase 0 planning is assessed as complete.

## Exact Phase 1 Entry Conditions

| Condition | Met? | Evidence |
| --- | --- | --- |
| The approved docs are internally consistent | **Yes** | This task's Documentation Synchronization Summary closed every stale statement found across `docs/ARCHITECTURE_AUDIT.md`, `docs/V1_ROADMAP.md`, `docs/REPO_STRUCTURE.md`, `docs/V1_TECH_STACK.md`, `readme.md` |
| The interpreter rule is corrected | **Yes** | See "Corrected Interpreter Installation Rule" above |
| The first migration batch remains exactly four scripts | **Yes** | Unchanged since Phase 0C1: `generate_default_current_network_scenario.py`, `validate_scenario.py`, `derive_optimizer_inputs.py`, `benchmark_existing_vs_optimized.py` |
| No V0 runtime/data path is scheduled to move | **Yes** | Phase 0B's frozen-paths list stands unmodified |
| Old CLI paths remain required | **Yes** | Phase 0C2's Backward Compatibility Contracts table, unmodified |
| Scenario adapter stdout JSON is treated as a blocking compatibility contract | **Yes** | Phase 0C2's dedicated subsection, reinforced by `docs/ARCHITECTURE_AUDIT.md`'s updated diagram noting `scenario-adapter.ts` parses this script's stdout live |
| The package will be introduced incrementally | **Yes** | Phase 0C2's five-batch Safe Migration Method |
| No FastAPI/UI/objective/map work is mixed into the first package task | **Yes** | Phase 0C1/0C2 scope is exactly the four scenario/benchmark scripts; `docs/V1_TECH_STACK.md`'s update this task confirms FastAPI/RQ/PostgreSQL remain deferred and Java/Leaflet remain current, unchanged by this planning |

**All conditions are met. Phase 1 may begin.**

The exact first implementation task, at a high level (not written out as a full prompt here — that belongs to whoever picks up Phase 1):

```text
Phase 1A — Minimal Python Package Bootstrap
```

Scope: `python/pyproject.toml` (setuptools, `requires-python >= "3.10"`, `numpy` dependency, `pytest` dev extra), `python/src/location_platform/__init__.py`, and the two Batch-1 shared modules (`common.paths`, `common.parsing`, per Phase 0C2's anti-overengineering-consolidated 5-module set) plus `data.candidates`/`data.matrix`. No wrapper is converted in Phase 1A — that begins in Phase 1B (Batch 2, `scenario.loading` + `scenario.validation`) per Phase 0C2's five-batch sequence.
