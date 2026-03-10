"""
Script de test para comparar predicciones ANTES vs DESPUÉS de las mejoras
"""
import sys
sys.path.append('src')
from predict import predict_final_boss

print("="*70)
print("  TEST: St Pauli vs Eintracht Frankfurt")
print("="*70)

# Caso de prueba: St Pauli vs Eintracht Frankfurt
# Cuotas hipotéticas: St Pauli 5.20 (local), Empate 4.00, Eintracht 1.65 (visitante)
# Estas cuotas indican que el mercado favorece mucho a Eintracht

predict_final_boss(
    local="St Pauli",
    visitante="Ein Frankfurt",
    h=5.20,
    d=4.00,
    a=1.65,
    match_league="D1"  # Bundesliga
)

print("\n" + "="*70)
print("  INTERPRETACIÓN:")
print("="*70)
print("""
MEJORAS APLICADAS:
1. ✅ Temperature scaling: 1.5 → 1.2 (más confianza en el modelo)
2. ✅ Mezcla: 60% modelo + 40% mercado → 75% modelo + 25% mercado
3. ✅ Debug info: muestra probabilidades RAW del modelo
4. ✅ Alerta H2H: detecta cuando histórico domina demasiado

RESULTADO ESPERADO:
- Probabilidades más balanceadas vs antes
- El modelo ahora debe confiar más en forma reciente y stats
- Si H2H sigue dominando, veremos la alerta ⚠️
""")
