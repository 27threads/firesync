# Requisitos — Calendário Harmonizado de Focos de Calor (MODIS + VIIRS)

Nov 13, 2026 · @Mateus Nogueira

Este documento separa o que o desafio **exige** (está nos Objetivos) do que ele só **sugere** (aparece como "pode considerar"). Assim fica claro o mínimo para entregar e o que dá pontos extras.

**Situação em 14/11/2026:** ✅ feito e verificado · ⏳ falta ou é parcial (a nota diz onde está). A frente A (dados e banco) está pronta; no front, D1–D7 já cobrem área e período, camada de focos recentes no mapa, calendário, indicadores, janela recente, sazonalidade, ranking, downloads e integração/proxy com a API; na API, o serviço histórico já está implementado e faltam as rotas HTTP ([api.md](api.md)).

## 1. Requisitos obrigatórios

### Parte A: Harmonização dos dados (backend / pipeline)

- [x] **RF01:** Buscar os focos de calor do **MODIS** (Terra e Aqua). É a série histórica, do início dos anos 2000 em diante. ✅ MODIS Terra (desde 01/11/2000) e Aqua (desde 04/07/2002) até hoje, Brasil inteiro, na tabela `focos` ([pipeline-dados.md](pipeline-dados.md)).
- [x] **RF02:** Buscar os focos de calor do **VIIRS**. É o sensor que continua a série, com mais detalhe. ✅ VIIRS S-NPP (2012 até 02/11/2026), NOAA-20 e NOAA-21, na tabela `focos`.
- [ ] **RF03:** Harmonizar as duas fontes numa **série temporal única e consistente**. Depois dessa etapa, "o sensor de origem não importa mais". O processo precisa compensar as diferenças entre os dois sensores: ⏳ **parcial:** método decidido ([decisoes-harmonizacao.md](decisoes-harmonizacao.md)), contagem bruta por satélite em `agregados` e 1.860 fatores Aqua → S-NPP gravados (13 cenários, cobertura P5–P95 medida). Falta a API aplicar os fatores.
  - resolução espacial (VIIRS \~375 m, MODIS \~1 km)
  - sensibilidade de detecção (o VIIRS detecta mais focos pequenos)
  - horário em que cada satélite passa
- [ ] **RF04:** Cobrir o período **do início dos anos 2000 até hoje**, com dados atualizados. ⏳ **parcial:** histórico de 2003 até hoje no banco de teste e job NRT a cada 3 h pronto (`job_nrt.py`). Falta rodar na VPS.
- [x] **RF05:** Entregar os dados harmonizados como **entrada da aplicação web**. ✅ `agregados`, `agregados_diarios`, `fatores_harmonizacao`, `dias_sem_dados`, `cobertura` e `config` no formato do [api.md](api.md) ([banco.md](banco.md)).

### Parte B: Aplicação web (frontend + API)

- [ ] **RF06:** Deixar o usuário **escolher uma região / área de interesse**. ⏳ **parcial:** contrato no [api.md](api.md) (região, GeoJSON, lat/lon) e **front pronto** em `frontend/src/controls/` (com fallback demo); falta a API.
- [ ] **RF07:** Deixar o usuário **escolher um intervalo de datas**. ⏳ **parcial:** contrato no [api.md](api.md) e **front pronto** em `frontend/src/controls/` (`2003-01` a `last_month`, UTC); falta a API.
- [ ] **RF08:** Mostrar um **calendário de atividade de queimadas** com o **número de focos de calor** da área escolhida, no formato meses × anos. ⏳ contrato no [api.md](api.md) e dados prontos (`agregados`); falta a API e o front.
- [ ] **RF09:** Mostrar **quais meses do ano têm mais fogo** (o padrão sazonal). ⏳ contrato no [api.md](api.md); falta a API e o front.
- [ ] **RF10:** Mostrar **quais anos tiveram mais fogo**. ⏳ contrato no [api.md](api.md); falta a API e o front.
- [ ] **RF11:** Comparar o **mês atual com a mediana histórica** da área. ⏳ contrato no [api.md](api.md) (janela recente); dados prontos (`agregados_diarios`, normal de ±15 dias em 7–40 ms); falta a API e o front.
- [ ] **RF12:** Mostrar **como a atividade atual se compara a períodos anteriores**, ou seja, as anomalias. ⏳ contrato no [api.md](api.md); falta a API e o front.
- [ ] **RF13:** Permitir **baixar as análises e visualizações** da busca. ⏳ **parcial:** contrato do pacote de auditoria no [api.md](api.md) (`POST /export`) e **front pronto** em `frontend/src/export/` (pacote de auditoria ZIP via `POST /api/v1/export`, CSV local `result.csv` / `years.csv` / `seasonality.csv` e PNG do calendário gerado no front a partir do SVG; jornada J7 passando); falta a API.

