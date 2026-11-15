# backend

API Python 3.12 + FastAPI que serve os cinco endpoints de [docs/api.md](../docs/api.md): health, regions, calendar, detections/recent e export. Frente C. A API só lê PostgreSQL/PostGIS; o pipeline continua responsável pelas cargas.

## Executar a API e o front

Na raiz, instale o pacote no ambiente Python do projeto:

```powershell
python -m pip install -e './backend[test]'
# DATABASE_URL deve estar configurada no ambiente, apontando para o banco carregado.
python -m uvicorn backend.adapters.inbound.http.app:create_app --factory --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
cd frontend
npm ci
$env:VITE_DEV_API_PROXY = 'http://127.0.0.1:8000'
npm run dev
```

O proxy existente encaminha `/api` para a API. `VITE_API_URL` permite uma API em outra origem; nesse caso, configure `FRONTEND_ORIGIN` com a origem exata do front. A API valida os metadados e uma amostra H3 antes de aceitar pedidos. O banco deve ter as migrations de `data-pipeline/migrations/`, cobertura e versões válidas.

| Variável | Padrão | Uso |
| --- | --- | --- |
| `DATABASE_URL` | obrigatória | PostgreSQL com a carga, via psycopg 3 e pool |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Única origem permitida pelo CORS |
| `CLIENT_IP_HEADER` | vazio (IP do socket) | Header com o IP real do usuário para o rate limit. Só atrás de proxy que sobrescreve o header (`CF-Connecting-IP` no Cloudflare Tunnel, [deploy.md](../docs/deploy.md)) |
| `RISK_MAX_AGE_DAYS` | `2` | Idade máxima, em dias, da nota de risco que o mapa mostra (`risco_celulas`). Mais velha que isso, os campos de risco não vêm. Na VPS está em 10: se o `job-risco` parar, o mapa segura a última nota por mais tempo ([deploy.md](../docs/deploy.md)) |
| `RATE_LIMIT_GENERAL` | `60` | Pedidos aceitos por IP na janela |
| `RATE_LIMIT_CALENDAR` | `10` | Pedidos de calendário por IP na janela |
| `RATE_LIMIT_EXPORT` | `2` | Pedidos de exportação por IP na janela |
| `RATE_LIMIT_WINDOW` | `60` | Duração da janela móvel, em segundos |
| `RESPONSE_CACHE_SIZE` | `128` | Máximo de respostas no LRU |
| `ASSISTANT_PROVIDERS` | vazio (assistente desligado) | Provedores do `POST /ask` em ordem de fallback, no formato OpenAI chat completions: `base_url|chave|modelo[|reasoning_effort]`, separados por vírgula. O 4º campo só vai quando preenchido: modelos que raciocinam (Qwen, Gemini) gastam o `max_tokens` pensando sem ele (testado: `none` na Cerebras, Groq e OpenRouter; `low` no Gemini). Segredo: só no `.env` da VPS. Valor inválido desliga só o assistente (erro no log), a API sobe normal |
| `ASSISTANT_DAILY_LIMIT` | `500` | Pedidos do assistente que chegam a um provedor por dia (UTC), somando todos os IPs. Por processo; zera ao reiniciar |
| `ASSISTANT_TIMEOUT_S` | `20` | Tempo máximo de cada chamada a um provedor |
| `ASSISTANT_BUDGET_S` | `60` | Tempo máximo da pergunta inteira, somando rodadas e provedores. Fica abaixo dos ~100 s que o Cloudflare Tunnel espera |
| `RATE_LIMIT_ASK` | `5` | Pedidos do assistente por IP na janela |
| `ALERT_RULES_PATH` | `config/alert_rules.json` do checkout | Versão, limites do alerta e da classe de intensidade |

Rate limit e cache são locais a cada processo. Para conservar o limite global configurado, rode um worker; o segundo limite no proxy pertence ao deploy C7. O IP vem da conexão ASGI: cabeçalhos encaminhados só devem ser confiados pelo Uvicorn quando vierem do proxy configurado. `429` inclui `Retry-After` em segundos. Os logs do Uvicorn incluem endpoint, status, duração e número de células.

