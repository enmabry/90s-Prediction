"""
Mapeo inteligente de equipos a sus ligas domésticas.
Permite mezclar contexto de Champions League + Liga Doméstica.
Incluye: auto-mapeo, alias de nombres, forma reciente, H2H.
"""

import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════
# 1. ALIAS: Nombre CL → Nombre en liga doméstica
#    Resuelve diferencias entre fuentes de datos
# ═══════════════════════════════════════════════════════════
NAME_ALIASES = {
    # CL name → domestic name
    'Manchester City': 'Man City',
    'Manchester United': 'Man United',
    'Newcastle United': 'Newcastle',
    'Tottenham Hotspur': 'Tottenham',
    'Paris Saint-Germain': 'Paris SG',
    'Eintracht Frankfurt': 'Ein Frankfurt',
    'Athletic Club': 'Ath Bilbao',
    'Atlético Madrid': 'Ath Madrid',
    'Borussia Dortmund': 'Dortmund',
    'Sporting CP': 'Sp Lisbon',
    # Alias inversos (por si acaso el dataset usa el nombre largo)
    'Man City': 'Manchester City',
    'Man United': 'Manchester United',
    'Newcastle': 'Newcastle United',
    'Tottenham': 'Tottenham Hotspur',
    'Paris SG': 'Paris Saint-Germain',
    'Ein Frankfurt': 'Eintracht Frankfurt',
    'Ath Bilbao': 'Athletic Club',
    'Ath Madrid': 'Atlético Madrid',
    'Sp Lisbon': 'Sporting CP',
}

# ═══════════════════════════════════════════════════════════
# 2. MAPEO MANUAL: Equipo → Liga doméstica
#    Para equipos cuya liga doméstica NO está en el dataset
# ═══════════════════════════════════════════════════════════
TEAM_LEAGUE_MAP = {
    # Serie A (Italia)
    'Juventus': 'I1', 'Inter': 'I1', 'AC Milan': 'I1', 'AS Roma': 'I1',
    'Atalanta': 'I1', 'Lazio': 'I1', 'Fiorentina': 'I1', 'Napoli': 'I1',
    'Udinese': 'I1', 'Torino': 'I1', 'Sassuolo': 'I1', 'Bologna': 'I1',
    
    # Premier League (Inglaterra)
    'Manchester City': 'E0', 'Man City': 'E0', 'Manchester United': 'E0',
    'Man United': 'E0', 'Liverpool': 'E0', 'Arsenal': 'E0', 'Chelsea': 'E0',
    'Tottenham': 'E0', 'Tottenham Hotspur': 'E0', 'Newcastle': 'E0',
    'Newcastle United': 'E0', 'Brighton': 'E0', 'Aston Villa': 'E0', 'West Ham': 'E0',
    
    # La Liga (España)
    'Real Madrid': 'SP1', 'Barcelona': 'SP1', 'Atletico Madrid': 'SP1',
    'Atlético Madrid': 'SP1', 'Ath Madrid': 'SP1',
    'Real Sociedad': 'SP1', 'Villarreal': 'SP1', 'Valencia': 'SP1',
    'Sevilla': 'SP1', 'Athletic Club': 'SP1', 'Ath Bilbao': 'SP1', 'Real Betis': 'SP1',
    
    # Bundesliga (Alemania)
    'Bayern Munich': 'D1', 'Borussia Dortmund': 'D1', 'Dortmund': 'D1',
    'RB Leipzig': 'D1', 'Leverkusen': 'D1',
    'Eintracht Frankfurt': 'D1', 'Ein Frankfurt': 'D1',
    'Union Berlin': 'D1', 'Cologne': 'D1', 'Wolfsburg': 'D1',
    
    # Ligue 1 (Francia)
    'Paris Saint-Germain': 'F1', 'Paris SG': 'F1', 'Monaco': 'F1', 'Lyon': 'F1',
    'Marseille': 'F1', 'Lens': 'F1', 'Lille': 'F1',
    
    # Liga NOS (Portugal)
    'Benfica': 'P1', 'Porto': 'P1', 'Sporting CP': 'P1', 'Sp Lisbon': 'P1',
    
    # Süper Lig (Turquía)
    'Galatasaray': 'T1', 'Fenerbahçe': 'T1', 'Besiktas': 'T1', 'Trabzonspor': 'T1',
    
    # Jupiler Pro League (Bélgica)
    'Club Brugge': 'B1', 'Union SG': 'B1', 'Anderlecht': 'B1',
}


