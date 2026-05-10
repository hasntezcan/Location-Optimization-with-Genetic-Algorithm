# Scripts Guide

This folder contains all Python scripts for the Kadikoy parcel locker optimization
project. Scripts cover demand preparation, distance matrix generation, archive plotting,
parameter-analysis post-processing, and exploratory thesis figure generation.

---

## Data Flow Overview

```text
data/candidate_points.csv
        │
        ▼
scripts/prepare_demand.py          → updates poi_score + demand_final in CSV
        │
        ▼
data/prepare_ga_inputs.py          → generates distance matrix artifacts
        │
        ▼
[Java SPEA2 run]                   → output/initial_archive.csv, output/final_archive.csv
        │
        └──► scripts/plot_archives.py        → output/archive_comparison_latest.png

[Java ParameterAnalyzer run]        → output/parameter_analysis_results.csv
        │
        └──► scripts/statistical_analysis.py → output/statistics/…
```

---

## 1. Demand Preparation Scripts

### `prepare_demand.py`

Main demand preparation script. Reads and **overwrites** `data/candidate_points.csv`.

What it does:

- Reads `data/candidate_points.csv`.
- Finds raw POI columns by the `poi_` prefix while excluding generated columns
  (`poi_score`, `demand_final`).
- Applies `log1p` transformation and min-max normalization to POI columns.
- Calculates POI weights with the Entropy Weight Method (EWM).
- Prompts for the lambda (λ) parameter (accepts both `.` and `,` as decimal separator).
- Updates `poi_score` and `demand_final`.
- Saves the result back to `data/candidate_points.csv`.

Run from the project root:

```bash
python3 scripts/prepare_demand.py
```

Demand formula:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

Lambda interpretation:

- `0.0`: no POI influence; demand follows `population_candidate`.
- `0.5`: balanced POI influence.
- `1.0`: stronger priority for urban activity hubs.

### `calculate_poi_weights.py`

Read-only analysis script for inspecting the current EWM POI weights.

What it does:

- Reads `data/candidate_points.csv`.
- Selects raw POI columns (excluding `poi_score`, `demand_final`).
- Prints the EWM weights sorted by descending weight.
- Does not write to the CSV file.

Run from the project root:

```bash
python3 scripts/calculate_poi_weights.py
```

---

## 2. Archive Plotting Script

### `plot_archives.py`

Reads the Java optimization output and generates a four-panel comparison plot.

Inputs:

```text
output/initial_archive.csv
output/final_archive.csv
output/run_metadata.json
```

Output:

```text
output/archive_comparison_latest.png
```

Plot panels:

- Initial Archive — Raw Objective Space
- Final Archive — Raw Objective Space
- Initial → Final Improvement Metrics (raw-objective ND metrics, C-metric)
- Final Archive — Hypervolume Space (normalized using final-ND bounds)

The script also prints:

- Archive sizes and ND counts.
- Pearson and Spearman correlation between f1 and f2.
- Best f1, best f2.
- C-metric values.

Run from the project root:

```bash
python3 scripts/plot_archives.py
```

---

## 3. Parameter Analysis Post-Processing Scripts

### `statistical_analysis.py`

Analyzes the output of `ParameterAnalyzer` (Java grid search) with rigorous
statistical tests.

Input:

```text
output/parameter_analysis_results.csv
```

What it does:

- Builds a Seed × GA_ID hypervolume matrix per K value.
- Computes descriptive statistics (mean, median, std, IQR, mean rank) per
  configuration per K.
- Runs the **Friedman test** to check whether any configurations differ
  significantly per K.
- Runs **Bonferroni-corrected Wilcoxon post-hoc tests** for K values where
  Friedman is significant.
- Selects the best configuration per K using the following priority:
  HV_Ratio median → HV_Ratio mean → std → ND archive ratio → runtime → pop size.

Output directory (default):

```text
output/statistics/
    ├── descriptive_by_k.csv
    ├── friedman_summary.csv
    ├── posthoc_bonferroni.csv
    └── selected_configurations.csv
```

Run:

```bash
python3 scripts/statistical_analysis.py
python3 scripts/statistical_analysis.py --input output/parameter_analysis_results_smoke.csv \
                                         --output-dir output/statistics_smoke
```

### `plot_analysis.py`

Older exploratory visualization script for the ParameterAnalyzer output.

Reads from `output/parameter analysis/parameter_analysis_results.csv` (note:
path uses Turkish-named folder from an earlier run).

Produces five plots in `output/parameter analysis/plots_advanced/`:

1. Population size vs Final HV (boxplot).
2. Lambda vs Final HV per K (pointplot).
3. Mutation × Crossover heatmaps per K.
4. MaxGen vs ND Count (convergence proxy).
5. Runtime vs HV (computation cost tradeoff).

Also writes `thesis_detailed_report.txt` with champion configurations per K and
per (K, Lambda).

Note: This script has a hardcoded path and is maintained for reference. Prefer
`statistical_analysis.py` for reproducible statistical comparison.

---

## 4. Temporary and Exploratory Plot Scripts

### `tmp_generate_final_result_plots.py`

Temporary helper used to generate final-result plots under
`sections/figures/final_results/`. It is kept for report figure regeneration,
not as part of the core optimization runtime.

---

## 5. Important Notes

### Rerun Safety for Demand Scripts

Both `prepare_demand.py` and `calculate_poi_weights.py` select raw POI columns using:

```python
col.startswith("poi_") and col not in {"poi_score", "demand_final"}
```

This prevents reruns on an already enriched CSV from feeding `poi_score` back
into the EWM.

### CSV Column Alignment Contract

The distance matrix was generated in ascending candidate ID order. Java preserves
that alignment with `CandidateRepository.finalizeRepository()`. This alignment
must be preserved whenever the candidate CSV or matrix artifacts change.

### Forbidden Candidates

`is_forbidden = 1` rows remain in both the CSV and distance matrix as demand
grid points. They are excluded from the selectable locker universe:

- In Java: via `CandidateRepository.getSelectableCandidateIds()`.

### Recommended Current Workflow

```bash
# 1. Inspect POI weights (optional)
python3 scripts/calculate_poi_weights.py

# 2. Update demand (if candidate data changed)
python3 scripts/prepare_demand.py

# 3. Run a single SPEA2 optimization
mvn -q compile exec:java

# 4. Visualize initial/final archive behavior
python3 scripts/plot_archives.py

# 5. Run parameter grid search when needed
mvn -q compile exec:java -Panalyze

# 6. Analyze parameter grid-search output
python3 scripts/statistical_analysis.py
```
