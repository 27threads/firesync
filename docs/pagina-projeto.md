# Página do projeto no Space Apps (C9)

Texto para colar na página do projeto, campo por campo, em inglês. Os campos vêm do checklist de [requisitos.md](requisitos.md), seção 5. Os números saem de [decisoes-harmonizacao.md](decisoes-harmonizacao.md), do [RFC 0003](rfcs/0003-modelo-risco.md), de [validacao-alerta.md](validacao-alerta.md), de [requisitos.md](requisitos.md) e da tela de Método (`frontend/index.html`). Se um desses números mudar, mude aqui também.

Pendente: o link da demo (D8). Quando o vídeo ou os slides existirem, troque o texto do campo "Link to Project Demo".

---

## Project Name

firesync

## High-Level Project Summary

Fire teams in Brazil can see where satellites detect fire today, but not whether today's activity is normal for that place and season. Answering that needs a long record, and NASA's record comes from two sensor generations that do not agree: VIIRS records about six times more detections than MODIS over the same fires. firesync converts the MODIS Aqua record (2003 to early 2012) to the VIIRS scale with factors calibrated in the 13 years both sensors flew, and joins it with the VIIRS record into one monthly series, with an uncertainty range wherever a month is estimated. Users draw any area in Brazil and see a months × years fire calendar, the seasonal pattern, the highest-fire years, and the last 7 days against the typical level for the same dates. A map of recent detections flags where to look first and shows a 14-day fire risk per area from a model trained only on past data, checked against NASA MCD64A1 burned area. An assistant answers questions in plain language from the same numbers. Every number can be rebuilt from a downloadable audit package.

## Link to Project Demo

PENDING (D8): video of up to 30 seconds or up to 7 slides, not recorded yet.

## Link to Final Project

- Live app: https://firesync.nogranlabs.com.br
- Public API: https://firesync-api.nogranlabs.com.br
- Source code: https://github.com/27threads/firesync

## Detailed Project Description

### The problem

NASA FIRMS shows where fire is detected right now. People who respond to fires also need context: is this much fire normal for this area at this time of year? To answer, you need a record long enough to define "normal". MODIS has flown since the early 2000s, and VIIRS since 2012. VIIRS has 375 m pixels against about 1 km for MODIS, so it sees many more small fires. Putting the raw counts side by side makes 2012 look like a sudden jump in fire that never happened.

### What firesync does

- **Fire calendar.** The user draws an area on the map (polygon or rectangle), picks a region, or types a point and radius, then chooses a period. firesync shows a months × years calendar of fire detections from January 2003 to the latest month, on one scale. Estimated months (MODIS era) are hatched and carry an uncertainty range. Months with a satellite outage are marked as missing data, which is different from zero detections.
- **Seasonal pattern and ranking.** Which months have the most fire, and which years had the most, using complete years only.
- **Now against normal.** The last 7 days and the month to date are compared with the median of the same dates (within ±15 days) in earlier VIIRS years. An alert level (Normal, Attention, Critical) follows rule v1, which is versioned in `config/alert_rules.json`.
- **Recent detections map.** The last 24, 72 or 168 hours as H3 hexagons or points, with an intensity class from fire radiative power.
- **Early warning.** A "Where to look first" list ranks areas of about 1,770 km² (H3 resolution 4) by alert level and by a 14-day fire risk from a trained model. Areas with a high risk enter the list even when there is no fire there now.
- **Ask the data.** A chat assistant answers questions such as "is the Pantanal above normal this week?" in the language of the question. It does not write numbers itself: it calls the same API functions as the screen (calendar, recent window, map, risk) and every figure in the answer is checked against what those functions returned, with the sources shown.
- **Downloads.** CSV tables, a PNG of the calendar, and an audit ZIP with the raw counts by cell, the conversion factors of every calibration scenario, the formula and the filters used, so anyone can recompute the calendar.

### How it works

