# 📋 Guía: Agregar Nueva Liga (EXTENSIBLE)

## Resumen
Este documento explica cómo agregar una nueva liga al sistema de predicción cuando tiene un formato diferente (como Champions League).

---

## Caso de Estudio: Champions League

### Problema Original
Champions League tiene un formato **diferente** que las ligas nacionales:

**Formato Original (champions_league_matches25-26.csv):**
- Columnas: `date`, `home_team`, `away_team`, `score`, `venue`, `referee`, etc.
- No tiene: `Div` (división), `FTR` (resultado H/A/D), column `HS`, `HC` (corners)

**Formato Requerido (para compatibilidad):**
- Columnas: `Div`, `Date`, `Time`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`, `HC`, `AvgH`, `AvgD`, `AvgA`, etc.
- Todas las calculadas automáticamente

---

## Solución: Script de Transformación

### Archivo: `src/transform_champions_league.py`

```python
# Este script:
1. Lee el CSV original
2. Parsea score ("1–3" → FTHG=1, FTAG=3)
3. Mapea resultado (Home Win → 'H', Away Win → 'A', Draw → 'D')
4. Renombra columnas al formato estándar
5. Agrega columnas faltantes (HC, AvgH, etc.) con valores default/estimados
6. Guarda como ChampionsLeague25-26.csv (compatible)
```

### Integración Automática

En `src/preprocessor.py`:

```python
if __name__ == "__main__":
    # Transformar Champions League si es necesario
    from transform_champions_league import transform_champions_league
    if transform_champions_league():
        print("[OK] Champions League transformado")
```

Ahora **cada vez que ejecutas preprocessor.py**, Champions League se transforma automáticamente.

---

## 🔄 Pasos para Agregar una NUEVA Liga

### 1. Crear el CSV en la estructura correcta

```
data/
  NuevaLiga/
    NuevaLiga25-26.csv  (archivo original con formato no estándar)
```

### 2. Crear `src/transform_nueva_liga.py`

Copia `transform_champions_league.py` y adapta:

```python
def transform_nueva_liga():
    """Transforma NuevaLiga al formato estándar"""
    
    input_file = Path(__file__).parent.parent / 'data' / 'NuevaLiga' / 'original.csv'
    output_file = Path(__file__).parent.parent / 'data' / 'NuevaLiga' / 'NuevaLiga25-26.csv'
    
    df = pd.read_csv(input_file)
    
    # 1. Mapear columnas
    output_df = pd.DataFrame({
        'Div': 'XX',  # Código de la liga (ej: CL, NL, etc.)
        'Date': pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y'),
        'HomeTeam': df['equipo_local'],
        'AwayTeam': df['equipo_visitante'],
        'FTHG': df['goles_casa'],
        'FTAG': df['goles_visita'],
        'FTR': df['resultado'].map({'local': 'H', 'visitante': 'A', 'empate': 'D'}),
        # ... más columnas
        'AvgH': df['cuota_h'],  # o calcular si no existe
        'AvgD': df['cuota_d'],
        'AvgA': df['cuota_a'],
    })
    
    output_df.to_csv(output_file, index=False)
    return True
```

### 3. Registrar en `preprocessor.py`

```python
# En LEAGUE_MAPPING:
LEAGUE_MAPPING = {
    # ... ligas existentes
    'NuevaLiga': 'XX'  # Código único
}
```

```python
# En if __name__ == "__main__":
from transform_nueva_liga import transform_nueva_liga
if transform_nueva_liga():
    print("[OK] NuevaLiga transformada")
```

### 4. Registrar en `main.py`

```python
LIGAS_DICT = {
    # ... ligas existentes
    'XX': '[PAÍS] NuevaLiga'
}
```

### 5. Validar

```bash
python src/validate_datasets.py data/NuevaLiga
```

Debería mostrar: `[OK] Tiene 15 columnas requeridas`

---

## ✅ Checklist para Nueva Liga

- [ ] CSV original en `data/NuevaLiga/`
- [ ] Script `src/transform_nueva_liga.py` creado
- [ ] Función registrada en `preprocessor.py` (`LEAGUE_MAPPING` + llamada en `__main__`)
- [ ] Código de liga agregado en `main.py` (`LIGAS_DICT`)
- [ ] Validación exitosa: `validate_datasets.py data/NuevaLiga`
- [ ] Test rápido: ejecutar `preprocessor.py` y ver que genera `dataset_final.csv` sin errores

---

## 📊 Columnas Requeridas (Obligatorias)

```
'Date', 'HomeTeam', 'AwayTeam', 
'FTHG', 'FTAG', 'FTR',         # Resultado final
'HS', 'AS',                     # Shots (total)
'HST', 'AST',                   # Shots on Target
'HC', 'AC',                     # Corners
'AvgH', 'AvgD', 'AvgA'         # Cuotas promedio
```

**Valores por Defecto (si no existen en original):**
- `HC`, `AC` (Corners) &rarr; `NaN`
- `AvgH`, `AvgD`, `AvgA` (Cuotas) &rarr; Estimadas según resultado (1.8/3.5/5.0)
- `HTHG`, `HTAG`, `HTR` (Medio tiempo) &rarr; `NaN`

---

## 🚀 Ejemplo: Agregar SuperCopa de Europa

```python
# data/SuperCopa/SuperCopa25-26.csv (formato no estándar)
# → transform_supercopa.py
# → data/SuperCopa/SuperCopa25-26.csv (formato estándar)

# LEAGUE_MAPPING: 'SuperCopa': 'SC'
# LIGAS_DICT: 'SC': '[EUROPA] SuperCopa'
```

---

## 🛠️ Troubleshooting

| Error | Solución |
|-------|----------|
| `[ERROR] Columnas FALTANTES: {...}` | Asegúrate que el output_df tenga todas las requeridas |
| `[WARN] No se pudo parsear las fechas` | Verifica formato de fecha (dd/mm/yyyy esperado) |
| `Total de partidos` muy bajo | Revisa que estés excluyendo filas con valores NaN |

---

## 📝 Notas

- **Código de liga**: Usa estándares de football-data.co.uk cuando sea posible
- **Transformación**: Siempre ejecutar **automáticamente** en `preprocessor.py`
- **Validación**: Siempre ejecutar `validate_datasets.py` antes de usar
- **Escalabilidad**: El sistema está diseñado para agregar N ligas sin cambiar la lógica principal

