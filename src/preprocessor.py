import pandas as pd
import glob
import os
import warnings
import numpy as np
from pandas.errors import PerformanceWarning

warnings.simplefilter(action='ignore', category=PerformanceWarning)

def get_rolling_stats(df, n_games=5):
    # Definimos las métricas base
    # Ofensivas: Tiros (S), Tiros a Puerta (ST), Corners (C)
    # Defensivas: Tiros Recibidos (OppS), Tiros a Puerta Recibidos (OppST), Corners Recibidos (OppC)
    
    # --- PASO 1: CREAR REGISTROS INDIVIDUALES POR EQUIPO ---
    home_stats = df[['Date', 'HomeTeam', 'HS', 'HST', 'HC', 'AS', 'AST', 'AC']].copy()
    home_stats.columns = ['Date', 'Team', 'S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    home_stats['IsHome'] = 1

    away_stats = df[['Date', 'AwayTeam', 'AS', 'AST', 'AC', 'HS', 'HST', 'HC']].copy()
    away_stats.columns = ['Date', 'Team', 'S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    away_stats['IsHome'] = 0

    combined = pd.concat([home_stats, away_stats]).sort_values(['Team', 'Date'])

    # --- PASO 2: CALCULAR MEDIAS MÓVILES Y DESVIACIÓN ESTÁNDAR ---
    features = ['S', 'ST', 'C', 'OppS', 'OppST', 'OppC']
    
    # A. Medias Generales (Forma reciente total)
    for f in features:
        combined[f'rolling_{f}_{n_games}'] = combined.groupby('Team')[f].transform(
            lambda x: x.rolling(window=n_games, min_periods=1).mean().shift(1)
        )
    
    # B. Desviación Estándar Móvil (Inestabilidad)
    # Captura cuán impredecible es un equipo (varianza en sus últimos n_games)
    for f in features:
        combined[f'std_{f}_{n_games}'] = combined.groupby('Team')[f].transform(
            lambda x: x.rolling(window=n_games, min_periods=1).std().shift(1)
        )
    
    # C. Medias por ROL (Solo Local o Solo Visitante)
    # Esto captura si el equipo se comporta diferente en casa o fuera
    for f in features:
        combined[f'rolling_{f}_{n_games}_Role'] = combined.groupby(['Team', 'IsHome'])[f].transform(
            lambda x: x.rolling(window=n_games, min_periods=1).mean().shift(1)
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
    
    # Probabilidades Implícitas de las cuotas
    sum_inv = (1/df['AvgH']) + (1/df['AvgD']) + (1/df['AvgA'])
    df['Market_Prob_H'] = (1/df['AvgH']) / sum_inv
    df['Market_Prob_D'] = (1/df['AvgD']) / sum_inv
    df['Market_Prob_A'] = (1/df['AvgA']) / sum_inv
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