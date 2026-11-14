# Banco de dados — decisões para o backend

Nov 14, 2026 · frente A → frente C · revisado no PR #2

Este documento junta o que o backend precisa para montar o `docker-compose.yml` e o `Dockerfile` e consultar o banco. O schema está em [`data-pipeline/migrations/`](../data-pipeline/migrations/): `001_inicial.sql` e `002_celulas_sem_dados.sql`, aplicadas nessa ordem.

## Decisões

| # | Ponto | Decisão | Status |
| --- | --- | --- | --- |
| 1 | Banco | PostgreSQL 16 + PostGIS 3.4 | aprovado no PR #2 |
| 2 | Imagem Docker | `postgis/postgis:16-3.4` (versão fixa) | proposta |
| 3 | H3 | Calculado no Python (lib `h3` v4) e guardado como `BIGINT`. **Sem** a extensão `h3-pg` | aprovado no PR #2 |
| 4 | Resolução H3 | **6**, fixa, numa fonte só (tabela `config`) e garantida por `CHECK` | aprovado no PR #2 |
| 5 | IDs do H3 fora do banco | Sempre texto (`"86a8100c7ffffff"`), nunca número no JSON | aprovado no PR #2 |
| 6 | Schema | Migrations versionadas em `data-pipeline/migrations/`, aplicadas em ordem | proposta |
| 7 | Carga em massa | `COPY` via `psycopg` 3. Sem ORM no pipeline | frente A |
| 8 | Acesso da API | SQL parametrizado (`psycopg` 3 + pool). SQLAlchemy opcional | sugestão |
| 9 | Cobertura × região de calibração | Cobertura = Brasil inteiro. Regiões de calibração = 6 biomas do IBGE | aprovado no PR #2 |
| 10 | `regioes.json` × tabela `regioes` | O JSON é a entrada. A tabela é a fonte de verdade | aprovado no PR #2 |
| 11 | Formato de `fatores_harmonizacao` e `agregados` | Fator por mês × dia/noite × ano. Agregado bruto, com o fator aplicado na API | aprovado no PR #2 |
| 12 | Escala da série | **VIIRS.** Aqua só para 2003–2011 e para a calibração. Terra fora (guardado, mas não entra na conta) | aprovado no PR #2 |
| 13 | Células de cada região | Tabela `celula_regiao (h3, regiao_id)`, chave só em `h3` (cada célula numa região só, garantido pelo banco), no lugar de uma lista dentro de `regioes` | aprovado no PR #2 |
| 14 | Confiança | Só nominal e alta entram em `agregados` (calendário e fator). Baixa fica guardada à parte | aprovado no PR #2 |
| 15 | Satélite em `agregados` | Só o satélite que vale em cada mês: Aqua até jan/2012, VIIRS de fev/2012 em diante. Os outros só servem para a calibração, que lê de `focos` | aprovado no PR #2 |
| 16 | Falha de satélite | Tabela `dias_sem_dados (data, satelite)`, preenchida por `pipeline.py sem_dados`. Não é por célula | aprovado no PR #2 |
| 17 | Produção | VPS com `docker compose`, **incluindo `focos`** (export de auditoria da frente C, até 500 mil linhas) | aprovado no PR #2 |

## Resolução H3: fixa e numa fonte só

**Por que 6** (~36 km², lado de ~3,7 km):

- **Contagem estável.** O fator de harmonização é aplicado sobre contagens. Células pequenas têm contagens baixas e com muito ruído. A resolução 6 junta focos suficientes por célula.
- **Borda suficiente.** O lado de ~3,7 km atende quem desenha uma área.
- Desempenho não decide: a resolução 7 (~5 km², ainda maior que o pixel de ~1 km² do MODIS) também caberia, com ~1,85 milhão de linhas.

**Regras:**

- A resolução **não** é parâmetro do request. Os `agregados` existem numa resolução só.
- **Fonte única:** `config.h3_resolucao = '6'`, criada pela migration. O pipeline lê dali (`pipeline.py cadastrar`). A API também deve ler dali e **não subir** se o valor for diferente do que ela espera (frente C).
- **O banco recusa célula errada.** A resolução fica nos bits 52–55 do ID, então `CHECK (((h3 >> 52) & 15) = 6)` em `focos.h3` e `agregados.h3` faz qualquer carga errada falhar na hora. Testado: uma célula de resolução 5 foi recusada.
- **Mudar a resolução é uma migração**, não um ajuste: exige refazer `agregados` e `celula_regiao` e trocar o `CHECK`.
- **O front nunca precisa saber a resolução.** Ele manda a área em GeoJSON.

## IDs do H3 no JSON: sempre como texto

Um ID da resolução 6 vale cerca de 6 × 10¹⁷, e o JavaScript só representa inteiros exatos até 2⁵³ (cerca de 9 × 10¹⁵). Se o ID for como número no JSON, o `JSON.parse` arredonda **todos** os IDs, sem nenhum erro.

