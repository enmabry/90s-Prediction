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
    
    # 9. HEAD-TO-HEAD RECIENTE (Nuevas métricas - Paso 8)
    h2h_features = [c for c in df.columns if 'H2H_' in c]
    features += h2h_features
    
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
    print(f"   - H2H: {len([f for f in features if 'H2H_' in f])}")
    print(f"   - Aggression Score: {len([f for f in features if 'Aggression' in f or 'Offensive' in f or 'Permissiveness' in f or 'Expected_' in f or 'Consistency' in f])}")
    print(f"   - Opposition Defense: {len([f for f in features if 'Defensive_Vulnerability' in f or 'Defensive_Pressing' in f or 'Attacking_vs_' in f or 'V2' in f])}")
    print(f"   - Possession Proxy: {len([f for f in features if 'Possession_' in f or 'With_Possession' in f])}")
    print(f"   - SOS (opponent): {len([f for f in features if 'opponent_' in f])}")
    print(f"   - Mercado: {len([f for f in features if 'Market_' in f or 'Odds_' in f])}")
    
    X = df[features]

    # --- CONFIGURACIÓN DE MODELO MÁS PROFUNDO ---
    # Usamos 150 estimadores y un learning_rate de 0.03 para mayor precisión
    model_params = {
        'n_estimators': 150,
        'learning_rate': 0.03,
        'max_depth': 6,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }

    # 1. RESULTADO (1X2)
    y_res = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})
    X_train, X_test, y_train, y_test = train_test_split(X, y_res, test_size=0.2, random_state=42)
    m1 = xgb.XGBClassifier(**model_params).fit(X_train, y_train)
    print(f"1X2 Precisión: {accuracy_score(y_test, m1.predict(X_test))*100:.2f}%")

    # 2. CORNERS DINÁMICOS
    y_corn = df['HC'] + df['AC']
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X, y_corn, test_size=0.2, random_state=42)
    m2 = xgb.XGBRegressor(**model_params).fit(X_train_c, y_train_c)
    print(f"Corners MAE: {mean_absolute_error(y_test_c, m2.predict(X_test_c)):.2f}")

    # 3. TIROS TOTALES
    y_shots = df['HS'] + df['AS']
    X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X, y_shots, test_size=0.2, random_state=42)
    m3 = xgb.XGBRegressor(**model_params).fit(X_train_s, y_train_s)
    print(f"Tiros Totales MAE: {mean_absolute_error(y_test_s, m3.predict(X_test_s)):.2f}")

    # 4. TIROS A PUERTA
    y_target = df['HST'] + df['AST']
    X_train_t, X_test_t, y_train_t, y_test_t = train_test_split(X, y_target, test_size=0.2, random_state=42)
    m4 = xgb.XGBRegressor(**model_params).fit(X_train_t, y_train_t)
    print(f"Tiros a Puerta MAE: {mean_absolute_error(y_test_t, m4.predict(X_test_t)):.2f}")

    # Guardar la "Cuádruple Inteligencia"
    os.makedirs('models', exist_ok=True)
    joblib.dump(m1, 'models/result_model.pkl')
    joblib.dump(m2, 'models/corners_model.pkl')
    joblib.dump(m3, 'models/shots_total_model.pkl')
    joblib.dump(m4, 'models/shots_target_model.pkl')
    print("\nModelos dinámicos listos.")

if __name__ == "__main__":
    train_dynamic_brain()