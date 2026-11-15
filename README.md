# firesync

Calendário harmonizado de focos de calor (MODIS + VIIRS) para o NASA Space Apps 2026, desafio [MODIS and VIIRS Hot Spots](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/).

O usuário escolhe uma área e um período e vê um calendário meses × anos com o número de focos de calor. A série junta MODIS (2003 em diante) e VIIRS (2012 em diante) numa escala única, então o sensor de origem não importa mais para quem lê o calendário.

**Prazo da submissão:** domingo, 15/11/2026, 23h59 (horário do evento local).

**Objetivo: ganhar um prêmio global.** Primeiro, nota alta nos 5 critérios de julgamento, que decidem quem chega à final. Depois, as categorias-alvo (Best Use of Data, Best Use of Science e Local Impact), que guiam a história na página e no vídeo. Tudo em [docs/premiacao.md](docs/premiacao.md). Leia antes de qualquer tarefa.

## Para agentes: ordem de leitura

Leia nesta ordem antes de escrever código. Os documentos são a fonte de verdade. Se o código e um documento discordarem, pergunte antes de mudar qualquer um dos dois.

| # | Documento | O que define | Quando ler |
| --- | --- | --- | --- |
| 1 | [Requisitos](docs/requisitos.md) | O que o desafio exige (RF), o que dá pontos (RD), requisitos não funcionais e checklist da submissão | Sempre |
| 2 | [FIRMS — extração e dados disponíveis](docs/firms-extracao-dados.md) | Sensores, datas, formas de baixar (arquivo, API, WMS), colunas dos CSVs | Antes de mexer em importação ou API do FIRMS |
| 3 | [Plano de extração — Brasil (Amazônia)](docs/plano-extracao-amazonia.md) | Quais dados baixar, papel de cada satélite, dados de validação (IBGE, INPE), jobs de atualização | Antes de mexer no pipeline |
| 4 | [Importação de novas regiões](docs/importacao-regioes.md) | Importador, tabelas, chave única, fatores de harmonização por região, como adicionar região | Antes de mexer no banco, no pipeline ou na API |
| 5 | [Arquitetura e stack](docs/arquitetura.md) | Stack de cada componente, o que já está decidido e o que falta decidir | Antes de escrever qualquer código |
| 6 | [Tarefas](docs/tarefas.md) | Frentes, responsáveis, branches, pastas de cada um, marcos e status | Antes de começar qualquer tarefa |
| 7 | [Pipeline de dados — o que já foi feito](docs/pipeline-dados.md) | Download do histórico, filtros de qualidade, análise por satélite, achados | Antes de mexer em `data-pipeline/` |
| 8 | [Banco de dados — decisões para o backend](docs/banco.md) | Imagem, H3, resolução, schema, consulta da API, carga na VPS, benchmark | Antes de mexer no banco ou na API |
| 9 | [Contrato da API](docs/api.md) | Endpoints, pedido, resposta, erros, export de auditoria. JSON de exemplo em [api-exemplo.json](docs/api-exemplo.json) | Antes de mexer na API ou no front |
| 10 | [Prompt do frontend](docs/prompt-frontend.md) | Prompt para o agente que constrói o front: direção de design, regras de dado na tela, animação, performance e etapas de construção | Antes de começar a frente D |
| 11 | [Critérios de julgamento e prêmios](docs/premiacao.md) | Os 5 critérios, as categorias-alvo e as regras de prioridade da equipe | Antes de qualquer tarefa |
| 12 | [Decisões da harmonização](docs/decisoes-harmonizacao.md) | Fator Aqua → S-NPP, faixa P5–P95, resultado da calibração e limites a declarar no Método | Antes de mexer em calibração, agregação ou na conta da API |
| 13 | [Regras entre as variáveis](docs/regras-variaveis.md) | Colunas de cada sensor, regras de remoção e de duplicata, classificador complementar | Antes de mexer nos filtros do pipeline |
| 14 | [UX: racional das telas](docs/ux-telas.md) | Objetivo, tarefas e decisões do usuário em cada tela | Antes de mexer no front |
| 15 | [Pitch e vídeo](docs/pitch.md) | Roteiro de 30 s, legenda em inglês e como gravar | Antes de montar a demo |
| 16 | [Testes e esteira](docs/testes.md) | TDD, regra dos bugs, cobertura, jornadas e jobs do GitHub Actions | Antes de escrever código |
| 17 | [Versionamento (SemVer)](docs/versionamento.md) | Tipo no commit e no título do PR, como lançar uma versão | Antes do primeiro commit |
| 18 | [Validação do nível de alerta](docs/validacao-alerta.md) | Solução A + B da issue #9: teste retroativo com "o que veio depois" e eventos conhecidos, no lugar da área queimada | Antes de mexer no alerta ou no `alert_rules.json` |
| 19 | [RFC 0001: backtest do alerta](docs/rfcs/0001-backtest-alerta.md) | Como implementar a solução A + B: consultas, janelas, contas, saídas, autoteste e plano | Antes de implementar o backtest do alerta |
| 20 | [Validação da API com a carga real](docs/validacao-api-eduardo.md) | Roteiro para o Eduardo conferir números, cobertura, ZIP e latência antes de fechar D7/M2 | Ao integrar a API com a carga real |
| 21 | [Simulação e auditoria pelos logs](docs/simulacao.md) | Como rodar o sistema de ponta a ponta num banco descartável e auditar pelos logs se ele entrega o que os critérios cobram | Antes de rodar a simulação ou investigar um problema |
| 22 | [Restrições para o mundo](docs/escala-mundial.md) | O que muda quando a cobertura passar do Brasil para o mundo, com a saída proposta para cada ponto | Antes de mexer em cobertura, seleção de área ou camada de focos |
| 23 | [Deploy](docs/deploy.md) | Front no Cloudflare, banco/API/job NRT na VPS pelo Cloudflare Tunnel, variáveis e segurança da VPS | Antes de publicar ou mexer em `infra/` |
| 24 | [Página do projeto](docs/pagina-projeto.md) | Texto em inglês de cada campo da página do projeto no Space Apps (C9) | Antes de preencher ou mudar a página da submissão |
| 25 | [RFC 0004: assistente virtual](docs/rfcs/0004-assistente-virtual.md) | Chat no site que responde perguntas com tool-use sobre os casos de uso da API: ferramentas, contrato `/ask`, front, riscos e plano | Antes de mexer no assistente |

