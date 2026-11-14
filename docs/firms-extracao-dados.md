# FIRMS — Possibilidades de extração e dados disponíveis

Levantamento feito em 14/11/2026 no formulário do FIRMS e na documentação da API.

## 1. Dados disponíveis por sensor

| Sensor | Satélite | Resolução | Disponível de | Até | Situação |
|---|---|---|---|---|---|
| MODIS C6.1 | Terra | 1 km | 01/11/2000 | hoje | Ativo, fim de vida próximo |
| MODIS C6.1 | Aqua | 1 km | 04/07/2002 | hoje | Ativo, fim de vida próximo |
| VIIRS C2 | S-NPP | 375 m | 20/01/2012 | 02/11/2026 | **Encerrado** |
| VIIRS C2 | NOAA-20 | 375 m | 01/04/2018 | hoje | Ativo |
| VIIRS C2 | NOAA-21 | 375 m | 01/03/2023 | hoje | Ativo |
| LANDSAT | Landsat 8/9 | 30 m | 20/06/2022 | hoje | Só EUA e Canadá |

Observações:

- No formulário de arquivo, o MODIS vem com Terra e Aqua juntos. A coluna `satellite` separa os dois.
- No arquivo de download, o S-NPP vai de 20/01/2012 a 02/11/2026. A NASA orienta usar NOAA-20 e NOAA-21 daqui para frente.
- Os dados NRT (quase tempo real) são substituídos pelos dados SP (qualidade científica) com uma defasagem de aproximadamente 5 meses.

## 2. Formas de extração

### 2.1 Archive Download (formulário)

URL: https://firms.modaps.eosdis.nasa.gov/download/create.php

- **Acesso:** Earthdata Login ou código por e-mail.
- **Recorte espacial:**
  - World
  - Country
  - Custom Region: desenho no mapa ou coordenadas (Lon, Lat ou Lat, Lon)
  - Protected Area
  - US States, US Dispatch Areas, US GACCs, US National Monuments, US National Parks
  - Canada Provinces/Territories, Canada National Parks
- **Sensores:** MODIS, VIIRS S-NPP, VIIRS NOAA-20, VIIRS NOAA-21, LANDSAT (só EUA).
- **Período:** campos "From" e "To".
- **Formatos:** Shapefile (.shp), CSV (.csv), JSON (.json).
- **Entrega:** o pedido é monitorado e aprovado pela equipe do FIRMS e chega depois, por e-mail ou no painel. Não é instantâneo.
- **Melhor uso:** carga histórica de um país ou região, num período longo.

### 2.2 Resumo anual por país

URL: https://firms.modaps.eosdis.nasa.gov/country/

- ZIPs anuais por sensor, com um CSV por país dentro.
- Download direto, sem fila de aprovação.
- **Melhor uso:** carga histórica rápida por país e ano, alternativa ao formulário.

### 2.3 API (CSV)

URL: https://firms.modaps.eosdis.nasa.gov/api

- **Acesso:** MAP_KEY gratuita, com limite de 5000 transações a cada 10 minutos. Consultas grandes contam como várias transações.
- **Endpoints:**
  - `area`: focos por bounding box, sensor e datas. Formato: `/api/area/csv/[MAP_KEY]/[SOURCE]/[oeste,sul,leste,norte]/[DIAS]/[DATA]`
  - `country`: focos por país, sensor e datas
  - `data_availability`: datas disponíveis de cada fonte SP e NRT
  - `missing_data`: datas sem dados de satélite
  - `kml_fire_footprints`: pegadas dos focos em KML
