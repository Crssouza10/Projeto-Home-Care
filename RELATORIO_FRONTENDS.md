# 📊 RELATÓRIO DE ANÁLISE DE FRONTENDS — PROJETO CUIDADOSO

**Versão:** v1.3 (29/07/2026)  
**Data da Análise:** 30/07/2026  
**Plataforma:** cuidaidoso.ia.br — Home Care Inteligente  
**Analista:** Hermes Agent

---

## 1. 📁 ARQUIVOS — Inventário

| Arquivo | Linhas | Tamanho | Tipo | Status |
|---|---|---|---|---|
| `home_care_ia.html` | 1.204 | 58 KB | Dashboard Cliente (principal/novo) | ✅ Ativo |
| `dashboard_cliente.html` | 7.641 | 368 KB | Dashboard Cliente (legado/completo) | ⚠️ Legado |
| `dashboard.html` | 195 | 19 KB | Dashboard Admin | ✅ Ativo |
| `landing.html` | 829 | 34 KB | Landing Page (tema escuro) | ✅ Ativo |
| `index.html` | 1.619 | 59 KB | Landing Page "Cuidadoso" (tema verde) | ✅ Ativo — Fonte da verdade |
| **TOTAL** | **11.488** | **∼538 KB** | 5 frontends | |

### Rotas do servidor (`cuidadoso-server.py`)

| Rota | Arquivo |
|---|---|
| `/` | `landing.html` |
| `/dashboard` | `home_care_ia.html` |
| `/dashboard-admin` | `dashboard.html` |
| `/dashboard-cliente` | `dashboard_cliente.html` |

---

## 2. 🧩 FUNCIONALIDADES POR DASHBOARD

### 2.1 `home_care_ia.html` (1.204 linhas) — Dashboard Cliente Principal

| Página/Seção | Funcionalidades |
|---|---|
| **Login/Registro** | Login via API (`/api/cliente/login`), registro via API (`/api/users`), auto-login via URL param `?user=`, persistência em `sessionStorage` |
| **Visão Geral** | Estatísticas (medicamentos hoje, tomados, pendentes, consultas futuras), lista de próximos medicamentos com botões "Tomei"/"Não tomei" |
| **Medicamentos** | CRUD completo, seleção de dias da semana, horário, dosagem, data de término/uso contínuo, marcar como tomado/não tomado, reagendar |
| **Consultas** | CRUD (médico, especialidade, data, hora, observações), confirmar/editar/excluir |
| **Responsáveis** | CRUD com validação de limite por plano, notificações (SMS, WhatsApp, Ligação) |
| **Emergência** | CRUD de contatos (nome, tipo, telefone, email, observações) |
| **Dados Clínicos** | Ficha clínica (idade, tipo sanguíneo, alergias, condições, plano de saúde), card de plano com upgrade |
| **Sistema** | Toast notifications, navegação SPA via abas, modal overlay, plano (Básico/Pro) |

### 2.2 `dashboard_cliente.html` (7.641 linhas) — Dashboard Cliente Legado

| Funcionalidade | Detalhes |
|---|---|
| **PWA Ready** | Manifest, service worker, notifications, install prompt |
| **Header** | Avatar, nome do usuário, estatísticas (remédios/consultas), data, logout |
| **Medicamentos** | Cards com ações "Tomei"/"Depois", status visual, revisão de contínuos vencidos |
| **Consultas** | Cards com borda colorida (confirmado/cancelado), campo `location` com link Google Maps |
| **Responsáveis** | Cards com avatar, ações WhatsApp/Ligação |
| **Contatos de Emergência** | Cards com tipo colorido |
| **Calendário Interativo** | Navegação entre meses, indicadores de eventos (🟢 meds, 🔴 consultas, ambos), legenda, seleção de dia |
| **Monitoramento** | Verificação de medicamentos a cada 30s, lembretes de consultas a cada 5min |
| **Trial Bar** | Badge de dias restantes (apenas trial), botão de upgrade |
| **Upload de Receita** | Botão flutuante para OCR (oculto para trial) |
| **Delete Inteligente** | Modal de confirmação com contagem de schedules futuras |
| **TTS/Áudio** | Alertas sonoros para medicamentos |
| **Scroll Único** | Todas as seções visíveis em scroll (sem abas) |

### 2.3 `dashboard.html` (195 linhas) — Dashboard Admin

| Funcionalidade |
|---|
| Lista de clientes ativos com estatísticas (medicamentos, consultas, responsáveis, contatos) |
| Calendário estático (mês atual) |
| Header com logo CR$, notificação, data |
| Autenticação via `localStorage.is_logged_in` |
| API: `GET /api/admin/clientes` |

