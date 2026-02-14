# Guía de Uso - Main.py

## Inicio Rápido

Para ejecutar el sistema centralizado:

```bash
python src/main.py
```

## Opciones del Menú

### 1. Preprocesar Datos
- Ejecuta `src/preprocessor.py`
- Procesa el dataset raw (CSVs) y genera features engineered
- Crea `data/dataset_final.csv` con:
  - Promedio móvil exponencial (EWM) para forma
  - Posiciones dinámicas del rival (opponent_position, opponent_points, opponent_gd)
  - Pesas temporales para recencia
  - Inestabilidad (CV de corners y tiros)

### 2. Entrenar Modelos
- Ejecuta `src/train.py`
- Entrena 4 modelos XGBoost:
  - **result_model**: Predicción 1X2 (3 clases)
  - **corners_model**: Total de corners (regresión)
  - **shots_total_model**: Total de tiros (regresión)
  - **shots_target_model**: Tiros a puerta (regresión)
- Guarda modelos en `models/*.pkl`
- **Requiere**: Haber ejecutado la opción 1 antes

### 3. Predicción Asistida (LA CLAVE)
Sistema inteligente de selección por índices:

1. **Selecciona Liga**: Elige entre La Liga (España) o Bundesliga (Alemania)
2. **Selecciona equipos**: 
   - Se muestran todos los equipos de la liga numerados
   - Ingresa número del equipo LOCAL
   - Ingresa número del equipo VISITANTE
3. **Ingresa cuotas**: Cuota 1 (local), X (empate), 2 (visitante)
4. **Predicción automática**: El sistema mapea nombres → calcula predicción

**Resultado**:
- Probabilidades 1X2 del modelo
- Predicciones de corners y tiros
- Recomendaciones Kelly ajustadas por inestabilidad
- Logs automáticos en `data/prediction_log.xlsx`

### 4. Backtesting
- Abre directamente `data/prediction_log.xlsx`
- Contiene todas las predicciones realizadas con:
  - Timestamp
  - Equipos
  - Probabilidad IA
  - Cuota del mercado
  - Monto Kelly recomendado
  - Puntuación de inestabilidad
  - Columnas para resultado manual (llenar después del partido)

### 5. Auto-Run
Ejecuta automáticamente en secuencia:
1. Preprocesamiento (opción 1)
2. Entrenamiento (opción 2)
3. Predicción Asistida (opción 3)

Ideal para actualizar modelos y hacer una predicción nueva en una sola ejecución.

## Archivos Generados

```
├── data/
│   ├── dataset_final.csv        ← Dataset procesado (opción 1)
│   └── prediction_log.xlsx      ← Log de predicciones (opción 3/4)
│
├── models/
│   ├── result_model.pkl         ← Modelo 1X2
│   ├── corners_model.pkl        ← Modelo corners
│   ├── shots_total_model.pkl    ← Modelo tiros totales
│   └── shots_target_model.pkl   ← Modelo tiros a puerta
│
└── src/
    ├── main.py                  ← Este archivo (interfaz)
    ├── preprocessor.py          ← Opción 1
    ├── train.py                 ← Opción 2
    ├── predict.py               ← Opción 3 (se ejecuta aquí)
    └── logger.py                ← Logging Excel
```

## Características Técnicas

- **Rich Console**: Interfaz profesional con paneles y tablas de color
- **Selección por Índices**: No requiere escribir nombres completos
- **Encoding UTF-8**: Compatible con acentos en Windows
- **Persistencia**: Al terminar cada operación, espera Enter antes de volver al menú
- **Limpieza de Pantalla**: Se limpia automáticamente con cada navegación

## Ejemplo de Uso

```
1. Ejecuta: python src/main.py
2. Selecciona opción 1 (Preprocesar) - espera confirmación
3. Selecciona opción 2 (Entrenar) - espera confirmación
4. Selecciona opción 3 (Predicción):
   - Liga: 1 (La Liga)
   - Equipo Local: 1 (Barcelona)
   - Equipo Visitante: 18 (Valencia)
   - Cuota 1: 1.85
   - Cuota X: 3.75
   - Cuota 2: 4.20
5. Verás predicción con Kelly y logs automáticos
6. Vuelve a presionar Enter para retornar al menú
```

## Troubleshooting

- **Missing rich**: `pip install rich`
- **Encoding errors**: Ejecuta en Windows CMD o PowerShell con `chcp 65001`
- **Path errors**: Ejecuta siempre desde la raíz del proyecto