Regras para agentes: [CLAUDE.md](CLAUDE.md).

## Estrutura do repositório

```
firesync/
├── README.md              este arquivo (mapa do projeto)
├── CLAUDE.md              regras para agentes
├── docs/                  todos os documentos do projeto (tabela acima)
├── data-pipeline/         download, importação, calibração, agregação e job NRT (frentes A e B)
│   ├── migrations/        schema do banco, aplicado em ordem
│   └── data/              ZIPs do FIRMS (Brasil, 2024, SP) para testes
├── backend/               API que serve o calendário, a janela recente e o export (frente C)
├── frontend/              aplicação web: mapa, calendário, alerta, downloads (frente D)
├── lovable/               protótipo feito no Lovable (TanStack Start); a abertura do globo foi portada para `frontend/src/hero/`
├── config/                regras que mudam sem mudar o código, como o alert_rules.json
└── infra/                 deploy na VPS: docker-compose com Cloudflare Tunnel, .env.example (frente C)
```

Cada pasta tem um `README.md` com o que vai nela, quem é responsável e as regras que valem ali. `backend/` tem as cinco rotas HTTP, histórico, janela recente, camada de focos, ZIP auditável e testes unitários, HTTP, PostGIS e E2E com dados sintéticos. `frontend/` já traz o esqueleto (D1), a seleção de área, período e camada de focos recentes no mapa (D2–D3, RD07), o calendário (D4), os indicadores/gráficos (D5), os downloads e pacote de auditoria (D6), o proxy e integração com a API (D7) e os testes E2E em `frontend/e2e/`. `infra/` tem o compose da VPS (banco, API, jobs NRT e de risco e túnel) e o `.env.example`. `data-pipeline/data/` tem os quatro ZIPs de teste:

