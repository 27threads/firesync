# Página do projeto no Space Apps (C9)

Texto para colar na página do projeto, campo por campo, em inglês. Os campos vêm do checklist de [requisitos.md](requisitos.md), seção 5. Os números saem de [decisoes-harmonizacao.md](decisoes-harmonizacao.md), do [RFC 0003](rfcs/0003-modelo-risco.md), de [validacao-alerta.md](validacao-alerta.md), de [requisitos.md](requisitos.md) e da tela de Método (`frontend/index.html`). Se um desses números mudar, mude aqui também.

Equipe no Space Apps: **27 Threads** (a página do formulário aparece traduzida como "27 fios" quando o navegador traduz). Projeto: **Firesync**.

Campos do formulário (confirmados na página de submissão em 15/11): Resumo (até 1.500 caracteres, sugestão de 50 a 200 palavras), Demonstração (vídeo de **até 30 s** ou **até 7 slides**, link público), Projeto (um link público), Detalhes (editor de texto sem limite, seis perguntas), Uso da Superinteligência (lista de seleção, não é texto livre; não é visto pelos avaliadores), Dados da NASA e Parceiro da Agência Espacial e Outros Dados (pares "Texto do link" e "URL do link"), e as duas caixas de verificação.

Pendente: o link da demo (D8). Quando o vídeo ou os slides existirem, troque o texto do campo "Link to Project Demo".

---

## Project Name

firesync

## High-Level Project Summary

(Field "Resumo", up to 1,500 characters; the form asks what we developed, how it addresses the challenge and why it matters, in 50 to 200 words. This text has 1154 characters and 200 words.)

firesync is a web platform that turns NASA fire data into decisions for fire commanders and crews. It shows where hot spots are burning now, whether that is normal for the place and time of year, and which areas carry the highest fire risk in the next 14 days.

It addresses the challenge by joining two sensor records into one. VIIRS records about six times more detections than MODIS, so we convert MODIS Aqua to the VIIRS scale with factors calibrated in the 13 years both sensors flew. The result is a consistent 24-year series, with estimated months marked and their uncertainty range available. A model trained only on past data estimates the 14-day risk per area: tested on the Amazon (2021-2024), it warned of 51 in 100 significant fire outbreaks, usually 10 days ahead.

It matters because commanders decide with little time. Knowing early where fire is likely can help place crews before it spreads. If early warning helped Amazon crews cut burned area as Cerrado brigades did (12%), that could mean about 290,000 hectares (710,000 acres) and 3.8 million tonnes of CO2 less in a year like 2024 (June to August): a hypothesis to test in a pilot.

## Link to Project Demo

PENDING (D8): video of up to 30 seconds or up to 7 slides, not recorded yet.

## Link to Final Project

- Live app: https://firesync.nogranlabs.com.br
- Public API: https://firesync-api.nogranlabs.com.br
- Source code: https://github.com/27threads/firesync

## Detailed Project Description

(Field "Detalhes do projeto", no character limit. It follows the six questions on the form: what it does and how it works, benefits, intended impact, tools, the creative aspect, and the factors the team considered.)

### What it does and how it works

firesync answers one question for the people who decide where to send fire crews: **where is fire burning now, is that normal for this place and time of year, and where is it likely to burn next?**