### 2.4 `landing.html` (829 linhas) — Landing Page Tema Escuro

| Seção | Conteúdo |
|---|---|
| Hero | Título, subtítulo, CTAs (Criar Conta / Login) |
| Planos | Básico (R$29,90) + Pro (R$49,90) — **preços v1.3 corretos** |
| Funcionalidades | 6 cards (medicamentos, consultas, cuidadores, emergência, ficha clínica, notificações) |
| Como Funciona | 3 passos |
| Para Quem | Idosos, Familiares, Cuidadores |
| CTA Final | Banner de cadastro gratuito |
| Modal | Login/Cadastro simples (não split-screen) |

### 2.5 `index.html` (1.619 linhas) — Landing Page "Cuidadoso" (Tema Verde)

| Seção | Conteúdo |
|---|---|
| **Nav** | Links: Funcionalidades, Planos, Como funciona, Depoimentos, FAQ, Entrar, Começar grátis |
| **Hero** | Badge IA, título, ilustração com cards flutuantes |
| **Trust Bar** | DeepSeek AI, Supabase, Dados criptografados |
| **Features** | 6 cards (lembretes, registro de saúde, conexão familiar, consultas, ficha, leitura de receitas por foto) |
| **Pricing** | Trial (14 dias grátis) + Básico (R$49,90/mês) + Pro (R$79,90/mês) — **⚠️ preços DESATUALIZADOS** |
| **How it Works** | 4 passos com fundo escuro |
| **Testimonials** | 3 depoimentos |
| **FAQ** | 8 perguntas frequentes |
| **CTA** | Cadastro gratuito |
| **Modal Split-Screen** | Coluna esquerda: detalhes do plano · Coluna direita: login/cadastro · Google/Apple OAuth (stubs) · Mercado Pago redirect · `openLogin(planKey)` |
| **JS** | `plansData` (trial/basico/pro), `handleLogin`, `handleRegister`, bind dos botões via `DOMContentLoaded` |

---

## 3. 🐛 BUGS CATALOGADOS

### 3.1 BUGS CONHECIDOS (já documentados/parcialmente corrigidos)

| ID | Arquivo | Linha | Descrição | Status | Impacto |
|---|---|---|---|---|---|
| **B1** | `home_care_ia.html` | 1008 | `saveResponsible()`: `const maxResp = plan === 'pro' ? 2 : 1;` — deve ser `1` para todos na v1.3 | ❌ NÃO CORRIGIDO | 🔴 ALTO — Contas Pro podem adicionar 2 responsáveis indevidamente |
| **B2** | `dashboard_cliente.html` | 2448-2474 | Trial badge aparecia para contas não-trial (condição sempre verdadeira) | ✅ CORRIGIDO (local) | 🟢 Resolvido |
| **B3** | `dashboard_cliente.html` | 5056 | Campo `location` nas consultas enviado ao backend mas sem suporte | ⚠️ BACKEND PENDENTE | 🟡 MÉDIO — Dado enviado mas não persistido |
| **B4** | `index.html` | 962-989 | Preços desatualizados: Básico R$49,90 (deveria ser R$29,90), Pro R$79,90 (deveria ser R$49,90) | ❌ NÃO CORRIGIDO | 🔴 ALTO — Divergência crítica de pricing |
| **B5** | `index.html` | 1293-1296 | `plansData.trial` mostra "Até 2 pessoas cuidadas" — skill diz que v1.3 não tem lógica de trial no backend | ⚠️ INCONSISTÊNCIA | 🟡 MÉDIO — Trial não existe no backend |

### 3.2 BUGS NOVOS (encontrados nesta análise)

| ID | Arquivo | Descrição | Impacto |
|---|---|---|---|
| **N1** | `home_care_ia.html` | Topbar mostra "v1.5 - 27/07/2026" enquanto a tela de login mostra "V1.3 - 29/07/2026" — inconsistência de versão no mesmo arquivo | 🟡 BAIXO — Confusão de versionamento |
| **N2** | `dashboard_cliente.html` | `saveResponsible()` (linha 5100) NÃO valida limite de responsáveis por plano — envia direto para API sem verificação local | 🟡 MÉDIO — API rejeita (backend faz validação), mas UX ruim (erro só no retorno) |
| **N3** | `home_care_ia.html` | `renderResponsibles()` não tem botão de excluir/editar responsável — só exibe lista | 🟡 MÉDIO — Funcionalidade incompleta |
| **N4** | `home_care_ia.html` | `renderEmergencyContacts()` não tem botão de excluir/editar — mesma limitação | 🟡 MÉDIO |
| **N5** | `dashboard_cliente.html` | Botão flutuante de receita OCR oculto para trial, mas `isTrialOrFree` também captura `currentUser.full_name.toLowerCase().includes('gratis')` — frágil | 🟡 MÉDIO — Heurística por nome |
| **N6** | `landing.html` | `doLogin()` redireciona para `window.location.href = '/ia'` — rota `/ia` não existe no `cuidadoso-server.py` | 🔴 ALTO — Login quebrado na landing page tema escuro |

