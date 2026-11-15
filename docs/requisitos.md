# Requisitos — Calendário Harmonizado de Focos de Calor (MODIS + VIIRS)

Nov 13, 2026 · @Mateus Nogueira

Este documento separa o que o desafio **exige** (está nos Objetivos) do que ele só **sugere** (aparece como "pode considerar"). Assim fica claro o mínimo para entregar e o que dá pontos extras.

**Situação em 14/11/2026:** ✅ implementado e verificado no escopo indicado · ⏳ parcial. C1–C6 e a integração técnica D7 passaram com PostGIS sintético e navegador, além dos testes unitários/HTTP. A carga científica real não foi acessada nesta entrega: Eduardo executa o [roteiro de validação](validacao-api-eduardo.md) antes de fechar D7/M2. Deploy público segue pendente.

## 1. Requisitos obrigatórios

### Parte A: Harmonização dos dados (backend / pipeline)

- [x] **RF01:** Buscar os focos de calor do **MODIS** (Terra e Aqua). É a série histórica, do início dos anos 2000 em diante. ✅ MODIS Terra (desde 01/11/2000) e Aqua (desde 04/07/2002) até hoje, Brasil inteiro, na tabela `focos` ([pipeline-dados.md](pipeline-dados.md)).
- [x] **RF02:** Buscar os focos de calor do **VIIRS**. É o sensor que continua a série, com mais detalhe. ✅ VIIRS S-NPP (2012 até 02/11/2026), NOAA-20 e NOAA-21, na tabela `focos`.
- [x] **RF03:** Harmonizar as duas fontes numa **série temporal única e consistente**. Depois dessa etapa, "o sensor de origem não importa mais". O processo precisa compensar as diferenças entre os dois sensores: ✅ API aplica os fatores por cenário e só depois calcula mediana/P5–P95; reconstrução pelo ZIP testada com PostGIS sintético. Conferência da carga real no M2 com Eduardo.
  - resolução espacial (VIIRS \~375 m, MODIS \~1 km)
  - sensibilidade de detecção (o VIIRS detecta mais focos pequenos)
  - horário em que cada satélite passa
- [ ] **RF04:** Cobrir o período **do início dos anos 2000 até hoje**, com dados atualizados. ⏳ **parcial:** histórico de 2003 até hoje no banco de teste e job NRT a cada 3 h pronto (`job_nrt.py`). Falta rodar na VPS.
- [x] **RF05:** Entregar os dados harmonizados como **entrada da aplicação web**. ✅ `agregados`, `agregados_diarios`, `fatores_harmonizacao`, `dias_sem_dados`, `cobertura` e `config` no formato do [api.md](api.md) ([banco.md](banco.md)).

### Parte B: Aplicação web (frontend + API)

- [x] **RF06:** Deixar o usuário **escolher uma região / área de interesse**. ✅ Front e `POST /api/v1/calendar` integrados: região, GeoJSON ou ponto/raio, com cobertura e erros do contrato.
- [x] **RF07:** Deixar o usuário **escolher um intervalo de datas**. ✅ Intervalo UTC de `2003-01` a `last_month`, valores padrão e `invalid_period` testados por HTTP.
- [x] **RF08:** Mostrar um **calendário de atividade de queimadas** com o **número de focos de calor** da área escolhida, no formato meses × anos. ✅ Calendário histórico servido pela API e renderizado pelo front; integração com PostGIS sintético passou no desktop e celular.
- [x] **RF09:** Mostrar **quais meses do ano têm mais fogo** (o padrão sazonal). ✅ Sazonalidade calculada pela API com anos completos e cenários preservados; exibida no front.
- [x] **RF10:** Mostrar **quais anos tiveram mais fogo**. ✅ Totais anuais/ranking servidos por HTTP, com faixa de incerteza e anos incompletos sem posição.
- [x] **RF11:** Comparar o **mês atual com a mediana histórica** da área. ✅ `recent.month_to_date` e `last_7_days` sobre `agregados_diarios`, comparados a janelas históricas de mesmo tamanho em ±15 dias; testes com valores manuais.
- [x] **RF12:** Mostrar **como a atividade atual se compara a períodos anteriores**, ou seja, as anomalias. ✅ Anomalias históricas independentes do filtro e comparação recente expostas; a proposta metodológica continua registrada em `api.md`.
- [x] **RF13:** Permitir **baixar as análises e visualizações** da busca. ✅ `POST /api/v1/export` gera ZIP auditável em memória; download real pelo navegador testado. CSVs locais e PNG permanecem no front.

## 2. Requisitos desejáveis (diferenciais)

