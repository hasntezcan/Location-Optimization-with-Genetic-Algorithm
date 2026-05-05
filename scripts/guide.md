# Scripts Guide: Demand Preparation

This folder contains the Python scripts that prepare demand-related columns before
running the Java genetic algorithm.

## Data Flow

Input file:

```text
data/candidate_points.csv
```

Main output:

```text
data/candidate_points.csv
```

`prepare_demand.py` writes back to the same CSV file. Keep a backup before
rerunning it if you need to preserve the previous `poi_score` and `demand_final`
values.

## Scripts

### `prepare_demand.py`

Main demand preparation script.

What it does:

- Reads `data/candidate_points.csv`.
- Finds raw POI columns by the `poi_` prefix while excluding generated columns
  such as `poi_score` and `demand_final`.
- Calculates POI weights with the Entropy Weight Method.
- Prompts for the lambda parameter.
- Updates `poi_score`.
- Updates `demand_final`.
- Saves the result back to `data/candidate_points.csv`.

Run it from the project root:

```bash
python3 scripts/prepare_demand.py
```

### `calculate_poi_weights.py`

Read-only analysis script for checking the current POI weights.

What it does:

- Reads `data/candidate_points.csv`.
- Finds raw POI columns by the `poi_` prefix while excluding generated columns
  such as `poi_score` and `demand_final`.
- Prints the calculated Entropy Weight Method weights.
- Does not write to the CSV file.

Run it from the project root:

```bash
python3 scripts/calculate_poi_weights.py
```

## Calculation

The final demand value used by the Java optimization code is:

```text
demand_final = population_candidate * (1 + lambda * poi_score)
```

Lambda controls how strongly POI attractiveness affects demand:

- `0.0`: no POI influence; demand follows `population_candidate`.
- `0.5`: balanced POI influence.
- `1.0`: stronger priority for urban activity hubs.

## Important Notes

- Both scripts detect raw POI columns with `col.startswith("poi_")` and exclude
  generated columns (`poi_score`, `demand_final`) so rerunning on an enriched
  CSV does not feed `poi_score` back into the Entropy Weight Method.
- `prepare_demand.py` overwrites `data/candidate_points.csv`; use
  `data/candidate_points_backup.csv` or another backup when needed.
- The Java `CsvLoader` maps required fields by header name. The default
  scientific demand model expects `poi_score` and `demand_final`; if those
  columns are absent, Java falls back to population-only demand.
- `is_forbidden = 1` rows remain demand grid points, but the Java GA excludes
  them from the selectable locker-location universe.

## Recommended Workflow

1. Start from a clean `data/candidate_points.csv`.
2. Run `python3 scripts/calculate_poi_weights.py` to inspect POI weights.
3. Run `python3 scripts/prepare_demand.py`.
4. Enter the lambda value when prompted.
5. Confirm that `poi_score` and `demand_final` exist in the CSV.
6. Run the Java optimization pipeline.

## Archive Plot and Hypervolume Assessment

The project also includes a plotting workflow for comparing the **initial archive**
and the **final archive** after a SPEA2 run.

### What is plotted

The archive comparison plot shows four panels:

- Initial Archive - Raw Objective Space
- Final Archive - Raw Objective Space
- Initial → Final Improvement Metrics
- Final Archive - Hypervolume Space

In these plots:

- **Blue points** represent all archive individuals.
- **Red points** represent the **non-dominated** individuals.
- The dashed red line connects the non-dominated points.
- In hypervolume space, the **orange X** is the hypervolume reference point.

### Raw objective space

In raw objective space, the solutions are plotted using their original objective
values:

- `f1`
- `f2`

This view is used to inspect the actual Pareto trade-off structure of the
archive.

### Hypervolume space

In hypervolume space, the same archive is plotted after normalization.

The purpose of this space is to compute and visualize the **2D hypervolume**
indicator.

### How normalization is done

The current official assessment separates two concepts:

- Initial-to-final improvement is measured with raw-objective non-dominated
  metrics and the C-metric.
- Hypervolume is visualized and computed for the final archive only.

For HV-space export and plotting, Java computes ideal/nadir bounds from the
final archive non-dominated set and normalizes archive rows with those bounds:

```text
norm_f1 = (f1 - ideal_f1) / (nadir_f1 - ideal_f1)
norm_f2 = (f2 - ideal_f2) / (nadir_f2 - ideal_f2)
```

Values are clamped to `[0, 1]`.

### How to run the plot

Run from the project root:

```bash
python3 scripts/plot_archives.py
```

The script writes the latest comparison image to:

```text
output/archive_comparison_latest.png
```
