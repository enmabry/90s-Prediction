# Guía: Agregar Nueva Liga (Premier League, Ligue 1, etc)

## El Sistema Ahora es Completamente Automático

Anteriormente había que editar múltiples archivos. Ahora **SOLO necesitas:**

### Paso 1: Agregar datos de la nueva liga

Crea una carpeta en `data/` con el nombre de la liga:

```
data/
├── LaLigaEspañola/
├── BundesligaAlemania/
└── PremierLeague/          ← NUEVA: Agregar archivos CSV aquí
    ├── Premier_20-21.csv
    ├── Premier_21-22.csv
    └── ...
```

### Paso 2: Verificar el mapeo (opcional)

Si tu carpeta de datos ya tiene un nombre que coincida con los mapeados, **no necesitas hacer nada más**.

**Nombres automáticamente reconocidos:**
- `Bundesliga` → `D1` (Bundesliga Alemania)
- `LaLiga` → `SP1` (La Liga España)
- `PremierLeague` → `PL` (Premier League UK)
- `Ligue1` → `L1` (Ligue 1 Francia)
- `SerieA` → `SA` (Serie A Italia)

### Paso 3: Agregar liga a los diccionarios (SI NECESITAS NOMBRE PERSONALIZADO)

**En `src/preprocessor.py`** (líneas 10-17):
```python
LEAGUE_MAPPING = {
    'Bundesliga': 'D1',
    'LaLiga': 'SP1',
    'PremierLeague': 'PL',    # Ya incluido
    'MiNuevaLiga': 'XX',      # ← Agregar aquí
}
```

**En `src/main.py`** (líneas 22-28):
```python
LIGAS_DICT = {
    'SP1': '[ESPAÑA] La Liga',
    'D1': '[ALEMANIA] Bundesliga',
    'PL': '[UK] Premier League',    # Ya incluido
    'XX': '[PAIS] Mi Nueva Liga',   # ← Agregar aquí
}
```

---

## Ejemplo Completo: Agregar Premier League

### 1. Estructura de carpetas
```
data/PremierLeague/
├── Premier20-21.csv
├── Premier21-22.csv
├── Premier22-23.csv
├── Premier23-24.csv
└── Premier24-25.csv
```

### 2. Ejecutar preprocessor
```bash
python src/preprocessor.py
```
**Resultado:** Detecta automáticamente "PremierLeague" → asigna `PL`

### 3. Ejecutar train
```bash
python src/train.py
```
**Resultado:** Entrena con 4 ligas (LaLiga + Bundesliga + **Premier + cualquier otra**)

### 4. Hacer predicción desde main
```bash
python src/main.py
→ Opción 3 (Predicción)
→ Verás 3 ligas disponibles:
   1: [ESPAÑA] La Liga (2,128 partidos)
   2: [ALEMANIA] Bundesliga (1,717 partidos)
   3: [UK] Premier League (XXXX partidos) ← NUEVA AUTOMATICAMENTE
```

---

## Arquitectura del Sistema (AGNÓSTICA DE LIGAS)

```
data/              ← Cualquier carpeta con nombre de liga
├── [NuevaLiga]/
│   └── *.csv      ← Busca recursivamente TODOS los CSV
│
src/
├── preprocessor.py
│   └── LEAGUE_MAPPING {automatico}
│       └── Carga y procesa todas las ligas
│
├── train.py
│   └── Entrena con TODOS los datos (multi-liga)
│
├── predict.py
│   └── Predice usando standings POR LIGA
│
└── main.py
    └── LIGAS_DICT {muestra dinámicamente}
        └── Selecciona liga → equipos → predicción
```

---

## Requisitos Mínimos para Nuevo Dataset

Los archivos CSV deben tener (como poco):
- `Date` o fecha
- `HomeTeam` 
- `AwayTeam`
- `FTHG` (Goles Home Final Time)
- `FTAG` (Goles Away Final Time)
- `FTR` (Full Time Result: H/D/A)
- `HC`, `AC` (Corners)
- `HS`, `AS` (Shots)
- `HST`, `AST` (Shots on Target)
- `AvgH`, `AvgD`, `AvgA` (Cuotas promedio)

Si no tiene columna `Div`, se asigna automáticamente según el nombre de la carpeta.

---

## Confirmación: Estos Archivos NO necesitan cambios

❌ **NO toques:**
- `src/train.py` → Lee dataset_final.csv, agnóstico de ligas
- `src/predict.py` → Usa standings por Div, automático
- `src/logger.py` → No depende de ligas específicas

✅ **Solo edita si:**
- Quieres cambiar el nombre visual de una liga en main.py
- Tienes una carpeta con nombre NO estándar

---

## Monitoreo: Ver qué Ligas se Cargaron

Al ejecutar `preprocessor.py`:
```
[DATA] Cargando dataset completo (MEMORIA + EWM):
   Total de archivos: 17
[OK] Dataset Multi-Año (EWM + Peso Temporal) generado:
   Total partidos: 8,500+
   Equipos: 95 unicos     ← Si ves 95 equipos = multi-liga funcionando
```

Si ves `/Unknown`, significa una carpeta no está mapeada. Ve a `preprocessor.py` LINE 10 y agrégala.
