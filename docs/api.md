# Contrato da API

Nov 14, 2026 · frente C · **rascunho**

Este documento define o que o front manda e o que a API devolve. As frentes C (API) e D (front) trabalham em paralelo a partir dele. O front usa o [JSON de exemplo](api-exemplo.json) até a API real ficar pronta.

Mudar este contrato exige avisar a equipe antes e atualizar este documento no mesmo commit.

## Princípios

- **Tudo o que é público fica em inglês:** endpoints, campos do JSON, códigos e mensagens de erro, arquivos do export e nomes de funções no código. Quem avalia o projeto lê inglês. Só este documento fica em português.
- **O banco continua em português** (`focos`, `agregados`, `regiao_id`…), como já está na migration. A tradução para o inglês acontece num lugar só, na camada da API que lê o banco.
- **O front nunca vê células H3.** Ele manda a área e recebe o calendário pronto. A resolução H3 fica só no banco ([banco.md](banco.md)).
- **IDs H3, quando aparecem, são texto.** Um ID da resolução 6 passa de 2⁵³, e o `JSON.parse` do navegador o arredonda sem erro. Ver "H3 IDs" abaixo.
- **Zero, sem dados e fora da cobertura são coisas diferentes**, e a resposta sempre diz qual é o caso.
- **A faixa de incerteza é calculada depois de somar.** Totais por ano, sazonalidade e anomalias são calculados por cenário, e só no fim saem a mediana e o P10–P90. A soma dos P10 não é o P10 da soma.
- **O número mostrado se chama `detections`** (detecções de fogo), a convenção do FIRMS. Um fogo grande ocupa vários pixels, então não é "número de incêndios".
- **O papel do sistema:** o FIRMS mostra onde o fogo está agora. O firesync diz se isso é normal para esse lugar e essa época do ano. O público inclui equipes de alerta precoce e de resposta a emergências (RD07), então o indicador principal é a **janela recente** (últimos 7 dias), e não o mês inteiro.

## Endpoints

Base: `/api/v1`.

| Método | Caminho | O que faz | Requisitos |
| --- | --- | --- | --- |
| `GET` | `/health` | Situação da API, versão dos dados, resolução H3 | — |
| `GET` | `/regions` | Regiões prontas para o seletor (biomas) | RF06 |
| `POST` | `/calendar` | Calendário, sazonalidade, ranking de anos, mês atual, anomalias e indicadores de uma área | RF06–RF12, RD06 |
| `POST` | `/export` | Pacote de auditoria em ZIP da mesma busca | RF13, RD05 |

`/calendar` e `/export` usam `POST` porque o GeoJSON da área pode ser grande demais para a URL.

## Pedido: `POST /calendar` e `POST /export`

```json
{
  "area": { "type": "geojson", "geometry": { "type": "Polygon", "coordinates": [[[-60.5, -3.5], [-59.5, -3.5], [-59.5, -2.5], [-60.5, -2.5], [-60.5, -3.5]]] } },
  "start": "2003-01",
  "end": "2026-11"
}
```

### `area`: três formas

| `type` | Campos | Uso |
| --- | --- | --- |
| `region` | `region_id` (de `GET /regions`) | Região pronta. Resposta em cache, instantânea |
| `geojson` | `geometry`: `Polygon` ou `MultiPolygon`, WGS84, ordem **lon, lat** (padrão GeoJSON) | Área desenhada no mapa (RD01) |
| `point` | `lat`, `lon`, `radius_km` (1 a 200) | Lat/lon digitado (RD02). A API transforma num círculo |

Como a área vira células: entra a célula cujo **centro** cai dentro da área (regra do `h3shape_to_cells`). Área menor que uma célula usa a célula do centro da área.

Limites:

- No máximo **150.000 células** (~5,4 milhões de km², mais que a Amazônia inteira). Acima disso: erro `area_too_large`.
- Geometria inválida (anel aberto, auto-interseção): erro `invalid_geometry`.

### `start` e `end`

- Formato `YYYY-MM`. Os dois são opcionais.
- Padrão: `start = 2003-01`, `end = last_month` (ver `GET /health`).
- Fora de `2003-01` a `last_month`: erro `invalid_period`.

## Resposta: `POST /calendar`

Exemplo completo em [api-exemplo.json](api-exemplo.json). Estrutura:

