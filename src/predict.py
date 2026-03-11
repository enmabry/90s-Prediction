import pandas as pd
import joblib
import os
import sys
import numpy as np
from scipy.stats import poisson
from logger import PredictionLogger
from team_context import (get_team_data_with_context, get_domestic_league,
                         fill_missing_stats, get_recent_form, get_h2h, resolve_team_name,
                         get_cl_stats, get_league_role_stats)

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

def predict_final_boss(local=None, visitante=None, h=None, d=None, a=None, match_league=None, h2h_weight=1.0):
    """
    Sistema de predicción contextual.
    
    Args:
        local (str, optional): Nombre del equipo local
        visitante (str, optional): Nombre del equipo visitante
        h (float, optional): Cuota para el local
        d (float, optional): Cuota para el empate
        a (float, optional): Cuota para el visitante
        match_league (str, optional): Liga del partido (ej: 'CL', 'E0') para contexto
        h2h_weight (float, optional): Factor para atenuar H2H (0.0=ignorar, 1.0=normal, 0.5=reducir 50%)
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
            # Auto-detectar CL solo si los equipos son de LIGAS DOMÉSTICAS DISTINTAS
            # (ej: Bayern vs Barcelona → CL; Liverpool vs Man City → E0, no CL)
            h_cl_games = df[(df['is_CL'] == 1) & ((df['HomeTeam'] == local) | (df['AwayTeam'] == local))]
            a_cl_games = df[(df['is_CL'] == 1) & ((df['HomeTeam'] == visitante) | (df['AwayTeam'] == visitante))]
            if len(h_cl_games) >= 2 and len(a_cl_games) >= 2:
                # Verificar si los equipos tienen la MISMA liga doméstica
                h_dom = get_domestic_league(local, df)
                a_dom = get_domestic_league(visitante, df)
                if h_dom and a_dom and h_dom != a_dom:
                    # Diferentes ligas domésticas → probablemente CL
                    match_league = 'CL'
                elif not h_matches.empty:
                    match_league = h_matches['Div'].mode()[0]
            elif not h_matches.empty:
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
        # A. Probabilidades de Mercado
        if 'Market_Prob' in col:
            if '_H' in col: input_dict[col] = (1/h) / sum_inv
            elif '_D' in col: input_dict[col] = (1/d) / sum_inv
            elif '_A' in col: input_dict[col] = (1/a) / sum_inv
        
        # B. Cuotas puras
        elif 'AvgH' in col: input_dict[col] = h
        elif 'AvgD' in col: input_dict[col] = d
        elif 'AvgA' in col: input_dict[col] = a
        elif 'Odds_Std' in col: input_dict[col] = np.std([h, d, a])

        # C. Liga como feature
        elif col == 'is_CL': input_dict[col] = 1 if match_league == 'CL' else 0
        elif col.startswith('is_'): input_dict[col] = 1 if match_league == col[3:] else 0
        
        # D. Días de descanso — 4 para CL (entre semana), 7 para doméstica
        elif col == 'home_rest_days': input_dict[col] = 4.0 if match_league == 'CL' else 7.0
        elif col == 'away_rest_days': input_dict[col] = 4.0 if match_league == 'CL' else 7.0

        # E. H2H features — CONSOLIDADO: solo H2H_Dominance
        # Rango: -1 (visitante domina) a +1 (local domina)
        elif col == 'H2H_Dominance':
            h2h_n = h2h.get('h2h_matches', 0)
            if h2h_n > 0:
                dominance = (h2h.get('h2h_wins_a', 0) - h2h.get('h2h_wins_b', 0)) / h2h_n
                input_dict[col] = dominance * h2h_weight
            else:
                input_dict[col] = 0
        elif col.startswith('H2H_'):
            # Legacy: si el modelo aún tiene features H2H viejas (compatibilidad)
            h2h_n = h2h.get('h2h_matches', 0)
            if col == 'H2H_Total': input_dict[col] = h2h_n * h2h_weight
            elif col == 'H2H_Draws': input_dict[col] = h2h.get('h2h_draws', 0) * h2h_weight
            elif col == 'H2H_Home_Wins': input_dict[col] = h2h.get('h2h_wins_a', 0) * h2h_weight
            elif col == 'H2H_Away_Wins': input_dict[col] = h2h.get('h2h_wins_b', 0) * h2h_weight
            elif col == 'H2H_Home_Win_Rate': input_dict[col] = (h2h.get('h2h_wins_a', 0) / max(h2h_n, 1)) * h2h_weight
            elif col == 'H2H_Away_Win_Rate': input_dict[col] = (h2h.get('h2h_wins_b', 0) / max(h2h_n, 1)) * h2h_weight
            else: input_dict[col] = 0

        # F. Datos HOME (Home_ prefix + _Home suffix)
        elif col.startswith('Home') or '_Home' in col:
            input_dict[col] = safe_get(h_row, col, 0)
        
        # G. Datos AWAY (Away_ prefix + _Away suffix)
        elif col.startswith('Away') or '_Away' in col:
            input_dict[col] = safe_get(a_row, col, 0)
        
        # H. Features con indicador home/away en minúsculas (opponent_*_home, etc.)
        elif 'home' in col.lower():
            input_dict[col] = safe_get(h_row, col, 0)
        elif 'away' in col.lower():
            input_dict[col] = safe_get(a_row, col, 0)
            
        # I. Diferencias y totales (diff_ / exp_)
        elif 'diff_' in col or 'exp_' in col:
            input_dict[col] = safe_get(h_row, col, 0)
        
        # J. Fallback: intentar desde h_row (temporal_weight, Points_Diff, etc.)
        else:
            input_dict[col] = safe_get(h_row, col, 0.0)

    # ═══════════════════════════════════════════════════════════════════
    # RECÁLCULO DE FEATURES CRUZADAS (dependen de AMBOS equipos)
    # Las features cruzadas en h_row/a_row son del ÚLTIMO partido de cada
    # equipo contra un rival DISTINTO. Aquí las recalculamos para el 
    # matchup ACTUAL (local vs visitante).
    # ═══════════════════════════════════════════════════════════════════
    
    # Extraer rolling stats de cada equipo (datos per-team, estos SÍ son correctos)
    rs_h = safe_get(h_row, 'rolling_S_5_Home', 10)    # Tiros local
    rs_a = safe_get(a_row, 'rolling_S_5_Away', 10)    # Tiros visitante
    rc_h = safe_get(h_row, 'rolling_C_5_Home', 5)     # Corners local
    rc_a = safe_get(a_row, 'rolling_C_5_Away', 5)     # Corners visitante
    rst_h = safe_get(h_row, 'rolling_ST_5_Home', 4)   # Tiros a puerta local
    rst_a = safe_get(a_row, 'rolling_ST_5_Away', 4)   # Tiros a puerta visitante
    ros_h = safe_get(h_row, 'rolling_OppS_5_Home', 10)   # Tiros que RECIBE el local
    ros_a = safe_get(a_row, 'rolling_OppS_5_Away', 10)   # Tiros que RECIBE el visitante
    roc_h = safe_get(h_row, 'rolling_OppC_5_Home', 5)    # Corners que RECIBE local
    roc_a = safe_get(a_row, 'rolling_OppC_5_Away', 5)    # Corners que RECIBE visitante
    rost_h = safe_get(h_row, 'rolling_OppST_5_Home', 4)  # Tiros a puerta que RECIBE local
    rost_a = safe_get(a_row, 'rolling_OppST_5_Away', 4)  # Tiros a puerta que RECIBE visitante
    rs_role_h = safe_get(h_row, 'rolling_S_5_Role_Home', rs_h)
    rs_role_a = safe_get(a_row, 'rolling_S_5_Role_Away', rs_a)
    
    # --- PASO 6: Defense Fatigue (cruzar ofensiva vs defensa del RIVAL ACTUAL) ---
    # Shot Advantage: mis tiros vs lo que concede EL RIVAL ACTUAL
    cross_fixes = {}
    cross_fixes['Home_vs_Away_Shot_Advantage'] = (rs_h - ros_a) / 2
    cross_fixes['Away_vs_Home_Shot_Advantage'] = (rs_a - ros_h) / 2
    # Match Shot Expectancy: promedio de mi ataque + defensa del rival actual
    cross_fixes['Match_Shot_Expectancy_Home'] = (rs_h + ros_a) / 2
    cross_fixes['Match_Shot_Expectancy_Away'] = (rs_a + ros_h) / 2
    cross_fixes['Match_Corner_Expectancy_Home'] = (rc_h + roc_a) / 2
    cross_fixes['Match_Corner_Expectancy_Away'] = (rc_a + roc_h) / 2
    # Defense Efficiency
    cross_fixes['Home_Defense_Efficiency'] = (rost_h + 0.1) / (ros_h + 0.1)
    cross_fixes['Away_Defense_Efficiency'] = (rost_a + 0.1) / (ros_a + 0.1)
    
    # --- PASO 7: Position Gap (usar posiciones ACTUALES de la tabla) ---
    # Buscar posiciones actuales de ambos equipos en la liga
    def get_current_standings(df, league):
        """Calcula standings actuales desde los datos del dataset"""
        league_df = df[df['Div'] == league].copy()
        if league_df.empty:
            return {}
        # Usar solo la temporada más reciente (últimos 12 meses)
        max_date = league_df['Date'].max()
        season_start = max_date - pd.Timedelta(days=365)
        league_df = league_df[league_df['Date'] >= season_start]
        
        teams = {}
        for _, row in league_df.iterrows():
            ht, at = row['HomeTeam'], row['AwayTeam']
            hg, ag = row.get('FTHG', 0), row.get('FTAG', 0)
            ftr = row.get('FTR', 'D')
            for t in [ht, at]:
                if t not in teams:
                    teams[t] = {'points': 0, 'gd': 0}
            if ftr == 'H':
                teams[ht]['points'] += 3
            elif ftr == 'A':
                teams[at]['points'] += 3
            else:
                teams[ht]['points'] += 1
                teams[at]['points'] += 1
            teams[ht]['gd'] += (hg - ag) if pd.notna(hg) else 0
            teams[at]['gd'] += (ag - hg) if pd.notna(ag) else 0
        
        sorted_teams = sorted(teams.items(), key=lambda x: (-x[1]['points'], -x[1]['gd']))
        standings = {}
        for pos, (team, data) in enumerate(sorted_teams, 1):
            standings[team] = {'position': pos, 'points': data['points'], 'gd': data['gd']}
        return standings
    
    standings = get_current_standings(df, match_league) if match_league else {}
    h_standing = standings.get(local, {'position': 10, 'points': 30, 'gd': 0})
    a_standing = standings.get(visitante, {'position': 10, 'points': 30, 'gd': 0})
    
    cross_fixes['Position_Diff'] = h_standing['position'] - a_standing['position']
    cross_fixes['Points_Diff'] = h_standing['points'] - a_standing['points']
    cross_fixes['GD_Diff'] = h_standing['gd'] - a_standing['gd']
    
    # Quality relativa: usa posiciones actuales, no del último oponente
    cross_fixes['Home_vs_Away_Quality'] = (h_standing['position'] / (a_standing['position'] + 0.1)) - 1
    cross_fixes['Away_vs_Home_Quality'] = (a_standing['position'] / (h_standing['position'] + 0.1)) - 1
    
    # opponent_position/points/gd: en el contexto actual = datos del rival ACTUAL
    cross_fixes['opponent_position_home'] = a_standing['position']  # Rival del local = visitante
    cross_fixes['opponent_position_away'] = h_standing['position']  # Rival del visitante = local
    cross_fixes['opponent_points_home'] = a_standing['points']
    cross_fixes['opponent_points_away'] = h_standing['points']
    cross_fixes['opponent_gd_home'] = a_standing['gd']
    cross_fixes['opponent_gd_away'] = h_standing['gd']
    
    # --- Aggression cruzada: Mi agresión × vulnerabilidad del RIVAL ACTUAL ---
    h_aggression = safe_get(h_row, 'Home_Aggression_Score', 0.5)
    a_aggression = safe_get(a_row, 'Away_Aggression_Score', 0.5)
    h_vuln = safe_get(h_row, 'Home_Defensive_Vulnerability', 0)
    a_vuln = safe_get(a_row, 'Away_Defensive_Vulnerability', 0)
    h_perm = safe_get(h_row, 'Home_Defensive_Permissiveness', 0)
    a_perm = safe_get(a_row, 'Away_Defensive_Permissiveness', 0)
    
    cross_fixes['Home_Attacking_vs_Away_Defense'] = h_aggression * (1 + np.clip(a_vuln, -1, 1))
    cross_fixes['Away_Attacking_vs_Home_Defense'] = a_aggression * (1 + np.clip(h_vuln, -1, 1))
    
    # Expected Shots: mi tiro × permisividad del RIVAL ACTUAL
    cross_fixes['Expected_Shots_Home'] = rs_role_h * (1 + a_perm * 0.5)
    cross_fixes['Expected_Shots_Away'] = rs_role_a * (1 + h_perm * 0.5)
    
    h_accuracy = safe_get(h_row, 'Home_Shot_Accuracy', 0.35)
    a_accuracy = safe_get(a_row, 'Away_Shot_Accuracy', 0.35)
    cross_fixes['Expected_ST_Home'] = cross_fixes['Expected_Shots_Home'] * h_accuracy
    cross_fixes['Expected_ST_Away'] = cross_fixes['Expected_Shots_Away'] * a_accuracy
    
    # Expected V2: con vulnerabilidad defensiva del rival actual
    cross_fixes['Expected_Shots_Home_V2'] = rs_h * (1 + np.clip(a_vuln, -0.5, 0.5) * 0.3)
    cross_fixes['Expected_Shots_Away_V2'] = rs_a * (1 + np.clip(h_vuln, -0.5, 0.5) * 0.3)
    
    # Possession EWM: ratio de tiros ambos equipos ACTUALES
    total_s = rs_h + rs_a + 0.1
    cross_fixes['Home_Possession_EWM'] = (rs_h / total_s) * 100
    cross_fixes['Away_Possession_EWM'] = (rs_a / total_s) * 100
    
    # Expected con posesión
    cross_fixes['Expected_Shots_Home_With_Possession'] = (
        cross_fixes['Expected_Shots_Home_V2'] * (1 + (cross_fixes['Home_Possession_EWM'] - 50) / 100)
    )
    cross_fixes['Expected_Shots_Away_With_Possession'] = (
        cross_fixes['Expected_Shots_Away_V2'] * (1 + (cross_fixes['Away_Possession_EWM'] - 50) / 100)
    )
    cross_fixes['Expected_ST_Home_Possession'] = cross_fixes['Expected_ST_Home'] * (1 + (cross_fixes['Home_Possession_EWM'] - 50) / 100)
    cross_fixes['Expected_ST_Away_Possession'] = cross_fixes['Expected_ST_Away'] * (1 + (cross_fixes['Away_Possession_EWM'] - 50) / 100)
    
    # Diff y exp: recalcular con datos cruzados correctos
    cross_fixes['diff_Shots'] = rs_h - rs_a
    cross_fixes['exp_Total_Shots'] = rs_h + rs_a
    cross_fixes['exp_Total_Corners'] = rc_h + rc_a
    cross_fixes['Shot_Share_Home'] = rs_h / (rs_h + rs_a + 0.1)
    cross_fixes['Corner_Share_Home'] = rc_h / (rc_h + rc_a + 0.1)

    # ── RECÁLCULO FEATURES SoT CRUZADAS (para el rival ACTUAL, no el del último partido) ──
    # Direct_SoT: mis shots × mi propia tasa de conversión a puerta (per-team stat OK)
    ewm_sot_rate_h = safe_get(h_row, 'EWM_SoT_Rate_Home', 0.3)
    ewm_sot_rate_a = safe_get(a_row, 'EWM_SoT_Rate_Away', 0.3)
    # EWM_OppSoT_Rate: cuánto concede el RIVAL en conversión de tiros a puerta
    ewm_opp_sot_rate_h = safe_get(h_row, 'EWM_OppSoT_Rate_Home', 0.3)  # concesión del LOCAL (útil para visitante)
    ewm_opp_sot_rate_a = safe_get(a_row, 'EWM_OppSoT_Rate_Away', 0.3)  # concesión del VISITANTE (útil para local)
    rst_role_h = safe_get(h_row, 'rolling_ST_5_Role_Home', rst_h)
    rst_role_a = safe_get(a_row, 'rolling_ST_5_Role_Away', rst_a)
    # Direct: mis shots × mi tasa de conversión
    cross_fixes['Direct_SoT_Home'] = rs_role_h * ewm_sot_rate_h
    cross_fixes['Direct_SoT_Away'] = rs_role_a * ewm_sot_rate_a
    # Cross: mis shots × tasa de concesión del RIVAL ACTUAL (recalculado correctamente)
    cross_fixes['Cross_SoT_Home'] = rs_role_h * ewm_opp_sot_rate_a
    cross_fixes['Cross_SoT_Away'] = rs_role_a * ewm_opp_sot_rate_h
    # SoT_Expectancy: blend 60/40
    cross_fixes['SoT_Expectancy_Home'] = 0.6 * cross_fixes['Direct_SoT_Home'] + 0.4 * cross_fixes['Cross_SoT_Home']
    cross_fixes['SoT_Expectancy_Away'] = 0.6 * cross_fixes['Direct_SoT_Away'] + 0.4 * cross_fixes['Cross_SoT_Away']
    # Conceded_SoT: tiros a puerta que RECIBE cada equipo en su rol (per-team, OK desde fila)
    conc_h = safe_get(h_row, 'Conceded_SoT_Home', rost_h)
    conc_a = safe_get(a_row, 'Conceded_SoT_Away', rost_a)
    cross_fixes['Conceded_SoT_Home'] = conc_h
    cross_fixes['Conceded_SoT_Away'] = conc_a
    # SoT_Dominance: mi expectativa de ataque / lo que concede el RIVAL ACTUAL
    cross_fixes['SoT_Dominance_Home'] = cross_fixes['SoT_Expectancy_Home'] / (conc_a + 0.5)
    cross_fixes['SoT_Dominance_Away'] = cross_fixes['SoT_Expectancy_Away'] / (conc_h + 0.5)
    # Fast_SoT / Fast_Shots: son per-team rolling (alfa=0.4), correctos desde cada fila
    cross_fixes['Fast_SoT_Home']   = safe_get(h_row, 'Fast_SoT_Home',   rst_role_h)
    cross_fixes['Fast_SoT_Away']   = safe_get(a_row, 'Fast_SoT_Away',   rst_role_a)
    cross_fixes['Fast_Shots_Home'] = safe_get(h_row, 'Fast_Shots_Home', rs_role_h)
    cross_fixes['Fast_Shots_Away'] = safe_get(a_row, 'Fast_Shots_Away', rs_role_a)

    # Aplicar a input_dict (modelo 1X2) y además construir shots_ext ya con los valores frescos
    for col, val in cross_fixes.items():
        if col in input_dict:
            input_dict[col] = val

    X_in = pd.DataFrame([input_dict])[model_features]
    X_in = X_in.fillna(0)  # Seguro final: ningún NaN llega a los modelos

    # 4. PREDICCIONES
    prob_1x2_raw = m_res.predict_proba(X_in)[0]
    
    # Calibración: suavizar probabilidades extremas con temperature scaling
    # p_cal = p^(1/T) / sum(p^(1/T)) — T>1 reduce overconfidence
    def calibrate_probs(probs, temperature):
        p_cal = np.power(np.clip(probs, 1e-10, 1), 1.0 / temperature)
        return p_cal / p_cal.sum()
    
    market_probs = np.array([(1/h)/sum_inv, (1/d)/sum_inv, (1/a)/sum_inv])
    if match_league == 'CL':
        # CL: modelo entrenado con 97% doméstico → calibrar fuerte + dar peso al mercado
        prob_cal = calibrate_probs(prob_1x2_raw, temperature=3.0)
        prob_1x2 = 0.20 * prob_cal + 0.80 * market_probs
    else:
        # Doméstica: modelo regularizado + mercado como ancla
        prob_cal = calibrate_probs(prob_1x2_raw, temperature=1.5)
        prob_1x2 = 0.60 * prob_cal + 0.40 * market_probs
    
    # ════════════════════════════════════════════════════════════════════
    # AJUSTE DE COHERENCIA: MODELO vs MERCADO + FORMA
    # Si el modelo diverge mucho del mercado Y la forma contradice al modelo,
    # aplicar corrección. Resuelve predicciones extremas incoherentes.
    # ════════════════════════════════════════════════════════════════════
    form_diff = h_form['form_points'] - a_form['form_points']  # >0 = local mejor forma
    
    # 1. Ajuste por forma reciente (si hay diferencia significativa)
    if abs(form_diff) >= 2:
        form_boost = np.clip(form_diff / 20.0, -0.08, 0.08)  # Max ±8%
        prob_1x2[0] += form_boost
        prob_1x2[2] -= form_boost
    
    # 2. Ajuste por divergencia extrema modelo↔mercado
    # Si el modelo da <10% a un equipo pero el mercado da >30%, hay sobreconfianza
    for idx in [0, 2]:  # Solo local y visitante (no empate)
        divergence = market_probs[idx] - prob_1x2[idx]
        if divergence > 0.15:  # Mercado >15% más alto que el modelo
            correction = divergence * 0.3  # Corregir 30% de la divergencia
            prob_1x2[idx] += correction
            other_idx = 2 if idx == 0 else 0
            prob_1x2[other_idx] -= correction * 0.5
            prob_1x2[1] -= correction * 0.5  # Distribuir entre empate y oponente
    
    # Renormalizar
    prob_1x2 = np.clip(prob_1x2, 0.02, 0.95)
    prob_1x2 = prob_1x2 / prob_1x2.sum()
    
    # Construir X_shots_in con las features propias de los modelos de tiros
    shots_model_features = m_corn.feature_names_in_
    shots_ext = dict(input_dict)  # base con features del modelo 1X2
    for col in shots_model_features:
        if col not in shots_ext:
            if '_Home' in col:
                shots_ext[col] = safe_get(h_row, col, 0.0)
            elif '_Away' in col:
                shots_ext[col] = safe_get(a_row, col, 0.0)
            else:
                shots_ext[col] = safe_get(h_row, col, 0.0)
    # Sobreescribir con cross_fixes (valores recalculados para el rival ACTUAL)
    # Esto elimina los valores rancios de h_row/a_row que usaban al oponente anterior
    for col, val in cross_fixes.items():
        shots_ext[col] = val
    X_shots_in = pd.DataFrame([shots_ext])[shots_model_features].fillna(0)

    mu_c = m_corn.predict(X_shots_in)[0]
    mu_s = m_shots.predict(X_shots_in)[0]
    mu_t = m_target.predict(X_shots_in)[0]
    
    # Modelos separados para HS/AS/HST/AST
    if has_separate_models:
        sep_features = m_hs.feature_names_in_
        X_sep = pd.DataFrame([shots_ext])[sep_features].fillna(0)
        
        mu_hs_direct = m_hs.predict(X_sep)[0]
        mu_as_direct = m_as.predict(X_sep)[0]
        mu_hst_direct = m_hst.predict(X_sep)[0]
        mu_ast_direct = m_ast.predict(X_sep)[0]
    
    # 5. REPARTO DINÁMICO
    # Calcular shares de los rolling stats reales de AMBOS equipos (no de una sola fila)
    h_roll_s = safe_get(h_row, 'rolling_S_5_Role_Home', 0)
    a_roll_s = safe_get(a_row, 'rolling_S_5_Role_Away', 0)
    h_roll_c = safe_get(h_row, 'rolling_C_5_Role_Home', 0)
    a_roll_c = safe_get(a_row, 'rolling_C_5_Role_Away', 0)
    
    share_s = h_roll_s / (h_roll_s + a_roll_s) if (h_roll_s + a_roll_s) > 0 else 0.5
    share_c = h_roll_c / (h_roll_c + a_roll_c) if (h_roll_c + a_roll_c) > 0 else 0.5
    
    # Clamp entre 0.25-0.75 para evitar extremos
    share_s = np.clip(share_s, 0.25, 0.75)
    share_c = np.clip(share_c, 0.25, 0.75)
    
    # 5B. AJUSTE CL: Corregir predicciones con promedios reales de CL
    cl_adj_applied = False
    if match_league == 'CL':
        h_cl = get_cl_stats(df, local, as_home=True, exclude_opponent=visitante)
        a_cl = get_cl_stats(df, visitante, as_home=False, exclude_opponent=local)
        
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

    # 5D. AJUSTE LIGA DOMÉSTICA: usa stats reales del equipo SOLO en esa liga/rol
    # Para equipos que juegan también CL, su rolling puede estar sesgado por CL
    if match_league and match_league != 'CL' and not cl_adj_applied:
        # Resolver alias de nombres para la búsqueda en liga doméstica
        local_res = resolve_team_name(local, df)
        visitante_res = resolve_team_name(visitante, df)
        h_lg = get_league_role_stats(df, local_res, match_league, as_home=True,
                                     n_games=8, exclude_opponent=visitante_res)
        a_lg = get_league_role_stats(df, visitante_res, match_league, as_home=False,
                                     n_games=8, exclude_opponent=local_res)
        if h_lg and a_lg:
            min_n = min(h_lg['n'], a_lg['n'])
            # Peso bajo: el modelo ya conoce estos datos domain-specific
            # Solo corrige sesgos por mezcla con otras competiciones
            lg_weight = 0.20 if min_n >= 5 else (0.12 if min_n >= 3 else 0.0)
            m_weight = 1 - lg_weight
            if lg_weight > 0:
                real_total_s = h_lg['shots'] + a_lg['shots']
                real_total_t = h_lg['shots_target'] + a_lg['shots_target']
                real_total_c = h_lg['corners'] + a_lg['corners']
                mu_s_pre = mu_s
                mu_t_pre = mu_t
                mu_s = m_weight * mu_s + lg_weight * real_total_s
                mu_t = m_weight * mu_t + lg_weight * real_total_t
                mu_c = m_weight * mu_c + lg_weight * real_total_c
                if has_separate_models:
                    mu_hs_direct = m_weight * mu_hs_direct + lg_weight * h_lg['shots']
                    mu_as_direct = m_weight * mu_as_direct + lg_weight * a_lg['shots']
                    mu_hst_direct = m_weight * mu_hst_direct + lg_weight * h_lg['shots_target']
                    mu_ast_direct = m_weight * mu_ast_direct + lg_weight * a_lg['shots_target']
                print(f"\n[LIGA-ADJ] Ajuste {match_league} ({lg_weight:.0%} liga real, {m_weight:.0%} modelo):")
                print(f"   Tiros: {mu_s_pre:.1f} \u2192 {mu_s:.1f} (Liga real: {real_total_s:.1f})")
                print(f"   A puerta: {mu_t_pre:.1f} \u2192 {mu_t:.1f} (Liga real: {real_total_t:.1f})")
                print(f"   Datos: {local} {h_lg['n']}p(H), {visitante} {a_lg['n']}p(A)")

    def get_p(mu, line): return (1 - poisson.cdf(line, mu)) * 100

    # 6. REPORTE VISUAL V2
    print("\n" + "╔" + "═"*55 + "╗")
    print(f"║ ⚽ {local.upper()} vs {visitante.upper()} ".ljust(56) + "║")
    print("╠" + "═"*55 + "╣")
    print(f"║ 1X2: L:{prob_1x2[0]*100:.1f}% | X:{prob_1x2[1]*100:.1f}% | V:{prob_1x2[2]*100:.1f}% ".ljust(56) + "║")
    
    # DIAGNÓSTICO: Mostrar probabilidades RAW vs MARKET
    print(f"║ [DEBUG] Modelo puro: L:{prob_1x2_raw[0]*100:.1f}% X:{prob_1x2_raw[1]*100:.1f}% V:{prob_1x2_raw[2]*100:.1f}% ".ljust(56) + "║")
    print(f"║ [DEBUG] Mercado:     L:{market_probs[0]*100:.1f}% X:{market_probs[1]*100:.1f}% V:{market_probs[2]*100:.1f}% ".ljust(56) + "║")
    
    # Mostrar si H2H fue atenuado
    if h2h_weight < 1.0:
        print(f"║ [INFO] H2H atenuado al {h2h_weight*100:.0f}% (forma reciente pesa más) ".ljust(56) + "║")
    
    # Detectar si H2H está dominando demasiado
    if h2h['h2h_matches'] >= 3:
        h2h_diff = abs(h2h['h2h_wins_a'] - h2h['h2h_wins_b'])
        if h2h_diff >= 2:
            dominant_team = local if h2h['h2h_wins_a'] > h2h['h2h_wins_b'] else visitante
            print(f"║ ⚠️  ALERTA: H2H dominante ({dominant_team}, {h2h_diff}+ victorias) ".ljust(56) + "║")
            if h2h_weight >= 0.9:
                print(f"║     H2H puede sesgar la predicción ".ljust(56) + "║")
                print(f"║     💡 Sugerencia: usar h2h_weight=0.3 para balancear ".ljust(56) + "║")
    
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
            if sep_val <= 0:
                return total_val
            ratio = sep_val / total_val
            # Si el separado diverge más de 50% del total, ignorarlo
            if ratio < 0.50 or ratio > 1.50:
                return total_val
            # CL con ajuste real: 55% total (ya tiene CL-ADJ) + 45% separado
            # Doméstica: 40% total + 60% separado (separados son más precisos por rol)
            w_sep = 0.45 if is_cl else 0.60
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
        league = sys.argv[6].upper() if len(sys.argv) > 6 else None
        predict_final_boss(local, visitante, h, d, a, match_league=league)
    else:
        predict_final_boss()