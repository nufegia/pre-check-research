import pandas as pd

df = pd.read_csv("outcomes.csv").dropna()
print(df.groupby("group")["response"].mean())
