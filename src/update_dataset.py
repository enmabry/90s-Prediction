"""
Sistema de actualización de datos desde Sofascore API
Descarga estadísticas de partidos finalizados y actualiza los CSVs de cada liga
"""

import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Dict, List, Optional

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

# API Key - Se puede configurar mediante variable de entorno
API_KEY = os.getenv('SOFASCORE_API_KEY', '0de86f0b58mshf4ca4b361ca589ep1c1eb0jsn2f549a3ba1f7')

# Directorios del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

HEADERS = {
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "x-rapidapi-key": API_KEY
}

# Mapeo de ligas: Nombre -> (tournament_id, directorio_csv, archivo_actual)
LEAGUES_CONFIG = {
    "Champions League": {
        "tournament_id": 7,
        "folder": "ChampionsLeague",
        "current_file": "ChampionsLeague25-26.csv",
        "div_code": "CL"
    },
    "Premier League": {
        "tournament_id": 17,
        "folder": "PremierLeague",
        "current_file": "PremierLeague24-25.csv",
        "div_code": "E0"
    },
    "LaLiga": {
        "tournament_id": 8,
        "folder": "LaLigaEspañola",
        "current_file": "LaLiga24-25.csv",
        "div_code": "SP1"
    },
    "Bundesliga": {
        "tournament_id": 35,
        "folder": "BundesligaAlemania",
        "current_file": "Bundesliga24-25.csv",
        "div_code": "D1"
    }
}

# Configuración de descarga
MAX_PARTIDOS_POR_LIGA = 20  # Máximo de partidos a descargar por liga
DIAS_HACIA_ATRAS = 7  # Solo descargar partidos de los últimos N días
DELAY_BETWEEN_REQUESTS = 0.5  # Segundos entre peticiones para evitar rate limiting


# ==========================================
# 2. FUNCIONES AUXILIARES
# ==========================================

def obtener_season_id(tournament_id: int) -> Optional[int]:
    """
    Obtiene el ID de la temporada actual para un torneo dado
    
    Args:
        tournament_id: ID del torneo en Sofascore
        
    Returns:
        ID de la temporada actual o None si falla
    """
    url = "https://sofascore.p.rapidapi.com/tournaments/get-seasons"
    try:
        response = requests.get(url, headers=HEADERS, params={"tournamentId": tournament_id}, timeout=10)
        if response.status_code == 200:
            seasons = response.json().get('seasons', [])
            return seasons[0].get('id') if seasons else None
        else:
            print(f"   ⚠️ Error obteniendo temporada: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error en obtener_season_id: {e}")
        return None


