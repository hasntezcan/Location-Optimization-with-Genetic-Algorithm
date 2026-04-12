# Location Optimization with Genetic Algorithm

This project prepares spatial candidate data and uses Java genetic algorithm
components to explore parcel locker placement in Kadikoy.

The current codebase has two main parts:

- Python scripts for demand preparation and POI weighting.
- Java classes for loading candidate points, initializing populations, and
  evaluating the accessibility objective.

The intended optimization approach is SPEA2, but the full SPEA2 loop is still in
progress.

## Repository Structure

```text
data/       Candidate CSV files and distance matrix artifacts
scripts/    Python demand preparation scripts
src/        Java optimization model and GA classes
guide.md    Technical guide for the Java/data architecture
```

Useful guides:

- `guide.md`: current Java architecture, data flow, status, and next steps.
- `scripts/guide.md`: Python demand preparation workflow.
- `data/kadikoy_ARTIFACTS_GUIDE.md`: generated distance matrix artifact notes.

## Data Flow

Main input:

```text
data/candidate_points.csv
```

The CSV is expected to include candidate IDs, neighborhood names, POI counts,
coordinates, forbidden flags, existing locker counts, `population_candidate`,
`poi_score`, and `demand_final`.

Demand preparation uses:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

`CsvLoader.java` maps CSV columns by fixed positions, so keep the CSV column
order stable unless the loader is updated too.

## Python Scripts

Inspect current POI weights:

```bash
python3 scripts/calculate_poi_weights.py
```

Regenerate `poi_score` and `demand_final`:

```bash
python3 scripts/prepare_demand.py
```

`prepare_demand.py` writes back to `data/candidate_points.csv`. Keep a backup
before rerunning it if you need to preserve prior values.

## Java Usage

Compile:

```bash
javac src/*.java
```

Run the current entry point:

```bash
java -cp src Main
```

Current `Main.java` behavior:

1. Loads `data/candidate_points.csv`.
2. Finalizes the repository and ID-to-index mapping.
3. Creates an initial population with `k = 5` and `populationSize = 100`.
4. Prints generated individuals.

It does not yet run the full SPEA2 optimization loop.

## Implemented

- Candidate data model: `CandidatePoint`.
- CSV loading: `CsvLoader`.
- Candidate repository and distance matrix index mapping: `CandidateRepository`.
- Individual representation with objective and SPEA2-related fields:
  `Individual`.
- Random initial population generation: `PopulationInitializer`.
- F1 accessibility objective calculation: `FitnessCalculator.evaluateF1(...)`.
- EWM-based demand preparation scripts.

## Pending Work

- Load the distance matrix into Java or convert it to a Java-friendly format.
- Implement `FitnessCalculator.evaluateF2(...)` for equity.
- Add SPEA2 dominance, raw fitness, density, archive handling, selection,
  crossover, and mutation.
- Decide how forbidden candidates should be filtered or penalized during
  initialization and optimization.

## Notes

- Distance matrix artifacts live under `data/`.
- The matrix uses sorted candidate positions, not raw candidate IDs.
- `CandidateRepository.finalizeRepository()` builds the ID-to-index mapping that
  keeps Java evaluation aligned with the matrix order.
