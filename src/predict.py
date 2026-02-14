import pandas as pd
import joblib
import os
import sys
import numpy as np
from scipy.stats import poisson
from logger import PredictionLogger

def calcular_kelly(prob_ia, cuota, banca_total=100, instabilidad=0):
    """
    Calcula el monto recomendado usando la fórmula de Kelly Fraccionario.
    
    Args:
        prob_ia (float): Probabilidad estimada por IA (valor entre 0 y 1, ej: 0.62)
        cuota (float): Cuota decimal (ej: 1.85)
        banca_total (float): Capital total disponible (default: 100)
        instabilidad (float): Índice de inestabilidad del equipo (0-2, default: 0)
    
    Returns:
        float: Monto recomendado para apostar (ajustado por inestabilidad)
    """
    # prob_ia: valor entre 0 y 1 (ej: 0.62)
    # cuota: cuota decimal (ej: 1.85)
    # instabilidad: ratio de desv.estándar/media (equipos impredecibles tienen valores altos)
    
    if cuota <= 1:
        return 0
    
    p = prob_ia
    q = 1 - p
    b = cuota - 1
    
    # Fórmula de Kelly: (bp - q) / b
    f_star = (b * p - q) / b
    
    # Aplicamos Kelly Fraccionario (1/4) para reducir volatilidad
    f_frac = f_star * 0.25
    
    if f_frac < 0:
        return 0  # No hay valor
    
    # AJUSTE POR INESTABILIDAD: equipos más volátiles = menor apuesta
    # Si instabilidad > 1, el equipo es muy impredecible
    stability_factor = 1 / (1 + instabilidad * 0.5)  # Factor entre 0.33 y 1
    
    monto_recom = banca_total * f_frac * stability_factor
    return monto_recom