```
meta            versão dos dados, escala, último mês, resolução H3
area            tipo, número de células, área em km², biomas da área
coverage        full | partial | none, com mensagem
months[]        o calendário: um item por mês do intervalo
years[]         total por ano e ranking (RF10)
seasonality[]   12 itens, um por mês do ano (RF09)
recent          últimos 7 dias e mês até hoje contra o normal da época (RF11)
indicators      números de destaque (RD06)
```

### `meta`

| Campo | Tipo | Exemplo | Significado |
| --- | --- | --- | --- |
| `data_version` | data | `"2026-11-14"` | Quando os dados foram carregados |
| `scale` | texto | `"VIIRS"` | Escala da série harmonizada |
| `last_month` | `YYYY-MM` | `"2026-11"` | Último mês com dado |
| `updated_at` | data e hora UTC | `"2026-11-14T15:00:00Z"` | Última atualização NRT. A tela mostra quão fresco é o dado |
| `h3_resolution` | inteiro | `6` | Só informativo. O front não usa |

### `area`

| Campo | Tipo | Significado |
| --- | --- | --- |
| `type` | texto | Igual ao pedido |
| `n_cells` | inteiro | Células da área |
| `area_km2` | número | Área coberta pelas células (não a desenhada) |
| `biomes` | lista | `{ "region_id", "name", "fraction" }`: quanto da área cai em cada bioma |

### `coverage`

| `status` | Quando | O que a API devolve |
| --- | --- | --- |
| `full` | Toda a área está dentro da cobertura | Tudo |
| `partial` | Parte da área está fora | Tudo, calculado só com a parte de dentro. `covered_fraction` diz quanto |
| `none` | A área inteira está fora | Só `meta`, `area` e `coverage`, com a mensagem. **Nunca um calendário com zeros** |

Exemplo de `none`:

```json
{ "status": "none", "covered_fraction": 0, "message": "No data for this area yet. Current coverage: Brazil." }
```

### `months[]`: o calendário (RF08)

Um item por mês do intervalo, sem buracos. Mês sem focos vem com `detections: 0`.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `month` | `YYYY-MM` | |
| `detections` | número | Detecções de fogo na escala VIIRS. Valor central |
| `p10`, `p90` | número ou `null` | Faixa de incerteza. `null` quando `source = observed_viirs` |
| `source` | texto | `estimated_modis` (até 2012-01) ou `observed_viirs` (a partir de 2012-02). **Depende só da data** |
| `raw_count` | inteiro | Contagem bruta do satélite daquele mês, antes do fator. Para auditoria |
| `missing_days` | inteiro | Dias do mês sem dado do satélite daquele mês (tabela `dias_sem_dados`) |
| `incomplete` | booleano | `true` se `missing_days >= 3`, ou se o mês é o atual e ainda não acabou |
| `provisional` | booleano | `true` se o mês tem dados NRT (ainda não substituídos pelos SP) |
| `frp_sum` | número ou `null` | Soma do FRP em MW. `null` quando `source = estimated_modis`, porque o FRP do MODIS não é comparável |
| `anomaly` | número ou `null` | `detections − mediana do mesmo mês nos anos de referência` (RF12). `null` no mês atual, que ainda não acabou (a comparação dele fica em `recent.month_to_date`) |
| `anomaly_pct` | número ou `null` | `detections / mediana − 1`. `null` quando a mediana é zero ou no mês atual |

`detections` é número decimal nos meses estimados (Aqua × fator). O front arredonda para mostrar.

### `years[]`: ranking dos anos (RF10)

Um item por ano do intervalo, **ordenado por `detections`, do maior para o menor**.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `year` | inteiro | |
| `detections` | número | Total do ano (soma dos meses, por cenário, mediana no fim) |
| `p10`, `p90` | número ou `null` | Faixa do total do ano |
| `source` | texto | `estimated_modis`, `observed_viirs` ou `mixed` (2012) |
| `complete` | booleano | `false` se o intervalo pega só parte do ano, ou se é o ano atual |
| `rank` | inteiro ou `null` | Posição no ranking, contando só os anos completos. `null` nos incompletos |

### `seasonality[]`: meses com mais fogo (RF09)

Doze itens, de janeiro a dezembro, usando **só os anos completos** do intervalo.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `month_of_year` | 1–12 | |
| `median` | número | Mediana entre os anos |
| `mean` | número | Média entre os anos |
| `min`, `max` | número | Menor e maior ano |
| `n_years` | inteiro | Quantos anos entraram |

### `recent`: o agora contra o normal da época (RF11)

