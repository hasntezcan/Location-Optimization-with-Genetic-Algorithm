# Scripts Guide

This folder contains all Python scripts for the Kadikoy parcel locker optimization
project. Scripts cover demand preparation, distance matrix generation, archive plotting,
RQ experimental validation, statistical analysis, and thesis table/figure export.

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
        ├──► scripts/plot_archives.py        → output/archive_comparison_latest.png
        │
        └──► scripts/run_rq_experiments.py  → output/rq_analysis/…
                     │
                     ├──► scripts/plot_rq_results.py     → output/rq_analysis/plots/
                     └──► scripts/export_thesis_tables.py → output/rq_analysis/tables/
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

## 3. RQ Analysis Pipeline

The RQ (Research Question) pipeline validates the SPEA2 optimizer against greedy
baselines for K ∈ {3, 6, 10} using 5 random seeds. It produces all metrics,
statistical tests, plots, and LaTeX tables needed for the thesis.

### Pipeline execution order

```bash
# Step 1: Run all SPEA2 experiments and compare with baselines
python3 scripts/run_rq_experiments.py

# Step 2: Generate thesis-quality figures
python3 scripts/plot_rq_results.py

# Step 3: Export LaTeX and Markdown tables
python3 scripts/export_thesis_tables.py
```

---

### `evaluate_solution.py`

Core evaluation library. Computes all metrics for a given set of selected locker IDs.

**Used as a library** by `run_rq_experiments.py` and `generate_baselines.py`.

Key public API:

```python
from evaluate_solution import load_problem_data, compute_all_metrics

data = load_problem_data()
metrics = compute_all_metrics(locker_ids, data)
```

`load_problem_data()` reads `data/candidate_points.csv` and
`data/kadikoy_distance_meters_nxn.npy`, sorts candidates by ascending ID (same
order as the Java repository), and builds the ID-to-index mapping.

`compute_all_metrics()` returns:

| Key | Meaning |
| --- | --- |
| `mean_distance_m` | Demand-weighted mean distance to nearest locker (m) |
| `median_distance_m` | Demand-weighted median distance (m) |
| `coverage_500m` | % of demand within 500 m |
| `coverage_1000m` | % of demand within 1 km |
| `coverage_2000m` | % of demand within 2 km |
| `cv_equity` | CV of neighborhood-level weighted mean distances |
| `variance_equity` | Variance of neighborhood-level weighted mean distances |
| `mahalle_mean_distances` | `{neighborhood → weighted mean distance}` dict |
| `nearest_distances` | Raw `(N,)` array of nearest-locker distances for each candidate |

Self-test:

```bash
python3 scripts/evaluate_solution.py --test
```

---

### `generate_baselines.py`

Generates three baseline placements for comparison with the SPEA2 optimizer.

Baselines:

1. **Greedy Demand** — top-K non-forbidden candidates sorted by `demand_final` descending.
2. **Random** — average of 30 random K-selections (seeded for reproducibility).
3. **Existing network** — all candidates with `locker_count > 0` (contextual reference only).

Can be run standalone:

```bash
python3 scripts/generate_baselines.py
python3 scripts/generate_baselines.py --validate   # sanity checks
```

Output:

```text
output/rq_analysis/baselines/baseline_results.json
```

Also called internally by `run_rq_experiments.py`.

---

### `statistical_tests.py`

Statistical test library for Research Question validation.

**VT1 — Accessibility test** (`test_accessibility`):

- Input: per-candidate nearest distances for baseline and optimized placements.
- Tests: Wilcoxon signed-rank (primary, non-parametric) + paired t-test (supplementary).
- Effect size: Cohen's d.
- H1: baseline distances > optimized distances (one-sided).

**VT3 — Equity test** (`test_equity`):

- Input: `{neighborhood → weighted mean distance}` dicts for baseline and optimized.
- Metrics: CV reduction, variance reduction.
- Tests: Levene's test + Brown-Forsythe (center=median) supplementary.

Used as a library by `run_rq_experiments.py`.

Self-test:

```bash
python3 scripts/statistical_tests.py --self-test
```

---

### `run_rq_experiments.py`

**Main RQ orchestrator.** Runs all SPEA2 experiments, computes baselines, applies
statistical tests, and saves aggregated results.

Default configuration:

```text
K_VALUES = [3, 6, 10]
SEEDS    = [42, 123, 7, 256, 999]   (5 runs per K)
POPULATION_SIZE = 200
ARCHIVE_SIZE    = 100
CROSSOVER_RATE  = 0.9
MUTATION_RATE   = 0.4
MAX_GENERATIONS = {3: 150, 6: 250, 10: 400}  (FE-budget-aware)
```

What it does (three phases):

**Phase 1 — Baselines**
- Calls `generate_baselines.py` internally.
- Computes greedy, random, and existing-network metrics for each K.

