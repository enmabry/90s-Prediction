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
