"""Statistical analysis for SPEA2 GA parameter experiments.

Default usage for the full experiment:
    python scripts/statistical_analysis.py

Smoke usage:
    python scripts/statistical_analysis.py --input output/parameter_analysis_results_smoke.csv --output-dir output/statistics_smoke
"""

from __future__ import annotations

import argparse
import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


REQUIRED_COLUMNS = {
    "Run_ID",
    "K",
    "Task",
    "GA_ID",
    "PopulationSize",
    "ArchiveSize",
    "MaxGenerations",
    "TargetFE",
    "FunctionEvals",
    "MutationRate",
    "CrossoverRate",
    "Seed",
    "Runtime_ms",
    "Final_HV",
    "Final_HV_Ratio",
    "ND_Count",
    "Final_ND_Archive_Ratio",
    "Spacing_CV",
    "Best_f1",
    "Best_f2",
    "Mean_f1",
    "Mean_f2",
}

DESCRIPTIVE_COLUMNS = [
    "K",
    "Task",
    "GA_ID",
    "PopulationSize",
    "ArchiveSize",
    "MutationRate",
    "CrossoverRate",
    "n_runs",
    "Final_HV_Ratio_mean",
    "Final_HV_Ratio_median",
    "Final_HV_Ratio_std",
    "Final_HV_Ratio_IQR",
    "Mean_Rank",
    "Runtime_ms_mean",
    "ND_Count_mean",
    "Final_ND_Archive_Ratio_mean",
    "Spacing_CV_mean",
    "Best_f1_mean",
    "Best_f2_mean",
]

FRIEDMAN_COLUMNS = [
    "K",
    "Task",
    "n_blocks",
    "n_configurations",
    "statistic",
    "p_value",
    "significant_0_05",
    "status",
    "null_hypothesis",
]

POSTHOC_COLUMNS = [
    "K",
    "Task",
    "GA_ID_A",
    "GA_ID_B",
    "median_A",
    "median_B",
    "mean_A",
    "mean_B",
    "raw_p",
    "adjusted_p",
    "significant_0_05",
    "higher_median_GA_ID",
]

SELECTED_COLUMNS = [
    "K",
    "Task",
    "Selected_GA_ID",
    "PopulationSize",
    "ArchiveSize",
    "MutationRate",
    "CrossoverRate",
    "Median_Final_HV_Ratio",
    "Mean_Final_HV_Ratio",
    "Std_Final_HV_Ratio",
    "Mean_Rank",
    "Friedman_p",
    "Friedman_Significant",
    "Selection_Group_Size",
    "Selection_Basis",
]


def ga_sort_key(ga_id: str) -> int:
    text = str(ga_id).strip().upper()
    if text.startswith("GA"):
        try:
            return int(text[2:])
        except ValueError:
            pass
    return 10_000


