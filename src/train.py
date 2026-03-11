import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib
import os

def train_dynamic_brain():
    df = pd.read_csv('data/dataset_final.csv', low_memory=False).copy()
    
    # Limpieza estricta de NaNs para evitar errores de XGBoost
    df = df.dropna(subset=['HC', 'AC', 'HS', 'AS', 'HST', 'AST', 'FTR', 'AvgH'])
    
    # SELECCIÓN AVANZADA: Features del modelo
    # 1. Medias móviles exponenciales (forma del equipo)
    features = [c for c in df.columns if 'rolling_' in c]
    
    # 2. Inestabilidad (desviación estándar)
    features += [c for c in df.columns if 'instability_' in c or 'std_' in c]
    
    # 3. Diferencias y expectativas
    features += [c for c in df.columns if 'diff_' in c or 'exp_' in c or 'Share' in c]
    
    # 4. Probabilidades de mercado y cuotas
    features += ['AvgH', 'AvgD', 'AvgA', 'Market_Prob_H', 'Market_Prob_D', 'Market_Prob_A', 'Odds_Std']
    
    # 5. STRENGTH OF SCHEDULE - Posición y forma del rival (¡CLAVE!)
    features += [c for c in df.columns if 'opponent_' in c]
    
    # 6. ATTACKING MOMENTUM (Nuevas métricas - Paso 5)
    attacking_momentum = [c for c in df.columns if 
                         'Shot_Accuracy' in c or 'Pressure_Index' in c or 'Attacking_Momentum' in c]
    features += attacking_momentum
    
    # 7. DEFENSE FATIGUE (Nuevas métricas - Paso 6)
    defense_fatigue = [c for c in df.columns if 
                      'Shot_Advantage' in c or 'Match_Shot_Expectancy' in c or 
                      'Match_Corner_Expectancy' in c or 'Defense_Efficiency' in c]
    features += defense_fatigue
    
    # 8. ELO/POSITION GAP (Nuevas métricas - Paso 7)
    position_gap = [c for c in df.columns if 
                   'Position_Diff' in c or 'Points_Diff' in c or 'GD_Diff' in c or 'Quality' in c]
    features += position_gap
    
    # 9. HEAD-TO-HEAD RECIENTE (Consolidado: solo H2H_Dominance)
    # ANTES: 6 features redundantes que dominaban 50% del modelo
    # AHORA: 1 feature compacta (-1 a +1) que no puede dominar
    features += ['H2H_Dominance']
    
    # 10. TEAM AGGRESSION SCORE (Nuevas métricas - Paso 9)
    # Agresividad ofensiva + defensiva + predicciones mejoradas
    aggression_features = [c for c in df.columns if 
                          'Aggression' in c or 'Offensive' in c or 'Permissiveness' in c or
                          'Expected_Shots' in c or 'Expected_ST' in c or 'Shooting_Volume' in c or
                          'Shot_Consistency' in c]
    features += aggression_features
    
    # 11. OPPOSITION DEFENSIVE STYLE (Nuevas métricas - Mejora #2)
    defensive_style = [c for c in df.columns if 
                      'Defensive_Vulnerability' in c or 'Defensive_Pressing' in c or
                      'Attacking_vs_' in c or 'V2' in c]
    features += defensive_style
    
    # 12. POSSESSION PROXY (Nuevas métricas - Mejora #3)
    possession_features = [c for c in df.columns if 
                          'Possession_' in c or 'With_Possession' in c]
    features += possession_features
    
    # 13. Factor de recencia temporal
    features += ['temporal_weight']
    
    # 14. NUEVAS FEATURES: Liga, descanso, tendencia, posesión real
    # Liga como feature (is_CL, is_E0, etc.)
    league_features = [c for c in df.columns if c.startswith('is_')]
    features += league_features
    
    # Días de descanso
    rest_features = [c for c in df.columns if 'rest_days' in c]
    features += rest_features
    
    # Tendencia de tiros (slope)
    slope_features = [c for c in df.columns if 'slope_' in c]
    features += slope_features
    
    # Posesión real (rolling)
    real_poss_features = [c for c in df.columns if 'rolling_Poss' in c]
    features += real_poss_features
    
    # Filtrar solo columnas que realmente existen
    features = [f for f in features if f in df.columns]
    # Eliminar duplicados
    features = list(set(features))
    
    print(f"[MODEL] Modelo entrenado con {len(features)} features:")
    print(f"   - Forma (rolling): {len([f for f in features if 'rolling_' in f])}")
    print(f"   - Inestabilidad: {len([f for f in features if 'instability_' in f or 'std_' in f])}")
    print(f"   - Attacking Momentum: {len([f for f in features if 'Shot_Accuracy' in f or 'Pressure_Index' in f])}")
    print(f"   - Defense Fatigue: {len([f for f in features if 'Shot_Advantage' in f or 'Expectancy' in f])}")
    print(f"   - Position Gap: {len([f for f in features if 'Diff' in f or 'Quality' in f])}")
    print(f"   - H2H: {len([f for f in features if 'H2H_' in f])} (consolidado: H2H_Dominance)")
    print(f"   - Aggression/Expected: {len([f for f in features if 'Aggression' in f or 'Offensive' in f or 'Permissiveness' in f or 'Expected_' in f or 'Consistency' in f])}")
    print(f"   - Opposition Defense: {len([f for f in features if 'Defensive_Vulnerability' in f or 'Defensive_Pressing' in f or 'Attacking_vs_' in f or 'V2' in f])}")
    print(f"   - Possession: {len([f for f in features if 'Possession' in f or 'Poss' in f])}")
    print(f"   - Liga/Descanso/Slope: {len([f for f in features if f.startswith('is_') or 'rest_' in f or 'slope_' in f])}")
    print(f"   - SOS (opponent): {len([f for f in features if 'opponent_' in f])}")
    print(f"   - Mercado: {len([f for f in features if 'Market_' in f or 'Odds_' in f])}")
    
    X = df[features]

    # --- CONFIGURACIÓN: MODELO RESULTADO (clasificación) ---
    # Regularizado para evitar sobreajuste a calidad histórica (Position/H2H)
    model_params = {
        'n_estimators': 200,
        'learning_rate': 0.05,
        'max_depth': 4,
        'min_child_weight': 5,
        'subsample': 0.8,
        'colsample_bytree': 0.7,
        'reg_alpha': 0.1,
        'reg_lambda': 2.0,
        'random_state': 42
    }

    # --- CONFIGURACIÓN: MODELOS DE TIROS (regresión especializada) ---
    # Más profundidad y estimadores para capturar patrones no lineales de tiros
    # Menos regularización porque los tiros son más predecibles que el resultado
    shots_params = {
        'n_estimators': 400,
        'learning_rate': 0.04,
        'max_depth': 6,
        'min_child_weight': 3,
        'subsample': 0.85,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.05,
        'reg_lambda': 1.0,
        'random_state': 42
    }

    # --- FEATURES ESPECIALIZADAS PARA MODELOS DE TIROS ---
    # Prioriza features de volumen/precisión de tiros, ignora mercado/H2H
    shots_priority = [
        c for c in features if any(kw in c for kw in [
            'rolling_S_', 'rolling_ST_', 'rolling_OppS_', 'rolling_OppST_',
            'EWM_Shots', 'EWM_Shots_Target', 'EWM_SoT_Rate', 'EWM_OppST',
            'EWM_OppSoT_Rate', 'EWM_S_Fast', 'EWM_ST_Fast',
            'slope_S_', 'slope_ST_',
            'Shot_Accuracy', 'Shooting_Volume', 'Shot_Consistency',
            'Direct_SoT', 'Cross_SoT', 'SoT_Expectancy', 'SoT_Dominance',
            'Conceded_SoT', 'Fast_SoT', 'Fast_Shots',
            'Expected_Shots', 'Expected_ST', 'Match_Shot_Expectancy',
            'Shot_Advantage', 'Attacking_Momentum', 'Pressure_Index',
            'Offensive_Index', 'Aggression_Score', 'Permissiveness',
            'Defensive_Vulnerability', 'Defense_Efficiency',
            'Attacking_vs_', 'With_Possession', 'Possession_EWM',
            'Home_Advantage_Factor', 'Home_Advantage_Target',
            'diff_Shots', 'exp_Total_Shots', 'Shot_Share',
            'rest_days', 'is_CL', 'is_E0', 'is_SP1', 'is_D1', 'is_I1',
            'opponent_position', 'opponent_points',
        ])
    ]
    shots_priority = list(set(shots_priority))
    # Pesos de recencia: más peso a partidos recientes para modelos de tiros
    sample_w = df['temporal_weight'].values if 'temporal_weight' in df.columns else None

    def split_w(X_data, y_data):
        """Split con pesos temporales si están disponibles"""
        if sample_w is not None:
            splits = train_test_split(X_data, y_data, sample_w, test_size=0.2, random_state=42)
            return splits[0], splits[1], splits[2], splits[3], splits[4]
        splits = train_test_split(X_data, y_data, test_size=0.2, random_state=42)
        return splits[0], splits[1], splits[2], splits[3], None

    # 1. RESULTADO (1X2) — usa features generales, sin pesos (clasificación)
    y_res = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})
    X_train, X_test, y_train, y_test = train_test_split(X, y_res, test_size=0.2, random_state=42)
    m1 = xgb.XGBClassifier(**model_params).fit(X_train, y_train)
    print(f"1X2 Precisión: {accuracy_score(y_test, m1.predict(X_test))*100:.2f}%")

    # Dataset especializado para modelos de tiros
    X_shots = df[shots_priority] if shots_priority else X

    # 2. CORNERS DINÁMICOS (features especializadas + pesos temporales)
    y_corn = df['HC'] + df['AC']
    X_tr_c, X_te_c, y_tr_c, y_te_c, w_tr_c = split_w(X_shots, y_corn)
    m2 = xgb.XGBRegressor(**shots_params)
    m2.fit(X_tr_c, y_tr_c, sample_weight=w_tr_c)
    print(f"Corners MAE: {mean_absolute_error(y_te_c, m2.predict(X_te_c)):.2f}")

    # 3. TIROS TOTALES
    y_shots = df['HS'] + df['AS']
    X_tr_s, X_te_s, y_tr_s, y_te_s, w_tr_s = split_w(X_shots, y_shots)
    m3 = xgb.XGBRegressor(**shots_params)
    m3.fit(X_tr_s, y_tr_s, sample_weight=w_tr_s)
    print(f"Tiros Totales MAE: {mean_absolute_error(y_te_s, m3.predict(X_te_s)):.2f}")

    # 4. TIROS A PUERTA TOTAL
    y_target = df['HST'] + df['AST']
    X_tr_t, X_te_t, y_tr_t, y_te_t, w_tr_t = split_w(X_shots, y_target)
    m4 = xgb.XGBRegressor(**shots_params)
    m4.fit(X_tr_t, y_tr_t, sample_weight=w_tr_t)
    print(f"Tiros a Puerta MAE: {mean_absolute_error(y_te_t, m4.predict(X_te_t)):.2f}")

    # ============ MODELOS SEPARADOS POR EQUIPO (HOME / AWAY) ============

    # 5. TIROS LOCAL (HS)
    y_hs = df['HS']
    X_tr_hs, X_te_hs, y_tr_hs, y_te_hs, w_tr_hs = split_w(X_shots, y_hs)
    m5 = xgb.XGBRegressor(**shots_params)
    m5.fit(X_tr_hs, y_tr_hs, sample_weight=w_tr_hs)
    print(f"Tiros Local (HS) MAE: {mean_absolute_error(y_te_hs, m5.predict(X_te_hs)):.2f}")

    # 6. TIROS VISITANTE (AS)
    y_as = df['AS']
    X_tr_as, X_te_as, y_tr_as, y_te_as, w_tr_as = split_w(X_shots, y_as)
    m6 = xgb.XGBRegressor(**shots_params)
    m6.fit(X_tr_as, y_tr_as, sample_weight=w_tr_as)
    print(f"Tiros Visitante (AS) MAE: {mean_absolute_error(y_te_as, m6.predict(X_te_as)):.2f}")

    # 7. TIROS A PUERTA LOCAL (HST)
    y_hst = df['HST']
    X_tr_hst, X_te_hst, y_tr_hst, y_te_hst, w_tr_hst = split_w(X_shots, y_hst)
    m7 = xgb.XGBRegressor(**shots_params)
    m7.fit(X_tr_hst, y_tr_hst, sample_weight=w_tr_hst)
    print(f"Tiros a Puerta Local (HST) MAE: {mean_absolute_error(y_te_hst, m7.predict(X_te_hst)):.2f}")

    # 8. TIROS A PUERTA VISITANTE (AST)
    y_ast = df['AST']
    X_tr_ast, X_te_ast, y_tr_ast, y_te_ast, w_tr_ast = split_w(X_shots, y_ast)
    m8 = xgb.XGBRegressor(**shots_params)
    m8.fit(X_tr_ast, y_tr_ast, sample_weight=w_tr_ast)
    print(f"Tiros a Puerta Visitante (AST) MAE: {mean_absolute_error(y_te_ast, m8.predict(X_te_ast)):.2f}")

    # Guardar todos los modelos
    os.makedirs('models', exist_ok=True)
    joblib.dump(m1, 'models/result_model.pkl')
    joblib.dump(m2, 'models/corners_model.pkl')
    joblib.dump(m3, 'models/shots_total_model.pkl')
    joblib.dump(m4, 'models/shots_target_model.pkl')
    joblib.dump(m5, 'models/shots_home_model.pkl')
    joblib.dump(m6, 'models/shots_away_model.pkl')
    joblib.dump(m7, 'models/shots_target_home_model.pkl')
    joblib.dump(m8, 'models/shots_target_away_model.pkl')
    print("\n8 modelos entrenados y guardados.")

if __name__ == "__main__":
    train_dynamic_brain()