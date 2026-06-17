"""
RQ1 K=5 Random Baseline Validation against SPEA2
=================================================

Purpose:
- Generate 20 random baseline placements for K=5
- Compare against existing SPEA2 results for K=5
- Compute Mann-Whitney U test
- Create visualization
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import os
import sys

# Paths
data_dir = r"data"
output_dir = r"output"
results_dir = r"output"
figures_dir = r"final_results"

os.makedirs(figures_dir, exist_ok=True)

print("=" * 70)
print("RQ1 K=5 Random Baseline vs SPEA2 Analysis")
print("=" * 70)

# ============================================================================
# STEP 1: Load Data
# ============================================================================
print("\n[1] Loading data files...")

# Load candidate points
cand_path = os.path.join(data_dir, "candidate_points.csv")
cand_df = pd.read_csv(cand_path)
print(f"   - Loaded {len(cand_df)} candidate points")
print(f"   - Selectable (is_forbidden==0): {(cand_df['is_forbidden']==0).sum()}")

# Load distance matrix
dist_path = os.path.join(data_dir, "kadikoy_distance_meters_nxn.npy")
dist_matrix = np.load(dist_path)
print(f"   - Loaded distance matrix: {dist_matrix.shape}")

# Load SPEA2 K=5 results from the restored final parameter analysis file
param_final_path = os.path.join(output_dir, "parameter_analysis", "parameter_analysis_results.csv")
print(f"   - Loading restored parameter analysis file: {param_final_path}")
param_final_df = pd.read_csv(param_final_path)
print(f"   - Loaded restored parameter analysis results: {param_final_df.shape}")
print(f"   - Unique K values: {sorted(param_final_df['K'].unique())}")

# ============================================================================
# STEP 2: Extract SPEA2 K=5 Results
# ============================================================================
print("\n[2] Extracting SPEA2 K=5 results...")

# Filter for K=5 and GA18 runs
spea2_k5_df = param_final_df[(param_final_df['K'] == 5) & (param_final_df['GA_ID'] == 'GA18')].copy()
print(f"   - Found {len(spea2_k5_df)} SPEA2 K=5 GA18 rows")

if len(spea2_k5_df) != 20:
    raise ValueError(f"Expected 20 rows for K=5 GA18, but found {len(spea2_k5_df)}. Please verify the restored final file.")

# For the baseline comparison, use Best_f1
spea2_f1_values = spea2_k5_df['Best_f1'].values

print(f"   - SPEA2 K=5 GA18 Best_f1 values (n={len(spea2_f1_values)}):")
print(f"     Mean: {spea2_f1_values.mean():.6f}")
print(f"     Median: {np.median(spea2_f1_values):.6f}")
print(f"     Std: {spea2_f1_values.std():.6f}")
print(f"     Min: {spea2_f1_values.min():.6f}, Max: {spea2_f1_values.max():.6f}")

# ============================================================================
# STEP 3: Compute f1 for Random Baselines
# ============================================================================
print("\n[3] Computing f1 for 20 random baseline placements (K=5)...")

# Get selectable candidates (is_forbidden == 0)
selectable_mask = cand_df['is_forbidden'] == 0
selectable_ids = cand_df.loc[selectable_mask, 'id'].values
selectable_indices = np.where(selectable_mask)[0]
print(f"   - Selectable candidates: {len(selectable_ids)}")

# Get demand scores and create index map
demand_scores = cand_df['demand_final'].values
total_demand = demand_scores.sum()
print(f"   - Total demand: {total_demand:.2f}")

# Parameters
K = 5
beta = 2.0
n_seeds = len(spea2_f1_values)  # Match the number of SPEA2 runs

print(f"   - K: {K}, beta: {beta}, n_seeds (matching SPEA2 runs): {n_seeds}")

# Store random baseline results
random_f1_values = []
random_baseline_details = []

np.random.seed(42)  # For reproducibility
for seed in range(1, n_seeds + 1):
    np.random.seed(seed)
    
    # Random sample K selectable candidates
    sampled_indices = np.random.choice(selectable_indices, size=K, replace=False)
    
    # Compute f1: demand-weighted average distance cost
    weighted_sum = 0.0
    for cand_idx, demand in enumerate(demand_scores):
        # Find minimum distance to any selected locker
        min_dist_meters = dist_matrix[cand_idx, sampled_indices].min()
        min_dist_km = min_dist_meters / 1000.0
        cost = (min_dist_km ** beta)
        weighted_sum += demand * cost
    
    f1 = weighted_sum / total_demand
    random_f1_values.append(f1)
    random_baseline_details.append({
        'seed': seed,
        'f1': f1,
        'selected_ids': cand_df.iloc[sampled_indices]['id'].values.tolist()
    })
    
    if seed <= 5 or seed == n_seeds:
        print(f"   - Seed {seed:2d}: f1 = {f1:.6f}, selected_ids = {cand_df.iloc[sampled_indices]['id'].values[:3]}...")

random_f1_values = np.array(random_f1_values)
print(f"\n   Random Baseline K=5 f1 distribution (n={len(random_f1_values)}):")
print(f"     Mean: {random_f1_values.mean():.6f}")
print(f"     Median: {np.median(random_f1_values):.6f}")
print(f"     Std: {random_f1_values.std():.6f}")
print(f"     Min: {random_f1_values.min():.6f}, Max: {random_f1_values.max():.6f}")

# ============================================================================
# STEP 4: Statistical Comparison (Mann-Whitney U Test)
# ============================================================================
print("\n[4] Statistical Comparison...")

# Mann-Whitney U test: H1: SPEA2 f1 < Random baseline f1
u_stat, p_value = stats.mannwhitneyu(spea2_f1_values, random_f1_values, alternative='less')

print(f"   Mann-Whitney U Test (one-sided: SPEA2 < Random):")
print(f"     U-statistic: {u_stat:.2f}")
print(f"     p-value: {p_value:.6f}")

if p_value < 0.05:
    print(f"     Result: STATISTICALLY SIGNIFICANT (p < 0.05)")
    print(f"     Interpretation: SPEA2 f1 is significantly lower than random baseline")
else:
    print(f"     Result: NOT significant (p >= 0.05)")

# Percent reduction
random_mean = random_f1_values.mean()
spea2_mean = spea2_f1_values.mean()
percent_reduction = ((random_mean - spea2_mean) / random_mean) * 100

print(f"\n   Improvement Summary:")
print(f"     Random Mean: {random_mean:.6f}")
print(f"     SPEA2 Mean: {spea2_mean:.6f}")
print(f"     Percent Reduction: {percent_reduction:.2f}%")

# ============================================================================
# STEP 5: Save Results
# ============================================================================
print("\n[5] Saving results...")

# Detailed comparison CSV
comparison_data = []
for i, spea2_val in enumerate(spea2_f1_values):
    comparison_data.append({
        'seed': i + 1,
        'random_f1': random_f1_values[i],
        'spea2_f1': spea2_val,
        'improvement': random_f1_values[i] - spea2_val
    })

comparison_df = pd.DataFrame(comparison_data)
comparison_csv = os.path.join(results_dir, "rq1_k5_random_baseline_comparison.csv")
comparison_df.to_csv(comparison_csv, index=False)
print(f"   - Saved: {comparison_csv}")

# Summary statistics CSV
summary_data = {
    'Metric': [
        'Mean',
        'Median',
        'Std Dev',
        'Min',
        'Max',
        'Count'
    ],
    'Random_Baseline': [
        random_f1_values.mean(),
        np.median(random_f1_values),
        random_f1_values.std(),
        random_f1_values.min(),
        random_f1_values.max(),
        len(random_f1_values)
    ],
    'SPEA2_K5_GA18': [
        spea2_f1_values.mean(),
        np.median(spea2_f1_values),
        spea2_f1_values.std(),
        spea2_f1_values.min(),
        spea2_f1_values.max(),
        len(spea2_f1_values)
    ]
}

summary_df = pd.DataFrame(summary_data)
summary_csv = os.path.join(results_dir, "rq1_k5_random_baseline_summary.csv")
summary_df.to_csv(summary_csv, index=False)
print(f"   - Saved: {summary_csv}")

# ============================================================================
# STEP 6: Create Boxplot Visualization
# ============================================================================
print("\n[6] Creating visualization...")

fig, ax = plt.subplots(figsize=(10, 6))

# Prepare data for boxplot
data_to_plot = [random_f1_values, spea2_f1_values]
labels = ['Random Baseline', 'SPEA2 Selected Config (GA18)']

# Create boxplot
bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True, widths=0.6)

# Customize colors
colors = ['#FFB6C1', '#87CEEB']  # Light pink, light blue
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

# Customize plot
ax.set_ylabel('Best f1 / accessibility cost (lower is better)', fontsize=11, fontweight='bold')
ax.set_title('RQ1 Validation: K=5 Random Baseline vs SPEA2', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add note
fig.text(0.5, 0.02, 'K=5, n=20 seeds. Lower f1 indicates better demand-weighted accessibility.',
         ha='center', fontsize=9, style='italic', color='gray')

# Add statistics text
stats_text = f'Mann-Whitney U test (one-sided):\np-value = {p_value:.4f}\nImprovement: {percent_reduction:.1f}%'
ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
        fontsize=9, verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.subplots_adjust(bottom=0.1)

boxplot_path = os.path.join(figures_dir, "rq1_k5_random_baseline_vs_spea2_boxplot.png")
plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
print(f"   - Saved: {boxplot_path}")
plt.close()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"""
RQ1 K=5 Baseline Validation Complete

Files created:
  1. {os.path.basename(comparison_csv)}
  2. {os.path.basename(summary_csv)}
  3. {os.path.basename(boxplot_path)}

Results:
  - Random Baseline Mean f1: {random_f1_values.mean():.6f}
  - SPEA2 K=5 Mean f1: {spea2_f1_values.mean():.6f}
  - Improvement: {percent_reduction:.2f}% reduction in accessibility cost
  - Mann-Whitney U p-value: {p_value:.6f}
  - Significance: {'YES (p < 0.05)' if p_value < 0.05 else 'NO (p >= 0.05)'}

Interpretation:
This is a representative K=5 baseline validation showing whether optimized 
SPEA2 placement improves accessibility compared with random placement.
DO NOT claim this validates all K values.
""")

print("=" * 70)
