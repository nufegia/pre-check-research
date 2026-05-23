import pandas as pd
df = pd.read_csv('project/data.csv').dropna()
sig = df[df['p'] < 0.05] if 'p' in df else df
print('rows', len(sig))