def predict_final_boss(local=None, visitante=None, h=None, d=None, a=None):
    """
    Sistema de predicción contextual.
    
    Args:
        local (str, optional): Nombre del equipo local
        visitante (str, optional): Nombre del equipo visitante
        h (float, optional): Cuota para el local
        d (float, optional): Cuota para el empate
        a (float, optional): Cuota para el visitante
    """
    # 1. Carga de recursos
    try:
        df = pd.read_csv('data/dataset_final.csv')
        # Asegurarse de que la fecha sea datetime para ordenar bien
        df['Date'] = pd.to_datetime(df['Date']) 
        
        m_res = joblib.load('models/result_model.pkl')
        m_corn = joblib.load('models/corners_model.pkl')
        m_shots = joblib.load('models/shots_total_model.pkl')
        m_target = joblib.load('models/shots_target_model.pkl')
    except Exception as e:
        print(f"Error cargando recursos: {e}")
        return
    
    # Inicializar logger
    logger = PredictionLogger('data/prediction_log.xlsx')

    print("\n" + "═"*55)
    print("      SISTEMA DE PREDICCIÓN CONTEXTUAL V2.0")
    print("═"*55)
    
    # --- Si no recibe argumentos, los pide ---
    if local is None or visitante is None:
        # BUSCADOR REPARADO
        busqueda = input("\nBuscar equipo (o Enter para saltar): ").strip()
        if busqueda:
            todos = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
            coincidencias = [e for e in todos if busqueda.lower() in str(e).lower()]
            print(f"Coincidencias: {', '.join(coincidencias)}")

        local = input("\nNombre Local: ") if local is None else local
        visitante = input("Nombre Visitante: ") if visitante is None else visitante
    
    if h is None or d is None or a is None:
        h = float(input("Cuota 1: ") if h is None else h)
        d = float(input("Cuota X: ") if d is None else d)
        a = float(input("Cuota 2: ") if a is None else a)

    # 2. LOCALIZACIÓN POR ROL (CAMBIO CLAVE)
    # Buscamos la última vez que el LOCAL jugó en CASA y el VISITANTE fuera
    try:
        h_row = df[df['HomeTeam'] == local].sort_values('Date').iloc[-1]
        a_row = df[df['AwayTeam'] == visitante].sort_values('Date').iloc[-1]
    except Exception:
        print("Error: No se encontraron datos para esos equipos en esos roles.")
        return

    model_features = m_res.feature_names_in_
    input_dict = {}

    # 3. CONSTRUCCIÓN DEL VECTOR (Compatible con el nuevo Preprocessor)
    sum_inv = (1/h) + (1/d) + (1/a) # Para Market Prob
    
    for col in model_features:
        # A. Probabilidades de Mercado (Nuevas en el Train)
        if 'Market_Prob' in col:
            if '_H' in col: input_dict[col] = (1/h) / sum_inv
            elif '_D' in col: input_dict[col] = (1/d) / sum_inv
            elif '_A' in col: input_dict[col] = (1/a) / sum_inv
        
        # B. Cuotas puras
        elif 'AvgH' in col: input_dict[col] = h
        elif 'AvgD' in col: input_dict[col] = d
        elif 'AvgA' in col: input_dict[col] = a
        elif 'Odds_Std' in col: input_dict[col] = np.std([h, d, a])

        # C. Datos de Local (Home) y Visitante (Away)
        elif '_Home' in col:
            # Si la columna existe en h_row (incluyendo las nuevas _Role y _Opp)
            input_dict[col] = h_row.get(col, 0)
        elif '_Away' in col:
            input_dict[col] = a_row[col] if col in a_row else 0
            
        # D. Diferencias y totales (diff_ / exp_)
        elif 'diff_' in col or 'exp_' in col:
            # Intentamos obtener el valor calculado en el preprocessor del local
            input_dict[col] = h_row.get(col, 0)
        else:
            input_dict[col] = 0.0

    X_in = pd.DataFrame([input_dict])[model_features]

    # 4. PREDICCIONES
    prob_1x2 = m_res.predict_proba(X_in)[0]
    mu_c = m_corn.predict(X_in)[0]
    mu_s = m_shots.predict(X_in)[0]
    mu_t = m_target.predict(X_in)[0]
    
    # 5. REPARTO DINÁMICO (Usando los nuevos Shares del Preprocessor)
    # Tomamos el share del local en su último partido en casa
    share_c = h_row.get('Corner_Share_Home', 0.5)
    share_s = h_row.get('Shot_Share_Home', 0.5)
    
    def get_p(mu, line): return (1 - poisson.cdf(line, mu)) * 100

    # 6. REPORTE VISUAL V2
    print("\n" + "╔" + "═"*55 + "╗")
    print(f"║ ⚽ {local.upper()} vs {visitante.upper()} ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    print(f"║ 1X2: L:{prob_1x2[0]*100:.1f}% | X:{prob_1x2[1]*100:.1f}% | V:{prob_1x2[2]*100:.1f}% ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    
    # Cálculos individuales
    # Local: mu * share | Visitante: mu * (1 - share)
    data = [
        (f"[HOME] {local}", mu_c * share_c, mu_s * share_s, mu_t * share_s, 4.5, 11.5, 4.5, h, h_row),
        (f"[AWAY] {visitante}", mu_c * (1-share_c), mu_s * (1-share_s), mu_t * (1-share_s), 3.5, 9.5, 3.5, a, a_row)
    ]

    for i, (name, cm, sm, tm, l_c, l_s, l_t, cuota_mercado, row_data) in enumerate(data):
        print(f"║ [STATS] {name.upper()}")
        print(f"║    CORNERS (Est: {cm:.1f}) -> +{l_c}: {get_p(cm, l_c):.1f}%")
        print(f"║    TIROS   (Est: {sm:.1f}) -> +{l_s}: {get_p(sm, l_s):.1f}%")
        print(f"║    A PUERTA(Est: {tm:.1f}) -> +{l_t}: {get_p(tm, l_t):.1f}%")
        
        # Cálculo de Kelly para Corners (con factor de inestabilidad)
        prob_ia_decimal = get_p(cm, l_c) / 100
        instabilidad = row_data.get('avg_instability_Home' if i == 0 else 'avg_instability_Away', 0)
        instabilidad = float(instabilidad) if pd.notna(instabilidad) else 0
        
        recomendacion = calcular_kelly(prob_ia_decimal, cuota_mercado, instabilidad=instabilidad)
        
        # Registrar en logger
        equipo = local if i == 0 else visitante
        logger.log_prediction(
            date_pred=str(pd.Timestamp.now().date()),
            home_team=local,
            away_team=visitante,
            event_type=f'Corners +{l_c}',
            over_line=l_c,
            prob_ia=prob_ia_decimal,
            cuota=cuota_mercado,
            kelly_amount=recomendacion,
            instability_score=instabilidad,
            notes=f'Equipo: {equipo}'
        )
        
        if recomendacion > 0:
            print(f"\u2551 [VALUE] Apostar {recomendacion:.2f}€ (inestabilidad: {instabilidad:.2f})")
        
        if i == 0: print("╟" + "─"*55 + "╢")
    print("╚" + "═"*55 + "╝")
    
    # Guardar predicciones en Excel
    logger.save_predictions()
    print(f"\n[OK] Predicción guardada en data/prediction_log.xlsx")

if __name__ == "__main__":
    # Permite recibir argumentos: python predict.py "Barcelona" "Valencia" "1.85" "3.75" "4.20"
    # O ejecutar sin argumentos para modo interactivo
    
    if len(sys.argv) >= 3:
        local = sys.argv[1]
        visitante = sys.argv[2]
        h = float(sys.argv[3]) if len(sys.argv) > 3 else None
        d = float(sys.argv[4]) if len(sys.argv) > 4 else None
        a = float(sys.argv[5]) if len(sys.argv) > 5 else None
        predict_final_boss(local, visitante, h, d, a)
    else:
        predict_final_boss()