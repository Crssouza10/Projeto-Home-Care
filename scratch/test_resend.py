import os
import requests
from dotenv import load_dotenv

load_dotenv()

resend_api_key = os.getenv("RESEND_API_KEY")
to_email = "crs.home.care.ai@gmail.com"

print(f"Key: {resend_api_key[:15]}...")
print(f"To: {to_email}")

resend_url = "https://api.resend.com/emails"
headers = {
    "Authorization": f"Bearer {resend_api_key}",
    "Content-Type": "application/json"
}

payload = {
    "from": "CR$ Home Care <onboarding@resend.dev>",
    "to": to_email,
    "subject": "Teste de Envio Resend API - CTG-104",
    "text": "Este é um teste de envio de e-mail usando a API do Resend."
}

try:
    resp = requests.post(resend_url, headers=headers, json=payload, timeout=20)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Erro ao enviar: {e}")
