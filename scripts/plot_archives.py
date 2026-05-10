from pathlib import Path
import json
import math
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ---------------------------------------------------------------------------
# Assessment methodology:
#   - Initial-to-final improvement is evaluated with ND-only raw-objective
#     improvement metrics and the dominance-based C-metric.
#   - Hypervolume is kept only as a final-archive/front quality visualization.
#   - The official HV-space normalization is based ONLY on the final archive
#     non-dominated set (ideal = min, nadir = max of final ND raw objectives).
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent)).resolve()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


OUTPUT_DIR = resolve_path(os.environ.get("GA_OUTPUT_DIR", "output"))
INITIAL_CSV = OUTPUT_DIR / "initial_archive.csv"
FINAL_CSV = OUTPUT_DIR / "final_archive.csv"
PLOT_PATH = OUTPUT_DIR / "archive_comparison_latest.png"

REFERENCE_F1 = 1.1
REFERENCE_F2 = 1.1

# Fallback defaults when run_metadata.json is missing
DEFAULT_POPULATION_SIZE = 100
DEFAULT_MAX_GENERATIONS = 200


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------

def load_run_metadata() -> dict:
    """Load run_metadata.json if present, otherwise return defaults."""
    meta_path = OUTPUT_DIR / "run_metadata.json"
    defaults = {
        "populationSize": DEFAULT_POPULATION_SIZE,
        "maxGenerations": DEFAULT_MAX_GENERATIONS,
    }
    try:
        if meta_path.exists():
            with open(meta_path, "r") as f:
                data = json.load(f)
            defaults.update(data)
    except (json.JSONDecodeError, OSError):
        pass  # fall back to defaults
    return defaults


