import pandas as pd
import glob
import os
import warnings
import numpy as np
from pandas.errors import PerformanceWarning

warnings.simplefilter(action='ignore', category=PerformanceWarning)

# Mapeo de carpetas a códigos de liga (EXTENSIBLE)
# NOTA: Los códigos siguen el estándar de football-data.co.uk
# D1=Bundesliga, E0=Premier, E1=Championship, SP1=LaLiga, I1=Serie A
# L1=Ligue1, B1=Bélgica, F1=Francia, T1=Turquía, P1=Portugal
LEAGUE_MAPPING = {
    'Bundesliga': 'D1',
    'LaLiga': 'SP1',
    'PremierLeague': 'E0',
    'Championship': 'E1',
    'Ligue1': 'L1',
    'SerieA': 'I1',
    'JupiterLeagueBelgium': 'B1',
    'LigueOneFrancia': 'F1',
    'TurkeyLeague': 'T1',
    'PortugalLeague': 'P1'  # Código estándar para Serie A (Italia)
}

def get_league_code(filepath):
    """Detecta automáticamente el código de liga desde la ruta del archivo"""
    for folder_name, code in LEAGUE_MAPPING.items():
        if folder_name in filepath:
            return code
    return 'Unknown'

def calculate_dynamic_standings(df):
    """
    Calcula la tabla clasificatoria dinámica para cada fecha y LIGA (CONSCIENTE DE RESULTADOS).
    Reconstruye la tabla después de cada jornada usando:
    - Puntos: 3 victoria, 1 empate, 0 derrota
    - Diferencia de goles
    - Goles a favor
    
    Args:
        df: DataFrame con columnas Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, Div
    
    Returns:
        dict: Para cada (fecha, liga, equipo) -> {'position': int, 'points': int, 'gd': int}
    """
    standings_dict = {}
    
    # Ordenar por fecha para procesar cronológicamente
    df_sorted = df.sort_values('Date').copy()
    df_sorted['Date'] = pd.to_datetime(df_sorted['Date'])
    dates = sorted(df_sorted['Date'].unique())
    ligas = df_sorted['Div'].unique()
    
    # Crear stats por liga
    team_stats_by_league = {liga: {} for liga in ligas}
    
    for date in dates:
        matches_today = df_sorted[df_sorted['Date'] == date]
        
        # Procesar cada partido de hoy
        for _, match in matches_today.iterrows():
            home = match['HomeTeam']
            away = match['AwayTeam']
            liga = match['Div']
            
            team_stats = team_stats_by_league[liga]
            
            # Inicializar si no existen en esta liga
            if home not in team_stats:
                team_stats[home] = {'points': 0, 'played': 0, 'gf': 0, 'ga': 0}
            if away not in team_stats:
                team_stats[away] = {'points': 0, 'played': 0, 'gf': 0, 'ga': 0}
            
            # Obtener resultado (validar NaN)
            try:
                fthg = int(match['FTHG']) if pd.notna(match['FTHG']) else 0
                ftag = int(match['FTAG']) if pd.notna(match['FTAG']) else 0
                ftr = match['FTR'] if pd.notna(match['FTR']) else 'D'
            except:
                continue
            
            # Actualizar goles
            team_stats[home]['gf'] += fthg
            team_stats[home]['ga'] += ftag
            team_stats[home]['played'] += 1
            
            team_stats[away]['gf'] += ftag
            team_stats[away]['ga'] += fthg
            team_stats[away]['played'] += 1
            
            # Asignar puntos según resultado (3-1-0)
            if ftr == 'H':  # Home win
                team_stats[home]['points'] += 3
            elif ftr == 'A':  # Away win
                team_stats[away]['points'] += 3
            elif ftr == 'D':  # Draw
                team_stats[home]['points'] += 1
                team_stats[away]['points'] += 1
        
        # Calcular tabla para CADA LIGA
        for liga in ligas:
            team_stats = team_stats_by_league[liga]
            
            # Calcular tabla ordenada por:
            # 1. Puntos (descendente)
            # 2. Diferencia de goles (descendente)
            # 3. Goles a favor (descendente)
            standings = sorted(
                [
                    (team, stats['points'], stats['gf'] - stats['ga'], stats['gf'])
                    for team, stats in team_stats.items()
                ],
                key=lambda x: (-x[1], -x[2], -x[3])  # Puntos, GD, GF
            )
            
            # Guardar standings para esta fecha y liga
            for position, (team, points, gd, gf) in enumerate(standings, 1):
                standings_dict[(date, liga, team)] = {
                    'position': position,
                    'points': points,
                    'gd': gd,
                    'gf': gf
                }
    
    return standings_dict

