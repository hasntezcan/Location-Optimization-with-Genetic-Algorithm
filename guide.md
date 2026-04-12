# Kadikoy Parcel Locker Placement Optimization Guide

This document summarizes the current structure of the parcel locker placement
optimization project. The project combines a Python data preparation pipeline
with Java classes for candidate loading, population initialization, and fitness
evaluation.

## Goal

The project models parcel locker placement as a multi-objective optimization
problem for Kadikoy. The algorithm selects `k` candidate points from a larger
grid-based candidate set.

Current objective direction:

- Minimize accessibility cost: demand-weighted distance from demand points to
  the nearest selected locker.
- Minimize equity cost: planned objective for balancing service quality across
  neighborhoods.

The intended optimization method is SPEA2, but the full SPEA2 loop is not yet
implemented in the current Java code.

## Data Pipeline

Primary input:

```text
data/candidate_points.csv
```

The CSV contains candidate IDs, neighborhood names, POI counts, coordinates,
forbidden flags, existing locker counts, candidate population, `poi_score`, and
`demand_final`.

Demand preparation scripts:

- `scripts/calculate_poi_weights.py`: read-only helper that prints POI weights
  calculated with the Entropy Weight Method.
- `scripts/prepare_demand.py`: updates `poi_score` and `demand_final` in
  `data/candidate_points.csv`.

Demand formula:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

See `scripts/guide.md` for the detailed Python workflow and overwrite notes.

## Java Components

### `CandidatePoint.java`

Data model for one candidate grid point.

Important fields:

- `id`
- `mahalleNameTurkish`
- `mahalleNameEnglish`
- `mahallePopulation`
- POI counts such as `poiAtm`, `poiBank`, `poiHospital`, and `poiTransport`
- Coordinates: `lon`, `lat`
- `isForbidden`
- `lockerCount`
- `gridCountByMahalle`
- `population`
- `poiScore`
- `demandScore`

`demandScore` corresponds to the CSV `demand_final` value and is used by the
fitness calculation.

### `CsvLoader.java`

Loads rows from `data/candidate_points.csv` and creates `CandidatePoint`
objects.

Important implementation detail:

- The loader maps CSV fields by fixed column indexes.
- If the CSV column order changes, the loader mapping must be updated too.

### `CandidateRepository.java`

Stores candidates and provides ID/index lookup for matrix-based evaluation.

Key structures:

- `candidateMap`: candidate ID to `CandidatePoint`.
- `idToIndexMap`: candidate ID to distance matrix index.
- `sortedCandidates`: candidates sorted by ID to match the matrix order.

Call `finalizeRepository()` after loading all candidates. It sorts the
candidates and builds the ID-to-index mapping used by `FitnessCalculator`.

### `Individual.java`

Represents one solution candidate in the genetic algorithm.

Important fields:

- `chromosome`: selected candidate IDs.
- `objective1`: accessibility objective.
- `objective2`: equity objective.
- SPEA2-related fields: `strength`, `rawFitness`, `density`, `totalFitness`.

### `PopulationInitializer.java`

Creates the initial population.

Current behavior:

- Validates candidate IDs, `k`, and population size.
- Creates each chromosome by shuffling available candidate IDs.
- Takes the first `k` IDs from the shuffled list.
- Creates an `Individual` for each chromosome.

### `FitnessCalculator.java`

Evaluates objective values using a distance matrix and the repository.

Implemented:

- `evaluateF1(...)`: calculates demand-weighted accessibility cost.

Not yet implemented:

- `evaluateF2(...)`: equity objective placeholder.

The F1 score uses:

```text
sum(demandScore_i * minDistanceToSelectedLocker_i^beta) / totalSystemDemand
```

### `Main.java`

Current entry point.

Current flow:

1. Create `CandidateRepository`, `CsvLoader`, and `PopulationInitializer`.
2. Load `data/candidate_points.csv`.
3. Call `repository.finalizeRepository()`.
4. Set `k = 5` and `populationSize = 100`.
5. Initialize the population.
6. Print the generated individuals.

The current `Main` does not yet run the full SPEA2 optimization loop.

## Distance Matrix Artifacts

Distance matrix files are stored under `data/`:

- `data/kadikoy_distance_meters_nxn.npy`
- `data/kadikoy_candidate_ids_sorted.npy`
- `data/kadikoy_index_map.csv`
- `data/kadikoy_ARTIFACTS_GUIDE.md`

Important concept:

- The matrix is indexed by sorted candidate position, not directly by candidate
  ID.
- `CandidateRepository.finalizeRepository()` creates the Java ID-to-index map
  needed to use this matrix consistently.

## Current Status

Implemented:

- Candidate CSV loading.
- Candidate repository and matrix index mapping.
- Initial population generation.
- Individual representation with objective and SPEA2 fields.
- F1 accessibility objective calculation.
- Python demand preparation with EWM-based `poi_score` and `demand_final`.

Pending:

- Load the `.npy` distance matrix into Java or provide a Java-readable matrix
  format.
- Implement F2 equity objective.
- Implement SPEA2 dominance, strength, raw fitness, density, archive handling,
  selection, crossover, and mutation.
- Filter or handle forbidden candidate points during population initialization
  if they should not be selected.

## Recommended Development Order

1. Confirm that `data/candidate_points.csv` has the expected column order.
2. Run `scripts/calculate_poi_weights.py` to inspect POI weighting.
3. Run `scripts/prepare_demand.py` if demand columns need to be regenerated.
4. Keep `CandidateRepository` sorting consistent with the distance matrix order.
5. Add Java loading for the distance matrix.
6. Complete `FitnessCalculator.evaluateF2(...)`.
7. Implement the SPEA2 loop and genetic operators.
