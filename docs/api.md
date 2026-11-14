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
- **A faixa de incerteza é calculada depois de somar.** Totais por ano, sazonalidade e anomalias são calculados por cenário, e só no fim saem a mediana e a faixa. A soma dos percentis das células não é o percentil da soma.
- **O FRP (potência do fogo em MW) não aparece na tela.** Os fogos mais fortes saturam o VIIRS: 7% das detecções saturadas respondem por 22% da energia, e isso piora no pico da temporada. A soma em MW engana como indicador de gravidade. No lugar, a tela mostra uma **classe de intensidade** (`low`, `medium`, `high`, ver "Classe de intensidade"). O FRP em MW continua no pacote de auditoria (`counts.csv` e `detections.csv`).
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
| `GET` | `/detections/recent` | Focos recentes na área visível do mapa: hexágonos com a contagem no mapa afastado, pontos no mapa próximo | RD07 |

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

- No máximo **250.000 células** (~9 milhões de km²). O Brasil inteiro tem cerca de 220 mil células, então cabe. Acima disso: erro `area_too_large`.
- **Tempo de áreas grandes ainda não medido.** A Amazônia (110 mil células) leva ~0,8 s no banco. O Brasil inteiro deve levar perto de 1,6 s pela proporção, mas isso é estimativa (medição pedida na issue #5). Para o mundo, áreas grandes vão usar uma tabela agregada em resolução mais grossa (depois da submissão).
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
| `band_low`, `band_high` | número ou `null` | Faixa de incerteza (percentis 5 e 95 dos cenários, ver "Faixa de incerteza"). `null` quando `source = observed_viirs` |
| `source` | texto | `estimated_modis` (até 2012-01) ou `observed_viirs` (a partir de 2012-02). **Depende só da data** |
| `raw_count` | inteiro | Contagem bruta do satélite daquele mês, antes do fator. Para auditoria |
| `missing_days` | inteiro | Dias do mês sem dado do satélite daquele mês (tabela `dias_sem_dados`) |
| `incomplete` | booleano | `true` se `missing_days >= 3`, ou se o mês é o atual e ainda não acabou |
| `provisional` | booleano | `true` se o mês tem dados NRT (ainda não substituídos pelos SP) |
| `anomaly` | número ou `null` | `detections − mediana do mesmo mês nos anos de referência` (RF12). `null` no mês atual, que ainda não acabou (a comparação dele fica em `recent.month_to_date`) |
| `anomaly_pct` | número ou `null` | `detections / mediana − 1`. `null` quando a mediana é zero ou no mês atual |

`detections` é número decimal nos meses estimados (Aqua × fator). O front arredonda para mostrar.

### `years[]`: ranking dos anos (RF10)

Um item por ano do intervalo, **ordenado por `detections`, do maior para o menor**.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `year` | inteiro | |
| `detections` | número | Total do ano (soma dos meses, por cenário, mediana no fim) |
| `band_low`, `band_high` | número ou `null` | Faixa de incerteza do total do ano |
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

Sempre calculado até o último dia com dado (`data_through`), **independente do intervalo pedido**. Compara a janela atual com **todas as janelas de mesmo tamanho num raio de ±15 dias da mesma data**, em cada ano de referência (cerca de 25 janelas por ano, umas 350 no total). Assim o normal fica estável e tolera a estação que adianta ou atrasa umas semanas de um ano para o outro. Não usa proporção: o fogo não se distribui igual dentro do mês, e na temporada ele cresce ao longo do mês. Uma proporção mostraria queda justamente quando a situação piora.

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
| `typical_median` | número | Mediana das detecções nas janelas de referência (±15 dias da mesma data, em cada ano) |
| `typical_p25`, `typical_p75` | número | Faixa do normal (25% e 75% das janelas), para a tela dizer "dentro do normal" ou "acima do normal" |
| `difference` | número | `detections − typical_median` |
| `difference_pct` | número ou `null` | `detections / typical_median − 1`. `null` quando a mediana é zero |
| `n_years` | inteiro | Quantos anos entraram no normal |
| `n_windows` | inteiro | Quantas janelas entraram no normal |
| `n_high` | inteiro | Detecções de intensidade `high` na janela atual |
| `high_share` | número | `n_high / detections`. `null` quando não há detecções |

Os dias recentes são sempre VIIRS observado, então não há fator nem faixa de incerteza. O normal usa só anos com VIIRS (2012 em diante), porque não existe fator diário para o Aqua.

Depende de duas coisas que ainda não existem: a tabela de **contagens diárias** (issue #8) e o **job NRT** (issue #5).

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
   - **`observed_viirs`:** `detections = soma das contagens brutas`. Sem faixa. De 2012-02 a 2026-10 é o S-NPP. De 2026-11 em diante é o NOAA-20, também somado **sem fator** (fator 1, decisão da frente B).
   - **`estimated_modis`:** para cada cenário `c` (ano de calibração), `detections_c = Σ bruto[bioma, periodo] × fator[bioma, Aqua→S-NPP, mes, periodo, c]`.
4. Totais por ano, sazonalidade e anomalias são calculados **por cenário**. Só no fim: valor central = mediana dos cenários, faixa = percentis 5 e 95 por **interpolação linear** (o padrão do `numpy.percentile`). Com 13 cenários, o método muda o número, então ele vai escrito também no `metadata.json`.
   - **O número de cenários não é fixo.** A API usa os anos de calibração que existem em `fatores_harmonizacao` (10 ou 13, conforme a validação, e janeiro tem um a menos). Nada no código assume uma quantidade.
5. Preenche com zero os meses sem linha e junta os dias sem dado.
6. Para `recent`, soma as contagens diárias da área na janela atual e em todas as janelas de mesmo tamanho num raio de ±15 dias da mesma data, em cada ano de referência, e tira a mediana e o P25–P75 entre essas janelas.

Os fatores ficam na memória da API (a tabela inteira tem poucos milhares de linhas) e são recarregados quando `data_version` muda.

### Faixa de incerteza

Os meses `estimated_modis` trazem uma faixa (`band_low` a `band_high`) entre os cenários de calibração.

- **Percentis 5 e 95.** Com 13 cenários, a faixa entre percentis cobre menos do que o nome sugere: numa simulação da frente B, um ano novo cai dentro de P10–P90 em ~69% dos casos, e dentro de P5–P95 em ~79%. A troca está registrada no `decisoes-harmonizacao.md`.
- **Nomes neutros.** Os campos não dizem o percentil. Ele vai em `metadata.json` (`"band_percentiles": [5, 95]`). Assim, mudar os percentis no futuro não quebra o contrato.
- **Texto da tela:** "o valor real fica dentro desta faixa em cerca de N de cada 10 casos", com **N medido** no teste da calibração, por bioma. Enquanto a cobertura real não for medida, a tela não promete número nenhum.
- A faixa P25–P75 do bloco `recent` é outra coisa (a variação natural entre anos) e não muda.

## Resposta: `POST /export`

Devolve `application/zip` com o pacote de auditoria. Com `counts.csv` × `factors.csv`, qualquer pessoa refaz o calendário.

| Arquivo | Conteúdo |
| --- | --- |
| `result.csv` | Os itens de `months[]`, uma linha por mês |
| `counts.csv` | `region_id, biome, year, month, satellite, daynight, raw_count, frp_sum` |
| `factors.csv` | Os fatores usados: `region_id, source_satellite, target_satellite, month, daynight, calibration_year, factor` |
| `metadata.json` | O pedido, `meta`, a fórmula, os percentis da faixa (`"band_percentiles": [5, 95]`), o método do percentil (interpolação linear), os anos de calibração usados, os filtros (`type = 0`, confiança nominal e alta, duplicatas), as fontes do FIRMS e a data da exportação |
| `detections.csv` | Focos brutos da área no intervalo, até **500.000 linhas**: `satellite, latitude, longitude, acquired_utc, confidence, frp, daynight, quality, source_file` |

Os valores também vão em inglês: `confidence` = `low`/`nominal`/`high`, `daynight` = `D`/`N` (como no FIRMS), `quality` = `SP`/`NRT`.

Se a área tiver mais de 500.000 focos, `detections.csv` sai do ZIP e `metadata.json` traz `"detections_omitted": true` com a contagem total. A mensagem para o usuário sugere uma área ou um período menor.

Nome do arquivo: `firesync-YYYY-MM-DD.zip`.

O PNG do calendário é gerado no front, a partir do que está na tela.

## `GET /detections/recent`

A camada de focos recentes do mapa. Vem da nossa API, e não do GIBS: as camadas de fogo do GIBS são vector tiles, que o Leaflet não lê sem plugin, e deram erro nos testes. Os dados são os focos NRT que o job de atualização grava em `focos`.

Tem dois modos, para nunca cortar dados:

- **Mapa afastado:** **hexágonos** com a contagem de focos de cada um (mapa de calor). Mostra tudo, sem limite.
- **Mapa próximo:** os **pontos** individuais.

Pedido:

```
GET /api/v1/detections/recent?bbox=-63.5,-6.0,-57.0,0.5&hours=168&zoom=5
```

| Parâmetro | Valores | Significado |
| --- | --- | --- |
| `bbox` | `oeste,sul,leste,norte` | Área visível do mapa |
| `hours` | `24`, `72` ou `168` (padrão `24`) | Janela de tempo até agora |
| `zoom` | inteiro (zoom do Leaflet) | Escolhe o modo e o tamanho dos hexágonos |
| `mode` | `auto` (padrão), `hexagons` ou `points` | Força um modo. O front usa `auto` |

### Como o modo é escolhido (`mode=auto`)

| Zoom | Modo | Hexágono |
| --- | --- | --- |
| até 4 | `hexagons` | Resolução H3 4 (~1.770 km²) |
| 5 e 6 | `hexagons` | Resolução H3 5 (~250 km²) |
| 7 | `hexagons` | Resolução H3 6 (~36 km², a do banco) |
| 8 em diante | `points` | — |

Se o modo `points` passar de **50.000 focos**, a API devolve hexágonos de resolução 6 no lugar. Nunca corta a lista.

O banco guarda só a resolução 6. A API junta as células nas resoluções 4 e 5 com `h3.cell_to_parent`. O hexágono pai não cobre os filhos com exatidão, o que não importa num mapa de calor.

### Resposta

Sempre GeoJSON, que o Leaflet desenha direto, sem precisar da biblioteca H3 no front.

**`hexagons`:**

```json
{
  "type": "FeatureCollection",
  "mode": "hexagons",
  "h3_resolution": 5,
  "hours": 168,
  "updated_at": "2026-11-14T15:00:00Z",
  "total_detections": 51588,
  "features": [
    { "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [[[-60.31, -3.05], [-60.22, -2.97], [-60.11, -3.01], [-60.10, -3.12], [-60.19, -3.20], [-60.30, -3.16], [-60.31, -3.05]]] },
      "properties": { "h3": "85a8100ffffffff", "detections": 37, "n_low": 21, "n_medium": 12, "n_high": 4 } }
  ]
}
```

- `h3` vai como **texto**, nunca como número (ver "H3 IDs").
- O front pinta os hexágonos com a mesma paleta do calendário (cividis em escala log).
- `n_low`, `n_medium` e `n_high` são a contagem por classe de intensidade, e somam `detections`.

**`points`:**

```json
{
  "type": "FeatureCollection",
  "mode": "points",
  "hours": 24,
  "updated_at": "2026-11-14T15:00:00Z",
  "total_detections": 3833,
  "features": [
    { "type": "Feature", "geometry": { "type": "Point", "coordinates": [-60.21, -3.12] },
      "properties": { "satellite": "N20", "acquired_utc": "2026-11-14T05:42:00Z", "confidence": "nominal", "intensity": "medium", "daynight": "N" } }
  ]
}
```

### Regras

- Só confiança nominal e alta, o mesmo filtro do calendário.
- Cache com a mesma regra da seção "Desempenho": a chave inclui o `updated_at`, então o cache se renova sozinho a cada atualização NRT.
- Erros: `invalid_bbox` (400), `invalid_hours` (400) e `invalid_mode` (400).

### Consulta e desempenho

A consulta filtra **primeiro pelo tempo**, pelo índice parcial `focos_nrt ON focos (datahora_utc) WHERE qualidade = 'NRT'` (migration 003 da frente A), e depois pelo bbox. Os últimos dias são sempre NRT, porque o SP chega meses depois.

```sql
SELECT h3, count(*) AS n
FROM focos
WHERE qualidade = 'NRT'
  AND datahora_utc >= now() - %s::interval
  AND confianca IN ('nominal', 'alta')
  AND lon BETWEEN %s AND %s AND lat BETWEEN %s AND %s   -- bbox visível
GROUP BY h3;
```

Medido pela frente A em 14/11, com o histórico completo (46,4 milhões de focos), na issue #5:

| Consulta | Tempo |
| --- | --- |
| 7 dias, bbox da Amazônia, agrupado por célula (51.588 focos → 7.962 hexágonos) | 19 ms (466 ms na primeira execução, com o disco disputado) |
| 24 h, bbox da Amazônia (3.833 focos) | 1 ms |

## Classe de intensidade

A tela não mostra o FRP em MW. Cada detecção recebe uma classe, para quem decide **onde atuar primeiro**: 3 detecções fortes podem pesar mais que 100 fracas. Proposta da frente B, aprovada no PR #4.

| Classe | Regra |
| --- | --- |
| `low` | FRP abaixo de 5 MW |
| `medium` | FRP de 5 a 25 MW |
| `high` | FRP de 25 MW ou mais, **ou pixel saturado do VIIRS** |

- **Por que o pixel saturado entra em `high`:** nos fogos mais fortes, o VIIRS satura, e o FRP sai **menor** do que o real. A mediana do FRP saturado é 18 MW (S-NPP, Amazônia, 2024). Só pelo FRP, mais da metade desses fogos cairia como `medium`. No VIIRS, a confiança alta (`confianca = 'alta'`) marca o pixel saturado. **Só no VIIRS:** no MODIS, confiança alta (80 ou mais) não indica saturação, então a regra não vale para ele.
- **Limites fixos e configuráveis:** os valores (5 e 25 MW) vêm da distribuição do S-NPP em 2024 (mediana 5,4 MW, P90 26,6 MW) e ficam no mesmo arquivo de configuração versionado do alerta (`alert_rules.json`). A tela usa sempre os mesmos limites, então o mesmo fogo não muda de classe quando o usuário mexe no mapa. Mudar os limites não exige mudar o código. A versão vai no `metadata.json`.
- **Só VIIRS:** a classe vale para detecções do VIIRS, que são todas as recentes. O FRP do MODIS não é comparável.
- **Limites a declarar na tela de Método:** o FRP de pixels na borda da faixa do satélite tende a sair maior, e os fogos à noite tendem a ter FRP menor. A classe ajuda a priorizar, mas não substitui informação de campo, vento e avanço da frente.

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
| 400 | `invalid_bbox`, `invalid_hours`, `invalid_mode` | Parâmetro inválido em `GET /detections/recent` |
| 404 | `region_not_found` | `region_id` não existe |
| 413 | `area_too_large` | Mais de 250.000 células |
| 429 | `rate_limited` | Passou do limite de pedidos por IP (RNF06). A resposta traz o cabeçalho `Retry-After`, com os segundos até poder tentar de novo |
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

**Como funciona o cache:** fica na memória da própria API (um LRU), sem serviço extra como Redis. A chave de cada resposta inclui o `updated_at` da última atualização NRT. Quando chega dado novo, a chave muda e o cache antigo simplesmente deixa de ser usado. Não existe um passo de "invalidar", e não há risco de mostrar dado velho.

A resposta também leva `ETag` com `updated_at`, para o navegador reaproveitar.

## Regras de operação

- **A API confere ao subir:** lê `config.h3_resolucao` e confere numa amostra de `agregados` que as células têm essa resolução. Se não bater, não sobe.
- **CORS:** só a origem do front.
- **Versão:** mudança que quebra o front vira `/api/v2`.

## Em aberto

| # | Ponto | Situação ou proposta | Quem decide |
| --- | --- | --- | --- |
| 1 | Job NRT mínimo e horário da última atualização | A cada 3 h, focos NRT das últimas 48 h, upsert e recálculo só dos dias e do mês atuais. Sem isso, `recent` não é verdade e o sistema não é "atualizado" (RNF03). Em andamento na issue #5 | Frente A |
| 2 | Tabela de contagens diárias | `agregados_diarios`, para o normal de ±15 dias e para o alerta. Pedida na issue #8 | Frente A |
| 3 | Nível de alerta (Normal / Atenção / Crítico) | Regra num `alert_rules.json` versionado, lido pela API. Validação com área queimada da NASA na issue #9 | Equipe, frentes B e C |
| 4 | Anos de referência da anomalia (RF12) | Todos os anos completos menos o próprio ano, fixo, independente do intervalo pedido | Equipe |
| 5 | Medida da anomalia | Diferença absoluta e percentual contra a mediana. O RD06 pede "média de vários anos", então `indicators` usa a média | Equipe |
| 6 | Linguagem e framework da API | Python, pela biblioteca `h3` e pelo código de consulta do [banco.md](banco.md) | Equipe (arquitetura, ponto 4) |
