"""
Script para predicción de partidos de Champions League
"""
import sys
sys.path.insert(0, 'src')
from predict import predict_final_boss

# Atalanta vs Bayern Munich - Octavos Champions League
# Cuotas reales: Atalanta 4.75, Empate 4.50, Bayern 1.61

print("\n" + "="*70)
print("         ATALANTA vs BAYERN MUNICH - CHAMPIONS LEAGUE")
print("="*70)

predict_final_boss(
    local="Atalanta",
    visitante="Bayern Munich",
    h=4.75,      # Atalanta
    d=4.50,      # Empate
    a=1.61,      # Bayern
    match_league='CL',
    h2h_weight=0.7  # Champions League: menos peso a H2H directo
)
