import pandas as pd
df = pd.read_csv('data.csv')
pd.DataFrame({'variable':['value'], 'n':[len(df)], 'mean':[df.value.mean()], 'sd':[df.value.std()]}).to_csv('script_summary.csv', index=False)
