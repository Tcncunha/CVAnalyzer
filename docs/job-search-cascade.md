# Job Search — Multi-Source Cascade

Decisão de arquitetura para busca de vagas em escala global no CVAnalyzer,
com **custo zero (R$0)**, **zero risco de ban** e dados **estruturados**.

**Data:** 2026-09-10
**Status:** Implementado (backend + frontend + testes) — validação QA: 234 passed na suíte completa.

---

## 1. Contexto e problema

O CVAnalyzer já tem uma aba "Job Search" funcional com integração à **Adzuna API**
(`src/job_search.py`), cobrindo 19 países. O objetivo é expandir a cobertura para
**escala global** sem gastar dinheiro e sem tomar ban em sites como LinkedIn,
Indeed, Glassdoor ou Pracuj.pl.

### Pergunta central analisada
> "MCP ou WebSearch para escala global?"

**Resposta da análise (Olhudo/BA):** nenhum dos dois. Ambos foram rejeitados em
favor do uso de **APIs oficiais gratuitas de múltiplos provedores**.

| Opção | Veredicto | Motivo |
|---|---|---|
| WebSearch | ❌ | Snippets não-estruturados; parsing de vários sites; risco de ToS |
| MCP (ex.: jobspy) | ❌ | Scraping disfarçado de LinkedIn/Indeed/Glassdoor; ban garantido no LinkedIn; manutenção frágil |
| **APIs oficiais gratuitas** | ✅ | Zero custo, zero ban, JSON estruturado, ToS claro |

Além disso, dados confirmados em 2026:
- **Adzuna** — agregado multi-país (19 países).
- **Himalayas** — 95.000+ vagas remotas globais, sem chave.
- **SerpApi/Google Jobs** — plano grátis de 250 buscas/mês.
- **Jooble** — chave grátis, porém **500 requisições na vida útil** por chave.
- **Arbeitnow** — feed público keyless com foco Europa/Alemanha (+ UK).
- **USAJOBS** — API pública do governo dos EUA (somente federal, se `country=us`).

---

## 2. Decisão de arquitetura: Cascata de fontes

O app tenta as fontes em ordem e **para assim que atingir o alvo N**
(= o valor de "Resultados por página", padrão 20).

```
Adzuna (on-site multi-país)
   ↓ se total < N
Himalayas (remoto global)
   ↓ se total < N
SerpApi / Google Jobs (global, opcional — requer chave grátis)
   ↓ se total < N
Jooble (agregador global, opcional — requer chave grátis)
   ↓ se total < N
Arbeitnow (Europa/Alemanha + UK)
   ↓ se total < N
USAJOBS (somente quando país = US, requer chave grátis)
```

### Regras gerais da cascata
- Provedor **sem chave configurada** é pulado silenciosamente (Adzuna, SerpApi,
  Jooble, USAJOBS precisam de credencial; Himalayas e Arbeitnow não precisam).
- **Deduplicação obrigatória** por `título + empresa + local` normalizados —
  Adzuna e Google Jobs agregam os mesmos boards (Indeed/Glassdoor).
- Falha de uma fonte não derruba a busca — registrada e segue para a próxima.
- Cada item retorna o schema normalizado já usado hoje + o campo `source`
  (ex.: `adzuna`, `himalayas`, `google_jobs`...) para exibir o **badge da fonte**.

---

## 3. Tabela comparativa das fontes (validado em 2026)

| Fonte | Custo | Quota gratuita real | Key? | Escopo | Campos ricos |
|---|---|---|---|---|---|
| **Adzuna** | R$0 | ~2.500 req/mês · 25/min | Sim (grátis) | 19 países, agrega vários boards | salário, categoria, `redirect_url` |
| **Himalayas** | R$0 | Sem limite publicada (rate limit 429) | **Não** | 95.000+ vagas remotas globais | salário (29 moedas, incl. PLN/BRL), senioridade, timezone |
| **SerpApi / Google Jobs** | R$0 | 250 buscas/mês · 50/h (caches não contam) | Sim (grátis) | Global | salário, via, data |
| **Jooble** | R$0 | **500 requisições na vida útil** por chave; 1 chave por país | Sim (grátis) | Agregador global | salário, snippet |
| **Arbeitnow** | R$0 | Feed keyless | **Não** | Europa (DE/PL…) + UK (`.co.uk`) | **filtros aplicados client-side** (API ignora params) |
| **USAJOBS** | R$0 | Alto volume | Sim (grátis) | EUA — federal | resumo, organização, local |

### Observações de uso
- **Adzuna**: exige exibição do logo "Jobs by Adzuna" e link de volta.
- **Himalayas**: exige link de volta à vaga original + crédito a Himalayas;
  proíbe re-envio a agregadores (Jooble, Neuvoo, Google Jobs, LinkedIn Jobs).
- **Arbeitnow**: desconfiar de `links.next` — o parâmetro `remote=true` é ecoado
  sem aplicar filtro; filtros devem ser feitos **localmente** sobre os dados.
- **Jooble**: é o mais limitado (500 req na vida útil). Permanece na ordem
  solicitada, porém é bom candidato a ser desativado se o consumo for alto.
- **Erros de fonte**: a UI exibe apenas os nomes das fontes que falharam
  (chaves de `errors` de `run_cascade`); a mensagem detalhada fica no log
  estruturado — comportamento intencional.

---

