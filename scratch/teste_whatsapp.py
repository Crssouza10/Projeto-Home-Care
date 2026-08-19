import os
import requests
import re
import sys
from dotenv import load_dotenv

# Forçar stdout para usar utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Tenta carregar .env do diretório atual ou do pai
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")

token = os.getenv("WHATSAPP_TOKEN")
phone_id = os.getenv("WHATSAPP_PHONE_ID")
telefone = "5561996127140"  # Número de teste do usuário

print(f"Token (truncado): {token[:15] if token else 'Nenhum'}...")
print(f"Phone ID: {phone_id}")

if not token or not phone_id:
    print("Erro: WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID ausentes no .env!")
    sys.exit(1)

url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data = {
    "messaging_product": "whatsapp",
    "to": telefone,
    "type": "text",
    "text": {
        "body": "💊 *CR$ HOME CARE AI (TESTE DE CONEXÃO)*\n\nOlá! Este é um teste de envio de notificações via API Oficial do WhatsApp.\n\nSeu sistema está integrado com sucesso! 👍"
    }
}

try:
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print("[SUCCESS] WhatsApp enviado com sucesso!")
        print("Resposta:", response.json())
    else:
        print(f"[ERROR] Erro da API WhatsApp: Code {response.status_code}")
        print("Erro detalhado:", response.text)
except Exception as e:
    print(f"[FAIL] Falha de conexão: {e}")
