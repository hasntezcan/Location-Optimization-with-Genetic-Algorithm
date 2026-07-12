# Architecture Audit

## Executive Summary

The repository is in the middle of a V0-to-V1 migration and the migration is going in the right direction, not in a confused one. The current stack (Java SPEA2 + Python scripts + Next.js) is not the problem. **Update (Phase 1G audit):** the Phase 1 Python package migration planned in `docs/PHASE_0_REPO_CLEANUP_PLAN.md` is now implemented. `python/src/location_platform/` exists (`common/`, `data/`, `scenario/`, `benchmark/` submodules) and owns all reusable scenario/benchmark logic; the four migrated scripts (`scripts/scenario/generate_default_current_network_scenario.py`, `scripts/scenario/validate_scenario.py`, `scripts/scenario/derive_optimizer_inputs.py`, `scripts/validation/benchmark_existing_vs_optimized.py`) are now thin CLI wrappers over that package at their original, unchanged paths. The scenario-to-optimizer gap described below as the original P0 finding was closed earlier (the adapter is wired into `/api/run-ga` through a temporary Next.js compatibility bridge, `scenario-adapter.ts`/`ga-runner.ts`); this pass confirms the underlying adapter logic has since moved into the package too (`location_platform.scenario.optimizer_inputs`). The remaining responsibility-boundary problems are unchanged in kind: the Next.js API route still owns long-running orchestration and is explicitly a temporary bridge rather than the final backend, and the UI still has no scenario-selection control to exercise the scenario path. **This migration has been verified only by static inspection (file reads and code search) — no pytest run, no CLI execution, no Java/Maven build.** Manual runtime validation (`py -m pytest python/tests -q` plus the CLI comparisons listed in `docs/V1_ROADMAP.md`) is still required from the user before this is considered behaviorally proven, and before any Phase 2 (further benchmark hardening) or later-phase UI/objective work begins. The main risk right now is momentum: it would be easy to start Phase 4 (UI scenario *editing*) or Phase 6 (objectives) work before that manual validation lands, which would recreate exactly the coupling the V1 docs warn against — see `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s stop conditions for the concrete version of this rule.

## Current Architecture Snapshot

```text
data/candidate_points.csv + data/kadikoy_distance_meters_nxn.npy   (V0 grid + matrix, unchanged)
        |
        v
data/scenarios/kadikoy_parcel_locker_current_network.json          (scenario.facilities[], seeded from existing_locker_count)
        |
        +--> scripts/scenario/validate_scenario.py                  (validates scenario against grid + matrix)
        +--> scripts/validation/benchmark_existing_vs_optimized.py  (reads scenario.facilities[] as current-network source of truth)
        +--> scripts/scenario/derive_optimizer_inputs.py            (derives --k / --fixedFacilityIds from scenario.facilities[]
        |                                                             + settings + constraints; never reads existing_locker_count
        |                                                             or nearby_locker_count)
        |
        |   <-- CONNECTED VIA A TEMPORARY BRIDGE (two parallel runtime paths now exist) -->
        |
        +--[scenario path]--> parcel-locker-ui/src/lib/server/scenario-adapter.ts
        |                       (validates scenarioPath is under data/scenarios/, invokes
        |                        derive_optimizer_inputs.py as a subprocess, parses its stdout JSON)
        |                       -> ga-runner.ts overwrites k/fixedFacilityIds with the derived values
        |                          and forces includeExistingLockers=false, OR short-circuits with
        |                          no Java/GA at all when the scenario's runType is "current_network"
        |
        +--[V0 path, still fully supported, no scenarioPath in the request]--> unchanged:
                src/main/java/app/Main.java  --includeExistingLockers / --fixedFacilityIds / --k
                (still reads existing facility presence directly from candidate_points.csv
                 `existing_locker_count`, via CandidateRepository, for this path only)
        |
        v
output/final_archive.csv, output/run_metadata.json  (shared, global, not run-scoped; a scenario-driven
        run also best-effort-merges a `scenario` summary key into run_metadata.json)
        |
        v
