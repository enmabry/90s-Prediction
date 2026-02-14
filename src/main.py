"""
SISTEMA CENTRALIZADO DE PREDICCION DEPORTIVA
Desarrollado por: Sistema de IA
Version: 2.0 - Interfaz Profesional
"""

import os
import sys
import subprocess
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from datetime import datetime

console = Console(force_terminal=True, width=100)

# Colores y estilos
HEADER_COLOR = "cyan"
SUCCESS_COLOR = "green"
ERROR_COLOR = "red"
INFO_COLOR = "yellow"
ACCENT_COLOR = "magenta"


def limpiar_consola():
    """Limpia la consola de forma multiplataforma"""
    os.system('cls' if os.name == 'nt' else 'clear')


def menu_principal():
    """Muestra el menu principal de forma profesional"""
    limpiar_consola()
    
    titulo = Text("[*] SISTEMA DE PREDICCION DEPORTIVA v2.0", style=f"bold {HEADER_COLOR}")
    console.print(Panel(titulo, expand=False, border_style=ACCENT_COLOR))
    
    fecha = datetime.now().strftime("%d de %B de %Y - %H:%M:%S")
    console.print(f"[{INFO_COLOR}]Fecha: {fecha}[/{INFO_COLOR}]\n")
    
    opciones = [
        ("1", "Preprocesar Datos", "Ejecuta preprocessor.py - Procesa dataset y features"),
        ("2", "Entrenar Modelos", "Ejecuta train.py - Entrena XGBoost"),
        ("3", "Prediccion Asistida", "Flujo: Liga -> Equipos -> Cuotas -> Prediccion"),
        ("4", "Backtesting", "Abre prediction_log.xlsx para analisis"),
        ("5", "Auto-Run", "Ejecuta 1 -> 2 -> 3 consecutivamente"),
        ("0", "Salir", "Cierra el programa"),
    ]
    
    table = Table(title="MENU DE OPCIONES", show_header=True, header_style=f"bold {HEADER_COLOR}")
    table.add_column("Op", style="cyan", width=4)
    table.add_column("Accion", style="magenta", width=20)
    table.add_column("Descripcion", style="white", width=65)
    
    for opcion, accion, desc in opciones:
        table.add_row(opcion, accion, desc)
    
    console.print(table)
    console.print()


def ejecutar_script(script_path, descripcion):
    """Ejecuta un script Python y muestra el progreso"""
    console.print(f"\n[{INFO_COLOR}]>>> Iniciando: {descripcion}[/{INFO_COLOR}]")
    console.print("[" + "="*60 + "]")
    
    try:
        if not os.path.exists(script_path):
            script_path = os.path.join(os.path.dirname(__file__), script_path)
        
        resultado = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if resultado.stdout:
            console.print(resultado.stdout)
        if resultado.stderr and resultado.returncode != 0:
            console.print(f"[{ERROR_COLOR}]{resultado.stderr}[/{ERROR_COLOR}]")
        
        if resultado.returncode == 0:
            console.print(f"[{SUCCESS_COLOR}][OK] {descripcion} completado[/{SUCCESS_COLOR}]")
        else:
            console.print(f"[{ERROR_COLOR}][FALLO] {descripcion} presento error[/{ERROR_COLOR}]")
    
    except subprocess.TimeoutExpired:
        console.print(f"[{ERROR_COLOR}][TIMEOUT] El script tardo demasiado[/{ERROR_COLOR}]")
    except Exception as e:
        console.print(f"[{ERROR_COLOR}][ERROR] {str(e)}[/{ERROR_COLOR}]")


