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
