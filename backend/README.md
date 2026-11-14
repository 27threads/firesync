# backend

API que serve o calendário, a janela recente, a camada de focos e o pacote de auditoria para o front.

- **Frente responsável:** C
- **Contrato:** [docs/api.md](../docs/api.md). Mudar o contrato exige avisar a equipe antes.
- **Lê do banco:** `config`, `regioes`, `celula_regiao`, `cobertura`, `fatores_harmonizacao`, `agregados`, `agregados_diarios`, `dias_sem_dados` e `focos` ([docs/banco.md](../docs/banco.md)).
- **Lê da configuração:** [config/alert_rules.json](../config/alert_rules.json) (alerta e classe de intensidade).
- **Não grava nada no banco.** Quem grava é o `data-pipeline/`.

Regras que valem aqui:

- Endpoints, campos do JSON, códigos de erro e nomes no código em inglês. A tradução dos nomes do banco (em português) acontece num lugar só, na camada que lê o banco.
- IDs H3 saem sempre como texto, nunca como número.
- A resolução H3 vem da tabela `config`. A API não sobe se ela não bater com as células do banco.

Linguagem: **Python**, confirmada por Rafael para esta primeira parte. O framework HTTP continua a decidir; FastAPI é uma proposta (ver [docs/arquitetura.md](../docs/arquitetura.md), ponto 4).

## Estrutura

O código fica diretamente em `backend/src/`. O `pyproject.toml` mapeia esse diretório para o pacote Python `backend`; por isso os imports continuam `backend.domain`, `backend.application`, `backend.ports` e `backend.adapters`, sem uma pasta física intermediária. Instale o pacote antes de usar; os testes ficam fora do código de produção. Domínio, repositório histórico PostgreSQL e serviço de calendário estão implementados; as pastas HTTP continuam reservadas para a entrega de integração.

```text
backend/
├── src/
│   ├── domain/
│   │   ├── models/                 objetos e valores do domínio
│   │   └── calculations/           funções puras de cálculo
│   ├── application/                casos de uso e regras de negócio
│   ├── ports/                      contratos de acesso aos dados
│   └── adapters/
│       ├── inbound/http/
│       │   ├── routes/             entrada e saída HTTP (próxima entrega)
│       │   └── schemas/            validação e serialização (próxima entrega)
│       └── outbound/
│           ├── postgres/           SQL e tradução dos nomes do banco
│           └── config_file/        leitura da configuração (próxima entrega)
├── tests/
│   ├── unit/
│   │   ├── domain/                 cálculos e objetos do domínio
│   │   └── services/               regras com repositórios falsos
│   ├── integration/repositories/   acesso real ao PostgreSQL/PostGIS
│   ├── contract/api/               formatos públicos de pedidos e respostas
│   ├── fixtures/                  dados pequenos para testes
│   └── fakes/                     implementações falsas dos contratos
└── data/                          espaço reservado para dados locais
```

Os serviços recebem os contratos de repositório por injeção de dependência. O domínio e os serviços permanecem independentes do framework HTTP e do driver SQL. As rotas delegam aos serviços; os repositórios concretos implementam os contratos e concentram o SQL. A configuração conecta as implementações aos serviços na inicialização.

As regras de alerta continuam em `config/alert_rules.json` na raiz do repositório. Dados reais, segredos e exports gerados não devem ser commitados em `backend/data/`. Os dados pequenos e versionados dos testes ficam em `tests/fixtures/`.

A separação permite testar e alterar as camadas de forma independente. Desempenho e capacidade de escala serão medidos quando houver implementação e consultas reais.

## Commits

Na branch `dev-backend-rafael`, cada classe de produção ou de teste terá seu próprio commit, usando Conventional Commits com descrição em português. A criação inicial de pastas fica em um único commit, pois ainda não há classes.

## Executar as partes 1–3

Na raiz do repositório, com Python 3.12 ou superior:

```bash
python -m pip install -e './backend[test]'
python -m pytest backend/tests/unit -q
TEST_DATABASE_URL=postgresql://usuario@localhost/banco_descartavel python -m pytest backend/tests -q
```

Os testes de integração criam um schema exclusivo por teste, aplicam as migrations do pipeline e removem apenas esse schema ao terminar. Exigem PostgreSQL 16/PostGIS 3.4 e permissão para criar schemas; use um banco descartável. Sem `TEST_DATABASE_URL`, esses testes são explicitamente pulados. O job `backend` do workflow `.github/workflows/ci.yml` fornece um PostGIS local e executa todas as verificações sem acessar FIRMS ou IBGE.

Uso do serviço em Python, com `DATABASE_URL` fornecida pelo ambiente:

