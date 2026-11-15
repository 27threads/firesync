# Prompt do backend — partes 4 a 6 (frente C)

Nov 14, 2026 · frente C · **rascunho, revisão e execução de `@theonlyrafael`**

Prompt autocontido para concluir as partes 4, 5 e 6 da API do firesync (tarefas **C1** e **C3–C6**) em um contexto limpo, em cima do que já entrou na `main` no PR #41 (partes 1 a 3).

---

## O prompt

Você vai implementar as **partes 4, 5 e 6** do backend (`backend/`) do projeto **firesync** para concluir as tarefas **C1, C3, C4, C5 e C6**.

### 1. Leitura obrigatória antes de escrever código

Leia estes arquivos na raiz do repositório antes de propor ou editar qualquer arquivo. Os documentos são a fonte de verdade:

1. [CLAUDE.md](../CLAUDE.md) — regras do repositório, commits sem menção a IA, idioma (código/API em inglês, documentação e commits em português) e fluxo TDD.
2. [docs/arquitetura.md](arquitetura.md) — ponto 4 (**Python 3.12 + FastAPI**, com `psycopg` 3) e regras de dependência entre camadas da arquitetura hexagonal (`domain`, `application`, `ports`, `adapters/inbound/http`, `adapters/outbound/postgres`, `adapters/outbound/config_file`).
3. [docs/api.md](api.md) e [docs/api-exemplo.json](api-exemplo.json) — contrato completo dos 5 endpoints sob `/api/v1`, formatos de pedido e resposta, regras de cálculo, pacote de auditoria ZIP, códigos de erro HTTP, cache em memória (`ETag` + LRU com `updated_at`), rate limit (`429` + `Retry-After`) e verificação no startup (`config.h3_resolucao`).
4. [docs/banco.md](banco.md), [docs/importacao-regioes.md](importacao-regioes.md) e `data-pipeline/migrations/001_inicial.sql` a `004_agregados_diarios.sql` — schema do PostgreSQL/PostGIS (`focos`, `agregados`, `agregados_diarios`, `regioes`, `celula_regiao`, `cobertura`, `dias_sem_dados`, `fatores_harmonizacao`, `config`).
5. [config/alert_rules.json](../config/alert_rules.json) — parâmetros versionados de baseline, níveis de alerta e limites de classe de intensidade.
6. [backend/README.md](../backend/README.md), [backend/pyproject.toml](../backend/pyproject.toml), [backend/requirements-dev.txt](../backend/requirements-dev.txt), [backend/vulture_whitelist.py](../backend/vulture_whitelist.py) e todo o código existente em `backend/src/` e `backend/tests/`.

### 2. O que já está pronto na `main` (partes 1 a 3 — PR #41)

- `backend/src/domain/`: `Area`, `Month`, `HistorySnapshot`, `CalendarError`, seleção espacial H3 (`spatial.py`), percentis/estatísticas (`statistics.py`) e cálculo histórico mensal/anual/sazonalidade (`history.py`).
- `backend/src/ports/history.py` e `backend/src/adapters/outbound/postgres/history.py`: `HistoryRepository` e `PostgresHistoryRepository` lendo o snapshot histórico em transação `REPEATABLE READ READ ONLY`.
- `backend/src/application/calendar.py`: `CalendarService.calculate()` retornando `meta`, `area`, `coverage`, `months`, `years`, `seasonality` e indicadores históricos (`total_detections`, `latest_complete_year`).

### 3. O que falta implementar (partes 4 a 6)

#### Parte 4 — Domínio e caso de uso da janela recente, intensidade e alerta (`recent` + `alert_rules.json`)

