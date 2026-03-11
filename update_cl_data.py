"""
Script para actualizar Champions League con rango amplio de fechas
Cubre los octavos de final (Feb-Mar 2026)
"""
import sys
sys.path.insert(0, 'src')

import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

# API Key
API_KEY = os.getenv('SOFASCORE_API_KEY', '0de86f0b58mshf4ca4b361ca589ep1c1eb0jsn2f549a3ba1f7')
HEADERS = {
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "x-rapidapi-key": API_KEY
}

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"

CL_CONFIG = {
    "tournament_id": 7,
    "folder": "ChampionsLeague",
    "current_file": "ChampionsLeague25-26.csv",
    "div_code": "CL"
}

# Ampliado a 60 días para capturar octavos de final
DIAS_ATRAS = 60
MAX_PAGINAS = 5
MAX_PARTIDOS = 50


def calcular_resultado(h, a):
    if h > a: return 'H'
    elif h < a: return 'A'
    return 'D'


def obtener_season_id(tournament_id):
    url = "https://sofascore.p.rapidapi.com/tournaments/get-seasons"
    try:
        r = requests.get(url, headers=HEADERS, params={"tournamentId": tournament_id}, timeout=10)
        if r.status_code == 200:
            seasons = r.json().get('seasons', [])
            return seasons[0].get('id') if seasons else None
    except Exception as e:
        print(f"Error obteniendo season: {e}")
    return None


