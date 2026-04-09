import pandas as pd

df = pd.read_csv('mixed_4hour_metrics.csv')
print(f'Rows: {len(df)}')
print(f'Columns: {df.columns.tolist()}')
print(f'\nClass distribution:')
print(df['sla_violated'].value_counts())
print(f'\nPositive class %: {df["sla_violated"].sum() / len(df) * 100:.2f}%')
print(f'\nServices: {df["service"].unique()}')