- **Fire now.** A map of the last 24, 72 or 168 hours of NASA hot spots, as H3 hexagons (about 1,770 km² each) or points, with the intensity class of each detection. An icon marks the areas that are above the usual for the season (Attention and Critical).
- **Is it normal?** The last 7 days and the month to date are compared with the median of the same dates (within ±15 days) in earlier VIIRS years. The alert level (Normal, Attention, Critical) follows rule v1, versioned in `config/alert_rules.json`.
- **Where next.** A 14-day risk for every area, in four tiers (very high, high, medium, lower). The "Where to look first" list ranks areas by risk, and high-risk areas enter the list even when there is no fire there now.
- **24-year calendar.** The user draws an area (polygon or rectangle), picks one of the six biome regions, or types a point and radius, and sees a months × years calendar of fire detections from January 2003 on one scale. Estimated months (MODIS era) are hatched and carry an uncertainty range. A month with a satellite outage is shown as missing data, which is different from zero.
- **Ask the data.** A chat assistant answers questions such as "is the Pantanal above normal this week?" in the language of the question. It does not write numbers itself: it calls the same API functions as the screen (calendar, recent window, map, risk) and every figure in the answer is checked against what those functions returned, with the sources shown.
- **Downloads.** CSV tables, a PNG of the calendar and an **audit package** (ZIP) with the raw counts by cell, the conversion factors of every scenario, the formula and the filters, so anyone can rebuild the calendar.

**How it works**

1. **Data.** NASA FIRMS active fire detections for Brazil since November 2000: MODIS Collection 6.1 (Terra and Aqua) and VIIRS 375 m Collection 2 (S-NPP, NOAA-20, NOAA-21), from the yearly country files and the near-real-time API. Only nominal and high-confidence vegetation fires are counted.
2. **Harmonization.** VIIRS records about six times more detections than MODIS over the same fires, so the raw counts cannot be joined (2012 would look like a jump in fire). We use the VIIRS scale. Only Aqua is used on the MODIS side. In the 13 overlap years (2012 to 2024) we count Aqua and S-NPP on an H3 grid and compute one factor per biome × month × day or night pass for each year: 1,860 factors in six IBGE biomes. A MODIS-era month is the median of the 13 scenarios, with a 5th to 95th percentile range.
3. **Area queries.** Counts are pre-aggregated by H3 cell, month, satellite and day or night in PostgreSQL with PostGIS. The API sums the cells of the drawn area, applies each scenario's factors and only then takes the median and the range, because the sum of cell percentiles is not the percentile of the sum.
4. **Risk model.** A gradient boosting model with 10 variables, all from daily VIIRS detection counts per cell (fire in the last 7, 14 and 30 days, trend, neighbouring cells, the same season in earlier years, week of the year, position). It estimates the probability of significant fire (10 or more VIIRS detections) in the next 14 days. It was trained only on earlier years and tested year by year. A separate job writes the scores to the database, and the API only reads them.

### Benefits

- **A decision aid for fire commanders and crews:** which areas to look at first today, and where to prepare resources in the next 14 days.
- **Context, not just a map.** Today's fire is shown against what is normal for the place and the season, with 24 years of NASA data read as one series.
- **Honest numbers.** Estimated months are marked and their uncertainty range is available, the alert rule is versioned, and every number can be rebuilt from the audit package.
- **Open and easy to reach:** open source, no login, works on desktop and mobile, in English, with colour scales that are readable with colour-vision deficiency.

### Intended impact

**What we measured** (Amazon, 2021 to 2024, a model trained each year only on earlier years):

- It **warned of 51 in every 100** starts of significant fire (10 or more VIIRS detections in 14 days). Of those, 42 were warned **3 days or more** ahead and 33 **7 days or more** ahead; among the warned, the median lead time was **10 days**. 49 in every 100 still arrive without a warning.
- When it flags an area (probability of 50% or more), significant fire followed in **78%** of cases, and it flagged **74%** of the areas that had significant fire (in Brazil: 76% and 66%).
- Looking only at the 20% of areas with the highest score each week, a brigade covers **66%** of the significant fire (top 10% of areas: 42%; a random choice captures only as much as the share of areas chosen).
- **Independent check with NASA burned area (MCD64A1):** the "very high" tier is 11% of the predictions and holds 75.5% of all the area burned in the following 14 days. 69% of the places that burned had been flagged high or very high. The score separates burned from unburned places with an AUC of 0.898, between 0.880 and 0.904 in each year. This hit rate is a floor: MCD64A1 misses small burns and pixels under cloud or smoke.

