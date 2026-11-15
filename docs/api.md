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
| `data_version` | data e hora UTC | `"2026-11-14T19:48:30Z"` | Quando os dados foram carregados. Tem a hora para duas cargas no mesmo dia não ficarem com a mesma versão (issue #15). A tela pode mostrar só a data. A comparação usa o valor inteiro |
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

Sempre calculado até o último dia com dado (`data_through`), **independente do intervalo pedido**. Compara a janela atual com **todas as janelas de mesmo tamanho num raio de ±15 dias da mesma data**, em cada ano de referência (31 janelas por ano, uma para cada deslocamento de −15 a +15 dias: 434 em 14 anos). Assim o normal fica estável e tolera a estação que adianta ou atrasa umas semanas de um ano para o outro. Não usa proporção: o fogo não se distribui igual dentro do mês, e na temporada ele cresce ao longo do mês. Uma proporção mostraria queda justamente quando a situação piora.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `data_through` | data | Último dia com dado |
| `alert_level` | texto ou `null` | `normal`, `attention` ou `critical`, calculado na janela de 7 dias; `null` sem referência histórica ou com dia indisponível na janela atual |
| `alert_rules_version` | texto | Versão de `config/alert_rules.json` usada no cálculo |
| `last_7_days` | objeto | Os 7 dias até `data_through` (janela principal, para alerta precoce) |
| `month_to_date` | objeto | Do dia 1 do mês atual até `data_through` (RF11) |

**Regra do alerta (decisão da [issue #59](https://github.com/27threads/firesync/issues/59#issuecomment-6886903635)):** Crítico exige `s7 >= max(2 × mediana, 10)` e soma de `t−2..t` maior que a de `t−5..t−3`. O piso de 10 vale para qualquer mediana, inclusive zero. Se não for Crítico, Atenção exige `s7 > P75`; caso contrário, Normal. Razão, piso, percentil e tendência vêm da configuração versionada. A semana fixa em domingo pertence ao backtest; a API avalia a janela móvel até `data_through`. O nível vale para `last_7_days`, não para o mês.

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

Usa a tabela de **contagens diárias** `agregados_diarios` (issue #8, migration 004) e o **job NRT** a cada 3 h (issue #5, `data-pipeline/job_nrt.py`), os dois prontos na frente A.

### `indicators` (RD06)

| Campo | Significado |
| --- | --- |
| `total_detections` | Soma de `detections` no intervalo |
| `latest_complete_year` | `{ "year", "detections", "reference_median", "anomaly_pct" }` |
| `last_7_days_vs_typical_pct` | Igual a `recent.last_7_days.difference_pct` |

Em `latest_complete_year`, `reference_median` é a mediana dos totais anuais dos anos de referência, calculada dentro de cada cenário; só depois se calcula a mediana entre cenários. `anomaly_pct` segue a mesma ordem: `total_do_ano / mediana_de_referência − 1` por cenário, mediana no fim. Por isso, a divisão dos dois valores centrais exibidos pode diferir desse percentual. Sem anos de referência, ambos são `null`; se a referência de algum cenário for zero, o percentual é `null`. Sem ano completo no intervalo pedido, `latest_complete_year` é `null`.

**Anos de referência** (decidido, ver "Decisões fechadas"): todos os anos completos da série, de 2003 ao último ano completo, menos o próprio ano do mês. Não depende do intervalo pedido, para a anomalia de um mês não mudar quando o usuário muda o filtro.

## Como a API calcula

A fórmula é a de [importacao-regioes.md](importacao-regioes.md). Resumo do que a API faz:

1. Converte a área em células (ou lê as células da região pronta).
2. Busca em `agregados` a contagem bruta da área por `regiao_id × ano × mes × satelite × periodo` ([consulta em banco.md](banco.md)).
3. Para cada mês:
   - **`observed_viirs`:** `detections = soma das contagens brutas`. Sem faixa. De 2012-02 a 2026-10 é o S-NPP. De 2026-11 em diante é o NOAA-20, também somado **sem fator** (fator 1, decisão da frente B).
   - **`estimated_modis`:** para cada cenário `c` (ano de calibração), `detections_c = Σ bruto[bioma, periodo] × fator[bioma, Aqua→S-NPP, mes, periodo, c]`.
4. Totais por ano, sazonalidade e anomalias são calculados **por cenário**. Só no fim: valor central = mediana dos cenários, faixa = percentis 5 e 95 por **interpolação linear** (o padrão do `numpy.percentile`). Com 13 cenários, o método muda o número, então ele vai escrito também no `metadata.json`.
   - **A quantidade de cenários não é fixa:** meses isolados (`months[]`) usam todos os cenários que têm fator naquele mês (em janeiro, o cenário 2012 fica de fora), e os **totais do ano (`years[]`, ranking e anomalias anuais) usam só os cenários completos** (com todos os fatores necessários no ano, sem entrar com zero nem preencher mês ausente pela mediana), conforme [importacao-regioes.md, "Fórmula do calendário", itens 6 e 7](importacao-regioes.md#fórmula-do-calendário-para-refazer-a-partir-do-export-de-auditoria).
5. Preenche com zero os meses sem linha e junta os dias sem dado.
6. Para `recent`, soma as contagens diárias da área na janela atual e em todas as janelas de mesmo tamanho num raio de ±15 dias da mesma data, em cada ano de referência, e tira a mediana e o P25–P75 entre essas janelas.

Os fatores ficam na memória da API (a tabela inteira tem poucos milhares de linhas) e são recarregados quando `data_version` muda. A comparação usa o valor inteiro, com a hora: cortar para a data perde a segunda carga do dia.

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
      "properties": { "h3": "85a8100ffffffff", "detections": 37, "n_low": 21, "n_medium": 12, "n_high": 4,
                      "alert_cell": "84a8101ffffffff", "alert_level": "critical" } }
  ],
  "alerts": {
    "data_through": "2026-11-14",
    "alert_rules_version": "1.1",
    "unit": "H3 resolution 4 cell (about 1,770 km2)",
    "horizon_days": 14,
    "overall_share": 0.042,
    "priority": [
      { "h3": "84a8101ffffffff", "alert_level": "critical", "detections_7d": 46, "typical_median": 7,
        "share_followed_by_high": 0.266, "center": [-60.2, -3.1] }
    ]
  }
}
```

- `h3` vai como **texto**, nunca como número (ver "H3 IDs").
- O front pinta os hexágonos com a mesma paleta do calendário (cividis em escala log).
- `n_low`, `n_medium` e `n_high` são a contagem por classe de intensidade, e somam `detections`.
- **`alert_cell` e `alert_level` (RFC 0003):** o nível de urgência (`normal`, `attention`, `critical`) da célula H3 de **resolução 4** que contém o hexágono, pela mesma regra `v1` do `recent`, aplicada à contagem diária da própria célula. A resolução 4 é a unidade em que a `v1` foi testada no backtest, por isso o nível é sempre o dela, mesmo quando o mapa mostra hexágonos menores (zoom 5 a 7). `null` quando a célula não tem histórico.

**`alerts` (os dois modos, RFC 0003):** onde olhar primeiro, entre as células de resolução 4 com fogo recente na área visível.

| Campo | Significado |
| --- | --- |
| `data_through` | Último dia das contagens diárias usado no nível |
| `alert_rules_version` | Versão do `alert_rules.json` |
| `unit`, `horizon_days`, `overall_share` | Do bloco `historical_outcome` do `alert_rules.json`: a unidade testada, o horizonte (14 dias) e a parte média das semanas seguida de muito fogo (4,2%) |
| `priority` | Células em **Crítico**, depois em **Atenção**, cada grupo da maior para a menor razão entre a semana e o normal. Normal fica de fora |
| `priority[].share_followed_by_high` | Com que frequência esse nível foi seguido de detecções incomumente altas nos 14 dias seguintes, no backtest de 2013 a 2024: Normal 2,6%, Atenção 10,7%, Crítico 26,6% (conferido no banco: 2,58%, 10,69% e 26,58%). No backtest o normal da célula usa todos os outros anos; no mapa usa só os anos anteriores ao atual, então a regra é quase a mesma, não idêntica. **É uma frequência do passado, não uma previsão** |
| `priority[].center` | `[lon, lat]` do centro da célula, para o front levar o mapa até ela |

**Risco dos próximos 14 dias, do modelo treinado (RFC 0003).** O modelo roda **fora da API** (`data-pipeline/risco_celulas.py`) e grava a tabela `risco_celulas`; a API só lê. Para cada célula de resolução 4 na área visível, soma:

- **aviso antecipado:** as notas vêm da tabela e não dos focos recentes. Toda célula com nota dentro da área visível entra, mesmo **sem fogo agora**, e as de faixa muito alta ou alta aparecem em `alerts.priority` (com `alert_level` e `detections_7d` nulos quando não há histórico recente). Sem fogo na área, o bloco `alerts` vem só com o risco;
- em cada hexágono (só onde há fogo), `risk_prob` (0 a 1) e `risk_tier` (`very_high`, `high`, `medium` ou `lower`) da célula que o contém. Ficam `null` quando a célula não tem nota;
- em `alerts.risk`, a legenda: `scored_at` (quando as notas foram calculadas), `data_ref`, `model_version`, `horizon_days` (14), `rules_version` e `tiers[]`, com `min_prob` e `historical_share` de cada faixa (muito alto a partir de 60%, alto de 40%, médio de 20%);
- em `alerts.priority[]`, os campos `risk_prob` e `risk_tier`. Com notas, a lista passa a ser **ordenada pela faixa de risco** (a mais alta primeiro), e o nível de alerta vira um selo ("incomum para a época"). Uma célula em faixa **muito alta ou alta** entra na lista mesmo com alerta Normal, e por isso `alert_level` pode vir `normal` ou `null`. Na temporada de fogo (ago a out) cerca de 29% das células ficam em "muito alto", e a lista pode ficar longa: o front limita os itens.

`historical_share` é com que frequência a faixa teve fogo relevante (10 ou mais detecções) nos 14 dias seguintes no teste de 2021 a 2024, treinando só com anos anteriores e sem o Pantanal: 82%, 46%, 27% e 3%. **É uma frequência do passado, não uma previsão** para a data. As faixas e as taxas ficam em `config/risk_rules.json`.

Quando os campos de risco **não vêm** (o mapa continua como antes): a tabela está vazia, não existe (migração 005 ainda não aplicada), ou a nota mais recente é mais velha que `RISK_MAX_AGE_DAYS` dias (padrão 2). Também não vêm com mais de 4.000 células na área, como o nível de alerta. A resposta do mapa fica em cache até a próxima atualização dos dados do pipeline, então notas novas do job aparecem no próximo ciclo.

Regras do nível no mapa:
- Os dias sem linha em `agregados_diarios` contam como zero, como no backtest. Diferente do `recent`, o mapa não exclui as janelas com dia indisponível. Janelas que começam antes do VIIRS (fevereiro de 2012) não entram.
- **Limite de desempenho:** com mais de 4.000 células de resolução 4 com fogo na área visível, o bloco `alerts` e os campos de alerta não vêm (o mapa continua igual). Na série de 2012 a 2024, a pior semana do Brasil inteiro teve 3.069 células com fogo (P95 de 2.770, mediana de 1.378), então o limite cobre até o pico da temporada. **O tempo da consulta no pico ainda não foi medido no banco**; o resultado fica em cache até o próximo foco sair da janela.
- As taxas são do backtest na série dos arquivos públicos do FIRMS, que reproduz o banco (ganho de +6,1 contra +6,0 do PR #85).

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
  ],
  "alerts": { "data_through": "2026-11-14", "alert_rules_version": "1.1", "priority": [] }
}
```

No modo `points`, o bloco `alerts` vem igual ao do modo `hexagons` (o exemplo acima está resumido).

### Regras

- Só confiança nominal e alta, o mesmo filtro do calendário.
- Cache com a mesma regra da seção "Desempenho": a chave inclui o `updated_at`, então o cache se renova sozinho a cada atualização NRT.
- Erros: `invalid_bbox` (400), `invalid_hours` (400) e `invalid_mode` (400).

### Consulta e desempenho

A consulta filtra **primeiro pelo tempo**, pelo índice parcial `focos_nrt ON focos (datahora_utc) WHERE qualidade = 'NRT'` (migration 003 da frente A), e depois pelo bbox. Os últimos dias são sempre NRT, porque o SP chega meses depois.

**Um satélite só.** O banco tem NRT de 4 satélites olhando os mesmos fogos (últimos 7 dias no banco de teste: NOAA-21 26.196, NOAA-20 24.576, Aqua 5.806, Terra 3.543). Sem o filtro, cada fogo aparece de 2 a 4 vezes no mapa. A consulta usa a mesma regra do satélite do mês dos `agregados` ([pipeline-dados.md](pipeline-dados.md)): um VIIRS por período, nunca a soma. Hoje é o NOAA-20 (`N20`), porque o S-NPP encerrou em 02/11/2026. O satélite vem dessa regra, não fica fixo na consulta. O filtro roda em cima do mesmo índice `focos_nrt`, então o tempo medido abaixo não muda (issue #22).

```sql
SELECT h3, count(*) AS n
FROM focos
WHERE qualidade = 'NRT'
  AND satelite = %s              -- o VIIRS do período atual (hoje 'N20'), nunca a soma
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
{ "status": "ok", "data_version": "2026-11-14T19:48:30Z", "last_month": "2026-11", "updated_at": "2026-11-14T15:00:00Z", "h3_resolution": 6 }
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

## Decisões fechadas (15/11/2026, Weberson, frente B; issue #75)

| # | Ponto | Decisão | Por quê |
| --- | --- | --- | --- |
| 1 | Nível de alerta (Normal / Atenção / Crítico) | A regra da submissão é a `v1` do `alert_rules.json` (piso contínuo de 10 detecções, tendência de 3 dias contra 3 dias, Atenção acima de P75), lida pela API. Validada por teste retroativo (solução A + B) em [validacao-alerta.md](validacao-alerta.md). A área queimada da NASA fica como próximo passo (issue #9) | A escolha pelo critério completo está no PR #62. Ela mede detecções, não área queimada |
| 2 | Anos de referência da anomalia (RF12) | Todos os anos completos da série menos o próprio ano, fixo, independente do intervalo pedido | A anomalia de um mês não muda quando o usuário muda o filtro, e o próprio ano nunca entra no seu normal (o mesmo cuidado do alerta) |
| 3 | Medida da anomalia | **Um só "normal": a mediana dos anos de referência**, no calendário (`months[].anomaly`), no alerta e nos indicadores. O `indicators.latest_complete_year` usa `reference_median` (issue #78) | A média é puxada pelos anos extremos (Pantanal 2020), e dois "normais" diferentes na mesma tela confundem quem decide. O RD06 ("média de vários anos") é lido como "o típico de vários anos" |
