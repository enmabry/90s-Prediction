import pandas as pd

df = pd.read_csv('data/ChampionsLeague/ChampionsLeague25-26.csv')

# Ver todos los equipos únicos
teams = sorted(set(df['HomeTeam'].tolist() + df['AwayTeam'].tolist()))
print("Equipos en CL CSV:")
for t in teams:
    print(f"  '{t}'")
