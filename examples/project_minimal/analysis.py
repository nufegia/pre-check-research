import pandas as pd

df = pd.read_csv("data.csv").dropna()
print(df.groupby("group")["value"].mean())
