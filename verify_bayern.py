import pandas as pd

df = pd.read_csv('data/dataset_final.csv')

# Últimos 10 partidos del Bayern (como local o visitante)
bayern_home = df[df['HomeTeam'] == 'Bayern Munich'].tail(10)[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HS', 'AS', 'HST', 'AST']].copy()
bayern_away = df[df['AwayTeam'] == 'Bayern Munich'].tail(10)[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HS', 'AS', 'HST', 'AST']].copy()

print('='*70)
print('ÚLTIMOS PARTIDOS DEL BAYERN MUNICH (LOCAL)')
print('='*70)
print(bayern_home.to_string())

print('\n' + '='*70)
print('ÚLTIMOS PARTIDOS DEL BAYERN MUNICH (VISITANTE)')
print('='*70)
print(bayern_away.to_string())

# Estadísticas
print('\n' + '='*70)
print('ESTADÍSTICAS DEL BAYERN')
print('='*70)
print(f'Tiros totales (local): {bayern_home["HS"].mean():.1f}')
print(f'Tiros a puerta (local): {bayern_home["HST"].mean():.1f}')
print(f'Tiros totales (visitante): {bayern_away["AS"].mean():.1f}')
print(f'Tiros a puerta (visitante): {bayern_away["AST"].mean():.1f}')
print(f'\nPromedio GENERAL visitante: {bayern_away["AS"].mean():.1f} tiros, {bayern_away["AST"].mean():.1f} a puerta')
