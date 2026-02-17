# 🌍 Contexto Inteligente: Champions League + Liga Doméstica

## Problema Original
Muchos equipos de Champions League también juegan en sus ligas domésticas:
- **Juventus** juega en Serie A (Italia)
- **Galatasaray** juega en la Süper Lig (Turquía)
- **Real Madrid** juega en La Liga (España)

Cuando se predecía un partido de Champions, el modelo **solo veía datos de Champions League**, perdiendo contexto importante sobre el rendimiento general del equipo.

---

## Solución: Contexto Inteligente

### 1. Mapeo de Ligas Domésticas (`src/team_context.py`)
Se creó un mapeo de equipos europeos a sus ligas domésticas:

```python
TEAM_LEAGUE_MAP = {
    'Juventus': 'I1',        # Serie A
    'Galatasaray': 'T1',     # Süper Lig
    'Real Madrid': 'SP1',    # La Liga
    'Manchester City': 'E0', # Premier League
    # ... 50+ equipos mapeados
}
```

### 2. Función de Obtención de Datos con Contexto

```python
def get_team_data_with_context(df, team_name, as_home=True, match_league='CL'):
    """
    Para un partido de Champions League, mezcla:
    - 70% datos de Champions League (más específico)
    - 30% datos de Liga Doméstica (contexto general)
    """
```

**Ejemplo práctico:**
```
Partido: Juventus vs Inter (Champions League)

Juventus:
  ├─ Datos CL recientes: Promedio 2.5 goles/partido
  ├─ Datos Serie A recientes: Promedio 2.2 goles/partido
  └─ Resultado final (70/30): 2.43 goles esperados

Inter:
  ├─ Datos CL recientes: Promedio 1.8 goles/partido
  ├─ Datos Serie A recientes: Promedio 2.3 goles/partido
  └─ Resultado final (70/30): 1.99 goles esperados
```

---

## Integración en el Sistema

### En `main.py`
```python
# Ahora pasa la liga a predict_final_boss
predict_final_boss(local, visitante, h, d, a, match_league=liga)
```

### En `predict.py`
```python
# Usa contexto inteligente en lugar de búsqueda simple
h_row = get_team_data_with_context(df, local, as_home=True, match_league=match_league)
a_row = get_team_data_with_context(df, visitante, as_home=False, match_league=match_league)
```

El sistema automáticamente:
1. Detecta que es un partido de **Champions League** (`match_league='CL'`)
2. Busca la **liga doméstica** de cada equipo
3. Mezcla los datos **70% CL + 30% Liga Doméstica**
4. Usa este contexto combinado para la predicción

---

## Equipos Mapeados (55 Total)

### Serie A (Italia)
Juventus, Inter, AC Milan, AS Roma, Atalanta, Lazio, Fiorentina, Napoli, Udinese...

### Premier League (Inglaterra)
Manchester City, Manchester United, Liverpool, Arsenal, Chelsea, Tottenham, Newcastle, Brighton...

### La Liga (España)
Real Madrid, Barcelona, Atletico Madrid, Real Sociedad, Villarreal, Valencia, Sevilla...

### Bundesliga (Alemania)
Bayern Munich, Borussia Dortmund, RB Leipzig, Leverkusen, Eintracht Frankfurt...

### Ligue 1 (Francia)
Paris Saint-Germain, Monaco, Lyon, Marseille, Lens, Lille...

### Otras Ligas
- Süper Lig (Turquía): Galatasaray, Fenerbahçe, Besiktas, Trabzonspor
- Liga NOS (Portugal): Benfica, Porto, Sporting CP
- Jupiler Pro League (Bélgica): Club Brugge, Union SG, Anderlecht

---

## Uso en Predicciones

### Predicción de Champions League
```bash
$ python src/main.py
Opción 3: Predicción Asistida
Opción 2: Champions League (144 partidos)

SELECCIONA LIGA:
2. [EUROPA] Champions League | 144 partidos

Selecciona equipos y cuotas...

[INFO] Usando contexto de ligas domésticas:
   Juventus: Champions League + I1 (Serie A)
   Inter: Champions League + I1 (Serie A)
```

El modelo ahora considera:
- **Forma reciente en Champions** (datos específicos del torneo)
- **Forma general en su liga** (contexto de rendimiento)
- **Confrontación directa** (si hay datos previos en Champions)

---

## Ajustes por Liga

| Escenario | Mezcla | Razón |
|-----------|--------|-------|
| **Champions League** | 70% CL + 30% Dom | Torneo específico es más relevante |
| **Liga Nacional** | 60% Liga + 40% Dom | Liga doméstica es contexto |
| **Ambas iguales** | 50% / 50% | Cuando la información es similar |

---

## Ventajas

✅ **Contexto más rico** - Las predicciones ven más datos del equipo  
✅ **Evita sesgos** - No sobrepesa un solo torneo  
✅ **Automático** - Se detecta la liga doméstica sin intervención  
✅ **Escalable** - Fácil agregar más equipos al mapeo  
✅ **Inteligente** - Usa pesos diferentes según el tipo de partido  

---

## Extensión Futura

Para agregar más equipos o cambiar los pesos de mezcla:

```python
# En src/team_context.py

# 1. Agregar equipo
TEAM_LEAGUE_MAP['Dinamo Zagreb'] = 'HR'  # Liga croata

# 2. Cambiar pesos de mezcla
def get_team_data_with_context(...):
    cl_weight = 0.8  # Aumentar a 80% en lugar de 70%
    domestic_weight = 0.2
```

---

## Resumen Técnico

**Archivos modificados:**
- `src/team_context.py` (nuevo) - Mapeo y lógica de contexto
- `src/predict.py` - Integración de contexto inteligente  
- `src/main.py` - Paso de parámetro de liga

**Flujo:**
```
[Usuario selecciona Champions League] 
  ↓
[main.py → predict_final_boss(liga='CL')] 
  ↓
[predict.py detecta CL y usa get_team_data_with_context] 
  ↓
[team_context.py busca liga doméstica de cada equipo] 
  ↓
[Mezcla datos: 70% CL + 30% Liga Doméstica] 
  ↓
[Modelo hace predicción con contexto rico]
```