| Arquivo | Conteúdo |
| --- | --- |
| `DL_FIRE_M-C61_848018.zip` | MODIS C6.1 (Terra + Aqua) |
| `DL_FIRE_SV-C2_848021.zip` | VIIRS S-NPP |
| `DL_FIRE_J1V-C2_848019.zip` | VIIRS NOAA-20 |
| `DL_FIRE_J2V-C2_848020.zip` | VIIRS NOAA-21 |

## Rodar localmente

Com `DATABASE_URL` configurada no ambiente e o banco carregado:

```powershell
python -m pip install -e './backend[test]'
python -m uvicorn backend.adapters.inbound.http.app:create_app --factory --host 127.0.0.1 --port 8000
```

Em outro terminal, `cd frontend`, `npm ci` e `npm run dev`. O proxy `/api` aponta para `http://localhost:8000`; `VITE_DEV_API_PROXY` permite usar `http://127.0.0.1:8000` quando necessário. Variáveis, rate limit, testes e carga sintética estão em [backend/README.md](backend/README.md). A validação da carga científica real será feita pelo Eduardo, conforme o [roteiro M2](docs/validacao-api-eduardo.md).

## Como os dados fluem

```
CSV do FIRMS (arquivo SP ou API NRT)
  → importador         normaliza colunas, calcula H3, upsert em `focos`
  → recorte por região polígono em `regioes` (bioma IBGE)
  → calibração         fatores por região em `fatores_harmonizacao` (congelados após a carga)
  → agregação          `agregados`: célula H3 × ano × mês, focos harmonizados
  → API                soma as células da área desenhada, responde "sem dados" fora da `cobertura`
  → frontend           calendário, sazonalidade, ranking de anos, anomalias, downloads
```

Detalhes de cada etapa: [importacao-regioes.md](docs/importacao-regioes.md).

## Regras que não mudam sem falar com a equipe

- O calendário começa em **janeiro de 2003**. Terra não entra no cálculo, só Aqua.
- **Um VIIRS por período, nunca a soma.** S-NPP até 02/11/2026, NOAA-20 depois. NOAA-21 só como reserva no NRT.
- Escala VIIRS: Aqua × fator (bioma × mês × dia/noite, um cenário por ano) de jan/2003 a jan/2012; S-NPP real de fev/2012 a out/2026; NOAA-20 real (fator 1) de nov/2026 em diante. Só confiança nominal ou alta e `type = 0`.
- Fatores ficam congelados depois da carga histórica. Jobs de atualização só aplicam o fator.
- Chave única do foco: (`satelite`, `lat`, `lon`, `datahora_utc`). Recarga SP apaga o NRT do período e insere o SP numa transação.
- Mês com falha de satélite (tabela `dias_sem_dados`) é diferente de mês com zero focos.
- Front e API não conhecem regiões específicas. Adicionar região é dado, não código.
- Interface em inglês, com crédito ao FIRMS visível.

## Estado atual

- [x] Requisitos e checklist da submissão
- [x] Levantamento do FIRMS e plano de extração
- [x] Modelo de dados e processo de importação
- [x] Dados de teste (Brasil, 2024)
- [x] Stack e arquitetura definidas (pipeline, banco, API, front, mapa e gráficos decididos em [arquitetura.md](docs/arquitetura.md))
- [ ] Contrato da API ([api.md](docs/api.md) na `main`; falta A e D confirmarem, tarefa T02)
- [x] Histórico do FIRMS baixado e análise por satélite ([pipeline-dados.md](docs/pipeline-dados.md))
- [x] Importador, pipeline, agregação, job NRT e série do INPE ([pipeline-dados.md](docs/pipeline-dados.md))
- [x] API HTTP C1–C6 (validação com dados sintéticos; conferência da carga real pelo Eduardo em [validacao-api-eduardo.md](docs/validacao-api-eduardo.md))
- [x] Frontend (D1–D7 prontos e conferidos com a carga real no site no ar em 15/11; aviso antecipado D10 no ar, conferido com a API real em 15/11; a demo D8 segue pendente)
- [ ] Deploy público
- [x] Texto da página do projeto ([pagina-projeto.md](docs/pagina-projeto.md); falta o link da demo)
- [ ] Demo (D8)

