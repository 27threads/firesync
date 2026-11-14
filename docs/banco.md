# Banco de dados — decisões para o backend

Nov 14, 2026 · frente A → frente C

Este documento junta o que o backend precisa para montar o `docker-compose.yml` e o `Dockerfile` e consultar o banco. O schema está em [`data-pipeline/migrations/001_inicial.sql`](../data-pipeline/migrations/001_inicial.sql).

## Decisões

| # | Ponto | Decisão | Status |
| --- | --- | --- | --- |
| 1 | Banco | PostgreSQL 16 + PostGIS 3.4 | decidido (frente A) |
| 2 | Imagem Docker | `postgis/postgis:16-3.4` (versão fixa) | proposta |
| 3 | H3 | Calculado no Python (lib `h3` v4) e guardado como `BIGINT`. **Sem** a extensão `h3-pg` | proposta |
| 4 | Resolução H3 | **6** (hexágono de ~36 km², lado de ~3,7 km) | proposta, precisa do ok da frente C |
| 5 | Schema | Migrations versionadas em `data-pipeline/migrations/`, aplicadas em ordem | proposta |
| 6 | Carga em massa | `COPY` via `psycopg` 3. Sem ORM no pipeline | decidido (frente A) |
| 7 | Acesso da API | SQL parametrizado (`psycopg` 3 + pool). SQLAlchemy opcional | sugestão |
| 8 | Polígonos das regiões | Células guardadas em `regioes.celulas_h3` no cadastro. A API não recalcula | proposta |
| 9 | Referência MODIS | Só Aqua, a partir de 2003. Terra guardado, mas fora do cálculo | decidido (frente A) |

### Por quê

- **3. H3 no Python:** a extensão `h3-pg` não existe na maioria dos Postgres gerenciados. Calculando no Python, qualquer Postgres serve. A API precisa usar **a mesma lib e a mesma resolução** que o pipeline, senão os IDs não batem.
- **4. Resolução 6:** é fina o bastante para a área desenhada pelo usuário (borda de ~3,7 km). A resolução 7 é mais fina que o pixel do MODIS (1 km), então não acrescenta nada. Medido nos dados reais: ~1 milhão de linhas em `agregados` para o Aqua de 2003 a 2026.
- **8. Células pré-calculadas:** o polígono do IBGE é muito detalhado. Converter a Amazônia inteira em células levou **102 s** no benchmark abaixo. Com as células guardadas em `regioes`, a API só lê o array. Uma área desenhada pelo usuário tem poucos vértices, e a conversão leva menos de 1 ms.

## Benchmark (Postgres local no Docker, agregados reais)

Carga: Aqua 2003–2026, resolução 6. São 976.260 linhas, carregadas com `COPY` em **3,8 s**.

| Área consultada | Células | Polígono → células | Consulta no banco |
| --- | --- | --- | --- |
| Amazônia inteira | 109.433 | 102 s (IBGE detalhado) → usar `celulas_h3` | **346 ms** |
| Pantanal inteiro | 4.177 | 0,7 s | **34 ms** |
| Área de ~100 × 100 km | 241 | < 1 ms | **3 ms** |

Conclusão: o Postgres, com a tabela `agregados` e a chave primária `(h3, ano, mes)`, dá conta da API sem cache nem ferramenta extra. Só a conversão de polígonos grandes precisa ser feita antes, no cadastro.

## Consulta da API

```sql
-- calendário meses × anos de uma área; %s são parâmetros (nunca concatenar string)
SELECT ano, mes, sum(focos_harmonizados) AS focos, bool_or(sem_dados) AS sem_dados
FROM agregados
WHERE h3 = ANY(%s::bigint[])                         -- células da área
  AND make_date(ano, mes, 1) BETWEEN %s AND %s       -- intervalo de datas
GROUP BY ano, mes
ORDER BY ano, mes;
```

Área desenhada → células, em Python:

```python
import h3
shape = h3.geo_to_h3shape(geojson_geometry)          # dict GeoJSON (Polygon/MultiPolygon)
cells = [h3.str_to_int(c) for c in h3.h3shape_to_cells(shape, 6)]
```

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
      - ./data-pipeline/migrations:/docker-entrypoint-initdb.d:ro   # aplica 001_inicial.sql no primeiro boot
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

## O que ainda não está decidido

- Formato final de `agregados` (T01). As colunas seguem [importacao-regioes.md](importacao-regioes.md), e `focos_harmonizados` depende da frente B.
- Linguagem e framework da API (arquitetura, ponto 4).
- Hospedagem (ponto 12). O Postgres gerenciado precisa ter PostGIS. H3 não é exigência, por causa da decisão 3.
