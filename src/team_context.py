"""
Mapeo inteligente de equipos a sus ligas domésticas.
Permite mezclar contexto de Champions League + Liga Doméstica.
"""

import pandas as pd
import numpy as np

# Mapeo manual de equipos europeos a sus ligas domésticas
# Format: {'Equipo': 'Código_Liga_Doméstica'}
TEAM_LEAGUE_MAP = {
    # Serie A (Italia)
    'Juventus': 'I1', 'Inter': 'I1', 'AC Milan': 'I1', 'AS Roma': 'I1',
    'Atalanta': 'I1', 'Lazio': 'I1', 'Fiorentina': 'I1', 'Napoli': 'I1',
    'Udinese': 'I1', 'Torino': 'I1', 'Sassuolo': 'I1', 'Bologna': 'I1',
    
    # Premier League (Inglaterra)
    'Manchester City': 'E0', 'Manchester United': 'E0', 'Liverpool': 'E0',
    'Arsenal': 'E0', 'Chelsea': 'E0', 'Tottenham': 'E0', 'Newcastle': 'E0',
    'Brighton': 'E0', 'Aston Villa': 'E0', 'West Ham': 'E0',
    
    # La Liga (España)
    'Real Madrid': 'SP1', 'Barcelona': 'SP1', 'Atletico Madrid': 'SP1',
    'Real Sociedad': 'SP1', 'Villarreal': 'SP1', 'Valencia': 'SP1',
    'Sevilla': 'SP1', 'Athletic Club': 'SP1', 'Real Betis': 'SP1',
    
    # Bundesliga (Alemania)
    'Bayern Munich': 'D1', 'Borussia Dortmund': 'D1', 'RB Leipzig': 'D1',
    'Leverkusen': 'D1', 'Eintracht Frankfurt': 'D1', 'Union Berlin': 'D1',
    'Cologne': 'D1', 'Wolfsburg': 'D1',
    
    # Ligue 1 (Francia)
    'Paris Saint-Germain': 'L1', 'Monaco': 'L1', 'Lyon': 'L1',
    'Marseille': 'L1', 'Lens': 'L1', 'Lille': 'L1',
    
    # Liga NOS (Portugal)
    'Benfica': 'P1', 'Porto': 'P1', 'Sporting CP': 'P1',
    
    # Süper Lig (Turquía)
    'Galatasaray': 'T1', 'Fenerbahçe': 'T1', 'Besiktas': 'T1',
    'Trabzonspor': 'T1',
    
    # Jupiler Pro League (Bélgica)
    'Club Brugge': 'B1', 'Union SG': 'B1', 'Anderlecht': 'B1',
}

def get_domestic_league(team_name):
    """
    Detecta la liga doméstica de un equipo.
    
    Args:
        team_name (str): Nombre del equipo
        
    Returns:
        str: Código de la liga doméstica (ej: 'I1', 'E0', etc.) o None
    """
    # Búsqueda exacta primero
    if team_name in TEAM_LEAGUE_MAP:
        return TEAM_LEAGUE_MAP[team_name]
    
    # Búsqueda parcial (case-insensitive)
    team_lower = team_name.lower()
    for mapped_team, league in TEAM_LEAGUE_MAP.items():
        if team_lower in mapped_team.lower() or mapped_team.lower() in team_lower:
            return league
    
    return None