def seleccionar_liga():
    """Muestra ligas disponibles y retorna la seleccionada"""
    try:
        df = pd.read_csv('data/dataset_final.csv')
        ligas = df['Div'].unique()
        ligas_dict = {
            'SP1': '[ESPAÑA] La Liga',
            'D1': '[ALEMANIA] Bundesliga'
        }
        
        console.print("\n[bold cyan]SELECCIONA LIGA:[/bold cyan]")
        tabla_ligas = Table(show_header=True, header_style=f"bold {HEADER_COLOR}")
        tabla_ligas.add_column("#", style="cyan")
        tabla_ligas.add_column("Liga", style="magenta")
        tabla_ligas.add_column("Partidos", style="green")
        
        liga_map = {}
        idx = 1
        for liga in sorted(ligas):
            if liga in ligas_dict:
                n_partidos = len(df[df['Div'] == liga])
                tabla_ligas.add_row(str(idx), ligas_dict[liga], str(n_partidos))
                liga_map[idx] = liga
                idx += 1
        
        console.print(tabla_ligas)
        
        while True:
            try:
                opcion = int(input("\nIngresa numero de liga: "))
                if opcion in liga_map:
                    return liga_map[opcion]
                else:
                    console.print(f"[{ERROR_COLOR}]Opcion invalida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Ingresa numero valido[/{ERROR_COLOR}]")
    
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error: {str(e)}[/{ERROR_COLOR}]")
        return None


def seleccionar_equipos(liga):
    """Muestra equipos de una liga y retorna local y visitante"""
    try:
        df = pd.read_csv('data/dataset_final.csv')
        df_liga = df[df['Div'] == liga]
        
        equipos = sorted(pd.concat([df_liga['HomeTeam'], df_liga['AwayTeam']]).unique())
        
        console.print(f"\n[bold cyan]EQUIPOS DE LA LIGA (Total: {len(equipos)})[/bold cyan]\n")
        
        tabla_equipos = Table(show_header=True, header_style=f"bold {HEADER_COLOR}")
        tabla_equipos.add_column("#", style="cyan", width=4)
        tabla_equipos.add_column("Equipo", style="magenta", width=30)
        tabla_equipos.add_column("PJ", style="green", width=5)
        
        equipo_map = {}
        for idx, equipo in enumerate(equipos, 1):
            n_partidos = len(df_liga[(df_liga['HomeTeam'] == equipo) | (df_liga['AwayTeam'] == equipo)])
            tabla_equipos.add_row(str(idx), equipo, str(n_partidos))
            equipo_map[idx] = equipo
        
        console.print(tabla_equipos)
        
        # Seleccionar Local
        while True:
            try:
                local_idx = int(input("\n[LOCAL] Selecciona numero: "))
                if local_idx in equipo_map:
                    local = equipo_map[local_idx]
                    break
                else:
                    console.print(f"[{ERROR_COLOR}]Opcion invalida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Numero invalido[/{ERROR_COLOR}]")
        
        console.print(f"[{SUCCESS_COLOR}][OK] Local: {local}[/{SUCCESS_COLOR}]")
        
        # Seleccionar Visitante
        while True:
            try:
                visitante_idx = int(input("\n[VISITANTE] Selecciona numero: "))
                if visitante_idx in equipo_map:
                    visitante = equipo_map[visitante_idx]
                    if visitante != local:
                        break
                    else:
                        console.print(f"[{ERROR_COLOR}]Visitante debe diferir del local[/{ERROR_COLOR}]")
                else:
                    console.print(f"[{ERROR_COLOR}]Opcion invalida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Numero invalido[/{ERROR_COLOR}]")
        
        console.print(f"[{SUCCESS_COLOR}][OK] Visitante: {visitante}[/{SUCCESS_COLOR}]")
        
        return local, visitante
    
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error: {str(e)}[/{ERROR_COLOR}]")
        return None, None


def opcion_prediccion():
    """Flujo completo de prediccion asistida"""
    limpiar_consola()
    console.print(Panel("[*] PREDICCION ASISTIDA", border_style=ACCENT_COLOR, expand=False))
    
    liga = seleccionar_liga()
    if liga is None:
        return
    
    local, visitante = seleccionar_equipos(liga)
    if local is None or visitante is None:
        return
    
    console.print("\n[bold cyan]INGRESA CUOTAS:[/bold cyan]")
    try:
        h = float(input(f"Cuota {local} (1): "))
        d = float(input("Cuota Empate (X): "))
        a = float(input(f"Cuota {visitante} (2): "))
    except ValueError:
        console.print(f"[{ERROR_COLOR}]Cuotas invalidas[/{ERROR_COLOR}]")
        return
    
    console.print("\n" + "="*60)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from predict import predict_final_boss
        
        predict_final_boss(local, visitante, h, d, a)
        console.print(f"[{SUCCESS_COLOR}][OK] Prediccion completada[/{SUCCESS_COLOR}]")
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error: {str(e)}[/{ERROR_COLOR}]")


