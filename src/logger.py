import pandas as pd
import os
from datetime import datetime

class PredictionLogger:
    """
    Logger para registrar predicciones y sus resultados.
    Guarda en Excel para auditoría y backtesting.
    """
    
    def __init__(self, log_file="data/prediction_log.xlsx"):
        self.log_file = log_file
        self.predictions = []
        
        # Crear archivo si no existe
        if not os.path.exists(log_file):
            self._create_empty_log()
    
    def _create_empty_log(self):
        """Crea un Excel vacío con la estructura correcta"""
        df = pd.DataFrame(columns=[
            'Timestamp',
            'Date_Prediction',
            'HomeTeam',
            'AwayTeam',
            'Event_Type',  # 'Corners', 'Shots', etc.
            'Over_Line',
            'Prob_IA',
            'Cuota',
            'Kelly_Amount',
            'Instability_Score',
            'Status',  # 'Pending', 'Win', 'Loss'
            'Result_Value',  # Valor real del evento
            'Payout',  # Ganancia/pérdida
            'Notes'
        ])
        df.to_excel(self.log_file, index=False, sheet_name='Predictions')
    
    def log_prediction(self, date_pred, home_team, away_team, event_type, over_line, 
                      prob_ia, cuota, kelly_amount, instability_score=0, notes=""):
        """
        Registra una predicción
        
        Args:
            date_pred (str): Fecha del partido
            home_team (str): Equipo local
            away_team (str): Equipo visitante
            event_type (str): Tipo de evento (Corners, Shots, etc.)
            over_line (float): Línea (ej: 4.5 corners)
            prob_ia (float): Probabilidad estimada (0-1)
            cuota (float): Cuota decimal
            kelly_amount (float): Monto recomendado por Kelly
            instability_score (float): Score de inestabilidad
            notes (str): Notas adicionales
        """
        prediction = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Date_Prediction': date_pred,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'Event_Type': event_type,
            'Over_Line': over_line,
            'Prob_IA': round(prob_ia, 4),
            'Cuota': cuota,
            'Kelly_Amount': round(kelly_amount, 2),
            'Instability_Score': round(instability_score, 4),
            'Status': 'Pending',
            'Result_Value': None,
            'Payout': None,
            'Notes': notes
        }
        self.predictions.append(prediction)
    
    def save_predictions(self):
        """Guarda las predicciones al archivo Excel"""
        if not self.predictions:
            return
        
        # Leer existing data si existe
        try:
            existing_df = pd.read_excel(self.log_file, sheet_name='Predictions')
        except:
            existing_df = pd.DataFrame(columns=[
                'Timestamp', 'Date_Prediction', 'HomeTeam', 'AwayTeam', 'Event_Type',
                'Over_Line', 'Prob_IA', 'Cuota', 'Kelly_Amount', 'Instability_Score',
                'Status', 'Result_Value', 'Payout', 'Notes'
            ])
        
        # Combinar y guardar
        new_df = pd.DataFrame(self.predictions)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_excel(self.log_file, index=False, sheet_name='Predictions')
        
        # Limpiar predictions después de guardar
        self.predictions = []
    
    @staticmethod
    def calculate_results(log_file="data/prediction_log.xlsx", results_file="data/match_results.xlsx"):
        """
        Automático: Calcula W/L basado en resultados reales
        Requiere que se haya llenado 'Result_Value' manualmente o vía API
        
        Args:
            log_file: Archivo de predicciones
            results_file: Archivo con resultados (opcional)
        """
        try:
            df = pd.read_excel(log_file, sheet_name='Predictions')
        except:
            print("No hay archivo de predicciones")
            return
        
        # Calcular SI hay datos de resultado
        df['Payout'] = df.apply(
            lambda row: (
                row['Kelly_Amount'] * row['Cuota'] 
                if (row['Result_Value'] is not None and row['Result_Value'] >= row['Over_Line'])
                else (
                    -row['Kelly_Amount'] 
                    if (row['Result_Value'] is not None and row['Status'] == 'Pending')
                    else None
                )
            ),
            axis=1
        )
        
        df['Status'] = df.apply(
            lambda row: (
                'Win' if (row['Payout'] is not None and row['Payout'] > 0)
                else ('Loss' if (row['Payout'] is not None and row['Payout'] < 0) else 'Pending')
            ),
            axis=1
        )
        
        df.to_excel(log_file, index=False, sheet_name='Predictions')
        
        # Mostrar estadísticas
        completed = df[df['Status'] != 'Pending']
        if len(completed) > 0:
            total_roi = completed['Payout'].sum()
            total_staked = completed[completed['Status'] == 'Loss']['Kelly_Amount'].sum()
            roi_percent = (total_roi / total_staked * 100) if total_staked > 0 else 0
            
            print("\n" + "═"*50)
            print("ESTADÍSTICAS DE BACKTESTING")
            print("═"*50)
            print(f"Predicciones Completadas: {len(completed)}")
            print(f"Ganancias: {completed[completed['Status'] == 'Win']['Payout'].sum():.2f}€")
            print(f"Pérdidas: {completed[completed['Status'] == 'Loss']['Payout'].sum():.2f}€")
            print(f"ROI Total: {total_roi:.2f}€")
            print(f"ROI %: {roi_percent:.2f}%")
            print("═"*50)
    
    def log_validation(self, date_match, home_team, away_team, event_type, selection, 
                      prediction_value, actual_value, precision=None, notes=""):
        """
        Registra VALIDUCIONES: Predicción IA vs Resultado Real (POST-PARTIDOS)
        
        Ideal para backtesting y comparativas técnicas del sistema V2.0
        
        Args:
            date_match (str): Fecha del partido
            home_team (str): Equipo local
            away_team (str): Equipo visitante
            event_type (str): Tipo de evento ('Corners', 'Shots', 'Shots Target', etc.)
            selection (str): Selección del pronóstico (ej: 'Over 11.5 Remates')
            prediction_value (float): Valor predicho por IA
            actual_value (float): Valor real del evento
            precision (float): Precisión alcanzada (0-1), si no se especifica se calcula auto
            notes (str): Notas adicionales
        
        Ejemplo:
            logger.log_validation(
                date_match='2026-02-15',
                home_team='Bremen',
                away_team='Bayern',
                event_type='Shots',
                selection='Bremen +11.5 Remates',
                prediction_value=18.4,
                actual_value=14,
                precision=0.76,
                notes='Sistema V2.0'
            )
        """
        
        # Calcular precisión si no se proporciona
        if precision is None:
            # Precisión = (1 - |predicción - real| / predicción) * 100
            error_percent = abs(prediction_value - actual_value) / (prediction_value + 0.1)
            precision = max(0, 1 - error_percent)  # Entre 0 y 1
        
        # Determinar si fue correcto (Over/Under)
        is_correct = "✅" if abs(prediction_value - actual_value) < 1.5 else "⚠️"
        
        validation = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Date_Match': date_match,
            'HomeTeam': home_team,
            'AwayTeam': away_team,
            'Partido': f"{home_team} vs {away_team}",
            'Event_Type': event_type,
            'Selección': selection,
            'Prediction_IA': round(prediction_value, 1),
            'Actual_Value': round(actual_value, 1),
            'Accuracy': round(precision * 100, 1),
            'Status': is_correct,
            'Notes': notes
        }
        
        self.predictions.append(validation)
    
    def save_validations(self, sheet_name='Validations'):
        """Guarda validaciones en una sheet separada del Excel"""
        if not self.predictions:
            return
        
        log_file = self.log_file
        
        # Verificar si el archivo existe y tiene la sheet
        try:
            with pd.ExcelWriter(log_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_validations = pd.DataFrame(self.predictions)
                df_validations.to_excel(writer, sheet_name=sheet_name, index=False)
        except:
            # Si la sheet no existe o hay error, crearla
            try:
                df_validations = pd.DataFrame(self.predictions)
                df_validations.to_excel(log_file, sheet_name=sheet_name, index=False)
            except:
                print(f"[ERROR] No se pudo guardar validaciones en {log_file}")
        
        # Limpiar después de guardar
        self.predictions = []
    
    @staticmethod
    def print_validation_summary(log_file="data/prediction_log.xlsx", sheet_name='Validations'):
        """Muestra resumen de validaciones (precisión promedio, aciertos, etc.)"""
        try:
            df = pd.read_excel(log_file, sheet_name=sheet_name)
        except:
            print(f"[ERROR] No se encontró sheet '{sheet_name}' en {log_file}")
            return
        
        if len(df) == 0:
            print("No hay validaciones registradas")
            return
        
        total_predictions = len(df)
        avg_accuracy = df['Accuracy'].mean()
        correct_predictions = len(df[df['Status'] == '✅'])
        
        print("\n" + "═"*60)
        print("RESUMEN DE VALIDACIONES - SISTEMA V2.0")
        print("═"*60)
        print(f"Total de validaciones: {total_predictions}")
        print(f"Aciertos: {correct_predictions} ({correct_predictions/total_predictions*100:.1f}%)")
        print(f"Precisión Promedio: {avg_accuracy:.1f}%")
        print(f"Mejor Predicción: {df['Accuracy'].max():.1f}%")
        print(f"Peor Predicción: {df['Accuracy'].min():.1f}%")
        print("═"*60)
        
        # Mostrar tabla resumen
        print("\n[VALIDACIONES DETALLADAS]")
        print(df[['Partido', 'Event_Type', 'Selección', 'Prediction_IA', 'Actual_Value', 'Accuracy', 'Status']].to_string(index=False))

