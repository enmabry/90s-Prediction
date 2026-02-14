import pandas as pd
import glob
import os

path = os.path.join('data', '**', '*.csv')
files = [f for f in glob.glob(path, recursive=True) 
         if 'dataset_final.csv' not in f and '25-26' in f]

for f in files:
    print(f"\n📄 {f}")
    temp = pd.read_csv(f, encoding='unicode_escape', nrows=1)
    cols = temp.columns.tolist()
    print(f"Columnas: {len(cols)}")
    print(f"'Div' presente: {'Div' in cols}")
    if 'Div' in cols:
        print(f"Valor de Div: {temp['Div'].values[0]}")
