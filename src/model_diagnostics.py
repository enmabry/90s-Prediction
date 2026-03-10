"""
Diagnóstico de modelos para entender qué features dominan las predicciones
"""
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

def analyze_model_diagnostics():
    """Analiza el modelo 1X2 para ver qué está influyendo en las predicciones"""
    
    print("\n" + "="*60)
    print("  DIAGNÓSTICO DE MODELO 1X2")
    print("="*60)
    
    # Cargar modelo y datos
    try:
        m_res = joblib.load('models/result_model.pkl')
        df = pd.read_csv('data/dataset_final.csv')
        df = df.dropna(subset=['FTR', 'AvgH'])
        
        print(f"\n[INFO] Modelo cargado: {type(m_res).__name__}")
        print(f"[INFO] Dataset: {len(df)} partidos")
        
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el modelo: {e}")
        return
    
    # 1. DISTRIBUCIÓN DE CLASES
    print("\n" + "-"*60)
    print("1. DISTRIBUCIÓN DE CLASES EN EL DATASET")
    print("-"*60)
    
    ftr_counts = df['FTR'].value_counts()
    total = len(df)
    
    print(f"{'Resultado':<15} {'Cantidad':<10} {'% del Total':<15}")
    print("-"*40)
    for resultado, count in ftr_counts.items():
        pct = (count / total) * 100
        label = {"H": "Local (H)", "D": "Empate (D)", "A": "Visitante (A)"}.get(resultado, resultado)
        print(f"{label:<15} {count:<10} {pct:>6.2f}%")
    
    # 2. FEATURE IMPORTANCE
    print("\n" + "-"*60)
    print("2. TOP 20 FEATURES MÁS IMPORTANTES")
    print("-"*60)
    
    try:
        importances = m_res.feature_importances_
        feature_names = m_res.feature_names_in_
        
        # Crear DataFrame y ordenar
        feat_imp = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        # Mostrar top 20
        print(f"\n{'#':<4} {'Feature':<45} {'Importancia':<12} {'% Acum':<10}")
        print("-"*75)
        
        total_imp = feat_imp['importance'].sum()
        cumsum = 0
        
        for idx, (_, row) in enumerate(feat_imp.head(20).iterrows(), 1):
            cumsum += row['importance']
            pct_acum = (cumsum / total_imp) * 100
            print(f"{idx:<4} {row['feature']:<45} {row['importance']:>10.4f}  {pct_acum:>6.2f}%")
        
        print(f"\n[INFO] Top 20 features explican: {pct_acum:.2f}% de la importancia total")
        
        # 3. CATEGORIZAR FEATURES
        print("\n" + "-"*60)
        print("3. IMPORTANCIA POR CATEGORÍA DE FEATURES")
        print("-"*60)
        
        categories = {
            'Mercado': ['Market_', 'Avg', 'Odds_'],
            'H2H': ['H2H_'],
            'Forma': ['rolling_', 'ewm_'],
            'Inestabilidad': ['instability_', 'std_'],
            'Position/Quality': ['Position_', 'Points_', 'GD_', 'Quality', 'opponent_'],
            'Attacking': ['Aggression', 'Offensive', 'Shot_Accuracy', 'Pressure'],
            'Defense': ['Defensive_', 'Permissiveness'],
            'Expected': ['Expected_', 'Shooting_', 'Consistency'],
            'Possession': ['Possession_', 'Poss'],
            'Liga/Descanso': ['is_', 'rest_', 'slope_'],
            'Otros': []
        }
        
        cat_importance = {cat: 0 for cat in categories.keys()}
        
        for _, row in feat_imp.iterrows():
            feature = row['feature']
            importance = row['importance']
            
            categorized = False
            for cat, patterns in categories.items():
                if cat == 'Otros':
                    continue
                if any(pattern in feature for pattern in patterns):
                    cat_importance[cat] += importance
                    categorized = True
                    break
            
            if not categorized:
                cat_importance['Otros'] += importance
        
        # Ordenar por importancia
        sorted_cats = sorted(cat_importance.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Categoría':<25} {'Importancia Total':<20} {'% del Modelo':<15}")
        print("-"*60)
        for cat, imp in sorted_cats:
            pct = (imp / total_imp) * 100
            print(f"{cat:<25} {imp:>15.4f}    {pct:>6.2f}%")
        
        # 4. ANÁLISIS DE PROBABILIDADES DEL MODELO
        print("\n" + "-"*60)
        print("4. CALIBRACIÓN DEL MODELO (sin mezcla con mercado)")
        print("-"*60)
        
        # Obtener features
        features = [c for c in df.columns if c in feature_names]
        X = df[features]
        y_true = df['FTR'].map({'H': 0, 'D': 1, 'A': 2})
        
        # Predicciones crudas
        probs_raw = m_res.predict_proba(X)
        preds = m_res.predict(X)
        
        # Accuracy crudo del modelo (sin calibración)
        accuracy = (preds == y_true).mean()
        print(f"\nAccuracy del modelo puro: {accuracy*100:.2f}%")
        
        # Distribución de confianza del modelo
        max_probs = probs_raw.max(axis=1)
        
        print("\nDistribución de confianza (max_prob):")
        print(f"  - Confianza baja (<50%):  {(max_probs < 0.5).sum()} partidos ({(max_probs < 0.5).mean()*100:.1f}%)")
        print(f"  - Confianza media (50-70%): {((max_probs >= 0.5) & (max_probs < 0.7)).sum()} partidos ({((max_probs >= 0.5) & (max_probs < 0.7)).mean()*100:.1f}%)")
        print(f"  - Confianza alta (70-85%):  {((max_probs >= 0.7) & (max_probs < 0.85)).sum()} partidos ({((max_probs >= 0.7) & (max_probs < 0.85)).mean()*100:.1f}%)")
        print(f"  - Confianza muy alta (>85%): {(max_probs >= 0.85).sum()} partidos ({(max_probs >= 0.85).mean()*100:.1f}%)")
        
        # Promedio de probabilidades por clase
        print("\nProbabilidades promedio por clase predicha:")
        for clase in [0, 1, 2]:
            mask = preds == clase
            if mask.sum() > 0:
                avg_prob = probs_raw[mask, clase].mean()
                label = {0: "Local (H)", 1: "Empate (D)", 2: "Visitante (A)"}[clase]
                print(f"  {label}: {avg_prob*100:.1f}% (en {mask.sum()} predicciones)")
        
        # 5. COMPARACIÓN CON MERCADO
        print("\n" + "-"*60)
        print("5. COMPARACIÓN MODELO vs MERCADO")
        print("-"*60)
        
        # Calcular probabilidades del mercado
        sum_inv = (1/df['AvgH']) + (1/df['AvgD']) + (1/df['AvgA'])
        market_prob_h = ((1/df['AvgH']) / sum_inv).values
        market_prob_d = ((1/df['AvgD']) / sum_inv).values
        market_prob_a = ((1/df['AvgA']) / sum_inv).values
        
        # Predicción del mercado
        market_preds = np.argmax([market_prob_h, market_prob_d, market_prob_a], axis=0)
        market_accuracy = (market_preds == y_true).mean()
        
        print(f"\nAccuracy del mercado (cuotas puras): {market_accuracy*100:.2f}%")
        print(f"Accuracy del modelo: {accuracy*100:.2f}%")
        print(f"Diferencia: {(accuracy - market_accuracy)*100:+.2f} puntos porcentuales")
        
        # Casos donde difieren
        differ = (preds != market_preds)
        print(f"\nEl modelo difiere del mercado en: {differ.sum()} partidos ({differ.mean()*100:.1f}%)")
        if differ.sum() > 0:
            model_wins_when_differ = ((preds == y_true) & differ).sum()
            market_wins_when_differ = ((market_preds == y_true) & differ).sum()
            print(f"  - Cuando difieren, el modelo acierta: {model_wins_when_differ} veces ({model_wins_when_differ/differ.sum()*100:.1f}%)")
            print(f"  - Cuando difieren, el mercado acierta: {market_wins_when_differ} veces ({market_wins_when_differ/differ.sum()*100:.1f}%)")
        
        print("\n" + "="*60)
        print("  DIAGNÓSTICO COMPLETADO")
        print("="*60)
        
        return feat_imp
        
    except Exception as e:
        print(f"[ERROR] Error al analizar feature importance: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_model_diagnostics()
