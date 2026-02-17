import pandas as pd
import joblib
import os
import sys
import numpy as np
from scipy.stats import poisson
from logger import PredictionLogger
from team_context import (get_team_data_with_context, get_domestic_league, 
                         fill_missing_stats, get_recent_form, get_h2h, resolve_team_name,
                         get_cl_stats)

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

def predict_final_boss(local=None, visitante=None, h=None, d=None, a=None, match_league=None):
    """
    Sistema de predicción contextual.
    
    Args:
        local (str, optional): Nombre del equipo local
        visitante (str, optional): Nombre del equipo visitante
        h (float, optional): Cuota para el local
        d (float, optional): Cuota para el empate
        a (float, optional): Cuota para el visitante
        match_league (str, optional): Liga del partido (ej: 'CL', 'E0') para contexto
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
        
        # Modelos separados (Mejora #6)
        try:
            m_hs = joblib.load('models/shots_home_model.pkl')
            m_as = joblib.load('models/shots_away_model.pkl')
            m_hst = joblib.load('models/shots_target_home_model.pkl')
            m_ast = joblib.load('models/shots_target_away_model.pkl')
            has_separate_models = True
        except FileNotFoundError:
            has_separate_models = False
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

    # 2. LOCALIZACIÓN POR ROL CON CONTEXTO INTELIGENTE (CAMBIO CLAVE)
    # Buscamos datos considerando:
    # - Si es Champions League, mezcla datos de CL + Liga doméstica
    # - Si es otra liga, usa su contexto doméstico como ayuda
    try:
        if match_league is None:
            # Fallback: detectar liga más común para los equipos
            h_matches = df[df['HomeTeam'] == local]
            a_matches = df[df['AwayTeam'] == visitante]
            if not h_matches.empty:
                match_league = h_matches['Div'].mode()[0]
        
        h_row = get_team_data_with_context(df, local, as_home=True, match_league=match_league)
        a_row = get_team_data_with_context(df, visitante, as_home=False, match_league=match_league)
        
        # Rellenar valores faltantes con datos REALES (no inventados)
        if h_row is not None:
            h_row = fill_missing_stats(h_row, df, local, as_home=True)
        if a_row is not None:
            a_row = fill_missing_stats(a_row, df, visitante, as_home=False)
        
        # INFO: Mostrar si usamos contexto doméstico
        if match_league == 'CL':
            h_domestic = get_domestic_league(local, df)
            a_domestic = get_domestic_league(visitante, df)
            if h_domestic or a_domestic:
                print(f"\n[INFO] Usando contexto de ligas domésticas:")
                if h_domestic:
                    h_dom_name = resolve_team_name(local, df)
                    extra = f" (como '{h_dom_name}')" if h_dom_name != local else ""
                    print(f"   {local}: Champions League + {h_domestic}{extra}")
                if a_domestic:
                    a_dom_name = resolve_team_name(visitante, df)
                    extra = f" (como '{a_dom_name}')" if a_dom_name != visitante else ""
                    print(f"   {visitante}: Champions League + {a_domestic}{extra}")
        
        # FORMA RECIENTE + H2H
        h_form = get_recent_form(df, local, n=5)
        a_form = get_recent_form(df, visitante, n=5)
        h2h = get_h2h(df, local, visitante, n=10)
        
        if h_row is None or a_row is None:
            print("Error: No se encontraron datos para esos equipos.")
            return
    except Exception as e:
        print(f"Error en búsqueda de datos: {str(e)}")
        return

    model_features = m_res.feature_names_in_
    input_dict = {}

    # Helper: obtener valor de una Serie, devolviendo default si es NaN
    def safe_get(row, col, default=0):
        val = row.get(col, default)
        return val if pd.notna(val) else default

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

        # C. Liga como feature (#1)
        elif col == 'is_CL': input_dict[col] = 1 if match_league == 'CL' else 0
        elif col.startswith('is_'): input_dict[col] = 1 if match_league == col[3:] else 0
        
        # D. Días de descanso (#4) - default 4 para CL (entre semana), 7 para doméstica
        elif col == 'home_rest_days': input_dict[col] = 4.0 if match_league == 'CL' else 7.0
        elif col == 'away_rest_days': input_dict[col] = 4.0 if match_league == 'CL' else 7.0

        # E. Datos de Local (Home) y Visitante (Away)
        elif '_Home' in col:
            input_dict[col] = safe_get(h_row, col, 0)
        elif '_Away' in col:
            input_dict[col] = safe_get(a_row, col, 0)
            
        # F. Diferencias y totales (diff_ / exp_)
        elif 'diff_' in col or 'exp_' in col:
            input_dict[col] = safe_get(h_row, col, 0)
        else:
            input_dict[col] = 0.0

    X_in = pd.DataFrame([input_dict])[model_features]
    X_in = X_in.fillna(0)  # Seguro final: ningún NaN llega a los modelos

    # 4. PREDICCIONES
    prob_1x2 = m_res.predict_proba(X_in)[0]
    mu_c = m_corn.predict(X_in)[0]
    mu_s = m_shots.predict(X_in)[0]
    mu_t = m_target.predict(X_in)[0]
    
    # MEJORA #6: Modelos separados para HS/AS/HST/AST
    # Predicen directamente los tiros de cada equipo (no total+share)
    if has_separate_models:
        # Crear X_in compatible con modelos separados
        sep_features = m_hs.feature_names_in_
        sep_dict = {}
        for col in sep_features:
            sep_dict[col] = input_dict.get(col, 0.0)
        X_sep = pd.DataFrame([sep_dict])[sep_features].fillna(0)
        
        mu_hs_direct = m_hs.predict(X_sep)[0]
        mu_as_direct = m_as.predict(X_sep)[0]
        mu_hst_direct = m_hst.predict(X_sep)[0]
        mu_ast_direct = m_ast.predict(X_sep)[0]
    
    # 5. REPARTO DINÁMICO (Usando los nuevos Shares del Preprocessor)
    # Tomamos el share del local en su último partido en casa
    share_c = safe_get(h_row, 'Corner_Share_Home', 0.5)
    share_s = safe_get(h_row, 'Shot_Share_Home', 0.5)
    
    # 5B. AJUSTE CL: Corregir predicciones con promedios reales de CL
    cl_adj_applied = False
    if match_league == 'CL':
        h_cl = get_cl_stats(df, local, as_home=True)
        a_cl = get_cl_stats(df, visitante, as_home=False)
        
        if h_cl and a_cl:
            min_n = min(h_cl['cl_n'], a_cl['cl_n'])
            cl_weight = 0.40 if min_n >= 3 else (0.25 if min_n >= 2 else 0.15)
            model_weight = 1 - cl_weight
            
            cl_total_shots = h_cl['cl_shots'] + a_cl['cl_shots']
            cl_total_target = h_cl['cl_shots_target'] + a_cl['cl_shots_target']
            cl_total_corners = h_cl['cl_corners'] + a_cl['cl_corners']
            
            cl_share_s = h_cl['cl_shots'] / cl_total_shots if cl_total_shots > 0 else 0.5
            cl_share_c = h_cl['cl_corners'] / cl_total_corners if cl_total_corners > 0 else 0.5
            
            mu_s_old = mu_s
            mu_t_old = mu_t
            mu_c_old = mu_c
            
            mu_s = model_weight * mu_s + cl_weight * cl_total_shots
            mu_t = model_weight * mu_t + cl_weight * cl_total_target
            mu_c = model_weight * mu_c + cl_weight * cl_total_corners
            share_s = model_weight * share_s + cl_weight * cl_share_s
            share_c = model_weight * share_c + cl_weight * cl_share_c
            
            # También ajustar modelos separados con CL real
            if has_separate_models:
                mu_hs_direct = model_weight * mu_hs_direct + cl_weight * h_cl['cl_shots']
                mu_as_direct = model_weight * mu_as_direct + cl_weight * a_cl['cl_shots']
                mu_hst_direct = model_weight * mu_hst_direct + cl_weight * h_cl['cl_shots_target']
                mu_ast_direct = model_weight * mu_ast_direct + cl_weight * a_cl['cl_shots_target']
            
            cl_adj_applied = True
            print(f"\n[CL-ADJ] Ajuste Champions ({cl_weight:.0%} CL real, {model_weight:.0%} modelo):")
            print(f"   Tiros totales: {mu_s_old:.1f} → {mu_s:.1f} (CL real: {cl_total_shots:.1f})")
            print(f"   A puerta total: {mu_t_old:.1f} → {mu_t:.1f} (CL real: {cl_total_target:.1f})")
            print(f"   Corners total: {mu_c_old:.1f} → {mu_c:.1f} (CL real: {cl_total_corners:.1f})")
            if has_separate_models:
                print(f"   HS directo: {mu_hs_direct:.1f} | AS directo: {mu_as_direct:.1f}")
                print(f"   HST directo: {mu_hst_direct:.1f} | AST directo: {mu_ast_direct:.1f}")
            print(f"   Datos CL: {local} {h_cl['cl_n']}p(H), {visitante} {a_cl['cl_n']}p(A)")
    
    def get_p(mu, line): return (1 - poisson.cdf(line, mu)) * 100

    # 6. REPORTE VISUAL V2
    print("\n" + "╔" + "═"*55 + "╗")
    print(f"║ ⚽ {local.upper()} vs {visitante.upper()} ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    print(f"║ 1X2: L:{prob_1x2[0]*100:.1f}% | X:{prob_1x2[1]*100:.1f}% | V:{prob_1x2[2]*100:.1f}% ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    
    # FORMA RECIENTE
    h_streak = h_form['form_streak']
    a_streak = a_form['form_streak']
    h_streak_str = f"+{h_streak}W" if h_streak > 0 else (f"{h_streak}L" if h_streak < 0 else "~")
    a_streak_str = f"+{a_streak}W" if a_streak > 0 else (f"{a_streak}L" if a_streak < 0 else "~")
    print(f"║ FORMA (5): {local}: {h_form['form_points']}pts ({h_streak_str}) | {visitante}: {a_form['form_points']}pts ({a_streak_str}) ".ljust(56) + "║")
    
    # HEAD TO HEAD
    if h2h['h2h_matches'] > 0:
        print(f"║ H2H ({h2h['h2h_matches']}p): {local}:{h2h['h2h_wins_a']}W | E:{h2h['h2h_draws']} | {visitante}:{h2h['h2h_wins_b']}W (gol: {h2h['h2h_goals_a']:.1f}-{h2h['h2h_goals_b']:.1f}) ".ljust(56) + "║")
    else:
        print(f"║ H2H: Sin enfrentamientos previos ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    
    # Cálculos individuales
    # ENSEMBLE INTELIGENTE: total+share como base, separados como refinamiento
    # Si los separados están dentro de rango razonable, contribuyen al promedio
    # Si divergen mucho (>40%), se ignoran y se usa solo total+share
    hs_from_total = mu_s * share_s
    as_from_total = mu_s * (1 - share_s)
    hst_from_total = mu_t * share_s
    ast_from_total = mu_t * (1 - share_s)
    
    if has_separate_models:
        def smart_blend(total_val, sep_val, is_cl=False):
            """Mezcla inteligente: usa separado solo si es razonable"""
            if total_val <= 0:
                return sep_val
            ratio = sep_val / total_val if total_val > 0 else 1
            # Si el separado diverge más de 40% del total, ignorarlo
            if ratio < 0.6 or ratio > 1.4:
                return total_val
            # CL: 75% total + 25% separado (total tiene mejor CL-ADJ)
            # Doméstica: 50% total + 50% separado
            w_sep = 0.25 if is_cl else 0.50
            return (1 - w_sep) * total_val + w_sep * sep_val
        
        is_cl = match_league == 'CL'
        hs_final = smart_blend(hs_from_total, mu_hs_direct, is_cl)
        as_final = smart_blend(as_from_total, mu_as_direct, is_cl)
        hst_final = smart_blend(hst_from_total, mu_hst_direct, is_cl)
        ast_final = smart_blend(ast_from_total, mu_ast_direct, is_cl)
    else:
        hs_final = hs_from_total
        as_final = as_from_total
        hst_final = hst_from_total
        ast_final = ast_from_total
    
    data = [
        (f"[HOME] {local}", mu_c * share_c, hs_final, hst_final, 4.5, 11.5, 4.5, h, h_row),
        (f"[AWAY] {visitante}", mu_c * (1-share_c), as_final, ast_final, 3.5, 9.5, 3.5, a, a_row)
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