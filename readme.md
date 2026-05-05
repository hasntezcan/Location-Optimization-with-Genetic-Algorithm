# Location Optimization with Genetic Algorithm

This project solves a **bi-objective** parcel locker location optimization problem for **Kadikoy** by selecting locker locations from a set of candidate points.

Core approach:
- **SPEA2**-based multi-objective GA (Java)
- Demand/POI score preparation and analysis (Python)
- Result exploration dashboard (Next.js)

## Quick Start

Requirements:
- Java 17
- Maven
- Python 3 (for demand scripts and plotting)

### 1) (Optional) Prepare demand

To update the `poi_score` and `demand_final` columns:

```bash
python3 scripts/prepare_demand.py
```

Note: This script overwrites `data/candidate_points.csv`. The current committed
CSV already contains `poi_score` and `demand_final` generated with lambda `0.5`.
See [scripts/guide.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/scripts/guide.md).

### 2) Run the Java SPEA2 optimizer

Default entry point: [app.Main](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/Main.java)

```bash
mvn -q compile exec:java
```

### 3) Generate archive plots

```bash
python3 scripts/plot_archives.py
```

## Outputs

The Java run produces the following under `output/`:
- `initial_archive.csv`: archive snapshot after generation 0
- `final_archive.csv`: archive snapshot after the final generation

The plot script produces:
- `output/archive_comparison_latest.png`

## Inputs and Artifacts

Main inputs:
- `data/candidate_points.csv`
- `data/kadikoy_distance_meters_nxn.npy`

Important contract:
- The distance matrix indexing order is **candidate id ascending**.
- The Java side maintains this alignment via `CandidateRepository.finalizeRepository()`.
- `is_forbidden = 1` rows remain demand grid points, but Java excludes them
  from the selectable locker-location universe.
- `poi_score` and `demand_final` must be present for the default scientific
  demand model. If they are missing, `CsvLoader` falls back to population-only
  demand, which changes the experiment.

See [kadikoy_ARTIFACTS_GUIDE.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/data/kadikoy_ARTIFACTS_GUIDE.md) for details.

## Parameters

Main parameters live in [GAParameters](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/config/GAParameters.java):
- `K`, `POPULATION_SIZE`, `ARCHIVE_SIZE`, `MAX_GENERATIONS`
- `BETA`, `CROSSOVER_RATE`, `MUTATION_RATE`
- Hypervolume reference point and assessment settings

## Hyperparameter Analysis

Grid-search runner: [ParameterAnalyzer](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/ParameterAnalyzer.java)

```bash
mvn -q compile exec:java -Panalyze
```

Output: `output/parameter_analysis_results.csv`

## UI (Next.js)

UI directory: [parcel-locker-ui](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/parcel-locker-ui)

The UI can visualize mock assets, and in local/dev mode it can also trigger the Java run via `/api/run-ga`.
See [parcel-locker-ui/README.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/parcel-locker-ui/README.md).