def calculate_h2h_stats(df, n_recent=3):
    """
    Calcula estadísticas HEAD-TO-HEAD recientes entre equipos.
    Identifica "bestias negras" - equipos que sistemáticamente ganan a otros.
    
    Args:
        df: DataFrame con partidos
        n_recent: Últimos N enfrentamientos a considerar
    
    Returns:
        dict: Para cada (HomeTeam, AwayTeam) -> {'h2h_wins_home': int, 'h2h_wins_away': int}
    """
    h2h_dict = {}
    df_sorted = df.sort_values('Date').copy()
    
    for idx, row in df_sorted.iterrows():
        home = row['HomeTeam']
        away = row['AwayTeam']
        ftr = row['FTR'] if pd.notna(row['FTR']) else 'D'
        
        # Inicializar si no existe este H2H
        key = (home, away)
        if key not in h2h_dict:
            h2h_dict[key] = {'wins_home': 0, 'wins_away': 0, 'history': []}
        
        # Registrar resultado
        if ftr == 'H':
            h2h_dict[key]['wins_home'] += 1
            h2h_dict[key]['history'].append('H')
        elif ftr == 'A':
            h2h_dict[key]['wins_away'] += 1
            h2h_dict[key]['history'].append('A')
        else:
            h2h_dict[key]['history'].append('D')
    
    # Filtrar solo los últimos N encuentros
    h2h_reciente = {}
    for key, stats in h2h_dict.items():
        recent_history = stats['history'][-n_recent:]
        h2h_reciente[key] = {
            'h2h_wins_home': recent_history.count('H'),
            'h2h_wins_away': recent_history.count('A'),
            'h2h_draws': recent_history.count('D')
        }
    
    return h2h_reciente

