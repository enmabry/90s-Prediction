"""
Script de validación de dataset híbrido
"""
import pandas as pd
import sys
sys.path.insert(0, 'src')

df = pd.read_csv('data/dataset_final.csv')
df['Date'] = pd.to_datetime(df['Date'])

print("\n=== DATASET HIBRIDO (MEMORIA + EWM) ===\n")
print(f"Total partidos: {len(df)}")
print(f"Rango de fechas: {df['Date'].min().date()} a {df['Date'].max().date()}")
print(f"Ligas: {', '.join(df['Div'].unique())}")
print(f"Equipos únicos: {df['HomeTeam'].nunique()}")

print(f"\nColumnas de Recencia Temporal:")
print(f"  - days_since_match: {df['days_since_match'].min():.0f} a {df['days_since_match'].max():.0f} días")
print(f"  - temporal_weight: {df['temporal_weight'].min():.3f} a {df['temporal_weight'].max():.3f}")

print(f"\nEWM en acción (últimos 5 partidos del dataset):")
cols_sample = ['HomeTeam', 'AwayTeam', 'rolling_C_5_Home', 'rolling_C_5_Away']
print(df[cols_sample].tail())

print(f"\nVerificacion de tablas por liga:")
for liga in df['Div'].unique():
    count = len(df[df['Div'] == liga])
    print(f"  {liga}: {count} partidos")

print("\n✓ Dataset listo para entrenamiento con memoria histórica + sensibilidad actual")