---

## 4. 🔄 CONSISTÊNCIA ENTRE DASHBOARDS

### 4.1 `home_care_ia.html` vs `dashboard_cliente.html`

| Aspecto | `home_care_ia.html` | `dashboard_cliente.html` |
|---|---|---|
| **API Base** | `''` (mesma origem) | `API_URL` variável (dinâmica) |
| **Persistência** | `sessionStorage.hc_user` | `localStorage.userId` + `localStorage.currentUser` |
| **Navegação** | SPA com abas (sidebar) | Scroll único (todas seções visíveis) |
| **Medicamentos** | Lista simples + botões inline | Cards visuais + "Tomei"/"Depois" + status |
| **Consultas** | Sem campo `location` | **Com** campo `location` + link Google Maps |
| **Calendário** | ❌ Não tem | ✅ Interativo com indicadores coloridos |
| **PWA** | ❌ Não tem | ✅ Manifest, SW, notifications |
| **Monitoramento** | ❌ Não tem | ✅ 30s meds + 5min consultas |
| **OCR Receita** | ❌ Não tem | ✅ Botão flutuante (Pro apenas) |
| **TTS/Áudio** | ❌ Não tem | ✅ Alertas sonoros |
| **Delete Inteligente** | ❌ Não tem | ✅ Modal com contagem de schedules |
| **Editar/Excluir** | Medicamentos e consultas sim; responsáveis e emergência NÃO | ✅ Completo em todas as entidades |
| **Validação Limite** | Cliente-side (com bug) + backend | Apenas backend |
| **Tema** | Escuro (cyberpunk) | Escuro (navy) |
| **Plano** | Card no Dados Clínicos + upgrade | Trial bar no header |
| **Versão** | "v1.5" (topbar) / "V1.3" (login) | Não exibe versão |

### 4.2 Duas Landing Pages

| Aspecto | `landing.html` | `index.html` |
|---|---|---|
| **Nome** | "CR$ HOME CARE AI" | "Cuidadoso" |
| **Tema** | Escuro (azul/cyan) | Claro (verde/branco) |
| **Preços** | ✅ v1.3 corretos: R$29,90 / R$49,90 | ❌ Antigos: R$49,90 / R$79,90 |
| **Planos** | 2 planos (sem Trial) | 3 planos (com Trial) |
| **Modal** | Simples (login OU cadastro) | Split-screen (plano + formulário) |
| **OAuth** | Não | Google + Apple (stubs) |
| **Mercado Pago** | Não | Sim (`/api/register-subscribe`) |
| **Qualidade CSS** | Bom, organizado | Excelente, design system |
| **Qualidade JS** | Básico | Robusto, fallback offline |
| **Fonte da verdade** | 🟡 Secundária | ✅ Principal (indicada pela skill) |

---

## 5. 🎨 UX/UI — Análise

### 5.1 Pontos Positivos

- ✅ **`index.html`**: Design system maduro — variáveis CSS, grid responsivo, animações sutis, tipografia com Outfit/Inter, seções bem estruturadas
- ✅ **`dashboard_cliente.html`**: Calendário interativo excelente, indicadores coloridos diferenciados (verde para meds, vermelho para consultas), legenda
- ✅ **`dashboard_cliente.html`**: Scroll único sem abas — evita confusão de navegação para idosos
- ✅ **`dashboard_cliente.html`**: Base font 17px (pensado para idosos), botões grandes, contraste adequado
- ✅ **`home_care_ia.html`**: Sidebar + abas — padrão familiar para usuários técnicos

### 5.2 Problemas de UX

| ID | Arquivo | Problema | Severidade |
|---|---|---|---|
| **UX1** | `home_care_ia.html` | Sem feedback de carregamento visual (loading spinner) durante chamadas API | 🟡 MÉDIO |
| **UX2** | `home_care_ia.html` | Lista de medicamentos não diferencia visualmente medicamentos do dia vs. todos | 🟡 MÉDIO |
| **UX3** | `dashboard_cliente.html` | 7.641 linhas — excessivamente longo, difícil manutenção | 🔴 ALTO |
| **UX4** | `dashboard.html` | Totalmente estático — hardcoded "Bom dia, Administrador", não puxa nome real | 🟡 MÉDIO |
| **UX5** | `dashboard.html` | Calendário com eventos hardcoded `[7,9,15,22]` — dados fake | 🟡 MÉDIO |
| **UX6** | Ambos dashboards | Nenhum tratamento de estado offline — falha silenciosamente | 🔴 ALTO |