def resolve_team_name(team_name, df):
    """
    Resuelve el nombre de un equipo CL al nombre que usa en la liga doméstica.
    Busca tanto por alias directo como por coincidencia en el dataset.
    
    Args:
        team_name: Nombre del equipo (como aparece en CL)
        df: Dataset completo
        
    Returns:
        str: Nombre doméstico del equipo (o el original si no hay alias)
    """
    # 1. Alias directo
    if team_name in NAME_ALIASES:
        alias = NAME_ALIASES[team_name]
        # Verificar que el alias existe realmente en el dataset doméstico
        dom_teams = df[df['Div'] != 'CL']
        all_teams = set(dom_teams['HomeTeam'].unique()) | set(dom_teams['AwayTeam'].unique())
        if alias in all_teams:
            return alias
    
    # 2. Ya existe con su nombre actual
    dom_teams = df[df['Div'] != 'CL']
    all_teams = set(dom_teams['HomeTeam'].unique()) | set(dom_teams['AwayTeam'].unique())
    if team_name in all_teams:
        return team_name
    
    # 3. Búsqueda fuzzy: primera/última palabra
    team_lower = team_name.lower()
    words = team_lower.split()
    for t in all_teams:
        t_lower = t.lower()
        # Coincidencia parcial significativa
        if (len(words) > 0 and words[0] in t_lower and len(words[0]) > 3) or \
           (len(words) > 1 and words[-1] in t_lower and len(words[-1]) > 3):
            return t
    
    return team_name  # sin alias encontrado


def get_domestic_league(team_name, df=None):
    """
    Detecta la liga doméstica de un equipo.
    Primero busca en el mapeo manual, luego auto-detecta del dataset.
    
    Args:
        team_name: Nombre del equipo
        df: Dataset completo (opcional, para auto-detección)
        
    Returns:
        str: Código de liga doméstica o None
    """
    # 1. Mapeo manual (incluye alias)
    if team_name in TEAM_LEAGUE_MAP:
        return TEAM_LEAGUE_MAP[team_name]
    
    # 2. Buscar alias y luego mapeo manual
    for alias_from, alias_to in NAME_ALIASES.items():
        if team_name == alias_from and alias_to in TEAM_LEAGUE_MAP:
            return TEAM_LEAGUE_MAP[alias_to]
        if team_name == alias_to and alias_from in TEAM_LEAGUE_MAP:
            return TEAM_LEAGUE_MAP[alias_from]
    
    # 3. Auto-detección del dataset
    if df is not None:
        dom_data = df[df['Div'] != 'CL']
        # Buscar con nombre exacto
        team_matches = dom_data[(dom_data['HomeTeam'] == team_name) | (dom_data['AwayTeam'] == team_name)]
        if not team_matches.empty:
            return team_matches['Div'].mode()[0]
        
        # Buscar con alias
        resolved = resolve_team_name(team_name, df)
        if resolved != team_name:
            team_matches = dom_data[(dom_data['HomeTeam'] == resolved) | (dom_data['AwayTeam'] == resolved)]
            if not team_matches.empty:
                return team_matches['Div'].mode()[0]
    
    return None


def get_recent_form(df, team_name, n=5):
    """
    Calcula la forma reciente de un equipo (últimos N partidos).
    
    Returns:
        dict: {
            'form_points': puntos en últimos N (0-15),
            'form_ratio': ratio de puntos (0.0-1.0),
            'form_goals_scored': goles a favor recientes,
            'form_goals_conceded': goles en contra recientes,
            'form_wins': victorias recientes,
            'form_streak': racha actual (+N victorias, -N derrotas, 0 empates)
        }
    """
    defaults = {
        'form_points': 7.5, 'form_ratio': 0.5,
        'form_goals_scored': 1.3, 'form_goals_conceded': 1.1,
        'form_wins': 2, 'form_streak': 0
    }
    
    # Buscar partidos del equipo (home o away, cualquier liga)
    home_matches = df[df['HomeTeam'] == team_name].copy()
    away_matches = df[df['AwayTeam'] == team_name].copy()
    
    # Normalizar a formato común
    records = []
    for _, row in home_matches.iterrows():
        if pd.notna(row.get('FTR')) and pd.notna(row.get('Date')):
            gf = row.get('FTHG', 0) or 0
            ga = row.get('FTAG', 0) or 0
            pts = 3 if row['FTR'] == 'H' else (1 if row['FTR'] == 'D' else 0)
            records.append({'date': row['Date'], 'gf': gf, 'ga': ga, 'pts': pts, 'result': row['FTR']})
    
    for _, row in away_matches.iterrows():
        if pd.notna(row.get('FTR')) and pd.notna(row.get('Date')):
            gf = row.get('FTAG', 0) or 0
            ga = row.get('FTHG', 0) or 0
            pts = 3 if row['FTR'] == 'A' else (1 if row['FTR'] == 'D' else 0)
            records.append({'date': row['Date'], 'gf': gf, 'ga': ga, 'pts': pts, 'result': row['FTR']})
    
    if not records:
        return defaults
    
    # Ordenar por fecha, tomar los últimos N
    records.sort(key=lambda x: x['date'], reverse=True)
    recent = records[:n]
    
    total_pts = sum(r['pts'] for r in recent)
    
    # Calcular racha (consecutivos del mismo resultado)
    streak = 0
    if recent:
        last_pts = recent[0]['pts']
        for r in recent:
            if r['pts'] == last_pts:
                streak += 1
            else:
                break
        if last_pts == 0:
            streak = -streak  # Racha negativa = derrotas
    
    return {
        'form_points': total_pts,
        'form_ratio': total_pts / (n * 3),
        'form_goals_scored': sum(r['gf'] for r in recent) / len(recent),
        'form_goals_conceded': sum(r['ga'] for r in recent) / len(recent),
        'form_wins': sum(1 for r in recent if r['pts'] == 3),
        'form_streak': streak
    }


