# Banco de dados — decisões para o backend

Nov 14, 2026 · frente A → frente C · revisado no PR #2

Este documento junta o que o backend precisa para montar o `docker-compose.yml` e o `Dockerfile` e consultar o banco. O schema está em [`data-pipeline/migrations/001_inicial.sql`](../data-pipeline/migrations/001_inicial.sql).

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
| 12 | Referência MODIS | Só Aqua, a partir de 2003. Terra guardado, mas fora do cálculo | frente A |

## Resolução H3: fixa e numa fonte só

**Por que 6** (~36 km², lado de ~3,7 km):

- **Contagem estável.** O fator de harmonização é aplicado sobre contagens. Células pequenas têm contagens baixas e com muito ruído. A resolução 6 junta focos suficientes por célula.
- **Borda suficiente.** O lado de ~3,7 km atende quem desenha uma área.
- Desempenho não decide: a resolução 7 (~5 km², ainda maior que o pixel de ~1 km² do MODIS) também caberia, com ~1,85 milhão de linhas.

**Regras:**

- A resolução **não** é parâmetro do request. Os `agregados` existem numa resolução só.
- **Fonte única:** `config.h3_resolucao = '6'`, criada pela migration. O pipeline lê dali (`pipeline.py cadastrar`). A API também deve ler dali e **não subir** se o valor for diferente do que ela espera (frente C).
- **O banco recusa célula errada.** A resolução fica nos bits 52–55 do ID, então `CHECK (((h3 >> 52) & 15) = 6)` em `focos.h3` e `agregados.h3` faz qualquer carga errada falhar na hora. Testado: uma célula de resolução 5 foi recusada.
- **Mudar a resolução é uma migração**, não um ajuste: exige refazer `agregados` e `regioes.celulas_h3` e trocar o `CHECK`.
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
- **`regioes.json` é a entrada:** versionada e fácil de revisar no git. `python pipeline.py cadastrar` lê o JSON, baixa o polígono, calcula `celulas_h3` na resolução da `config` e grava em `regioes`, com upsert por `nome`. **Nenhuma outra etapa lê o JSON.**
- **A tabela `regioes` é a fonte de verdade:** a API, a calibração, a agregação e o próprio pipeline (bbox da API do FIRMS e recorte da cobertura) leem só ela.
- Fora da cobertura, a API responde "sem dados para esta área (cobertura atual: Brasil)". Nunca zero.
- **Para levar a outro país:** acrescentar os polígonos em `regioes.json`, rodar `cadastrar`, trocar `cobertura_pais` e baixar. O código não muda.

## Fatores e agregados

**`fatores_harmonizacao`**: uma linha por `regiao_id × satelite_origem × satelite_destino × mes × periodo (D/N) × ano_calibracao`. Cada ano da sobreposição é um cenário. O fator central é a mediana dos anos, e a faixa é o P10–P90.

**`agregados`**: contagem **bruta** por `h3 × ano × mes × satelite × periodo`, com o `regiao_id` (bioma) da célula. Mês sem focos não tem linha, e a API preenche com zero.

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
| Amazônia inteira | 109.433 | 102 s (IBGE detalhado) → usar `regioes.celulas_h3` | 346 ms |
| Pantanal inteiro | 4.177 | 0,7 s | 34 ms |
| Área de ~100 × 100 km | 241 | < 1 ms | 3 ms |

Carga com `COPY`: 3,8 s para ~1 milhão de linhas. Conclusão: o Postgres dá conta sem cache. Só a conversão de polígonos grandes precisa ser feita antes, no `cadastrar`.

## Compose sugerido para o serviço do banco

O backend é dono do `docker-compose.yml`. Este trecho é só a configuração recomendada para o serviço `db`:

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
volumes:
  db-data:
```

- O `docker-entrypoint-initdb.d` só roda com o volume vazio. Migrations novas (`002_...sql`) precisam ser aplicadas à mão ou por um passo de deploy.
- A API deve esperar o `healthcheck` (`depends_on: db: condition: service_healthy`).

## Variáveis de ambiente

| Variável | Quem usa | Exemplo |
| --- | --- | --- |
| `DATABASE_URL` | pipeline e API | `postgresql://firesync:<senha>@db:5432/firesync` |
| `POSTGRES_PASSWORD` | compose (serviço `db`) | só no `.env` |
| `FIRMS_MAP_KEY` | pipeline (`download`) | só no `.env` |

## Ainda em aberto

- Escala da série: Aqua ou VIIRS
- Anos de calibração (proposta: 2012–2021, antes da deriva do Aqua)
- Regra de duplicatas do MODIS e se a baixa confiança entra no calendário
- `sem_dados` como tabela por data (`dias_sem_dados`)
- O que sobe para produção (sem `focos`?) e como fica o export de focos (RD05)
- Linguagem e framework da API (arquitetura, ponto 4) e hospedagem (ponto 12)