def opcion_backtesting():
    """Abre el archivo de log de predicciones"""
    limpiar_consola()
    console.print(Panel("[*] BACKTESTING", border_style=ACCENT_COLOR, expand=False))
    
    log_path = 'data/prediction_log.xlsx'
    
    if os.path.exists(log_path):
        console.print(f"[{SUCCESS_COLOR}]Abriendo {log_path}...[/{SUCCESS_COLOR}]")
        try:
            if os.name == 'nt':
                os.startfile(log_path)
            elif os.name == 'posix':
                subprocess.Popen(['open', log_path])
            console.print(f"[{SUCCESS_COLOR}][OK] Archivo abierto[/{SUCCESS_COLOR}]")
        except Exception as e:
            console.print(f"[{ERROR_COLOR}]Error: {str(e)}[/{ERROR_COLOR}]")
    else:
        console.print(f"[{ERROR_COLOR}]Archivo no encontrado: {log_path}[/{ERROR_COLOR}]")


def opcion_autorun():
    """Ejecuta opciones 1, 2 y 3 consecutivamente"""
    limpiar_consola()
    console.print(Panel("[*] AUTO-RUN (Preprocesar -> Entrenar -> Prediccion)", 
                       border_style=ACCENT_COLOR, expand=False))
    
    ejecutar_script('src/preprocessor.py', 'Preprocesamiento')
    input("\nPresiona Enter para continuar...")
    
    limpiar_consola()
    ejecutar_script('src/train.py', 'Entrenamiento')
    input("\nPresiona Enter para continuar...")
    
    opcion_prediccion()