1. **Data.** All NASA FIRMS detections for Brazil from November 2000: MODIS Collection 6.1 (Terra and Aqua) and VIIRS Collection 2 (S-NPP, NOAA-20, NOAA-21), from the yearly country files (standard processing) and the FIRMS API (near real time) for the most recent days. Only nominal and high-confidence vegetation fires (`type = 0`) are counted.
2. **Harmonization (team method).** The series uses the VIIRS scale. Only Aqua is used on the MODIS side, so the calendar starts in January 2003. In the overlap years (2012 to 2024), we count Aqua and S-NPP detections on an H3 grid and compute one factor per biome × month × day or night overpass for each year. Each calibration year is one scenario (1,860 factors in total, 6 IBGE biomes). A MODIS-era month is the median of the 13 scenarios, with a 5th to 95th percentile range. From February 2012 the record is observed by VIIRS with no conversion: S-NPP until October 2026, NOAA-20 from November 2026.
3. **Area queries.** Counts are pre-aggregated by H3 cell, month, satellite and day or night in PostgreSQL with PostGIS. The API sums the cells of the drawn area, applies each scenario's factors and only then takes the median and the range, because the sum of cell percentiles is not the percentile of the sum.
4. **Risk model.** A gradient boosting model with 10 variables, all from daily VIIRS detection counts per cell (fire in the last 7, 14 and 30 days, trend, fire in neighbouring cells, the same season in earlier years, week of the year and position). It gives each cell a probability of relevant fire (10 or more VIIRS detections) in the next 14 days, shown in four tiers. It runs as a separate job and writes scores to the database; the API only reads them.

### Does it work? What we measured

- **Calibration, leave-one-year-out.** For each year from 2012 to 2024, we built the factors without that year, converted its Aqua counts and compared them with real S-NPP counts. Weighted yearly error in the Amazon: 5.7% on average in 2012–2021 and 6.4% in 2022–2024 (from 2.4% in 2017 to 12.6% in 2020). The pre-set criterion for dropping the years affected by Aqua's orbit drift (1.5× more error) was not met, so all 13 years were kept.
- **Uncertainty range, measured.** The real value fell inside the 5th–95th percentile range in 0.76 to 0.80 of the months in five biomes and 0.68 in the Pampa. During each biome's fire season it reached 0.87 in the Amazon, 0.86 in the Pantanal and 0.83 in the Caatinga.
- **Independent check against INPE.** Against INPE's Programa Queimadas series (2003–2025), the harmonized series has a monthly correlation of 0.94 to 0.99 in all six biomes. The 2012 sensor switch creates no artificial jump in the Amazon (−0.6%) and stays within about 7% in the Cerrado, Caatinga and Pantanal.
- **Why the sensors disagree.** In 2024, in areas MODIS was observing, MODIS also saw 15–18% of the VIIRS fires under 2 MW and 71–87% of those of 25 MW or more. A model trained on 2019–2021 reproduced this pattern in 2022–2024.
- **Alert rule v1, backtested 2013–2024** on H3 resolution 4 cells: after a Critical week, the next 14 days had unusually high VIIRS detections 26.6% of the time, 6.0 points more than a simple persistence rule at the same alert frequency (95% interval 4.1 to 8.0), with a gain in all 12 years. In the Pantanal in 2020, rule v1 reached Critical 40 days before the Mato Grosso do Sul emergency decree. A trained model beat v1 by only 0.9 points, so we kept the simple rule that anyone can check.
- **14-day risk model**, tested on 2021–2024 and trained only on earlier years. When it flags a cell (probability of 50% or more), relevant fire followed in 78% of cases in the Amazon and 76% in Brazil (precision), and it flagged 74% of the Amazon cells that had relevant fire (66% in Brazil). In the map tiers, relevant fire followed in 82% (very high), 46% (high), 27% (medium) and 3% (lower) of past cases. On the same question, it ranked areas better than INPE's official fire-risk index in every year: 59–64% of its top 10% areas had relevant fire, against 25–31% for the index, which measures how flammable the vegetation is, not where detections will occur.
- **14-day risk map against NASA burned area.** Because the model learns from VIIRS, we checked it with an independent NASA product, MODIS burned area MCD64A1 v061. For every Sunday from 2021 to 2024, the model was trained only on earlier years and scored the 2,128 Amazon cells (about 440,000 predictions); both pass criteria were fixed before the run. Burned area fell tier by tier in all four years: the very high tier was 11% of the predictions and held 75.5% of all burned area. A place that burned got a higher score than one that did not in about 9 of 10 pairs (AUC 0.898, 0.880 to 0.904 by year, criterion 0.80). 69% of the places that burned were flagged high or very high, and this is a floor: only 37% of the weeks with 10 or more VIIRS detections have a mapped scar of 1 km² or more.
- **Speed**, measured on the test database: a 100 × 100 km calendar in 2–9 ms, the whole Amazon in about 0.8 s, recent detections in 19 ms.