def load_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    df = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    numeric_columns = [
        "Run_ID",
        "K",
        "PopulationSize",
        "ArchiveSize",
        "MaxGenerations",
        "TargetFE",
        "FunctionEvals",
        "MutationRate",
        "CrossoverRate",
        "Seed",
        "Runtime_ms",
        "Final_HV",
        "Final_HV_Ratio",
        "ND_Count",
        "Final_ND_Archive_Ratio",
        "Spacing_CV",
        "Best_f1",
        "Best_f2",
        "Mean_f1",
        "Mean_f2",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.sort_values(["K", "GA_ID", "Seed"], key=sort_series)
    return df


def sort_series(series: pd.Series) -> pd.Series:
    if series.name == "GA_ID":
        return series.map(ga_sort_key)
    return series


def build_matrix(k_df: pd.DataFrame) -> pd.DataFrame:
    matrix = k_df.pivot_table(
        index="Seed",
        columns="GA_ID",
        values="Final_HV_Ratio",
        aggfunc="mean",
    )
    columns = sorted(matrix.columns, key=ga_sort_key)
    return matrix.loc[:, columns].sort_index()


def compute_descriptive(df: pd.DataFrame) -> pd.DataFrame:
    rank_frames: list[pd.DataFrame] = []

    for k, k_df in df.groupby("K", sort=True):
        matrix = build_matrix(k_df)
        ranks = matrix.rank(axis=1, ascending=False, method="average")
        mean_ranks = ranks.mean(axis=0, skipna=True).rename("Mean_Rank")
        rank_part = mean_ranks.reset_index()
        rank_part["K"] = k
        rank_frames.append(rank_part)

    rank_df = pd.concat(rank_frames, ignore_index=True) if rank_frames else pd.DataFrame()

    rows: list[dict] = []
    grouped = df.groupby(["K", "Task", "GA_ID"], sort=False)
    for (k, task, ga_id), group in grouped:
        hv = group["Final_HV_Ratio"].dropna()
        row = {
            "K": k,
            "Task": task,
            "GA_ID": ga_id,
            "PopulationSize": int(group["PopulationSize"].iloc[0]),
            "ArchiveSize": int(group["ArchiveSize"].iloc[0]),
            "MutationRate": group["MutationRate"].iloc[0],
            "CrossoverRate": group["CrossoverRate"].iloc[0],
            "n_runs": int(len(group)),
            "Final_HV_Ratio_mean": hv.mean(),
            "Final_HV_Ratio_median": hv.median(),
            "Final_HV_Ratio_std": hv.std(ddof=1) if len(hv) > 1 else 0.0,
            "Final_HV_Ratio_IQR": hv.quantile(0.75) - hv.quantile(0.25) if len(hv) else np.nan,
            "Runtime_ms_mean": group["Runtime_ms"].mean(),
            "ND_Count_mean": group["ND_Count"].mean(),
            "Final_ND_Archive_Ratio_mean": group["Final_ND_Archive_Ratio"].mean(),
            "Spacing_CV_mean": group["Spacing_CV"].mean(),
            "Best_f1_mean": group["Best_f1"].mean(),
            "Best_f2_mean": group["Best_f2"].mean(),
        }
        rows.append(row)

    descriptive = pd.DataFrame(rows)
    if not rank_df.empty:
        descriptive = descriptive.merge(rank_df, on=["K", "GA_ID"], how="left")
    else:
        descriptive["Mean_Rank"] = np.nan

    descriptive["GA_Number"] = descriptive["GA_ID"].map(ga_sort_key)
    descriptive = descriptive.sort_values(["K", "GA_Number"]).drop(columns=["GA_Number"])
    return descriptive.loc[:, DESCRIPTIVE_COLUMNS]


def compute_friedman(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    null_hypothesis = "No statistically significant performance difference among GA configurations."

    for k, k_df in df.groupby("K", sort=True):
        task = str(k_df["Task"].iloc[0])
        complete_matrix = build_matrix(k_df).dropna(axis=0, how="any")
        n_blocks, n_configurations = complete_matrix.shape

        if n_configurations < 3:
            rows.append({
                "K": k,
                "Task": task,
                "n_blocks": n_blocks,
                "n_configurations": n_configurations,
                "statistic": np.nan,
                "p_value": np.nan,
                "significant_0_05": False,
                "status": "insufficient_configurations",
                "null_hypothesis": null_hypothesis,
            })
            continue

        if n_blocks < 2:
            rows.append({
                "K": k,
                "Task": task,
                "n_blocks": n_blocks,
                "n_configurations": n_configurations,
                "statistic": np.nan,
                "p_value": np.nan,
                "significant_0_05": False,
                "status": "insufficient_blocks",
                "null_hypothesis": null_hypothesis,
            })
            continue

        samples = [complete_matrix[column].to_numpy() for column in complete_matrix.columns]
        statistic, p_value = stats.friedmanchisquare(*samples)
        rows.append({
            "K": k,
            "Task": task,
            "n_blocks": n_blocks,
            "n_configurations": n_configurations,
            "statistic": statistic,
            "p_value": p_value,
            "significant_0_05": bool(p_value < 0.05),
            "status": "ok",
            "null_hypothesis": null_hypothesis,
        })

    return pd.DataFrame(rows, columns=FRIEDMAN_COLUMNS)


def compute_posthoc(df: pd.DataFrame, friedman: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    significant_k = set(
        friedman.loc[friedman["significant_0_05"] == True, "K"].tolist()  # noqa: E712
    )

    for k, k_df in df.groupby("K", sort=True):
        if k not in significant_k:
            continue

        task = str(k_df["Task"].iloc[0])
        complete_matrix = build_matrix(k_df).dropna(axis=0, how="any")
        ga_ids = list(complete_matrix.columns)
        comparisons = list(itertools.combinations(ga_ids, 2))
        comparison_count = len(comparisons)

        for ga_a, ga_b in comparisons:
            values_a = complete_matrix[ga_a].to_numpy()
            values_b = complete_matrix[ga_b].to_numpy()
            raw_p = wilcoxon_p_value(values_a, values_b)
            adjusted_p = min(raw_p * comparison_count, 1.0) if not math.isnan(raw_p) else np.nan
            median_a = float(np.median(values_a))
            median_b = float(np.median(values_b))

            if median_a > median_b:
                higher_median = ga_a
            elif median_b > median_a:
                higher_median = ga_b
            else:
                higher_median = "tie"

            rows.append({
                "K": k,
                "Task": task,
                "GA_ID_A": ga_a,
                "GA_ID_B": ga_b,
                "median_A": median_a,
                "median_B": median_b,
                "mean_A": float(np.mean(values_a)),
                "mean_B": float(np.mean(values_b)),
                "raw_p": raw_p,
                "adjusted_p": adjusted_p,
                "significant_0_05": bool(adjusted_p < 0.05) if not math.isnan(adjusted_p) else False,
                "higher_median_GA_ID": higher_median,
            })

    return pd.DataFrame(rows, columns=POSTHOC_COLUMNS)


def wilcoxon_p_value(values_a: np.ndarray, values_b: np.ndarray) -> float:
    differences = values_a - values_b
    if np.allclose(differences, 0.0, equal_nan=False):
        return 1.0

    try:
        _, p_value = stats.wilcoxon(values_a, values_b, alternative="two-sided")
        return float(p_value)
    except ValueError:
        return np.nan


def select_configurations(
    descriptive: pd.DataFrame,
    friedman: pd.DataFrame,
    posthoc: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []

    for k, k_desc in descriptive.groupby("K", sort=True):
        k_desc = k_desc.copy()
        k_desc["GA_Number"] = k_desc["GA_ID"].map(ga_sort_key)
        k_desc = k_desc.sort_values(
            [
                "Final_HV_Ratio_median",
                "Final_HV_Ratio_mean",
                "Final_HV_Ratio_std",
                "Final_ND_Archive_Ratio_mean",
                "Runtime_ms_mean",
                "PopulationSize",
                "GA_Number",
            ],
            ascending=[False, False, True, False, True, True, True],
            na_position="last",
        )

        best_by_hv = str(k_desc.iloc[0]["GA_ID"])
        k_friedman = friedman.loc[friedman["K"] == k]
        friedman_p = float(k_friedman["p_value"].iloc[0]) if not k_friedman.empty else np.nan
        friedman_significant = bool(k_friedman["significant_0_05"].iloc[0]) if not k_friedman.empty else False

        if friedman_significant:
            top_group = bonferroni_top_group(best_by_hv, k_desc, posthoc.loc[posthoc["K"] == k])
            if len(top_group) == 1:
                basis = "Friedman significant; selected configuration is separated by Bonferroni tests where available."
            else:
                basis = "Friedman significant; selected from Bonferroni top group by HV median, variance, archive ratio, runtime, and size."
        else:
            top_group = set(k_desc["GA_ID"].tolist())
            basis = "Friedman not significant or unavailable; selected by HV median/mean and tie-breakers."

        selection_pool = k_desc.loc[k_desc["GA_ID"].isin(top_group)].sort_values(
            [
                "Final_HV_Ratio_median",
                "Final_HV_Ratio_mean",
                "Final_HV_Ratio_std",
                "Final_ND_Archive_Ratio_mean",
                "Runtime_ms_mean",
                "PopulationSize",
                "GA_Number",
            ],
            ascending=[False, False, True, False, True, True, True],
            na_position="last",
        )
        selected = selection_pool.iloc[0]

        rows.append({
            "K": int(selected["K"]),
            "Task": selected["Task"],
            "Selected_GA_ID": selected["GA_ID"],
            "PopulationSize": int(selected["PopulationSize"]),
            "ArchiveSize": int(selected["ArchiveSize"]),
            "MutationRate": selected["MutationRate"],
            "CrossoverRate": selected["CrossoverRate"],
            "Median_Final_HV_Ratio": selected["Final_HV_Ratio_median"],
            "Mean_Final_HV_Ratio": selected["Final_HV_Ratio_mean"],
            "Std_Final_HV_Ratio": selected["Final_HV_Ratio_std"],
            "Mean_Rank": selected["Mean_Rank"],
            "Friedman_p": friedman_p,
            "Friedman_Significant": friedman_significant,
            "Selection_Group_Size": int(len(top_group)),
            "Selection_Basis": basis,
        })

    return pd.DataFrame(rows, columns=SELECTED_COLUMNS)


def bonferroni_top_group(best_ga: str, k_desc: pd.DataFrame, k_posthoc: pd.DataFrame) -> set[str]:
    top_group = {best_ga}

    for other_ga in k_desc["GA_ID"].tolist():
        if other_ga == best_ga:
            continue

        pair = k_posthoc.loc[
            ((k_posthoc["GA_ID_A"] == best_ga) & (k_posthoc["GA_ID_B"] == other_ga))
            | ((k_posthoc["GA_ID_A"] == other_ga) & (k_posthoc["GA_ID_B"] == best_ga))
        ]

        if pair.empty:
            top_group.add(other_ga)
            continue

        row = pair.iloc[0]
        if not bool(row["significant_0_05"]):
            top_group.add(other_ga)

    return top_group


def write_outputs(
    output_dir: Path,
    descriptive: pd.DataFrame,
    friedman: pd.DataFrame,
    posthoc: pd.DataFrame,
    selected: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptive.to_csv(output_dir / "descriptive_by_k.csv", index=False)
    friedman.to_csv(output_dir / "friedman_summary.csv", index=False)
    posthoc.to_csv(output_dir / "posthoc_bonferroni.csv", index=False)
    selected.to_csv(output_dir / "selected_configurations.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze SPEA2 parameter experiment results.")
    parser.add_argument(
        "--input",
        default="output/parameter_analysis_results.csv",
        help="Input parameter analysis CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/statistics",
        help="Directory for generated statistics CSV files.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    df = load_results(input_path)
    descriptive = compute_descriptive(df)
    friedman = compute_friedman(df)
    posthoc = compute_posthoc(df, friedman)
    selected = select_configurations(descriptive, friedman, posthoc)
    write_outputs(output_dir, descriptive, friedman, posthoc, selected)

    print(f"Read {len(df)} rows from {input_path}")
    print(f"Wrote statistics outputs to {output_dir}")


if __name__ == "__main__":
    main()