## Uso de IA

A submissão exige identificar o código gerado com IA. Registre aqui quais partes foram geradas ou assistidas por IA, e com qual ferramenta, à medida que o código entra.

| Parte | Ferramenta | Como foi usada |
| --- | --- | --- |
| Integração do PR #26 com a `main`, resolução de `data-pipeline/.coveragerc` e limpeza das pendências da B6 em `docs/` | OpenAI Codex | Preservação do mínimo de cobertura de 71% e atualização dos documentos conforme a issue #68; sem alteração das contas |
| `data-pipeline/pipeline.py`, `agregar.py`, `eda.py`, `test_pipeline.py`, `test_banco.py`, `job_nrt.py`, `Dockerfile`, `migrations/` | Claude Code (Claude Opus 5.5) | Código gerado a partir das especificações de filtro escritas pelo time de dados. Revisado pela equipe |
| `docs/banco.md`, `data-pipeline/migrations/001_inicial.sql` | Claude Code (Claude Opus 5.5) | Schema e documento de decisões gerados a partir dos docs do repo e de um benchmark local. Revisado pela equipe |
| `docs/pipeline-dados.md` | Claude Code (Claude Opus 5.5) | Redação do relatório do que foi feito e dos achados da análise exploratória |
| Teste de paridade API/backtest e calendário bissexto (issue #64) | OpenAI Codex | Comparação desde a série diária sintética, testes de limites e correção de 29/02 no backtest após falha reproduzida |
| Indicador anual da API, testes, contrato e tipo do frontend (issue #78) | OpenAI Codex | Ajuste em TDD para mediana dos anos de referência por cenário, conforme decisão da equipe na #75; integração do campo `reference_median` |
| Código e testes em `backend/src/`, `backend/tests/`, configuração Python e CI do backend | OpenAI Codex | Implementação assistida do domínio, portas, PostgreSQL e análise histórica; C1–C6 com cinco rotas FastAPI, janelas recentes, alerta com piso contínuo da issue #59 e configuração v1.0, intensidade, rate limit/cache, ZIP auditável, carga sintética em `backend/scripts/`, testes HTTP/PostGIS e E2E via proxy. TDD e CI conforme documentação da equipe |
| Estrutura e documentação do `backend/`, ajustes em `docs/arquitetura.md`, `docs/tarefas.md`, `docs/importacao-regioes.md` e `docs/api.md` | OpenAI Codex | Organização das camadas e revisão da documentação; atualização dos READMEs, requisitos, tarefas, testes e roteiro `docs/validacao-api-eduardo.md`. Decisões de método referenciadas nos registros da equipe |
| `docs/prompt-frontend.md` | Claude Code (Claude Opus 5.5) | Prompt do front escrito a partir dos docs do repo. A equipe aprova antes de usar |
| `docs/api.md`, `docs/api-exemplo.json` (issues #22 e #29) | Claude Code (Claude Opus 5.5) | Correções do contrato escritas a partir das issues da auditoria. Revisado pela equipe |
| `docs/validacao-alerta.md`, `docs/rfcs/0001-backtest-alerta.md` | Claude Code (Claude Opus 5.5) | Proposta de validação do alerta e RFC de implementação, escritos a partir da issue #9 e da revisão do PR #42. Revisado pela equipe |
| `data-pipeline/validacao/backtest_alerta.py`, `data-pipeline/tests/test_backtest_alerta.py`, `data-pipeline/referencia/eventos_conhecidos.csv` | Claude Code (Claude Opus 5.5) | Backtest do alerta escrito a partir do RFC 0001, com TDD; correção dos eventos conhecidos e da regra atual para o piso contínuo da `v1` (issue #66) e achados da revisão do PR #71 (piso da grade pelo JSON, limite e continuidade da antecedência). As fontes dos eventos foram conferidas nas páginas oficiais. Revisado pela equipe |
| Limpeza dos `.md` (README, CLAUDE.md, `docs/`, READMEs das pastas) | Claude Code (Claude Opus 5.5) | Levantamento do que estava desatualizado, comparando os docs com o código da `main`, e correção dos trechos. Revisado pela equipe no PR |
| `.github/workflows/ci.yml` (job "Só documentação?"), `.github/scripts/roda_testes.sh`, `test_roda_testes.sh` | Claude Code (Claude Opus 5.5) | Filtro que pula os testes de código em PR só de `.md`. Revisado pela equipe |
| `data-pipeline/harmonizacao/` (`calibrar.py`, `validar_inpe.py`, `modelo_a.py`, `test_calibrar.py`, `test_validar_inpe.py`), `data-pipeline/tests/test_harmonizacao.py`, `test_calibrar_integracao.py`, `test_modelo_a.py` | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Código escrito a partir das decisões de método do Weberson (escala VIIRS, fator por bioma, mês e dia ou noite, cenários por ano, faixa P5 a P95, critério de 1,5×, regras de limpeza e o modelo A pelo caminho C, RFC 0002). Os erros achados na revisão do PR #26 foram corrigidos com um teste para cada um. Revisado pelo Mateus |
| `docs/decisoes-harmonizacao.md`, `docs/regras-variaveis.md`, `docs/ux-telas.md`, seção de harmonização de `docs/importacao-regioes.md` | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Redação e análise feitas a partir das decisões do Weberson e dos resultados rodados pela frente A. As escolhas de método são da equipe e estão marcadas como tal nos documentos. Revisado pela equipe |
| `data-pipeline/validacao/modelo_risco.py`, `data-pipeline/tests/test_modelo_risco.py`, `docs/rfcs/0003-modelo-risco.md` | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Experimento do modelo de risco escrito com TDD a partir das decisões do Weberson (alvo, pistas, validação em avanço e regra de decisão fixada antes das rodadas de clima). A série dos dados públicos foi conferida contra a rodada da frente A no banco. O modelo da pergunta "fogo acima do normal?" não entra no produto. A equipe revisa no PR |
| Nível de urgência no mapa de focos recentes (`backend/src/domain/calculations/cell_alerts.py`, `map_features.py`, `alert.py`, `adapters/outbound/postgres/api.py`, `config/alert_rules.json` 1.1, testes e `docs/api.md`) | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Escrito com TDD a partir da decisão do Weberson (risco dos próximos 14 dias pela `v1`, na célula de resolução 4 em que ela foi testada). Reaproveita a função `alert_level` da API, com teste de paridade com o `recent`. Rafael e Eduardo revisam no PR |
| `data-pipeline/risco_celulas.py`, `data-pipeline/tests/test_risco_celulas.py`, `data-pipeline/migrations/005_risco_celulas.sql`, `config/risk_rules.json` | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Job do risco por célula com o modelo treinado ("onde vai ter fogo nos próximos 14 dias"), escrito com TDD a partir das decisões do Weberson (pergunta, alvo, variáveis, treino só com o passado, faixas por probabilidade e critério de decisão fixado antes de rodar). Reaproveita as funções do experimento do RFC 0003. A equipe revisa no PR |
| Decisões do front em `docs/arquitetura.md` (pontos 5 a 8) e `frontend/README.md` | Claude Code (Claude Opus 5.5) | Levantamento das opções e redação das justificativas. As escolhas foram feitas pela equipe |
| Ponto 4 de `docs/arquitetura.md` e responsáveis em `docs/tarefas.md` | Claude Code (Claude Opus 5.5) | Redação da justificativa e levantamento dos responsáveis pelos autores dos commits. As escolhas foram feitas pela equipe |
| `frontend/` (D9: nova interface, `index.html`, `src/hero/`, `src/calendar/CalendarSvg.tsx`, `src/map/`, `src/summary/`, `src/history/`, `src/discovery/`, `src/state/`, `src/styles.css` e testes) | Claude Code (Claude Opus 5.5) | Abertura com GSAP, área de análise, descoberta guiada, tela de Método e diagrama da harmonização, escritos a partir do prompt de direção de arte da frente D, do `api.md` e do `ux-telas.md`. Reaproveita o cliente da API e os modelos de D1–D7. A equipe revisa no PR |
| `data-pipeline/logs.py`, logs em `pipeline.py`, `agregar.py`, `job_nrt.py`, `tests/test_logs.py`, `docs/simulacao.md` | Claude Code (Claude Opus 5.5) | Logs estruturados gerados a partir do RNF07 e dos pontos de decisão do pipeline. Revisado pela equipe |
| `frontend/` (D1–D7: `index.html`, `src/`, configuração do Vite, testes unitários e E2E) | Claude Code (Claude Opus 5.5) em D1, D4, D5 e na fonte do decreto em Data & credits (#65); Antigravity em D2, D3, D6 e D7 | Esqueleto (D1), calendário (D4) e indicadores/gráficos (D5) gerados a partir do `prompt-frontend.md`, `api.md` e `ux-telas.md`. Seleção de área e período (D2–D3: mapa Leaflet + Geoman em `src/controls/`, cliente API `src/api/client.ts`, validação UTC, fallback demo), camada de focos recentes e integração com a API (D7: `GET /api/v1/detections/recent` em hexágonos `cividis` log e pontos por intensidade, proxy `/api` no Vite) e downloads/exportação (D6: pacote de auditoria `POST /api/v1/export`, CSVs e PNG do calendário em `src/export/` e todas as jornadas J1–J9 em `e2e/jornadas.spec.ts`) escritos em TDD a partir dos docs. A equipe revisa no PR |
| `docs/rfcs/0004-assistente-virtual.md` | Claude Code (Claude Opus 5.5) | RFC do assistente virtual escrito a partir da leitura do código da API (`application/api.py`, `ports/api.py`, rotas do `app.py`) e dos docs; decisão por tool-use no lugar de text-to-SQL; pontos da revisão do Mateus no PR #121 aplicados (risco, `hours`, idioma, validação de `messages[]`, custo e cadeia de provedores) |
| Mapa base padrão NASA GIBS (`frontend/src/map/MapStage.tsx`, `MapStage.test.tsx`) | Claude Code (Claude Opus 5.5) | Revisão das fontes de dados do projeto e troca do padrão em TDD. A equipe revisa no PR |
| Deploy (`infra/docker-compose.yml`, `infra/.env.example`, `backend/Dockerfile`, `.dockerignore`, `frontend/wrangler.jsonc`, `frontend/public/_headers`, `docs/deploy.md`) e IP real no rate limit atrás do Cloudflare (`app.py`, testes) | Claude Code (Claude Opus 5.5) | Configuração escrita a partir da decisão de pôr o front no Cloudflare e a API atrás do túnel; o bug do rate limit foi reproduzido num teste antes da correção. A equipe revisa no PR |
| Job de risco no deploy (`data-pipeline/Dockerfile`, serviço `job-risco` e `RISK_MAX_AGE_DAYS` em `infra/docker-compose.yml` e `infra/.env.example`, `docs/deploy.md`) | Claude Code (Claude Opus 5.5) | Configuração escrita a partir da issue #96 e testada rodando o job na imagem contra um Postgres descartável. A equipe revisa no PR |
| Carga do banco na VPS e status da C7 (`docs/tarefas.md`, `docs/deploy.md`, `README.md`; issue #98) | Claude Code (Claude Opus 5.5) | Roteiro de carga, acesso temporário para o dump e conferência guiados pela IA, executados e conferidos pela equipe na VPS; documentos atualizados com os endereços no ar |
| Aviso antecipado no mapa (D10: `frontend/src/map/alertsModel.ts`, `EarlyWarning.tsx`, tooltip em `src/controls/recentDetectionsModel.ts`, tipos, estilos e jornadas J10 e J11) | Claude Code (Claude Opus 5.5) | Escrito em TDD a partir do contrato dos PRs #86 e #97 e do texto do PR #103, com todos os campos novos opcionais; a correção do foco do mapa veio de uma jornada que falhava. A equipe revisa no PR |
| Resultados da frente B na tela de Método (`frontend/index.html`, `frontend/public/img/`, `src/index-html.test.ts`) | Claude Code (Claude Sonnet 5.5, Opus 5.5 e Fable 5.2) | Textos em inglês escritos a partir de `docs/decisoes-harmonizacao.md` e do RFC 0003, com os números copiados dos documentos, e testes antes do texto. A equipe revisa no PR |
| Ajustes da abertura em `lovable/` (`src/lib/opening-copy.ts`, `MapOpening.tsx`, `OrbitalScene.tsx`, `styles.css`, `src/assets/satellites/CREDITS.md`, teste `src/test/opening-copy.test.ts`) | Claude Code (Claude Opus 5.5) | Revisão da abertura pelos critérios do `docs/premiacao.md` e troca dos textos e dos rótulos dos satélites (Aqua; S-NPP → NOAA-20) conforme as regras do README, com o teste antes do código. O resto de `lovable/` foi gerado no Lovable pela equipe. A equipe revisa no PR |
| `docs/pagina-projeto.md` (C9) | Claude Code (Claude Opus 5.5) | Texto em inglês da página do projeto, escrito a partir dos docs do repo, da tela de Método e desta tabela, com os números copiados dos documentos. A equipe revisa no PR |
| Assets de `lovable/` no git (`src/assets/`: texturas da Terra, `aqua.glb`, `suomi-npp.glb`, `country-boundaries.geojson`; imports em `OrbitalScene.tsx`, `AreaMap.tsx`, `routes/index.tsx`) | Claude Code (Claude Opus 5.5) | Troca dos ponteiros `*.asset.json` (só funcionavam na hospedagem do Lovable) por arquivos das fontes públicas: modelos da NASA com o Draco decodificado, textura gerada da camada GIBS do mapa e GeoJSON sem alteração. O Terra rotulado como Aqua virou o modelo do Aqua. Conferido no navegador local. A equipe revisa no PR |
| `RISK_MAX_AGE_DAYS` na tabela de variáveis do `backend/README.md` e status de RNF03, RNF09 e B9 (`docs/requisitos.md`, `docs/tarefas.md`, `docs/deploy.md`, `infra/.env.example`) | Claude Code (Claude Opus 5.5) | Texto escrito a partir dos logs do `job-nrt` e do `job-risco` e do `docker stats` da VPS em 15/11, colados pela equipe. A equipe revisa no PR |
| Abertura com o globo em `frontend/` (`src/hero/OrbitalOpening.tsx`, `OrbitalScene.tsx`, `globeTransition.ts`, `openingCopy.ts`, `assets/`, testes) e indicadores em destaque do RD06 (`src/summary/indicatorsModel.ts`, `IndicatorRow.tsx`, teste) | Claude Code (Claude Opus 5.5) | Porte da abertura de `lovable/` para o front oficial (Vite + React), com a descida terminando no mapa do explorador (mesmo enquadramento e mesma camada do GIBS), correção da emenda pontilhada da textura, tema claro pelas variáveis do `styles.css` e fileira de indicadores com os campos `indicators` da API. Teste antes do código; conferido no navegador no desktop e no celular. A equipe revisa no PR |
| Luz dos satélites da abertura (`frontend/src/hero/globeTransition.ts`, `OrbitalScene.tsx`, teste) | Claude Code (Claude Opus 5.5) | Diagnóstico dos modelos da NASA desbotados para branco (luz ambiente 2.2 + sol 3 iluminava a textura a 1,65×) e redução para 0.8 + 2.3. Teste que reproduz o bug antes da correção; conferido em Chromium com GPU, antes e depois. A equipe revisa no PR |
| CSP das texturas dos satélites (`frontend/public/_headers`, teste `frontend/src/security-headers.test.ts`) | Claude Code (Claude Opus 5.5) | Diagnóstico dos satélites ainda brancos no site no ar: o CSP sem `blob:` no `connect-src` bloqueava as texturas do GLTFLoader. Teste que reproduz o bug antes da correção; conferido no build de produção servido com o CSP do `_headers`. A equipe revisa no PR |
| Responsividade do front (`src/ui/useMediaQuery.ts`, `openingLayout` em `src/hero/globeTransition.ts`, geometrias estreitas em `src/calendar/CalendarSvg.tsx`, `src/history/SeasonalChart.tsx`, `YearRanking.tsx`, `styles.css`, link da curva no `index.html`, `e2e/responsivo.spec.ts`) | Claude Code (Claude Opus 5.5) | Teste no navegador a 375 px e 768 px, testes Playwright que reproduzem cada problema antes da correção, e as correções: abertura sem o globo sobre o texto no tablet, gráficos legíveis no celular, botões de 44 px na tela de toque. Conferido com capturas do Playwright. A equipe revisa no PR |
| Modo simples do explorador (`frontend/src/summary/verdictModel.ts`, `Verdict.tsx`, "More options" em `src/controls/SelectionPanel.tsx`, estilos, testes, jornadas J3 e J4, `docs/ux-telas.md`) | Claude Code (Claude Opus 5.5) | Veredito em uma frase e controles avançados recolhidos, a pedido do Mateus ("simples até para uma criança"). Usa a mesma régua P25–P75 do cartão dos 7 dias, sem número novo. Teste antes do código; conferido no navegador no desktop e no celular. A equipe revisa no PR |
| Unificação do calendário animado (`frontend/src/history/HistoryPanel.tsx`, `src/hero/heroIntro.ts`, `src/App.tsx`, `index.html`, testes) | Antigravity | A animação da faixa cronológica MODIS → VIIRS se dobrando no calendário passa para o calendário principal do explorador e remove a segunda grade repetida logo abaixo. A equipe revisa no PR |
| Assistente virtual: `backend/src/application/assistant.py`, `assistant_tools.py`, `backend/src/ports/llm.py`, `backend/src/adapters/outbound/llm/openai.py`, rota `/ask` no `app.py`, bucket `ask` no `limits.py`, `frontend/src/assistant/`, `askAssistant` no cliente, testes `test_assistant.py`, `test_ask_route.py` e `AssistantBubble.test.tsx` | Claude Code (Claude Opus 5.5) | Implementação do RFC 0004 com TDD: ferramentas sobre os casos de uso existentes, validação do `messages[]`, cadeia de provedores, teto diário e bolinha atrás de `VITE_ENABLE_ASSISTANT`. Depois da auditoria: fontes e checagem dos números na resposta, prazo total por pergunta, leitura curta no banco por ferramenta e foco preso no painel. Testado com Cerebras, Groq, Gemini e OpenRouter no banco local |
| Toque no mapa no celular (`frontend/src/map/MapStage.tsx`, `MapStage.test.tsx`, `src/hero/OrbitalScene.tsx`, `src/styles.css`, `e2e/responsivo.spec.ts`) | Antigravity | Rolagem da página com 1 dedo sobre o mapa (com aviso temporário `"Use two fingers to move the map."`), arrasto e zoom do mapa com 2 dedos via `L.Handler.TouchZoom`, desenho de retângulo com 1 dedo quando o modo de desenho está ativo e preservação de `touch-action: pan-y` no canvas 3D da abertura. A equipe revisa no PR |
| Tela do mapa em `lovable/` com o layout do Figma (`src/components/firesync/RecentWorkspace.tsx`, `AreaMap.tsx`, `OrbitalScene.tsx`, `src/lib/recent-data.ts`, `src/routes/index.tsx`, `styles.css`, `src/test/color-scale.test.ts`) | Claude Code (Claude Opus 5.5 e Claude Sonnet 5.5) | Abas Fire now e Risk, next 14 days, filtros, status, painel Indicators agrupado por faixa de risco, legenda, círculos de alerta, zoom suave pela roda e globo pausado atrás do mapa, a partir das telas do Figma desenhadas pela equipe. Teste das faixas de cor; conferido no navegador. A equipe revisa no PR |

## Dados e créditos

- Focos de calor: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS C6.1 e VIIRS C2)
- Polígonos de biomas: IBGE, Biomas do Brasil 1:250.000
- Série de validação: INPE, Programa Queimadas
- Textura da Terra na abertura (`frontend/src/hero/` e `lovable/`): [NASA GIBS](https://www.earthdata.nasa.gov/gibs), camada `BlueMarble_ShadedRelief_Bathymetry`
- Modelos 3D do Aqua e do Suomi NPP: [NASA 3D Resources](https://github.com/nasa/NASA-3D-Resources)
- Limites de países: [datasets/geo-countries](https://github.com/datasets/geo-countries) (Natural Earth)