def get_rolling_stats(df, n_games=5):
    # Definimos las métricas base
    # Ofensivas: Tiros (S), Tiros a Puerta (ST), Corners (C)
    # Defensivas: Tiros Recibidos (OppS), Tiros a Puerta Recibidos (OppST), Corners Recibidos (OppC)
    
    # --- PASO 0A: CALCULAR H2H STATS ---
    h2h_stats = calculate_h2h_stats(df)
    
    # --- PASO 0: CALCULAR STANDINGS (ANTES DE PERDER Div) ---
    # Hacer esto primero para que Div siga presente en el dataframe
    standings = calculate_dynamic_standings(df)
    
    # --- PASO 1: CREAR REGISTROS INDIVIDUALES POR EQUIPO ---
    home_stats = df[['Date', 'HomeTeam', 'HS', 'HST', 'HC', 'AS', 'AST', 'AC']].copy()
    home_stats.columns = ['Date', 'Team', 'S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    home_stats['IsHome'] = 1

    away_stats = df[['Date', 'AwayTeam', 'AS', 'AST', 'AC', 'HS', 'HST', 'HC']].copy()
    away_stats.columns = ['Date', 'Team', 'S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    away_stats['IsHome'] = 0

    combined = pd.concat([home_stats, away_stats]).sort_values(['Team', 'Date'])

    # --- PASO 2: MEDIAS PONDERADAS EXPONENCIALES (EWM) - HYBRID MEMORY ---
    # EWM (Exponential Weighted Moving Average) da MÁS peso a los partidos recientes
    # pero CONSERVA la memoria histórica (no la olvida como rolling())
    # span=n_games: define qué tan rápido "olvida" el pasado lejano
    features = ['S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    
    # A. Media Exponencial General (Forma reciente con memoria histórica)
    for f in features:
        combined[f'rolling_{f}_{n_games}'] = combined.groupby('Team')[f].transform(
            lambda x: x.ewm(span=n_games, adjust=False).mean().shift(1)
        )
    
    # B. Desviación Estándar Móvil (Inestabilidad) - Sigue siendo rolling
    # porque EWM no tiene std incorporado de forma eficiente
    for f in features:
        combined[f'std_{f}_{n_games}'] = combined.groupby('Team')[f].transform(
            lambda x: x.rolling(window=n_games, min_periods=1).std().shift(1)
        )
    
    # C. Media Exponencial por ROL (Local/Visitante con memoria)
    for f in features:
        combined[f'rolling_{f}_{n_games}_Role'] = combined.groupby(['Team', 'IsHome'])[f].transform(
            lambda x: x.ewm(span=n_games, adjust=False).mean().shift(1)
        )
    
    # D. Desviación Estándar por ROL (Inestabilidad en casa vs fuera)
    for f in features:
        combined[f'std_{f}_{n_games}_Role'] = combined.groupby(['Team', 'IsHome'])[f].transform(
            lambda x: x.rolling(window=n_games, min_periods=1).std().shift(1)
        )

    # --- PASO 3: REINTEGRAR AL DATAFRAME ORIGINAL ---
    # Unimos para el Local
    df = df.merge(combined, left_on=['Date', 'HomeTeam'], right_on=['Date', 'Team'], how='left').drop('Team', axis=1)
    
    # Unimos para el Visitante (con sufijos)
    df = df.merge(combined, left_on=['Date', 'AwayTeam'], right_on=['Date', 'Team'], how='left', suffixes=('_Home', '_Away')).drop('Team', axis=1)
    
    # --- PASO 4: FEATURES DERIVADAS ---
    # Diferencias y Probabilidades (dinámicas según n_games)
    df['diff_Shots'] = df[f'rolling_S_{n_games}_Home'] - df[f'rolling_S_{n_games}_Away']
    df['exp_Total_Corners'] = df[f'rolling_C_{n_games}_Home'] + df[f'rolling_C_{n_games}_Away']
    df['exp_Total_Shots'] = df[f'rolling_S_{n_games}_Home'] + df[f'rolling_S_{n_games}_Away']
    
    # Corner Share: Qué porcentaje de corners suele aportar cada equipo
    df['Corner_Share_Home'] = df[f'rolling_C_{n_games}_Home'] / (df[f'rolling_C_{n_games}_Home'] + df[f'rolling_C_{n_games}_Away']).replace(0, 1)
    df['Shot_Share_Home'] = df[f'rolling_S_{n_games}_Home'] / (df[f'rolling_S_{n_games}_Home'] + df[f'rolling_S_{n_games}_Away']).replace(0, 1)
    
    # --- INESTABILIDAD (VARIANZA INDIVIDUAL) ---
    # Ratio de Inestabilidad: Desviación Estándar / Media (Coeficiente de Variación)
    # Si es alto, el equipo es impredecible
    df['instability_C_Home'] = df[f'std_C_{n_games}_Home'] / (df[f'rolling_C_{n_games}_Home'] + 0.1)  # +0.1 para evitar división por 0
    df['instability_C_Away'] = df[f'std_C_{n_games}_Away'] / (df[f'rolling_C_{n_games}_Away'] + 0.1)
    df['instability_S_Home'] = df[f'std_S_{n_games}_Home'] / (df[f'rolling_S_{n_games}_Home'] + 0.1)
    df['instability_S_Away'] = df[f'std_S_{n_games}_Away'] / (df[f'rolling_S_{n_games}_Away'] + 0.1)
    
    # Inestabilidad promedio general (combinada)
    df['avg_instability_Home'] = (df['instability_C_Home'] + df['instability_S_Home']) / 2
    df['avg_instability_Away'] = (df['instability_C_Away'] + df['instability_S_Away']) / 2
    
    # --- STRENGTH OF SCHEDULE (SOS) - Tabla Clasificatoria Dinámica POR LIGA ---
    # Usa standings calculados al inicio (PASO 0)
    # Calcula la posición y puntos del rival en cada fecha y liga
    
    df['opponent_position_home'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['AwayTeam']), {}).get('position', 10),
        axis=1
    )
    df['opponent_points_home'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['AwayTeam']), {}).get('points', 0),
        axis=1
    )
    df['opponent_gd_home'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['AwayTeam']), {}).get('gd', 0),
        axis=1
    )
    df['opponent_position_away'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['HomeTeam']), {}).get('position', 10),
        axis=1
    )
    df['opponent_points_away'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['HomeTeam']), {}).get('points', 0),
        axis=1
    )
    df['opponent_gd_away'] = df.apply(
        lambda row: standings.get((row['Date'], row['Div'], row['HomeTeam']), {}).get('gd', 0),
        axis=1
    )
    
    # Probabilidades Implícitas de las cuotas
    sum_inv = (1/df['AvgH']) + (1/df['AvgD']) + (1/df['AvgA'])
    df['Market_Prob_H'] = (1/df['AvgH']) / sum_inv
    df['Market_Prob_D'] = (1/df['AvgD']) / sum_inv
    df['Market_Prob_A'] = (1/df['AvgA']) / sum_inv
    df['Odds_Std'] = df[['AvgH', 'AvgD', 'AvgA']].std(axis=1)
    
    # ============ PASO 5: ATTACKING MOMENTUM (Precisión y Agresividad) ============
    # El objetivo: Diferenciar entre equipos que disparan mucho pero marcan poco
    # vs equipos que disparan menos pero son más precisos y peligrosos.
    
    # 1. Shot Accuracy (Precisión de Tiro)
    df['Home_Shot_Accuracy'] = df[f'rolling_ST_{n_games}_Home'] / (df[f'rolling_S_{n_games}_Home'] + 0.1)
    df['Away_Shot_Accuracy'] = df[f'rolling_ST_{n_games}_Away'] / (df[f'rolling_S_{n_games}_Away'] + 0.1)
    
    # 2. Pressure Index (Presión Ofensiva Total)
    # Mide qué tan "asfixiante" es un equipo: tiros + corners
    df['Home_Pressure_Index'] = df[f'rolling_S_{n_games}_Home'] + (df[f'rolling_C_{n_games}_Home'] * 0.5)
    df['Away_Pressure_Index'] = df[f'rolling_S_{n_games}_Away'] + (df[f'rolling_C_{n_games}_Away'] * 0.5)
    
    # 3. Attacking Momentum Score (Agresividad Ponderada)
    # Combinación: (Tiros en Puerta / Tiros Total) * Presión Total
    df['Home_Attacking_Momentum'] = df['Home_Shot_Accuracy'] * df['Home_Pressure_Index']
    df['Away_Attacking_Momentum'] = df['Away_Shot_Accuracy'] * df['Away_Pressure_Index']
    
    # ============ PASO 6: DEFENSE FATIGUE (Defensa del Rival) ============
    # Cruzar la ofensiva del equipo con la defensa permisiva del rival
    # Idea: "Mis tiros vs tiros que recibe el rival"
    
    df['Home_vs_Away_Shot_Advantage'] = (df[f'rolling_S_{n_games}_Home'] - df[f'rolling_OppS_{n_games}_Away']) / 2
    df['Away_vs_Home_Shot_Advantage'] = (df[f'rolling_S_{n_games}_Away'] - df[f'rolling_OppS_{n_games}_Home']) / 2
    
    # Match Shot Expectancy (Promedio de ofensiva local y defensa del visitante)
    df['Match_Shot_Expectancy_Home'] = (df[f'rolling_S_{n_games}_Home'] + df[f'rolling_OppS_{n_games}_Away']) / 2
    df['Match_Shot_Expectancy_Away'] = (df[f'rolling_S_{n_games}_Away'] + df[f'rolling_OppS_{n_games}_Home']) / 2
    
    # Match Corner Expectancy (Similar para corners)
    df['Match_Corner_Expectancy_Home'] = (df[f'rolling_C_{n_games}_Home'] + df[f'rolling_OppC_{n_games}_Away']) / 2
    df['Match_Corner_Expectancy_Away'] = (df[f'rolling_C_{n_games}_Away'] + df[f'rolling_OppC_{n_games}_Home']) / 2
    
    # Defense Efficiency Ratio (Cuántos tiros recibe pero evita que sean peligrosos)
    df['Home_Defense_Efficiency'] = (df[f'rolling_OppST_{n_games}_Home'] + 0.1) / (df[f'rolling_OppS_{n_games}_Home'] + 0.1)
    df['Away_Defense_Efficiency'] = (df[f'rolling_OppST_{n_games}_Away'] + 0.1) / (df[f'rolling_OppS_{n_games}_Away'] + 0.1)
    
    # ============ PASO 7: ELO/POSITION GAP (Diferencia de Nivel) ============
    # Captura la "distancia" real entre equipos más allá de números planos
    
    df['Position_Diff'] = df['opponent_position_away'] - df['opponent_position_home']  # Positivo = Local mejor
    df['Points_Diff'] = df['opponent_points_away'] - df['opponent_points_home']
    df['GD_Diff'] = df['opponent_gd_away'] - df['opponent_gd_home']
    
    # Calidad relativa del rival
    df['Home_vs_Away_Quality'] = (df['opponent_position_away'] / (df['opponent_position_home'] + 0.1)) - 1
    df['Away_vs_Home_Quality'] = (df['opponent_position_home'] / (df['opponent_position_away'] + 0.1)) - 1
    
    # ============ PASO 8: HEAD-TO-HEAD RECIENTE (Bestias Negras) ============
    # Identifica matchups donde un equipo sistemáticamente le gana a otro
    
    df['H2H_Home_Wins'] = df.apply(
        lambda row: h2h_stats.get((row['HomeTeam'], row['AwayTeam']), {}).get('h2h_wins_home', 0),
        axis=1
    )
    df['H2H_Away_Wins'] = df.apply(
        lambda row: h2h_stats.get((row['HomeTeam'], row['AwayTeam']), {}).get('h2h_wins_away', 0),
        axis=1
    )
    df['H2H_Draws'] = df.apply(
        lambda row: h2h_stats.get((row['HomeTeam'], row['AwayTeam']), {}).get('h2h_draws', 0),
        axis=1
    )
    
    # Head to Head Win Rate
    df['H2H_Total'] = df['H2H_Home_Wins'] + df['H2H_Away_Wins'] + df['H2H_Draws']
    df['H2H_Home_Win_Rate'] = df['H2H_Home_Wins'] / (df['H2H_Total'].replace(0, 1))
    df['H2H_Away_Win_Rate'] = df['H2H_Away_Wins'] / (df['H2H_Total'].replace(0, 1))
    
    return df

