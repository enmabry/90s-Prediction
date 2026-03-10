"""
Script para corregir partidos con HS=0 (tiros totales faltantes)
Elimina partidos con HS=0 para que puedan ser re-descargados correctamente
"""

import pandas as pd
from pathlib import Path

# Rutas de los CSVs
DATA_DIR = Path(__file__).parent.parent / "data"

LEAGUES_FILES = {
    "Premier League": DATA_DIR / "PremierLeague" / "PremierLeague24-25.csv",
    "LaLiga": DATA_DIR / "LaLigaEspañola" / "LaLiga24-25.csv",
    "Bundesliga": DATA_DIR / "BundesligaAlemania" / "Bundesliga24-25.csv",
    "Champions League": DATA_DIR / "ChampionsLeague" / "ChampionsLeague25-26.csv",
}

def fix_missing_shots():
    """
    Elimina partidos con HS=0 o AS=0 de los CSVs para que puedan ser re-descargados
    """
    print("\n" + "="*60)
    print("🔧 CORRECCIÓN DE PARTIDOS CON TIROS FALTANTES")
    print("="*60)
    
    total_eliminados = 0
    
    for league_name, csv_path in LEAGUES_FILES.items():
        if not csv_path.exists():
            print(f"\n⚠️ {league_name}: Archivo no encontrado")
            continue
        
        # Leer CSV
        df = pd.read_csv(csv_path)
        partidos_iniciales = len(df)
        
        # Identificar partidos con HS=0 o AS=0
        partidos_problematicos = df[(df['HS'] == 0) | (df['AS'] == 0)]
        num_problematicos = len(partidos_problematicos)
        
        if num_problematicos == 0:
            print(f"\n✅ {league_name}: Sin partidos con tiros faltantes")
            continue
        
        print(f"\n⚽ {league_name}")
        print(f"   Partidos totales: {partidos_iniciales}")
        print(f"   Partidos con HS=0 o AS=0: {num_problematicos}")
        
        # Mostrar algunos ejemplos
        print(f"\n   Ejemplos de partidos a eliminar:")
        for idx, row in partidos_problematicos.head(3).iterrows():
            print(f"      - {row['HomeTeam']} vs {row['AwayTeam']} ({row['Date']})")
        
        # Eliminar partidos problemáticos
        df_limpio = df[(df['HS'] != 0) & (df['AS'] != 0)]
        
        # Guardar CSV actualizado
        df_limpio.to_csv(csv_path, index=False)
        
        partidos_finales = len(df_limpio)
        eliminados = partidos_iniciales - partidos_finales
        total_eliminados += eliminados
        
        print(f"\n   ✨ {eliminados} partidos eliminados")
        print(f"   📊 Partidos restantes: {partidos_finales}")
    
    # Resumen final
    print("\n" + "="*60)
    print(f"✅ CORRECCIÓN COMPLETADA")
    print(f"   Total de partidos eliminados: {total_eliminados}")
    print(f"\n   Ejecuta 'python src/update_dataset.py' para re-descargarlos")
    print("="*60 + "\n")

if __name__ == "__main__":
    fix_missing_shots()