Sempre calculado até o último dia com dado (`data_through`), **independente do intervalo pedido**. Compara sempre **os mesmos dias do calendário** nos anos de referência. Não usa proporção: o fogo não se distribui igual dentro do mês, e na temporada ele cresce ao longo do mês. Uma proporção mostraria queda justamente quando a situação piora.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `data_through` | data | Último dia com dado |
| `last_7_days` | objeto | Os 7 dias até `data_through` (janela principal, para alerta precoce) |
| `month_to_date` | objeto | Do dia 1 do mês atual até `data_through` (RF11) |

Os dois objetos têm o mesmo formato:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `start`, `end` | data | Janela comparada |
| `detections` | número | Detecções na janela, agora |
| `typical_median` | número | Mediana das detecções nos **mesmos dias do calendário** dos anos de referência |
| `typical_p25`, `typical_p75` | número | Faixa do normal (25% e 75% dos anos), para a tela dizer "dentro do normal" ou "acima do normal" |
| `difference` | número | `detections − typical_median` |
| `difference_pct` | número ou `null` | `detections / typical_median − 1`. `null` quando a mediana é zero |
| `n_years` | inteiro | Quantos anos entraram no normal |

Os dias recentes são sempre VIIRS observado, então não há fator nem faixa de incerteza. O normal usa só anos com VIIRS (2012 em diante), porque não existe fator diário para o Aqua.

Depende de duas coisas que ainda não existem (ver "Em aberto"): a tabela de **contagens diárias** e o **job NRT**.

### `indicators` (RD06)

| Campo | Significado |
| --- | --- |
| `total_detections` | Soma de `detections` no intervalo |
| `latest_complete_year` | `{ "year", "detections", "reference_mean", "anomaly_pct" }` |
| `last_7_days_vs_typical_pct` | Igual a `recent.last_7_days.difference_pct` |

**Anos de referência** (proposta, ver "Em aberto"): todos os anos completos da série, de 2003 ao último ano completo, menos o próprio ano do mês. Não depende do intervalo pedido, para a anomalia de um mês não mudar quando o usuário muda o filtro.

## Como a API calcula

A fórmula é a de [importacao-regioes.md](importacao-regioes.md). Resumo do que a API faz:

1. Converte a área em células (ou lê as células da região pronta).
2. Busca em `agregados` a contagem bruta da área por `regiao_id × ano × mes × satelite × periodo` ([consulta em banco.md](banco.md)).
3. Para cada mês:
   - **`observed_viirs`:** `detections = soma das contagens brutas`. Sem faixa.
   - **`estimated_modis`:** para cada cenário `c` (ano de calibração), `detections_c = Σ bruto[bioma, periodo] × fator[bioma, Aqua→S-NPP, mes, periodo, c]`.
4. Totais por ano, sazonalidade e anomalias são calculados **por cenário**. Só no fim: valor central = mediana dos cenários, faixa = P10 e P90.
5. Preenche com zero os meses sem linha e junta os dias sem dado.
6. Para `recent`, soma as contagens diárias da área na janela atual e na mesma janela de cada ano de referência, e tira a mediana e o P25–P75 entre os anos.

Os fatores ficam na memória da API (a tabela inteira tem poucos milhares de linhas) e são recarregados quando `data_version` muda.

## Resposta: `POST /export`

Devolve `application/zip` com o pacote de auditoria. Com `counts.csv` × `factors.csv`, qualquer pessoa refaz o calendário.

| Arquivo | Conteúdo |
| --- | --- |
| `result.csv` | Os itens de `months[]`, uma linha por mês |
| `counts.csv` | `region_id, biome, year, month, satellite, daynight, raw_count, frp_sum` |
| `factors.csv` | Os fatores usados: `region_id, source_satellite, target_satellite, month, daynight, calibration_year, factor` |
| `metadata.json` | O pedido, `meta`, a fórmula, os filtros (`type = 0`, confiança nominal e alta, duplicatas), as fontes do FIRMS e a data da exportação |
| `detections.csv` | Focos brutos da área no intervalo, até **500.000 linhas**: `satellite, latitude, longitude, acquired_utc, confidence, frp, daynight, quality, source_file` |

Os valores também vão em inglês: `confidence` = `low`/`nominal`/`high`, `daynight` = `D`/`N` (como no FIRMS), `quality` = `SP`/`NRT`.

