# Tarefas

Divisão do trabalho entre as 4 pessoas da equipe, até a submissão (domingo, 15/11/2026, 23h59).

## Como usar

- Cada pessoa tem uma frente e mexe **só nas pastas da sua frente**. Para mexer em outra pasta, fale antes com o responsável dela.
- As frentes dependem de **contratos** (formato da tabela `agregados` e `docs/api.md`), nunca do código de outra frente. Até a parte real ficar pronta, trabalhe com dados falsos no formato do contrato.
- Cada tarefa vai numa branch própria, criada a partir da `main` atualizada, e entra na `main` por PR assim que algo funcionar (regras de Git no [CLAUDE.md](../CLAUDE.md)).
- Mudar um contrato exige avisar a equipe antes. Depois, atualize o documento do contrato no mesmo commit.
- Ao começar uma tarefa, mude o status para `fazendo`. Ao terminar, mude para `feito`. Status possíveis: `a fazer`, `fazendo`, `feito`, `bloqueado`, `cortado`.
- Agentes: leia a sua frente inteira e os documentos indicados nela antes de começar.

## Frentes

| Frente | Responsável | Pastas |
| --- | --- | --- |
| A. Importador e dados | Eduardo | `data-pipeline/` (importação) |
| B. Harmonização | Weberson | `data-pipeline/` (calibração e agregação, em módulo separado do importador), `config/` (regras do alerta) |
| C. API, deploy e submissão | Rafael | `backend/`, `infra/` (deploy), `docs/api.md` |
| D. Frontend e demo | Mateus | `frontend/` |

A e B dividem `data-pipeline/`. Antes de começar, combinem a estrutura de subpastas para não editarem os mesmos arquivos.

## Marcos

| Marco | Quando | O que precisa estar pronto |
| --- | --- | --- |
| M0. Contratos | Sábado, antes de dividir | Stack decidida, formato de `agregados`, `docs/api.md` com JSON de exemplo |
| M1. Partes isoladas | Sábado, fim do dia | Importador com os dados de 2024, fatores calculados, API respondendo com dados falsos, front mostrando o calendário com o JSON de exemplo |
| M2. Integração | Domingo, 12h | Front → API → `agregados` reais, rodando local de ponta a ponta. Atingido: conferido com a carga real em 15/11, no site no ar (D7) |
| M3. No ar | Domingo, 18h | App público, sem login, interface em inglês |
| M4. Submissão | Domingo, 22h | Página e demo enviadas. Fica uma folga até 23h59 para reenvio |

## M0. Contratos (todos juntos)

