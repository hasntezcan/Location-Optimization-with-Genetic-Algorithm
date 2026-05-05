"""
Plot all thesis figures for RQ1, RQ2, RQ3.

Reads results from output/rq_analysis/metrics/rq_analysis_results.json
and generates publication-quality figures.

Usage:
    python scripts/plot_rq_results.py
    python scripts/plot_rq_results.py --dpi 300
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = PROJECT_ROOT / "output" / "rq_analysis" / "metrics" / "rq_analysis_results.json"
PLOTS_DIR = PROJECT_ROOT / "output" / "rq_analysis" / "plots"

K_VALUES = [3, 6, 10]

# Style
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 150,
})

COLORS = {
    "greedy": "#e74c3c",
    "optimized": "#2ecc71",
    "random": "#95a5a6",
    "existing": "#3498db",
}


def load_results() -> dict:
    with open(RESULTS_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# RQ1: Accessibility comparison
# ---------------------------------------------------------------------------


def plot_rq1_distance_comparison(results: dict, dpi: int = 300):
    """Bar chart: mean and median distance for baseline vs optimized across K."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bar_width = 0.25
    x = np.arange(len(K_VALUES))

    for ax_idx, metric in enumerate(["mean_distance_m", "median_distance_m"]):
        ax = axes[ax_idx]
        title = "Mean Distance" if ax_idx == 0 else "Median Distance"

        greedy_vals = []
        opt_vals = []
        random_vals = []

        for k in K_VALUES:
            greedy_vals.append(results["baselines"].get(f"greedy_k{k}", {}).get(metric, 0))
            random_vals.append(results["baselines"].get(f"random_k{k}", {}).get(metric, 0))

            comp = results.get("comparisons", {}).get(str(k), {})
            seed_summary = comp.get("seed_summary", {})
            key = "mean_distance" if ax_idx == 0 else "mean_distance"
            opt_vals.append(seed_summary.get(key, {}).get("mean", 0))

        bars1 = ax.bar(x - bar_width, greedy_vals, bar_width, label="Greedy Baseline",
                       color=COLORS["greedy"], alpha=0.85, edgecolor="white", linewidth=0.5)
        bars2 = ax.bar(x, opt_vals, bar_width, label="Optimized (Knee)",
                       color=COLORS["optimized"], alpha=0.85, edgecolor="white", linewidth=0.5)
        bars3 = ax.bar(x + bar_width, random_vals, bar_width, label="Random Baseline",
                       color=COLORS["random"], alpha=0.85, edgecolor="white", linewidth=0.5)

        ax.set_xlabel("Number of Lockers (K)")
        ax.set_ylabel(f"{title} (m)")
        ax.set_title(f"{title} to Nearest Locker")
        ax.set_xticks(x)
        ax.set_xticklabels([f"K={k}" for k in K_VALUES])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Add value labels
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height + 20,
                            f"{height:.0f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out = PLOTS_DIR / "rq1_distance_comparison.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_rq1_coverage(results: dict, dpi: int = 300):
    """Grouped bar chart: coverage at 500m, 1km, 2km thresholds."""
    fig, ax = plt.subplots(figsize=(10, 6))

    thresholds = ["coverage_500m", "coverage_1000m", "coverage_2000m"]
    threshold_labels = ["500 m", "1 km", "2 km"]

    n_k = len(K_VALUES)
    n_thresh = len(thresholds)
    bar_width = 0.12
    group_width = bar_width * (n_k * 2 + 1)

    for t_idx, (thresh, t_label) in enumerate(zip(thresholds, threshold_labels)):
        base_x = t_idx * (group_width + 0.15)

        for k_idx, k in enumerate(K_VALUES):
            greedy_val = results["baselines"].get(f"greedy_k{k}", {}).get(thresh, 0)
            comp = results.get("comparisons", {}).get(str(k), {})
            # Get optimized coverage
            per_seed = comp.get("per_seed_metrics", [])
            if per_seed:
                opt_val = np.mean([m.get(thresh, 0) for m in per_seed])
            else:
                opt_val = 0

            x_greedy = base_x + k_idx * bar_width * 2.2
            x_opt = x_greedy + bar_width * 1.1

            ax.bar(x_greedy, greedy_val, bar_width, color=COLORS["greedy"],
                   alpha=0.85, edgecolor="white", linewidth=0.5)
            ax.bar(x_opt, opt_val, bar_width, color=COLORS["optimized"],
                   alpha=0.85, edgecolor="white", linewidth=0.5)

            # Labels
            if t_idx == 0:
                mid = (x_greedy + x_opt) / 2
                ax.text(mid, -3, f"K={k}", ha="center", fontsize=9, fontweight="bold")

    # Custom x-axis
    group_centers = []
    for t_idx in range(n_thresh):
        base_x = t_idx * (group_width + 0.15)
        center = base_x + (n_k - 1) * bar_width * 1.1
        group_centers.append(center)

    ax.set_xticks(group_centers)
    ax.set_xticklabels(threshold_labels)
    ax.set_ylabel("Population Coverage (%)")
    ax.set_title("Coverage at Distance Thresholds: Greedy vs. Optimized")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(axis="y", alpha=0.3)

    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS["greedy"], alpha=0.85, label="Greedy Baseline"),
        Patch(facecolor=COLORS["optimized"], alpha=0.85, label="Optimized (Knee)"),
    ]
    ax.legend(handles=legend_elements, loc="upper left")

    plt.tight_layout()
    out = PLOTS_DIR / "rq1_coverage_thresholds.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# RQ2: Performance vs K