**What we estimate as a scenario, not as a result.** Brigades in conservation units of the Cerrado reduced burned area by about 12% (Oliveira et al., via Aliança da Terra and Embrapa). The Amazon burned about 2.4 million hectares from June to August 2024, an extreme drought year (IPAM). If early warning helped Amazon brigades do the same, **that could mean about 290,000 hectares (710,000 acres) less burned area and about 3.8 million tonnes of CO2 less** in a year like 2024 (288,000 ha × 13.1 t CO2 per hectare, from the same IPAM figures). This assumes that the Cerrado effect also holds in the Amazon, that warning ahead makes brigades more effective (the study measures having brigades, not having a warning), and that an average year would give less. It is a hypothesis to test in a pilot with a fire brigade.

### Tools, languages, hardware and software

- **Data pipeline and models:** Python (pandas, PyArrow, GeoPandas, pyogrio, Shapely, h3, psycopg, scikit-learn).
- **Database:** PostgreSQL 16 with PostGIS 3.4 and the Uber H3 grid.
- **API:** Python, FastAPI and Uvicorn, in a hexagonal architecture.
- **Front end:** TypeScript, React, Vite, Leaflet with Leaflet-Geoman, D3 (d3-scale, d3-scale-chromatic), GSAP, three.js for the opening globe, Archivo typeface.
- **Assistant:** tool calling over the API's use cases, through OpenAI-compatible chat completion APIs with a fallback chain of providers.
- **Tests and delivery:** pytest, Vitest, Testing Library, Playwright user journeys, GitHub Actions, Docker Compose, Cloudflare Workers and Cloudflare Tunnel.
- **Hardware:** no special hardware. The site is static and the API and jobs run on one small virtual server.

### The creative aspect

- **Joining two sensors without hiding the doubt.** Instead of hiding the 2012 sensor switch, firesync converts MODIS to the VIIRS scale with 13 calibration scenarios, hatches the estimated months on the calendar and gives each one an uncertainty range. The opening of the site shows the MODIS-to-VIIRS band folding into the calendar.
- **"Is this fire normal?"** Today's fire is compared with the same dates in earlier years, in plain language, with a verdict in one sentence.
- **Early warning for places with no fire yet.** The risk list brings areas to the top before the first detection.
- **Everything can be rebuilt.** A versioned alert rule and an audit package for every query, so a judge or a scientist can recompute the numbers.
- **A descent from the planet to the decision.** The opening takes the user from the globe, with the Aqua and Suomi NPP satellites in orbit, down to a full-screen map with the tools of a commander.

### Factors the team considered

- **Detections are not fires and not burned area.** One large fire produces many detections. We count detections, and say so on screen.
- **Risk is an estimate from past cases, not a guarantee.** 52% of the high-detection periods followed a week rated Normal, and 49 in every 100 starts of significant fire still arrive without a warning. The risk model uses only VIIRS detection counts: no weather forecast. NASA POWER weather data and more MODIS history were tested and did not improve it under criteria fixed before the runs, so they are not in the product.
- **Test years.** The risk model was tested on 2021 to 2024. 2025 and 2026 have not yet been tested out of sample.
- **Where it is weak.** The Pantanal has few areas and an anomalous 2020, so its results carry a warning. The model covers less outside the fire season (62% in the Amazon).
- **The conversion assumes** the sensor ratio of 2003 to 2011 was similar to 2012 to 2024, which cannot be tested. In exceptional years (2020 and 2024 in the Amazon) the estimate errs more.
- **Sensor change.** S-NPP is the VIIRS source until October 2026 and NOAA-20 from November 2026, and the risk model was tested for the switch with no harm.
- **Independent reference.** The harmonized series was compared with INPE's Programa Queimadas (monthly correlation of 0.94 to 0.99 in all six biomes) and the risk model with INPE's fire-risk index.
- **People under pressure.** Large touch targets, shape and text besides colour, a colour scale readable with colour-vision deficiency, and no login.
- **The virtual assistant stays inside the data.** It answers only with figures returned by our own API and shows its sources.
- **A decision aid, not a decision.** The tool ranks where to look. It does not replace field information, wind, or the judgment of the commander.