def get_h2h(df, team_a, team_b, n=10):
    """
    Obtiene historial de enfrentamientos directos entre dos equipos.
    
    Returns:
        dict: {
            'h2h_matches': total partidos,
            'h2h_wins_a': victorias de team_a,
            'h2h_wins_b': victorias de team_b,
            'h2h_draws': empates,
            'h2h_goals_a': goles promedio team_a,
            'h2h_goals_b': goles promedio team_b,
            'h2h_advantage_a': ventaja de team_a (-1 a 1)
        }
    """
    defaults = {
        'h2h_matches': 0, 'h2h_wins_a': 0, 'h2h_wins_b': 0,
        'h2h_draws': 0, 'h2h_goals_a': 1.2, 'h2h_goals_b': 1.2,
        'h2h_advantage_a': 0.0
    }
    
    # También buscar alias
    names_a = {team_a}
    names_b = {team_b}
    if team_a in NAME_ALIASES:
        names_a.add(NAME_ALIASES[team_a])
    if team_b in NAME_ALIASES:
        names_b.add(NAME_ALIASES[team_b])
    
    # Filtrar enfrentamientos directos (A vs B o B vs A)
    mask_ab = (df['HomeTeam'].isin(names_a)) & (df['AwayTeam'].isin(names_b))
    mask_ba = (df['HomeTeam'].isin(names_b)) & (df['AwayTeam'].isin(names_a))
    
    h2h_data = df[mask_ab | mask_ba].sort_values('Date', ascending=False).head(n)
    
    if h2h_data.empty:
        return defaults
    
    wins_a = 0
    wins_b = 0
    draws = 0
    goals_a = []
    goals_b = []
    
    for _, row in h2h_data.iterrows():
        ftr = row.get('FTR', '')
        hg = float(row.get('FTHG', 0) or 0)
        ag = float(row.get('FTAG', 0) or 0)
        
        if row['HomeTeam'] in names_a:
            # A es local
            goals_a.append(hg)
            goals_b.append(ag)
            if ftr == 'H': wins_a += 1
            elif ftr == 'A': wins_b += 1
            else: draws += 1
        else:
            # B es local, A es visitante
            goals_a.append(ag)
            goals_b.append(hg)
            if ftr == 'A': wins_a += 1
            elif ftr == 'H': wins_b += 1
            else: draws += 1
    
    total = len(h2h_data)
    avg_ga = np.mean(goals_a) if goals_a else 1.2
    avg_gb = np.mean(goals_b) if goals_b else 1.2
    
    # Ventaja: +1 = domina team_a, -1 = domina team_b, 0 = equilibrado
    advantage = (wins_a - wins_b) / total if total > 0 else 0.0
    
    return {
        'h2h_matches': total,
        'h2h_wins_a': wins_a,
        'h2h_wins_b': wins_b,
        'h2h_draws': draws,
        'h2h_goals_a': avg_ga,
        'h2h_goals_b': avg_gb,
        'h2h_advantage_a': advantage
    }


