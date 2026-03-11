"""
Normaliza nombres de equipos en el CSV de Champions League,
unificando los nombres que vienen de la API con los nombres
canónicos existentes en el dataset.
"""
import pandas as pd

# Mapa de normalización: nombre API → nombre canónico
NORMALIZE = {
    'AFC Ajax': 'Ajax',
    'AS Monaco': 'Monaco',
    'Bayer 04 Leverkusen': 'Leverkusen',
    'FC Bayern München': 'Bayern Munich',
    'Club Brugge KV': 'Club Brugge',
    'Borussia Dortmund': 'Dortmund',
    'FC København': 'FC Copenhagen',
    'Kairat Almaty': 'FC Kairat',
    'Olympiacos FC': 'Olympiacos',
    'Olympique de Marseille': 'Marseille',
    'PSV Eindhoven': 'PSV',
    'Qarabağ FK': 'Qarabağ',
    'Royale Union Saint-Gilloise': 'Union SG',
    'SK Slavia Praha': 'Slavia Prague',
}

csv_path = 'data/ChampionsLeague/ChampionsLeague25-26.csv'
df = pd.read_csv(csv_path)

print(f"Partidos antes: {len(df)}")

# Aplicar normalización
df['HomeTeam'] = df['HomeTeam'].replace(NORMALIZE)
df['AwayTeam'] = df['AwayTeam'].replace(NORMALIZE)

# Deduplicar por si hay duplicados tras la normalización
df_clean = df.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'], keep='last')

# Verificar equipos únicos
teams = sorted(set(df_clean['HomeTeam'].tolist() + df_clean['AwayTeam'].tolist()))
print(f"\nPartidos despues: {len(df_clean)}")
print(f"\nEquipos unicos ({len(teams)}):")
for t in teams:
    print(f"  {t}")

df_clean.to_csv(csv_path, index=False)
print(f"\nGuardado: {csv_path}")