### How we used AI tools

The idea, the method and every pass or fail criterion are the team's, and were fixed before the runs. We used AI coding assistants (Claude Code, OpenAI Codex, Antigravity and Lovable) to write and review **code and documents** from those decisions, test-first where possible, and every change entered through a pull request with automated tests. The AI-assisted parts, file by file, are in the "Uso de IA" table of the repository README. **No image, video or audio in the project or in the demo was generated by AI.** The optional virtual assistant in the site calls a language model at run time and gets every figure in its answers from our own API.

## NASA Data

- **NASA FIRMS (Fire Information for Resource Management System)**, the core of the product. Every number in the calendar, the alert, the map and the risk model comes from FIRMS active fire detections for Brazil:
  - **MODIS Collection 6.1** (Aqua, and Terra in the stored history), standard processing yearly country files from November 2000. Aqua is converted to the VIIRS scale for January 2003 to January 2012.
  - **VIIRS 375 m Collection 2**: S-NPP (observed record from February 2012 and calibration reference for 2012–2024), NOAA-20 (current record from November 2026) and NOAA-21 (backup in near real time).
  - **FIRMS API**, near real time, for the current month and the recent detections map.
  - Data from LANCE FIRMS, operated by NASA's Earth Science Data and Information System (ESDIS). Credit is shown in the app.
- **NASA MCD64A1 v061 (MODIS Burned Area, 500 m)**, from NASA LP DAAC: independent check of the 14-day risk map, 2021–2024 in the Amazon. Not used to compute any number in the app. https://lpdaac.usgs.gov/products/mcd64a1v061/
- **NASA GIBS (Global Imagery Browse Services)**, base maps: VIIRS Black Marble (2016), Blue Marble Next Generation and Coastlines, through the WMTS endpoint. The opening globe texture uses the GIBS layer BlueMarble_ShadedRelief_Bathymetry.
- **NASA POWER** (daily rainfall, maximum temperature, humidity and wind) was tested as input to the risk models. It did not improve them under criteria fixed before the runs, so it is not in the product. The result is reported in the method notes.
- **NASA 3D Resources**: 3D models of Aqua and Suomi NPP, used in the opening animation of the app.

## Space Agency Partner Data and Other References

### Space agency partner data

- **Brazilian Space Agency (AEB) / INPE** (Instituto Nacional de Pesquisas Espaciais, Brazil), Programa Queimadas: monthly fire series for Brazil's biomes, used as the independent reference to check the harmonized series (2003–2025). https://data.inpe.br/queimadas/
- **Brazilian Space Agency (AEB) / INPE**, Fire Risk index (Risco de Fogo), version 2.2, daily NetCDF files, 2021–2024: external benchmark for the 14-day risk model. Not used in the product.

### Other data

- **IBGE**, Biomas do Brasil, 1:250,000: boundaries of the six biomes used for calibration and regions. https://www.ibge.gov.br/
- **NOAA Climate Prediction Center**, Oceanic Niño Index (ONI): tested as input to the risk model, not used in the product. https://www.cpc.ncep.noaa.gov/
- **Government of Mato Grosso do Sul**, Decree 080/2020, environmental emergency in the Pantanal (24 July 2020): historical example for the alert. https://www.semadesc.ms.gov.br/?p=108045
- **OpenStreetMap contributors**: coastline data in the GIBS Coastlines layer. https://www.openstreetmap.org/copyright
- **datasets/geo-countries** (from Natural Earth): country boundaries in the opening animation. https://github.com/datasets/geo-countries