- No banco, `BIGINT`. A conversão acontece só na saída da API: `h3.int_to_str(id)`.
- De preferência, o front manda o GeoJSON e recebe o calendário pronto, sem ver células.
- Se precisar de células (por exemplo, para desenhar hexágonos no mapa), elas vão como texto, que é o formato do `h3-js`.
- O contrato precisa de um teste: uma célula conhecida volta igual depois de passar pelo JSON.

## Cobertura, regiões e `regioes.json`

| Conceito | O que é | Agora |
| --- | --- | --- |
| **Cobertura** | Onde temos focos baixados | Brasil inteiro (`config.cobertura_pais`) |
| **Região de calibração** | Onde vale um conjunto de fatores | Os 6 biomas do IBGE, na tabela `regioes` |
| **Região de demonstração** | O que a demo destaca | Amazônia e Pantanal (escolha da apresentação, não do banco) |

- `focos` guarda **tudo o que foi baixado**, sem coluna de região. O bioma só entra na calibração e na agregação.
- **`regioes.json` é a entrada:** versionada e fácil de revisar no git. `python pipeline.py cadastrar` lê o JSON, baixa o polígono, grava em `regioes` (upsert por `nome`) e grava as células da região, na resolução da `config`, em `celula_regiao`. **Nenhuma outra etapa lê o JSON.** O cadastro roda numa transação e deixa a tabela igual ao JSON: região renomeada ou removida do JSON sai do banco (com as células, agregados e fatores dela).
- **Células por região numa tabela, não numa lista:** `celula_regiao (h3, regiao_id)` tem chave só em `h3` (o banco recusa a mesma célula em duas regiões), índice em `regiao_id` e o mesmo `CHECK` de resolução. Uma lista dentro da linha de `regioes` não escala (o mundo tem ~4 milhões de células de terra na res 6).
- **Polígono simplificado só para achar as células:** tolerância de 0,001° (~110 m), muito menor que o lado da célula (~3,7 km). A simplificação mudou menos de 0,01% das células, e o polígono gravado em `regioes.geom` é o original.
- **Cada célula numa região só, sem perder a borda:** a célula vai para a região que contém o centro dela. As células de borda (costa e fronteira) cujo centro cai fora de todos os biomas vão para a região que encosta nelas. Sem isso, 0,08–0,12% dos focos de 2024 ficavam sem região e sumiriam dos `agregados`; com isso, 0%. O cadastro dos 6 biomas leva ~3 min e roda uma vez só.
- **Conferido:** a soma da área real das células de cada bioma fica entre +0,1% e +0,4% da área do polígono do IBGE. A área de um hexágono H3 varia com o lugar: no Brasil vai de ~30 a ~43 km².
- **A tabela `regioes` é a fonte de verdade:** a API, a calibração, a agregação e o próprio pipeline (bbox da API do FIRMS e recorte da cobertura) leem só ela.
- Fora da cobertura, a API responde "sem dados para esta área (cobertura atual: Brasil)". Nunca zero.
- **Para levar a outro país:** acrescentar os polígonos em `regioes.json`, rodar `cadastrar`, trocar `cobertura_pais` e baixar. O código não muda.

## Fatores e agregados

**`fatores_harmonizacao`**: uma linha por `regiao_id × satelite_origem × satelite_destino × mes × periodo (D/N) × ano_calibracao`. Cada ano da sobreposição é um cenário. O fator central é a mediana dos anos, e a faixa é o P10–P90.

Duas colunas extras, pedidas no PR #3: `n_focos_origem` (quantos focos do Aqua sustentam o fator) e `fusao_com` (condição vizinha usada quando o mínimo de focos não é atingido).

**`agregados`**: contagem **bruta** por `h3 × ano × mes × satelite × periodo`, com o `regiao_id` (bioma) da célula. Mês sem focos não tem linha, e a API preenche com zero. A agregação (frente B, tarefa B4) grava:

- **só o satélite que vale no mês:** Aqua até janeiro de 2012, VIIRS de fevereiro de 2012 em diante (um VIIRS por período: S-NPP até 02/11/2026, NOAA-20 depois). Isso deixa a tabela com cerca de metade das linhas;
- **só confiança nominal e alta** (o arquivo `lowconf` do `clean` não entra).

**`config.data_version`** (texto `YYYY-MM-DD`): gravado pelo `agregar.py` quando ele refaz a tabela inteira. É o `meta.data_version` da API, e quando ele muda a API recarrega os fatores.

**`dias_sem_dados`**: dias em que o FIRMS informa falha de um satélite (`missing_data`). Vale para o mundo todo. A API devolve quantos dias sem dado cada mês teve, e o front marca o mês a partir de 3 dias. A resposta diferencia três casos: zero focos, mês com falha de satélite e área fora da cobertura. Uma falha da coluna NRT do FIRMS só entra se for **depois** do último dia SP daquele satélite (regra do próprio FIRMS: antes disso o SP tem o dado). Conferido com os focos de 2024: nenhum dia marcado tem foco daquele satélite. Hoje são 169 dias × satélite (2001–2026). O `sem_dados` substitui a tabela inteira a cada execução.