1. **Domínio (`backend/src/domain/`):**
   - Implemente `backend/src/domain/intensity.py` com `intensity_class(frp, sensor, confianca, intensity_rules)` seguindo `docs/api.md` e `config/alert_rules.json`:
     - `low`: FRP `< 5` MW
     - `medium`: FRP de `5` a `< 25` MW
     - `high`: FRP `>= 25` MW, ou sensor `"VIIRS"` com `confianca in ("alta", "high")` (pixel saturado; no MODIS confiança alta não indica saturação).
   - Implemente `backend/src/domain/alert.py` com `alert_level(agora, mediana, p75, ultimos, anteriores, alert_rules)`:
     - `critical`: quando `agora >= min_ratio_to_median * mediana` e tendência de alta nos últimos `trend_days` (`sum(ultimos) > sum(anteriores)` ou conforme os casos de `test_dominio_spec.py`).
     - `attention`: quando acima do `p75` (`agora > p75`).
     - `normal`: nos demais casos.
   - Implemente `backend/src/domain/windows.py` com `reference_windows(ref_date, window_days=7, neighbor_days=15, years=...)`:
     - Gera a lista de tuplas `(start_date, end_date)` de tamanho `window_days` (`(end_date - start_date).days == window_days - 1`) para cada deslocamento de `-neighbor_days` a `+neighbor_days` em cada ano de `years`, tratando `29/02` em ano comum como `28/02`.
   - Remova o marcador `@TDD` (`pytest.mark.xfail(strict=True)`) dos 4 testes em `backend/tests/domain/test_dominio_spec.py` e garanta que todos passem.
2. **Adaptador de configuração (`backend/src/adapters/outbound/config_file/`):**
   - Porta em `backend/src/ports/` e adaptador em `backend/src/adapters/outbound/config_file/` para ler e validar `config/alert_rules.json`.
3. **Janela recente no `CalendarService` (`recent` e `indicators.last_7_days_vs_typical_pct`):**
   - Quando `coverage.status != "none"`, componha o bloco `recent` (`data_through`, `last_7_days`, `month_to_date`) e `indicators.last_7_days_vs_typical_pct` (igual a `recent.last_7_days.difference_pct`).
   - Compare a janela atual até `data_through` com todas as janelas de mesmo tamanho num raio de `±15` dias da mesma data nos anos de referência VIIRS (`2012` em diante), usando `agregados_diarios` e calculando `typical_median`, `typical_p25`, `typical_p75`, `difference`, `difference_pct`, `n_years`, `n_windows`, `n_high` e `high_share`.
4. **Focos recentes no mapa (`GET /api/v1/detections/recent`):**
   - Parâmetros: `bbox` (`oeste,sul,leste,norte`), `hours` (`24`, `72` ou `168`, padrão `24`), `zoom` (inteiro), `mode` (`auto`, `hexagons` ou `points`, padrão `auto`).
   - Escolha do modo em `mode=auto`:
     - `zoom <= 4` → `hexagons` em H3 resolução `4`
     - `zoom in (5, 6)` → `hexagons` em H3 resolução `5`
     - `zoom == 7` → `hexagons` em H3 resolução `6`
     - `zoom >= 8` → `points` (se passar de **50.000 focos**, devolve `hexagons` em H3 resolução `6` no lugar, sem cortar a lista).
   - Consulta pelo índice parcial `focos_nrt` (`qualidade = 'NRT'`), filtrando apenas o satélite VIIRS do período atual (`Month(...).satellite`, nunca somando múltiplos satélites) e `confianca IN ('nominal', 'alta')`.
   - Devolve GeoJSON `FeatureCollection` com `h3` sempre como texto e contagens `n_low`, `n_medium`, `n_high` nos hexágonos (usando `h3.cell_to_parent` para resoluções 4 e 5) ou `intensity` e `confidence` traduzida (`nominal`/`high`) nos pontos.

#### Parte 5 — Exportação do pacote de auditoria (`POST /api/v1/export`, tarefa C6)