### Scientific references

- Nuñez, J. R., Anderton, C. R., Renslow, R. S. (2018). Optimizing colormaps with consideration for color vision deficiency to enable accurate interpretation of scientific data. PLOS ONE 13(7): e0199239. (cividis color scale)
- IPAM (Instituto de Pesquisa Ambiental da Amazônia) (2024). CO₂ emissions from fires in the Amazon grow by 60% (June–August 2024 burned area and emissions reference). https://ipam.org.br/co2-emissions-from-fires-in-the-amazon-grow-by-60/
- Sano, E. E. et al. / Oliveira et al. (Embrapa / Aliança da Terra). Implementation of fire policies in Brazil (reference for 12% burned-area reduction by brigades in the Cerrado). https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1136281/1/Sano-implementation-of-fire-policies-in-Brazil.pdf · https://www.aliancadaterra.org/_files/ugd/18a265_69d4f963acd24c3ab3f32f3a4b711f7e.pdf
- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/
- NASA GIBS: https://www.earthdata.nasa.gov/gibs
- NASA POWER: https://power.larc.nasa.gov/
- NASA 3D Resources: https://github.com/nasa/NASA-3D-Resources
- H3 hexagonal grid (Uber): https://h3geo.org/

### Software and libraries (all open source)

- Front end: React, React DOM, Vite, TypeScript, Leaflet, Leaflet-Geoman (free), D3 (d3-scale, d3-scale-chromatic), GSAP, three.js, Fontsource Archivo (SIL Open Font License).
- Front-end tests: Vitest, Testing Library (React, jest-dom), jsdom, Playwright.
- API: FastAPI, Uvicorn, psycopg, h3, Shapely, pyproj.
- Data pipeline and models: pandas, PyArrow, GeoPandas, pyogrio, Shapely, h3, psycopg, scikit-learn (HistGradientBoostingClassifier).
- Tests and quality: pytest, pytest-cov, httpx, Ruff, Vulture.
- Database and infrastructure: PostgreSQL, PostGIS (`postgis/postgis` image), Docker Compose, Cloudflare Workers, Cloudflare Tunnel, GitHub Actions.
- Opening animation prototype (`lovable/` folder): built with Lovable (TanStack Start).

## Use of Super Intelligence

The idea and the method are the team's. The choice of the VIIRS scale, the biome × month × day/night factor, the calibration years and the 1.5× criterion, the 5th–95th percentile range, the alert rule, the risk model's question, target and variables, and every pass/fail criterion were decided by team members and fixed before the runs. These decisions are recorded, with who made them, in the repository documents.

We used AI coding assistants to write and review code and documents from those decisions:

- **Claude Code** (Anthropic; Claude Opus, Sonnet and Fable models): data pipeline, calibration and validation scripts, risk model job, database schema, front-end interface and method screen, deployment configuration, tests, and drafting of documents, including this page.
- **OpenAI Codex**: API domain, ports and adapters, HTTP routes, tests and documentation updates.
- **Antigravity**: front-end area selection, recent detections layer, API integration and downloads.
- **Lovable**: the opening animation prototype in the `lovable/` folder.

The app itself also uses a language model at run time: the chat assistant. It only chooses which API function to call and words the answer; the numbers come from the API and are checked before the answer is shown.

Code was written test-first where possible, and every change entered through a pull request with automated tests, reviewed by the team. The full list of AI-assisted parts, file by file and with the tool used, is in the "Uso de IA" table of the repository README: https://github.com/27threads/firesync#uso-de-ia

No image, video or audio in the project or in the demo was generated by AI. The optional virtual assistant in the site calls a language model at run time and gets every figure in its answers from our own API.

---

## Link pairs for the form ("Texto do link" and "URL do link")

### Field "Dados da NASA"

