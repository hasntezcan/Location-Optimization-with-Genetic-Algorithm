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
- Node.js and npm (for the Next.js dashboard)

### 1) (Optional) Prepare demand

To update the `poi_score` and `demand_final` columns:

```bash
python3 scripts/prepare_demand.py
```

Note: This script overwrites `data/candidate_points.csv`. The current committed
CSV already contains `poi_score` and `demand_final` generated with lambda `0.5`.
See [scripts/guide.md](scripts/guide.md).

### 2) Run the Java SPEA2 optimizer

Default entry point: [app.Main](src/main/java/app/Main.java)

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
- `run_metadata.json`: run parameters and estimated function evaluations

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

See [kadikoy_ARTIFACTS_GUIDE.md](data/kadikoy_ARTIFACTS_GUIDE.md) for details.

## Parameters

Main parameters live in [GAParameters](src/main/java/config/GAParameters.java):
- `K`, `POPULATION_SIZE`, `ARCHIVE_SIZE`, `MAX_GENERATIONS`
- `BETA`, `CROSSOVER_RATE`, `MUTATION_RATE`
- Hypervolume reference point and assessment settings

## Hyperparameter Analysis

Grid-search runner: [ParameterAnalyzer](src/main/java/app/ParameterAnalyzer.java)

```bash
mvn -q compile exec:java -Panalyze
```

Outputs:

- `output/parameter_analysis_results.csv`
- `output/ga_configuration_table.csv`

Smoke check:

```bash
mvn -q compile exec:java -Panalyze -Dexec.args="--smoke"
```

Post-processing:

```bash
python3 scripts/statistical_analysis.py
```

## UI (Next.js)

UI directory: [parcel-locker-ui](parcel-locker-ui)

The UI can visualize generated archive assets, browse Pareto/best-objective
solutions on a map, run the MCDA preference selector over Pareto solutions, and
in local/dev mode trigger the Java run via `/api/run-ga`.
See [parcel-locker-ui/README.md](parcel-locker-ui/README.md).

## Phase 1 Deployment

The current deployment path keeps the local/dev architecture: Next.js runs
`/api/run-ga`, which spawns Maven, waits for the Java optimizer, runs Python
plotting/post-processing, and refreshes UI mock assets.

Useful files:
- `DEPLOYMENT_PHASE1.md`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

Docker Compose:

```bash
docker compose up --build
```

This is a local/single-user deployment model, not a production job backend.

```
Location-Optimization-with-Genetic-Algorithm
├─ .dockerignore
├─ .env.example
├─ DEPLOYMENT_PHASE1.md
├─ Dockerfile
├─ docker-compose.yml
├─ pom.xml
├─ readme.md
├─ General_GUIDE.md
├─ guide.md
├─ requirements.txt
│
├─ data
│  ├─ candidate_points.csv
│  ├─ kadikoy_candidate_ids_sorted.npy
│  ├─ kadikoy_distance_meters_nxn.npy
│  ├─ kadikoy_index_map.csv
│  ├─ prepare_ga_inputs.py
│  └─ raw
│     ├─ candidate_points.gpkg
│     ├─ kadikoy_boundary.geojson
│     ├─ kadikoy.gpkg
│     ├─ Kadikoy_Base.gpkg
│     ├─ grid_100m_clipped.gpkg
│     ├─ grid_with_forbidden_area.gpkg
│     ├─ lockers_32635.gpkg
│     ├─ pois_all_points.gpkg
│     └─ small_grids_forbidden.gpkg
│
├─ scripts
│  ├─ calculate_poi_weights.py
│  ├─ prepare_demand.py
│  ├─ statistical_analysis.py
│  ├─ plot_analysis.py
│  ├─ plot_archives.py
│  ├─ tmp_generate_final_result_plots.py
│  └─ guide.md
│
├─ src
│  └─ main
│     └─ java
│        ├─ analyse_guide.md
│        ├─ SRC_GUIDE.MD
│        │
│        ├─ app
│        │  ├─ Main.java
│        │  ├─ ParameterAnalyzer.java
│        │  └─ backend_guide.md
│        │
│        ├─ algorithm
│        │  ├─ Evaluate.java
│        │  ├─ Selection.java
│        │  ├─ Survivor.java
│        │  ├─ Variation.java
│        │  └─ helper
│        │     ├─ Dominance.java
│        │     ├─ Pareto.java
│        │     └─ Truncation.java
│        │
│        ├─ config
│        │  ├─ GAParameters.java
│        │  ├─ GAResult.java
│        │  └─ GAState.java
│        │
│        ├─ io
│        │  ├─ CsvLoader.java
│        │  └─ DistanceMatrixLoader.java
│        │
│        ├─ model
│        │  ├─ CandidatePoint.java
│        │  ├─ CandidateRepository.java
│        │  └─ Individual.java
│        │
│        └─ service
│           ├─ FitnessCalculator.java
│           ├─ HypervolumeIndicator.java
│           ├─ ObjectiveNormalizer.java
│           └─ PopulationInitializer.java
│
└─ parcel-locker-ui
   ├─ package.json
   ├─ package-lock.json
   ├─ next.config.ts
   ├─ tsconfig.json
   ├─ eslint.config.mjs
   ├─ postcss.config.mjs
   ├─ README.md
   │
   ├─ public
   │  └─ mock
   │     ├─ candidate-points.json
   │     ├─ candidate_points.csv
   │     ├─ ga-results.json              (generated)
   │     ├─ archive_comparison_latest.png (generated)
   │     └─ kadikoy_boundary.geojson
   │
   └─ src
      ├─ app
      │  ├─ api
      │  │  └─ run-ga
      │  │     └─ route.ts
      │  ├─ globals.css
      │  ├─ layout.tsx
      │  └─ page.tsx
      │
      ├─ components
      │  └─ dashboard
      │     ├─ control-panel.tsx
      │     ├─ locker-detail-panel.tsx
      │     ├─ locker-map.tsx
      │     └─ locker-strip.tsx
      │
      ├─ lib
      │  ├─ chart-data.ts
      │  ├─ ga-api.ts
      │  ├─ ga-mock.ts
      │  ├─ mcda.ts
      │  ├─ mock-data.ts
      │  ├─ python-runner.ts
      │  ├─ solution-utils.ts
      │  ├─ types.ts
      │  └─ server
      │     ├─ ga-runner.ts
      │     └─ runtime-config.ts
      │
      └─ scripts
         ├─ build_candidate_json.py
         └─ process_ga_data.py

```
