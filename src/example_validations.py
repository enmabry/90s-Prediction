"""
EJEMPLO: Cómo registrar validaciones del Sistema V2.0 en el logger
Comparativa Técnica: Predicciones IA vs Realidad
"""

from logger import PredictionLogger

def register_bundesliga_validations():
    """
    Registra las validaciones del ejemplo que proporcionaste:
    W. Bremen vs Bayern
    Hoffenheim vs Freiburg
    St. Pauli vs Leipzig
    Stuttgart vs Colonia
    Leverkusen vs St Pauli
    """
    
    logger = PredictionLogger(log_file="data/prediction_log.xlsx")
    
    print("[LOGGER] Registrando validaciones del Sistema V2.0...\n")
    
    # ======================== PARTIDO 1 ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='W. Bremen',
        away_team='Bayern',
        event_type='Shots',
        selection='Bremen +11.5 Remates',
        prediction_value=18.4,
        actual_value=14.0,
        precision=0.76,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 2 ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='Hoffenheim',
        away_team='Freiburg',
        event_type='Shots',
        selection='Freiburg +9.5 Remates',
        prediction_value=14.1,
        actual_value=10.0,
        precision=0.71,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 3 ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='St. Pauli',
        away_team='Leipzig',
        event_type='Shots',
        selection='St. Pauli +5.5 Remates',
        prediction_value=10.4,
        actual_value=11.0,
        precision=0.94,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 4A ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='Stuttgart',
        away_team='Colonia',
        event_type='Shots',
        selection='Stuttgart +11.5 Remates',
        prediction_value=14.9,
        actual_value=13.0,
        precision=0.87,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 4B ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='Stuttgart',
        away_team='Colonia',
        event_type='Shots on Target',
        selection='Stuttgart +3.5 a Puerta',
        prediction_value=5.8,
        actual_value=4.0,
        precision=0.69,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 4C ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='Colonia',
        away_team='Stuttgart',
        event_type='Shots',
        selection='Colonia +9.5 Remates',
        prediction_value=12.2,
        actual_value=10.0,
        precision=0.82,
        notes='Sistema V2.0 - Bundesliga'
    )
    
    # ======================== PARTIDO 5 ========================
    logger.log_validation(
        date_match='2026-02-15',
        home_team='Leverkusen',
        away_team='St. Pauli',
        event_type='1X2 Result',
        selection='Victoria Leverkusen',
        prediction_value=68.2,  # Probabilidad 68.2%
        actual_value=100.0,     # Ganó 3-0
        precision=1.0,
        notes='Sistema V2.0 - Resultado acertado 100%'
    )
    
    # Guardar todas las validaciones
    logger.save_validations(sheet_name='Validations')
    print("[OK] Validaciones guardadas en data/prediction_log.xlsx\n")
    
    # Mostrar resumen
    PredictionLogger.print_validation_summary(log_file="data/prediction_log.xlsx", sheet_name='Validations')

if __name__ == "__main__":
    register_bundesliga_validations()
    
    print("\n[TIP] Para agregar más validaciones, usa:")
    print("  logger = PredictionLogger()")
    print("  logger.log_validation(...)")
    print("  logger.save_validations()")
