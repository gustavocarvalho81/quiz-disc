from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import os
import time
import json

class GoogleSheetsManager:
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        try:
            credentials_json = os.getenv('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise Exception("GOOGLE_CREDENTIALS environment variable not found")
                
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=self.SCOPES)
            
            self.service = build('sheets', 'v4', credentials=credentials)
            self.spreadsheet_id = '18cxDWZAjzrpw21HpjRvLWOWKCe-oakhqm0ZTyduL_nk'
            print("Conexão com Google Sheets estabelecida com sucesso!")
        except Exception as e:
            print(f"Erro ao inicializar Google Sheets: {str(e)}")
            self.save_local_backup({"error": "Falha na inicialização", "details": str(e)})
            raise

    def _execute_with_retry(self, func):
        """Executa uma função com tentativas múltiplas em caso de erro"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func()
            except HttpError as e:
                last_error = e
                if e.resp.status == 429:  # Too Many Requests
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"Rate limit - Aguardando {wait_time} segundos")
                    time.sleep(wait_time)
                    continue
                break
            except TimeoutError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"Timeout - Tentativa {attempt + 1} de {self.max_retries}")
                    time.sleep(wait_time)
                    continue
                break
            except Exception as e:
                last_error = e
                print(f"Erro inesperado: {str(e)}")
                break
        
        # Se chegou aqui, todas as tentativas falharam
        print(f"Todas as tentativas falharam. Último erro: {str(last_error)}")
        return None

    def save_local_backup(self, data):
        """Salva os dados localmente em caso de falha"""
        try:
            backup_dir = 'backup'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backup_file = os.path.join(backup_dir, 'responses_backup.jsonl')
            with open(backup_file, 'a', encoding='utf-8') as f:
                backup_data = {
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }
                f.write(json.dumps(backup_data, ensure_ascii=False) + '\n')
            print(f"Backup local salvo em: {backup_file}")
        except Exception as e:
            print(f"Erro ao salvar backup local: {str(e)}")

    def setup_sheet(self):
        """Configura os cabeçalhos da planilha"""
        def _setup():
            headers = [
                'Data/Hora',
                'Nome',
                'Email',
                'Empresa',
                'Q1 - Autoconhecimento (Resposta)',
                'Q1 - Pontuação',
                'Q2 - Áreas de Destaque (Resposta)',
                'Q2 - Pontuação',
                'Q3 - Identificação DISC (Resposta)',
                'Q3 - Pontuação',
                'Q4 - Liderança (Resposta)',
                'Q4 - Pontuação',
                'Q5 - Perfil Comportamental (Resposta)',
                'Q5 - Pontuação',
                'Pontuação Total'
            ]
            
            body = {
                'values': [headers]
            }
            
            return self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range='A1:O1',
                valueInputOption='RAW',
                body=body
            ).execute()

        result = self._execute_with_retry(_setup)
        if result is None:
            print("Falha ao configurar planilha - salvando cabeçalhos localmente")
            self.save_local_backup({"type": "headers_setup", "timestamp": datetime.now().isoformat()})

    def save_response(self, user_data, responses, scores):
        """Salva as respostas na planilha"""
        print("\nIniciando salvamento na planilha...")
        print("Dados do usuário:", user_data)
        print("Respostas:", responses)
        print("Pontuações:", scores)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calcular pontuação total
        total_score = sum(scores.values())
        print(f"Pontuação total: {total_score}")
        
        # Preparar linha para salvar
        row = [
            now,
            user_data.get('name', ''),
            user_data.get('email', ''),
            user_data.get('company', '')
        ]
        
        # Adicionar respostas e pontuações para cada questão
        for q_num in range(1, 6):
            q_id = str(q_num)
            if q_id in responses:
                row.append('; '.join(responses[q_id]))  # Respostas
                row.append(scores.get(q_id, 0))        # Pontuação
            else:
                row.append('')  # Resposta vazia
                row.append(0)   # Pontuação zero
        
        # Adicionar pontuação total
        row.append(total_score)
        
        print("Linha preparada para salvar:", row)
        
        try:
            # Encontrar próxima linha vazia
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A:A'
            ).execute()
            next_row = len(result.get('values', [])) + 1
            
            # Salvar dados
            body = {
                'values': [row]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'A{next_row}:O{next_row}',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("Dados salvos com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao salvar na planilha: {str(e)}")
            # Se falhar, tentar salvar localmente
            backup_data = {
                "user_data": user_data,
                "responses": responses,
                "scores": scores,
                "timestamp": datetime.now().isoformat()
            }
            self.save_local_backup(backup_data)
            return False