```python
import os
from psycopg_pool import ConnectionPool
from backend.domain.models.area import Area
from backend.adapters.outbound.postgres.history import PostgresHistoryRepository
from backend.application.calendar import CalendarService

with ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=4) as pool:
    repository = PostgresHistoryRepository(pool)
    calendar = CalendarService(repository)
    result = calendar.calculate(Area("region", region_id=1), "2020-01", "2020-12")
```

O ID acima é ilustrativo: a região precisa existir no banco. O pool pertence à aplicação e deve ser fechado por ela. Cada chamada lê os metadados e os dados na mesma transação `REPEATABLE READ READ ONLY`, em UTC. O banco precisa ter as migrations aplicadas, células, cobertura, agregados, fatores quando houver contagens MODIS, e `config.data_version`/`config.atualizado_em` válidos (a segunda chave é traduzida para `meta.updated_at`). Uma falha não deixa a conexão em transação abortada.

### Políticas e limites desta entrega

- A seleção aceita região, GeoJSON ou ponto com raio geodésico; usa H3 6 e limita a seleção a 250.000 células. As frações dos biomas e da cobertura usam a área real das células selecionadas.
- O calendário mensal usa o satélite definido pela data. Contagens observadas não recebem fator. Os valores estimados e os totais anuais preservam os cenários até calcular a mediana e P5–P95 por interpolação linear.
- **Decisão de Rafael:** ao somar condições ou meses com conjuntos diferentes de cenários, usar a interseção dos anos de calibração. Nenhum fator ausente é inventado. Conjuntos disjuntos ou fatores ausentes para contagens positivas geram `CalendarError`.
- As anomalias seguem a proposta atual de `docs/api.md`: anos completos disponíveis desde 2003, excluindo o próprio ano, independentemente do filtro de exibição. Essa regra ainda está em aberto para a equipe no contrato. Valores sem referência ou com denominador zero usam `None`; sazonalidade sem ano completo tem `n_years=0` e estatísticas `None`.
- Os anos disponíveis para referência exigem cobertura temporal de todos os meses e de todos os biomas selecionados. Uma lacuna temporal no intervalo solicitado gera erro de dados, em vez de transformar ausência em zero. O formato HTTP desse erro pertence à parte 6.
- `indicators.total_detections` segue a definição textual do contrato: soma dos valores centrais mensais. `years[].detections` é a mediana dos totais por cenário; essas duas contas podem diferir. A definição do indicador merece revisão da equipe se for necessário torná-las equivalentes.
- `CalendarService` retorna somente a parte histórica: `meta`, `area`, `coverage`, `months`, `years`, `seasonality` e indicadores históricos. Fora da cobertura retorna apenas os três primeiros. **Não é ainda uma resposta completa do endpoint**: `recent` e `last_7_days_vs_typical_pct` serão compostos na parte 4; HTTP, cache, CORS e limites de requisição pertencem à parte 6.
- O repositório lê agregados em lote e só consulta focos para identificar meses NRT, usando o filtro do índice parcial. Não há consulta SQL por mês. A validação foi feita com dados sintéticos; as metas de latência do contrato ainda precisam de benchmark com o histórico real.

Referências das bibliotecas: [Python](https://docs.python.org/3/), [H3](https://uber.github.io/h3-py/), [Shapely](https://shapely.readthedocs.io/), [pyproj](https://pyproj4.github.io/pyproj/), [Psycopg](https://www.psycopg.org/psycopg3/docs/), [pytest](https://docs.pytest.org/).

### Integração da main e organização para revisão

A estrutura segue a arquitetura hexagonal da main: `application` depende de `domain` e `ports`; os adaptadores implementam os contratos. O pacote foi validado tanto na instalação editável quanto como wheel, fora do checkout.

Os testes TDD de percentis, seleção de satélite, IDs H3 e calendário agora chamam as interfaces implementadas e não usam `xfail`. As especificações de intensidade, alerta e janelas recentes continuam marcadas como pendentes da parte 4. Os valores esperados da especificação original foram preservados.

O CI instala as dependências do `pyproject.toml`, inicia PostGIS e executa integração junto com unidade e contrato. A cobertura mínima de linhas e ramos foi elevada para 94,2%. O workflow separado de backend foi consolidado no CI principal, evitando duas esteiras com instalações diferentes.

O adaptador preserva `data_version` completo (inclusive hora, conforme o PR #23), aceita versões históricas contendo só a data e rejeita timestamps sem fuso horário. Assim, duas cargas no mesmo dia mantêm versões diferentes.

Validação após integração: 76 testes aprovados, 13 especificações futuras em `xfail`, cobertura de linhas e ramos de 94,21%. Ruff e Vulture passaram. A instalação editável e a wheel foram verificadas. Os testes do pipeline e as migrations também passaram; as jornadas do frontend foram apenas listadas, sem execução de navegador.
