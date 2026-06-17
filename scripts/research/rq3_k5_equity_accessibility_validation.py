#!/usr/bin/env python3
"""
RQ3 K=5 Equity + Accessibility Validation

Purpose
-------
Generate representative K=5 archive-level baseline evidence for RQ3 by comparing
selected SPEA2 results against 20 random K=5 placements.

This script intentionally does NOT run Java, Maven, SPEA2, app.Main, or
ParameterAnalyzer. It only reads existing CSV/NPY files and computes the random
baseline objectives directly in Python.

Expected input files, relative to project root:
- data/candidate_points.csv
- data/kadikoy_distance_meters_nxn.npy
- output/parameter_analysis/parameter_analysis_results.csv

Outputs:
- output/rq3_k5_equity_accessibility_comparison.csv
- output/rq3_k5_equity_accessibility_summary.csv
- sections/figures/final_results/rq3_k5_equity_accessibility_validation.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError as exc:  # pragma: no cover
    raise SystemExit("matplotlib is required to create the output figure. Install it and rerun.") from exc

try:
    from scipy.stats import mannwhitneyu
except ImportError:  # pragma: no cover
    mannwhitneyu = None


K_VALUE = 5
SELECTED_GA_ID = "GA18"
N_SEEDS = 20
RANDOM_SEEDS = list(range(1, N_SEEDS + 1))
BETA = 2.0

REQUIRED_K_VALUES = {1, 5, 10, 15}
EXPECTED_PARAMETER_ROWS = 1440


class ValidationError(RuntimeError):
    """Raised when an input file does not match the expected project contract."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate RQ3 K=5 random-baseline validation outputs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Project root. Defaults to the parent of the scripts directory when "
            "the script is run from scripts/, otherwise the current working directory."
        ),
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=BETA,
        help="Distance-cost exponent. Default: 2.0."
    )
    return parser.parse_args()


def resolve_project_root(cli_root: Path | None) -> Path:
    if cli_root is not None:
        return cli_root.resolve()

    script_path = Path(__file__).resolve()
    if script_path.parent.name == "scripts":
        return script_path.parents[1]
    return Path.cwd().resolve()


def require_file(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"Required file is missing: {path}")
    if not path.is_file():
        raise ValidationError(f"Expected a file, but found something else: {path}")


