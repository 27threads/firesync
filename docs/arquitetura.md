# Arquitetura e stack

Este documento registra as escolhas técnicas do projeto. Cada linha "a decidir" precisa de um responsável e de uma escolha antes de alguém escrever código naquela parte.

**Status:** falta só o cálculo da anomalia (ponto 13).

## Já decidido (vem dos outros documentos)

| Ponto | Decisão | Fonte |
| --- | --- | --- |
| Fonte dos focos | NASA FIRMS: arquivo SP para o histórico, API NRT para a atualização | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Escopo inicial | Brasil baixado inteiro, Amazônia recortada pelo bioma do IBGE | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Índice espacial | H3 (célula calculada na carga) | [importacao-regioes.md](importacao-regioes.md) |
| Modelo de dados | 8 tabelas mais a `config`: `focos`, `regioes`, `celula_regiao`, `cobertura`, `fatores_harmonizacao`, `dias_sem_dados`, `agregados`, `agregados_diarios` | [importacao-regioes.md](importacao-regioes.md), [banco.md](banco.md) |
| Granularidade guardada | Célula H3 × ano × mês × satélite × dia/noite (`agregados`); por dia só para a janela recente (`agregados_diarios`) | [banco.md](banco.md) |
| Consulta | Pré-agregada. A API não consulta o FIRMS na hora | [requisitos.md](requisitos.md), RNF04 |
| Início do calendário | Janeiro de 2003 | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |

## A decidir