def get_team_data_with_context(df, team_name, as_home=True, match_league='CL'):
    """
    Obtiene datos de un equipo, mezclando Champions League + Liga Doméstica.
    Usa alias para encontrar equipos con nombres diferentes entre CL y liga doméstica.
    """
    role_col = 'HomeTeam' if as_home else 'AwayTeam'
    
    # Resolver alias para búsqueda doméstica
    domestic_name = resolve_team_name(team_name, df)
    domestic_league = get_domestic_league(team_name, df)
    
    if match_league == 'CL':
        # Buscar datos CL con nombre CL
        cl_data = df[(df['Div'] == 'CL') & (df[role_col] == team_name)]
        
        if not cl_data.empty:
            cl_row = cl_data.sort_values('Date').iloc[-1]
            
            # Mezclar con liga doméstica si existe
            if domestic_league:
                # Buscar con nombre doméstico (alias)
                search_name = domestic_name if domestic_name != team_name else team_name
                domestic_data = df[(df['Div'] == domestic_league) & (df[role_col] == search_name)]
                
                # Si no hay resultado, intentar con nombre original
                if domestic_data.empty and search_name != team_name:
                    domestic_data = df[(df['Div'] == domestic_league) & (df[role_col] == team_name)]
                
                if not domestic_data.empty:
                    domestic_row = domestic_data.sort_values('Date').iloc[-1]
                    
                    # Mezclar: 70% CL + 30% Doméstica
                    blended_row = cl_row.copy()
                    for col in blended_row.index:
                        try:
                            cl_val = cl_row[col]
                            dom_val = domestic_row[col] if col in domestic_row.index else None
                            if pd.notna(cl_val) and pd.notna(dom_val):
                                if isinstance(cl_val, (int, float, np.integer, np.floating)) and \
                                   isinstance(dom_val, (int, float, np.integer, np.floating)):
                                    blended_row[col] = cl_val * 0.7 + dom_val * 0.3
                        except:
                            pass
                    return blended_row
            
            return cl_row
    
    # Liga doméstica normal
    main_data = df[(df['Div'] == match_league) & (df[role_col] == team_name)]
    if not main_data.empty:
        return main_data.sort_values('Date').iloc[-1]
    
    # Fallback: cualquier liga
    any_data = df[df[role_col] == team_name]
    if not any_data.empty:
        return any_data.sort_values('Date').iloc[-1]
    
    # Último intento: buscar con alias
    if domestic_name != team_name:
        any_data = df[df[role_col] == domestic_name]
        if not any_data.empty:
            return any_data.sort_values('Date').iloc[-1]
    
    return None


def get_cl_stats(df, team_name, as_home=True, exclude_opponent=None):
    """
    Obtiene promedios REALES de un equipo en Champions League (home o away).
    Sirve para corregir la predicción del modelo en partidos CL.
    exclude_opponent: excluir partidos contra este rival (evita data leakage)
    
    Returns:
        dict: {
            'cl_shots': media de tiros,
            'cl_shots_target': media de tiros a puerta,
            'cl_corners': media de corners,
            'cl_n': número de partidos CL en ese rol
        } o None si no hay datos
    """
    cl_data = df[df['Div'] == 'CL']
    
    if as_home:
        team_cl = cl_data[cl_data['HomeTeam'] == team_name]
        if exclude_opponent:
            team_cl = team_cl[team_cl['AwayTeam'] != exclude_opponent]
        shots_col, st_col, c_col = 'HS', 'HST', 'HC'
    else:
        team_cl = cl_data[cl_data['AwayTeam'] == team_name]
        if exclude_opponent:
            team_cl = team_cl[team_cl['HomeTeam'] != exclude_opponent]
        shots_col, st_col, c_col = 'AS', 'AST', 'AC'
    
    if team_cl.empty:
        return None
    
    return {
        'cl_shots': team_cl[shots_col].mean(),
        'cl_shots_target': team_cl[st_col].mean(),
        'cl_corners': team_cl[c_col].mean(),
        'cl_n': len(team_cl)
    }


def fill_missing_stats(row, df, team_name, as_home=True):
    """
    Rellena valores NaN con promedios REALES del equipo del dataset.
    Nunca inventa números - solo usa datos que existen.
    """
    cols_to_fill = [
        'Expected_Corners_Home', 'Expected_Corners_Away',
        'Expected_Shots_Home', 'Expected_Shots_Away',
        'Expected_ST_Home', 'Expected_ST_Away',
        'Expected_Shots_Home_With_Possession', 'Expected_Shots_Away_With_Possession',
        'Expected_ST_Home_Possession', 'Expected_ST_Away_Possession',
        'Corner_Share_Home', 'Corner_Share_Away',
        'Shot_Share_Home', 'Shot_Share_Away',
        'HC', 'AC', 'HS', 'AS', 'HST', 'AST'
    ]
    
    role_col = 'HomeTeam' if as_home else 'AwayTeam'
    
    # Obtener datos reales del equipo en CUALQUIER liga (incluye alias)
    team_data = df[df[role_col] == team_name]
    if team_data.empty:
        # Intentar con alias
        resolved = resolve_team_name(team_name, df)
        if resolved != team_name:
            team_data = df[df[role_col] == resolved]
    
    for col in cols_to_fill:
        if col in row.index and pd.isna(row[col]):
            if col in team_data.columns and not team_data.empty:
                avg_val = team_data[col].mean()
                if pd.notna(avg_val):
                    row[col] = avg_val
                    continue
            
            if col in df.columns:
                global_avg = df[col].mean()
                if pd.notna(global_avg):
                    row[col] = global_avg
                else:
                    row[col] = 0.0
    
    return row