### 5.3 Responsividade

| Arquivo | Mobile | Tablet | Desktop |
|---|---|---|---|
| `home_care_ia.html` | ✅ Sidebar vira horizontal, grid 2 col, lista empilhada | ✅ OK | ✅ OK |
| `dashboard_cliente.html` | ✅ Bem tratado (calendário compacto, cards empilhados) | ✅ Grid adapta | ✅ Grid 1fr+380px |
| `dashboard.html` | ✅ @media 768px | ✅ OK | ✅ OK |
| `landing.html` | ✅ Stack vertical, botões full-width | ✅ OK | ✅ OK |
| `index.html` | ✅ Excelente: 2 breakpoints (900px, 600px), nav collapse | ✅ OK | ✅ OK |

### 5.4 Acessibilidade

| Aspecto | Status |
|---|---|
| `prefers-reduced-motion` | ✅ Apenas em `index.html` e `landing.html` |
| `:focus-visible` | ✅ Apenas em `landing.html` |
| Contraste | ✅ Satisfatório nos temas escuros |
| Alt text em imagens | ❌ Nenhum atributo `alt` significativo |
| ARIA labels | ❌ Ausentes em todos os arquivos |
| Navegação por teclado | ⚠️ Parcial — modais fecham com Escape, mas sem trap de foco |
| Tamanho de fonte | ✅ 16-17px base (bom para idosos) |

---

## 6. 💻 CÓDIGO — Más Práticas e Duplicações

### 6.1 JavaScript Inline

Todos os 5 arquivos usam **exclusivamente** `<script>` inline no próprio HTML — **zero arquivos .js externos**.

| Arquivo | Linhas de JS (~) | Funções (~) |
|---|---|---|
| `home_care_ia.html` | ∼550 linhas | ∼25 funções |
| `dashboard_cliente.html` | ∼4.500 linhas | 118 funções |
| `dashboard.html` | ∼55 linhas | 3 funções |
| `landing.html` | ∼90 linhas | 7 funções |
| `index.html` | ∼330 linhas | 14 funções |

### 6.2 Funções Duplicadas / Redundantes

| Função | Presente em | Observação |
|---|---|---|
| `doLogin()` | `home_care_ia.html` (L579), `landing.html` (L761), `index.html` (`handleLogin` L1423) | 3 implementações diferentes da MESMA funcionalidade |
| `doRegister()` | `home_care_ia.html` (L610), `landing.html` (L790), `index.html` (`handleRegister` L1490) | 3 implementações diferentes |
| `saveResponsible()` | `home_care_ia.html` (L999), `dashboard_cliente.html` (L5100) | Lógica duplicada com validações diferentes |
| `saveAppointment()` | `home_care_ia.html` (L918), `dashboard_cliente.html` (L5042) | Divergência: legado tem campo `location`, novo não |
| `saveMedication()` | `home_care_ia.html` (L808), `dashboard_cliente.html` (∼L5000) | Duplicado |
| `renderMedications()` | Ambos dashboards | Lógicas de renderização diferentes |
| `formatDate()` | Ambos dashboards | Função utilitária simples mas duplicada |
| `toast()` / `showToast()` | Ambos dashboards | Nomes e implementações diferentes |

### 6.3 Más Práticas Identificadas

| ID | Problema | Arquivo(s) | Severidade |
|---|---|---|---|
| **MP1** | `sessionStorage` para dados sensíveis (user object com potential token) | `home_care_ia.html`, `landing.html` | 🔴 ALTO |
| **MP2** | `localStorage` como mecanismo de auth (`is_logged_in === 'true'`) — bypass trivial | `dashboard.html`, `index.html` | 🔴 ALTO |
| **MP3** | Fallback offline com credenciais hardcoded (`admin`/`admin123`) | `index.html` L1436-1453 | 🔴 CRÍTICO |
| **MP4** | `innerHTML` com dados da API sem sanitização — XSS potential | Todos os dashboards | 🔴 ALTO |
| **MP5** | Variáveis globais (`state`, `API`, `userId`, `currentUser`, `medicationsData`) | Todos | 🟡 MÉDIO |
| **MP6** | `confirm()` nativo para diálogos de confirmação | `home_care_ia.html`, `dashboard_cliente.html` | 🟡 MÉDIO |
| **MP7** | `alert()` para erros e mensagens ao usuário | `landing.html`, `dashboard_cliente.html` | 🟡 MÉDIO |
| **MP8** | Tratamento de erro inconsistente — alguns try/catch genéricos, outros sem catch | Todos | 🟡 MÉDIO |
| **MP9** | Código CSS duplicado entre arquivos (variáveis de tema, estilos de modal, grid backgrounds) | `dashboard_cliente.html` + `dashboard.html` | 🟡 MÉDIO |
| **MP10** | `setTimeout` mágico para sincronização (`loadAllData()` + 300ms depois carregar seções) | `dashboard_cliente.html` L2512 | 🟡 MÉDIO |

