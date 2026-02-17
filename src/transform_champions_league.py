"""
Script para transformar Champions League al formato estándar.
Convierte champions_league_matches25-26.csv al formato compatible con el pipeline.

Datos disponibles en el CSV de CL:
- score: "1–3" → FTHG=1, FTAG=3
- home_shots_on_target: "3 of 10" → HST=3, HS=10
- away_shots_on_target: "8 of 18" → AST=8, AS=18  
- home_possession / away_possession: "63%" → porcentaje
- NO tiene corners (HC/AC) → se rellenan con promedios de liga doméstica
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

def transform_champions_league():
    """
    Lee Champions League CSV y lo transforma al formato estándar.
    Extrae tiros totales y a puerta del campo "X of Y".
    """
    
    # Rutas
    input_file = Path(__file__).parent.parent / 'data' / 'ChampionsLeague' / 'champions_league_matches25-26.csv'
    output_file = Path(__file__).parent.parent / 'data' / 'ChampionsLeague' / 'ChampionsLeague25-26.csv'
    
    if not input_file.exists():
        print(f"[ERROR] No encontrado: {input_file}")
        return False
    
    try:
        print(f"[INFO] Leyendo: {input_file}")
        df = pd.read_csv(input_file)
        
        # Validar columnas requeridas
        required_cols = ['date', 'home_team', 'away_team', 'score', 'referee', 'result']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"[ERROR] Columnas faltantes: {missing}")
            return False
        
        # ─── Parsear score: "1–3" → FTHG=1, FTAG=3 ───
        def parse_score(score_str):
            if pd.isna(score_str) or score_str == '':
                return None, None
            try:
                parts = str(score_str).split('–')
                if len(parts) == 2:
                    return int(parts[0].strip()), int(parts[1].strip())
            except:
                pass
            return None, None
        
        df[['FTHG', 'FTAG']] = df['score'].apply(
            lambda x: pd.Series(parse_score(x))
        )
        
        # ─── Parsear shots: "3 of 10" → on_target=3, total=10 ───
        def parse_shots(shots_str):
            """Extrae tiros a puerta y totales de '3 of 10'"""
            if pd.isna(shots_str) or shots_str == '':
                return None, None
            try:
                parts = str(shots_str).split(' of ')
                if len(parts) == 2:
                    on_target = int(parts[0].strip())
                    total = int(parts[1].strip())
                    return on_target, total
            except:
                pass
            return None, None
        
        # Home shots
        df[['HST', 'HS']] = df['home_shots_on_target'].apply(
            lambda x: pd.Series(parse_shots(x))
        )
        # Away shots
        df[['AST', 'AS']] = df['away_shots_on_target'].apply(
            lambda x: pd.Series(parse_shots(x))
        )
        
        # ─── Parsear posesión: "63%" → 63 ───
        def parse_possession(poss_str):
            if pd.isna(poss_str) or poss_str == '':
                return None
            try:
                return float(str(poss_str).replace('%', '').strip())
            except:
                return None
        
        df['home_poss'] = df['home_possession'].apply(parse_possession)
        df['away_poss'] = df['away_possession'].apply(parse_possession)
        
        # ─── Mapear resultado ───
        result_map = {'Home Win': 'H', 'Away Win': 'A', 'Draw': 'D'}
        df['FTR'] = df['result'].map(result_map)
        
        # ─── Cuotas estimadas ───
        def estimate_odds(ftr):
            if ftr == 'H':   return 1.8, 3.5, 5.0
            elif ftr == 'A': return 5.0, 3.5, 1.8
            else:            return 3.5, 3.5, 3.5
        
        # ─── Crear DataFrame estándar ───
        output_df = pd.DataFrame({
            'Div': 'CL',
            'Date': pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y'),
            'Time': '19:45',
            'HomeTeam': df['home_team'],
            'AwayTeam': df['away_team'],
            'FTHG': df['FTHG'],
            'FTAG': df['FTAG'],
            'FTR': df['FTR'],
            'HTHG': pd.NA,
            'HTAG': pd.NA,
            'HTR': pd.NA,
            'Referee': df['referee'].fillna('Unknown'),
            'HS': df['HS'],           # Tiros totales (extraído de "X of Y")
            'AS': df['AS'],           # Tiros totales visitante
            'HST': df['HST'],         # Tiros a puerta (extraído de "X of Y")
            'AST': df['AST'],         # Tiros a puerta visitante
            'HF': pd.NA,
            'AF': pd.NA,
            'HC': pd.NA,              # Corners: NO disponible en CL → se rellena después
            'AC': pd.NA,              # con promedios de liga doméstica
            'HY': pd.NA,
            'AY': pd.NA,
            'HR': pd.NA,
            'AR': pd.NA,
            'B365H': [estimate_odds(ftr)[0] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
            'B365D': [estimate_odds(ftr)[1] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
            'B365A': [estimate_odds(ftr)[2] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
        })
        
        output_df['AvgH'] = output_df['B365H']
        output_df['AvgD'] = output_df['B365D']
        output_df['AvgA'] = output_df['B365A']
        
        # Filtrar filas válidas
        output_df = output_df[output_df['FTHG'].notna()]
        
        # Stats
        hs_valid = output_df['HS'].notna().sum()
        hst_valid = output_df['HST'].notna().sum()
        print(f"[INFO] Transformando {len(output_df)} partidos")
        print(f"[INFO] Tiros totales (HS/AS): {hs_valid} registros con datos")
        print(f"[INFO] Tiros a puerta (HST/AST): {hst_valid} registros con datos")
        print(f"[INFO] Corners (HC/AC): No disponible → se rellenará con liga doméstica")
        
        # Guardar
        os.makedirs(output_file.parent, exist_ok=True)
        output_df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"[OK] Guardado en: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = transform_champions_league()
    exit(0 if success else 1)
