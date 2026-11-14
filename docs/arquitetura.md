# Arquitetura e stack

Este documento registra as escolhas técnicas do projeto. Cada linha "a decidir" precisa de um responsável e de uma escolha antes de alguém escrever código naquela parte.

**Status:** rascunho. Nenhuma stack foi decidida ainda.

## Já decidido (vem dos outros documentos)

| Ponto | Decisão | Fonte |
| --- | --- | --- |
| Fonte dos focos | NASA FIRMS: arquivo SP para o histórico, API NRT para a atualização | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Escopo inicial | Brasil baixado inteiro, Amazônia recortada pelo bioma do IBGE | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Índice espacial | H3 (célula calculada na carga) | [importacao-regioes.md](importacao-regioes.md) |
| Modelo de dados | 5 tabelas: `focos`, `regioes`, `cobertura`, `fatores_harmonizacao`, `agregados` | [importacao-regioes.md](importacao-regioes.md) |
| Granularidade guardada | Célula H3 × ano × mês | [importacao-regioes.md](importacao-regioes.md) |
| Consulta | Pré-agregada. A API não consulta o FIRMS na hora | [requisitos.md](requisitos.md), RNF04 |
| Início do calendário | Janeiro de 2003 | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |

## A decidir

| # | Ponto | Opções levantadas | Escolha | Responsável |
| --- | --- | --- | --- | --- |
| 1 | Linguagem do pipeline | Python | Python (pandas, geopandas, pyarrow) | frente A |
| 2 | Banco de dados | PostgreSQL + PostGIS + h3-pg; DuckDB | PostgreSQL + PostGIS (H3 calculado no Python, ver [banco.md](banco.md)) | frente A |
| 3 | Resolução H3 | 5, 6, 7 | 6 (proposta em [banco.md](banco.md)) | frentes A e C |
| 4 | Linguagem e framework da API | | a decidir | |
| 5 | Framework do front | | a decidir | |
| 6 | Biblioteca de mapa e desenho de área (RD01) | | a decidir | |
| 7 | Biblioteca de gráficos do calendário | | a decidir | |
| 8 | Paleta acessível (RD04) | viridis ou cividis | a decidir | |
| 9 | Formato do download (RF13) | PNG, PDF, CSV | a decidir | |
| 10 | Granularidade mostrada no calendário | mensal ou diária | a decidir | |
| 11 | Onde roda o job NRT e a recarga SP | | a decidir | |
| 12 | Hospedagem pública (front, API e banco) | VPS; Postgres gerenciado | VPS com `docker compose`, incluindo `focos` (decidido no PR #2, ver [banco.md](banco.md)) | frentes A e C |
| 13 | Cálculo da anomalia (RF11, RF12) | mediana histórica, média de vários anos | a decidir | |

Ao decidir um ponto, preencha a escolha e escreva abaixo, em uma ou duas frases, por que ela foi escolhida.

## Justificativas

- **1. Python no pipeline:** preferência do time de dados. Tem as bibliotecas de dado geoespacial prontas (geopandas para o recorte por polígono, pyarrow para parquet) e já roda o download e a análise ([pipeline-dados.md](pipeline-dados.md)).
- **2. PostgreSQL:** escolha do time de dados. Tem PostGIS para os polígonos de `regioes`. O H3 é calculado no Python e guardado como `BIGINT`, então qualquer Postgres serve ([banco.md](banco.md)). Serve tanto para o pipeline quanto para a API, e tem hospedagem gratuita em vários provedores.

## Componentes

### data-pipeline

- **Faz:** importa os CSVs, recorta por região, calcula os fatores, gera os `agregados` e roda os jobs NRT e SP.
- **Entrada:** CSVs do FIRMS e shapefile de biomas do IBGE.
- **Saída:** tabelas preenchidas no banco.
- **Comandos previstos:** `importar <arquivo.csv>`, `recalcular <regiao>`.

### backend

- **Faz:** recebe área e período, soma os `agregados` das células H3 da área e devolve o calendário, a sazonalidade, o ranking de anos e as anomalias.
- **Contrato:** ver `api.md` nesta pasta (a escrever).

### frontend

- **Faz:** mapa para escolher a área, seletor de datas, calendário em heatmap, indicadores principais e downloads.
- **Requisitos que cobre:** RF06–RF13 e RD01–RD07.

## Ambientes e variáveis

| Variável | Uso | Onde fica |
| --- | --- | --- |
| `FIRMS_MAP_KEY` | API do FIRMS (jobs NRT e SP) | a decidir |
| _(conexão com o banco)_ | Pipeline e API | a decidir |
