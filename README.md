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

## Instalación

1. Clonar el repositorio
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Actualización de Datos

Para mantener actualizado el dataset con los últimos partidos:

1. **Configurar API Key** (opcional):
   - Copia `.env.example` a `.env`
   - Añade tu API key de Sofascore (RapidAPI)
   - Si no configuras el .env, usa la clave por defecto

2. **Ejecutar actualización**:
   ```bash
   python src/update_dataset.py
   ```

Este script:
- Descarga automáticamente los últimos partidos de todas las ligas configuradas
- Evita duplicados
- Actualiza los archivos CSV de cada liga
- Incluye estadísticas completas: tiros, tiros a puerta, corners, faltas, tarjetas

**Ligas soportadas**: Champions League, Premier League, LaLiga, Bundesliga, Serie A, Ligue 1

## Uso

```bash
python src/preprocessor.py  # Procesa datos
python src/train.py         # Entrena modelos
python src/predict.py       # Realiza predicciones
```

---

*Versión 1.0 | Sistema de Predicción Contextual*
