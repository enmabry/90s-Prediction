import pandas as pd
import glob
import os
import warnings
import numpy as np
from pandas.errors import PerformanceWarning

warnings.simplefilter(action='ignore', category=PerformanceWarning)

def get_rolling_stats(df, n_games=5):
    # Limpieza de nombres y creación de puntos
    df['HomeTeam'] = df['HomeTeam'].str.strip()
    df['AwayTeam'] = df['AwayTeam'].str.strip()
    df['Points_H'] = df['FTR'].map({'H': 3, 'D': 1, 'A': 0})
    df['Points_A'] = df['FTR'].map({'A': 3, 'D': 1, 'H': 0})
    
    # Calculamos cuánto del total suele aportar el equipo (Home Share / Away Share)
    df['Home_Corner_Share'] = df['HC'] / (df['HC'] + df['AC']).replace(0, 1)
    df['Home_Shot_Share'] = df['HS'] / (df['HS'] + df['AS']).replace(0, 1)

    # Crear dataset largo para promedios por equipo
    home = df[['Date', 'Div', 'HomeTeam', 'HS', 'HST', 'HC', 'Points_H', 'Home_Corner_Share', 'Home_Shot_Share']].rename(
        columns={'HomeTeam': 'Team', 'HS': 'Shots', 'HST': 'ShotsTarget', 'HC': 'Corners', 'Points_H': 'Points', 
                 'Home_Corner_Share': 'Corner_Share', 'Home_Shot_Share': 'Shot_Share'}
    )
    away = df[['Date', 'Div', 'AwayTeam', 'AS', 'AST', 'AC', 'Points_A']].rename(
        columns={'AwayTeam': 'Team', 'AS': 'Shots', 'AST': 'ShotsTarget', 'AC': 'Corners', 'Points_A': 'Points'}
    )
    # Para el equipo visitante, la share es el complemento
    away['Corner_Share'] = 1 - df['Home_Corner_Share']
    away['Shot_Share'] = 1 - df['Home_Shot_Share']
    
    teams_df = pd.concat([home, away]).sort_values(['Team', 'Date'])
    
    # Métricas de ataque: Puntería y Volumen
    teams_df['Accuracy'] = teams_df['ShotsTarget'] / teams_df['Shots'].replace(0, 1)
    teams_df['AttackVolume'] = teams_df['Shots'] + teams_df['Corners']
    
    features = ['Shots', 'ShotsTarget', 'Corners', 'Points', 'Accuracy', 'AttackVolume', 'Corner_Share', 'Shot_Share']
    col_names = [f'rolling_{f}_{n_games}' for f in features]
    
    # Medias móviles (min_periods=1 para no perder datos iniciales)
    teams_df[col_names] = teams_df.groupby('Team')[features].transform(
        lambda x: x.rolling(window=n_games, min_periods=1).mean().shift(1)
    )
    
    # Re-unión al dataset principal
    df = df.merge(teams_df[['Date', 'Team'] + col_names], left_on=['Date', 'HomeTeam'], right_on=['Date', 'Team'], how='left').drop('Team', axis=1)
    df = df.merge(teams_df[['Date', 'Team'] + col_names], left_on=['Date', 'AwayTeam'], right_on=['Date', 'Team'], how='left', suffixes=('_Home', '_Away')).drop('Team', axis=1)

    # 1. Calcular la "Capacidad Defensiva" del Rival (Goles y Tiros concedidos)
    # Registramos cuántos tiros y corners RECIBE cada equipo
    home_def = df[['Date', 'HomeTeam', 'AS', 'AST', 'AC']].rename(
        columns={'HomeTeam': 'Team', 'AS': 'ShotsConceded', 'AST': 'TargetConceded', 'AC': 'CornersConceded'}
    )
    away_def = df[['Date', 'AwayTeam', 'HS', 'HST', 'HC']].rename(
        columns={'AwayTeam': 'Team', 'HS': 'ShotsConceded', 'HST': 'TargetConceded', 'HC': 'CornersConceded'}
    )
    def_df = pd.concat([home_def, away_def]).sort_values(['Team', 'Date'])

    # Medias de lo que el rival SUELE PERMITIR (últimos 5 juegos)
    def_features = ['ShotsConceded', 'TargetConceded', 'CornersConceded']
    def_col_names = [f'rolling_Opp_{f}_5' for f in def_features]
    def_df[def_col_names] = def_df.groupby('Team')[def_features].transform(
        lambda x: x.rolling(window=n_games, min_periods=1).mean().shift(1)
    )

    # 2. Unir al dataset para que la IA vea: "Mi ataque VS Su defensa"
    df = df.merge(def_df[['Date', 'Team'] + def_col_names], left_on=['Date', 'AwayTeam'], right_on=['Date', 'Team'], how='left').drop('Team', axis=1)
    df = df.rename(columns={c: f"{c}_Home_Vs" for c in def_col_names}) # Lo que el Local enfrentará
    
    df = df.merge(def_df[['Date', 'Team'] + def_col_names], left_on=['Date', 'HomeTeam'], right_on=['Date', 'Team'], how='left').drop('Team', axis=1)
    df = df.rename(columns={c: f"{c}_Away_Vs" for c in def_col_names}) # Lo que el Visitante enfrentará

    # Diferenciales y Expectativas Totales (para regresión)
    df['diff_Shots'] = df['rolling_Shots_5_Home'] - df['rolling_Shots_5_Away']
    df['exp_Total_Corners'] = df['rolling_Corners_5_Home'] + df['rolling_Corners_5_Away']
    df['exp_Total_Shots'] = df['rolling_Shots_5_Home'] + df['rolling_Shots_5_Away']
    
    # 1. Calcular Probabilidades Implícitas de las cuotas
    # La suma de (1/cuota) siempre es > 1 debido al margen de la casa (overround)
    sum_inv = (1/df['AvgH']) + (1/df['AvgD']) + (1/df['AvgA'])
    
    # Probabilidades reales "limpias" según el mercado
    df['Market_Prob_H'] = (1/df['AvgH']) / sum_inv
    df['Market_Prob_D'] = (1/df['AvgD']) / sum_inv
    df['Market_Prob_A'] = (1/df['AvgA']) / sum_inv

    # 2. Variable de "Inestabilidad" o Sorpresa
    # Si las cuotas son muy parecidas, el partido es inestable.
    # Usamos la desviación estándar de las cuotas como feature.
    df['Odds_Std'] = df[['AvgH', 'AvgD', 'AvgA']].std(axis=1)
    
    return df

if __name__ == "__main__":
    path = os.path.join('data', '**', '*.csv')
    files = [f for f in glob.glob(path, recursive=True) if 'dataset_final.csv' not in f]
    
    df_list = []
    for f in files:
        temp = pd.read_csv(f, encoding='unicode_escape')
        temp['Date'] = pd.to_datetime(temp['Date'], dayfirst=True, errors='coerce')
        df_list.append(temp)
    
    full_df = pd.concat(df_list).dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
    final_data = get_rolling_stats(full_df.sort_values('Date'))
    
    # Limpieza de seguridad para el entrenamiento
    final_data.dropna(subset=['AvgH', 'HC', 'HS']).to_csv('data/dataset_final.csv', index=False)
    print(f"Dataset Multi-Liga generado: {len(final_data)} partidos.")