if __name__ == "__main__":
    path = os.path.join('data', '**', '*.csv')
    # CARGAR TODO para MEMORIA HISTÓRICA + EWM para SENSIBILIDAD ACTUAL
    # No filtramos por 25-26 porque queremos que el modelo vea:
    # - 3800+ partidos para entender patrones generales del fútbol
    # - EWM automáticamente ponderará MÁS los recientes, menos los antiguos
    files = [f for f in glob.glob(path, recursive=True) if 'dataset_final.csv' not in f]
    
    print(f"[DATA] Cargando dataset completo (MEMORIA + EWM):")
    print(f"   Total de archivos: {len(files)}")
    
    df_list = []
    for f in files:
        temp = pd.read_csv(f, encoding='unicode_escape')
        temp['Date'] = pd.to_datetime(temp['Date'], dayfirst=True, errors='coerce')
        
        # Si no existe Div, crearlo automáticamente desde la ruta
        if 'Div' not in temp.columns:
            temp['Div'] = get_league_code(f)
        
        df_list.append(temp)
    
    full_df = pd.concat(df_list).dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
    final_data = get_rolling_stats(full_df.sort_values('Date'))
    
    # --- FACTOR DE TEMPORADA (Recencia) ---
    # Añadimos columnas que indiquen cuán reciente es cada dato
    max_date = final_data['Date'].max()
    final_data['days_since_match'] = (max_date - final_data['Date']).dt.days
    
    # Weight exponencial: partidos de hoy = 1.0, partidos de hace 3 años ≈ 0.1
    # Esto ayuda al modelo a entender: "Los datos recientes son más relevantes"
    final_data['temporal_weight'] = np.exp(-final_data['days_since_match'] / 365)
    
    # Limpieza de seguridad para el entrenamiento
    final_data.dropna(subset=['AvgH', 'HC', 'HS']).to_csv('data/dataset_final.csv', index=False)
    print(f"[OK] Dataset Multi-Año (EWM + Peso Temporal) generado:")
    print(f"   Total partidos: {len(final_data)}")
    print(f"   Rango: {final_data['Date'].min().date()} a {final_data['Date'].max().date()}")
    print(f"   Equipos: {final_data['HomeTeam'].nunique()} unicos")