Se a área tiver mais de 500.000 focos, `detections.csv` sai do ZIP e `metadata.json` traz `"detections_omitted": true` com a contagem total. A mensagem para o usuário sugere uma área ou um período menor.

Nome do arquivo: `firesync-YYYY-MM-DD.zip`.

O PNG do calendário é gerado no front, a partir do que está na tela.

## `GET /regions`

```json
[
  { "region_id": 1, "name": "Amazônia", "source": "IBGE, Biomas do Brasil 1:250.000", "bbox": [-74.0, -16.3, -43.9, 5.3] }
]
```

`bbox` é `[oeste, sul, leste, norte]`, para o front centralizar o mapa. `name` é o nome oficial da fonte. O front pode mostrar a tradução ("Amazon").

## `GET /health`

```json
{ "status": "ok", "data_version": "2026-11-14", "last_month": "2026-11", "updated_at": "2026-11-14T15:00:00Z", "h3_resolution": 6 }
```

## Erros

Formato único:

```json
{ "error": { "code": "area_too_large", "message": "The selected area is too large. Draw a smaller area." } }
```

| HTTP | `code` | Quando |
| --- | --- | --- |
| 400 | `invalid_geometry` | GeoJSON inválido ou de tipo não aceito |
| 400 | `invalid_period` | Data fora de `2003-01` a `last_month`, ou `start` depois de `end` |
| 404 | `region_not_found` | `region_id` não existe |
| 413 | `area_too_large` | Mais de 150.000 células |
| 500 | `internal_error` | Qualquer outro. A mensagem não expõe detalhes do servidor |

Área fora da cobertura **não** é erro: é `200` com `coverage.status = "none"`.

## H3 IDs

A API não devolve células por padrão. Se um dia precisar (por exemplo, para desenhar os hexágonos no mapa), elas vão como texto, no formato do `h3-js`:

```json
{ "cells": ["86a8100c7ffffff"] }
```

Teste obrigatório: a API devolve uma célula conhecida, e o teste confere que ela volta igual depois de passar pelo JSON.

## Desempenho

| Caso | Meta (no servidor) | Como |
| --- | --- | --- |
| Região pronta (`type: region`) | < 50 ms | Cache calculado depois de cada carga de dados |
| Área desenhada de até ~100 × 100 km | < 100 ms | Consulta direta |
| Área desenhada do tamanho da Amazônia | < 1,5 s | Consulta direta |
| Mesmo pedido repetido | < 50 ms | Cache por (células da área + intervalo + `updated_at`) |

A resposta leva `ETag` com `updated_at`, para o navegador reaproveitar. O cache expira a cada atualização NRT.

## Regras de operação

- **A API confere ao subir:** lê `config.h3_resolucao` e confere numa amostra de `agregados` que as células têm essa resolução. Se não bater, não sobe.
- **CORS:** só a origem do front.
- **Versão:** mudança que quebra o front vira `/api/v2`.

## Em aberto

| # | Ponto | Proposta | Quem decide |
| --- | --- | --- | --- |
| 1 | NOAA-20 → S-NPP: aplicar fator ou tratar como iguais | Pergunta feita no PR #3 | Frente B |
| 2 | Job NRT mínimo (volta o X1 do `tarefas.md`) | A cada 3 h, focos NRT das últimas 48 h pela API do FIRMS, upsert e recálculo só dos dias e do mês atuais. Container com cron na VPS. A recarga SP (X2) continua cortada. Sem isso, `recent` não é verdade e o sistema não é "atualizado" (RNF03) | Equipe, frente A |
| 2b | Tabela de contagens diárias | `agregados_diarios (h3, data, satelite, periodo, focos_brutos)`, só dias com foco, VIIRS de 2012 em diante. Estimativa: ~15 milhões de linhas no Brasil, cabe na VPS | Frente A |
| 2c | Camada de focos recentes no mapa | Detecções das últimas 24 h ou 7 dias por cima do mapa, pela camada do FIRMS no GIBS (sem chave). É o que a equipe de resposta olha primeiro | Frente D |
| 3 | Anos de referência da anomalia (RF12) | Todos os anos completos menos o próprio ano, fixo, independente do intervalo pedido | Equipe |
| 4 | Medida da anomalia | Diferença absoluta e percentual contra a mediana. O RD06 pede "média de vários anos", então `indicators` usa a média | Equipe |
| 5 | Linguagem e framework da API | Python, pela biblioteca `h3` e pelo código de consulta do [banco.md](banco.md) | Equipe (arquitetura, ponto 4) |
