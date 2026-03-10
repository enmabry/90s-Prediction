"""
Comparación de predicciones con diferentes pesos de H2H
"""
import sys
sys.path.append('src')
from predict import predict_final_boss

print("="*70)
print("  COMPARACIÓN: St Pauli vs Eintracht Frankfurt")
print("  Diferentes pesos de H2H para balancear vs forma actual")
print("="*70)

# Cuotas del mercado: St Pauli 5.20, Empate 4.00, Eintracht 1.65
local, visitante = "St Pauli", "Ein Frankfurt"
h, d, a = 5.20, 4.00, 1.65
league = "D1"

print("\n\n" + "="*70)
print("  ESCENARIO 1: H2H NORMAL (peso 100% - default)")
print("="*70)
predict_final_boss(local, visitante, h, d, a, league, h2h_weight=1.0)

print("\n\n" + "="*70)
print("  ESCENARIO 2: H2H REDUCIDO (peso 50%)")
print("="*70)
predict_final_boss(local, visitante, h, d, a, league, h2h_weight=0.5)

print("\n\n" + "="*70)
print("  ESCENARIO 3: H2H MINIMO (peso 30% - forma reciente domina)")
print("="*70)
predict_final_boss(local, visitante, h, d, a, league, h2h_weight=0.3)

print("\n\n" + "="*70)
print("  RESUMEN")
print("="*70)
print("""
¿CUÁNDO USAR QUÉ PESO?

• h2h_weight=1.0 (Default)
  - Cuando los equipos no han cambiado mucho
  - Cuando el H2H es reciente (<2 años)
  - Cuando los planteles son estables

• h2h_weight=0.5 (Balanceado)
  - Cuando uno de los equipos mejoró/empeoró significativamente
  - Cuando hay cambios de entrenador recientes
  - Cuando la forma actual contradice el H2H

• h2h_weight=0.3 (Forma actual)
  - Cuando el H2H es antiguo (>2-3 años)
  - Cuando uno de los equipos recién ascendió/descendió
  - Cuando la forma reciente es MUY diferente al histórico
  
NOTA: El sistema ahora confía 75% en el modelo puro y 25% en el mercado,
      por lo que será más sensible a estos cambios.
""")
