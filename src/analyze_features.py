"""
Feature Importance Analysis
Ver qué características realmente importan para predecir tiros y remates
"""

import pandas as pd
import joblib
import matplotlib.pyplot as plt
import os

def analyze_feature_importance():
    """Analiza importancia de features en todos los modelos"""
    
    df = pd.read_csv('data/dataset_final.csv', low_memory=False)
    df = df.dropna(subset=['HC', 'AC', 'HS', 'AS', 'HST', 'AST', 'FTR', 'AvgH'])
    
    # Obtener lista de features igual a como lo hace train.py
    features = [c for c in df.columns if 'rolling_' in c]
    features += [c for c in df.columns if 'instability_' in c or 'std_' in c]
    features += [c for c in df.columns if 'diff_' in c or 'exp_' in c or 'Share' in c]
    features += ['AvgH', 'AvgD', 'AvgA', 'Market_Prob_H', 'Market_Prob_D', 'Market_Prob_A', 'Odds_Std']
    features += [c for c in df.columns if 'opponent_' in c]
    features += [c for c in df.columns if 'Shot_Accuracy' in c or 'Pressure_Index' in c or 'Attacking_Momentum' in c]
    features += [c for c in df.columns if 'Shot_Advantage' in c or 'Match_Shot_Expectancy' in c or 'Match_Corner_Expectancy' in c or 'Defense_Efficiency' in c]
    features += [c for c in df.columns if 'Position_Diff' in c or 'Points_Diff' in c or 'GD_Diff' in c or 'Quality' in c]
    features += [c for c in df.columns if 'H2H_' in c]
    features += [c for c in df.columns if 'Aggression' in c or 'Offensive' in c or 'Permissiveness' in c or 'Expected_' in c or 'Consistency' in c or 'Volume' in c]
    features += ['temporal_weight']
    
    features = [f for f in features if f in df.columns]
    features = list(set(features))
    
    print(f"\n[FEATURE IMPORTANCE ANALYSIS]")
    print(f"Total features: {len(features)}\n")
    
    # Cargar modelos
    try:
        m_shots = joblib.load('models/shots_total_model.pkl')
        m_st = joblib.load('models/shots_target_model.pkl')
    except:
        print("[ERROR] Modelos no encontrados")
        return
    
    # TIROS TOTALES - Top 15 features
    print("="*70)
    print("TOP 15 FEATURES - TIROS TOTALES (Shots)")
    print("="*70)
    
    # Los modelos tienen exactamente len(features) features
    if len(features) == len(m_shots.feature_importances_):
        importance_shots = pd.DataFrame({
            'feature': features,
            'importance': m_shots.feature_importances_
        }).sort_values('importance', ascending=False).head(15)
        
        for idx, row in importance_shots.iterrows():
            pct = row['importance'] * 100
            bar_len = int(pct / 2)
            print(f"{row['feature']:40s} {'█' * bar_len} {pct:6.2f}%")
    else:
        print(f"[ERROR] Features mismatch: {len(features)} features vs {len(m_shots.feature_importances_)} importances")
    
    # TIROS A PUERTA - Top 15 features
    print("\n" + "="*70)
    print("TOP 15 FEATURES - TIROS A PUERTA (Shots on Target)")
    print("="*70)
    if len(features) == len(m_st.feature_importances_):
        importance_st = pd.DataFrame({
            'feature': features,
            'importance': m_st.feature_importances_
        }).sort_values('importance', ascending=False).head(15)
        
        for idx, row in importance_st.iterrows():
            pct = row['importance'] * 100
            bar_len = int(pct / 2)
            print(f"{row['feature']:40s} {'█' * bar_len} {pct:6.2f}%")
    else:
        print(f"[ERROR] Features mismatch: {len(features)} features vs {len(m_st.feature_importances_)} importances")
    
    # CATEGORÍAS MÁS IMPORTANTES
    print("\n" + "="*70)
    print("IMPORTANCIA POR CATEGORÍA - TIROS TOTALES")
    print("="*70)
    
    categories = {
        'Rolling Stats': [f for f in features if 'rolling_' in f],
        'Inestabilidad': [f for f in features if 'instability_' in f or 'std_' in f],
        'Attacking Momentum': [f for f in features if 'Shot_Accuracy' in f or 'Pressure_Index' in f or 'Attacking_Momentum' in f],
        'Aggression Score': [f for f in features if 'Aggression' in f or 'Offensive' in f or 'Permissiveness' in f or 'Expected_' in f or 'Consistency' in f or 'Volume' in f],
        'Expected Shots': [f for f in features if 'Expected_' in f],
        'Defense Fatigue': [f for f in features if 'Shot_Advantage' in f or 'Match_Shot_Expectancy' in f or 'Defense_Efficiency' in f],
        'SOS/Opponent': [f for f in features if 'opponent_' in f],
        'H2H': [f for f in features if 'H2H_' in f],
        'Mercado': [f for f in features if 'Market_' in f or 'Odds_' in f],
    }
    
    category_importance = {}
    for cat, feats in categories.items():
        feat_in_model = [f for f in feats if f in features]
        importance_sum = m_shots.feature_importances_[[features.index(f) for f in feat_in_model]].sum()
        category_importance[cat] = importance_sum * 100
    
    for cat, imp in sorted(category_importance.items(), key=lambda x: x[1], reverse=True):
        bar_len = int(imp / 2)
        print(f"{cat:30s} {'█' * bar_len} {imp:6.2f}%")
    
    print("\n" + "="*70)
    print("💡 RECOMENDACIÓN:")
    print("="*70)
    if category_importance.get('Expected Shots', 0) > 5:
        print("✓ Expected_Shots ES IMPORTANTE (>5%) - Mantener Feature #2")
    else:
        print("✗ Expected_Shots NO es crucial (<5%) - Considerar optimizar")
    
    if category_importance.get('Aggression Score', 0) > 8:
        print("✓ Aggression Score ES IMPORTANTE (>8%) - Bien implementado")
    else:
        print("⚠ Aggression Score podría mejorarse")

if __name__ == "__main__":
    analyze_feature_importance()