def estimate_function_evaluations(metadata: dict) -> int:
    """Return the estimated number of function evaluations for the run.
    Uses pre-computed value from metadata if available, otherwise
    calculates population_size * (max_generations + 1)."""
    if "estimatedFunctionEvaluations" in metadata:
        return int(metadata["estimatedFunctionEvaluations"])
    pop = int(metadata.get("populationSize", DEFAULT_POPULATION_SIZE))
    gen = int(metadata.get("maxGenerations", DEFAULT_MAX_GENERATIONS))
    return pop * (gen + 1)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def load_archive(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = {
        "archive_index",
        "chromosome",
        "f1",
        "f2",
        "norm_f1",
        "norm_f2",
        "strength",
        "raw_fitness",
        "density",
        "total_fitness",
    }

    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {csv_path.name}: {sorted(missing)}")

    return df


def non_dominated_mask(df: pd.DataFrame, x_col: str, y_col: str) -> pd.Series:
    xs = df[x_col].to_numpy()
    ys = df[y_col].to_numpy()

    mask = []
    for i in range(len(df)):
        dominated = False
        for j in range(len(df)):
            if i == j:
                continue

            better_or_equal = xs[j] <= xs[i] and ys[j] <= ys[i]
            strictly_better = xs[j] < xs[i] or ys[j] < ys[i]

            if better_or_equal and strictly_better:
                dominated = True
                break

        mask.append(not dominated)

    return pd.Series(mask, index=df.index)


def prepare_front(df: pd.DataFrame, x_col: str, y_col: str) -> pd.DataFrame:
    nd = df[non_dominated_mask(df, x_col, y_col)].copy()
    nd = nd.sort_values(by=x_col, ascending=True).reset_index(drop=True)
    return nd


def compute_hypervolume_2d(front: pd.DataFrame, x_col: str, y_col: str,
                           ref_x: float, ref_y: float) -> float:
    hv = 0.0
    current_upper_y = ref_y

    for _, row in front.iterrows():
        x = row[x_col]
        y = row[y_col]

        if y < current_upper_y:
            width = ref_x - x
            height = current_upper_y - y
            if width > 0 and height > 0:
                hv += width * height
            current_upper_y = y

    return hv


# ---------------------------------------------------------------------------
# Plot: Raw objective space
# ---------------------------------------------------------------------------

def plot_raw_space(ax, df: pd.DataFrame, title: str):
    ax.scatter(df["f1"], df["f2"], alpha=0.75, s=35, label="Archive individuals")

    front = prepare_front(df, "f1", "f2")
    ax.scatter(front["f1"], front["f2"], color="red", s=50, label="Non-dominated")
    ax.plot(front["f1"], front["f2"], linestyle="--", linewidth=1)

    ax.set_title(title)
    ax.set_xlabel("f1")
    ax.set_ylabel("f2")
    ax.grid(True, alpha=0.3)
    ax.legend()

    return front


# ---------------------------------------------------------------------------
# Plot: HV space — axis scaling based on final ND points, not full archive.
#
# Because normalization bounds come from the final ND set only, some
# dominated archive individuals may fall outside [0, 1].  We set axis
# limits primarily from the ND front and reference point so that the
# HV-space plot stays visually tight and meaningful, rather than being
# stretched by a few extreme dominated outliers.
# ---------------------------------------------------------------------------

def plot_hv_space(ax, df: pd.DataFrame, title: str, ref_x: float, ref_y: float):
    ax.scatter(df["norm_f1"], df["norm_f2"], alpha=0.75, s=35, label="Archive individuals")

    front = prepare_front(df, "norm_f1", "norm_f2")
    ax.scatter(front["norm_f1"], front["norm_f2"], color="red", s=50, label="Non-dominated")
    ax.plot(front["norm_f1"], front["norm_f2"], linestyle="--", linewidth=1, color="red")

    # Reference point
    ax.scatter([ref_x], [ref_y], marker="x", s=90, linewidths=2, label="HV reference point")

    # Hypervolume rectangles
    current_upper_y = ref_y
    for _, row in front.iterrows():
        x = row["norm_f1"]
        y = row["norm_f2"]

        if y < current_upper_y:
            width = ref_x - x
            height = current_upper_y - y
            if width > 0 and height > 0:
                rect = Rectangle(
                    (x, y),
                    width,
                    height,
                    fill=False,
                    linestyle=":",
                    linewidth=1
                )
                ax.add_patch(rect)
            current_upper_y = y

    hv = compute_hypervolume_2d(front, "norm_f1", "norm_f2", ref_x, ref_y)
    hv_ratio = hv / (ref_x * ref_y)

    ax.set_title(title)
    ax.set_xlabel("norm_f1 (HV space)")
    ax.set_ylabel("norm_f2 (HV space)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Robust axis limits based on final ND front + reference point.
    # Dominated outliers outside this range are visually clipped — acceptable.
    margin = 0.05
    nd_x_vals = front["norm_f1"]
    nd_y_vals = front["norm_f2"]

    x_lo = min(0, nd_x_vals.min() if len(nd_x_vals) else 0) - margin
    x_hi = max(ref_x, nd_x_vals.max() if len(nd_x_vals) else ref_x) + margin
    y_lo = min(0, nd_y_vals.min() if len(nd_y_vals) else 0) - margin
    y_hi = max(ref_y, nd_y_vals.max() if len(nd_y_vals) else ref_y) + margin

    ax.set_xlim(left=x_lo, right=x_hi)
    ax.set_ylim(bottom=y_lo, top=y_hi)

    text = (
        f"ND count: {len(front)}\n"
        f"HV: {hv:.6f}\n"
        f"HV ratio: {hv_ratio:.6f}"
    )
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox=dict(boxstyle="round", alpha=0.15)
    )

    return front, hv, hv_ratio


# ---------------------------------------------------------------------------
# Improvement metrics (ND-based, raw objectives + C-metric)
#
# These are the official initial-to-final improvement assessment metrics.
# Hypervolume is NOT used for initial-to-final comparison.
# ---------------------------------------------------------------------------

def dominates(a, b, x_col="f1", y_col="f2"):
    """Return True if solution *a* dominates solution *b* (minimization)."""
    leq_f1 = a[x_col] <= b[x_col]
    leq_f2 = a[y_col] <= b[y_col]
    strict = a[x_col] < b[x_col] or a[y_col] < b[y_col]
    return leq_f1 and leq_f2 and strict


def coverage_metric(set_a: pd.DataFrame, set_b: pd.DataFrame,
                    x_col="f1", y_col="f2") -> float:
    """C-metric: fraction of solutions in *set_b* dominated by at least one
    solution in *set_a*.  Returns NaN when *set_b* is empty."""
    if len(set_b) == 0:
        return float("nan")
    if len(set_a) == 0:
        return 0.0

    dominated_count = 0
    for _, b_row in set_b.iterrows():
        for _, a_row in set_a.iterrows():
            if dominates(a_row, b_row, x_col, y_col):
                dominated_count += 1
                break
    return dominated_count / len(set_b)


def safe_improvement_percent(initial_value: float, final_value: float) -> float:
    """Percentage improvement (positive = better for minimization).
    Returns NaN when the denominator is zero."""
    if initial_value == 0:
        return float("nan")
    return (initial_value - final_value) / initial_value * 100


def compute_improvement_metrics(initial_df: pd.DataFrame,
                                final_df: pd.DataFrame) -> dict:
    """Compute all initial-to-final improvement metrics using raw objective
    non-dominated sets.  Handles empty fronts gracefully."""
    initial_nd = prepare_front(initial_df, "f1", "f2")
    final_nd = prepare_front(final_df, "f1", "f2")

    metrics = {}

    # ND count metrics
    metrics["initial_nd_count"] = len(initial_nd)
    metrics["final_nd_count"] = len(final_nd)
    metrics["nd_count_change"] = len(final_nd) - len(initial_nd)

    # Best objective improvements
    if len(initial_nd) > 0 and len(final_nd) > 0:
        metrics["best_f1_improvement"] = safe_improvement_percent(
            initial_nd["f1"].min(), final_nd["f1"].min())
        metrics["best_f2_improvement"] = safe_improvement_percent(
            initial_nd["f2"].min(), final_nd["f2"].min())
        metrics["mean_nd_f1_improvement"] = safe_improvement_percent(
            initial_nd["f1"].mean(), final_nd["f1"].mean())
        metrics["mean_nd_f2_improvement"] = safe_improvement_percent(
            initial_nd["f2"].mean(), final_nd["f2"].mean())
    else:
        metrics["best_f1_improvement"] = float("nan")
        metrics["best_f2_improvement"] = float("nan")
        metrics["mean_nd_f1_improvement"] = float("nan")
        metrics["mean_nd_f2_improvement"] = float("nan")

    # C-metric (set coverage)
    metrics["c_final_initial"] = coverage_metric(final_nd, initial_nd)
    metrics["c_initial_final"] = coverage_metric(initial_nd, final_nd)

    return metrics


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_percent(value) -> str:
    """Format a percentage value with two decimal places, or 'N/A'."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.2f}%"


def format_number(value) -> str:
    """Format a numeric value, or 'N/A' if not computable."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    if isinstance(value, int):
        return str(value)
    return f"{value}"


def format_with_commas(value) -> str:
    """Format an integer with thousands separators, or 'N/A'."""
    if value is None:
        return "N/A"
    return f"{int(value):,}"


def _format_coverage_percent(raw_fraction) -> str:
    """Convert a [0,1] coverage fraction to a display percentage string."""
    if raw_fraction is None or (isinstance(raw_fraction, float) and math.isnan(raw_fraction)):
        return "N/A"
    return format_percent(raw_fraction * 100)


# ---------------------------------------------------------------------------
# Plot: Improvement metrics panel
# ---------------------------------------------------------------------------

def plot_metrics_panel(ax, metrics: dict):
    """Render the improvement metrics as a clean table on the given axes."""
    ax.axis("off")
    ax.set_title("Initial \u2192 Final Improvement Metrics")

    rows = [
        ("Population size",          format_with_commas(metrics.get("population_size"))),
        ("Max generations",          format_with_commas(metrics.get("max_generations"))),
        ("Est. function evals",      format_with_commas(metrics.get("estimated_function_evaluations"))),
        ("Initial ND count",         format_number(metrics.get("initial_nd_count"))),
        ("Final ND count",           format_number(metrics.get("final_nd_count"))),
        ("ND count change",          format_number(metrics.get("nd_count_change"))),
        ("Best f1 improvement",      format_percent(metrics.get("best_f1_improvement"))),
        ("Best f2 improvement",      format_percent(metrics.get("best_f2_improvement"))),
        ("Mean ND f1 improvement",   format_percent(metrics.get("mean_nd_f1_improvement"))),
        ("Mean ND f2 improvement",   format_percent(metrics.get("mean_nd_f2_improvement"))),
        ("C(Final, Initial)",        _format_coverage_percent(metrics.get("c_final_initial"))),
        ("C(Initial, Final)",        _format_coverage_percent(metrics.get("c_initial_final"))),
    ]

    table = ax.table(
        cellText=[[label, value] for label, value in rows],
        colLabels=["Metric", "Value"],
        cellLoc="left",
        colWidths=[0.55, 0.35],
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # Style header row
    for col_idx in range(2):
        cell = table[0, col_idx]
        cell.set_text_props(weight="bold")
        cell.set_facecolor("#d5d5d5")


# ---------------------------------------------------------------------------
# Archive statistics
# ---------------------------------------------------------------------------

def archive_stats(df: pd.DataFrame, label: str) -> dict:
    pearson = df[["f1", "f2"]].corr(method="pearson").iloc[0, 1]
    spearman = df[["f1", "f2"]].corr(method="spearman").iloc[0, 1]

    nd_raw = prepare_front(df, "f1", "f2")
    nd_hv = prepare_front(df, "norm_f1", "norm_f2")

    stats = {
        "label": label,
        "count": len(df),
        "pearson": pearson,
        "spearman": spearman,
        "nd_raw_count": len(nd_raw),
        "nd_hv_count": len(nd_hv),
        "best_f1": df["f1"].min(),
        "best_f2": df["f2"].min(),
    }
    return stats


def print_stats(stats: dict):
    print("=" * 60)
    print(stats["label"])
    print(f"Archive size            : {stats['count']}")
    print(f"Pearson corr(f1, f2)    : {stats['pearson']:.6f}")
    print(f"Spearman corr(f1, f2)   : {stats['spearman']:.6f}")
    print(f"ND count (raw space)    : {stats['nd_raw_count']}")
    print(f"ND count (HV space)     : {stats['nd_hv_count']}")
    print(f"Best f1                 : {stats['best_f1']:.6f}")
    print(f"Best f2                 : {stats['best_f2']:.6f}")


def print_improvement_metrics(metrics: dict):
    """Print improvement metrics block to console."""
    print("============== INITIAL TO FINAL IMPROVEMENT ==============")
    print(f"Population size              : {format_with_commas(metrics.get('population_size'))}")
    print(f"Max generations              : {format_with_commas(metrics.get('max_generations'))}")
    print(f"Estimated function evals     : {format_with_commas(metrics.get('estimated_function_evaluations'))}")
    print(f"Initial ND count             : {format_number(metrics.get('initial_nd_count'))}")
    print(f"Final ND count               : {format_number(metrics.get('final_nd_count'))}")
    print(f"ND count change              : {format_number(metrics.get('nd_count_change'))}")
    print(f"Best f1 improvement (%)      : {format_percent(metrics.get('best_f1_improvement'))}")
    print(f"Best f2 improvement (%)      : {format_percent(metrics.get('best_f2_improvement'))}")
    print(f"Mean ND f1 improvement (%)   : {format_percent(metrics.get('mean_nd_f1_improvement'))}")
    print(f"Mean ND f2 improvement (%)   : {format_percent(metrics.get('mean_nd_f2_improvement'))}")
    print(f"C(Final, Initial)            : {_format_coverage_percent(metrics.get('c_final_initial'))}")
    print(f"C(Initial, Final)            : {_format_coverage_percent(metrics.get('c_initial_final'))}")
    print("==========================================================")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    initial_df = load_archive(INITIAL_CSV)
    final_df = load_archive(FINAL_CSV)

    initial_stats = archive_stats(initial_df, "INITIAL ARCHIVE")
    final_stats = archive_stats(final_df, "FINAL ARCHIVE")

    print_stats(initial_stats)
    print_stats(final_stats)

    # Load run metadata (population size, generations, function evals)
    run_meta = load_run_metadata()

    # Compute improvement metrics (ND-based, raw objectives + C-metric)
    metrics = compute_improvement_metrics(initial_df, final_df)

    # Inject run metadata into metrics dict for panel/console display
    metrics["population_size"] = int(run_meta.get("populationSize", DEFAULT_POPULATION_SIZE))
    metrics["max_generations"] = int(run_meta.get("maxGenerations", DEFAULT_MAX_GENERATIONS))
    metrics["estimated_function_evaluations"] = estimate_function_evaluations(run_meta)

    print_improvement_metrics(metrics)

    # -----------------------------------------------------------------------
    # 2x2 figure layout:
    #   [0,0] Initial Archive - Raw Objective Space
    #   [0,1] Final Archive   - Raw Objective Space
    #   [1,0] Initial → Final Improvement Metrics
    #   [1,1] Final Archive   - Hypervolume Space
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    initial_front_raw = plot_raw_space(
        axes[0, 0],
        initial_df,
        "Initial Archive - Raw Objective Space"
    )

    final_front_raw = plot_raw_space(
        axes[0, 1],
        final_df,
        "Final Archive - Raw Objective Space"
    )

    # Bottom-left: improvement metrics panel
    plot_metrics_panel(axes[1, 0], metrics)

    # Bottom-right: final archive HV space (normalization from final ND only)
    ref_x = REFERENCE_F1
    ref_y = REFERENCE_F2

    final_front_hv, final_hv, final_hv_ratio = plot_hv_space(
        axes[1, 1],
        final_df,
        "Final Archive - Hypervolume Space",
        ref_x,
        ref_y
    )

    # Bottom summary text
    c_fi_str = _format_coverage_percent(metrics.get("c_final_initial"))
    c_if_str = _format_coverage_percent(metrics.get("c_initial_final"))

    summary = (
        f"Initial Pearson: {initial_stats['pearson']:.4f} | "
        f"Initial Spearman: {initial_stats['spearman']:.4f} | "
        f"Final Pearson: {final_stats['pearson']:.4f} | "
        f"Final Spearman: {final_stats['spearman']:.4f}\n"
        f"Initial ND(raw): {len(initial_front_raw)} | "
        f"Final ND(raw): {len(final_front_raw)} | "
        f"Best f1 impr: {format_percent(metrics.get('best_f1_improvement'))} | "
        f"Best f2 impr: {format_percent(metrics.get('best_f2_improvement'))} | "
        f"Mean ND f1 impr: {format_percent(metrics.get('mean_nd_f1_improvement'))} | "
        f"Mean ND f2 impr: {format_percent(metrics.get('mean_nd_f2_improvement'))}\n"
        f"Function evals: {format_with_commas(metrics.get('estimated_function_evaluations'))} | "
        f"C(Final,Initial): {c_fi_str} | "
        f"C(Initial,Final): {c_if_str} | "
        f"Final HV ratio: {final_hv_ratio:.4f} | "
        f"(HV bounds: final ND only)"
    )

    fig.suptitle("Initial vs Final Archive Analysis", fontsize=16)
    fig.text(0.5, 0.01, summary, ha="center", va="bottom", fontsize=8)

    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save as latest for easy access
    latest_path = OUTPUT_DIR / "archive_comparison_latest.png"
    plt.savefig(latest_path, dpi=300, bbox_inches='tight')
    # plt.show() # Commented out to avoid blocking in non-interactive environments

    for candidate in OUTPUT_DIR.glob("archive_comparison_*.png"):
        if candidate.name == "archive_comparison_latest.png":
            continue
        candidate.unlink(missing_ok=True)

    print(f"============================================================")
    print(f"Latest plot updated at: {latest_path}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
