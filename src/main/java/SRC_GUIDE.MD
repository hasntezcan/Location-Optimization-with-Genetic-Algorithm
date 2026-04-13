# src_guide.md

## Overview

This document explains the current `src` codebase of the Kadıköy parcel locker location optimization project.

The project implements a **multi-objective evolutionary optimization workflow** based on **SPEA2**. The goal is to find good locker placement combinations over candidate points by balancing:

- **Accessibility** (`f1`)
- **Equity / fairness across neighborhoods** (`f2`)

This guide is written for both:
- a **human developer** joining the project
- an **AI assistant/model** that needs fast technical context

It explains:
- what each package and class does
- how the classes connect to each other
- what assumptions are currently used
- what is already working
- what still needs improvement

---

# 1. High-Level Project Logic

## 1.1 Problem Setting

We have a candidate set of possible locker points in Kadıköy.

Each solution:
- selects `k` locker locations
- evaluates how good this selection is according to two objectives

The optimization is multi-objective:
- minimize **accessibility cost**
- minimize **equity inequality**

The algorithm currently uses:
- **SPEA2-style evaluation**
- archive-based survivor selection
- binary tournament parent selection
- crossover + mutation based offspring generation

---

## 1.2 Current Objective Definitions

### Objective 1: Accessibility (`f1`)
Current logic is based on a gravity-style accessibility formulation.

In practice, for each demand point:
- the nearest selected locker is found
- distance is converted from metres to **kilometres** before applying the decay exponent
- distance penalty is applied using `beta` (currently `beta = 2`)
- weighted demand contribution is accumulated

Current implementation note:
- distances are read from a precomputed **distance matrix** stored in metres
- the conversion to kilometres happens inside `FitnessCalculator.findDistanceCostToNearestLocker`
- this keeps `f1` values in a numerically manageable range (typically single-digit to low double-digit)

### Objective 2: Equity (`f2`)
Current logic measures inter-neighborhood inequality.

The implementation:
- aggregates neighborhood-level weighted mean accessibility costs
- computes the **coefficient of variation (CV)** across neighborhoods
- CV = `standardDeviation / mean`, which is a **dimensionless ratio**

Why CV was chosen:
- it is independent of the distance unit (metres vs kilometres does not affect the result)
- it produces values in a bounded, interpretable range (typically 0 to 2)
- it avoids the squared-scale explosion that variance caused in earlier iterations
- it is widely used in inequality measurement literature

---

## 1.3 Current SPEA2 Flow

The algorithm follows this broad sequence:

1. Load candidate points and distance matrix
2. Create initial random population
3. Evaluate objectives
4. Normalize objectives for SPEA2 internal calculations
5. Compute:
   - strength
   - raw fitness
   - density
   - total fitness
6. Select archive using survivor logic
7. Generate offspring through selection + variation
8. Repeat over generations
9. Compare initial archive and final archive
10. Assess quality using hypervolume

---

# 2. Package Structure

Current code is organized roughly like this:

- `app`
- `algorithm`
- `algorithm.helper`
- `config`
- `io`
- `model`
- `service`

Each one has a clear role.

---

# 3. app Package

## `app.Main`

This is the main entry point of the project.

### Responsibilities
- load input data
- initialize core services
- create the first population
- run the SPEA2 loop
- print initial archive and final archive
- track runtime
- perform final hypervolume assessment

### Current role in architecture
`Main` is currently the orchestration layer.

It should:
- contain the main optimization loop
- avoid heavy mathematical logic
- delegate actual work to `service` and `algorithm` classes

### Important current behavior
`Main` currently also:
- reads all parameters from `config.GAParameters`
- stores an initial archive snapshot
- stores a final archive snapshot
- tracks global raw objective bounds across generations
- applies post-hoc normalization for archive comparison and HV computation
- logs per-generation diagnostics (best f1, best f2)

### Future direction
`Main` should remain thin.
If the project grows, a dedicated runner/controller class can be introduced later, but for now `Main` is acceptable as the workflow coordinator.

---

# 4. model Package

## `model.CandidatePoint`

Represents one candidate location / demand point record from the dataset.

### Typical contents
This class contains the properties needed for optimization, such as:
- id
- coordinates
- population / demand related values
- neighborhood information
- other cleaned attributes coming from the CSV