A API soma as contagens brutas da área por (região, ano, mês, satélite, D/N), multiplica pelos fatores de cada cenário e só então calcula o valor central e a faixa. Isso é necessário porque **a soma dos P10 das células não é o P10 da soma**. O cálculo é pequeno (anos × meses × 2 satélites × 2 períodos), e mudar um fator não exige refazer `agregados`.

## Consulta da API

```sql
-- contagem bruta da área por região, mês, satélite e D/N; %s são parâmetros (nunca concatenar string)
SELECT regiao_id, ano, mes, satelite, periodo, sum(focos_brutos) AS focos, sum(frp_soma) AS frp
FROM agregados
WHERE h3 = ANY(%s::bigint[])                         -- células da área
  AND make_date(ano, mes, 1) BETWEEN %s AND %s       -- intervalo de datas
GROUP BY regiao_id, ano, mes, satelite, periodo;
```

Depois, em Python, cada linha é multiplicada pelos fatores de (`regiao_id`, `mes`, `periodo`, par de satélites) de cada `ano_calibracao`. Os cenários são somados por mês e a mediana e o P10–P90 saem dessa soma.

Área desenhada → células:

```python
import h3
res = int(conn.execute("SELECT valor FROM config WHERE chave = 'h3_resolucao'").fetchone()[0])
shape = h3.geo_to_h3shape(geojson_geometry)          # dict GeoJSON (Polygon/MultiPolygon)
cells = [h3.str_to_int(c) for c in h3.h3shape_to_cells(shape, res)]
```

## Benchmark (Postgres local no Docker)

Medido com o formato anterior de `agregados` (uma linha por célula × mês, só Aqua 2003–2026, 976.260 linhas). O formato novo tem mais linhas por célula (satélite × D/N), então os tempos servem como ordem de grandeza.

| Área consultada | Células | Polígono → células | Consulta no banco |
| --- | --- | --- | --- |
| Amazônia inteira | 109.433 | 102 s (IBGE detalhado) → ler de `celula_regiao` | 346 ms |
| Pantanal inteiro | 4.177 | 0,7 s | 34 ms |
| Área de ~100 × 100 km | 241 | < 1 ms | 3 ms |

Carga com `COPY`: 3,8 s para ~1 milhão de linhas. Conclusão: o Postgres dá conta sem cache. Só a conversão de polígonos grandes precisa ser feita antes, no `cadastrar`.

## Compose sugerido para o banco e o job NRT

O backend é dono do `docker-compose.yml`. Este trecho é só a configuração recomendada para os serviços `db` e `job-nrt`:

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: firesync
      POSTGRES_USER: firesync
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}      # vem do .env, nunca no compose
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./data-pipeline/migrations:/docker-entrypoint-initdb.d:ro   # aplica as migrations no primeiro boot
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U firesync -d firesync"]
      interval: 5s
      retries: 10
  job-nrt:                                         # issue #5: focos NRT a cada 3 h
    build: ./data-pipeline                         # Dockerfile da frente A
    environment:
      DATABASE_URL: postgresql://firesync:${POSTGRES_PASSWORD}@db:5432/firesync
      FIRMS_MAP_KEY: ${FIRMS_MAP_KEY}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
volumes:
  db-data:
```

- O `docker-entrypoint-initdb.d` só roda com o volume vazio. Migrations novas (`002_...sql`) precisam ser aplicadas à mão ou por um passo de deploy.
- A API deve esperar o `healthcheck` (`depends_on: db: condition: service_healthy`).
- O `job-nrt` roda `job_nrt.py` a cada 3 h: baixa as últimas 48 h de `VIIRS_NOAA20_NRT` e `VIIRS_NOAA21_NRT`, importa, refaz `agregados` dos meses da janela, atualiza `dias_sem_dados` e grava `config.atualizado_em`. Tem trava no banco (`pg_try_advisory_lock`), então duas rodadas nunca correm juntas. Uma rodada que falha não grava `atualizado_em`, e a próxima tenta de novo.
- **`config.atualizado_em`** (texto ISO 8601 em UTC, ex.: `2026-11-14T18:43:16Z`, igual ao `updated_at` do `api.md`) é a hora da última rodada que deu certo: é o `meta.updated_at` da API.

## Variáveis de ambiente

| Variável | Quem usa | Exemplo |
| --- | --- | --- |
| `DATABASE_URL` | pipeline e API | `postgresql://firesync:<senha>@db:5432/firesync` |
| `POSTGRES_PASSWORD` | compose (serviço `db`) | só no `.env` |
| `FIRMS_MAP_KEY` | pipeline (`download`) | só no `.env` |

## Ainda em aberto

- Regra de duplicatas do MODIS (em análise no PR #1; por enquanto só as exatas)
- Linguagem e framework da API (arquitetura, ponto 4)
