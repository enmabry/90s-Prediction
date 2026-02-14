import joblib
import pandas as pd
import matplotlib.pyplot as plt

# Cargar modelo 1X2
clf = joblib.load('models/result_model.pkl')

# Get feature importance
importance = pd.DataFrame({
    'feature': clf.feature_names_in_,
    'importance': clf.feature_importances_
}).sort_values('importance', ascending=False)

# Features de posición del rival
position_features = importance[importance['feature'].str.contains('opponent_')]
print("\n🏆 IMPORTANCIA - POSICIÓN DEL RIVAL:")
print(position_features.to_string(index=False))
print(f"\nPromedio importancia opponent_*: {position_features['importance'].mean():.4f}")

# Top 15 features generales
print("\n\n🔝 TOP 15 FEATURES MÁS IMPORTANTES:")
print(importance.head(15).to_string(index=False))

# Visualizar
fig, ax = plt.subplots(figsize=(12, 8))
importance.head(20).sort_values('importance').plot(
    x='feature', y='importance', kind='barh', ax=ax, legend=False
)
ax.set_xlabel('Importancia XGBoost')
ax.set_title('Top 20 Features - Modelo 1X2')
plt.tight_layout()
plt.savefig('images/feature_importance.png', dpi=100, bbox_inches='tight')
print("\n\n📊 Gráfico guardado: images/feature_importance.png")
