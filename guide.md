# Kadıköy Parcel Locker Placement Optimization — Technical Guide (SPEA2)

This document describes the technical structure of the Kadıköy parcel locker (kargo otomatı) placement project and summarizes the current codebase architecture. The goal is to optimize parcel locker locations using **SPEA2 (Strength Pareto Evolutionary Algorithm 2)** as a **multi-objective** optimization approach.

---

## 1) Project Overview

We formulate parcel locker placement as an urban multi-objective optimization problem. From a candidate set of grid-based locations within Kadıköy, the algorithm aims to select an optimal subset that balances:

- **Accessibility**: maximize service convenience / reach (e.g., demand coverage, proximity-based service quality).
- **Equity**: improve fairness of service distribution across neighborhoods (avoid over-serving some areas while under-serving others).

The optimization is planned to produce **Pareto-optimal** solutions using SPEA2.

---

## 2) Codebase Components

### `CandidatePoint.java`
**Purpose:** Data model representing a single candidate location.

**What it stores (typical fields):**
- Spatial coordinates: `lat`, `lon`
- Demand proxy: `weightedPopulation` (derived from neighborhood population normalization)
- POI counts around the candidate (e.g., ATM, bank, hospital, school, etc.)
- Existing locker proximity/count features (if available in the CSV)

**Notes:**
- `toString()` is used for debugging / inspection.
- This class is designed to carry all features needed by the fitness evaluation stage.

---

### `CandidateRepository.java`
**Purpose:** In-memory storage and lookup of all candidates.

**Key idea:** Uses a `HashMap<Integer, CandidatePoint>` for **O(1)** access by candidate ID.

**Common operations:**
- `addCandidate(CandidatePoint candidate)`
- `getCandidateById(int id)`
- `getAllCandidates()`
- `getAllCandidateIds()`

**Why this matters:** Fitness calculations and GA operators often require quick access to candidate attributes by ID.

---

### `CsvLoader.java`
**Purpose:** Loads candidate data from `candidate_points.csv` into the system.

**Responsibilities:**
- Parse CSV rows into `CandidatePoint` objects
- Convert types safely (String → int/double)
- Read flags such as `isForbidden` (if present) and handle them consistently

---

### `Individual.java`
**Purpose:** Represents a single GA individual (solution candidate).

**Chromosome representation:**
- A list/array of candidate IDs (or indices) representing chosen locker locations.

**Fitness representation:**
- In the SPEA2 context, “fitness” is not a single scalar objective. The class structure is intended to support:
  - dominance / strength calculations
  - raw fitness
  - density estimation
  - multi-objective values (Accessibility, Equity) stored separately

> Note: If the current code uses a placeholder scalar `fitness`, it should later be refactored to store objective vectors + SPEA2-specific values.

---

### `PopulationInitializer.java`
**Purpose:** Creates the initial population for the evolutionary run.

**Typical logic:**
- Randomly select `k` candidate locations per individual
- Use `Collections.shuffle()` or equivalent to ensure diversity

**Why this matters:** Initial diversity helps SPEA2 explore different trade-offs early.

---

### `Main.java`
**Purpose:** Application entry point and workflow orchestration.

**Typical flow:**
1. Load candidates using `CsvLoader`
2. Store candidates in `CandidateRepository`
3. Initialize population with `PopulationInitializer`
4. Start the optimization loop (SPEA2 steps)

---

## 3) Data & Object Flow (How Components Interact)

1. **Main** calls **CsvLoader** → produces **CandidatePoint** objects  
2. **CandidateRepository** stores them → provides O(1) lookup by ID  
3. **PopulationInitializer** uses repository IDs to create **Individuals**  
4. During evaluation, **Individuals** access candidate attributes via **CandidateRepository**

---

## 4) Technical Details & Implementation Notes

### 4.1 Demand Representation
- `weightedPopulation` is currently the primary demand proxy for each candidate.
- It is computed externally (QGIS pipeline) and stored in the CSV.
- If neighborhood-level normalization is used, it should be documented in the data pipeline guide.

---

### 4.2 Fitness Objectives (Planned)

> The current structure supports multi-objective evaluation, but objective implementations may still be placeholders depending on the current sprint.

#### Accessibility (Objective 1)
Typical approaches may include:
- POI-based accessibility proxies (counts within 300m)
- distance-based coverage models
- methods such as **2SFCA (Two-Step Floating Catchment Area)** if capacity/demand structure is modeled

#### Equity (Objective 2)
Measures how fairly service is distributed across neighborhoods, such as:
- variance / std. deviation of coverage between neighborhoods
- worst-served neighborhood minimization
- Gini-like inequality measures (optional)

---

### 4.3 Genetic Operators (Planned)

Even if the current code has not implemented all operators yet, the chromosome design supports:

- **Selection:** binary tournament selection (SPEA2-compatible)
- **Crossover:** single-point / uniform crossover on ID lists
- **Mutation:** replace one chosen ID with another valid candidate ID

> Constraint handling (e.g., uniqueness, forbiddens, minimum spacing) should be enforced during crossover/mutation repair.

---

## 5) Distance Matrix Artifacts (External Precomputation)

To enable fast distance-based evaluation (overlap/coverage/dispersion), we generate a precomputed distance matrix:

- `kadikoy_distance_meters_nxn.npy` — distances between candidates (meters)
- `kadikoy_candidate_ids_sorted.npy` — ID ordering used by the matrix
- `kadikoy_index_map.csv` — idx ↔ id ↔ lon/lat mapping for debug/pinning
- See: `data/GA_Input_Artifacts_Guide.md` for details

**Important concept:**
- The distance matrix is indexed by **idx (0..N-1)**, not raw candidate ID.
- Mapping is done via `ids[idx]`.

---

## 6) Current Status vs Next Steps

**Implemented / available**
- Candidate ingestion (CSV → CandidatePoint → Repository)
- Initial population generation
- Distance matrix artifacts produced and versioned

**Next steps**
- Implement objective computations (Accessibility, Equity)
- Implement SPEA2 pipeline (strength, raw fitness, density, archive handling)
- Integrate distance matrix into evaluation efficiently (idx mapping)
- Output: Pareto set solutions → map pins via `kadikoy_index_map.csv`

---

This guide reflects the current project architecture and is intended to be updated after each major change.