## 4. Plano de implementação por arquivo

| Arquivo | Ação |
|---|---|
| **`src/job_providers.py`** (novo) | Base `JobProvider` + adaptadores: `AdzunaProvider`, `HimalayasProvider`, `SerpApiProvider`, `JoobleProvider`, `ArbeitnowProvider`, `USAJobsProvider`; orquestrador `run_cascade(config, target)` com dedup e skip silencioso |
| **`src/job_search.py`** | `fetch_jobs` passa a delegar ao `AdzunaProvider`; normalização exposta e reutilizável |
| **`src/ui.py`** | Aba Job Search (~357-427): toggle "Modo cascata" + alvo N; sidebar (~170-182): chaves opcionais SerpApi/Jooble/USAJOBS; badge de fonte em cada card; legenda "Adzuna: 15 · Himalayas: 8 · ..." |
| **`src/i18n.py`** | Strings novas (PT/EN/ES): fonte, cascata, alvo, badges, mensagens de provedor |
| **`src/app.py`** | Sem mudança estrutural (tab Job Search já registrado) |

### Provedores — referências de endpoint
- Adzuna: `https://api.adzuna.com/v1/api/jobs/{country}/search/1`
- Himalayas: `https://himalayas.app/jobs/api/search?q=&country=&page=`
  (spec OpenAPI 3.1 em `https://himalayas.app/docs/openapi.json`)
- SerpApi: `https://serpapi.com/search?engine=google_jobs&q=&location=`
- Jooble: `POST https://{domain}.jooble.org/api/{key}` (ex.: `jooble.org` = US)
- Arbeitnow: `https://www.arbeitnow.com/api/job-board-api` (+ `.co.uk` p/ UK)
- USAJOBS: `https://data.usajobs.gov/api/search?Keyword=&LocationName=`
  (headers `User-Agent` + `Authorization: Bearer <key>`)

---

## 5. Regras de negócio (RN) e requisitos

| ID | Regra |
|----|-------|
| **RN01** | Busca de vagas **somente via APIs oficiais/gratuitas** — nunca scraping de sites que bloqueiam acesso automatizado |
| **RN02** | Respeitar rate limits de cada API (Adzuna, SerpApi 250/mês, Jooble 500 lifetime) |
| **RN03** | Chaves de API **session-only**, nunca persistidas em disco (padrão já existente) |
| **RN04** | Cascata para quando o total < N; alvo N = "Resultados por página" |
| **RN05** | Deduplicar por `título+empresa+local`; manter `source` por item |
| **RN06** | Provedor sem chave é pulado silenciosamente; falha de fonte não aborta a busca |
| **RN07** | "Usar nesta análise" busca descrição completa via `src/job_fetcher.py` e preenche o Analyzer |
| **RN08** | UI indica cobertura de cada fonte (🌍 Remoto / 🇪🇺 Europa / 🗽 EUA / 🔎 Google Jobs) |
| **RN09** | Falha total → mensagem clara + fallback manual (colar descrição) |

---

## 6. Fora de escopo

- ❌ Scraping de LinkedIn, Indeed, Glassdoor, Pracuj.pl
- ❌ APIs pagas (JobsPipe $49/mês, JSearch/SerpApi além do free tier, Re 500 lifetime)
- ❌ MCP servers dentro do Streamlit (protocolo para LLMs, não para apps)
- ❌ Candidatura automática, cache persistente de vagas, notificações
- ❌ Mudanças na aba de "Match" (o "Usar nesta análise" já conecta Job Search → Match)

---

## 7. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Jooble esgotar (500 req lifetime) | Manter desativável; badge + contagem de chamadas visíveis |
| SerpApi free tier (250/mês) | Apenas invocado quando as keyless não completam o alvo; cache de busca grátis |
| Arbeitnow ignora filtros de query | Filtrar **client-side** sobre o feed |
| Duplicatas entre fontes | Dedup obrigatório por título+empresa+local |
| Quota Adzuna (2.500/mês) | Cascata prioriza virar para keyless antes de repetir chamadas |

---

## 8. Handoff — entregue vs. pendências

**Entregue (backend):**
1. ✅ `src/job_providers.py` — base `JobProvider` + adaptadores (`AdzunaProvider`, `HimalayasProvider`, `SerpApiProvider`, `JoobleProvider`, `ArbeitnowProvider`, `USAJobsProvider`) e orquestrador `run_cascade(config, target)` com dedup e skip silencioso
2. ✅ `src/job_search.py` — `fetch_jobs` delega ao `AdzunaProvider`; normalização única em `job_providers` (sem import circular)
3. ✅ Testes de automação (`tests/test_job_providers.py` + demais) — suíte completa 234 passed

**Entregue (frontend):**
4. ✅ `src/ui.py` — toggle "Modo cascata" + alvo N; chaves opcionais SerpApi/Jooble/USAJOBS na sidebar; badge de fonte em cada card; legenda de cobertura e erros por fonte
5. ✅ `src/i18n.py` — strings novas PT/EN/ES (fonte, cascata, alvo, badges, mensagens de provedor)

**Pendências (validação operacional):**
6. ⏳ Teste manual com chaves reais (Adzuna, SerpApi, Jooble, USAJOBS) — a suíte automatizada é hermética (mocks, zero rede)
7. ⏳ Itens da seção 6 (Fora de escopo) permanecem de fora, por decisão do ADR