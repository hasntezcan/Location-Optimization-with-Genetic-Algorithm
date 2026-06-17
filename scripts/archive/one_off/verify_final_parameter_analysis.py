import pandas as pd
path = r'output\parameter_analysis_final\parameter_analysis_results.csv'
df = pd.read_csv(path)
print('rows=', len(df))
print('K unique=', sorted(df['K'].unique()))
sub = df[(df['K'] == 5) & (df['GA_ID'] == 'GA18')]
print('K=5 GA_ID=GA18 rows=', len(sub))
print('Best_f1 sample=', sub['Best_f1'].head().tolist())
print('Mean_f1 sample=', sub['Mean_f1'].head().tolist())
