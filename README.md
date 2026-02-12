# Proyecto de Predicción

<div align="center">
  <img src="images/90s.png" alt="Logo Proyecto" width="150">
</div>

## ¿Qué hemos logrado?

Un **sistema de predicción contextual** que analiza datos históricos de partidos de fútbol para estimar:

- **Probabilidades de resultado** (1X2)
- **Corners esperados** (con desglose individual por equipo)
- **Tiros totales y a puerta**
- **Análisis de matchups** (ataque vs defensa)

### Características principales:

- **4 modelos XGBoost** entrenados con features dinámicas  
- **Medias móviles** de rendimiento (últimos 5 partidos)  
- **Análisis defensivo** (capacidad de resistencia de cada equipo)  
- **Probabilidades de mercado** extraídas de las cuotas  
- **Ventaja de localía** (home advantage)  
- **Búsqueda de equipos** para facilitar el manejo  

## Uso

```bash
python src/preprocessor.py  # Procesa datos
python src/train.py         # Entrena modelos
python src/predict.py       # Realiza predicciones
```

---

*Versión 1.0 | Sistema de Predicción Contextual*
