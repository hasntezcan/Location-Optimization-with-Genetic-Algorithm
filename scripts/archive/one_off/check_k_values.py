import pandas as pd

os_df = pd.read_csv(r"output\objective_space_run_summary.csv")
print("objective_space_run_summary.csv - K values analysis:")
print(f"  K values: {sorted(os_df['k'].unique())}")
print(f"\nAll rows with K info:")
print(os_df[['run_id', 'k', 'population_size', 'final_archive_min_f1', 'final_archive_max_f1']])
