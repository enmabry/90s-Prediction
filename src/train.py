import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib
import os

def train_dynamic_brain():
    df = pd.read_csv('data/dataset_final.csv').copy()
    
    # Limpieza estricta de NaNs para evitar errores de XGBoost
    df = df.dropna(subset=['HC', 'AC', 'HS', 'AS', 'HST', 'AST', 'FTR', 'AvgH'])
    
    # SELECCIÓN AVANZADA: Ahora incluimos las probabilidades del mercado
    features = [c for c in df.columns if 'rolling_' in c or 'diff_' in c or 'exp_' in c]
    features += ['AvgH', 'AvgD', 'AvgA', 'Market_Prob_H', 'Market_Prob_D', 'Market_Prob_A', 'Odds_Std']
    
    # Eliminar duplicados si los hubiera por error de lógica
    features = list(set(features))
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