## Organização e consistência

O `pyproject.toml` mapeia `src/` para o pacote `backend`, sem diretório intermediário:

- `domain/`: área, mês, H3, cenários, percentis, janelas e intensidade; funções puras.
- `application/`: calendário histórico, composição da janela recente e documento de auditoria.
- `ports/`: interfaces de leitura histórica e unidade de leitura da API.
- `adapters/inbound/http/`: fábrica FastAPI, erros, rate limit, cache e serialização ZIP/CSV.
- `adapters/outbound/postgres/`: SQL parametrizado e tradução dos nomes/valores em português para inglês.
- `adapters/outbound/config_file/`: leitura das regras versionadas.
- `scripts/demo_data.py`: gerador C2 de dados sintéticos, separado do serviço de leitura.
- `scripts/assistant_benchmark.py`: bateria do assistente (RFC 0004) com perguntas cujo gabarito sai do próprio calendário, incluindo continuação de conversa, fora do assunto e lugar sem cobertura. Rode à mão antes de mudar prompt, ferramenta ou provedor: precisa de `DATABASE_URL` com a carga real e de `ASSISTANT_PROVIDERS`, então não entra na esteira.
- `tests/`: unidade, contratos HTTP, integração PostGIS e jornadas com navegador.

Cada pedido lê metadados e dados em uma transação `REPEATABLE READ READ ONLY`, em UTC. O pool pertence à aplicação e fecha ao encerrar. Fatores são mantidos em memória por `data_version` completa, inclusive hora. O LRU de respostas usa área/parâmetros, `updated_at` e `data_version`; o calendário também inclui o dia UTC para atualizar os marcadores de mês/ano corrente. No mapa, o cache também expira quando o foco mais antigo sai da janela; resultados vazios são reavaliados após um minuto, mesmo sem atualização NRT. `ETag` acompanha as respostas JSON e GET aceita `If-None-Match`.

## Regras implementadas

