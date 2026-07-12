# 📖 Manual de Implementações Inteligentes — CR$ Home Care AI

Este manual detalha as novas funcionalidades de inteligência artificial, acessibilidade por voz, otimização de layout mobile-first e funcionamento em segundo plano integradas na versão **v2.1.1 (build 2026-07-12)**.

---

## 1. 🎤 Acessibilidade por Voz & Alertas Personalizados

A IA Maximus fala com o usuário e interage de forma adaptativa.

### Como funciona:
- **Áudio Contextual com Horário**: Quando chega a hora de uma medicação ou quando o aplicativo faz a verificação pós-5 minutos, a IA sintetiza voz personalizada informando o nome e o horário programado do remédio.
  * *Exemplo de Lembrete:* `"Atenção! Está na hora de tomar o seu remédio Lisador, 1 comprimido, agendado para às 06:00."`
  * *Exemplo de Pergunta:* `"Você já tomou o seu remédio Lisador, 1 comprimido, agendado para às 06:00?"`
- **Reconhecimento de Fala Adaptativo**: O usuário responde por voz ("Tomei", "Sim", "Não" ou "Reagendar"). O aplicativo entende a resposta e executa a ação de forma síncrona.
- **Detecção de Horário por Transcrição**: Ao solicitar o reagendamento por voz, a IA compreende expressões coloquiais como *"reagendar para as dez e meia"* e converte automaticamente em formato digital `10:30` para atualizar o cronograma.

> [!TIP]
> **Dica de Autoplay**: Navegadores mobile bloqueiam a saída de som automática sem interação prévia. Sempre que entrar no aplicativo, dê um toque em qualquer lugar da tela para que os alertas sonoros sejam autorizados a tocar no horário exato!

---

## 2. ☁️ Lembretes Offline & Web Push Interativo (Segundo Plano)

O aplicativo funciona de forma inteligente mesmo se estiver completamente fechado ou com o celular bloqueado.

### Como funciona:
- **Notificação Rica**: O sistema dispara uma notificação do sistema com o payload estruturado (nome do medicamento, dosagem e horário).
- **Botões de Ação Direta**: A notificação no celular exibe dois botões de ação:
  1. `✅ Tomei o Remédio`: Registra a tomada no banco de dados Supabase instantaneamente, sem precisar abrir o aplicativo ou o navegador.
  2. `🔍 Abrir`: Redireciona o usuário diretamente para o painel de cuidados.
- **Sincronização em Tempo Real**: Caso o usuário tome o remédio pressionando o botão de fora da notificação enquanto o painel estiver aberto em segundo plano, o Service Worker envia um aviso interno que atualiza e recarrega os dados da tela imediatamente.

---

## 3. 📋 Ficha Médica Inteligente com IA & OCR

O painel de controle do paciente foi simplificado, e todas as informações importantes foram consolidadas na **Ficha Médica** (acessada pelo ícone de Perfil 👤).

```
[👤 Perfil Clínico]
       |
       +---> [Ficha Médica]
                   |
                   +---> Informações Clínicas (Idade, Sangue, Doenças)
                   |
                   +---> Responsável & Contatos de Emergência
                   |
                   +---> 📷 Importar Laudo (OCR de Alergias)
                   |
                   +---> 📤 Importar Carteirinha (OCR + Upload de Imagem)
```

### 3.1. OCR Inteligente de Alergias 📷
- Ao editar a Ficha Médica, o usuário pode clicar em **`📷 Importar Laudo (OCR)`**.
- Ao tirar foto de um exame, laudo ou receita contendo alergias, a IA do Gemini lê a imagem, extrai os termos médicos de alergia e os insere organizados e formatados por vírgula no campo de texto de Alergias.

### 3.2. Importação & Upload da Carteirinha do Plano de Saúde 📤
- O usuário clica em **`📤 Importar Carteirinha`** para enviar a foto da carteirinha do plano de saúde.
- A IA do Gemini lê a imagem, identifica automaticamente o nome da operadora e o número da matrícula (ex: `Amil (Nº 38472910...)`) e preenche o campo de texto.
- A imagem da carteirinha é arquivada com segurança no servidor e exibida como miniatura interativa na Ficha Médica. O usuário pode clicar nela a qualquer momento para abrir em tamanho real.

### 3.3. Rede de Apoio Integrada (Responsável & Contatos)
- O **Responsável** (que recebe os alertas de atraso via WhatsApp) e até **2 Contatos de Emergência** são gerenciados dentro da Ficha Médica, reduzindo a poluição visual da tela principal.

---

## 4. 📱 Interface Otimizada & Mobile-First

O layout do aplicativo foi refinado para garantir que funcione perfeitamente em telas pequenas (smartphones).

- **Fim dos Cortes Horizontais**: Todas as margens de visualização (`max-width: 100%`, `overflow-x: hidden`) foram rigidamente testadas para garantir que nenhuma barra de rolagem horizontal apareça no mobile.
- **Aproximação de Botões**: Os botões de ação do card (Câmera 📷, Calendário 📅, Editar ✏️ e Excluir 🗑️) foram movidos para a esquerda, colados ao badge de horário. Isso resolveu definitivamente os cortes no botão de excluir (Lixeira) em celulares de telas estreitas.