### Purpose
This is the core domain entity for the spatial candidate set.

---

## `model.CandidateRepository`

Stores all candidate points in memory.

### Responsibilities
- keep loaded candidate points
- provide access by id
- provide all candidate ids
- finalize and synchronize loaded candidate data with other structures

### Important note
This repository is central because almost all optimization logic eventually queries candidate data through it.

---

## `model.Individual`

Represents one solution in the evolutionary algorithm.

### A solution contains
- a chromosome: selected candidate IDs
- raw objective values
- normalized objective values
- SPEA2 values:
  - strength
  - raw fitness
  - density
  - total fitness

### Important implementation detail
The chromosome is treated as an **unordered set** of selected locker IDs.

Because of that:
- chromosomes are canonicalized
- equivalent permutations should not be treated as meaningfully different solutions

This was introduced because earlier runs showed many archive duplicates that were actually the same solution in different gene orderings.

### Why this matters
Without canonicalization:
- archive diversity becomes fake
- same solution can appear many times
- convergence analysis becomes misleading

---

# 5. io Package

## `io.CsvLoader`

Loads candidate point data from CSV.

### Responsibilities
- read `candidate_points.csv`
- parse each row
- populate the repository

### Why it exists
Separates file parsing from model logic.

---

## `io.DistanceMatrixLoader`

Loads the precomputed distance matrix.

### Current data source
The project uses a `.npy` distance matrix file.

### Responsibilities
- load matrix from disk
- return `double[][]`
- provide the matrix in the same order as the repository synchronization

### Why this matters
Distance evaluation is too expensive to compute repeatedly on the fly.
The matrix is precomputed and then reused during optimization.

---

# 6. service Package

The `service` package contains the core mathematical and utility services used by the algorithm.

---

## `service.FitnessCalculator`

This is one of the most important classes.

### Responsibilities
- compute raw `f1`
- compute raw `f2`
- evaluate one individual
- evaluate a population

### Current state
This class is where the **problem-specific objective definitions live**.

### Distance handling
The precomputed distance matrix stores values in **metres**.
`findDistanceCostToNearestLocker` converts distances to **kilometres** before applying `beta`.
This keeps objective values in a manageable numerical range.

### Equity metric
`f2` uses the **coefficient of variation (CV)** of mahalle-level weighted mean accessibility costs.
CV = `standardDeviation / mean` → dimensionless, bounded, and independent of distance unit.

### Possible future experiments
- testing alternative equity metrics (Gini, MAD)
- adjusting `beta` value
- experimenting with different demand weighting schemes

---

## `service.ObjectiveNormalizer`

Used to normalize objective values.

### Two different conceptual uses
This is important.

#### A. Internal normalization
Used inside the evolutionary workflow for:
- density calculation
- SPEA2 comparison support

#### B. Assessment normalization
Used after the full run so that:
- initial archive
- final archive

can be compared in the **same objective space**

### Current lesson learned
Generation-by-generation normalization caused invalid hypervolume comparisons.

So now the important rule is:

> For final quality assessment, initial and final archives must be normalized using the exact same global bounds.

### Future note
This class may later be split into:
- `InternalObjectiveNormalizer`
- `AssessmentObjectiveNormalizer`

if clearer separation becomes necessary.

---

## `service.PopulationInitializer`

Creates the initial population.

### Responsibilities
- sample chromosomes randomly
- enforce chromosome size `k`
- produce the requested population size

### Current role
This is used only at generation 0.

---

## `service.HypervolumeIndicator`

Computes the 2D hypervolume indicator.

### Current intent
Used for final assessment of:
- initial archive
- final archive

after post-hoc normalization in a shared objective space.

### Important caveat
Hypervolume has been one of the most sensitive parts of the project so far.

Key lessons already discovered:
- raw-space HV is not suitable when objective magnitudes differ a lot
- per-generation normalization breaks comparability
- global min-max can still be too loose if outliers exist
- the quality of HV interpretation depends strongly on how the common normalization space is built

### Current use
This class assumes:
- normalized objectives already exist
- reference point is fixed, typically `(1.1, 1.1)`

### Future concern
If archive quality is still not distinguishable enough, the normalization window for assessment may need refinement.

---