## 2. Requisitos desejáveis (diferenciais)

- [ ] **RD01:** **Mapa interativo** em que o usuário desenha a área de interesse (polígono ou retângulo). ⏳ **parcial:** **front pronto** em `frontend/src/controls/` (Leaflet `preferCanvas` + Leaflet-Geoman; desenho vira GeoJSON Polygon e passa na jornada J2); falta expor a rota HTTP na API.
- [ ] **RD02:** Opção de **digitar latitude e longitude**, como alternativa ao desenho no mapa. ⏳ **parcial:** contrato no [api.md](api.md) (`point` com raio) e **front pronto** em `frontend/src/controls/` (campos lat/lon/raio de 1 a 200 km); falta expor a rota HTTP na API.
- [x] **RD03:** **Rampa de cores** no calendário, para mostrar as diferenças entre meses como um heatmap. ✅ escala logarítmica no calendário e nos hexágonos do mapa (`frontend/src/calendar/colorScale.ts`).
- [x] **RD04:** Cores **acessíveis**, legíveis para quem tem daltonismo (por exemplo, viridis ou cividis). ✅ paleta `cividis` em escala logarítmica no calendário e nos hexágonos H3, hachura/borda nos meses estimados e incompletos, e diferenciação por raio e espessura/estilo de borda além da cor nos pontos de intensidade (`low`, `medium`, `high`) no mapa.
- [ ] **RD05:** **Exportar um CSV** com os focos de calor encontrados na busca. ⏳ **parcial:** `detections.csv` no pacote de auditoria (`POST /api/v1/export`, até 500.000 focos) e **front pronto** em `frontend/src/export/` (chamada ao ZIP de auditoria, exportação local da série visível em CSV e aviso sobre o limite de 500.000 focos); `focos` vai para produção; falta a API.
- [ ] **RD06:** **Indicadores principais** em destaque: ⏳ **parcial:** contrato no [api.md](api.md) (`indicators`) e **front pronto** em `frontend/src/summary/KeyIndicators.tsx`; falta expor a rota HTTP na API.
  - número total de focos detectados e registrados
  - anomalia em relação à média de vários anos
- [ ] **RD07:** Interface pensada para o **público-alvo**: equipes de alerta precoce, resposta a emergências, cientistas, gestores de terras e bombeiros. Precisa ser rápida de ler e de usar. ⏳ **parcial:** janela recente (`RecentPanel.tsx`) e camada de focos recentes no mapa (`GET /api/v1/detections/recent` em `AreaMap.tsx`, com janelas de `24 h`, `72 h` e `7 days`, hexágonos em `cividis` log e pontos por classe de intensidade `low`/`medium`/`high` sem exibir FRP em MW) prontas no front; dados e índice prontos no banco (19 ms); falta expor a rota HTTP na API.

## 3. Requisitos não funcionais (implícitos no texto)

