import re

file_path = "C:/Users/carlo/.gemini/antigravity-ide/scratch/Projeto-Home-Care/dashboard_cliente.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Substitui todas as ocorrencias de error.message que estao em contextos de exibicao (showToast, alert, console, etc)
# por obterMensagemErro(error)
original_len = len(content)

# Regex para substituir error.message por obterMensagemErro(error)
content = re.sub(r"error\.message", "obterMensagemErro(error)", content)
content = re.sub(r"err\.message", "obterMensagemErro(err)", content)

# Corrige tambem os caracteres zoados "â Œ " para "❌ " para ficar limpo
content = content.replace("â Œ", "❌")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Modificado com regex. Comprimento inicial: {original_len}, final: {len(content)}")