| # | Ponto | Opções levantadas | Escolha | Responsável |
| --- | --- | --- | --- | --- |
| 1 | Linguagem do pipeline | Python | Python (pandas, geopandas, pyarrow) | frente A |
| 2 | Banco de dados | PostgreSQL + PostGIS + h3-pg; DuckDB | PostgreSQL + PostGIS (H3 calculado no Python, ver [banco.md](banco.md)) | frente A |
| 3 | Resolução H3 | 5, 6, 7 | 6 (aprovado no PR #2, ver [banco.md](banco.md)) | frentes A e C |
| 4 | Linguagem e framework da API | Python | Python 3.12 + FastAPI, com psycopg 3 para o banco | frente C |
| 5 | Framework do front | HTML/JS sem build; Vite + React; Vite + Svelte | Vite + React + TypeScript | frente D |
| 6 | Biblioteca de mapa e desenho de área (RD01) | Leaflet; MapLibre GL | Leaflet com renderizador canvas + Leaflet-Geoman; tiles do NASA GIBS (VIIRS Black Marble como padrão, Blue Marble como alternativa), para os dados da NASA ficarem no centro (critério Relevance) | frente C, confirmado pela frente D |
| 7 | Biblioteca de gráficos do calendário | ECharts; D3 + SVG; Observable Plot | D3 + SVG próprio (módulos `d3-scale`, `d3-scale-chromatic`, `d3-shape`, `d3-array`) | frente D |
| 8 | Paleta acessível (RD04) | viridis ou cividis; escala linear ou log | cividis com escala logarítmica | frente C, confirmado pela frente D |
| 9 | Formato do download (RF13) | PNG, PDF, CSV | ZIP de auditoria com CSVs (`POST /export`); o PNG do calendário é gerado no front ([requisitos.md](requisitos.md), seção 4; [api.md](api.md)) | equipe |
| 10 | Granularidade mostrada no calendário | mensal ou diária | Mensal no calendário; diária só na janela recente e no alerta ([requisitos.md](requisitos.md), seção 4) | equipe |
| 11 | Onde roda o job NRT e a recarga SP | | Job NRT no serviço `job-nrt` do `docker compose` da VPS ([banco.md](banco.md)). A recarga SP ficou fora da submissão | frente A |
| 12 | Hospedagem pública (front, API e banco) | VPS; Postgres gerenciado | VPS com `docker compose`, incluindo `focos` (decidido no PR #2, ver [banco.md](banco.md)) | frentes A e C |
| 13 | Cálculo da anomalia (RF11, RF12) | mediana histórica, média de vários anos | mediana dos anos de referência, em todo lugar, com todos os anos completos menos o próprio ano (decidido em 15/11/2026, [api.md](api.md), "Decisões fechadas", itens 2 e 3; o ajuste do `indicators` é a issue #78) | equipe |

Ao decidir um ponto, preencha a escolha e escreva abaixo, em uma ou duas frases, por que ela foi escolhida.

## Justificativas

- **1. Python no pipeline:** preferência do time de dados. Tem as bibliotecas de dado geoespacial prontas (geopandas para o recorte por polígono, pyarrow para parquet) e já roda o download e a análise ([pipeline-dados.md](pipeline-dados.md)).
- **2. PostgreSQL:** escolha do time de dados. Tem PostGIS para os polígonos de `regioes`. O H3 é calculado no Python e guardado como `BIGINT`, então qualquer Postgres serve ([banco.md](banco.md)). Serve tanto para o pipeline quanto para a API, e tem hospedagem gratuita em vários provedores.
- **4. Python + FastAPI:** a API usa a mesma linguagem do pipeline, então o cálculo dos cenários e do H3 usa as mesmas bibliotecas (`h3`, `shapely`) e a mesma equipe revisa os dois lados. O domínio e os casos de uso já estão em Python no PR #41. O FastAPI fica só no adaptador HTTP da arquitetura hexagonal e valida pedido e resposta pelos tipos.
- **5. Vite + React + TypeScript:** a ferramenta tem estado que muda junto (área, período, resposta da API, estados de erro e downloads), e componentes React organizam isso melhor que JS solto. O Leaflet e o GSAP têm exemplos prontos com React. A esteira E2E já sobe o front com `npm run build` e `npm run preview` na porta 5173, que é o padrão do Vite.
- **6. Leaflet (canvas):** num teste lado a lado com os mesmos pontos (14/11/2026), Leaflet e MapLibre ficaram a 61 fps ao arrastar com até 60.000 focos, e o Leaflet desenhou mais rápido (141 ms contra 309 ms com 60.000). Com o desempenho empatado no nosso volume, ganhou o mais simples de colocar no ar: mais exemplos prontos e desenho de polígono, retângulo e círculo pelo Geoman. Os focos usam o renderizador canvas (`preferCanvas`), não marcadores DOM. A camada de focos recentes vem da nossa API, porque as camadas de fogo do GIBS são vector tiles (o Leaflet não lê sem plugin) e deram erro nos testes. O mapa base vem todo do **NASA EOSDIS GIBS**, sem chave de API: `VIIRS_Black_Marble` (padrão, escuro e do próprio VIIRS) e `BlueMarble_NextGeneration` (alternativa), com `Coastlines_15m` por cima. Os tiles CARTO Dark Matter, escolha anterior, passaram a devolver uma imagem "API key required" em 14/11/2026. A `Reference_Features_15m` respondeu com erro 400/500 no mesmo teste, e a camada de nomes (`Reference_Labels_15m`) deixou blocos pretos no mapa; nenhuma das duas é usada. Todas as fontes de tiles e bibliotecas estão creditadas em `#credits` do `frontend/index.html`.
- **7. D3 + SVG próprio:** o calendário é a peça que o jurado vê primeiro, e um heatmap de biblioteca pronta tem a cara de qualquer painel. Com D3 desenhando SVG, a gente controla cada célula: hachura nos meses estimados, borda nos incompletos, estado próprio para sem dados e fora da cobertura, a marca da troca de sensor em fev/2012 e a animação com GSAP. O SVG também é acessível (foco por teclado, rótulo por célula). O D3 só calcula escalas e formas e não substitui o React no DOM. O ECharts foi descartado por isso, mesmo sendo mais rápido de montar. O PNG do download sai serializando o SVG num canvas.
- **8. Cividis com escala logarítmica:** o cividis é o mais seguro para daltonismo e é citado no desafio (RD04). A escala é logarítmica porque setembro tem cerca de 30× mais focos que março: numa escala linear, todos os meses fora da temporada ficariam da mesma cor. Estados especiais (mês incompleto, estimado pelo MODIS, fora da cobertura) são marcados por hachura, borda ou rótulo, nunca só por cor.

## Componentes

### data-pipeline

- **Faz:** importa os CSVs, recorta por região, calcula os fatores, gera os `agregados` e roda o job NRT.
- **Entrada:** CSVs do FIRMS e shapefile de biomas do IBGE.
- **Saída:** tabelas preenchidas no banco.
- **Comandos:** `pipeline.py importar`, `agregar.py` e `job_nrt.py` ([pipeline-dados.md](pipeline-dados.md)). Falta o `recalcular <regiao>` (tarefa B5).

### backend

- **Faz:** recebe área e período, soma os `agregados` das células H3 da área e devolve o calendário, a sazonalidade, o ranking de anos e as anomalias.
- **Contrato:** [api.md](api.md).

### frontend

- **Faz:** mapa para escolher a área, seletor de datas, calendário em heatmap, indicadores principais e downloads.
- **Requisitos que cobre:** RF06–RF13 e RD01–RD07.

## Ambientes e variáveis

| Variável | Uso | Onde fica |
| --- | --- | --- |
| `FIRMS_MAP_KEY` | API do FIRMS (download e job NRT) | `.env` da VPS, nunca no git ([banco.md](banco.md)) |
| `DATABASE_URL` | Pipeline e API | `.env` da VPS, nunca no git ([banco.md](banco.md)) |
| `POSTGRES_PASSWORD` | Serviço `db` do compose | `.env` da VPS, nunca no git |

## Princípios de código

Valem para todo código novo, incluindo a continuação da API.

### Arquitetura hexagonal (portas e adaptadores)

O núcleo (domínio e casos de uso) não conhece HTTP, SQL nem arquivo. Ele fala com o mundo só por **portas** (interfaces). Os **adaptadores** ligam as portas ao mundo real. Trocar o banco, o framework web ou a fonte de configuração não mexe no núcleo, e o núcleo é testado sem nada disso.

```
backend/src/
├── domain/          regras puras: faixa P5–P95, origem do mês, classe de intensidade, alerta, janelas, IDs H3
├── application/     casos de uso: calendário, janela recente, focos recentes, export
├── ports/           interfaces (Protocol): HistoryRepository implementada; demais portas conforme os casos de uso
└── adapters/
    ├── inbound/http/        rotas (FastAPI): validam a entrada e devolvem o formato do api.md
    └── outbound/
        ├── postgres/        consultas SQL e tradução dos nomes do banco (português) para o domínio (inglês)
        └── config_file/     leitura do config/alert_rules.json
```

O pacote Python continua chamado `backend`, mapeado para `backend/src/` pelo `pyproject.toml`; não há diretório intermediário de pacote.

| Camada | Pode depender de | Não pode depender de |
| --- | --- | --- |
| `domain` | nada (só a biblioteca padrão e bibliotecas de conta, como `numpy` e `h3`) | `application`, `ports`, `adapters`, framework web, banco |
| `application` | `domain`, `ports` | `adapters` |
| `ports` | `domain` (tipos) | `adapters` |
| `adapters` | tudo acima | — |

- **S (uma responsabilidade):** cada camada muda por um motivo só. Mudar o banco não mexe na fórmula, e mudar a fórmula não mexe no HTTP.
- **D (depender de abstrações):** os casos de uso recebem as portas de fora. Nos testes, entra um adaptador falso em memória, sem banco.
- **O (aberto para extensão):** a regra do alerta ([config/alert_rules.json](../config/alert_rules.json)) e as regiões (`regioes.json`) vêm de configuração. Uma regra ou região nova não exige mexer no código antigo.
- **L e I pesam menos aqui.** Não vale criar classes e interfaces só para cumprir a sigla.
- O `data-pipeline/` é um conjunto de scripts de carga e não precisa seguir o hexágono. Código novo de regra que ele compartilhar com a API vai para o `domain`.

### Clean Code

- **Nomes que dizem o que é**, em inglês no código (`uncertainty_band`, `month_source`), sem abreviação obscura.
- **Funções pequenas, que fazem uma coisa só.** Se precisa de um comentário para explicar o que um bloco faz, ele vira uma função com esse nome.
- **Sem número mágico:** limites, percentis e janelas vêm do `alert_rules.json` ou de uma constante com nome.
- **Comentário explica o porquê**, não o quê. O "o quê" fica no nome.
- **Sem código morto nem comentado.** O histórico está no git. A esteira checa (`ruff` e `vulture`, ver [testes.md](testes.md)).
- **Erro explícito**, com mensagem clara. Nada de engolir exceção.
- **Deixe o código melhor do que encontrou**, mas refatoração grande vai num PR separado.

### Orientação a objetos com moderação

- **Contas são funções puras.** Mediana, percentis, fatores e a classe de intensidade recebem números e devolvem números. São as mais fáceis de testar e de auditar, e combinam com o pacote de auditoria.
- **Objetos para os dados do domínio** (área, mês do calendário, janela, regra) e para o acesso ao banco (repositórios).
- Nenhum desses princípios é o objetivo em si. O objetivo é código fácil de testar e de mudar.

### Transações (ACID)

O PostgreSQL é ACID, mas só protege o que estiver dentro de uma transação.

- **Escrita (pipeline):** os dados novos e a versão (`config.atualizado_em`, exposto como `meta.updated_at`) vão no mesmo commit, para a API nunca ler metade de uma atualização. Verificação do pipeline na issue #15.
- **Leitura (API):** cada pedido abre uma transação `REPEATABLE READ` e lê o `updated_at` dentro dela. Assim, todas as consultas do pedido veem o banco no mesmo instante, mesmo que o job faça commit no meio.
- **Recarga SP**, quando voltar: apagar o NRT e inserir o SP numa transação só.

## Qualidade e testes

A estratégia completa (TDD, regra dos bugs, cobertura, jornadas e esteira) está em [testes.md](testes.md).

### Testes automáticos (CI)

Todo PR com código roda os testes pelo **GitHub Actions** e só entra na `main` se passar (RNF08). A configuração fica em `.github/workflows/`.

| Parte | O que o CI testa |
| --- | --- |
| `data-pipeline/` | Os filtros (`test_pipeline.py`) e as migrations aplicadas num `postgis/postgis` limpo, duas vezes seguidas (para provar que podem rodar de novo sem quebrar) |
| `backend/` | Os serviços com repositório falso: fórmula, percentis por interpolação linear, cenários variáveis, janela de ±15 dias, alerta e classe de intensidade |
| `backend/` | O contrato: a resposta de `/calendar` tem os campos do [api-exemplo.json](api-exemplo.json), e uma célula H3 volta igual depois de passar pelo JSON (como texto) |
| `frontend/` | Build sem erro e a tela renderizando o `api-exemplo.json` |

- Os testes de fórmula usam números pequenos, calculados à mão, e ficam no repositório. Isso também serve de documentação da conta.
- O CI não acessa o FIRMS nem a VPS. Tudo roda com dados de teste.

### Antes de ir para produção

Fora do escopo da submissão, mas necessário numa aplicação real:

- Limite de requisições e monitoramento: RNF06 e RNF07 em [requisitos.md](requisitos.md).
- Backup do banco e um passo de deploy que aplica as migrations novas. O `docker-entrypoint-initdb.d` só roda com o banco vazio.
- Um ambiente de teste separado da produção.
