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
- Finds POI columns by the `poi_` prefix.
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
- Finds POI columns by the `poi_` prefix.
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

- Both scripts detect POI columns with `col.startswith("poi_")`.
- If `candidate_points.csv` already contains a generated `poi_score` column, it
  also matches the `poi_` prefix. Use a clean CSV or remove generated columns
  before recalculating if you only want raw POI categories in the weighting step.
- `prepare_demand.py` overwrites `data/candidate_points.csv`; use
  `data/candidate_points_backup.csv` or another backup when needed.
- The Java `CsvLoader` currently maps CSV fields by fixed column positions. Do
  not reorder the CSV columns unless you also update the loader mapping.

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
- Initial Archive - Hypervolume Space
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

The initial archive and the final archive are compared in the **same normalized
objective space**.

This is done by first building a common assessment bound set:

- `min_f1`
- `max_f1`
- `min_f2`
- `max_f2`

Then both archives are normalized using the same min-max transformation:

```text
norm_f1 = (f1 - min_f1) / (max_f1 - min_f1)
norm_f2 = (f2 - min_f2) / (max_f2 - min_f2)


### How to run the plot

Run from the project root:

```bash
python3 scripts/plot_archives.py
```

The script writes the latest comparison image to:

```text
output/archive_comparison_latest.png
```