# 7. algorithm Package

This package contains the core evolutionary steps.

---

## `algorithm.Evaluate`

Runs the SPEA2 evaluation pipeline.

### Responsibilities
For a merged set of individuals:
- evaluate raw objectives
- normalize objectives
- assign strength
- assign raw fitness
- assign density
- assign total fitness

### Meaning
This is the class that converts raw candidate solutions into SPEA2-scored solutions.

### Dependency usage
It relies on:
- `FitnessCalculator`
- `ObjectiveNormalizer`
- `Dominance`

### Why it matters
This class implements the core SPEA2 evaluation logic, not the problem-specific objective formulas.

---

## `algorithm.Survivor`

Builds the next archive.

### Responsibilities
- extract non-dominated set
- if archive is too small, fill with best dominated individuals
- if archive is too large, truncate

### Important logic
This follows standard SPEA2 survivor selection behavior.

### Additional implementation detail
Archive duplicate control has been an important topic.
The archive is supposed to represent elite memory, not repeated copies of the same solution.

---

## `algorithm.Selection`

Performs parent selection.

### Current method
Binary tournament selection on archive individuals.

### Comparison order
Selection prefers:
1. smaller total fitness
2. then smaller raw fitness
3. then density tie-breaking if needed

### Role
Creates the mating pool for the variation stage.

---

## `algorithm.Variation`

Generates offspring.

### Responsibilities
- crossover
- mutation
- chromosome repair
- uniqueness control inside chromosomes

### Crossover design
The crossover operator uses **shared-gene priority recombination**:
- genes present in both parents are guaranteed to appear in both children
- remaining chromosome slots are filled from parent-exclusive genes in shuffled order
- a repair step ensures correctness and handles edge cases

This approach preserves proven gene combinations while maintaining diversity.

### Important note
The chromosome represents a set of selected points, so repair logic matters.

### Current issues to keep in mind
Even if chromosomes are canonicalized, the population can still converge too strongly.
Variation design is still a key driver of exploration vs exploitation balance.

---

# 8. algorithm.helper Package

These classes support SPEA2 logic.

---

## `algorithm.helper.Dominance`

Checks whether one individual dominates another.

### Current assumption
Bi-objective minimization:
- lower `f1` is better
- lower `f2` is better

This class is fundamental for:
- Pareto extraction
- strength assignment
- raw fitness assignment

---

## `algorithm.helper.Pareto`

Extracts the non-dominated subset from a list of individuals.

### Role
Used by:
- `Survivor`
- `HypervolumeIndicator`

---

## `algorithm.helper.Truncation`

Used when the non-dominated archive is too large.

### Responsibilities
- remove individuals from dense regions
- preserve diversity in archive

### Why it matters
Without truncation, archive can become crowded in one region of the Pareto front.

---

# 9. Current Workflow in Practice

The workflow currently looks like this:

1. `Main` loads CSV data into `CandidateRepository`
2. `Main` loads the `.npy` distance matrix
3. `PopulationInitializer` creates generation 0 population
4. `Evaluate` scores the population
5. `Survivor` creates generation 0 archive
6. generation 0 archive is saved as the **initial archive snapshot**
7. for each generation:
   - `Selection` picks parents from archive
   - `Variation` creates offspring population
   - `Evaluate` scores offspring + archive
   - `Survivor` creates next archive
   - global raw objective min/max are updated
8. final archive is saved as the **final archive snapshot**
9. both snapshots are normalized in the same final global assessment space
10. `HypervolumeIndicator` computes HV for both
11. runtime and final diagnostics are printed

---

# 10. What Is Already Working

The following parts are already operational:

- candidate data loading
- distance matrix loading
- random initialization
- raw objective evaluation
- SPEA2 strength / raw fitness / density / total fitness
- non-dominated archive construction
- truncation logic
- binary tournament selection
- crossover / mutation / repair
- archive snapshots for initial vs final comparison
- runtime tracking
- post-hoc hypervolume comparison in a shared space

This means the project already has a functioning end-to-end optimization pipeline.

---

# 11. Known Issues and Open Questions

This section tracks remaining concerns and resolved items.

---

## 11.1 Objective scaling — RESOLVED

