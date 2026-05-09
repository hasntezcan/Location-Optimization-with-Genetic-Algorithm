import pandas as pd
import matplotlib.pyplot as plt
import os

# Paths to CSV files
csv_paths = {
    'selected_configurations': r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\output\statistics\selected_configurations.csv',
    'descriptive_by_k': r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\output\statistics\descriptive_by_k.csv',
    'parameter_analysis_results': r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\output\parameter_analysis_results.csv',
    'friedman_summary': r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\output\statistics\friedman_summary.csv',
    'posthoc_bonferroni': r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\output\statistics\posthoc_bonferroni.csv'
}

# Output directory
output_dir = r'c:\Users\ROG\Desktop\Location-Optimization-with-Genetic-Algorithm\sections\figures\final_results'
os.makedirs(output_dir, exist_ok=True)

# Read CSVs
dfs = {}
for name, path in csv_paths.items():
    dfs[name] = pd.read_csv(path)
    print(f"Columns in {name}.csv: {list(dfs[name].columns)}")

# Validate K values
k_values = [1, 5, 10, 15]
for name, df in dfs.items():
    if 'K' in df.columns:
        unique_k = sorted(df['K'].unique())
        print(f"Unique K in {name}.csv: {unique_k}")
        if not all(k in unique_k for k in k_values):
            print(f"Warning: Not all required K values {k_values} present in {name}.csv")
    else:
        print(f"No K column in {name}.csv")

# Filter to only K=1,5,10,15
for name, df in dfs.items():
    if 'K' in df.columns:
        dfs[name] = df[df['K'].isin(k_values)]

# Selected configurations
sel_df = dfs['selected_configurations']
desc_df = dfs['descriptive_by_k']
param_df = dfs['parameter_analysis_results']

# Merge selected with descriptive for additional metrics
sel_merged = sel_df.merge(desc_df[['K', 'GA_ID', 'Best_f1_mean', 'Best_f2_mean', 'Runtime_ms_mean']], 
                          left_on=['K', 'Selected_GA_ID'], right_on=['K', 'GA_ID'], how='left')

# Create summary CSV
summary_df = sel_merged[['K', 'Selected_GA_ID', 'PopulationSize', 'ArchiveSize', 'MutationRate', 'CrossoverRate', 
                         'Mean_Final_HV_Ratio', 'Median_Final_HV_Ratio', 'Std_Final_HV_Ratio', 
                         'Best_f1_mean', 'Best_f2_mean', 'Runtime_ms_mean']]
summary_df.columns = ['K', 'Selected_GA_ID', 'PopulationSize', 'ArchiveSize', 'MutationRate', 'CrossoverRate', 
                      'Final_HV_Ratio_mean', 'Final_HV_Ratio_median', 'Final_HV_Ratio_std', 
                      'Best_f1_mean', 'Best_f2_mean', 'Runtime_ms_mean']
summary_path = os.path.join(output_dir, 'selected_config_summary.csv')
summary_df.to_csv(summary_path, index=False)

# Plot 1: 3_1_selected_hv_ratio_vs_k.png
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
k_list = sel_df['K'].values
hv_mean = sel_df['Mean_Final_HV_Ratio'].values
hv_std = sel_df['Std_Final_HV_Ratio'].values
ga_ids = sel_df['Selected_GA_ID'].values
ax.errorbar(k_list, hv_mean, yerr=hv_std, fmt='o-', capsize=5, label='HV Ratio')
for i, ga in enumerate(ga_ids):
    ax.annotate(ga, (k_list[i], hv_mean[i]), textcoords="offset points", xytext=(0,10), ha='center')
ax.set_xticks([1, 5, 10, 15])
ax.set_xlabel('Number of Lockers (K)')
ax.set_ylabel('Final HV Ratio')
ax.set_title('Selected GA Final HV Ratio Across K')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_1_selected_hv_ratio_vs_k.png'), bbox_inches='tight')
plt.close()

# Plot 2: 3_2_best_f1_vs_k.png
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
f1_mean = sel_merged['Best_f1_mean'].values
ax.plot(k_list, f1_mean, 'o-', label='Best f1 mean')
for i, val in enumerate(f1_mean):
    ax.annotate(f'{val:.4f}', (k_list[i], val), textcoords="offset points", xytext=(0,10), ha='center')
ax.set_xticks([1, 5, 10, 15])
ax.set_xlabel('Number of Lockers (K)')
ax.set_ylabel('Best f1 mean (lower is better)')
ax.set_title('Accessibility Objective Across K')
ax.set_ylim(bottom=min(f1_mean) - 0.1, top=max(f1_mean) + 0.5)  # Add padding
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_2_best_f1_vs_k.png'), bbox_inches='tight')
plt.close()

