import os
import pandas as pd

# Check output directory structure
output_dir = r"output"
for root, dirs, files in os.walk(output_dir):
    level = root.replace(output_dir, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        file_path = os.path.join(root, file)
        try:
            if file.endswith('.csv'):
                df = pd.read_csv(file_path)
                print(f'{subindent}{file} ({df.shape[0]} rows, {df.shape[1]} cols)')
                if 'K' in df.columns:
                    print(f'{subindent}  -> K values: {sorted(df["K"].unique())}')
                    if 'Seed' in df.columns or 'seed' in df.columns:
                        seed_col = 'Seed' if 'Seed' in df.columns else 'seed'
                        print(f'{subindent}  -> Seeds found: {sorted(df[seed_col].unique())[:10]}...')
            else:
                print(f'{subindent}{file}')
        except Exception as e:
            print(f'{subindent}{file} (unable to read: {str(e)[:30]})')