| ID | Tarefa | Status | Pronto quando |
| --- | --- | --- | --- |
| T00 | Decidir os pontos 1, 2, 4, 5 e 12 de [arquitetura.md](arquitetura.md) e escrever as justificativas | feito | Os 5 pontos preenchidos |
| T01 | Fechar o formato de `agregados` (colunas, tipos, resolução H3) | feito ([banco.md](banco.md), PR #2) | Seção escrita em [importacao-regioes.md](importacao-regioes.md) |
| T02 | Escrever `docs/api.md` com endpoints, pedido, resposta, erros e um JSON de exemplo | fazendo (na `main`, falta A e D confirmarem) | A e D leram e concordaram |
| T03 | Preencher responsáveis desta página | feito | Tabela de frentes preenchida |

## A. Importador e dados

Ler antes: [firms-extracao-dados.md](firms-extracao-dados.md), [plano-extracao-amazonia.md](plano-extracao-amazonia.md), [importacao-regioes.md](importacao-regioes.md).

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| A1 | Conferir o pedido do FIRMS. Se o histórico não chegar a tempo, baixar os resumos anuais por país (Brasil, 2003 até hoje), que não passam por aprovação | — | feito (resumos anuais 2000–2025 + API para 2026, ver [pipeline-dados.md](pipeline-dados.md)) | Histórico em mãos, ou decisão registrada de demo só com 2024 |
| A2 | Baixar o shapefile de biomas do IBGE e a série mensal do bioma Amazônia do INPE | — | feito (IBGE em `cadastrar`; INPE em `pipeline.py inpe` -> `referencia/inpe_mensal_biomas.csv`, conferido: correlação 0,998 com o nosso Aqua) | Arquivos em `data-pipeline/data/`, fora do git se forem grandes |
| A3 | Criar `.gitignore` para CSVs descompactados e arquivos gerados | — | feito | `git status` limpo depois de descompactar os ZIPs |
| A4 | Criar o banco com as tabelas `focos`, `regioes` e `cobertura` | T00 | feito (`data-pipeline/migrations/` 001 a 003) | Script de criação versionado |
| A5 | Importador: normalizar colunas, calcular H3, upsert com a chave única, atualizar `cobertura` | A4 | feito (`pipeline.py importar`; 2024 bate com o plano, diferença < 0,2% = fora dos biomas) | `importar` carrega os 5 arquivos de 2024 e as contagens batem com a tabela do plano de extração |
| A6 | Cadastrar as regiões Amazônia e Pantanal em `regioes`, com as células em `celula_regiao` | A2, A4 | feito (os 6 biomas, `pipeline.py cadastrar`) | As duas regiões com polígono e células |
| A7 | Carregar o histórico completo | A1, A5 | feito no banco de teste (46,4 mi de focos, ver `pipeline-dados.md`) | `cobertura` mostra cada satélite no período esperado |
| A8 | Backtest do alerta (solução A + B da issue #9, RFC 0001): `validacao/backtest_alerta.py` e `referencia/eventos_conhecidos.csv` | A7, `agregados_diarios` | feito no banco de teste; a `v1` (piso contínuo) foi aprovada e seus números estão na tela de Método (#65) | `backtest.csv`, `por_bioma.csv` e `eventos.csv` gerados; autoteste sem banco passa |
| A9 | Logs estruturados (JSON) nos pontos de decisão do pipeline e do job NRT (RNF07) | A5 | feito (`data-pipeline/logs.py`, branch `logs-estruturados`, ver [pipeline-dados.md](pipeline-dados.md)) | Cada rodada do job registra `run_id`, focos que entraram, duração e a etapa do erro |

## B. Harmonização

Ler antes: [importacao-regioes.md](importacao-regioes.md) (seção "Harmonização por região"), [plano-extracao-amazonia.md](plano-extracao-amazonia.md).

B1 e B2 podem começar direto nos CSVs de 2024, sem esperar o importador.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| B1 | Protótipo do cálculo do fator Aqua → S-NPP (escala VIIRS) **por bioma, mês e dia/noite**, em contagens por célula H3, só confiança nominal ou alta e `type = 0`. Primeiro nos CSVs de 2024, depois nos anos de sobreposição disponíveis. Ver [decisoes-harmonizacao.md](decisoes-harmonizacao.md) | — | feito (protótipo nos CSVs de 2024: Amazônia com razão anual 6,23, dia 2,4 a 4,5, noite 12 a 25. Cumprido o papel, o código saiu no PR #26 e ficou no histórico do git, commit `6ca3ac9`; os números que vão para a tela de Método saem do `calibrar.py`, com o histórico completo) | Fatores da Amazônia calculados, com razão média perto de 6 e variação mensal visível |
| B2 | Definir a escolha do satélite por mês (Aqua, S-NPP, NOAA-20), como aplicar a cadeia de fatores e como rotular cada mês como observado ou estimado | — | feito (tabela de períodos e origem pela data em `importacao-regioes.md`) | Regra escrita em [importacao-regioes.md](importacao-regioes.md) |
| B3 | Job de calibração gravando em `fatores_harmonizacao`, com um cenário por ano de calibração (base 2012 a 2024; o próprio job roda a validação deixando um ano de fora e aplica o critério de 1,5× para escolher os anos) e só confiança nominal e alta | A5, B1 | feito no banco de teste (`data-pipeline/harmonizacao/calibrar.py`; 13 anos, 1.860 fatores gravados, cobertura da faixa P5 a P95 de 0,68 a 0,80 por bioma; ver [decisoes-harmonizacao.md](decisoes-harmonizacao.md)) | Fatores dos 6 biomas no banco |
| B4 | Job de agregação gravando a contagem bruta em `agregados` (célula × ano × mês × satélite × dia/noite), só do satélite que vale em cada mês e só com confiança nominal e alta, no formato do `banco.md` (PR #2) | T01, B3 | feito pela frente A (`data-pipeline/agregar.py`, PR #2) | `agregados` preenchida para as duas regiões |
| B5 | Comando `recalcular <regiao>` (fatores + agregados da região) | B3, B4 | a fazer | Rodar duas vezes dá o mesmo resultado |
| B6 | Validar a série harmonizada contra a do INPE (só forma da curva, anos altos, meses de pico) e registrar o resultado da validação do B3 (erro por ano, decisão dos anos e cobertura da faixa) | A2, A7, B4 | feito (validação da B3 e comparação com o INPE registradas em [decisoes-harmonizacao.md](decisoes-harmonizacao.md), com a rodada final da issue #40; `data-pipeline/harmonizacao/validar_inpe.py` entra pelo PR #26; gráficos disponíveis em `docs/img/b6/`, já incorporados à `main`) | Gráficos de comparação salvos, para usar na página do projeto |
| B7 | Modelo A pelo caminho C: curva de detecção e prova cruzada do fator ([rfcs/0002-modelo-a.md](rfcs/0002-modelo-a.md)). Etapa A com os dados de 2024; etapa B com os arquivos anuais públicos de 2019 a 2024 | B6 | feito, as duas etapas (`data-pipeline/harmonizacao/modelo_a.py`; resultado em [decisoes-harmonizacao.md](decisoes-harmonizacao.md), seção 5): o modelo treinado em 2019 a 2021 vale em 2022 a 2024 | Curva de detecção para a tela de Método |
| B8 | Experimento: modelo de risco treinado contra a regra `v1` do alerta, com pistas de fogo, ONI e clima do NASA POWER e validação em avanço ([rfcs/0003-modelo-risco.md](rfcs/0003-modelo-risco.md)) | A8 | feito: ganho de +0,9 ponto sobre a `v1` (2017 a 2023), clima e ONI não ajudaram. Não entra no produto (`data-pipeline/validacao/modelo_risco.py`) | Frase para a tela de Método explicando por que ficamos com a regra simples |
| B9 | Risco por célula com o modelo treinado: "onde vai ter fogo nos próximos 14 dias" ([rfcs/0003-modelo-risco.md](rfcs/0003-modelo-risco.md)): job `data-pipeline/risco_celulas.py`, tabela `risco_celulas` (migration 005) e faixas em `config/risk_rules.json` | B8, A7 | job, tabela e testes feitos; rodado com dados reais de 2 datas; comparado com o índice oficial de Risco de Fogo do INPE (2024), que serve como validação externa e não entra no modelo. O job roda no serviço `job-risco` do compose (testado na imagem com um banco descartável). Falta o código da API que lê a tabela (issue #90) e a primeira rodada com o banco real na VPS | Faixas de risco no mapa (vermelho, laranja e amarelo), com a taxa de cada faixa, e a frase da comparação com o INPE para a tela de Método |

## C. API, deploy e submissão

Ler antes: [requisitos.md](requisitos.md), [importacao-regioes.md](importacao-regioes.md), `docs/api.md`.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| C1 | Esqueleto da API respondendo o JSON de exemplo do `api.md` | T00, T02 | feito (cinco rotas FastAPI, erros do contrato, CORS, cache/ETag e rate limit em TDD) | D consegue apontar o front para ela |
| C2 | Gerar `agregados` falsos no formato do contrato, para testar sem esperar B | T01 | feito (`backend/scripts/demo_data.py`, carga sintética pequena e reproduzível para PostgreSQL descartável) | Script versionado |
| C3 | Converter a área (polígono, retângulo ou lat/lon) em células H3 e somar os `agregados` | C1 | feito (H3, PostgreSQL e HTTP testados em integração; conferência com a carga real no roteiro M2 do Eduardo) | Calendário meses × anos correto para uma área de teste |
| C4 | Sazonalidade, ranking de anos, mediana do mês atual e anomalias (RF09–RF12) | C3 | feito (paridade API/backtest desde a série diária testada na #64; indicador anual por mediana com cenários preservados e contrato `reference_median` na #78; histórico e janelas recentes de ±15 dias, P25–P75, intensidade e alerta com piso contínuo da issue #59 testados no domínio e por HTTP) | Valores conferidos à mão para uma área |
| C5 | Resposta "sem dados" fora da `cobertura` e marcação dos dias de `dias_sem_dados` | C3 | feito (cobertura full/partial/none e dias sem dados expostos e testados por HTTP) | Área fora do Brasil devolve o aviso, não um calendário vazio |
| C6 | Export CSV dos focos da busca (RD05) | C3 | feito (ZIP em memória com CSVs e metadados; caso de 500.001 focos testado no PostGIS) | Arquivo abre no Excel |
| C7 | Deploy público de banco, API e front | T00, M2 | feito em 15/11/2026 (front em <https://firesync.nogranlabs.com.br>, API em <https://firesync-api.nogranlabs.com.br>; carga do dump conferida com os números da frente A, na issue #98; ver [deploy.md](deploy.md)) | Link funciona numa janela anônima |
| C8 | Pedir a classificação FortiGuard do site | C7 | feito (15/11: site e API já classificados como Business, herdado do domínio `nogranlabs.com.br` desde 13/06/2026; pedida a reclassificação dos dois para Information Technology) | Pedido enviado |
| C9 | Página do projeto em inglês: summary, descrição detalhada, NASA Data, referências, uso de IA | B6 | a fazer | Todos os campos do checklist de [requisitos.md](requisitos.md) preenchidos |
| C10 | Completar a tabela "Uso de IA" do README | — | a fazer | Cada parte com IA registrada |

## D. Frontend e demo

Ler antes: [requisitos.md](requisitos.md), `docs/api.md`.

D1 a D5 começam com o JSON de exemplo do `api.md`, sem esperar a API.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| D1 | Esqueleto do app, interface em inglês e crédito ao FIRMS visível | T00 | feito (Vite + React + TS em `frontend/`; texto fixo, Method e Data & credits no `index.html`, abre sem JS) | App abre local |
| D2 | Mapa com desenho de polígono e retângulo (RD01) e entrada de lat/lon (RD02) | D1 | feito (`frontend/src/controls/`: Leaflet `preferCanvas` + Leaflet-Geoman em carga tardia, basemaps do NASA GIBS (VIIRS Black Marble e Blue Marble, sem `Reference_Labels_15m`), desenho de retângulo e polígono em GeoJSON, camada de focos recentes `GET /api/v1/detections/recent` em hexágonos `cividis` log e pontos por classe de intensidade `low`/`medium`/`high`, campos de latitude/longitude/raio de 1 a 200 km, select de região via `GET /regions` e cliente `src/api/client.ts` com fallback em `api-exemplo.json`) | Área desenhada vira o pedido do `api.md` |
| D3 | Seletor de intervalo de datas (RF07) | D1 | feito (`frontend/src/controls/`: início e fim em `YYYY-MM` em UTC de `2003-01` até `meta.last_month` de `GET /health`, validação de intervalo equivalente a `invalid_period`, estados de cobertura `none`, `429` com `Retry-After`, erro do contrato e aviso de dado velho) | Datas entram no pedido |
| D4 | Calendário meses × anos em heatmap com paleta acessível (RF08, RD03, RD04) e meses com falha de satélite (`dias_sem_dados`) diferentes de zero | D1 | feito (`frontend/src/calendar/`: D3 + SVG, cividis log, hachura no estimado, borda no incompleto, estados próprios para zero e sem dados, linha da troca de sensor, tooltip e teclado; renderiza o `api-exemplo.json`) | Renderiza o JSON de exemplo |
| D5 | Indicadores principais, sazonalidade, ranking de anos, mês atual vs. mediana e anomalia (RF09–RF12, RD06) | D1 | feito (`frontend/src/summary/`: indicadores, cartões "last 7 days" e "month to date" com a janela atual desenhada sobre a faixa P25–P75, sazonalidade com mediana e mínimo–máximo, ranking com faixa nos anos estimados, 2012 `mixed` e anos incompletos sem posição; renderiza o `api-exemplo.json`) | Renderiza o JSON de exemplo |
| D6 | Download das análises e do CSV (RF13, RD05) | D4, D5 | feito (`frontend/src/export/`: pacote de auditoria `POST /api/v1/export` com preservação do `Content-Disposition` e fallback UTC `firesync-YYYY-MM-DD.zip`, erros `429` e do contrato em `role="alert"`, exportação local de `result.csv`, `years.csv`, `seasonality.csv` e PNG do calendário serializado do SVG para canvas com crédito ao NASA FIRMS; jornada J7 passando) | Arquivos baixam e abrem |
| D7 | Ligar o front na API real | C3, D2–D5 | feito (com a carga real, conferido em 15/11 no site no ar: `health`, `regions`, `calendar`, `detections/recent` em 24 h e 7 dias e `export`, sem erro de CORS, no desktop e no celular) | M2 atingido |
| D9 | Nova interface: abertura em que a faixa de meses MODIS → VIIRS se dobra no calendário (GSAP), área de análise com mapa, resumo "is recent activity typical?" e calendário juntos, descoberta guiada do exemplo e tela de Método com o diagrama da harmonização | D1–D7 | feito (`frontend/src/hero/`, `calendar/CalendarSvg.tsx`, `map/`, `summary/`, `history/`, `discovery/`, `state/`; 113 testes de unidade e as 9 jornadas no desktop e no celular passando) | A equipe aprova o visual no PR |
| D10 | Aviso antecipado no mapa (RFC 0003): lista "Where to look first" na ordem de `alerts.priority`, selo "Unusual for the season", faixa de risco no tooltip e na lista, legenda do risco dos 14 dias com os limites | D7; API dos PRs #86 e #97 | feito (`frontend/src/map/alertsModel.ts` e `EarlyWarning.tsx`; campos novos opcionais; jornadas J10 com `alerts` e J11 sem, no desktop e no celular). Conferido em 15/11 no site no ar, com a API real: lista de 10 com "Show all", selo, faixa, legenda com notas de 15/11 14:54 UTC, e o clique leva o mapa ao `center` da célula. As cores do mapa não mudaram (decisão 3 do [ux-telas.md](ux-telas.md)) | Lista e legenda aparecem com a API no ar |
| D8 | Demo: vídeo de até 30 s com legenda em inglês, ou até 7 slides em inglês, com nome da equipe, membros, desafio, imagem do projeto, experiência do usuário e uso dos dados da NASA | D7 | a fazer | Link público testado numa janela anônima |

## Cortado ou depois da submissão

| ID | Tarefa | Motivo |
| --- | --- | --- |
| X1 | Job de atualização NRT pela API do FIRMS | Voltou pela issue #5 e foi feito: `data-pipeline/job_nrt.py` + `Dockerfile` (a cada 3 h) |
| X2 | Recarga SP mensal | Depende do X1 |
| X3 | Região da Califórnia | Precisa de pedido novo no FIRMS |