- Recebe o mesmo corpo JSON de `POST /api/v1/calendar` (`area`, `start`, `end`).
- Devolve `application/zip` com nome `firesync-YYYY-MM-DD.zip`.
- Conteúdo do ZIP conforme `docs/api.md`:
  1. `result.csv`: itens de `months[]`, uma linha por mês.
  2. `counts.csv`: `region_id, biome, year, month, satellite, daynight, raw_count, frp_sum`.
  3. `factors.csv`: `region_id, source_satellite, target_satellite, month, daynight, calibration_year, factor`.
  4. `metadata.json`: pedido, `meta`, fórmula, `"band_percentiles": [5, 95]`, método do percentil (interpolação linear), anos de calibração usados, versão de `alert_rules.json`, filtros (`type = 0`, confiança nominal e alta, duplicatas), fontes do FIRMS e data da exportação.
  5. `detections.csv`: focos brutos da área no intervalo, até **500.000 linhas** (`satellite, latitude, longitude, acquired_utc, confidence, frp, daynight, quality, source_file`), com valores em inglês (`confidence` = `low`/`nominal`/`high`, `daynight` = `D`/`N`, `quality` = `SP`/`NRT`). Se passar de 500.000 focos, `detections.csv` sai do ZIP e `metadata.json` traz `"detections_omitted": true` com a contagem total.

#### Parte 6 — Camada HTTP FastAPI, cache, rate limit e operação (`backend/src/adapters/inbound/http/`)

- Adicione `fastapi` e `uvicorn` às dependências de `backend/pyproject.toml` (e `httpx` no extra `test` e em `backend/requirements-dev.txt`).
- Implemente as rotas em `backend/src/adapters/inbound/http/` sob o prefixo `/api/v1`:
  - `GET /api/v1/health` → `{ "status": "ok", "data_version": ..., "last_month": ..., "updated_at": ..., "h3_resolution": 6 }`
  - `GET /api/v1/regions` → `[ { "region_id": 1, "name": "Amazônia", "source": "IBGE, Biomas do Brasil 1:250.000", "bbox": [-74.0, -16.3, -43.9, 5.3] }, ... ]`
  - `POST /api/v1/calendar` → resposta completa no formato de `docs/api-exemplo.json` (ou somente `meta`, `area`, `coverage` quando `coverage.status == "none"`).
  - `POST /api/v1/export` → pacote ZIP de auditoria.
  - `GET /api/v1/detections/recent` → GeoJSON de hexágonos ou pontos.
- Formato único de erro `{ "error": { "code": "...", "message": "..." } }` com os códigos HTTP de `docs/api.md`:
  - `400`: `invalid_geometry`, `invalid_period`, `invalid_bbox`, `invalid_hours`, `invalid_mode`
  - `404`: `region_not_found`
  - `413`: `area_too_large`
  - `429`: `rate_limited` (com cabeçalho `Retry-After`)
  - `500`: `internal_error` (sem expor detalhes internos do servidor)
- Operação e desempenho:
  - Cache LRU em memória cuja chave inclui `updated_at` + cabeçalho `ETag` com `updated_at`.
  - Verificação no startup (lifespan): lê `config.h3_resolucao` e confere numa amostra de `agregados` que as células têm essa resolução; se não bater, a API não sobe.
  - CORS configurável para a origem do front.

### 4. Verificação obrigatória antes do PR

Execute a partir da raiz do repositório e garanta que todos passem:

```bash
ruff check .
vulture data-pipeline backend/src backend/vulture_whitelist.py --exclude "tests,test_*.py" --min-confidence 60
TEST_DATABASE_URL=postgresql://usuario@localhost/banco_descartavel python -m pytest backend/tests -v -rxX --cov=backend/src --cov-branch --cov-report=term-missing --cov-fail-under=94.2
```

- Se adicionar entradas públicas chamadas apenas pelo FastAPI/testes em `backend/vulture_whitelist.py`, justifique cada símbolo.
- Atualize `backend/README.md`, `CLAUDE.md` (comando para subir a API HTTP), `README.md` (tabela de uso de IA, se aplicável) e `docs/tarefas.md` (marcando `C1` e `C3–C6` como `feito`).
