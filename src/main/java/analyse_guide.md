# Parameter Analysis Guide (`analyse_guide.md`)

## Overview

This document describes the current `ParameterAnalyzer` workflow for the
Kadikoy Parcel Locker SPEA2 optimization project.

The analyzer is a Java grid-search runner for comparing fixed GA
configurations under a constant function-evaluation budget. It is separate from
the default `Main` single-run workflow.

Current implementation:

- File: `src/main/java/app/ParameterAnalyzer.java`
- Maven profile: `mvn -q compile exec:java -Panalyze`
- Output directory: `output/` by default
- Full output CSV: `output/parameter_analysis_results.csv`
- Smoke output CSV: `output/parameter_analysis_results_smoke.csv`
- Configuration table: `output/ga_configuration_table.csv`

Environment overrides:

```text
GA_CANDIDATE_CSV   candidate CSV path
GA_DISTANCE_MATRIX distance matrix path
GA_OUTPUT_DIR      output directory
```

## 1. Experimental Design

### 1.1 Locker Counts

The current grid evaluates four network sizes:

```text
K_VALUES = {1, 5, 10, 15}
```

### 1.2 GA Configurations

The analyzer builds 18 GA configurations:

```text
POPULATION_SIZES = {50, 100, 200}
MUTATION_RATES   = {0.10, 0.25, 0.40}
CROSSOVER_RATES  = {0.70, 0.90}
ARCHIVE_SIZE     = POPULATION_SIZE / 2
```

Each configuration is assigned an ID (`GA1`, `GA2`, ...).

### 1.3 Seeds

The full experiment uses 20 shared seeds:

```text
SEEDS = {1, 2, ..., 20}
```

Full grid-search size:

```text
4 K values × 18 GA configurations × 20 seeds = 1440 grid runs
```

### 1.4 Function-Evaluation Budgets

Each K value has a fixed target FE budget:

| K | Target FE |
| --- | --- |
| 1 | 30,000 |
| 5 | 50,000 |
| 10 | 80,000 |
| 15 | 100,000 |

Generation count is derived from:

```text
maxGenerations = (targetFE / populationSize) - 1
functionEvals  = populationSize × (maxGenerations + 1)
```

This keeps the comparison fair across population sizes.

### 1.5 Demand and Lambda

Lambda is not part of the current Java grid. `ParameterAnalyzer` evaluates
solutions using the precomputed `demand_final` values loaded from
`data/candidate_points.csv`, through the standard three-argument
`FitnessCalculator(distanceMatrix, repository, beta)` constructor.

If demand assumptions change, rerun `scripts/prepare_demand.py` first to update
`poi_score` and `demand_final` in the CSV, then rerun the analyzer.

## 2. Hypervolume Bounds

For each K, `ParameterAnalyzer` runs a calibration phase before the grid search:

```text
CALIBRATION_POPULATION_SIZE = 100
CALIBRATION_ARCHIVE_SIZE    = 50
CALIBRATION_SEEDS           = {101, 102, 103, 104, 105}
CALIBRATION_MARGIN          = 0.02
```

Calibration procedure:

1. Run SPEA2 with calibration seeds for the active K.
2. Union the final archive members.
3. Extract the non-dominated set from that union.
4. Compute min/max bounds for f1 and f2.
5. Expand each range by a 2% margin.
6. Use these locked bounds for all grid-search runs with that K.

The output `Final_HV` and `Final_HV_Ratio` are therefore comparable within the
same K value. They should not be treated as directly comparable across different
K values because each K uses its own calibration bounds.

## 3. Output CSV Schema

`parameter_analysis_results.csv` contains:

```text
Run_ID,K,Task,GA_ID,PopulationSize,ArchiveSize,MaxGenerations,TargetFE,
FunctionEvals,MutationRate,CrossoverRate,Seed,Runtime_ms,Final_HV,
Final_HV_Ratio,ND_Count,Final_ND_Archive_Ratio,Spacing_CV,
Best_f1,Best_f2,Mean_f1,Mean_f2
```

`ga_configuration_table.csv` contains:

```text
GA_ID,PopulationSize,ArchiveSize,MutationRate,CrossoverRate
```

## 4. Smoke Mode

For a quick wiring check:

```bash
mvn -q compile exec:java -Panalyze -Dexec.args="--smoke"
```

Smoke mode limits the run to:

```text
K values: first 1
GA configurations: first 2
Seeds: first 2
Target FE: 200
Calibration seeds: {101}
```

It writes:

```text
output/parameter_analysis_results_smoke.csv
```

## 5. Statistical Post-Processing

After the full analyzer run:

```bash
python3 scripts/statistical_analysis.py
```

Default input:

```text
output/parameter_analysis_results.csv
```

Default output directory:

```text
output/statistics/
```

Generated files:

```text
descriptive_by_k.csv
friedman_summary.csv
posthoc_bonferroni.csv
selected_configurations.csv
```

What the Python script does:

- Builds a Seed × GA_ID matrix of `Final_HV_Ratio` for each K.
- Computes descriptive statistics and mean ranks.
- Runs a Friedman test per K.
- Runs Bonferroni-corrected Wilcoxon post-hoc comparisons where Friedman is
  significant.
- Selects one configuration per K using HV ratio median/mean, variance,
  ND-archive ratio, runtime, and population size as tie-breakers.

Smoke post-processing:

```bash
python3 scripts/statistical_analysis.py \
  --input output/parameter_analysis_results_smoke.csv \
  --output-dir output/statistics_smoke
```

## 6. Legacy Plotting Note

`scripts/plot_analysis.py` is an older exploratory plotting script. It expects
an older CSV path and schema under:

```text
output/parameter analysis/parameter_analysis_results.csv
```

It references old columns such as `Lambda`, `PopSize`, `MutRate`, and
`CrossRate`. It should not be treated as the canonical analyzer post-processing
path for the current `ParameterAnalyzer` output. Use
`scripts/statistical_analysis.py` for reproducible statistical selection.