- [ ] **RNF01:** Ser uma **aplicação web**, acessada pelo navegador. ⏳ **parcial:** front completo (`frontend/`) com proxy para a API (`vite.config.ts`); falta expor as rotas HTTP da API e fazer o deploy público.
- [x] **RNF02:** **Fonte de dados:** o texto sugere o **NASA FIRMS** (Earthdata), que fornece os dados do MODIS e do VIIRS. ✅ NASA FIRMS: resumos anuais por país (SP) e API (SP e NRT).
- [ ] **RNF03:** **Atualização contínua.** O calendário precisa estar "atualizado", então os dados novos devem entrar periodicamente. ⏳ **parcial:** job NRT a cada 3 h pronto e testado (`job_nrt.py` + `Dockerfile`); falta rodar na VPS.
- [x] **RNF04:** **Desempenho.** São mais de 20 anos de focos no mundo inteiro, então as consultas por área e período precisam ser rápidas. Isso pede pré-agregação e indexação espacial. ✅ pré-agregação (`agregados`, `agregados_diarios`) e índice espacial H3: calendário de 100 × 100 km em 2–9 ms, Amazônia inteira em ~0,8 s, focos recentes em 19 ms (medido no banco de teste).
- [x] **RNF05:** **Usabilidade e acessibilidade**, porque o usuário pode estar numa situação de emergência. ✅ controles de área/período e camada de focos recentes com labels, `aria-pressed`, `aria-describedby`, alertas em `role="alert"`, calendário em `cividis` com hachura/borda, pontos diferenciados por raio e borda além da cor, navegação por teclado e downloads acessíveis no front (D1–D7, validado nas 18 jornadas E2E J1–J9 em desktop e celular).

### Definidos pela equipe

Não vêm do texto do desafio. São necessários porque o sistema é público e precisa estar sempre atualizado para o público de emergência (RD07).

- [ ] **RNF06:** **Limite de requisições na API.** A API é pública, e uma área grande (até 250 mil células) custa caro. Sem limite, uma pessoa ou um robô consegue derrubar o servidor. ⏳ contrato no [api.md](api.md) (`429 rate_limited`); falta a API.
  - Limite por IP, com valores em configuração. Proposta inicial: 60 pedidos por minuto no geral, 10 por minuto em `POST /calendar` e 2 por minuto em `POST /export`.
  - Acima do limite: HTTP `429` com o código `rate_limited` e o cabeçalho `Retry-After`.
  - Um segundo limite no servidor web (ver `infra/`), antes de o pedido chegar à API.
- [ ] **RNF07:** **Monitoramento.** ⏳ **parcial:** `config.atualizado_em` gravado pelo job e logs de cada rodada; falta o aviso de dado velho e os logs da API.
  - **Dado velho:** se o `updated_at` passar de **6 horas** (duas rodadas do job NRT perdidas), a equipe recebe um aviso, e a tela mostra ao usuário que os dados podem estar desatualizados. Para o público de emergência, mostrar dado velho como se fosse atual é pior do que avisar.
  - **Logs da API:** cada pedido registra o endpoint, o tempo de resposta, o número de células da área e o status HTTP.
  - **Logs do job NRT:** cada rodada registra quantos focos entraram, quanto tempo levou e os erros.
  - O canal do aviso (e-mail, Discord, Telegram) é decidido no deploy.
- [x] **RNF08:** **Testes automáticos (CI).** Todo PR com código roda os testes sozinho, pelo GitHub Actions, e só entra na `main` se passar. Detalhes em [arquitetura.md](arquitetura.md), seção "Qualidade e testes". ✅ esteira no GitHub Actions (pipeline, integração com PostGIS, contrato da API, jornadas E2E); `main` protegida.

## 4. Decisões que o texto deixa em aberto

O enunciado não diz como fazer estes pontos, e eles vão definir a arquitetura:

