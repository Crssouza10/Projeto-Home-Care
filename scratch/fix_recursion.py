file_path = "C:/Users/carlo/.gemini/antigravity-ide/scratch/Projeto-Home-Care/dashboard_cliente.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Corrige a recursao infinita acidental na funcao obterMensagemErro
content = content.replace(
    "const msg = error ? (obterMensagemErro(error) || String(error)) : '';",
    "const msg = error ? (error.message || String(error)) : '';"
)

# Corrige tambem os caracteres zoados "â Œ " para "❌ " em todo o arquivo
content = content.replace("â Œ ", "❌ ")
content = content.replace("â Œ", "❌")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Corrigido recursão e caracteres zoados!")