| Texto do link | URL do link |
| --- | --- |
| NASA FIRMS (Fire Information for Resource Management System) | https://firms.modaps.eosdis.nasa.gov/ |
| NASA FIRMS active fire data: MODIS Collection 6.1 and VIIRS 375 m Collection 2 | https://firms.modaps.eosdis.nasa.gov/active_fire/ |
| NASA GIBS (Global Imagery Browse Services): Blue Marble, Black Marble and Coastlines | https://www.earthdata.nasa.gov/gibs |
| NASA 3D Resources: Aqua and Suomi NPP models | https://github.com/nasa/NASA-3D-Resources |
| NASA MCD64A1 burned area (independent check of the risk model) | https://lpdaac.usgs.gov/products/mcd64a1v061/ |
| NASA POWER (tested as model input, not in the product) | https://power.larc.nasa.gov/ |

### Field "Parceiro da Agência Espacial e Outros Dados"

Data and studies:

| Texto do link | URL do link |
| --- | --- |
| INPE, Programa Queimadas (monthly fire series by biome, independent reference) | https://data.inpe.br/queimadas/ |
| INPE, Risco de Fogo v2.2 (benchmark of the 14-day risk model) | https://data.inpe.br/queimadas/ |
| IBGE, Biomas do Brasil 1:250,000 | https://www.ibge.gov.br/ |
| NOAA Climate Prediction Center, Oceanic Niño Index (tested, not in the product) | https://www.cpc.ncep.noaa.gov/ |
| Government of Mato Grosso do Sul, Decree 080/2020 (Pantanal emergency, 2020) | https://www.semadesc.ms.gov.br/?p=108045 |
| OpenStreetMap contributors (coastline data in the GIBS layer) | https://www.openstreetmap.org/copyright |
| datasets/geo-countries, from Natural Earth (country boundaries in the opening globe) | https://github.com/datasets/geo-countries |
| Oliveira et al., brigades in Cerrado conservation units, via Aliança da Terra (source of the 12%) | https://www.aliancadaterra.org/_files/ugd/18a265_69d4f963acd24c3ab3f32f3a4b711f7e.pdf |
| Sano (Embrapa), implementation of fire policies in Brazil (source of the 12%) | https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1136281/1/Sano-implementation-of-fire-policies-in-Brazil.pdf |
| IPAM, CO2 emissions from fires in the Amazon (2.4 million ha and 31.5 Mt CO2, June to August 2024) | https://ipam.org.br/co2-emissions-from-fires-in-the-amazon-grow-by-60/ |
| Nuñez, Anderton and Renslow (2018), cividis colour scale, PLOS ONE | https://doi.org/10.1371/journal.pone.0199239 |
| H3 hexagonal grid (Uber) | https://h3geo.org/ |

Software, fonts and libraries (all open source):

| Texto do link | URL do link |
| --- | --- |
| React | https://react.dev/ |
| Vite | https://vite.dev/ |
| Leaflet | https://leafletjs.com/ |
| Leaflet-Geoman | https://github.com/geoman-io/leaflet-geoman |
| D3 (d3-scale, d3-scale-chromatic) | https://d3js.org/ |
| GSAP | https://gsap.com/ |
| three.js | https://threejs.org/ |
| Fontsource Archivo (SIL Open Font License) | https://fontsource.org/fonts/archivo |
| Vitest, Testing Library and Playwright | https://vitest.dev/ |
| FastAPI and Uvicorn | https://fastapi.tiangolo.com/ |
| scikit-learn | https://scikit-learn.org/ |
| pandas, PyArrow, GeoPandas, Shapely, pyproj | https://pandas.pydata.org/ |
| PostgreSQL and PostGIS | https://postgis.net/ |
| Docker Compose, Cloudflare Workers and Cloudflare Tunnel | https://developers.cloudflare.com/workers/ |
| TanStack Start (the Lovable prototype in the lovable/ folder) | https://tanstack.com/start |
| Source code of firesync | https://github.com/27threads/firesync |