### 6.4 Console.log de Debug em Produção

`dashboard_cliente.html` está repleto de `console.log` com prefixos `[DIAGNÓSTICO]`:
- Linhas 5195, 5199, 5201, 5203, 5208... — dezenas de logs ativos
- Excesso de logs degrada performance e expõe estrutura interna

---

## 7. 📋 RECOMENDAÇÕES PRIORIZADAS

### 🔴 CRÍTICO (Corrigir IMEDIATAMENTE)

| # | Ação | Arquivo |
|---|---|---|
| 1 | Remover fallback `admin`/`admin123` hardcoded | `index.html` L1436-1453 |
| 2 | Corrigir `saveResponsible()` — `maxResp = 1` para todos | `home_care_ia.html` L1008 |
| 3 | Atualizar preços no `index.html`: Básico R$29,90 / Pro R$49,90 | `index.html` precificação + `plansData` |
| 4 | Corrigir redirect `/ia` → `/dashboard` na landing page | `landing.html` L782 |
| 5 | Sanitizar innerHTML ou usar `textContent`/`createElement` | Todos |

### 🟡 ALTO (Próxima sprint)

| # | Ação |
|---|---|
| 6 | Unificar `doLogin()`/`doRegister()` — extrair para módulo compartilhado |
| 7 | Adicionar campo `location` ao modal de consultas do `home_care_ia.html` |
| 8 | Adicionar backend suporte ao campo `location` na tabela `appointments` |
| 9 | Substituir `localStorage` auth por token JWT seguro |
| 10 | Adicionar botões de editar/excluir em Responsáveis e Emergência no `home_care_ia.html` |

### 🟢 MÉDIO (Backlog)

| # | Ação |
|---|---|
| 11 | Extrair CSS compartilhado para arquivo externo |
| 12 | Extrair JS para módulos — fim do monólito inline |
| 13 | Remover `console.log` de diagnóstico em produção |
| 14 | Adicionar tratamento de estado offline |
| 15 | Adicionar ARIA labels e navegação por teclado |
| 16 | Unificar versionamento nos headers |

### 💡 ESTRATÉGICO

| # | Ação |
|---|---|
| 17 | Decidir: `landing.html` vs `index.html` — qual é a landing page canônica? Eliminar a outra |
| 18 | Decidir: `home_care_ia.html` vs `dashboard_cliente.html` — unificar dashboards ou manter ambos? |
| 19 | Migrar para framework SPA (React/Vue/Svelte) ou ao menos usar Web Components |

---

## 8. 📊 RESUMO EXECUTIVO

| Métrica | Valor |
|---|---|
| **Frontends ativos** | 5 |
| **Linhas totais de código** | 11.488 |
| **Bugs confirmados** | 10 (4 conhecidos + 6 novos) |
| **Bugs críticos** | 3 (B1, B4, N6) |
| **Problemas de segurança** | 3 (MP1, MP2, MP3) |
| **Funções duplicadas** | 8 pares/grupos |
| **Más práticas código** | 10 categorias |
| **Consistência entre dashboards** | BAIXA — divergências significativas em API base, persistência, features, e UX |
| **Qualidade do `index.html`** | ⭐⭐⭐⭐⭐ (melhor frontend do projeto) |
| **Qualidade do `dashboard_cliente.html`** | ⭐⭐⭐ (funcional mas inchado) |
| **Qualidade do `home_care_ia.html`** | ⭐⭐⭐ (limpo mas incompleto) |

---

**Conclusão:** O projeto tem 2 landing pages e 2 dashboards cliente competindo entre si, com funcionalidades complementares mas não unificadas. O `index.html` é o frontend mais bem-acabado enquanto o `dashboard_cliente.html` é o mais completo em funcionalidades. A prioridade imediata é corrigir os 3 bugs críticos (B1: limite de responsáveis, B4: preços desatualizados, N6: redirect quebrado) e remover credenciais hardcoded.
