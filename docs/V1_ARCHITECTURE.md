# V1 Architecture

## V1 Vision

V1 turns the current Kadikoy parcel locker optimizer into a generic grid-based location optimization platform. The platform should support multiple facility-planning use cases by separating base spatial data, editable scenarios, modular objectives, optimization execution, benchmark reporting, and map-based decision support.

The product direction is a scenario sandbox: users define or import a candidate grid, place or import facilities, choose objectives, run optimization, compare alternatives, and explain business tradeoffs.

## Current V0 Use Case

The current system solves a Kadikoy parcel locker problem:

- Candidate locations come from `data/candidate_points.csv`.
- Distances come from `data/kadikoy_distance_meters_nxn.npy`.
- Java SPEA2 selects `K` candidate IDs.
- The current objectives are accessibility cost and equity cost.
- The Next.js UI visualizes map and dashboard modes for generated archive outputs.

This remains the baseline implementation while V1 contracts are introduced.

## Target V1 Platform Architecture

V1 should be organized around reusable platform modules rather than a single parcel-locker workflow.

### Spatial Data Engine

Owns grid and candidate data, feature layers, spatial joins, distance matrix generation, and schema validation.

Responsibilities:

- Load candidate/grid records.
- Validate candidate IDs and coordinates.
- Preserve candidate ID and matrix alignment.
- Manage feature layers such as demand, population, restrictions, and proximity indicators.
- Keep raw provenance separate from normalized runtime inputs.

### Scenario Engine

Owns editable decision state.

Responsibilities:

- Store existing facilities as scenario entities.
- Store proposed, locked, disabled, and manually edited facilities.
- Import scenario facilities from CSV or GIS sources.
- Snap imported or manually drawn facilities to candidates when required.
- Pass scenario constraints and selected candidates into the backend.

### Objective Engine

Owns modular objective definitions.

Responsibilities:

- Define objective inputs, direction, normalization, and output labels.
- Support early V1 minimize-only objectives.
- Keep objective logic separate from use-case labels.
- Allow use-case bundles such as parcel lockers, food deserts, fire stations, or police coverage.

### Optimization Engine

Owns algorithm execution.

Responsibilities:

- Continue using Java SPEA2 as the authoritative current engine.
- Accept generic scenario and objective inputs over time.
- Return candidate IDs, objective values, metadata, and diagnostics.
- Preserve deterministic contracts for candidate IDs and distance matrix indexing.

### Benchmark & Reporting Engine

Owns business-facing comparisons.

Responsibilities:

- Compare current network and optimized alternatives.
- Support same-K comparisons.
- Support same-coverage-with-fewer-facilities comparisons.
- Report coverage, demand, cost, equity, and operational metrics.
- Phrase claims carefully when demand is proxy demand rather than calibrated real demand.

### Map / Scenario UI

Owns the interactive decision-support experience.

Responsibilities:

- Provide a scenario canvas.
- Add, remove, disable, and lock facilities.
- Show layers, heatmaps, coverage, and scenario comparisons.
- Evolve beyond a result viewer into a sandbox for planning workflows.

## High-Level Data Flow

```text
Raw GIS/CSV sources
  -> Spatial Data Engine
  -> validated grid/candidate features + distance matrix
  -> Scenario Engine
  -> objective bundle + constraints + facilities
  -> Optimization Engine
  -> Pareto candidates + metadata
  -> Benchmark & Reporting Engine
  -> Map / Scenario UI
```

## What Stays From the Current System

- Java SPEA2 remains the authoritative optimization engine.
- `data/candidate_points.csv` remains the current runtime candidate source.
- `data/kadikoy_distance_meters_nxn.npy` remains the current runtime distance matrix.
- Candidate ID and distance matrix alignment remains a hard contract.
- The Next.js UI remains the current visualization and local run surface.
- Current Kadikoy parcel locker outputs remain useful as V0 examples and benchmarks.

## What Changes

- The core vocabulary moves from parcel lockers to generic facilities.
- Existing facilities move from base candidate CSV attributes into scenario data.
- Objectives become modular and use-case configurable.
- Data becomes layered and extensible instead of one wide, use-case-specific CSV.
- Benchmarks become business-facing comparisons, not only raw F1/F2 values.
- The map becomes a scenario canvas, not just a viewer for generated solutions.

