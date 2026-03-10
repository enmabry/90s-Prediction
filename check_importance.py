import joblib
import pandas as pd

m = joblib.load('models/result_model.pkl')
feat_imp = pd.DataFrame({
    'feature': m.feature_names_in_,
    'importance': m.feature_importances_
}).sort_values('importance', ascending=False)

print('TOP 25 FEATURES:')
for i, (_, row) in enumerate(feat_imp.head(25).iterrows(), 1):
    f_name = row['feature']
    f_imp = row['importance']
    print(f"  {i:3d}. {f_name:<45} {f_imp:.4f}")

total = feat_imp['importance'].sum()
print(f"\nIMPORTANCIA POR CATEGORIA:")
print("-" * 50)

categories = {
    'H2H': ['H2H_'],
    'Quality/Position': ['Position_Diff', 'Points_Diff', 'GD_Diff', 'Quality', 'opponent_'],
    'Mercado': ['Market_', 'Avg', 'Odds_'],
    'Forma (rolling)': ['rolling_'],
    'Inestabilidad': ['instability_', 'std_'],
    'Attacking': ['Aggression', 'Offensive', 'Shot_Accuracy', 'Pressure', 'Momentum'],
    'Defense': ['Defensive_', 'Permissiveness', 'Defense_Eff'],
    'Expected': ['Expected_', 'Shooting_Vol', 'Consistency'],
    'Possession': ['Possession_', 'Poss'],
    'Liga/Descanso': ['is_', 'rest_', 'slope_'],
}

for cat, patterns in categories.items():
    mask = feat_imp['feature'].apply(lambda f: any(p in f for p in patterns))
    imp = feat_imp[mask]['importance'].sum()
    pct = imp / total * 100
    n_feats = mask.sum()
    print(f"  {cat:<25} {pct:>6.2f}%  ({n_feats} features)")
