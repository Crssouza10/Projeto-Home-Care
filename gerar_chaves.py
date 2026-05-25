from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Gera o par de chaves EC P-256 (padrão VAPID)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Converte para Base64 URL-Safe (formato exigido pelo navegador)
def format_key(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).decode('utf-8').rstrip('=')

# Extrai bytes
pub_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
priv_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Imprime no formato correto
print("🔵 PUBLIC_KEY:", format_key(pub_bytes))
print("🔴 PRIVATE_KEY:", format_key(priv_bytes))