parcel-locker-ui Next.js API route /api/run-ga  (spawns Maven synchronously, streams SSE, then runs
        scripts/plot_archives.py and parcel-locker-ui/src/scripts/process_ga_data.py, then writes public/mock/*)
```

The scenario layer and the benchmark layer already talk to each other correctly, and — as of the work summarized below — the optimizer runtime can now be driven by scenario data too, through a temporary compatibility bridge. The two runtime paths (V0 direct-CSV and scenario-driven) currently coexist by design: the scenario path is additive and opt-in (only used when the request includes `scenarioPath`), not a replacement. See `docs/PHASE_0_REPO_CLEANUP_PLAN.md` for the full runtime-path documentation (Phase 0A) and the plan to move this logic into a proper Python package (Phase 0B–0C2).

> **Status:** The scenario-to-optimizer adapter described in the original version of this audit as a P0/P3 gap now exists and is wired end to end: `/api/run-ga` can optionally accept `scenarioPath` (plus `forceExistingOff`/`targetTotalFacilityCount`); `scenario-adapter.ts` invokes `derive_optimizer_inputs.py`; a `current_network` scenario short-circuits with no Java/GA invocation at all; an optimizer-requiring scenario uses the derived `k`/`fixedFacilityIds` with `includeExistingLockers` forced off. `constraints.disabledCandidateIds` is derived and reported in `adapterWarnings` but still **not enforced** (Java has no CLI flag to exclude candidates from the selectable pool — confirmed still true by this pass: no `--disabledCandidateIds`-style flag exists in `Main.java`). The UI still has **no scenario-selection control** — a developer/script must construct the `scenarioPath` request body manually; there is no dashboard element to trigger it yet. `ga-runner.ts`/`scenario-adapter.ts` remain an explicitly **temporary** compatibility bridge (per `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s Phase 0B decision), not the final backend architecture — FastAPI/worker-queue work remains deferred. **Update (Phase 1G):** the reusable Python logic is now packaged — `python/src/location_platform/` (`scenario.seed`, `scenario.validation`, `scenario.optimizer_inputs`, `benchmark.current_network`/`evaluation`/`reporting`, plus `common`/`data` support modules) — and `scripts/scenario/derive_optimizer_inputs.py`/`validate_scenario.py`/`generate_default_current_network_scenario.py` and `scripts/validation/benchmark_existing_vs_optimized.py` are now thin wrappers over it, at their original unchanged paths. This was verified by static inspection only; no runtime test suite has been run against it yet. See the updated P0/P1/P3 findings, the Responsibility Boundaries table, and "Suggested Next Claude/Codex Tasks" below for what remains open.

## What Is Going Well

- **The scenario contract is implemented faithfully, not just documented.** `scripts/scenario/generate_default_current_network_scenario.py` and `validate_scenario.py` produce and validate `data/scenarios/kadikoy_parcel_locker_current_network.json` using the exact schema in `docs/V1_SCENARIO_CONTRACT.md` (`kind`, `status`, `snap.snapStatus`, `runType`, `targetNewFacilityCount`/`targetTotalFacilityCount`). This is real Phase 1/Phase 2 roadmap work, not a stub.
- **`nearby_locker_count` vs `existing_locker_count` discipline is actually respected in code**, not only in docs. `scripts/prepare_candidate_existing_lockers.py` explicitly renames legacy `locker_count` to `nearby_locker_count` and computes `existing_locker_count` as a separate, snap-derived field. A repo-wide search found no active-code instance of `nearby_locker_count > 0` used as existing-facility logic, and `CandidateRepository.java` even carries an inline comment reinforcing this rule.
- **The benchmark script (`scripts/validation/benchmark_existing_vs_optimized.py`) already reads `scenario.facilities[]` as the current-network source of truth**, with `existing_locker_count` demoted to an optional seed-match validation (`--validate-v0-seed-match`), exactly matching the `V1_BENCHMARKING.md` migration path. This file's recent diff (170 insertions) is the single best piece of evidence that the scenario migration is real, not aspirational.
- **Candidate ID / matrix alignment discipline is intact.** `validate_scenario.py` and the benchmark script both check candidate ID existence, matrix shape, and matrix companion-ID alignment before doing anything else.
- **Generated vs. source boundaries are mostly respected on disk.** `output/`, `parcel-locker-ui/public/mock/`, `data/archive/`, `docs/archive/`, `scripts/archive/` are consistently treated as non-source in both code and docs.
- **Docs are unusually well-aligned with each other.** `AGENTS.md`, `readme.md`, and the `V1_*` docs repeat the same non-negotiable rules (candidate ID stability, `nearby_locker_count` semantics, minimize-only objectives) almost verbatim, which is a good sign for an AI-agent-maintained repo — there's one story, told consistently.

## Main Problems

### P0 — Scenario data is not yet consumed by the optimizer runtime (resolved for the scenario-driven path; V0 path unchanged by design)

**Problem (as originally found):** `src/main/java/app/Main.java` and the Next.js `/api/run-ga` route derived existing-facility presence only from `--includeExistingLockers` (a boolean) and read `existing_locker_count` directly out of `candidate_points.csv` via `CandidateRepository`. Neither path read `data/scenarios/*.json`. The scenario layer existed in parallel with the optimizer runtime, not upstream of it.

**Why it matters:** This was exactly the seam the roadmap calls Phase 3 ("Scenario-Driven Optimizer Input"), and the docs explicitly warn against building further UI/objective features on top of the old path.

**Recommended direction (as originally written):** Add a thin adapter that converts `scenario.facilities[]` + `constraints` into Java CLI flags, preserving V0 behavior and the Java CLI contract while making scenario JSON the actual input.

**Status: done for the scenario-driven path.** `scripts/scenario/derive_optimizer_inputs.py` implements the adapter — it resolves `activeExistingCandidateIds` from `scenario.facilities[]` (not `existing_locker_count`), combines them with `constraints.lockedCandidateIds` into `--fixedFacilityIds`, and resolves `--k` from `targetNewFacilityCount` (expansion) or `targetTotalFacilityCount` (greenfield/same-count), minus the fixed count. It deliberately never emits `--includeExistingLockers`. **This is now wired end to end:** `/api/run-ga` accepts an optional `scenarioPath`; `scenario-adapter.ts` invokes the adapter as a subprocess and validates the path stays under `data/scenarios/`; `ga-runner.ts` overwrites `k`/`fixedFacilityIds` with the derived values and forces `includeExistingLockers: false`, or — when the scenario's `runType` is `current_network` — skips Java/Maven entirely and returns a `Completed` event with scenario counts only. The **V0 path is unchanged and remains fully supported**: a request without `scenarioPath` still uses bare `k`/`includeExistingLockers` exactly as before, which is intentional (backward compatibility), not an oversight. Two gaps remain: (a) `constraints.disabledCandidateIds` is derived and reported in `adapterWarnings` but not enforced, since Java has no CLI flag to exclude candidates from the selectable pool; (b) the UI has no scenario-selection control — the scenario path can only be triggered by a manually-constructed request body today, not from the dashboard. Both remain open — see "Suggested Next Claude/Codex Tasks."

**Priority: P0 → downgraded to P1 for the two remaining gaps (disabled-candidate Java support; UI scenario-selection control)**

### P0 — Next.js still owns long-running orchestration

**Problem:** `/api/run-ga/route.ts` spawns Maven, streams SSE for the whole run, then runs `scripts/plot_archives.py` and `parcel-locker-ui/src/scripts/process_ga_data.py` in-process, then writes to `public/mock/`. This matches `docs/DEPLOYMENT_PHASE1.md` exactly — it is a known, documented limitation, not a surprise.

**Why it matters:** `V1_TECH_STACK.md` is explicit that this is the "bad pattern" to move away from, and that Next.js should not own Maven/Python orchestration. It's currently tolerable only because usage is single-user/local.

**Recommended direction:** No action needed until FastAPI work begins (Phase 3 of the tech-stack roadmap). Just don't add more responsibilities to this route (e.g., don't make it also orchestrate scenario validation or benchmark generation — put new orchestration behind a script/CLI boundary that a future FastAPI layer can call directly).

**Priority: P0 (guardrail, not urgent implementation)**

### P1 — `scripts/` mixes at least five different responsibilities with no naming convention to tell them apart

**Problem:** At the top level of `scripts/` (excluding `archive/`, `research/`, `validation/`, `scenario/`), there are: `calculate_poi_weights.py` and `prepare_demand.py` (data prep, one overwrites `candidate_points.csv` in place), `prepare_candidate_existing_lockers.py` (data prep + audit report generation), `plot_archives.py` (568 lines, plotting + methodology commentary in comments), `statistical_analysis.py` (488 lines, parameter-analysis statistics). `scripts/scenario/` and `scripts/validation/` are new, better-scoped subfolders, but the older top-level scripts don't follow that pattern yet.

**Why it matters:** `docs/V1_TECH_STACK.md` already defines the target (`location_platform/` package + thin `scripts/*_cli.py` wrappers). Every new standalone script added at the top level of `scripts/` without a package to move logic into makes that eventual migration larger. The good news: `scripts/scenario/` and `scripts/validation/` already demonstrate the desired shape (focused, single-responsibility, no plotting-and-stats-and-io mixed together) — new work should follow that pattern, not the older top-level pattern.

**Recommended direction:** Don't refactor now. When the `location_platform/` package is created (Tech Stack Phase 2), migrate in this order: `scenario/` scripts first (already closest to package-ready), then `validation`/benchmark logic, then `prepare_demand.py`/`calculate_poi_weights.py`/`prepare_candidate_existing_lockers.py` (these three are tightly coupled to `candidate_points.csv` mutation and should become `location_platform/data/`), then `plot_archives.py`/`statistical_analysis.py` last (most research-specific, lowest reuse value).

**Priority: P1**

### P1 — Facility-count semantics are ambiguous at the UI/API boundary (resolved for scenario requests; V0 requests intentionally retain bare `k`)

**Problem (as originally found):** `/api/run-ga` took a bare `k: number` and `includeExistingLockers: boolean` from the request body. `docs/V1_SCENARIO_CONTRACT.md` explicitly says "Do not use a bare `k` field in long-term scenario contracts" and defines `targetNewFacilityCount`/`targetTotalFacilityCount` to remove exactly this ambiguity.

**Why it mattered:** This was the same P0 gap viewed from the UI side.

**Status: resolved for scenario-driven requests.** A request with `scenarioPath` now conveys facility-count intent through the scenario's own `targetNewFacilityCount`/`targetTotalFacilityCount`/`includeExistingFacilities` settings (plus an optional `targetTotalFacilityCount` request-level override), which `derive_optimizer_inputs.py` translates into `k` internally — the ambiguous bare `k` never has to be supplied by the client in this path. **The V0 request shape (no `scenarioPath`) intentionally still accepts bare `k`/`includeExistingLockers`** — this is deliberate backward compatibility, documented in `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s Backward Compatibility Contracts, not an unresolved ambiguity. The remaining gap is UI-side, not API-side: there is still no dashboard control that lets a user pick a scenario and have the UI send `scenarioPath` instead of bare `k` — that is the same UI-scenario-selection gap named in the P0 finding above.

**Priority: P1 → remaining item folded into the P0 UI-scenario-selection gap above**

### P2 — Shared, overwritten output files remain the only benchmark record

**Problem:** `output/final_archive.csv` and `output/run_metadata.json` are still global, singular files. `scripts/validation/benchmark_existing_vs_optimized.py` reads these two fixed paths by default. Confirmed structure: `output/archives/`, `output/data_audit/`, `output/parameter analysis/` (note: this directory name contains a literal space — see Folder-by-Folder Review), `output/validation/`.

**Why it matters:** `V1_BENCHMARKING.md` and `V1_TECH_STACK.md` both call out run-specific output folders (`output/runs/<run_id>/...`) as a non-negotiable direction before any multi-run or multi-scenario comparison work is trustworthy. Right now, running the optimizer twice silently overwrites the previous run's benchmark baseline.

**Recommended direction:** This is explicitly a later-phase item per the roadmap (Phase 10 / Tech Stack Phase 4) and doesn't need to happen before scenario/optimizer wiring. Flagging it now so it isn't forgotten once multiple scenario comparisons become common.

**Priority: P2**

### P3 — Java optimizer boundary has no scenario-facing adapter layer at all (resolved)

**Problem (as originally found):** There was no file anywhere in `src/main/java` or `scripts/` whose job was "translate a scenario JSON into Java CLI arguments."

**Recommended direction (as originally written):** Build as a small, explicit Python module, unit-testable independent of Maven/Java.

**Status: done.** `scripts/scenario/derive_optimizer_inputs.py` is exactly this module — a standalone, unit-testable Python script with no Maven/Java dependency, called by `scenario-adapter.ts` as a subprocess. **Update (Phase 1G):** its logic now lives in `location_platform.scenario.optimizer_inputs` per `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s Phase 0C1/0C2 plan (see Responsibility Boundaries below); the script itself is now a thin wrapper at the same path.

**Priority: Resolved — no further action required for this specific finding**

## Wrong-Direction Risks

- **Building Phase 4 (Scenario UI) before Phase 3 (scenario-driven optimizer input) exists.** The scenario JSON and validator are stable enough to demo, which creates temptation to start wiring a scenario editor into the UI next. Per the roadmap, UI scenario editing should wait until scenario state can actually drive an optimizer run — otherwise the UI would be editing state that has no effect, which is the "UI-only feature that can't serialize into scenario contract" anti-pattern the docs call out.
- **Letting `existing_locker_count` in `candidate_points.csv` become permanently load-bearing.** It currently is load-bearing (Java reads it directly). This is fine as a documented V0 compatibility path, but every month it remains the *only* input to Java increases the temptation to add more logic on top of it instead of finishing the scenario-to-CLI adapter.
- **Adding a second use-case demo before Phase 3 closes.** Not attempted yet, and the roadmap already sequences this correctly (Phase 9, after objective engine). No current evidence of drift here — noting only because it's the single most likely subagent-driven mistake if a future task is scoped loosely ("build a fire-station demo").
- **`output/parameter analysis/` with a literal space in the directory name.** Minor, but scripting against this path from PowerShell/shell without quoting will silently fail or behave unexpectedly; worth normalizing to `parameter_analysis` when that folder is next touched (not urgent enough to rename unprompted now).

## Folder-by-Folder Review

| Folder | Role | Notes |
| --- | --- | --- |
| `src/main/java` | Source (optimizer) | Still fully V0/locker-coupled by design; correct per current roadmap phase. |
| `parcel-locker-ui/src` | Source (UI) | No scenario state yet (`lib/` has `ga-api.ts`, `mcda.ts`, `types.ts`, etc., but no `scenario.ts`) — confirms Phase 4 hasn't started, consistent with roadmap sequencing. |
| `parcel-locker-ui/src/scripts` | Source (UI-adjacent Python) | `process_ga_data.py` converts optimizer output to UI mock JSON; single-purpose, fine as-is. |
| `scripts/` (top-level) | Mixed: source + one-off | See P1 above. |
| `scripts/scenario/` | Source (new, well-scoped) | Best-organized part of `scripts/`; use as the template for future additions. |
| `scripts/validation/` | Source (benchmark/validation) | Currently one file; well-aligned with `V1_BENCHMARKING.md`. |
| `scripts/research/` | Research/report scripts | Explicitly says "does NOT run Java/GA" in its own docstrings — good self-documentation. |
| `scripts/archive/` | Archive | Correctly separated (`legacy/`, `one_off/`). |
| `data/` (root files) | Source (V0 runtime) | `candidate_points.csv`, matrix `.npy` files — unchanged, as expected. |
| `data/scenarios/` | Source (new, V1) | One scenario file so far; correctly separated from `data/raw` and `data/archive`. |
| `data/raw/`, `data/archive/` | Provenance/archive | Untouched, as instructed. |
| `docs/` | Documentation | V1 docs are current and mutually consistent; `docs/archive/` correctly isolated. |
| `output/` | Generated | Global/shared files still the default (see P2). Space in `output/parameter analysis/` is a minor hygiene issue. |
| `backup/` (removed) | Legacy Java experiment (historical) | **Update (Phase 1G2):** `(experimental)Main.java` was a confirmed-dead Tier 1 cleanup candidate and has been deleted. Git does not track empty directories, so `backup/` no longer exists in the current repository structure. |
| `sections/figures/final_results/` | Report artifacts | Generated, correctly treated as such. |

## Python Scripts Review

Classification of every active (non-archive) script:

| Script | Category | Notes |
| --- | --- | --- |
| `scripts/prepare_demand.py` | Reusable product logic (data prep) | Overwrites its own input CSV in place; matches documented warning in `readme.md`. Future home: `location_platform/data/`. |
| `scripts/calculate_poi_weights.py` | Reusable product logic (data prep) | Small, focused; future home: `location_platform/data/`. |
| `scripts/prepare_candidate_existing_lockers.py` | Reusable product logic (data prep + audit) | Does the `locker_count`→`nearby_locker_count`/`existing_locker_count` split correctly; future home: `location_platform/data/` + `location_platform/scenario/seed.py`. |
| `scripts/scenario/generate_default_current_network_scenario.py` | Thin CLI wrapper | Migrated (Phase 1C); logic now in `location_platform/scenario/seed.py`. |
| `scripts/scenario/validate_scenario.py` | Thin CLI wrapper | Migrated (Phase 1B); logic now in `location_platform/scenario/validation.py`. |
| `scripts/scenario/derive_optimizer_inputs.py` | Thin CLI wrapper | Migrated (Phase 1D); logic now in `location_platform/scenario/optimizer_inputs.py`. |
| `scripts/validation/benchmark_existing_vs_optimized.py` | Thin CLI wrapper | Migrated (Phase 1E/1F); logic now in `location_platform/benchmark/current_network.py`, `evaluation.py`, `reporting.py`. |
| `scripts/plot_archives.py` | CLI wrapper + reusable logic mixed | 568 lines mixing plotting, methodology comments, and file I/O; candidate for splitting when the package is created. |
| `scripts/statistical_analysis.py` | Benchmark/reporting tool | Parameter-analysis specific; lower reuse priority. |
| `scripts/research/*.py` | Research/one-off (report-specific) | Self-documented as not touching Java/GA; fine to leave as research scripts, not package candidates. |
| `scripts/archive/**` | Archive candidate | Already archived; no action. |

No scripts were found duplicating optimizer logic outside Java — this is a real strength, not just an absence of evidence (checked `scripts/validation` and `scripts/scenario` specifically since they're the closest to optimizer-adjacent logic; both call into the matrix/candidate data only for evaluation, not for selection).

## Scenario Architecture Review

- The scenario JSON (`data/scenarios/kadikoy_parcel_locker_current_network.json`) matches the `V1_SCENARIO_CONTRACT.md` example structure field-for-field, including `snap`, `constraints`, `benchmark`, and `metadata` blocks.
- `existing_locker_count` is used correctly and only as a seed source (`source: "seed_from_v0_data"`, `snapMethod: "seed_from_existing_locker_count"`), matching the documented migration rule.
- `validate_scenario.py` enforces schema shape, allowed `kind`/`status` enums, candidate ID existence, locked/disabled conflict detection, and a current-network-specific seed-match check — this is a more complete validator than the contract doc strictly requires, which is a good sign.
- **Gap:** scenario data is validated and benchmarked, but not yet consumed by the optimizer (see P0 above). The scenario system is real but currently a side-channel, not the optimizer's actual input path.
- **Gap:** no CSV/GIS import tooling yet for *new* facilities (Phase 2 of the roadmap) — only the V0-seed generation path exists. This is expected at this stage, not a problem.

## Benchmark Architecture Review

- `benchmark_existing_vs_optimized.py` is the strongest evidence of correct direction in the whole repo: it sources current-network placement from `scenario.facilities[]`, explicitly documents that `nearby_locker_count` is context-only and unused, explicitly documents that `existing_locker_count` is seed-validation-only, validates matrix alignment via the companion ID artifact, and states demand type and objective bundle in its output metadata.
- It still writes to a shared `output/validation/` directory rather than a run-scoped folder — consistent with the repo-wide P2 finding, not a defect specific to this script.
- It only supports one scenario (current network) vs. one archive; multi-scenario comparison (same-K, expansion, reduction) from `V1_BENCHMARKING.md`'s benchmark types 2–6 isn't built yet. That's fine — it's Phase 5 work, and this script is a reasonable Phase 3-adjacent foundation for it.

## UI / Backend Boundary Review

- Confirmed runtime path exactly matches `REPO_STRUCTURE.md`'s documented diagram for the V0 case: `/api/run-ga` → `ga-runner.ts` → Maven/Java → `plot_archives.py` → `process_ga_data.py` → `public/mock/`.
- **Updated:** the route now *also* accepts an optional `scenarioPath` (plus `forceExistingOff`/`targetTotalFacilityCount`), validated for shape and, inside `scenario-adapter.ts`, for path safety (must resolve under `data/scenarios/`, no `..`, no absolute paths). When present, `ga-runner.ts` derives `k`/`fixedFacilityIds` from the scenario instead of trusting client-sent values, and forces `includeExistingLockers: false`. When absent, the route behaves exactly as before (bare `k` required, 1–30).
- No FastAPI code exists yet, which is correct for the current phase (`V1_TECH_STACK.md` Phase 1 says keep Next.js + Java + Python, don't add FastAPI yet). The scenario bridge above is explicitly temporary per `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s Phase 0B decision, not a step toward making Next.js the permanent backend.
- **No UI scenario-selection control exists yet** (`components/dashboard/*` are still all locker-specific viewer components: `locker-map.tsx`, `locker-strip.tsx`, `locker-detail-panel.tsx`; no `scenario.ts` state module exists in `lib/`) — this is acceptable per the contract (parcel-locker labels are fine in UI display layers) and correctly sequenced (Phase 4 hasn't started), but it does mean the scenario path built above can only be exercised by a manually-constructed request today, not from the dashboard.

## Java Optimizer Boundary Review

- Java remains focused on SPEA2 execution, Pareto/dominance logic, and CLI-driven runs — no scenario editing, no CSV import, no reporting logic inside Java. This matches the target boundary in `V1_TECH_STACK.md`.
- `Main.java` CLI flags (`--k`, `--includeExistingLockers`, `--fixedFacilityIds`) are V0-shaped and read `existing_locker_count` directly via `CandidateRepository` — this is the concrete form of the P0/P3 findings above.
- No recommendation to touch `FitnessCalculator.java`, `Dominance.java`, or `Pareto.java` — objective/dominance logic is out of scope for this audit's findings and appears untouched by the scenario work, which is correct (Phase 6 objective refactor comes later).

## Data and Output Management Review

- Candidate ID / matrix alignment: protected consistently across `validate_scenario.py`, `benchmark_existing_vs_optimized.py`, and Java `CandidateRepository` (all three either check matrix shape/ID alignment or rely on the same sorted-ascending contract).
- Generated vs. source boundary: clean. No evidence found of hand-edited generated files.
- Output management: still global/shared files by default (`output/final_archive.csv`, `output/run_metadata.json`) — flagged as P2, matches known and already-documented limitation.
- One hygiene finding: `output/parameter analysis/` contains a space in its directory name — flagged under Wrong-Direction Risks, not urgent.

## Documentation Review

- `readme.md`, `AGENTS.md`, `CLAUDE.md`, and all `docs/V1_*.md` files are internally consistent on every non-negotiable rule checked (candidate ID stability, `nearby_locker_count` semantics, `existing_locker_count` semantics, minimize-only objectives, Java authority, generated-file boundaries).
- `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md` (3,414 lines) is correctly marked archived/historical in every place it's referenced (readme, AGENTS.md, REPO_STRUCTURE.md) and does not contradict current contracts in the areas spot-checked (no stray `locker_count > 0` logic, no conflicting FastAPI/scenario claims).
- No stale claims found suggesting FastAPI, PostgreSQL, or a worker queue are already implemented — the tech stack doc's "Current Stack" section accurately reflects what's in the repo today.
- `docs/REPO_STRUCTURE.md`'s "Current Runtime Path" diagram is accurate and matches the actual `route.ts`/`ga-runner.ts`/Java call chain observed in code.

## Target Folder Direction

No change from `docs/V1_TECH_STACK.md`'s "Recommended Target Repo Shape." This audit found no evidence that the target shape needs revision — the new `scripts/scenario/`, `scripts/validation/`, and `data/scenarios/` folders are already small, correctly-scoped previews of the eventual `location_platform/scenario/` and `location_platform/benchmark/` packages.

## Responsibility Boundaries

Confirmed current-vs-target boundary status:

| Layer | Target owner | Current owner | Status |
| --- | --- | --- | --- |
| Optimization algorithm | Java SPEA2 | Java SPEA2 | Aligned |
| Scenario definition/validation | Python package | `location_platform.scenario.seed`/`.validation`, called by thin `scripts/scenario/*.py` wrappers | Packaged (Phase 1B/1C) — static inspection only, not runtime-verified |
| Scenario → optimizer input translation | Python package (adapter) | `location_platform.scenario.optimizer_inputs`, called by the thin `scripts/scenario/derive_optimizer_inputs.py` wrapper + temporary `parcel-locker-ui/src/lib/server/scenario-adapter.ts` bridge | Packaged (Phase 1D); bridge remains temporary per `docs/PHASE_0_REPO_CLEANUP_PLAN.md` — static inspection only, not runtime-verified |
| Benchmark computation | Python package | `location_platform.benchmark.current_network`/`.evaluation`/`.reporting`, called by the thin `scripts/validation/benchmark_existing_vs_optimized.py` wrapper | Packaged (Phase 1E/1F) — static inspection only, not runtime-verified |
| Long-running job orchestration | FastAPI + worker queue | Next.js API route (synchronous) | Known, documented, acceptable for now |
| UI scenario editing | Next.js | Not built yet | Correctly not started (Phase 4 not reached) |
| Persistent scenario/run storage | PostgreSQL/PostGIS | Flat JSON files | Correctly not started (Phase 6 of tech stack) |

## Recommended Migration Plan

### P0 — Audit and Stabilization

Already largely done by this audit and by the recent "Existing Locker Integration" work. Remaining action: none required to "stabilize" further — V0 continues to run unmodified.

### P1 — Python Package Cleanup

Not urgent. When started, migrate `scripts/scenario/` and `scripts/validation/` first (lowest risk, already package-shaped), then data-prep scripts, then plotting/statistics scripts last.

### P2 — Scenario Foundation Hardening

Mostly done. Remaining: facility import from arbitrary CSV/GIS (Phase 2 of roadmap) is not yet built — only the V0-seed path exists.

### P3 — Scenario-Based Benchmarking

Partially done (current-network benchmark exists and is scenario-based). Same-K, expansion, and reduction benchmark types from `V1_BENCHMARKING.md` are not yet built.

### P4 — Scenario Edit / Import Core

Not started. Should wait until the P0 optimizer-input adapter (above) exists, per roadmap sequencing.

### P5 — Leaflet Scenario UI Foundation

Not started. Correctly sequenced after P4.

### P6 — Backend Boundary Preparation

Not started; no FastAPI code present. Correctly deferred per `V1_TECH_STACK.md` Phase 1 guidance.

### P7 — Run Isolation and Output Management

Not started (`output/` remains global/shared). Matches P2 finding above; fine to defer until multiple scenarios are compared regularly.

### P8 — Objective Engine Refactor

Not started; F1/F2 remain hard-coded in `FitnessCalculator.java`. Correctly deferred — objective refactor should come after scenario/optimizer wiring per roadmap Phase 6 sequencing.

### P9 — Second Use-Case Demo

Not started. Correctly deferred.

### P10 — Map Modernization Evaluation

Not started; Leaflet still in use, no MapLibre/deck.gl code found. Correctly deferred per roadmap Phase 8.

## Do Not Do List

- Do not start UI scenario editing (Phase 4 / roadmap) before the scenario-to-optimizer-input adapter (P0 above) exists — it would create editable state with no runtime effect.
- Do not let `existing_locker_count` become anything other than a seed source; do not add new logic that reads it directly instead of going through `scenario.facilities[]`.
- Do not add FastAPI, a database, or a worker queue yet — current phase guidance (`V1_TECH_STACK.md` Phase 1) says keep the current stack until the Python package and scenario-optimizer wiring are done.
- Do not rewrite `FitnessCalculator.java`, `Dominance.java`, or SPEA2 logic to "simplify" — not requested, not warranted, and explicitly against `V1_TECH_STACK.md` guidance.
- Do not migrate the map engine before scenario editing exists and is stable.
- Do not build a second use-case demo before the P0 gap closes — it would either duplicate the same missing adapter per use case or fake genericity by hard-coding a second domain on top of the same locker-coupled Java CLI.
- Do not rename `output/parameter analysis/` or otherwise touch generated output folders without an explicit task — noted as a hygiene issue only, not actioned here.

## Open Questions

- ~~Is there a concrete owner/timeline for the scenario-to-optimizer-input adapter (P0)?~~ Resolved — implemented and wired into `/api/run-ga`; see `docs/PHASE_0_REPO_CLEANUP_PLAN.md` for the Python package migration timeline that will house it long-term.
- ~~Should the adapter be a Python script invoked before Maven, or a small Java-side JSON reader?~~ Resolved — a Python script (`derive_optimizer_inputs.py`) invoked as a subprocess by `scenario-adapter.ts`; Java was not touched.
- Is `output/parameter analysis/` (with the space) intentional, or a typo from an earlier script run? Still open — `docs/PHASE_0_REPO_CLEANUP_PLAN.md` also flags this and defers any rename.
- ~~Should `scripts/scenario/` and `scripts/validation/` be treated as the de facto start of `location_platform/` now?~~ Resolved — `docs/PHASE_0_REPO_CLEANUP_PLAN.md`'s Phase 0B–0C2 answers this in detail (Option A package layout, exact target modules, migration batches); implementation has not started.

## Suggested Next Claude/Codex Tasks

1. ~~Scope and implement the scenario-to-optimizer-input adapter~~ **Done**: `scripts/scenario/derive_optimizer_inputs.py` translates `settings`/`constraints`/`facilities` into `--k`/`--fixedFacilityIds`.
2. ~~Wire `derive_optimizer_inputs.py` into `/api/run-ga`~~ **Done**: `route.ts`/`ga-runner.ts`/`scenario-adapter.ts`/`runtime-config.ts` now support an optional `scenarioPath` request, deriving `k`/`fixedFacilityIds` from the scenario and short-circuiting Java entirely for `current_network` scenarios. V0 requests are unaffected.
3. **Add a minimal Java `--disabledCandidateIds` flag** (comma-separated, same parsing pattern as `--fixedFacilityIds`) so `constraints.disabledCandidateIds` can actually be excluded from `repository.getSelectableCandidateIds()` in `Main.java`, instead of only being reported as a warning by the adapter. Still open.
4. **Add a UI scenario-selection control** so a user can pick a scenario from the dashboard and have the UI send `scenarioPath` — today the scenario path can only be exercised via a manually-constructed request body. This is a small, contained UI addition (a selector + passing `scenarioPath` through), not the full Phase 4 scenario-editing UI, and does not require UI scenario *editing* state to exist yet.
5. **Add same-K and expansion benchmark types to `scripts/validation/`** using the existing scenario-based pattern already proven in `benchmark_existing_vs_optimized.py`. Still open.
6. ~~Implement the Phase 1 Python package migration~~ **Done (Phases 1A–1F):** `python/src/location_platform/` exists with `common`/`data`/`scenario`/`benchmark` modules; all four scenario/benchmark scripts are now thin wrappers at their original paths. Verified by static inspection only (Phase 1G) — **manual runtime validation (`py -m pytest python/tests -q` and the CLI comparison commands in `docs/V1_ROADMAP.md`) is still required from the user before Phase 2 or further UI/objective-engine work begins**, per this document's stop conditions and this audit's Wrong-Direction Risks.
7. **Add a minimal Java `--disabledCandidateIds` flag** and **a UI scenario-selection control** (items 3–4 above) remain the next concrete implementation gaps once manual validation of the Phase 1 package migration is confirmed.