def descargar_estadisticas_partido(match_id: int, match_info: dict, div_code: str) -> Optional[dict]:
    """
    Descarga las estadísticas completas de un partido desde la API
    
    Args:
        match_id: ID del partido en Sofascore
        match_info: Información básica del partido (equipos, resultado, etc.)
        div_code: Código de la división/liga (e.g., 'E0', 'SP1')
        
    Returns:
        Diccionario con todas las estadísticas o None si falla
    """
    url_stats = "https://sofascore.p.rapidapi.com/matches/get-statistics"
    
    try:
        response = requests.get(url_stats, headers=HEADERS, params={"matchId": match_id}, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        if 'statistics' not in data or not data['statistics']:
            return None

        # Buscamos el bloque del partido completo (ALL periods)
        stats_all = next(
            (item for item in data['statistics'] if item.get("period") == "ALL"),
            data['statistics'][0] if data['statistics'] else None
        )
        
        if not stats_all:
            return None
            
        groups = stats_all.get('groups', [])
        
        # Inicializar fila con datos básicos
        fila = {
            "Div": div_code,
            "Date": datetime.fromtimestamp(match_info.get('startTimestamp', 0)).strftime('%d/%m/%Y'),
            "Time": datetime.fromtimestamp(match_info.get('startTimestamp', 0)).strftime('%H:%M'),
            "HomeTeam": match_info.get('homeTeam', {}).get('name', ''),
            "AwayTeam": match_info.get('awayTeam', {}).get('name', ''),
            "FTHG": match_info.get('homeScore', {}).get('display', 0),
            "FTAG": match_info.get('awayScore', {}).get('display', 0),
            "FTR": calcular_resultado(
                match_info.get('homeScore', {}).get('display', 0),
                match_info.get('awayScore', {}).get('display', 0)
            ),
            # Estadísticas inicializadas en 0
            "HS": 0, "AS": 0,           # Total shots
            "HST": 0, "AST": 0,         # Shots on target
            "HC": 0, "AC": 0,           # Corners
            "HF": 0, "AF": 0,           # Fouls
            "HY": 0, "AY": 0,           # Yellow cards
            "HR": 0, "AR": 0,           # Red cards
        }

        # Extraer estadísticas de los grupos
        for group in groups:
            for item in group.get('statisticsItems', []):
                key = item.get('key', '')
                home_val = item.get('homeValue', 0)
                away_val = item.get('awayValue', 0)
                
                # Mapeo de claves de API a columnas del CSV
                if key == 'totalShotsOnGoal':
                    fila["HS"], fila["AS"] = home_val, away_val
                elif key == 'shotsOnGoal':
                    fila["HST"], fila["AST"] = home_val, away_val
                elif key == 'cornerKicks':
                    fila["HC"], fila["AC"] = home_val, away_val
                elif key == 'fouls':
                    fila["HF"], fila["AF"] = home_val, away_val
                elif key == 'yellowCards':
                    fila["HY"], fila["AY"] = home_val, away_val
                elif key == 'redCards':
                    fila["HR"], fila["AR"] = home_val, away_val
                    
        return fila
        
    except Exception as e:
        print(f"      ⚠️ Error descargando stats del partido {match_id}: {e}")
        return None


def calcular_resultado(home_goals: int, away_goals: int) -> str:
    """Calcula el resultado del partido (H/D/A)"""
    if home_goals > away_goals:
        return 'H'
    elif home_goals < away_goals:
        return 'A'
    else:
        return 'D'


def cargar_csv_existente(file_path: Path) -> pd.DataFrame:
    """
    Carga un CSV existente o crea uno vacío con las columnas necesarias
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con los datos existentes o vacío
    """
    if file_path.exists():
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            print(f"   ⚠️ Error leyendo {file_path.name}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def partidos_ya_descargados(df: pd.DataFrame, home_team: str, away_team: str, date: str) -> bool:
    """
    Verifica si un partido ya está en el DataFrame
    
    Args:
        df: DataFrame con partidos existentes
        home_team: Nombre del equipo local
        away_team: Nombre del equipo visitante
        date: Fecha del partido en formato 'dd/mm/yyyy'
        
    Returns:
        True si el partido ya existe, False en caso contrario
    """
    if df.empty:
        return False
    
    return ((df['HomeTeam'] == home_team) & 
            (df['AwayTeam'] == away_team) & 
            (df['Date'] == date)).any()


def es_partido_reciente(timestamp: int, dias_atras: int = DIAS_HACIA_ATRAS) -> bool:
    """
    Verifica si un partido está dentro del rango de días especificado
    
    Args:
        timestamp: Timestamp Unix del partido
        dias_atras: Número de días hacia atrás a considerar
        
    Returns:
        True si el partido está dentro del rango, False en caso contrario
    """
    fecha_partido = datetime.fromtimestamp(timestamp)
    fecha_limite = datetime.now() - timedelta(days=dias_atras)
    return fecha_partido >= fecha_limite



# ==========================================
# 3. FUNCIÓN PRINCIPAL
# ==========================================

def actualizar_liga(league_name: str, config: dict, max_matches: int = MAX_PARTIDOS_POR_LIGA) -> int:
    """
    Actualiza los datos de una liga específica desde Sofascore
    
    Args:
        league_name: Nombre de la liga
        config: Configuración de la liga (tournament_id, folder, etc.)
        max_matches: Número máximo de partidos a descargar
        
    Returns:
        Número de partidos nuevos añadidos
    """
    print(f"\n{'='*60}")
    print(f"⚽ {league_name}")
    print(f"{'='*60}")
    
    tournament_id = config['tournament_id']
    folder = config['folder']
    current_file = config['current_file']
    div_code = config['div_code']
    
    # Obtener season ID
    season_id = obtener_season_id(tournament_id)
    if not season_id:
        print(f"   ❌ No se pudo obtener el Season ID")
        return 0
    
    print(f"   Season ID: {season_id}")
    
    # Preparar archivo CSV
    csv_path = DATA_DIR / folder / current_file
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    df_existente = cargar_csv_existente(csv_path)
    print(f"   Partidos ya registrados: {len(df_existente)}")
    
    # Obtener resultados recientes
    url_last_matches = "https://sofascore.p.rapidapi.com/tournaments/get-last-matches"
    partidos_nuevos = []
    
    try:
        # Intentar obtener partidos de varias páginas
        for page in range(3):  # Máximo 3 páginas
            params = {"tournamentId": tournament_id, "seasonId": season_id, "pageIndex": page}
            response = requests.get(url_last_matches, headers=HEADERS, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"   ⚠️ Error HTTP {response.status_code} en página {page}")
                break
            
            data_json = response.json()
            partidos = data_json.get('events', []) or data_json.get('tournamentEvents', [])
            
            if not partidos:
                print(f"   ℹ️ No hay más partidos en la página {page}")
                break
            
            print(f"   Procesando página {page + 1}: {len(partidos)} partidos encontrados")
            
            # Procesar cada partido
            for partido in partidos:
                if len(partidos_nuevos) >= max_matches:
                    break
                
                # Solo partidos finalizados
                if partido.get('status', {}).get('type') != 'finished':
                    continue
                
                # Filtrar por fecha (últimos N días)
                partido_timestamp = partido.get('startTimestamp', 0)
                if not es_partido_reciente(partido_timestamp, DIAS_HACIA_ATRAS):
                    continue
                
                home_team = partido.get('homeTeam', {}).get('name', '')
                away_team = partido.get('awayTeam', {}).get('name', '')
                date_str = datetime.fromtimestamp(partido_timestamp).strftime('%d/%m/%Y')
                
                # Verificar si ya existe
                if partidos_ya_descargados(df_existente, home_team, away_team, date_str):
                    continue
                
                # Descargar estadísticas del partido
                time.sleep(DELAY_BETWEEN_REQUESTS)
                stats = descargar_estadisticas_partido(partido['id'], partido, div_code)
                
                if stats:
                    partidos_nuevos.append(stats)
                    print(f"      ✅ {home_team} vs {away_team} ({date_str})")
            
            # Si ya alcanzamos el máximo, salir
            if len(partidos_nuevos) >= max_matches:
                break
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    except Exception as e:
        print(f"   ❌ Error durante la descarga: {e}")
    
    # Guardar nuevos partidos
    if partidos_nuevos:
        df_nuevos = pd.DataFrame(partidos_nuevos)
        
        # Si el archivo existe, concatenar; si no, crear nuevo
        if not df_existente.empty:
            df_final = pd.concat([df_existente, df_nuevos], ignore_index=True)
        else:
            df_final = df_nuevos
        
        # Guardar
        df_final.to_csv(csv_path, index=False)
        print(f"\n   ✨ {len(partidos_nuevos)} partidos nuevos guardados en {csv_path.name}")
        return len(partidos_nuevos)
    else:
        print(f"\n   ℹ️ No hay partidos nuevos para descargar")
        return 0


def actualizar_todas_las_ligas(ligas: Optional[List[str]] = None):
    """
    Actualiza todas las ligas configuradas o solo las especificadas
    
    Args:
        ligas: Lista de nombres de ligas a actualizar. Si es None, actualiza todas.
    """
    print("\n" + "="*60)
    print("🚀 SISTEMA DE ACTUALIZACIÓN DE DATOS - SOFASCORE API")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Rango: Últimos {DIAS_HACIA_ATRAS} días")
    print(f"Límite: Máximo {MAX_PARTIDOS_POR_LIGA} partidos por liga")
    
    # Validar API Key
    if not API_KEY or API_KEY == '':
        print("\n❌ ERROR: API_KEY no configurada")
        print("   Configura la variable de entorno SOFASCORE_API_KEY")
        return
    
    # Seleccionar ligas
    if ligas:
        ligas_a_actualizar = {k: v for k, v in LEAGUES_CONFIG.items() if k in ligas}
    else:
        ligas_a_actualizar = LEAGUES_CONFIG
    
    total_partidos = 0
    
    # Actualizar cada liga
    for league_name, config in ligas_a_actualizar.items():
        try:
            partidos_nuevos = actualizar_liga(league_name, config)
            total_partidos += partidos_nuevos
        except Exception as e:
            print(f"\n   ❌ Error procesando {league_name}: {e}")
    
    # Resumen final
    print("\n" + "="*60)
    print(f"✅ ACTUALIZACIÓN COMPLETADA")
    print(f"   Total de partidos nuevos: {total_partidos}")
    print("="*60)


# ==========================================
# 4. PUNTO DE ENTRADA
# ==========================================

if __name__ == "__main__":
    # Actualizar todas las ligas
    actualizar_todas_las_ligas()
    
    # Para actualizar solo ligas específicas:
    # actualizar_todas_las_ligas(['Premier League', 'LaLiga'])