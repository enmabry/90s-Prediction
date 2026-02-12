import pandas as pd
import joblib
import os
import numpy as np
from scipy.stats import poisson

def predict_final_boss():
    # 1. Carga de recursos
    try:
        df = pd.read_csv('data/dataset_final.csv')
        m_res = joblib.load('models/result_model.pkl')
        m_corn = joblib.load('models/corners_model.pkl')
        m_shots = joblib.load('models/shots_total_model.pkl')
        m_target = joblib.load('models/shots_target_model.pkl')
    except Exception as e:
        print(f"Error: {e}")
        return

    print("\n" + "═"*55)
    print("      SISTEMA DE PREDICCIÓN CONTEXTUAL V1.0")
    print("═"*55)
    
    # --- AYUDA PARA EL USUARIO ---
    print("\n[?] ¿No sabes el nombre exacto? Escribe una parte del nombre para buscarlo.")
    busqueda = input("Buscar equipo (o pulsa Enter para saltar): ").strip()
    if busqueda:
        coincidencias = df[df['HomeTeam'].str.contains(busqueda, case=False, na=False)]['HomeTeam'].unique().tolist()
        if coincidencias:
            print(f"Equipos encontrados: {', '.join(coincidencias)}")
        else:
            print(f"No se encontraron equipos con '{busqueda}'")
    # -----------------------------
    
    local = input("Local: ")
    visitante = input("Visitante: ")
    h, d, a = float(input("Cuota 1: ")), float(input("Cuota X: ")), float(input("Cuota 2: "))

    # 2. Localizar registros
    h_row = df[(df['HomeTeam']==local) | (df['AwayTeam']==local)].sort_values('Date').iloc[-1]
    a_row = df[(df['HomeTeam']==visitante) | (df['AwayTeam']==visitante)].sort_values('Date').iloc[-1]
    
    model_features = m_res.feature_names_in_
    input_dict = {}

    def get_val(row, base_name):
        # Busca cualquier columna que contenga el nombre base
        for col in row.index:
            if base_name in col:
                return row[col]
        return 0.0

    for col in model_features:
        # Extraer métrica base (ej: rolling_Shots_5)
        base = col.replace('_Home', '').replace('_Away', '').replace('_Vs', '')
        
        if '_Home' in col:
            # Si es 'Vs', necesitamos la defensa del VISITANTE para el ataque del LOCAL
            source = a_row if '_Vs' in col else h_row
            input_dict[col] = get_val(source, base)
        elif '_Away' in col:
            # Si es 'Vs', necesitamos la defensa del LOCAL para el ataque del VISITANTE
            source = h_row if '_Vs' in col else a_row
            input_dict[col] = get_val(source, base)
        else:
            # Cuotas y especiales
            if col == 'AvgH': input_dict[col] = h
            elif col == 'AvgD': input_dict[col] = d
            elif col == 'AvgA': input_dict[col] = a
            elif 'diff_Shots' in col:
                s_h = get_val(h_row, 'rolling_Shots_5')
                s_a = get_val(a_row, 'rolling_Shots_5')
                input_dict[col] = s_h - s_a
            elif 'exp_Total_Corners' in col:
                c_h = get_val(h_row, 'rolling_Corners_5')
                c_a = get_val(a_row, 'rolling_Corners_5')
                input_dict[col] = c_h + c_a
            else:
                input_dict[col] = 0.0

    X_in = pd.DataFrame([input_dict])[model_features]

    # 3. Predicciones
    prob_1x2 = m_res.predict_proba(X_in)[0]
    mu_c = m_corn.predict(X_in)[0]
    mu_s = m_shots.predict(X_in)[0]
    mu_t = m_target.predict(X_in)[0]
    
    # 4. Desglose con "Shares"
    # Buscamos el ratio de participación en corners y tiros
    c_h = get_val(h_row, 'rolling_Corner_Share_5')
    c_a = get_val(a_row, 'rolling_Corner_Share_5')
    c_ratio = c_h / (c_h + c_a) if (c_h + c_a) > 0 else 0.5
    
    s_h = get_val(h_row, 'rolling_Shot_Share_5')
    s_a = get_val(a_row, 'rolling_Shot_Share_5')
    s_ratio = s_h / (s_h + s_a) if (s_h + s_a) > 0 else 0.5
    
    def get_p(mu, line): return (1 - poisson.cdf(line, mu)) * 100

    # 5. Reporte Visual
    print("\n" + "╔" + "═"*55 + "╗")
    print(f"║ ⚽ {local.upper()} vs {visitante.upper()} ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    print(f"║ 1X2: L:{prob_1x2[0]*100:.1f}% | X:{prob_1x2[1]*100:.1f}% | V:{prob_1x2[2]*100:.1f}% ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    
    # Equipos y sus Lambdas desglosados
    data = [
        (local, mu_c * c_ratio, mu_s * s_ratio, mu_t * s_ratio),
        (visitante, mu_c * (1-c_ratio), mu_s * (1-s_ratio), mu_t * (1-s_ratio))
    ]

    for name, cm, sm, tm in data:
        print(f"║ 📊 {name.upper()}")
        print(f"║    CORNERS (Est: {cm:.1f}) -> +3.5: {get_p(cm, 3.5):.1f}% | +5.5: {get_p(cm, 5.5):.1f}%")
        print(f"║    TIROS   (Est: {sm:.1f}) -> +10.5: {get_p(sm, 10.5):.1f}% | +13.5: {get_p(sm, 13.5):.1f}%")
        print(f"║    A PUERTA(Est: {tm:.1f}) -> +3.5: {get_p(tm, 3.5):.1f}% | +5.5: {get_p(tm, 5.5):.1f}%")
        if name == local: print("╟" + "─"*55 + "╢")
    print("╚" + "═"*55 + "╝")

if __name__ == "__main__":
    predict_final_boss()