def descargar_stats(match_id, match_info, div_code):
    url = "https://sofascore.p.rapidapi.com/matches/get-statistics"
    try:
        r = requests.get(url, headers=HEADERS, params={"matchId": match_id}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if 'statistics' not in data or not data['statistics']:
            return None

        stats_all = next(
            (item for item in data['statistics'] if item.get("period") == "ALL"),
            data['statistics'][0] if data['statistics'] else None
        )
        if not stats_all:
            return None

        ts = match_info.get('startTimestamp', 0)
        fila = {
            "Div": div_code,
            "Date": datetime.fromtimestamp(ts).strftime('%d/%m/%Y'),
            "Time": datetime.fromtimestamp(ts).strftime('%H:%M'),
            "HomeTeam": match_info.get('homeTeam', {}).get('name', ''),
            "AwayTeam": match_info.get('awayTeam', {}).get('name', ''),
            "FTHG": match_info.get('homeScore', {}).get('display', 0),
            "FTAG": match_info.get('awayScore', {}).get('display', 0),
            "FTR": calcular_resultado(
                match_info.get('homeScore', {}).get('display', 0),
                match_info.get('awayScore', {}).get('display', 0)
            ),
            "HTHG": None, "HTAG": None, "HTR": None, "Referee": None,
            "HS": 0, "AS": 0, "HST": 0, "AST": 0,
            "HC": 0, "AC": 0, "HF": 0, "AF": 0,
            "HY": 0, "AY": 0, "HR": 0, "AR": 0,
            "HPoss": None, "APoss": None,
            "B365H": None, "B365D": None, "B365A": None,
            "AvgH": None, "AvgD": None, "AvgA": None,
        }

        for group in stats_all.get('groups', []):
            for item in group.get('statisticsItems', []):
                key = item.get('key', '')
                hv = item.get('homeValue', 0) or 0
                av = item.get('awayValue', 0) or 0
                if key == 'totalShotsOnGoal':
                    fila["HS"], fila["AS"] = hv, av
                elif key == 'shotsOnGoal':
                    fila["HST"], fila["AST"] = hv, av
                elif key == 'cornerKicks':
                    fila["HC"], fila["AC"] = hv, av
                elif key == 'fouls':
                    fila["HF"], fila["AF"] = hv, av
                elif key == 'yellowCards':
                    fila["HY"], fila["AY"] = hv, av
                elif key == 'redCards':
                    fila["HR"], fila["AR"] = hv, av
                elif key == 'ballPossession':
                    fila["HPoss"] = hv
                    fila["APoss"] = av
        return fila
    except Exception as e:
        print(f"   Error en partido {match_id}: {e}")
        return None


def actualizar_cl():
    print("\n" + "="*60)
    print("ACTUALIZANDO CHAMPIONS LEAGUE 2025-2026")
    print(f"Buscando partidos de los ultimos {DIAS_ATRAS} dias")
    print("="*60)

    tournament_id = CL_CONFIG['tournament_id']
    csv_path = DATA_DIR / CL_CONFIG['folder'] / CL_CONFIG['current_file']

    # Cargar datos existentes
    df_existente = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
    print(f"Partidos existentes: {len(df_existente)}")

    # Obtener season ID
    season_id = obtener_season_id(tournament_id)
    if not season_id:
        print("ERROR: No se pudo obtener el Season ID")
        return
    print(f"Season ID: {season_id}")

    # Fecha límite
    fecha_limite = datetime.now() - timedelta(days=DIAS_ATRAS)
    partidos_nuevos = []
    total_procesados = 0

    for page in range(MAX_PAGINAS):
        print(f"\nPagina {page + 1}...")
        params = {"tournamentId": tournament_id, "seasonId": season_id, "pageIndex": page}
        try:
            r = requests.get(
                "https://sofascore.p.rapidapi.com/tournaments/get-last-matches",
                headers=HEADERS, params=params, timeout=15
            )
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} - fin de paginas")
                break

            data = r.json()
            partidos = data.get('events', []) or data.get('tournamentEvents', [])
            if not partidos:
                print("  Sin mas partidos")
                break

            print(f"  {len(partidos)} partidos encontrados")
            partidos_en_rango = 0

            for partido in partidos:
                if partido.get('status', {}).get('type') != 'finished':
                    continue

                ts = partido.get('startTimestamp', 0)
                fecha_partido = datetime.fromtimestamp(ts)

                # Solo partidos dentro del rango
                if fecha_partido < fecha_limite:
                    continue

                partidos_en_rango += 1
                home = partido.get('homeTeam', {}).get('name', '')
                away = partido.get('awayTeam', {}).get('name', '')
                date_str = fecha_partido.strftime('%d/%m/%Y')

                # Saltar si ya existe
                if not df_existente.empty:
                    ya_existe = ((df_existente['HomeTeam'] == home) &
                                 (df_existente['AwayTeam'] == away) &
                                 (df_existente['Date'] == date_str)).any()
                    if ya_existe:
                        print(f"  [SKIP] {home} vs {away} ({date_str}) - ya existe")
                        continue

                time.sleep(0.6)
                stats = descargar_stats(partido['id'], partido, 'CL')
                total_procesados += 1

                if stats:
                    partidos_nuevos.append(stats)
                    print(f"  [OK] {home} vs {away} ({date_str}) | HST:{stats['HST']} AST:{stats['AST']}")
                else:
                    print(f"  [FAIL] {home} vs {away} ({date_str})")

                if len(partidos_nuevos) >= MAX_PARTIDOS:
                    break

            print(f"  Partidos en rango de fechas: {partidos_en_rango}")
            if len(partidos_nuevos) >= MAX_PARTIDOS:
                break

        except Exception as e:
            print(f"  Error en pagina {page}: {e}")
            break

    # Guardar
    if partidos_nuevos:
        df_nuevos = pd.DataFrame(partidos_nuevos)
        if not df_existente.empty:
            df_final = pd.concat([df_existente, df_nuevos], ignore_index=True)
            # Deduplicar
            df_final = df_final.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'], keep='last')
        else:
            df_final = df_nuevos

        df_final.to_csv(csv_path, index=False)
        print(f"\n{'='*60}")
        print(f"GUARDADOS: {len(partidos_nuevos)} partidos nuevos")
        print(f"Total en archivo: {len(df_final)}")
        print(f"{'='*60}")
    else:
        print("\nNo se encontraron partidos nuevos para guardar")


if __name__ == "__main__":
    actualizar_cl()