# Plot 3: 3_3_marginal_f1_reduction.png
f1_values = {k: sel_merged[sel_merged['K'] == k]['Best_f1_mean'].values[0] for k in k_values}
reductions = []
labels = []
for i in range(len(k_values)-1):
    prev_k = k_values[i]
    curr_k = k_values[i+1]
    prev_f1 = f1_values[prev_k]
    curr_f1 = f1_values[curr_k]
    red = (prev_f1 - curr_f1) / prev_f1 * 100
    reductions.append(red)
    labels.append(f'{prev_k}→{curr_k}')

fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
bars = ax.bar(labels, reductions)
for bar, val in zip(bars, reductions):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{val:.2f}%', ha='center', va='bottom')
ax.set_xlabel('K Transition')
ax.set_ylabel('Relative Best f1 Reduction (%)')
ax.set_title('Marginal f1 Reduction Across K Transitions')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_3_marginal_f1_reduction.png'), bbox_inches='tight')
plt.close()

# Plot 4: 3_4_best_f2_vs_k.png
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
f2_mean = sel_merged['Best_f2_mean'].values
ax.plot(k_list, f2_mean, 'o-', label='Best f2 mean')
for i, val in enumerate(f2_mean):
    ax.annotate(f'{val:.4f}', (k_list[i], val), textcoords="offset points", xytext=(0,10), ha='center')
ax.set_xticks([1, 5, 10, 15])
ax.set_xlabel('Number of Lockers (K)')
ax.set_ylabel('Best f2 mean (lower is better)')
ax.set_title('Equity Objective Across K')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_4_best_f2_vs_k.png'), bbox_inches='tight')
plt.close()

# Plot 5: 3_5_runtime_vs_k.png
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
runtime_sec = sel_merged['Runtime_ms_mean'].values / 1000
ax.plot(k_list, runtime_sec, 'o-', label='Runtime (s)')
for i, val in enumerate(runtime_sec):
    ax.annotate(f'{val:.1f}s', (k_list[i], val), textcoords="offset points", xytext=(0,10), ha='center')
ax.set_xticks([1, 5, 10, 15])
ax.set_xlabel('Number of Lockers (K)')
ax.set_ylabel('Runtime (seconds)')
ax.set_title('Runtime Scaling of Selected Configurations')
ax.set_ylim(bottom=min(runtime_sec) - 10, top=max(runtime_sec) + 50)  # Add padding
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_5_runtime_vs_k.png'), bbox_inches='tight')
plt.close()

# Plot 6: 3_7_hv_distribution_by_ga_combined.png
fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=300)
axes = axes.flatten()
for idx, k in enumerate(k_values):
    ax = axes[idx]
    k_data = param_df[param_df['K'] == k]
    ga_groups = k_data.groupby('GA_ID')['Final_HV_Ratio'].apply(list)
    # Sort GA_ID numerically
    ga_sorted = sorted(ga_groups.index, key=lambda x: int(x[2:]))
    ga_groups = ga_groups.reindex(ga_sorted)
    ax.boxplot(ga_groups.values, tick_labels=ga_groups.index)
    selected_ga = sel_df[sel_df['K'] == k]['Selected_GA_ID'].values[0]
    if selected_ga in ga_groups.index:
        pos = list(ga_groups.index).index(selected_ga) + 1
        ax.axvline(pos, color='red', linestyle='--', label=f'Selected: {selected_ga}')
    ax.set_xlabel('GA_ID')
    ax.set_ylabel('Final HV Ratio')
    ax.set_title(f'K={k}')
    ax.tick_params(axis='x', rotation=45)
    ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, '3_7_hv_distribution_by_ga_combined.png'), bbox_inches='tight')
plt.close()

# Plot 7: 3_6_mutation_rate_effect.png
if 'MutationRate' in desc_df.columns and 'Final_HV_Ratio_median' in desc_df.columns:
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    for k in k_values:
        k_data = desc_df[desc_df['K'] == k]
        mut_groups = k_data.groupby('MutationRate')['Final_HV_Ratio_median'].mean()
        ax.plot(mut_groups.index, mut_groups.values, 'o-', label=f'K={k}')
    ax.set_xlabel('Mutation Rate')
    ax.set_ylabel('Median Final HV Ratio')
    ax.set_title('Mutation Rate Effect on Final HV Ratio')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '3_6_mutation_rate_effect.png'), bbox_inches='tight')
    plt.close()
else:
    print("Warning: Required columns for mutation_rate_effect.png not found. Skipping.")

print("Script completed.")
print(f"Summary CSV saved to: {summary_path}")
print("Plots generated:")
for f in ['3_1_selected_hv_ratio_vs_k.png', '3_2_best_f1_vs_k.png', '3_3_marginal_f1_reduction.png', '3_4_best_f2_vs_k.png', '3_5_runtime_vs_k.png', '3_7_hv_distribution_by_ga_combined.png']:
    print(f"  {os.path.join(output_dir, f)}")
if os.path.exists(os.path.join(output_dir, '3_6_mutation_rate_effect.png')):
    print(f"  {os.path.join(output_dir, '3_6_mutation_rate_effect.png')}")
else:
    print("  3_6_mutation_rate_effect.png skipped")