### Limits we state on screen

- The conversion assumes the ratio between the sensors in 2003–2011 was similar to 2012–2024. This cannot be tested, because there is no VIIRS before 2012.
- In exceptional fire years (2020 and 2024 in the Amazon) the estimate errs more and the range covers less. In the Pampa the estimate tends to be low.
- firesync counts detections, not fires and not burned area. One large fire produces many detections.
- The alert levels and risk tiers are frequencies from the past, not forecasts. 52% of the high-detection periods followed a week rated Normal. The risk model uses no weather forecast, has few data for the Pantanal, and covers less outside the fire season (62% in the Amazon).
- Calibrated for Brazil's biomes. Other regions are data in the database, not code, but they need their own calibration.

### Benefits

- One question answered in seconds for fire brigades, civil defense, land managers and researchers: is this normal here, for this time of year, and where should brigades be positioned for the next 14 days?
- In the Amazon (2021–2024), our model warned of 51 in every 100 significant fire outbreaks, usually 10 days ahead (49% still arrive without warning at the 50% threshold). Brigades cut burned area by 12% in the Cerrado. In a year like 2024 (June–August), that could mean about 290,000 hectares and 3.8 million tonnes of CO₂ less in the Amazon. A hypothesis to test in a pilot.
- 24 years of NASA data from two sensors read as one series, with the uncertainty shown instead of hidden.
- Transparent: versioned alert rule, measured (not promised) uncertainty, and an audit package for every query.
- Open source, no login, works on desktop and mobile, interface in English.

### Tools and languages

- **Data pipeline:** Python (pandas, PyArrow, GeoPandas, pyogrio, Shapely, h3, psycopg, scikit-learn).
- **Database:** PostgreSQL 16 with PostGIS 3.4, Uber H3 grid.
- **API:** Python, FastAPI and Uvicorn, hexagonal architecture.
- **Front end:** TypeScript, React, Vite, Leaflet with Leaflet-Geoman, D3 (d3-scale, d3-scale-chromatic), GSAP, three.js, Archivo typeface.
- **Assistant:** tool calling over the API's use cases, through OpenAI-compatible chat completion APIs with a fallback chain of providers.
- **Tests and delivery:** pytest, Vitest, Testing Library, Playwright user journeys, GitHub Actions, Docker Compose, Cloudflare Workers and Cloudflare Tunnel.
- **AI disclosure:** The harmonization method, alert rule, risk model design and pass/fail criteria are the team's; AI coding assistants (Claude Code, OpenAI Codex, Antigravity, Lovable) were used to implement and test code and documents, documented file by file in the [README "Uso de IA" table](https://github.com/27threads/firesync#uso-de-ia).

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
- Opening animation prototype: built with Lovable (TanStack Start), then ported to the React front end.

## Use of Super Intelligence

The idea and the method are the team's. The choice of the VIIRS scale, the biome × month × day/night factor, the calibration years and the 1.5× criterion, the 5th–95th percentile range, the alert rule, the risk model's question, target and variables, and every pass/fail criterion were decided by team members and fixed before the runs. These decisions are recorded, with who made them, in the repository documents.

We used AI coding assistants to write and review code and documents from those decisions:

- **Claude Code** (Anthropic; Claude Opus, Sonnet and Fable models): data pipeline, calibration and validation scripts, risk model job, database schema, front-end interface and method screen, deployment configuration, tests, and drafting of documents, including this page.
- **OpenAI Codex**: API domain, ports and adapters, HTTP routes, tests and documentation updates.
- **Antigravity**: front-end area selection, recent detections layer, API integration and downloads.
- **Lovable**: the opening animation prototype, later ported to the React front end.

The app itself also uses a language model at run time: the chat assistant. It only chooses which API function to call and words the answer; the numbers come from the API and are checked before the answer is shown.

Code was written test-first where possible, and every change entered through a pull request with automated tests, reviewed by the team. The full list of AI-assisted parts, file by file and with the tool used, is in the "Uso de IA" table of the repository README: https://github.com/27threads/firesync#uso-de-ia