### `f1`
Previously `f1` used raw metre distances, causing values in the millions.
Now distances are converted to kilometres before applying `beta`.
This brings `f1` into a manageable single-digit to low double-digit range.

### `f2`
Previously `f2` used variance, which grew at squared scale and caused very wide spreads.
Now `f2` uses **coefficient of variation (CV)**, a dimensionless ratio typically in the 0–2 range.
This resolved the normalization and hypervolume interpretation issues.

---

## 11.2 Hypervolume sensitivity
After the objective scaling fixes, HV should produce more meaningful comparisons.

Monitoring notes:
- initial HV ratio should no longer appear artificially close to 1.0
- final HV improvement should be clearly visible
- if HV sensitivity is still too low, the normalization window may need further refinement

---

## 11.3 Internal normalization vs assessment normalization
These are conceptually different and must not be mixed.

Current code already moved in the right direction by doing final archive comparison post-hoc.

Still, this distinction should always be kept in mind when editing the project.

---

## 11.4 Generation-level diagnostics — PARTIALLY RESOLVED

Now implemented:
- best `f1` per generation
- best `f2` per generation

Still useful future diagnostics:
- number of unique archive individuals
- number of non-dominated archive individuals
- hypervolume trend over generations
- diversity indicators

These will be especially important for the future web UI.

---

# 12. Completed Steps and Remaining Next Steps

---

## 12.1 ~~Revisit `f1` scale~~ — DONE
Distance is now converted from metres to kilometres before applying `beta`.
This reduced `f1` values from ~1M to ~1, keeping the objective meaning the same.

---

## 12.2 ~~Revisit `f2` definition~~ — DONE
Variance was replaced with **coefficient of variation (CV)**.
CV = `std / mean` → dimensionless, bounded, and independent of distance unit.

---

## 12.3 ~~Centralize configuration~~ — DONE
All GA parameters are now defined in `config.GAParameters`.
`Main` reads from that class instead of using hard-coded values.

---

## 12.4 Improve assessment reliability
Hypervolume should remain the final quality metric.

Now that objectives are rescaled:
- rerun archive comparisons to verify HV improvement is visible
- monitor whether the normalization window is tight enough

---

## 12.5 Add UI-oriented outputs later
The project will eventually feed a web UI.

Future outputs likely needed:
- archive snapshots every N generations
- coordinates of selected locker IDs
- generation summaries as JSON
- best front progression for animation

This is not the current focus, but the code should stay compatible with it.

---

# 13. Practical Advice for Anyone Editing This Code

## If you want to change the optimization logic
Start with:
- `algorithm.Evaluate`
- `algorithm.Survivor`
- `algorithm.Selection`
- `algorithm.Variation`

## If you want to change the objective formulas
Start with:
- `service.FitnessCalculator`

## If you want to change GA parameters
Start with:
- `config.GAParameters`

## If you want to change archive quality assessment
Start with:
- `service.ObjectiveNormalizer`
- `service.HypervolumeIndicator`
- `app.Main`

## If you want to change data loading
Start with:
- `io.CsvLoader`
- `io.DistanceMatrixLoader`
- `model.CandidateRepository`

---

# 14. Final Summary

This codebase already contains a working SPEA2-style optimization engine for the Kadıköy locker placement problem.

The architecture is modular:
- data layer
- model layer
- config layer
- service layer
- algorithm layer
- orchestration layer

The current state:

- **algorithmic pipeline: implemented**
- **archive mechanics: implemented**
- **objective design: revised** (km-based f1, CV-based f2)
- **configuration: centralized** in `config.GAParameters`
- **diagnostics: per-generation** best f1/f2 logging
- **crossover: improved** with shared-gene priority recombination
- **assessment pipeline: functional** but may need further HV sensitivity tuning

The main focus going forward is:

> Validating that the revised objectives produce stable, interpretable results and tuning the assessment pipeline if needed.

The main challenge is no longer “does the GA run?”
It does.

The main challenge now is:

> Are the objective definitions and assessment pipeline producing values that are stable, interpretable, and scientifically convincing?

So the project is currently at this stage:

- **algorithmic pipeline: implemented**
- **archive mechanics: implemented**
- **assessment pipeline: partially implemented but still being refined**
- **objective design: needs the next major revision**

That is the correct current context for anyone continuing this project.