- **Fontes (`source`):** `MODIS_NRT`, `MODIS_SP`, `VIIRS_SNPP_NRT`, `VIIRS_SNPP_SP`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA20_SP`, `VIIRS_NOAA21_NRT`, `LANDSAT_NRT`.
- **Melhor uso:** job de atualização diária (NRT) e verificação de lacunas. Não serve para a carga histórica.

### 2.4 WMS / WFS e GIBS (visualização)

- WMS do FIRMS: https://firms2.modaps.eosdis.nasa.gov/mapserver/wms-info/ (exige MAP_KEY, atualizado a cada 15 min).
- GIBS (tiles WMTS/WMS, sem autenticação): https://nasa-gibs.github.io/gibs-api-docs/
- **Melhor uso:** camadas visuais no mapa do front. Não entram nos cálculos.

## 3. Colunas dos CSVs de arquivo

`latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type`

| Coluna | Significado | Uso no projeto |
|---|---|---|
| `latitude`, `longitude` | Centro do pixel do foco | Célula H3 |
| `acq_date`, `acq_time` | Data e hora (UTC, HHMM) da passagem | Mês/ano do calendário |
| `satellite` | Terra, Aqua, SNPP, N20, N21 | Separar a fonte na harmonização |
| `instrument` | MODIS ou VIIRS | — |
| `confidence` | MODIS: 0–100. VIIRS: `l` (baixa), `n` (nominal), `h` (alta) | Filtro opcional |
| `frp` | Potência radiativa do fogo (MW) | Indicador extra de intensidade |
| `daynight` | D (dia) ou N (noite) | Harmonização por horário de passagem |
| `type` | 0 = vegetação, 1 = vulcão, 2 = outra fonte estática em terra, 3 = offshore | Manter só `type = 0` |
| `scan`, `track` | Tamanho real do pixel | — |
| `brightness`, `bright_t31` | Temperatura de brilho (K) | — |
| `version` | Versão da coleção | — |

A coluna `type` existe só nos dados de arquivo (SP). Os dados NRT não trazem essa coluna.

## 4. O que já temos baixado

Recorte: Brasil inteiro, de 01/01/2024 a 31/12/2024, dados de arquivo (SP).

| Arquivo | Satélite | Focos no Brasil | Na Amazônia Legal (bbox aprox.) |
|---|---|---|---|
| `fire_archive_M-C61_848018.csv` | Aqua | 319.074 | 242.292 |
| `fire_archive_M-C61_848018.csv` | Terra | 208.820 | 165.440 |
| `fire_archive_SV-C2_848021.csv` | S-NPP | 1.935.740 | 1.524.471 |
| `fire_archive_J1V-C2_848019.csv` | NOAA-20 | 1.988.404 | 1.564.429 |
| `fire_archive_J2V-C2_848020.csv` | NOAA-21 | 1.948.842 | 1.531.634 |

Tamanho: cerca de 160 MB de CSV por sensor VIIRS e 43 MB para o MODIS (2024, Brasil).

O que esses dados mostram:

- S-NPP, NOAA-20 e NOAA-21 têm contagens quase iguais em todos os meses, porque veem os mesmos focos. Usar um VIIRS por período, nunca somar os três.
- Na Amazônia, o VIIRS (S-NPP) detecta cerca de 6,3× mais focos que o MODIS Aqua.
- A forma do calendário é a mesma em todos os sensores, com pico em agosto–outubro e máximo em setembro.

## 5. Proposta de extração

Recorte: **País = Brasil**, em CSV. O recorte da Amazônia é feito no processamento, e o Pantanal fica disponível para a demo.

| Pedido | Sensor | De | Até |
|---|---|---|---|
| 1 | MODIS (Terra + Aqua) | 01/11/2000 | hoje |
| 2 | VIIRS S-NPP | 20/01/2012 | 02/11/2026 |
| 3 | VIIRS NOAA-20 | 01/04/2018 | hoje |

Uso na harmonização:

- **Escala da série: VIIRS (S-NPP).** De fevereiro de 2012 em diante, o calendário mostra a contagem real do VIIRS, sem conversão.
- **2003 a janeiro de 2012:** só o MODIS Aqua, convertido para a escala do VIIRS por um fator Aqua → S-NPP, com faixa de incerteza. O calendário começa em 2003, o primeiro ano completo do Aqua. Somar Terra e Aqua criaria um salto artificial em julho de 2002.
- **Fator Aqua → S-NPP:** por bioma × mês × dia/noite, um cenário por ano de calibração. Os anos saem da validação deixando um ano de fora (2012–2024, ou 2012–2021 se a deriva da órbita do Aqua pesar). 2025 em diante fica fora.
- **NOAA-20:** usado de novembro de 2026 em diante, com fator 1 (tratado como igual ao S-NPP).
- **Atualização:** job NRT a cada 3 h pela API, com `VIIRS_NOAA20_NRT` e `VIIRS_NOAA21_NRT`.
- **Recarga SP mensal:** fora do escopo da submissão.

Regras completas em [importacao-regioes.md](importacao-regioes.md) e [decisoes-harmonizacao.md](decisoes-harmonizacao.md).

## Fontes

- [FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download/)
- [FIRMS API](https://firms.modaps.eosdis.nasa.gov/api)
- [FIRMS WMS](https://firms2.modaps.eosdis.nasa.gov/mapserver/wms-info/)
- [FIRMS no Earthdata](https://www.earthdata.nasa.gov/data/tools/firms)
- [GIBS](https://nasa-gibs.github.io/gibs-api-docs/)
