# Backend Guide

## Purpose

This guide explains how the current Java optimization pipeline can be used by a backend layer for the web UI.

The frontend prototype already assumes a dashboard structure with:

- parameter controls on the left
- a central Kadikoy map
- generation/result exploration in the middle
- detail/statistics panels on the right

The project currently includes a **local/dev integration path** where the UI can trigger the Java optimizer and refresh the UI data. A production-grade backend service is still a separate concern.

Current local/dev route files:

- `parcel-locker-ui/src/app/api/run-ga/route.ts`
- `parcel-locker-ui/src/lib/server/ga-runner.ts`
- `parcel-locker-ui/src/lib/server/runtime-config.ts`
- `parcel-locker-ui/src/lib/ga-api.ts`

---

## Current frontend reality

The UI has two data paths:
- mock data loading from `parcel-locker-ui/public/mock/`
- a local/dev “run GA” endpoint that triggers the real optimizer and then regenerates the mock assets

The frontend currently expects concepts like:

- a generation sequence
- active lockers for a generation
- generation-level metrics
- a selected solution / selected locker
- map-friendly candidate and locker data

Today, this is delivered by generating files and then transforming them into the UI’s expected JSON/CSV shapes.

---

## Current Java reality

The Java side already has a working SPEA2-style optimization loop.

The current `Main.java` does the following:

1. loads candidate points from CSV
2. loads the distance matrix
3. initializes a random population
4. evaluates objectives
5. computes SPEA2 fitness components
6. creates an initial archive
7. evolves the population through generations
8. stores:
   - initial archive snapshot
   - final archive snapshot
9. writes run parameter metadata
10. normalizes archive exports with final-ND-based assessment bounds
11. exports archive CSV files

So the optimizer is already capable of producing final optimization outputs, but it is not yet structured as a backend service.

---

## What the current Main exports

The current `Main.java` produces these files in `output/`:

### 1. `initial_archive.csv`
This is the archive snapshot taken after generation 0.

It contains archive individuals and their:

- chromosome
- raw objectives (`f1`, `f2`)
- normalized objectives (`norm_f1`, `norm_f2`)
- SPEA2-related values

### 2. `final_archive.csv`
This is the archive snapshot after the last generation.

It contains the same structure as the initial archive export.

### 3. `run_metadata.json`
This contains the parameters used for the latest run, including `k`,
population size, archive size, max generations, rates, optional random seed,
and estimated function evaluations.

---

## Current assessment logic

The pipeline exports normalized objective columns for both archive snapshots,
but official initial-to-final improvement is not based on comparing initial HV
against final HV.

Current `Main` behavior:
- extracts the final archive non-dominated set
- derives ideal/nadir bounds from that final ND set
- normalizes both archive CSV snapshots with those bounds for export consistency
- computes final-archive hypervolume with a fixed reference point (e.g. `(1.1, 1.1)`)
- reports initial-to-final improvement with raw-objective ND metrics and C-metric

This is important for backend understanding because:

- the backend does not need to rebuild normalization logic itself
- the backend can trust the exported normalized values from Java
- the frontend can display both raw and normalized results if needed
- backend summaries should treat final HV as a final-front quality indicator, not
  as the official initial-to-final improvement metric

---

## What is still missing for backend consumption

The current `Main` is still oriented toward:

- terminal output
- final archive comparison
- offline plotting

It is **not yet backend-shaped** in the following sense:

- there is no run ID
- there is no structured generation-by-generation export
- there is no generation summary file
- there is no dedicated final Pareto front CSV
- there is no machine-friendly result JSON output beyond run parameter metadata
- there is no dedicated optimizer service (job queue, isolation, concurrency control, persistence)

So the backend team should think of the current optimizer as a **batch computation engine** that already produces some useful files, but not yet a direct API-ready service.

---

## What the backend team can already use right now

Even without changing `Main`, backend can already start with the following file-based flow:

### Step 1
Trigger the Java optimization run.

### Step 2
Wait until the run completes.

### Step 3
Read these files:

- `output/initial_archive.csv`
- `output/final_archive.csv`
- `output/archive_comparison_latest.png` (optional visualization)

### Step 4
Parse:
- chromosomes
- objective values
- normalized objective values
- SPEA2 metrics

### Step 5
Transform them into API responses for the frontend.

This is enough for a **first backend integration milestone**.

---

## Recommended first backend endpoints

Even with the current Java outputs, the backend can expose a minimal API like this:

### `POST /runs`
Start a new optimization run.

Request body can contain future parameter fields such as:

- `k`
- `populationSize`
- `archiveSize`
- `maxGenerations`
- `crossoverRate`
- `mutationRate`
- `randomSeed`

For the first version, backend can pass the CLI arguments currently supported by
`Main`. Unsupported parameters should remain in `GAParameters` until Java exposes
a validated runtime configuration format.