def main():
    """Loop principal del programa"""
    while True:
        menu_principal()
        
        opcion = input("Selecciona opcion (0-5): ").strip()
        
        try:
            if opcion == "1":
                limpiar_consola()
                ejecutar_script('src/preprocessor.py', 'Preprocesamiento')
                input("\n[cyan]Enter para volver al menu...[/cyan]")
            
            elif opcion == "2":
                limpiar_consola()
                ejecutar_script('src/train.py', 'Entrenamiento')
                input("\n[cyan]Enter para volver al menu...[/cyan]")
            
            elif opcion == "3":
                opcion_prediccion()
                input("\n[cyan]Enter para volver al menu...[/cyan]")
            
            elif opcion == "4":
                opcion_backtesting()
                input("\n[cyan]Enter para volver al menu...[/cyan]")
            
            elif opcion == "5":
                opcion_autorun()
                input("\n[cyan]Enter para volver al menu...[/cyan]")
            
            elif opcion == "0":
                limpiar_consola()
                console.print(Panel("[green][OK] Hasta luego![/green]", border_style=ACCENT_COLOR, expand=False))
                break
            
            else:
                console.print(f"[{ERROR_COLOR}]Opcion invalida[/{ERROR_COLOR}]")
                input("\nEnter para continuar...")
        
        except KeyboardInterrupt:
            console.print(f"\n[{ERROR_COLOR}]Operacion cancelada[/{ERROR_COLOR}]")
            input("Enter para volver al menu...")
        except Exception as e:
            console.print(f"[{ERROR_COLOR}]Error: {str(e)}[/{ERROR_COLOR}]")
            input("Enter para volver al menu...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        limpiar_consola()
        print("Programa interrumpido por el usuario")
        sys.exit(0)

# Colores y estilos
HEADER_COLOR = "cyan"
SUCCESS_COLOR = "green"
ERROR_COLOR = "red"
INFO_COLOR = "yellow"
ACCENT_COLOR = "magenta"


def limpiar_consola():
    """Limpia la consola de forma multiplataforma"""
    os.system('cls' if os.name == 'nt' else 'clear')


def menu_principal():
    """Muestra el menú principal de forma profesional"""
    limpiar_consola()
    
    titulo = Text("[*] SISTEMA DE PREDICCIÓN DEPORTIVA v2.0", style=f"bold {HEADER_COLOR}")
    console.print(Panel(titulo, expand=False, border_style=ACCENT_COLOR))
    
    fecha = datetime.now().strftime("%d de %B de %Y - %H:%M:%S")
    console.print(f"[{INFO_COLOR}]Fecha: {fecha}[/{INFO_COLOR}]\n")
    
    opciones = [
        ("1", "Preprocesar Datos", "Ejecuta preprocessor.py - Procesa dataset y features"),
        ("2", "Entrenar Modelos", "Ejecuta train.py - Entrena XGBoost"),
        ("3", "Predicción Asistida", "Flujo de selección por liga -> equipo -> predicción"),
        ("4", "Backtesting", "Abre prediction_log.xlsx para análisis"),
        ("5", "Auto-Run", "Ejecuta 1 -> 2 -> 3 consecutivamente"),
        ("0", "Salir", "Cierra el programa"),
    ]
    
    table = Table(title="MENÚ DE OPCIONES", show_header=True, header_style=f"bold {HEADER_COLOR}")
    table.add_column("Opción", style="cyan", width=8)
    table.add_column("Acción", style="magenta", width=20)
    table.add_column("Descripción", style="white", width=55)
    
    for opcion, accion, desc in opciones:
        table.add_row(opcion, accion, desc)
    
    console.print(table)
    console.print()


def ejecutar_script(script_path, descripcion):
    """Ejecuta un script Python y muestra el progreso"""
    console.print(f"\n[{INFO_COLOR}]> Iniciando: {descripcion}[/{INFO_COLOR}]")
    console.print("─" * 60)
    
    try:
        # Convertir a ruta relativa si es necesario
        if not os.path.exists(script_path):
            script_path = os.path.join(os.path.dirname(__file__), script_path)
        
        resultado = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if resultado.stdout:
            console.print(resultado.stdout)
        if resultado.stderr:
            console.print(f"[{ERROR_COLOR}]{resultado.stderr}[/{ERROR_COLOR}]")
        
        if resultado.returncode == 0:
            console.print(f"[{SUCCESS_COLOR}][OK] {descripcion} completado exitosamente[/{SUCCESS_COLOR}]")
        else:
            console.print(f"[{ERROR_COLOR}][ERROR] Error: {descripcion} fallo[/{ERROR_COLOR}]")
    
    except subprocess.TimeoutExpired:
        console.print(f"[{ERROR_COLOR}][TIMEOUT] El script tardo demasiado[/{ERROR_COLOR}]")
    except Exception as e:
        console.print(f"[{ERROR_COLOR}][ERROR] Error: {str(e)}[/{ERROR_COLOR}]")


def seleccionar_liga():
    """Muestra ligas disponibles y retorna la seleccionada"""
    try:
        df = pd.read_csv('data/dataset_final.csv')
        ligas = df['Div'].unique()
        ligas_dict = {
            'SP1': '⚪ La Liga (España)',
            'D1': '🔴 Bundesliga (Alemania)'
        }
        
        console.print("\n[bold cyan]SELECCIONA LIGA:[/bold cyan]")
        tabla_ligas = Table(show_header=True, header_style=f"bold {HEADER_COLOR}")
        tabla_ligas.add_column("[#]", style="cyan")
        tabla_ligas.add_column("Liga", style="magenta") # Dummy comment to track line
        tabla_ligas.add_column("Partidos", style="green")
        
        liga_map = {}
        idx = 1
        for liga in sorted(ligas):
            if liga in ligas_dict:
                n_partidos = len(df[df['Div'] == liga])
                tabla_ligas.add_row(str(idx), ligas_dict[liga], str(n_partidos))
                liga_map[idx] = liga
                idx += 1
        
        console.print(tabla_ligas)
        
        while True:
            try:
                opcion = int(input("\nIngresa el número de la liga: "))
                if opcion in liga_map:
                    return liga_map[opcion]
                else:
                    console.print(f"[{ERROR_COLOR}]Opción inválida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Ingresa un número válido[/{ERROR_COLOR}]")
    
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error cargando ligas: {str(e)}[/{ERROR_COLOR}]")
        return None


def seleccionar_equipos(liga):
    """Muestra equipos de una liga y retorna local y visitante"""
    try:
        df = pd.read_csv('data/dataset_final.csv')
        df_liga = df[df['Div'] == liga]
        
        # Obtener equipos únicos ordenados
        equipos = sorted(pd.concat([df_liga['HomeTeam'], df_liga['AwayTeam']]).unique())
        
        console.print(f"\n[bold cyan]EQUIPOS DE LA LIGA (Total: {len(equipos)})[/bold cyan]\n")
        
        tabla_equipos = Table(show_header=True, header_style=f"bold {HEADER_COLOR}", max_width=80)
        tabla_equipos.add_column("Nº", style="cyan", width=5)
        tabla_equipos.add_column("Equipo", style="magenta", width=25)
        tabla_equipos.add_column("Partidos", style="green", width=12)
        
        equipo_map = {}
        for idx, equipo in enumerate(equipos, 1):
            n_partidos = len(df_liga[(df_liga['HomeTeam'] == equipo) | (df_liga['AwayTeam'] == equipo)])
            tabla_equipos.add_row(str(idx), equipo, str(n_partidos))
            equipo_map[idx] = equipo
        
        console.print(tabla_equipos)
        
        # Seleccionar Local
        while True:
            try:
                local_idx = int(input("\n⚪ Selecciona EQUIPO LOCAL (número): "))
                if local_idx in equipo_map:
                    local = equipo_map[local_idx]
                    break
                else:
                    console.print(f"[{ERROR_COLOR}]Opción inválida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Ingresa un número válido[/{ERROR_COLOR}]")
        
        console.print(f"[{SUCCESS_COLOR}]✓ Local seleccionado: {local}[/{SUCCESS_COLOR}]")
        
        # Seleccionar Visitante
        while True:
            try:
                visitante_idx = int(input("\n🚌 Selecciona EQUIPO VISITANTE (número): "))
                if visitante_idx in equipo_map:
                    visitante = equipo_map[visitante_idx]
                    if visitante != local:
                        break
                    else:
                        console.print(f"[{ERROR_COLOR}]El visitante debe ser diferente al local[/{ERROR_COLOR}]")
                else:
                    console.print(f"[{ERROR_COLOR}]Opción inválida[/{ERROR_COLOR}]")
            except ValueError:
                console.print(f"[{ERROR_COLOR}]Ingresa un número válido[/{ERROR_COLOR}]")
        
        console.print(f"[{SUCCESS_COLOR}]✓ Visitante seleccionado: {visitante}[/{SUCCESS_COLOR}]")
        
        return local, visitante
    
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error seleccionando equipos: {str(e)}[/{ERROR_COLOR}]")
        return None, None


def opcion_prediccion():
    """Flujo completo de predicción asistida"""
    limpiar_consola()
    console.print(Panel("🎯 PREDICCIÓN ASISTIDA", border_style=ACCENT_COLOR, expand=False))
    
    # Seleccionar liga
    liga = seleccionar_liga()
    if liga is None:
        return
    
    # Seleccionar equipos
    local, visitante = seleccionar_equipos(liga)
    if local is None or visitante is None:
        return
    
    # Pedir cuotas
    console.print("\n[bold cyan]INGRESA LAS CUOTAS:[/bold cyan]")
    try:
        h = float(input(f"Cuota para {local} (1): "))
        d = float(input("Cuota para Empate (X): "))
        a = float(input(f"Cuota para {visitante} (2): "))
    except ValueError:
        console.print(f"[{ERROR_COLOR}]Cuotas inválidas[/{ERROR_COLOR}]")
        return
    
    # Ejecutar predicción
    console.print("\n" + "─" * 60)
    try:
        # Agregar la carpeta src al path para importar el módulo
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from predict import predict_final_boss
        
        predict_final_boss(local, visitante, h, d, a)
        console.print(f"[{SUCCESS_COLOR}]✅ Predicción completada[/{SUCCESS_COLOR}]")
    except Exception as e:
        console.print(f"[{ERROR_COLOR}]Error en predicción: {str(e)}[/{ERROR_COLOR}]")


def opcion_backtesting():
    """Abre el archivo de log de predicciones"""
    limpiar_consola()
    console.print(Panel("📊 BACKTESTING", border_style=ACCENT_COLOR, expand=False))
    
    log_path = 'data/prediction_log.xlsx'
    
    if os.path.exists(log_path):
        console.print(f"[{SUCCESS_COLOR}]Abriendo {log_path}...[/{SUCCESS_COLOR}]")
        try:
            if os.name == 'nt':  # Windows
                os.startfile(log_path)
            elif os.name == 'posix':  # macOS/Linux
                subprocess.Popen(['open', log_path])
            console.print(f"[{SUCCESS_COLOR}]✅ Archivo abierto[/{SUCCESS_COLOR}]")
        except Exception as e:
            console.print(f"[{ERROR_COLOR}]Error abriendo archivo: {str(e)}[/{ERROR_COLOR}]")
    else:
        console.print(f"[{ERROR_COLOR}]Archivo no encontrado: {log_path}[/{ERROR_COLOR}]")


def opcion_autorun():
    """Ejecuta opciones 1, 2 y 3 consecutivamente"""
    limpiar_consola()
    console.print(Panel("⚙️ AUTO-RUN (Preprocesar → Entrenar → Predicción)", 
                       border_style=ACCENT_COLOR, expand=False))
    
    # 1. Preprocesar
    ejecutar_script('src/preprocessor.py', 'Preprocesamiento')
    input("\nPresiona Enter para continuar...")
    
    # 2. Entrenar
    limpiar_consola()
    ejecutar_script('src/train.py', 'Entrenamiento de Modelos')
    input("\nPresiona Enter para continuar...")
    
    # 3. Predicción
    opcion_prediccion()


def main():
    """Loop principal del programa"""
    while True:
        menu_principal()
        
        opcion = input("Selecciona una opción (0-5): ").strip()
        
        try:
            if opcion == "1":
                limpiar_consola()
                ejecutar_script('src/preprocessor.py', 'Preprocesamiento de Datos')
                input("\n[cyan]Presiona Enter para volver al menú...[/cyan]")
            
            elif opcion == "2":
                limpiar_consola()
                ejecutar_script('src/train.py', 'Entrenamiento de Modelos')
                input("\n[cyan]Presiona Enter para volver al menú...[/cyan]")
            
            elif opcion == "3":
                opcion_prediccion()
                input("\n[cyan]Presiona Enter para volver al menú...[/cyan]")
            
            elif opcion == "4":
                opcion_backtesting()
                input("\n[cyan]Presiona Enter para volver al menú...[/cyan]")
            
            elif opcion == "5":
                opcion_autorun()
                input("\n[cyan]Presiona Enter para volver al menú...[/cyan]")
            
            elif opcion == "0":
                limpiar_consola()
                console.print(Panel("[green]✅ ¡Hasta luego![/green]", border_style=ACCENT_COLOR, expand=False))
                break
            
            else:
                console.print(f"[{ERROR_COLOR}]Opción no válida[/{ERROR_COLOR}]")
                input("\nPresiona Enter para continuar...")
        
        except KeyboardInterrupt:
            console.print(f"\n[{ERROR_COLOR}]Operación cancelada[/{ERROR_COLOR}]")
            input("Presiona Enter para volver al menú...")
        except Exception as e:
            console.print(f"[{ERROR_COLOR}]Error inesperado: {str(e)}[/{ERROR_COLOR}]")
            input("Presiona Enter para volver al menú...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        limpiar_consola()
        console.print("[yellow]Programa interrumpido por el usuario[/yellow]")
        sys.exit(0)
