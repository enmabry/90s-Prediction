import requests
import pandas as pd
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
API_KEY = "0de86f0b58mshf4ca4b361ca589ep1c1eb0jsn2f549a3ba1f7"
DATA_DIR = "data"
CSV_FILE = os.path.join(DATA_DIR, "test_api.csv")

HEADERS = {
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "x-rapidapi-key": API_KEY
}

MIS_LIGAS = {
    "Champions League": 7,
    "Premier League":   17,
    "LaLiga":           8,
    "Bundesliga":       35
}

# Crear carpeta si no existe
os.makedirs(DATA_DIR, exist_ok=True)

# ==========================================
# 2. FUNCIONES
# ==========================================
def obtener_sid_actual(tid):
    url = "https://sofascore.p.rapidapi.com/tournaments/get-seasons"
    res = requests.get(url, headers=HEADERS, params={"tournamentId": tid})
    if res.status_code == 200:
        seasons = res.json().get('seasons', [])
        return seasons[0].get('id') if seasons else None
    return None

def descargar_stats(match_id, p):
    url_stats = "https://sofascore.p.rapidapi.com/matches/get-statistics"
    res = requests.get(url_stats, headers=HEADERS, params={"matchId": match_id})
    
    if res.status_code == 200:
        data = res.json()
        if 'statistics' not in data or not data['statistics']: return None

        # Buscamos el bloque del partido completo (ALL)
        stats_all = next((item for item in data['statistics'] if item.get("period") == "ALL"), data['statistics'][0])
        groups = stats_all.get('groups', [])
        
        fila = {
            "Date": datetime.fromtimestamp(p.get('startTimestamp', 0)).strftime('%Y-%m-%d'),
            "Home": p.get('homeTeam', {}).get('name'),
            "Away": p.get('awayTeam', {}).get('name'),
            "FTHG": p.get('homeScore', {}).get('display', 0),
            "FTAG": p.get('awayScore', {}).get('display', 0),
            "HST": 0, "AST": 0, "HC": 0, "AC": 0
        }

        for group in groups:
            for item in group.get('statisticsItems', []):
                key = item.get('key')
                if key == 'shotsOnGoal':
                    fila["HST"], fila["AST"] = item.get('homeValue', 0), item.get('awayValue', 0)
                elif key == 'cornerKicks':
                    fila["HC"], fila["AC"] = item.get('homeValue', 0), item.get('awayValue', 0)
        return fila
    return None

# ==========================================
# 3. EJECUCIÓN
# ==========================================
def actualizar_todo():
    print(f"🚀 Intentando poblar: {CSV_FILE}")
    resultados_totales = []

    for liga, tid in MIS_LIGAS.items():
        sid = obtener_sid_actual(tid)
        print(f"\n⚽ {liga} (SID: {sid})")
        if not sid: continue

        # Probamos con 'get-last-matches' que suele ser más estable para algunas cuentas
        url_res = "https://sofascore.p.rapidapi.com/tournaments/get-results"
        params = {"tournamentId": tid, "seasonId": sid, "pageIndex": 0}
        
        res = requests.get(url_res, headers=HEADERS, params=params)

        if res.status_code == 200:
            data_json = res.json()
            # La API a veces devuelve 'events' y otras 'tournamentEvents'
            partidos = data_json.get('events', []) or data_json.get('tournamentEvents', [])
            
            if not partidos:
                print(f"   ⚠️ No se encontraron partidos en la respuesta. (Status: 200 OK)")
                continue

            for p in partidos[:5]: # Solo los últimos 5 para probar rápido
                if p.get('status', {}).get('type') == 'finished':
                    datos = descargar_stats(p['id'], p)
                    if datos:
                        resultados_totales.append(datos)
                        print(f"      ✅ Guardado: {datos['Home']} vs {datos['Away']}")
        else:
            print(f"   ❌ Error API {res.status_code}: {res.text[:100]}")

    if resultados_totales:
        df = pd.DataFrame(resultados_totales)
        # Modo 'a' (append) pero con chequeo de duplicados si quieres
        df.to_csv(CSV_FILE, mode='a', index=False, header=not os.path.exists(CSV_FILE))
        print(f"\n✨ ¡ÉXITO! Se han guardado {len(resultados_totales)} partidos en {CSV_FILE}")
    else:
        print("\n❌ La respuesta de la API vino vacía. Posiblemente necesites habilitar los resultados en tu dashboard de RapidAPI.")

if __name__ == "__main__":
    actualizar_todo()