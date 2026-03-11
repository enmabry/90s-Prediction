import pandas as pd
df = pd.read_csv('data/ChampionsLeague/ChampionsLeague25-26.csv')
print(f'Total partidos CL: {len(df)}')
print(f'Fechas desde: {df["Date"].min()} hasta: {df["Date"].max()}')
print('\nUltimos 10 partidos:')
print(df.tail(10)[['Date','HomeTeam','AwayTeam','FTHG','FTAG','HST','AST']].to_string())
print('\nPartidos por fecha:')
print(df['Date'].value_counts().sort_index().to_string())
