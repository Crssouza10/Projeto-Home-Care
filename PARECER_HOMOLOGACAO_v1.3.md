# 📋 PARECER DE HOMOLOGAÇÃO — PROJETO CUIDADOSO v1.3

**Data:** 30/07/2026  
**Solicitante:** Carlos Roberto de Souza  
**Executor:** Maximus (Diretor-Coordenador Hermes Agent)  
**Agentes acionados:** Backend Analyst · Frontend Analyst · QA/Tester  
**Método:** Análise paralela multidisciplinar (3 agentes simultâneos)

---

## 🔴 PARECER: NÃO HOMOLOGADO

O projeto **não atende aos critérios mínimos de qualidade e segurança** para homologação. Foram identificados **14 bugs ativos** (5 críticos, 6 altos, 3 médios), **9 vulnerabilidades de segurança** (4 críticas) e **inconsistências de arquitetura** entre os 5 frontends e o backend. Recomenda-se correção dos itens críticos antes da homologação.

---

## 📊 CONSOLIDAÇÃO DOS RESULTADOS

### Bugs Ativos (14)

| ID | Severidade | Módulo | Descrição |
|---|---|---|---|
| B1 | 🔴 CRÍTICO | Backend | `temp_user_id` não definido em `criar_assinatura()` (NameError) |
| B2 | 🔴 CRÍTICO | Backend | `from models import ...` — módulo inexistente em `notificar_responsavel_se_nao_tomou()` |
| B3 | 🔴 CRÍTICO | Frontend | `index.html` preços desatualizados (R$49,90/R$79,90 vs v1.3 R$29,90/R$49,90) |
| B4 | 🔴 CRÍTICO | Frontend | `landing.html` redireciona login para `/ia` — rota inexistente |
| B5 | 🔴 CRÍTICO | Infra | `DATABASE_URL` fallback hardcoded → dev acessa banco de produção |
| B6 | 🟡 ALTO | Backend | Campo `location` ausente no modelo Appointment (frontend já envia) |
| B7 | 🟡 ALTO | Backend | `trial` inexistente no backend mas presente na landing page |
| B8 | 🟡 ALTO | Frontend | `saveResponsible()` L1008: `maxResp = plan === 'pro' ? 2 : 1` (deveria ser 1) |
| B9 | 🟡 ALTO | Frontend | `dashboard_cliente.html`: `saveResponsible()` não valida limite localmente |
| B10 | 🟡 ALTO | Frontend | `home_care_ia.html`: sem editar/excluir responsáveis e emergência |
| B11 | 🟡 ALTO | Frontend | Dois dashboards com features divergentes (ex: location, calendário, PWA) |
| B12 | 🟢 MÉDIO | Frontend | `requirements.txt` não inclui `groq` |
| B13 | 🟢 MÉDIO | Frontend | Inconsistência de versão: v1.5 no topbar, V1.3 no login, v1.3 no app.py |
| B14 | 🟢 MÉDIO | UX | Sem feedback de loading / estado offline nos dashboards |

### Vulnerabilidades de Segurança (9)

| ID | Severidade | Descrição |
|---|---|---|
| S1 | 🔴 CRÍTICA | SHA256 sem salt para senhas |
| S2 | 🔴 CRÍTICA | Senha admin hardcoded (`admin123`) |
| S3 | 🔴 CRÍTICA | Reset de senha retorna senha em plain text (`redefinida123`) |
| S4 | 🔴 CRÍTICA | DATABASE_URL hardcoded como fallback |
| S5 | 🟡 ALTA | Sem JWT/sessão — autenticação frágil |
| S6 | 🟡 ALTA | CORS wildcard (`allow_origins=["*"]`) |
| S7 | 🟡 ALTA | Login vulnerável a enumeração de usuários |
| S8 | 🟢 MÉDIA | Sem rate limiting (brute force) |
| S9 | 🟢 MÉDIA | Credenciais em localStorage (XSS) |

### Riscos de Negócio/Infra (7)

| ID | Risco | Probabilidade | Impacto |
|---|---|---|---|
| R1 | Mercado Pago não configurado → perda de receita | Alta | Crítico |
| R2 | Banco de produção usado em dev → corrupção de dados | Média | Crítico |
| R3 | Túnel Cloudflare efêmero → URL muda, links quebram | Alta | Médio |
| R4 | Sem testes automatizados → regressões não detectadas | Alta | Alto |
| R5 | Dois dashboards concorrentes → manutenção duplicada | Certa | Alto |
| R6 | `force push` do Carlos → perda de código | Média | Crítico |
| R7 | DeepSeek/Gemini API offline → Chat e OCR quebram | Baixa | Médio |

---

## 📝 CHECKLIST EXECUTIVO DE HOMOLOGAÇÃO

### Ações Imediatas (antes do deploy)

- [ ] **Corrigir B1:** Adicionar `temp_user_id = uuid.uuid4()` antes da linha 3681
- [ ] **Corrigir B2:** Remover `from models import ...` ou criar módulo models.py
- [ ] **Atualizar index.html:** Preços: R$49,90→R$29,90 (Básico), R$79,90→R$49,90 (Pró)
- [ ] **Corrigir landing.html:** Redirecionar login para `/dashboard` (não `/ia`)
- [ ] **Adicionar `groq` ao requirements.txt**
- [ ] **Adicionar campo `location` na tabela appointments** (migration + modelo + endpoints)
- [ ] **Corrigir `saveResponsible()`** no `home_care_ia.html` L1008: `const maxResp = 1;`

### Ações de Curto Prazo (próximo sprint)

- [ ] Substituir SHA256 por bcrypt/passlib com salt
- [ ] Remover senha hardcoded do admin (`POST /api/create-admin`)
- [ ] Corrigir forgot-password para gerar token em vez de retornar senha
- [ ] Remover DATABASE_URL hardcoded — usar apenas env var
- [ ] Restringir CORS para origens explícitas
- [ ] Adicionar tratamento de estado offline nos dashboards
- [ ] Unificar versão (v1.3) em todos os arquivos
- [ ] Adicionar feedback de loading visual nos dashboards

### Ações de Médio Prazo (roadmap)

- [ ] Implementar JWT para autenticação
- [ ] Implementar rate limiting
- [ ] Criar suíte de testes automatizados (pytest + Playwright)
- [ ] Unificar dashboards (`home_care_ia.html` + `dashboard_cliente.html`)
- [ ] Configurar CI/CD com GitHub Actions
- [ ] Migrar túnel Cloudflare para túnel nomeado (URL fixa)
- [ ] Adicionar ambiente de staging separado da produção
- [ ] Implementar validação client-side de limite de responsáveis no dashboard legado

---

## 📂 RELATÓRIOS GERADOS

| Arquivo | Conteúdo | Tamanho |
|---|---|---|
| `RELATORIO_FRONTENDS.md` | Análise completa de 5 frontends | 18.8 KB |
| `QA_CUIDADOSO_RELATORIO.md` | Plano de testes + 17 casos + 24 riscos | 34.1 KB |
| Subagent backend | 63 endpoints, 9 modelos, 9 vulns, 6 bugs | 17.1 KB |

---

**Conclusão:** O projeto tem base sólida (FastAPI + Supabase + IA + MP) mas acumulou débito técnico significativo com a evolução acelerada (v2.3.6 → v1.3). A homologação deve ser reavaliada após correção dos 7 itens imediatos e 4 críticos de segurança.