### `GET /runs/latest/initial-archive`
Return parsed rows from `initial_archive.csv`.

### `GET /runs/latest/final-archive`
Return parsed rows from `final_archive.csv`.

### `GET /runs/latest/summary`
Return:
- runtime
- initial ND count
- final ND count
- hypervolume values
- assessment bounds used for archive normalization

These values are already printed by `Main`, but backend can later expose them in structured form.

---

## How the frontend can use current outputs

## 1. Left parameter panel
The frontend currently has a concept of user-controlled parameters.

The current local/dev route already passes the supported runtime parameters to
`Main` through Maven `-Dexec.args`.

Short-term approach:
- keep unsupported Java parameters, such as `beta`, in `GAParameters`
- pass supported fields (`k`, population size, archive size, generations,
  crossover rate, mutation rate, random seed) through the request body
- move to a validated runtime configuration format before production use

## 2. Center map
The frontend map needs selected locker coordinates for a solution.

The current archive CSVs already include chromosomes.  
Each chromosome is the selected locker ID set for one solution.

Backend can:
1. parse the chromosome string
2. look up candidate metadata
3. build a map-ready solution object

## 3. Right-side metrics panel
The current archive CSVs already contain enough metrics for a details panel:

- `f1`
- `f2`
- `norm_f1`
- `norm_f2`
- `strength`
- `raw_fitness`
- `density`
- `total_fitness`

So even before generation playback is implemented, backend can already serve:
- selected solution details
- initial vs final comparison
- final archive exploration

---

## Important limitation of the current Main

The current `Main` does **not** export per-generation states.

This means the backend cannot yet deliver a true real-generation playback stream to the frontend.

That is important because the frontend prototype is conceptually built around generation-based exploration.

So with the current unchanged `Main`, the backend can support:

- initial archive exploration
- final archive exploration
- final-result map display
- archive table / statistics
- hypervolume summary

But it cannot yet support:

- true generation slider based on real GA states
- previous/next generation playback from the actual optimizer
- map animation across real generations

That part would require later Java-side export extensions.

---

## Recommended backend development order

## Phase 1 — File-based final-result integration
Goal: connect the frontend to real optimization output as quickly as possible.

Use:
- `initial_archive.csv`
- `final_archive.csv`

Backend tasks:
- trigger run
- parse CSVs
- expose archive rows
- expose run summary

Frontend result:
- serve final archive exploration from backend-parsed optimizer output
- optionally show initial vs final comparison

## Phase 2 — Add final Pareto front endpoint
Even if `Main` does not yet export a dedicated Pareto CSV, backend can derive it from `final_archive.csv`.

Backend tasks:
- compute non-dominated subset server-side
- expose `/runs/latest/final-pareto-front`

Frontend result:
- final Pareto front table
- final best solutions list
- cleaner result panel

## Phase 3 — Add true generation exports from Java
This is the point where Java should later export:
- generation summaries
- generation archive members
- final Pareto front CSV

Frontend result:
- real playback
- map evolution
- generation-level exploration

---

## What the backend team should not do yet

At this stage, backend should avoid:

- rewriting the optimizer logic outside Java
- duplicating normalization logic in another language
- rebuilding SPEA2 internals on the server side
- trying to infer full generation playback from only initial/final archive snapshots

The Java layer should remain the single source of truth for optimization logic.

---

## Practical short-term contract between Java and backend

For now, the backend can assume this contract:

### Input side
Java reads:
- candidate CSV
- distance matrix
- fixed GA parameters from `GAParameters`

### Output side
Java writes:
- `initial_archive.csv`
- `final_archive.csv`
- terminal summary with HV and runtime info

### Backend responsibility
Backend:
- runs Java
- reads those outputs
- serializes structured responses for the frontend

This is enough to start backend work without changing the optimizer immediately.

---

## Recommended next Java-side additions later

When the team is ready to extend Java outputs for the backend, the most valuable additions will be:

1. `final_pareto_front.csv`
2. `generation_summary.csv`
3. `generation_archive_members.csv`
4. optional JSON export
5. run-specific output folders

But these are **next-step improvements**, not blockers for the backend team to begin.

---

## Summary

With the current unchanged `Main.java`, the backend can already start by treating the Java side as a batch optimizer that produces two main result files:

- `initial_archive.csv`
- `final_archive.csv`

This is enough for:
- final archive inspection
- initial vs final comparison
- map rendering for selected solutions
- detailed solution metrics in the UI

What is not yet available is real generation-by-generation playback from the actual optimizer.

So the correct immediate backend strategy is:

- start with file-based final-result integration
- expose initial/final archives
- keep the optimizer unchanged for now
- extend Java exports later when the team is ready for real playback support
