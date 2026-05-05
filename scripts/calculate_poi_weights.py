"""Calculate entropy-based weights for POI columns in candidate point data."""

import numpy as np
import pandas as pd


DEFAULT_INPUT_CSV = "data/candidate_points.csv"
DEFAULT_POI_PREFIX = "poi_"
GENERATED_COLUMNS = {"poi_score", "demand_final"}


def calculate_poi_weights(csv_path, poi_prefix=DEFAULT_POI_PREFIX):
    """
    Calculate objective POI category weights using the Entropy Weight Method.

    The function reads the candidate points CSV, selects columns that start with
    ``poi_prefix``, applies a log transformation and min-max normalization, and
    returns entropy-based weights for each POI category.

    Args:
        csv_path: Path to the candidate points CSV file.
        poi_prefix: Prefix used to identify POI columns.

    Returns:
        A dictionary mapping each POI column name to its calculated weight.

    Raises:
        ValueError: If no POI columns are found with the given prefix.
    """
    df = pd.read_csv(csv_path)
    poi_cols = [
        col for col in df.columns
        if col.startswith(poi_prefix) and col not in GENERATED_COLUMNS
    ]

    if not poi_cols:
        raise ValueError(
            f"No columns found starting with prefix '{poi_prefix}'. Please check the data."
        )

    poi_data = df[poi_cols].fillna(0)
    n = len(poi_data)

    log_x = np.log1p(poi_data)
    min_vals = log_x.min()
    max_vals = log_x.max()
    ranges = max_vals - min_vals
    ranges[ranges == 0] = 1.0

    norm_x = (log_x - min_vals) / ranges

    col_sums = norm_x.sum()
    p = norm_x.divide(col_sums.replace(0, 1))
    ln_p = np.log(p.replace(0, 1))

    k = 1.0 / np.log(n)
    entropy = -k * (p * ln_p).sum()

    divergence = 1 - entropy
    divergence[col_sums == 0] = 0
    weights = divergence / divergence.sum()

    return weights.to_dict()


def main():
    """Calculate and print POI weights for the default candidate points CSV."""
    try:
        print("Calculating POI weights...\n")
        weights = calculate_poi_weights(DEFAULT_INPUT_CSV)
        sorted_weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)

        for poi, weight in sorted_weights:
            print(f"{poi:<20}: {weight:.4f} ({weight * 100:.2f}%)")

    except Exception as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
