import re

file_path = "C:/Users/carlo/.gemini/antigravity-ide/scratch/Projeto-Home-Care/dashboard_cliente.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Substitui as mensagens de erro genericas pelo obterMensagemErro
replacements = [
    ("showToast('â Œ ' + error.message, true);", "showToast('❌ ' + obterMensagemErro(error), true);"),
    ("showToast('❌ ' + error.message, true);", "showToast('❌ ' + obterMensagemErro(error), true);"),
    ("showToast('â Œ Erro: ' + error.message, true);", "showToast('❌ Erro: ' + obterMensagemErro(error), true);"),
]

original_len = len(content)
for old, new in replacements:
    content = content.replace(old, new)

# Para casos onde os caracteres bizarros aparecem de formas ligeiramente diferentes
content = re.sub(r"showToast\('[\w\sâŒ❌\s]*'\s*\+\s*error\.message\s*,\s*true\s*\);", "showToast('❌ ' + obterMensagemErro(error), true);", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Modificado dashboard_cliente.html. Comprimento inicial: {original_len}, final: {len(content)}")
