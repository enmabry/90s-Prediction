#!/usr/bin/env python
"""
Validador de datasets para agregar nueva liga
Verifica que los CSVs tengan los atributos necesarios
"""

import pandas as pd
import glob
import os

REQUIRED_COLUMNS = [
    'Date', 'HomeTeam', 'AwayTeam',
    'FTHG', 'FTAG', 'FTR',           # Resultados (Full Time)
    'HS', 'AS',                       # Shots
    'HST', 'AST',                     # Shots on Target
    'HC', 'AC',                       # Corners
    'AvgH', 'AvgD', 'AvgA'           # Cuotas promedio
]

OPTIONAL_COLUMNS = [
    'Div',                            # Liga (se asigna automáticamente)
    'HF', 'AF',                       # Fouls
    'HY', 'AY',                       # Amarillas
    'HR', 'AR'                        # Rojas
]

def validate_dataset(folder_path):
    """Valida todos los CSVs en una carpeta"""
    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    
    if not csv_files:
        print(f"[ERROR] No se encontraron CSVs en: {folder_path}")
        return False
    
    all_valid = True
    
    for csv_file in csv_files:
        print(f"\nAnalizando: {os.path.basename(csv_file)}")
        
        try:
            df = pd.read_csv(csv_file, encoding='unicode_escape', nrows=5)
            columns = set(df.columns)
            
            # Verificar columnas requeridas
            missing = set(REQUIRED_COLUMNS) - columns
            if missing:
                print(f"  [ERROR] Columnas FALTANTES: {missing}")
                all_valid = False
            else:
                print(f"  [OK] Tiene {len(REQUIRED_COLUMNS)} columnas requeridas")
            
            # Avisar de columnas opcionales disponibles
            optional_present = set(OPTIONAL_COLUMNS) & columns
            if optional_present:
                print(f"  [INFO] Columnas opcionales: {optional_present}")
            
            # Verificar tamaño del dataset
            total_rows = len(pd.read_csv(csv_file, encoding='unicode_escape'))
            print(f"  [INFO] Total de partidos: {total_rows}")
            
            # Verificar fechas
            df_dates = pd.read_csv(csv_file, encoding='unicode_escape')
            try:
                df_dates['Date'] = pd.to_datetime(df_dates['Date'], dayfirst=True, errors='coerce')
                date_range = f"{df_dates['Date'].min().date()} a {df_dates['Date'].max().date()}"
                print(f"  [INFO] Rango de fechas: {date_range}")
            except:
                print(f"  [WARN] No se pudo parsear las fechas")
            
        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            all_valid = False
    
    return all_valid

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # Validar todas las ligas
        folders = [
            'data/LaLigaEspañola',
            'data/BundesligaAlemania',
            'data/PremierLeague'
        ]
    else:
        folders = [sys.argv[1]]
    
    print("[VALIDADOR] Verificando estructura de datasets\n")
    print(f"Requeridas: {REQUIRED_COLUMNS}")
    print(f"Opcionales: {OPTIONAL_COLUMNS}\n")
    
    for folder in folders:
        if os.path.exists(folder):
            print(f"\n{'='*60}")
            print(f"Carpeta: {folder}")
            print('='*60)
            result = validate_dataset(folder)
            if result:
                print(f"\n[OK] {folder} es válido para el sistema")
            else:
                print(f"\n[ERROR] {folder} tiene problemas - ver arriba")
        else:
            print(f"\n[SKIP] {folder} no existe")
    
    print(f"\n{'='*60}")
    print("[INSTRUCCIONES]")
    print("1. Si ves [ERROR], agrega las columnas faltantes al CSV")
    print("2. Si ves [OK], puedes ejecutar: python src/preprocessor.py")
    print('='*60)