# ---------------------------------------------------------------------------


def plot_rq2_scaling(results: dict, dpi: int = 300):
    """Line plots: metrics vs K for greedy, optimized, and random."""
    metrics = [
        ("mean_distance_m", "Mean Distance (m)", False),
        ("coverage_500m", "Coverage at 500 m (%)", True),
        ("coverage_1000m", "Coverage at 1 km (%)", True),
        ("cv_equity", "CV (Equity)", False),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for idx, (metric_key, ylabel, higher_better) in enumerate(metrics):
        ax = axes[idx // 2][idx % 2]

        greedy_vals = []
        opt_mean_vals = []
        opt_std_vals = []
        random_vals = []

        for k in K_VALUES:
            greedy_vals.append(
                results["baselines"].get(f"greedy_k{k}", {}).get(metric_key, 0)
            )
            random_vals.append(
                results["baselines"].get(f"random_k{k}", {}).get(metric_key, 0)
            )

            comp = results.get("comparisons", {}).get(str(k), {})
            per_seed = comp.get("per_seed_metrics", [])
            if per_seed:
                vals = [m.get(metric_key, 0) for m in per_seed]
                opt_mean_vals.append(np.mean(vals))
                opt_std_vals.append(np.std(vals))
            else:
                opt_mean_vals.append(0)
                opt_std_vals.append(0)

        ax.plot(K_VALUES, greedy_vals, "o-", color=COLORS["greedy"],
                label="Greedy Baseline", linewidth=2, markersize=8)
        ax.errorbar(K_VALUES, opt_mean_vals, yerr=opt_std_vals, fmt="s-",
                    color=COLORS["optimized"], label="Optimized (Knee ± σ)",
                    linewidth=2, markersize=8, capsize=4)
        ax.plot(K_VALUES, random_vals, "^--", color=COLORS["random"],
                label="Random Baseline", linewidth=1.5, markersize=7, alpha=0.7)

        ax.set_xlabel("Number of Lockers (K)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(K_VALUES)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

        # Mark improvement direction
        if higher_better:
            ax.annotate("↑ better", xy=(0.02, 0.95), xycoords="axes fraction",
                        fontsize=8, color="green", alpha=0.7)
        else:
            ax.annotate("↓ better", xy=(0.02, 0.95), xycoords="axes fraction",
                        fontsize=8, color="green", alpha=0.7)

    plt.suptitle("Performance Scaling with Number of Lockers (K)", fontsize=14, y=1.02)
    plt.tight_layout()
    out = PLOTS_DIR / "rq2_performance_scaling.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_rq2_marginal_gains(results: dict, dpi: int = 300):
    """Bar chart: marginal improvement from K=3→6 and K=6→10."""
    metrics = [
        ("mean_distance_m", "Mean Distance Reduction (m)", True),
        ("coverage_500m", "Coverage Increase at 500m (pp)", False),
        ("cv_equity", "CV Reduction", True),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    transitions = [("3→6", 3, 6), ("6→10", 6, 10)]
    x = np.arange(len(transitions))
    bar_width = 0.35

    for ax_idx, (metric_key, ylabel, is_reduction) in enumerate(metrics):
        ax = axes[ax_idx]

        greedy_gains = []
        opt_gains = []

        for label, k_from, k_to in transitions:
            g_from = results["baselines"].get(f"greedy_k{k_from}", {}).get(metric_key, 0)
            g_to = results["baselines"].get(f"greedy_k{k_to}", {}).get(metric_key, 0)

            comp_from = results.get("comparisons", {}).get(str(k_from), {})
            comp_to = results.get("comparisons", {}).get(str(k_to), {})

            ps_from = comp_from.get("per_seed_metrics", [])
            ps_to = comp_to.get("per_seed_metrics", [])

            o_from = np.mean([m.get(metric_key, 0) for m in ps_from]) if ps_from else 0
            o_to = np.mean([m.get(metric_key, 0) for m in ps_to]) if ps_to else 0

            if is_reduction:
                greedy_gains.append(g_from - g_to)
                opt_gains.append(o_from - o_to)
            else:
                greedy_gains.append(g_to - g_from)
                opt_gains.append(o_to - o_from)

        ax.bar(x - bar_width / 2, greedy_gains, bar_width, label="Greedy",
               color=COLORS["greedy"], alpha=0.85, edgecolor="white")
        ax.bar(x + bar_width / 2, opt_gains, bar_width, label="Optimized",
               color=COLORS["optimized"], alpha=0.85, edgecolor="white")

        ax.set_ylabel(ylabel)
        ax.set_title(ylabel.split("(")[0].strip())
        ax.set_xticks(x)
        ax.set_xticklabels([t[0] for t in transitions])
        ax.set_xlabel("K Transition")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        ax.axhline(y=0, color="black", linewidth=0.5)

    plt.suptitle("Marginal Improvement Analysis (VT2)", fontsize=14, y=1.02)
    plt.tight_layout()
    out = PLOTS_DIR / "rq2_marginal_gains.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# RQ3: Equity comparison
# ---------------------------------------------------------------------------


def plot_rq3_equity(results: dict, dpi: int = 300):
    """Bar chart: CV and variance for greedy vs optimized."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bar_width = 0.3
    x = np.arange(len(K_VALUES))

    for ax_idx, (metric, ylabel) in enumerate([
        ("cv_equity", "Coefficient of Variation (CV)"),
        ("variance_equity", "Variance of Neighborhood Mean Distances"),
    ]):
        ax = axes[ax_idx]

        greedy_vals = []
        opt_vals = []

        for k in K_VALUES:
            greedy_vals.append(
                results["baselines"].get(f"greedy_k{k}", {}).get(metric, 0)
            )
            comp = results.get("comparisons", {}).get(str(k), {})
            per_seed = comp.get("per_seed_metrics", [])
            if per_seed:
                opt_vals.append(np.mean([m.get(metric, 0) for m in per_seed]))
            else:
                opt_vals.append(0)

        ax.bar(x - bar_width / 2, greedy_vals, bar_width, label="Greedy Baseline",
               color=COLORS["greedy"], alpha=0.85, edgecolor="white")
        ax.bar(x + bar_width / 2, opt_vals, bar_width, label="Optimized (Knee)",
               color=COLORS["optimized"], alpha=0.85, edgecolor="white")

        ax.set_xlabel("Number of Lockers (K)")
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel.split("(")[0].strip() if "(" in ylabel else ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels([f"K={k}" for k in K_VALUES])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        ax.annotate("↓ better", xy=(0.02, 0.95), xycoords="axes fraction",
                    fontsize=8, color="green", alpha=0.7)

    plt.suptitle("Equity Comparison: Greedy vs. Optimized (VT3)", fontsize=14, y=1.02)
    plt.tight_layout()
    out = PLOTS_DIR / "rq3_equity_comparison.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_rq3_mahalle_heatmap(results: dict, dpi: int = 300):
    """Heatmap: neighborhood-level mean distances for greedy vs optimized, per K."""
    # Collect neighborhood names
    neighborhoods = sorted(
        results["baselines"].get("greedy_k3", {}).get("mahalle_mean_distances", {}).keys()
    )
    if not neighborhoods:
        print("  ⚠ No neighborhood data for heatmap")
        return

    n_neigh = len(neighborhoods)

    fig, axes = plt.subplots(1, len(K_VALUES), figsize=(6 * len(K_VALUES), max(8, n_neigh * 0.4)))

    for k_idx, k in enumerate(K_VALUES):
        ax = axes[k_idx]

        greedy_mahalle = results["baselines"].get(f"greedy_k{k}", {}).get(
            "mahalle_mean_distances", {}
        )

        # Get best-seed optimized mahalle distances
        comp = results.get("comparisons", {}).get(str(k), {})
        eq = comp.get("equity_test", {})

        greedy_dists = [greedy_mahalle.get(n, 0) for n in neighborhoods]
        # For optimized, we need per-seed data... use the metrics
        per_seed = comp.get("per_seed_metrics", [])
        if per_seed:
            # We don't have mahalle in per_seed_metrics in JSON...
            # Just show greedy for now
            pass

        y = np.arange(n_neigh)

        ax.barh(y, greedy_dists, 0.4, label="Greedy", color=COLORS["greedy"], alpha=0.85)

        ax.set_yticks(y)
        ax.set_yticklabels(neighborhoods, fontsize=8)
        ax.set_xlabel("Mean Distance (m)")
        ax.set_title(f"K = {k}")
        ax.grid(axis="x", alpha=0.3)

        if k_idx == 0:
            ax.legend()

    plt.suptitle("Neighborhood-Level Mean Distances", fontsize=14)
    plt.tight_layout()
    out = PLOTS_DIR / "rq3_mahalle_distances.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Statistical test summary table
# ---------------------------------------------------------------------------


def plot_stat_test_table(results: dict, dpi: int = 300):
    """Visual table of statistical test results."""
    rows = []
    for k in K_VALUES:
        comp = results.get("comparisons", {}).get(str(k), {})
        acc = comp.get("accessibility_test", {})
        eq = comp.get("equity_test", {})

        rows.append([
            f"K={k}",
            f"{acc.get('mean_improvement_m', 0):.1f}",
            f"{acc.get('cohens_d', 0):.4f}",
            f"{acc.get('wilcoxon_p', 1):.2e}",
            "Yes" if acc.get("wilcoxon_significant_005") else "No",
            f"{eq.get('baseline_cv', 0):.4f}",
            f"{eq.get('optimized_cv', 0):.4f}",
            f"{eq.get('cv_reduction_pct', 0):.1f}%",
            f"{eq.get('levene_p', 1):.4f}",
        ])

    col_labels = [
        "K", "Mean Impr.\n(m)", "Cohen's d",
        "Wilcoxon\np-value", "Sig.\n(p<0.05)",
        "Baseline\nCV", "Optimized\nCV", "CV\nReduction",
        "Levene\np-value",
    ]

    fig, ax = plt.subplots(figsize=(14, 2 + len(rows) * 0.6))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)

    # Style header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#34495e")
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#ecf0f1")

    plt.title("Statistical Test Summary (VT1 + VT3)", fontsize=13, pad=20)
    plt.tight_layout()
    out = PLOTS_DIR / "stat_test_summary.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Generate thesis figures")
    parser.add_argument("--dpi", type=int, default=300, help="Figure DPI")
    args = parser.parse_args()

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    if not RESULTS_PATH.exists():
        print(f"Results not found: {RESULTS_PATH}")
        print("Run 'python scripts/run_rq_experiments.py' first.")
        return

    print("Loading results...")
    results = load_results()

    print("\nGenerating figures...")
    plot_rq1_distance_comparison(results, args.dpi)
    plot_rq1_coverage(results, args.dpi)
    plot_rq2_scaling(results, args.dpi)
    plot_rq2_marginal_gains(results, args.dpi)
    plot_rq3_equity(results, args.dpi)
    plot_rq3_mahalle_heatmap(results, args.dpi)
    plot_stat_test_table(results, args.dpi)

    print(f"\nAll figures saved to: {PLOTS_DIR}")


if __name__ == "__main__":
    main()
