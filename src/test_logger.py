import pandas as pd
import os
sys = __import__('sys')
sys.path.insert(0, 'src')
from logger import PredictionLogger

# Crear logger y registrar predicciones de prueba
logger = PredictionLogger('data/prediction_log.xlsx')

predicciones_test = [
    {
        'home': 'Barcelona', 'away': 'Real Madrid', 'event': 'Corners +4.5',
        'prob': 0.65, 'cuota': 1.85, 'kelly': 12.50, 'inestabilidad': 0.45
    },
    {
        'home': 'Barcelona', 'away': 'Real Madrid', 'event': 'Shots +11.5',
        'prob': 0.58, 'cuota': 1.80, 'kelly': 10.20, 'inestabilidad': 0.38
    },
]

for pred in predicciones_test:
    logger.log_prediction(
        date_pred='2026-02-14',
        home_team=pred['home'],
        away_team=pred['away'],
        event_type=pred['event'],
        over_line=float(pred['event'].split('+')[1]),
        prob_ia=pred['prob'],
        cuota=pred['cuota'],
        kelly_amount=pred['kelly'],
        instability_score=pred['inestabilidad'],
        notes='Prueba de logger'
    )

logger.save_predictions()
print("✅ Predicciones guardadas en data/prediction_log.xlsx")

# Verificar
if os.path.exists('data/prediction_log.xlsx'):
    df = pd.read_excel('data/prediction_log.xlsx')
    print(f"\n✓ Archivo creado con {len(df)} predicciones")
    print(df.head())