- [x] **RD01:** **Mapa interativo** em que o usuário desenha a área de interesse (polígono ou retângulo). ✅ Desenho do front integrado à seleção H3 e à rota HTTP, com `invalid_geometry` e `area_too_large`.
- [x] **RD02:** Opção de **digitar latitude e longitude**, como alternativa ao desenho no mapa. ✅ Ponto/raio de 1 a 200 km integrado à API; área fora da cobertura testada no navegador.
- [x] **RD03:** **Rampa de cores** no calendário, para mostrar as diferenças entre meses como um heatmap. ✅ escala logarítmica no calendário e nos hexágonos do mapa (`frontend/src/calendar/colorScale.ts`).
- [x] **RD04:** Cores **acessíveis**, legíveis para quem tem daltonismo (por exemplo, viridis ou cividis). ✅ paleta `cividis` em escala logarítmica no calendário e nos hexágonos H3, hachura/borda nos meses estimados e incompletos, e diferenciação por raio e espessura/estilo de borda além da cor nos pontos de intensidade (`low`, `medium`, `high`) no mapa.
- [x] **RD05:** **Exportar um CSV** com os focos de calor encontrados na busca. ✅ `detections.csv` no ZIP até 500.000 focos inclusive; acima disso, omissão e contagem total nos metadados. Caso com 500.001 focos verificado em PostGIS sintético.
- [x] **RD06:** **Indicadores principais** em destaque: ✅ Indicadores históricos e `last_7_days_vs_typical_pct` servidos pela API e exibidos no front.
  - número total de focos detectados e registrados
  - anomalia em relação à média de vários anos
- [x] **RD07:** Interface pensada para o **público-alvo**: equipes de alerta precoce, resposta a emergências, cientistas, gestores de terras e bombeiros. Precisa ser rápida de ler e de usar. ✅ Janela recente e mapa com 24/72/168 h, hexágonos ou pontos e classes `low`/`medium`/`high`, integrados à API; limite de 50.000 pontos troca para hexágonos sem truncamento.

## 3. Requisitos não funcionais (implícitos no texto)

- [ ] **RNF01:** Ser uma **aplicação web**, acessada pelo navegador. ⏳ **parcial:** app integrado localmente (front → proxy → API → PostGIS sintético); carga real aguarda Eduardo e deploy público segue em C7.
- [x] **RNF02:** **Fonte de dados:** o texto sugere o **NASA FIRMS** (Earthdata), que fornece os dados do MODIS e do VIIRS. ✅ NASA FIRMS: resumos anuais por país (SP) e API (SP e NRT).
- [ ] **RNF03:** **Atualização contínua.** O calendário precisa estar "atualizado", então os dados novos devem entrar periodicamente. ⏳ **parcial:** job NRT a cada 3 h pronto e testado (`job_nrt.py` + `Dockerfile`); falta rodar na VPS.
- [x] **RNF04:** **Desempenho.** São mais de 20 anos de focos no mundo inteiro, então as consultas por área e período precisam ser rápidas. Isso pede pré-agregação e indexação espacial. ✅ pré-agregação (`agregados`, `agregados_diarios`) e índice espacial H3: calendário de 100 × 100 km em 2–9 ms, Amazônia inteira em ~0,8 s, focos recentes em 19 ms (medido no banco de teste).
- [x] **RNF05:** **Usabilidade e acessibilidade**, porque o usuário pode estar numa situação de emergência. ✅ controles de área/período e camada de focos recentes com labels, `aria-pressed`, `aria-describedby`, alertas em `role="alert"`, calendário em `cividis` com hachura/borda, pontos diferenciados por raio e borda além da cor, navegação por teclado e downloads acessíveis no front (D1–D7, validado nas 18 jornadas E2E J1–J9 em desktop e celular).

### Definidos pela equipe

Não vêm do texto do desafio. São necessários porque o sistema é público e precisa estar sempre atualizado para o público de emergência (RD07).

- [ ] **RNF06:** **Limite de requisições na API.** A API é pública, e uma área grande (até 250 mil células) custa caro. Sem limite, uma pessoa ou um robô consegue derrubar o servidor. ⏳ **parcial:** limite por IP implementado na API, configurável, com `429 rate_limited` e `Retry-After` testados. Segundo limite no servidor web aguarda C7.
  - Limite por IP, com valores em configuração. Padrões implementados: 60 pedidos por minuto no geral, 10 por minuto em `POST /calendar` e 2 por minuto em `POST /export` ([variáveis](../backend/README.md)).
  - Acima do limite: HTTP `429` com o código `rate_limited` e o cabeçalho `Retry-After`.
  - Um segundo limite no servidor web (ver `infra/`), antes de o pedido chegar à API.
- [ ] **RNF07:** **Monitoramento.** ⏳ **parcial:** front avisa sobre dados com mais de 6 h; API registra endpoint, duração, células e status, e job registra as rodadas. Canal de aviso à equipe aguarda deploy.
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
