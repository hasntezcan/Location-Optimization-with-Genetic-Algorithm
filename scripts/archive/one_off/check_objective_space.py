import pandas as pd

# Check objective space files
try:
    od_df = pd.read_csv(r"output\objective_space_nd_points.csv")
    print("objective_space_nd_points.csv:")
    print(f"  Shape: {od_df.shape}")
    print(f"  Columns: {list(od_df.columns)}")
    if 'K' in od_df.columns:
        print(f"  K values: {sorted(od_df['K'].unique())}")
    print()
except Exception as e:
    print(f"Error reading objective_space_nd_points.csv: {e}\n")

try:
    os_df = pd.read_csv(r"output\objective_space_run_summary.csv")
    print("objective_space_run_summary.csv:")
    print(f"  Shape: {os_df.shape}")
    print(f"  Columns: {list(os_df.columns)}")
    if 'K' in os_df.columns:
        print(f"  K values: {sorted(os_df['K'].unique())}")
    if 'Seed' in os_df.columns:
        seeds = sorted(os_df['Seed'].unique())
        print(f"  Seeds: {seeds[:10]}... (total: {len(seeds)})")
    print("\nFirst few rows:")
    print(os_df.head())
except Exception as e:
    print(f"Error reading objective_space_run_summary.csv: {e}\n")