- Área por região, Polygon/MultiPolygon ou ponto com raio geodésico, H3 6 e limite de 250.000 células. Frações usam áreas reais das células. `none` retorna somente `meta`, `area` e `coverage`; `partial` calcula apenas a parte coberta.
- Histórico: satélite definido pela data, fatores somente no MODIS e cenários preservados até a mediana/P5–P95. A combinação segue a [decisão da equipe](../docs/importacao-regioes.md#fórmula-do-calendário-para-refazer-a-partir-do-export-de-auditoria).
- Anomalias seguem a decisão do contrato: referência independente do filtro, excluindo o próprio ano. O indicador anual usa `reference_median`, com mediana dos anos de referência e percentual calculados por cenário antes do resumo final. Ausência de referência e denominador zero são `null`. `indicators.total_detections` soma os valores centrais mensais; o total anual preserva cenários e pode diferir.
- Recente: `data_through` é o último dia de cobertura VIIRS comum aos biomas selecionados, inclusive dias cobertos com zero focos. Soma `agregados_diarios`, usa janelas de mesmo tamanho deslocadas de −15 a +15 dias, apenas anos anteriores com VIIRS, e interpolação linear para mediana/P25–P75. 29/02 usa 28/02 em ano comum. Janelas de referência que atravessam dias sem cobertura ou `dias_sem_dados` não entram; `n_windows` e `n_years` registram o suporte efetivo. Sem amostras, as estatísticas são `null`, não zero.
- `n_high` vem de `focos`, porque a tabela diária não contém intensidade, na mesma transação e com os mesmos filtros/satélite. `high_share` é `null` com zero detecções. Falta de cobertura temporal no período histórico solicitado ou de cobertura VIIRS gera `500 internal_error`, sem detalhes internos.
- Mapa: somente NRT, confiança nominal/alta, tipo 0 ou ausente no NRT, FRP positivo e um VIIRS por período. Pontos acima de 50.000 viram hexágonos H3 6, sem truncar; zoom escolhe H3 4/5/6 conforme o contrato. H3 sempre string e geometria GeoJSON em lon/lat. Limites de intensidade vêm do arquivo de regras; FRP não sai no JSON do mapa.
- ZIP em memória: `result.csv`, `counts.csv`, `factors.csv`, `metadata.json`, mais `detections.csv` até 500.000 linhas inclusive. Contagens, fatores usados e focos seguem a mesma área/período e o satélite do calendário. Acima do limite, metadados informam omissão, contagem total e mensagem em inglês. CSV UTF-8 com BOM, datas UTC, valores/cabeçalhos em inglês e booleanos `true`/`false`.

## Testar

Na raiz, com o pacote instalado:

```powershell
# Unidade e contratos HTTP não precisam de servidor externo.
python -m pytest backend/tests -q
# Para incluir integração, configure TEST_DATABASE_URL com um PostGIS descartável.
python -m pytest backend/tests -q --cov=backend/src --cov-branch --cov-fail-under=97.1
ruff check .
vulture data-pipeline backend/src backend/vulture_whitelist.py --exclude 'tests,test_*.py' --min-confidence 60
```

Os testes PostGIS criam schemas exclusivos e removem apenas esses schemas. Sem `TEST_DATABASE_URL`, são pulados explicitamente. O caso volumoso cria 500.001 focos sintéticos para verificar os limites do mapa e do ZIP. O alerta da issue #59 está integrado ao `recent`, com piso contínuo, tendência de 3 dias e versão da regra; os testes do domínio e da rota HTTP estão ativos.

Com uma API já no ar:

```powershell
$env:API_URL = 'http://127.0.0.1:8000'
python -m pytest backend/tests/contract/test_api_contract.py -k live_api -q
```

### Carga sintética C2 e navegador

Em um banco **vazio e descartável**, com nome terminado em `_test` ou `_demo`, configure `DEMO_DATABASE_URL` e execute:

```powershell
python backend/scripts/demo_data.py --apply
```

O script aplica as migrations e insere uma região chamada `Synthetic demo`. Sem `--apply`, apenas imprime o SQL. Nunca aponte esse gerador para a carga científica. Os valores inventados exercitam a harmonização e as janelas; não representam observações da NASA.

Suba a API com `DATABASE_URL` apontando para esse banco e o front pelo proxy. Para várias jornadas seguidas, os limites podem ser aumentados apenas nesse ambiente de testes. Então:

```powershell
npm --prefix frontend/e2e ci
npm --prefix frontend ci
# Instalar o Chromium: a partir de frontend/e2e, npx playwright install chromium.
$env:FRONTEND_URL = 'http://127.0.0.1:5173'
node frontend/e2e/node_modules/@playwright/test/cli.js test -c backend/tests/e2e/playwright.config.cjs
```

As duas jornadas novas usam os cinco endpoints reais, conferem o calendário, a janela recente, o mapa, o ZIP e a ausência de cobertura no desktop e celular. A CI executa esse fluxo além das 18 jornadas existentes com API simulada. A implementação foi verificada com dados sintéticos; desempenho e números da carga real aguardam o [roteiro do Eduardo](../docs/validacao-api-eduardo.md). D7/M2 permanece com essa pendência explícita.

Referências: [Python](https://docs.python.org/3/), [FastAPI](https://fastapi.tiangolo.com/), [Starlette](https://www.starlette.io/), [Uvicorn](https://www.uvicorn.org/), [HTTPX](https://www.python-httpx.org/), [H3](https://uber.github.io/h3-py/), [Shapely](https://shapely.readthedocs.io/), [pyproj](https://pyproj4.github.io/pyproj/), [Psycopg](https://www.psycopg.org/psycopg3/docs/), [pytest](https://docs.pytest.org/), [Playwright](https://playwright.dev/).
