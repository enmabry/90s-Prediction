"""
Script para transformar Champions League al formato estándar.
Convierte champions_league_matches25-26.csv al formato compatible con el pipeline.
"""

import pandas as pd
import os
from pathlib import Path

def transform_champions_league():
    """
    Lee Champions League CSV y lo transforma al formato estándar.
    
    Mapeo:
    - date → Date, time → Time (default 19:45)
    - home_team → HomeTeam
    - away_team → AwayTeam
    - score → FTHG, FTAG (ej: "1–3" → FTHG=1, FTAG=3)
    - result → FTR (Away Win→A, Home Win→H, Draw→D)
    - Agrega Div='CL' (Champions League)
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
        
        # Procesar score (ej: "1–3" → FTHG=1, FTAG=3)
        def parse_score(score_str):
            if pd.isna(score_str) or score_str == '':
                return None, None
            try:
                # El separador es "–" (en-dash) no "-"
                parts = str(score_str).split('–')
                if len(parts) == 2:
                    return int(parts[0].strip()), int(parts[1].strip())
            except:
                pass
            return None, None
        
        # Crear FTHG y FTAG
        df[['FTHG', 'FTAG']] = df['score'].apply(
            lambda x: pd.Series(parse_score(x))
        )
        
        # Mapear result a FTR
        result_map = {
            'Home Win': 'H',
            'Away Win': 'A',
            'Draw': 'D'
        }
        df['FTR'] = df['result'].map(result_map)
        
        # Crear columnas de cuotas estimadas basadas en FTR
        # (promedio simple: victoria=1.8, empate=3.5, derrota=5.0)
        def estimate_odds(ftr):
            if ftr == 'H':
                return 1.8, 3.5, 5.0
            elif ftr == 'A':
                return 5.0, 3.5, 1.8
            else:  # Draw
                return 3.5, 3.5, 3.5
        
        # Crear DataFrame con columnas estándar
        output_df = pd.DataFrame({
            'Div': 'CL',  # Champions League
            'Date': pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y'),
            'Time': '19:45',  # Hora por defecto
            'HomeTeam': df['home_team'],
            'AwayTeam': df['away_team'],
            'FTHG': df['FTHG'],
            'FTAG': df['FTAG'],
            'FTR': df['FTR'],
            'HTHG': pd.NA,  # No disponible en Champions League
            'HTAG': pd.NA,
            'HTR': pd.NA,
            'Referee': df['referee'].fillna('Unknown'),
            'HS': pd.NA,  # Shots (usar HST como proxy)
            'AS': pd.NA,
            'HST': pd.to_numeric(df['home_shots_on_target'], errors='coerce'),  # Shots on target
            'AST': pd.to_numeric(df['away_shots_on_target'], errors='coerce'),
            'HF': pd.NA,  # Fouls (no disponible)
            'AF': pd.NA,
            'HC': pd.NA,  # Corners (no disponible)
            'AC': pd.NA,
            'HY': pd.NA,  # Tarjetas (no disponible)
            'AY': pd.NA,
            'HR': pd.NA,  # Red cards
            'AR': pd.NA,
            # Cuotas estándar (Bet365, usamos estimadas)
            'B365H': [estimate_odds(ftr)[0] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
            'B365D': [estimate_odds(ftr)[1] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
            'B365A': [estimate_odds(ftr)[2] if pd.notna(ftr) else pd.NA for ftr in df['FTR']],
        })
        
        # Cuotas promedio (necesarias para validación)
        output_df['AvgH'] = output_df['B365H']
        output_df['AvgD'] = output_df['B365D']
        output_df['AvgA'] = output_df['B365A']
        
        # Filtrar filas donde FTHG y FTAG no son NaN (datos válidos)
        output_df = output_df[output_df['FTHG'].notna()]
        
        print(f"[INFO] Transformando {len(output_df)} partidos")
        
        # Guardar
        os.makedirs(output_file.parent, exist_ok=True)
        output_df.to_csv(output_file, index=False)
        
        print(f"[OK] Guardado en: {output_file}")
        print(f"[INFO] Columnas: {', '.join(output_df.columns[:15])}")
        print(f"[INFO] Primeros 3 registros:\n{output_df.head(3)}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    success = transform_champions_league()
    exit(0 if success else 1)
