import os
from dotenv import load_dotenv

load_dotenv()

# Configura o Cwd no PATH para importar o modulo app
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import _send_email_via_gmail_api

to_email = "crs.home.care.ai@gmail.com"
subject = "Teste de Redirecionamento - CTG-104"
body = "Este e um teste para verificar o redirecionamento automatico para o e-mail do proprietario do Resend."

print(f"Enviando e-mail para: {to_email}")
res = _send_email_via_gmail_api(to_email=to_email, subject=subject, body=body)
print(f"Resultado do envio: {res}")