1. **Método de harmonização.** Por exemplo: agregar os focos numa grade comum (como 0,25° ou 1 km) e calcular um fator de calibração no período em que os dois sensores funcionaram juntos (2012 em diante). Outra opção é filtrar por confiança ou potência radiativa (FRP). ✅ **Decidido: escala VIIRS, fator Aqua → S-NPP por bioma × mês × dia/noite em células H3, um cenário por ano de 2012 a 2024, faixa P5–P95 ([decisoes-harmonizacao.md](decisoes-harmonizacao.md)).**
2. **Granularidade do calendário:** contagem mensal ou diária. ✅ **Decidido: mensal no calendário; diária só para a janela recente e o alerta (`agregados_diarios`).**
3. **Escopo geográfico:** o mundo todo ou só o Brasil num primeiro momento (muda muito o volume de dados). ✅ **Decidido: Brasil inteiro, calibrado nos 6 biomas do IBGE.**
4. **Dados pré-processados ou consulta à API do FIRMS na hora.** A API do FIRMS tem limites, então pré-processar é mais seguro. ✅ **Decidido: pré-processados no banco, atualizados pelo job NRT a cada 3 h.**
5. **Formato do download** pedido no RF13: PNG, PDF ou CSV. ✅ **Decidido: ZIP de auditoria com CSVs (`POST /export`); o PNG do calendário é gerado no front ([api.md](api.md)).**

## 5. Entregáveis da submissão (Space Apps 2026)

A submissão fecha no domingo, 15/11, às 23h59 no horário do evento local. Dá para reenviar até lá, e vale a última versão. [Guia de submissão](https://www.spaceappschallenge.org/resources/project-submission-guide/) · [Página do desafio](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/)

### Página do projeto (tudo em inglês)

- [ ] Project Name
- [ ] High-Level Project Summary: o que foi feito, como resolve o desafio, por que importa
- [ ] Link to Project Demo (público, sem login)
- [ ] Link to Final Project: app no ar e/ou repositório (público, sem login)
- [ ] Detailed Project Description: o que faz, como funciona, benefícios, ferramentas e linguagens
- [ ] NASA Data: FIRMS (MODIS e VIIRS) e o que mais usarmos (GIBS, POWER). Mínimo de um recurso da NASA para concorrer ao prêmio global
- [ ] Space Agency Partner Data and Other References: todas as fontes, bibliotecas e imagens. Considerar dados de parceiras (INPE/AEB, CONAE)
- [ ] Use of Super Intelligence: declarar onde e como IA foi usada
- [ ] Marcar "Terms and Conditions" e "Confirm All Work is Original" e clicar em "Submit for Judging"

### Demo

- [ ] Escolher o formato: vídeo de até 30 s ou até 7 slides (contando título e introdução). Passar do limite tira o projeto do julgamento global
- [ ] Vídeo com legenda em inglês (a fala pode ser em português) ou slides em inglês
- [ ] Conteúdo obrigatório: nome da equipe, nomes dos membros, desafio escolhido, imagem do projeto, experiência do usuário e como os dados abertos da NASA tornaram o projeto possível
- [ ] Hospedar fora do site (YouTube, Drive, GitHub) e testar o link numa janela anônima
- [ ] Sem imagem, vídeo ou voz de menores de 18 anos
- [ ] Definir um responsável pela demo e pela página

### Aplicação

- [ ] Interface em inglês
- [ ] Crédito ao FIRMS visível no app
- [ ] Identificar código gerado com IA em texto descritivo ou metadados (ex.: README)
- [ ] Pedir a classificação FortiGuard do site para os jurados não terem o acesso bloqueado (recomendado, não obrigatório)

### Elegibilidade

- [ ] Todos os membros confirmados no mesmo evento local

Os critérios de julgamento são Impact, Creativity, Validity, Relevance e Presentation. O guia diz que a IA não deve ser usada para criar a ideia de como resolver o desafio, então a abordagem final precisa ser da equipe.
