import sys; sys.path.append('src')
import pandas as pd
df = pd.read_csv('data/dataset_final.csv')
df['Date'] = pd.to_datetime(df['Date'])

league_df = df[df['Div'] == 'D1'].copy()
max_date = league_df['Date'].max()
season_start = max_date - pd.Timedelta(days=365)
league_df = league_df[league_df['Date'] >= season_start]
teams = {}
for _, row in league_df.iterrows():
    ht, at = row['HomeTeam'], row['AwayTeam']
    hg, ag = row.get('FTHG', 0), row.get('FTAG', 0)
    ftr = row.get('FTR', 'D')
    for t in [ht, at]:
        if t not in teams:
            teams[t] = {'points': 0, 'gd': 0}
    if ftr == 'H':
        teams[ht]['points'] += 3
    elif ftr == 'A':
        teams[at]['points'] += 3
    else:
        teams[ht]['points'] += 1
        teams[at]['points'] += 1
    teams[ht]['gd'] += int(hg - ag) if pd.notna(hg) else 0
    teams[at]['gd'] += int(ag - hg) if pd.notna(ag) else 0

sorted_teams = sorted(teams.items(), key=lambda x: (-x[1]['points'], -x[1]['gd']))
print('BUNDESLIGA STANDINGS (ultima temporada):')
for pos, (team, data) in enumerate(sorted_teams, 1):
    marker = ' <---' if team in ['St Pauli', 'Ein Frankfurt'] else ''
    pts = data['points']
    gd = data['gd']
    print(f"  {pos:2d}. {team:<20} {pts:>3d}pts  GD:{gd:>+4d}{marker}")
