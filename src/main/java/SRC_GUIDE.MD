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
- distance penalty is applied using a distance-decay exponent `beta`
- weighted demand contribution is accumulated

Current implementation note:
- distances are currently read from a precomputed **distance matrix**
- `beta = 2` is being used in experiments
- current `f1` values can become numerically large, especially because distance penalties are strong

### Objective 2: Equity (`f2`)
Current logic measures inter-neighborhood inequality.

At the moment:
- neighborhood-level accessibility values are aggregated
- equity is represented using **variance across neighborhood means**

Important note:
- this objective can become **very large**
- because variance grows at squared scale
- this has already created normalization and hypervolume interpretation issues

This is one of the main areas planned for revision.

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
- stores an initial archive snapshot
- stores a final archive snapshot
- tracks global raw objective bounds across generations
- applies post-hoc normalization for archive comparison and HV computation

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

### Important note
This is also the most likely place where future methodological revisions will happen.

Why:
- `f1` can become very large depending on distance treatment
- `f2` currently uses variance and can explode in magnitude
- hypervolume difficulties may partially come from objective scaling behavior defined here

### Expected future revisions
Likely future experiments:
- rescaling distance before applying `beta`
- revisiting `f2` definition
- testing standard deviation / coefficient of variation / Gini as equity alternatives
- improving interpretability of raw objective ranges

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

This section is critical.

---

## 11.1 Objective scaling still needs revision
The biggest current technical concern is not the GA loop itself, but the **objective behavior**.

### `f1`
`f1` may still be numerically too large because:
- distance penalties are strong
- distance units may still create inflated values

### `f2`
`f2` is currently the bigger concern.
Using variance over already-large accessibility values can create very wide spreads.

This can:
- distort assessment
- make hypervolume hard to interpret
- create large min-max gaps

---

## 11.2 Hypervolume sensitivity
Even after fixing comparability across generations, initial HV has still sometimes appeared too high.

This suggests:
- archive quality may already be decent even in generation 0
- or more likely, the objective space still has large outlier-driven spreads

This is not only an HV problem.
It is also a clue that objective definitions may need refinement.

---

## 11.3 Internal normalization vs assessment normalization
These are conceptually different and must not be mixed.

Current code already moved in the right direction by doing final archive comparison post-hoc.

Still, this distinction should always be kept in mind when editing the project.

---

## 11.4 Need for better generation-level diagnostics
Right now the run prints archive contents and summary information.

Still useful future diagnostics would be:
- best `f1` per generation
- best `f2` per generation
- number of unique archive individuals
- number of non-dominated archive individuals
- hypervolume trend over generations
- diversity indicators

These will be especially important for the future web UI.

---

# 12. Planned Next Steps

These are the most important technical next steps.

---

## 12.1 Revisit `f1` scale
Investigate whether distance should be rescaled before exponentiation.

Possible direction:
- use kilometers instead of raw meters
- or otherwise scale distance before applying `beta`

Goal:
- keep meaning the same
- reduce objective inflation

---

## 12.2 Revisit `f2` definition
This is one of the main expected changes.

Possible alternatives to variance:
- standard deviation
- coefficient of variation
- mean absolute deviation
- Gini coefficient

If variance remains, it may still be necessary to:
- change the scale of the underlying accessibility values
- or transform the neighborhood-level values before variance calculation

---

## 12.3 Improve assessment reliability
Hypervolume should remain the final quality metric, but its interpretation depends on objective behavior.

After objective revisions:
- rerun archive comparisons
- check whether initial HV becomes more reasonable
- verify that final HV improvement becomes clearer

---

## 12.4 Add UI-oriented outputs later
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

The architecture is now reasonably modular:
- data layer
- model layer
- service layer
- algorithm layer
- orchestration layer

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