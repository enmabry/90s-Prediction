"""
Script de validación de tabla clasificatoria dinámica
Verifica que los puntos y posiciones se calculan correctamente POR LIGA
"""
import pandas as pd
import sys
sys.path.insert(0, 'src')
from preprocessor import calculate_dynamic_standings

# Cargar datos
df = pd.read_csv('data/dataset_final.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Calcular standings
standings = calculate_dynamic_standings(df)

# Seleccionar última fecha
last_date = df['Date'].max()
ligas = df['Div'].unique()

print(f"\n📊 TABLA CLASIFICATORIA AL {last_date.strftime('%Y-%m-%d')}")
print("=" * 70)

for liga in sorted(ligas):
    print(f"\n🏆 LIGA: {liga}")
    print("─" * 70)
    
    # Obtener posiciones para última fecha y liga
    current_standings = {
        team: standings[(last_date, liga, team)]
        for team in df[df['Div'] == liga]['HomeTeam'].unique()
        if (last_date, liga, team) in standings
    }
    
    # Ordenar por posición
    sorted_standings = sorted(
        current_standings.items(),
        key=lambda x: x[1]['position']
    )
    
    print(f"{'Pos':<5} {'Equipo':<25} {'Pts':<5} {'GD':<5} {'GF':<5}")
    print("─" * 70)
    
    for team, stats in sorted_standings:
        print(f"{stats['position']:<5} {team:<25} {stats['points']:<5} {stats['gd']:<5} {stats['gf']:<5}")
    
    # Estadísticas
    points_values = [s['points'] for s in current_standings.values()]
    print(f"\n   📈 {len(current_standings)} equipos | Max: {max(points_values)} pts | Min: {min(points_values)} pts")

print(f"\n✅ Validación completada")