def get_team_data_with_context(df, team_name, as_home=True, match_league='CL'):
    """
    Obtiene datos de un equipo, mezclando Champions League + Liga Doméstica.
    
    Si estamos prediciendo un partido de Champions League, da prioridad a:
    1. Datos recientes de Champions League (si existen)
    2. Datos de su liga doméstica (para contexto general)
    
    Args:
        df (pd.DataFrame): Dataset completo
        team_name (str): Nombre del equipo
        as_home (bool): Si buscamos datos como local (True) o visitante (False)
        match_league (str): Liga en que se juega el partido (ej: 'CL')
        
    Returns:
        pd.Series: Fila con datos más relevantes para la predicción
    """
    
    # 1. Buscar datos en Champions League (más reciente)
    if match_league == 'CL':
        role_col = 'HomeTeam' if as_home else 'AwayTeam'
        cl_data = df[(df['Div'] == 'CL') & (df[role_col] == team_name)]
        
        if not cl_data.empty:
            # Preferir datos recientes de CL
            cl_row = cl_data.sort_values('Date').iloc[-1]
            
            # Si tenemos datos de CL y hay liga doméstica, mezclar
            domestic_league = get_domestic_league(team_name)
            if domestic_league:
                domestic_data = df[(df['Div'] == domestic_league) & (df[role_col] == team_name)]
                if not domestic_data.empty:
                    domestic_row = domestic_data.sort_values('Date').iloc[-1]
                    
                    # Mezclar datos: 70% CL + 30% Liga Doméstica
                    blended_row = cl_row.copy()
                    
                    # Obtener columnas numéricas y mezclar
                    for col in blended_row.index:
                        try:
                            cl_val = cl_row[col]
                            dom_val = domestic_row[col] if col in domestic_row.index else None
                            if pd.notna(cl_val) and pd.notna(dom_val):
                                # Mezcla: 70% CL + 30% Doméstica
                                if isinstance(cl_val, (int, float)) and isinstance(dom_val, (int, float)):
                                    blended_row[col] = cl_val * 0.7 + dom_val * 0.3
                        except:
                            pass
                    
                    return blended_row
            
            return cl_row
    
    # 2. Si no es Champions o no hay datos de CL, buscar con contexto doméstico
    role_col = 'HomeTeam' if as_home else 'AwayTeam'
    main_data = df[(df['Div'] == match_league) & (df[role_col] == team_name)]
    
    if not main_data.empty:
        primary_row = main_data.sort_values('Date').iloc[-1]
        
        # Intentar mezclar con liga doméstica si existe
        domestic_league = get_domestic_league(team_name)
        if domestic_league and domestic_league != match_league:
            domestic_data = df[(df['Div'] == domestic_league) & (df[role_col] == team_name)]
            if not domestic_data.empty:
                domestic_row = domestic_data.sort_values('Date').iloc[-1]
                
                # Mezclar: 60% Liga principal + 40% Liga doméstica
                blended_row = primary_row.copy()
                
                for col in blended_row.index:
                    try:
                        primary_val = primary_row[col]
                        dom_val = domestic_row[col] if col in domestic_row.index else None
                        if pd.notna(primary_val) and pd.notna(dom_val):
                            if isinstance(primary_val, (int, float)) and isinstance(dom_val, (int, float)):
                                blended_row[col] = primary_val * 0.6 + dom_val * 0.4
                    except:
                        pass
                
                return blended_row
        
        return primary_row
    
    # 3. Si aún no encontramos nada, buscar en cualquier liga (fallback)
    any_data = df[df['HomeTeam' if as_home else 'AwayTeam'] == team_name]
    if not any_data.empty:
        return any_data.sort_values('Date').iloc[-1]
    
    return None


def fill_missing_stats(row, df, team_name, as_home=True):
    """
    Rellena valores NaN con promedios REALES del equipo del dataset.
    Nunca inventa números - solo usa datos que existen.
    
    Args:
        row (pd.Series): Fila con datos potencialmente incompletos
        df (pd.DataFrame): Dataset completo para calcular promedios
        team_name (str): Nombre del equipo
        as_home (bool): Si estamos buscando como local o visitante
    
    Returns:
        pd.Series: Row con valores completados usando datos reales
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
    opp_col = 'AwayTeam' if as_home else 'HomeTeam'
    
    # Obtener datos reales del equipo en CUALQUIER liga
    team_data = df[df[role_col] == team_name]
    
    for col in cols_to_fill:
        if col in row.index and pd.isna(row[col]):
            # Intentar obtener promedio real del equipo
            if col in team_data.columns:
                avg_val = team_data[col].mean()
                if pd.notna(avg_val) and not np.isnan(avg_val):
                    row[col] = avg_val
                    continue
            
            # Si no hay datos del equipo en ese rol, buscar el promedio GLOBAL
            # (de todos los equipos) para NO inventar números
            if col in df.columns:
                global_avg = df[col].mean()
                if pd.notna(global_avg) and not np.isnan(global_avg):
                    row[col] = global_avg
                else:
                    # Última opción: marcar como 0 pero NO inventar
                    row[col] = 0.0
    
    return row
