"""
RQ1 K=5 Random Baseline vs SPEA2 — Dumbbell Plot
================================================

This script does NOT run GA / SPEA2.
It only reads the already-created comparison CSV:

    output/rq1_k5_random_baseline_comparison.csv

and creates a clearer slide-ready dumbbell plot:

    final_results/rq1_k5_random_baseline_vs_spea2_dumbbell.png
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
comparison_path = Path("output") / "rq1_k5_random_baseline_comparison.csv"
figures_dir = Path("final_results")
figures_dir.mkdir(parents=True, exist_ok=True)

output_path = figures_dir / "rq1_k5_random_baseline_vs_spea2_dumbbell.png"


# ---------------------------------------------------------------------
# Load existing comparison data
# ---------------------------------------------------------------------
if not comparison_path.exists():
    raise FileNotFoundError(
        f"Missing file: {comparison_path}\n"
        "First run scripts/rq1_k5_baseline_analysis.py once to create the comparison CSV."
    )

df = pd.read_csv(comparison_path)

required_cols = {"seed", "random_f1", "spea2_f1"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns in {comparison_path}: {missing}")

df = df[["seed", "random_f1", "spea2_f1"]].copy()
df = df.sort_values("random_f1", ascending=True).reset_index(drop=True)

random_values = df["random_f1"].to_numpy(dtype=float)
spea2_values = df["spea2_f1"].to_numpy(dtype=float)

n = len(df)
if n == 0:
    raise ValueError("Comparison CSV is empty.")

random_mean = random_values.mean()
spea2_mean = spea2_values.mean()
percent_reduction = (random_mean - spea2_mean) / random_mean * 100

u_stat, p_value = stats.mannwhitneyu(
    spea2_values,
    random_values,
    alternative="less"
)

all_improved = int((spea2_values < random_values).sum())


# ---------------------------------------------------------------------
# Create dumbbell plot
# ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.2))

y_positions = np.arange(n)

# Draw one horizontal line per seed-indexed comparison
for y, random_f1, spea2_f1 in zip(y_positions, random_values, spea2_values):
    ax.plot(
        [spea2_f1, random_f1],
        [y, y],
        linewidth=1.6,
        alpha=0.45,
        zorder=1,
    )

# Draw points
ax.scatter(
    random_values,
    y_positions,
    s=58,
    label="Random baseline",
    alpha=0.85,
    zorder=3,
)

ax.scatter(
    spea2_values,
    y_positions,
    s=58,
    label="SPEA2 selected config (GA18)",
    alpha=0.95,
    zorder=4,
)

# Mean reference lines
ax.axvline(
    random_mean,
    linestyle="--",
    linewidth=1.4,
    alpha=0.75,
)

ax.axvline(
    spea2_mean,
    linestyle="--",
    linewidth=1.4,
    alpha=0.75,
)

# Mean labels
ax.text(
    random_mean,
    n + 0.15,
    f"Random mean = {random_mean:.2f}",
    ha="center",
    va="bottom",
    fontsize=9,
)

ax.text(
    spea2_mean,
    n + 0.15,
    f"SPEA2 mean = {spea2_mean:.2f}",
    ha="center",
    va="bottom",
    fontsize=9,
)

# Axes and title
ax.set_title(
    "RQ1 Validation: K=5 Random Baseline vs SPEA2",
    fontsize=14,
    fontweight="bold",
    pad=12,
)

ax.set_xlabel(
    "Best f₁ / accessibility cost (lower is better)",
    fontsize=11,
    fontweight="bold",
)

ax.set_ylabel(
    "Seed-indexed comparison\n(sorted by random baseline f₁)",
    fontsize=10,
)

# Use compact y labels, not all seed IDs, to keep it clean
ax.set_yticks(y_positions)
ax.set_yticklabels(df["seed"].astype(int).astype(str), fontsize=8)

ax.grid(axis="x", linestyle="--", alpha=0.28)
ax.grid(axis="y", linestyle=":", alpha=0.12)

# Improve x-axis readability
x_max = max(random_values.max(), spea2_values.max()) * 1.08
x_min = max(0, min(random_values.min(), spea2_values.min()) * 0.85)
ax.set_xlim(x_min, x_max)

# Stats box
p_display = "p < 0.001" if p_value < 0.001 else f"p = {p_value:.4f}"

stats_text = (
    f"K=5, n={n} seed-indexed comparisons\n"
    f"Mean f₁: {random_mean:.4f} → {spea2_mean:.4f}\n"
    f"Reduction: {percent_reduction:.2f}%\n"
    f"SPEA2 lower in {all_improved}/{n} comparisons\n"
    f"Mann–Whitney U: {p_display}"
)

ax.text(
    0.985,
    0.04,
    stats_text,
    transform=ax.transAxes,
    ha="right",
    va="bottom",
    fontsize=9,
    bbox=dict(
        boxstyle="round,pad=0.45",
        facecolor="white",
        edgecolor="gray",
        alpha=0.92,
    ),
)

ax.legend(
    loc="upper right",
    frameon=True,
    fontsize=9,
)

# Footer
fig.text(
    0.5,
    0.01,
    "Lower f₁ indicates better demand-weighted accessibility. "
    "This is a representative K=5 baseline validation, not an all-K baseline claim.",
    ha="center",
    fontsize=8.5,
    style="italic",
)

plt.tight_layout(rect=(0, 0.035, 1, 1))
plt.savefig(output_path, dpi=300, bbox_inches="tight")
plt.close()

print("=" * 70)
print("RQ1 dumbbell plot created.")
print(f"Input : {comparison_path}")
print(f"Output: {output_path}")
print()
print(f"Random mean f1 : {random_mean:.6f}")
print(f"SPEA2 mean f1  : {spea2_mean:.6f}")
print(f"Reduction      : {percent_reduction:.2f}%")
print(f"Mann-Whitney U : U={u_stat:.2f}, p={p_value:.8f}")
print(f"SPEA2 lower    : {all_improved}/{n}")
print("=" * 70)