**Phase 2 — SPEA2 runs**
- For each (K, seed) pair, calls `mvn -q compile exec:java` with override args.
- Copies `final_archive.csv`, `initial_archive.csv`, `run_metadata.json` to
  `output/rq_analysis/experiments/k{K}_seed{seed}/`.
- Parses the final Pareto front (non-dominated set).
- Selects three representative solutions: Best-f1, Best-f2, Knee-point.
- Evaluates each representative with `compute_all_metrics()`.

**Phase 3 — Statistical comparisons**
- For each K, aggregates knee-point metrics across seeds.
- Selects the best-performing seed (lowest mean distance) for VT1/VT3 tests.
- Runs `test_accessibility()` and `test_equity()`.
- Stores results in a structured dict.

Outputs:

```text
output/rq_analysis/metrics/rq_analysis_results.json
output/rq_analysis/metrics/comparison_summary.csv
output/rq_analysis/experiments/k{K}_seed{seed}/
    ├── final_archive.csv
    ├── initial_archive.csv
    └── run_metadata.json
```

CLI options:

```bash
python3 scripts/run_rq_experiments.py                     # full run (all K, all seeds)
python3 scripts/run_rq_experiments.py --k 3 --seeds 1     # quick test (K=3, 1 seed)
python3 scripts/run_rq_experiments.py --skip-ga           # re-analyze existing outputs
```

---

### `plot_rq_results.py`

Generates all thesis figures from the saved RQ analysis results.

Input:

```text
output/rq_analysis/metrics/rq_analysis_results.json
```

Output directory:

```text
output/rq_analysis/plots/
```

Figures produced:

| File | Description |
| --- | --- |
| `rq1_distance_comparison.png` | Mean and median distance: Greedy vs Optimized vs Random across K |
| `rq1_coverage_thresholds.png` | Coverage at 500 m, 1 km, 2 km: Greedy vs Optimized |
| `rq2_performance_scaling.png` | Line plots: mean distance, coverage, CV vs K (with ±σ error bars) |
| `rq2_marginal_gains.png` | Marginal improvement: K=3→6 and K=6→10 for greedy and optimized |
| `rq3_equity_comparison.png` | CV and variance: Greedy vs Optimized across K |
| `rq3_mahalle_distances.png` | Per-neighborhood mean distances for greedy baseline |
| `stat_test_summary.png` | Visual table of all statistical test results (VT1 + VT3) |

Run:

```bash
python3 scripts/plot_rq_results.py
python3 scripts/plot_rq_results.py --dpi 300    # high-res export
```

Requires `rq_analysis_results.json` to exist (run `run_rq_experiments.py` first).

---

### `export_thesis_tables.py`

Exports formatted comparison tables in both Markdown and LaTeX (booktabs) format.

Input:

```text
output/rq_analysis/metrics/rq_analysis_results.json
```

Output directory:

```text
output/rq_analysis/tables/
```

Tables produced:

| File (md + tex) | Description |
| --- | --- |
| `table1_summary` | Main K × Strategy performance comparison (mean ± std across seeds) |
| `table2_statistical_tests` | VT1 (Wilcoxon + t-test) and VT3 (Levene) test results per K |
| `table3_marginal_improvement` | Marginal improvement for K=3→6 and K=6→10 transitions |
| `table4_existing_reference` | Existing locker network contextual metrics |

Run:

```bash
python3 scripts/export_thesis_tables.py
```

---

## 4. Parameter Analysis Post-Processing Scripts

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

## 5. Important Notes

### Rerun Safety for Demand Scripts

Both `prepare_demand.py` and `calculate_poi_weights.py` select raw POI columns using:

```python
col.startswith("poi_") and col not in {"poi_score", "demand_final"}
```

This prevents reruns on an already enriched CSV from feeding `poi_score` back
into the EWM.

### CSV Column Alignment Contract

`evaluate_solution.py` sorts candidates by `id` ascending — the same order as
`CandidateRepository.finalizeRepository()` in Java. This alignment must be
preserved. The distance matrix was also generated in ascending ID order.

### Forbidden Candidates

`is_forbidden = 1` rows remain in both the CSV and distance matrix as demand
grid points. They are excluded from the selectable locker universe:

- In Java: via `CandidateRepository.getSelectableCandidateIds()`.
- In Python: via `data.candidates[data.candidates["is_forbidden"] == 0]`.

### Recommended Full RQ Workflow

```bash
# 1. Inspect POI weights (optional)
python3 scripts/calculate_poi_weights.py

# 2. Update demand (if candidate data changed)
python3 scripts/prepare_demand.py

# 3. Run all RQ experiments (Java GA + baselines + statistical tests)
python3 scripts/run_rq_experiments.py

# 4. Generate thesis figures
python3 scripts/plot_rq_results.py --dpi 300

# 5. Export LaTeX tables
python3 scripts/export_thesis_tables.py

# 6. Single-run archive visualization
python3 scripts/plot_archives.py
```