def require_columns(df: pd.DataFrame, required: Iterable[str], file_label: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValidationError(
            f"{file_label} is missing required column(s): {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def load_candidate_data(candidate_path: Path) -> pd.DataFrame:
    require_file(candidate_path)
    df = pd.read_csv(candidate_path)
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    required = ["id", "Mahalle_Name_Turkish", "is_forbidden", "demand_final"]
    require_columns(df, required, "candidate_points.csv")

    df = df.copy()
    df["id"] = pd.to_numeric(df["id"], errors="raise").astype(int)
    df["is_forbidden"] = pd.to_numeric(df["is_forbidden"], errors="raise").astype(int)
    df["demand_final"] = pd.to_numeric(df["demand_final"], errors="raise")

    if df["id"].duplicated().any():
        duplicates = df.loc[df["id"].duplicated(), "id"].tolist()
        raise ValidationError(f"candidate_points.csv contains duplicate id values: {duplicates[:10]}")

    if (df["demand_final"] < 0).any():
        raise ValidationError("candidate_points.csv contains negative demand_final values.")

    if df["demand_final"].sum() <= 0:
        raise ValidationError("Total demand_final must be positive.")

    if df["Mahalle_Name_Turkish"].isna().any() or (df["Mahalle_Name_Turkish"].astype(str).str.strip() == "").any():
        raise ValidationError("Mahalle_Name_Turkish contains missing or blank values.")

    # Java CandidateRepository synchronizes the distance matrix by sorting candidates by ID.
    df = df.sort_values("id", ascending=True).reset_index(drop=True)
    return df


def load_distance_matrix(matrix_path: Path, expected_size: int) -> np.ndarray:
    require_file(matrix_path)
    matrix = np.load(matrix_path)

    if matrix.ndim != 2:
        raise ValidationError(f"Distance matrix must be 2D, got shape {matrix.shape}.")
    if matrix.shape[0] != matrix.shape[1]:
        raise ValidationError(f"Distance matrix must be square, got shape {matrix.shape}.")
    if matrix.shape != (expected_size, expected_size):
        raise ValidationError(
            f"Distance matrix shape {matrix.shape} does not match candidate count {expected_size}."
        )
    if not np.isfinite(matrix).all():
        raise ValidationError("Distance matrix contains non-finite values.")
    if (matrix < 0).any():
        raise ValidationError("Distance matrix contains negative distances.")

    return matrix.astype(float, copy=False)


def load_and_validate_parameter_results(parameter_path: Path) -> pd.DataFrame:
    require_file(parameter_path)
    df = pd.read_csv(parameter_path)
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    required = ["K", "GA_ID", "Seed", "Best_f1", "Best_f2"]
    require_columns(df, required, "parameter_analysis_results.csv")

    if len(df) != EXPECTED_PARAMETER_ROWS:
        raise ValidationError(
            f"parameter_analysis_results.csv row count must be {EXPECTED_PARAMETER_ROWS}; found {len(df)}. "
            "This may be an old/refactored analysis file. Do not use it for RQ3."
        )

    df = df.copy()
    df["K"] = pd.to_numeric(df["K"], errors="raise").astype(int)
    df["Seed"] = pd.to_numeric(df["Seed"], errors="raise").astype(int)
    df["Best_f1"] = pd.to_numeric(df["Best_f1"], errors="raise")
    df["Best_f2"] = pd.to_numeric(df["Best_f2"], errors="raise")
    df["GA_ID"] = df["GA_ID"].astype(str).str.strip()

    actual_k_values = set(df["K"].dropna().unique().tolist())
    if actual_k_values != REQUIRED_K_VALUES:
        raise ValidationError(
            f"K values must be {sorted(REQUIRED_K_VALUES)}; found {sorted(actual_k_values)}."
        )

    spea2 = df[(df["K"] == K_VALUE) & (df["GA_ID"] == SELECTED_GA_ID)].copy()
    if len(spea2) != N_SEEDS:
        raise ValidationError(
            f"K={K_VALUE}, GA_ID={SELECTED_GA_ID} must return {N_SEEDS} rows; found {len(spea2)}."
        )

    expected_seeds = set(RANDOM_SEEDS)
    actual_seeds = set(spea2["Seed"].tolist())
    if actual_seeds != expected_seeds:
        raise ValidationError(
            f"K={K_VALUE}, GA_ID={SELECTED_GA_ID} seeds must be {sorted(expected_seeds)}; "
            f"found {sorted(actual_seeds)}."
        )

    if not np.isfinite(spea2[["Best_f1", "Best_f2"]].to_numpy()).all():
        raise ValidationError("SPEA2 Best_f1/Best_f2 contains non-finite values.")

    return spea2.sort_values("Seed", ascending=True).reset_index(drop=True)


def evaluate_objectives(
    locker_ids: np.ndarray,
    candidate_df_sorted: pd.DataFrame,
    distance_matrix: np.ndarray,
    id_to_index: dict[int, int],
    beta: float,
) -> tuple[float, float]:
    """Compute f1 and f2 using the same raw objective definitions as Java FitnessCalculator."""
    try:
        locker_indices = np.array([id_to_index[int(locker_id)] for locker_id in locker_ids], dtype=int)
    except KeyError as exc:
        raise ValidationError(f"Locker candidate ID not found in id_to_index map: {exc}") from exc

    nearest_distance_m = distance_matrix[:, locker_indices].min(axis=1)
    distance_cost = np.power(nearest_distance_m / 1000.0, beta)

    demand = candidate_df_sorted["demand_final"].to_numpy(dtype=float)
    total_demand = float(demand.sum())

    f1 = float(np.sum(demand * distance_cost) / total_demand)

    mahalle = candidate_df_sorted["Mahalle_Name_Turkish"].astype(str).to_numpy()
    tmp = pd.DataFrame({"mahalle": mahalle, "demand": demand, "cost": distance_cost})
    tmp["weighted_cost"] = tmp["demand"] * tmp["cost"]
    grouped = tmp.groupby("mahalle", sort=True, observed=False).agg(
        weighted_cost_sum=("weighted_cost", "sum"),
        demand_sum=("demand", "sum"),
    )
    if (grouped["demand_sum"] <= 0).any():
        bad = grouped.index[grouped["demand_sum"] <= 0].tolist()
        raise ValidationError(f"Demand sum must be positive for every mahalle. Bad mahalle values: {bad[:10]}")

    mahalle_mean_costs = (grouped["weighted_cost_sum"] / grouped["demand_sum"]).to_numpy(dtype=float)
    mean_of_mahalle_means = float(np.mean(mahalle_mean_costs))
    if mean_of_mahalle_means <= 0:
        f2 = 0.0
    else:
        # Java uses population variance/std: average squared deviation, not sample ddof=1.
        f2 = float(np.std(mahalle_mean_costs, ddof=0) / mean_of_mahalle_means)

    return f1, f2


def generate_random_baseline(
    candidate_df_sorted: pd.DataFrame,
    distance_matrix: np.ndarray,
    beta: float,
) -> pd.DataFrame:
    selectable_ids = candidate_df_sorted.loc[candidate_df_sorted["is_forbidden"] == 0, "id"].to_numpy(dtype=int)
    if len(selectable_ids) < K_VALUE:
        raise ValidationError(
            f"Need at least {K_VALUE} selectable candidates where is_forbidden == 0; found {len(selectable_ids)}."
        )

    id_to_index = {int(candidate_id): idx for idx, candidate_id in enumerate(candidate_df_sorted["id"].tolist())}

    rows: list[dict[str, float | int | str]] = []
    for seed in RANDOM_SEEDS:
        rng = np.random.default_rng(seed)
        selected_ids = np.sort(rng.choice(selectable_ids, size=K_VALUE, replace=False))
        random_f1, random_f2 = evaluate_objectives(
            selected_ids,
            candidate_df_sorted,
            distance_matrix,
            id_to_index,
            beta,
        )
        rows.append({
            "seed": seed,
            "random_locker_ids": "|".join(str(int(x)) for x in selected_ids),
            "random_f1": random_f1,
            "random_f2": random_f2,
        })

    return pd.DataFrame(rows)


def one_sided_mann_whitney_less(spea2_values: np.ndarray, random_values: np.ndarray) -> float:
    if mannwhitneyu is None:
        raise ValidationError(
            "scipy is required for the Mann–Whitney U test. Install scipy and rerun: pip install scipy"
        )
    result = mannwhitneyu(spea2_values, random_values, alternative="less", method="auto")
    return float(result.pvalue)


def percent_reduction(random_mean: float, spea2_mean: float) -> float:
    if random_mean == 0:
        return float("nan")
    return (random_mean - spea2_mean) / random_mean * 100.0


def create_comparison_and_summary(
    random_df: pd.DataFrame,
    spea2_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int | str]]:
    spea2_small = spea2_df[["Seed", "Best_f1", "Best_f2"]].rename(columns={
        "Seed": "seed",
        "Best_f1": "spea2_best_f1",
        "Best_f2": "spea2_best_f2",
    })

    comparison = random_df.merge(spea2_small, on="seed", how="inner").sort_values("seed")
    if len(comparison) != N_SEEDS:
        raise ValidationError(f"Comparison merge must produce {N_SEEDS} rows; found {len(comparison)}.")

    comparison["f1_improvement"] = (
        (comparison["random_f1"] - comparison["spea2_best_f1"]) / comparison["random_f1"] * 100.0
    )
    comparison["f2_improvement"] = (
        (comparison["random_f2"] - comparison["spea2_best_f2"]) / comparison["random_f2"] * 100.0
    )

    random_mean_f1 = float(comparison["random_f1"].mean())
    spea2_mean_f1 = float(comparison["spea2_best_f1"].mean())
    random_mean_f2 = float(comparison["random_f2"].mean())
    spea2_mean_f2 = float(comparison["spea2_best_f2"].mean())

    f1_reduction = percent_reduction(random_mean_f1, spea2_mean_f1)
    f2_reduction = percent_reduction(random_mean_f2, spea2_mean_f2)

    f1_p = one_sided_mann_whitney_less(
        comparison["spea2_best_f1"].to_numpy(dtype=float),
        comparison["random_f1"].to_numpy(dtype=float),
    )
    f2_p = one_sided_mann_whitney_less(
        comparison["spea2_best_f2"].to_numpy(dtype=float),
        comparison["random_f2"].to_numpy(dtype=float),
    )

    f1_lower_count = int((comparison["spea2_best_f1"] < comparison["random_f1"]).sum())
    f2_lower_count = int((comparison["spea2_best_f2"] < comparison["random_f2"]).sum())

    supported = (spea2_mean_f2 < random_mean_f2) and (spea2_mean_f1 < random_mean_f1)
    interpretation = (
        "Supported for the representative K=5 archive-level baseline validation: "
        "SPEA2 reduces the neighborhood equity objective f2 while also keeping f1 lower than the random baseline."
        if supported else
        "Not fully supported for the representative K=5 archive-level baseline validation: "
        "the summary does not show simultaneous archive-level improvement in both f2 and f1 versus random."
    )

    metrics = {
        "random_mean_f1": random_mean_f1,
        "spea2_mean_f1": spea2_mean_f1,
        "f1_reduction_percent": f1_reduction,
        "f1_p_value": f1_p,
        "f1_spea2_lower_count": f1_lower_count,
        "random_mean_f2": random_mean_f2,
        "spea2_mean_f2": spea2_mean_f2,
        "f2_reduction_percent": f2_reduction,
        "f2_p_value": f2_p,
        "f2_spea2_lower_count": f2_lower_count,
        "n": N_SEEDS,
        "interpretation": interpretation,
    }

    summary = pd.DataFrame([metrics])
    return comparison, summary, metrics


def format_p_value(p_value: float) -> str:
    if p_value < 0.001:
        return "p < 0.001"
    return f"p = {p_value:.3f}"


def plot_dumbbell_panel(
    ax: plt.Axes,
    comparison: pd.DataFrame,
    random_col: str,
    spea2_col: str,
    title: str,
    reduction_percent: float,
    p_value: float,
) -> None:
    y = comparison["seed"].to_numpy(dtype=int)
    random_values = comparison[random_col].to_numpy(dtype=float)
    spea2_values = comparison[spea2_col].to_numpy(dtype=float)

    for yi, rand_val, spea2_val in zip(y, random_values, spea2_values):
        ax.plot([rand_val, spea2_val], [yi, yi], linewidth=1.2, alpha=0.55)

    ax.scatter(random_values, y, label="Random baseline", s=28, alpha=0.85)
    ax.scatter(spea2_values, y, label="SPEA2 best", s=28, alpha=0.95)

    random_mean = float(np.mean(random_values))
    spea2_mean = float(np.mean(spea2_values))
    ax.axvline(random_mean, linestyle="--", linewidth=1.2, alpha=0.75)
    ax.axvline(spea2_mean, linestyle="-", linewidth=1.2, alpha=0.75)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Objective value (lower is better)")
    ax.set_ylabel("Seed")
    ax.set_yticks(y)
    ax.grid(True, axis="x", alpha=0.25)
    ax.text(
        0.02,
        0.97,
        f"Mean reduction: {reduction_percent:.2f}%\n{format_p_value(p_value)}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )


def create_figure(comparison: pd.DataFrame, metrics: dict[str, float | int | str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=False)

    plot_dumbbell_panel(
        axes[0],
        comparison,
        random_col="random_f2",
        spea2_col="spea2_best_f2",
        title="Equity objective f₂",
        reduction_percent=float(metrics["f2_reduction_percent"]),
        p_value=float(metrics["f2_p_value"]),
    )
    plot_dumbbell_panel(
        axes[1],
        comparison,
        random_col="random_f1",
        spea2_col="spea2_best_f1",
        title="Accessibility guardrail f₁",
        reduction_percent=float(metrics["f1_reduction_percent"]),
        p_value=float(metrics["f1_p_value"]),
    )

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.94))

    fig.suptitle(
        "RQ3 Validation: Equity Improvement While Preserving Accessibility",
        fontsize=16,
        fontweight="bold",
        y=0.985,
    )
    fig.text(
        0.5,
        0.02,
        "Representative K=5 archive-level baseline validation. Lower f₁ and f₂ are better. "
        "This is not an all-K baseline claim.",
        ha="center",
        va="bottom",
        fontsize=10,
    )
    fig.tight_layout(rect=[0.03, 0.06, 0.97, 0.90])
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def print_terminal_summary(metrics: dict[str, float | int | str]) -> None:
    print("\nRQ3 K=5 Validation Complete")
    print(f"Random mean f2 : {float(metrics['random_mean_f2']):.6f}")
    print(f"SPEA2 mean f2  : {float(metrics['spea2_mean_f2']):.6f}")
    print(f"f2 reduction   : {float(metrics['f2_reduction_percent']):.2f}%")
    print(f"f2 p-value     : {float(metrics['f2_p_value']):.6g}")
    print(f"Random mean f1 : {float(metrics['random_mean_f1']):.6f}")
    print(f"SPEA2 mean f1  : {float(metrics['spea2_mean_f1']):.6f}")
    print(f"f1 reduction   : {float(metrics['f1_reduction_percent']):.2f}%")
    print(f"f1 p-value     : {float(metrics['f1_p_value']):.6g}")
    print(f"SPEA2 lower f2 : {int(metrics['f2_spea2_lower_count'])}/{int(metrics['n'])}")
    print(f"SPEA2 lower f1 : {int(metrics['f1_spea2_lower_count'])}/{int(metrics['n'])}")
    print(f"RQ3 support    : {metrics['interpretation']}")


def main() -> int:
    args = parse_args()
    root = resolve_project_root(args.root)

    candidate_path = root / "data" / "candidate_points.csv"
    matrix_path = root / "data" / "kadikoy_distance_meters_nxn.npy"
    parameter_path = root / "output" / "parameter_analysis" / "parameter_analysis_results.csv"

    comparison_output = root / "output" / "rq3_k5_equity_accessibility_comparison.csv"
    summary_output = root / "output" / "rq3_k5_equity_accessibility_summary.csv"
    figure_output = root / "sections" / "figures" / "final_results" / "rq3_k5_equity_accessibility_validation.png"

    try:
        if args.beta <= 0:
            raise ValidationError("Beta must be positive.")

        candidate_df_sorted = load_candidate_data(candidate_path)
        distance_matrix = load_distance_matrix(matrix_path, expected_size=len(candidate_df_sorted))
        spea2_df = load_and_validate_parameter_results(parameter_path)

        random_df = generate_random_baseline(candidate_df_sorted, distance_matrix, beta=float(args.beta))
        comparison, summary, metrics = create_comparison_and_summary(random_df, spea2_df)

        comparison_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.parent.mkdir(parents=True, exist_ok=True)

        comparison_columns = [
            "seed",
            "random_f1",
            "random_f2",
            "spea2_best_f1",
            "spea2_best_f2",
            "f1_improvement",
            "f2_improvement",
            "random_locker_ids",
        ]
        comparison[comparison_columns].to_csv(comparison_output, index=False)
        summary.to_csv(summary_output, index=False)
        create_figure(comparison, metrics, figure_output)

        print_terminal_summary(metrics)
        print("\nOutput files:")
        print(f"- {comparison_output}")
        print(f"- {summary_output}")
        print(f"- {figure_output}")
        return 0

    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
