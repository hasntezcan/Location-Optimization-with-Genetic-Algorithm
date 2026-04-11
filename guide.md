# Kadıköy Parcel Locker Placement Optimization — Technical Guide (SPEA2)

This document describes the technical structure of the Kadıköy parcel locker (kargo otomatı) placement project and summarizes the current codebase architecture. The goal is to optimize parcel locker locations using **SPEA2 (Strength Pareto Evolutionary Algorithm 2)** as a **multi-objective** optimization approach.

---

## 1) Project Overview

We formulate parcel locker placement as an urban multi-objective optimization problem. From a candidate set of grid-based locations within Kadıköy, the algorithm aims to select an optimal subset that balances:

- **Accessibility**: maximize service convenience and reach (e.g., demand-weighted mean distance).
- **Equity**: improve fairness of service distribution across neighborhoods (minimize the variance of accessibility between neighborhoods).

The optimization produces a **Pareto-optimal** set of solutions using SPEA2, eliminating the need for subjective weighted-sum aggregations.

---

## 2) Codebase Components

### `CandidatePoint.java`
**Purpose:** Data model representing a single candidate location.

**What it stores (typical fields):**
- Spatial coordinates: `lat`, `lon`
- Base Demand: `weightedPopulation` (derived from neighborhood population)
- POI Features: `poiScore` (0-1 score representing urban attractiveness)
- **Final Demand:** `demandFinal` (the ultimate metric combining population and POIs, used by the GA)
- Existing locker proximity/count features (if available)

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

**Why this matters:** Fitness calculations and GA operators require fast, constant-time access to candidate attributes by ID during millions of evaluations.

---

### `CsvLoader.java`
**Purpose:** Loads candidate data from the enriched CSV (`candidate_points_enriched.csv`) into the system.

**Responsibilities:**
- Parse CSV rows into `CandidatePoint` objects
- Convert types safely (String → int/double)
- Read flags such as `isForbidden` and map the new `demand_final` column.

---

### `Individual.java`
**Purpose:** Represents a single GA individual (solution candidate).

**Chromosome representation:**
- A list/array of `k` candidate IDs (or indices) representing chosen locker locations.

**Fitness representation:**
- In the SPEA2 context, "fitness" is not a single scalar. The class stores:
  - Dominance / strength calculations
  - Raw fitness
  - Density estimation (k-th nearest neighbor distance in objective space)
  - Objective vectors: `accessibilityScore` and `equityScore` stored separately.

---

### `PopulationInitializer.java`
**Purpose:** Creates the initial population for the evolutionary run.

**Typical logic:**
- Randomly select `k` candidate locations per individual.
- Use `Collections.shuffle()` or equivalent to ensure diversity.

**Why this matters:** Initial diversity helps SPEA2 explore different trade-offs across the Pareto front early in the run.

---

### `Main.java`
**Purpose:** Application entry point and workflow orchestration.

**Typical flow:**
1. Load candidates using `CsvLoader`
2. Store candidates in `CandidateRepository`
3. Initialize population with `PopulationInitializer`
4. Start the optimization loop (SPEA2 evaluation, environmental selection, mating selection, variation)

---

## 3) Data & Object Flow (How Components Interact)

1. **Main** calls **CsvLoader** → produces **CandidatePoint** objects  
2. **CandidateRepository** stores them → provides O(1) lookup by ID  
3. **PopulationInitializer** uses repository IDs to create **Individuals** 4. During evaluation, **Individuals** access candidate attributes (specifically `demandFinal`) via **CandidateRepository** to calculate spatial distances.

---

## 4) Technical Details & Implementation Notes

### 4.1 Data-Driven Demand Representation (EWM Integration)
Demand is not treated as a simple population metric. To account for the attractiveness of urban facilities (POIs) without subjective bias (e.g., avoiding arbitrary AHP weights), we utilize the **Entropy Weight Method (EWM)**. 

A preprocessing Python script (`scripts/prepare_demand.py`) generates the final demand for the GA:
1. **`baseDemand`**: The starting demographic weight (currently `weighted_population`).
2. **`poi_score`**: An objective 0-1 score derived from EWM, which assigns weights based on the spatial information variance of each POI category (e.g., Universities receive higher weights than standard bus stops).
3. **`demand_final`**: The ultimate weight for each candidate, computed as:
   `w_i = baseDemand_i * (1 + λ * poi_score_i)`
   *(where λ is a sensitivity parameter controlling the "pull" of POIs).*

**Important:** The Java GA strictly uses `demand_final` for all objective calculations. It does not interact with raw POI counts.

---

### 4.2 Fitness Objectives (SPEA2)

#### Objective 1: Accessibility (Minimize)
The demand-weighted mean distance from all demand points to their nearest selected locker.
- Evaluates how efficiently the locker network serves the population, weighted heavily towards areas with high `demand_final`.

#### Objective 2: Equity (Minimize)
The variance of the mean accessibility distances across different neighborhoods.
- Ensures that service quality does not disproportionately favor a single highly-populated district at the complete expense of peripheral neighborhoods.

---

### 4.3 Genetic Operators

- **Selection:** Binary tournament selection (comparing SPEA2 fitness values).
- **Crossover:** Single-point or uniform crossover on ID lists, ensuring no duplicate IDs exist within a single chromosome.
- **Mutation:** Replace one chosen locker ID with a randomly selected valid candidate ID.
- **Constraint Handling:** `isForbidden` areas are filtered out before initialization.

---

## 5) Distance Matrix Artifacts (External Precomputation)

To enable fast distance-based evaluation, we utilize a precomputed distance matrix generated via Python:

- `kadikoy_distance_meters_nxn.npy` — distances between candidates (meters)
- `kadikoy_candidate_ids_sorted.npy` — ID ordering used by the matrix
- `kadikoy_index_map.csv` — idx ↔ id ↔ lon/lat mapping for debug/pinning
- See: `data/kadikoy_ARTIFACTS_GUIDE.md` for details

**Important concept:**
- The distance matrix is indexed by **idx (0..N-1)**, not the raw candidate ID.
- Mapping is done via `ids[idx] = candidateID`.

---

## 6) Current Status vs Next Steps

**Implemented / Available:**
- Candidate ingestion (CSV → CandidatePoint → Repository)
- Initial population generation
- Distance matrix artifacts produced and versioned
- POI Weighting via Entropy Weight Method (EWM) and `demand_final` generation (Python pipeline)

**Next Steps:**
- Update `CandidatePoint.java` and `CsvLoader.java` to ingest the new `demand_final` column.
- Implement the mathematical objective computations (Accessibility and Equity) in Java using the distance matrix.
- Complete the SPEA2 pipeline logic (archive truncation, strength calculations, density estimation).