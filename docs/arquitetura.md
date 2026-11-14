# Arquitetura e stack

Este documento registra as escolhas técnicas do projeto. Cada linha "a decidir" precisa de um responsável e de uma escolha antes de alguém escrever código naquela parte.

**Status:** rascunho. Nenhuma stack foi decidida ainda.

## Já decidido (vem dos outros documentos)

| Ponto | Decisão | Fonte |
| --- | --- | --- |
| Fonte dos focos | NASA FIRMS: arquivo SP para o histórico, API NRT para a atualização | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Escopo inicial | Brasil baixado inteiro, Amazônia recortada pelo bioma do IBGE | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |
| Índice espacial | H3 (célula calculada na carga) | [importacao-regioes.md](importacao-regioes.md) |
| Modelo de dados | 5 tabelas: `focos`, `regioes`, `cobertura`, `fatores_harmonizacao`, `agregados` | [importacao-regioes.md](importacao-regioes.md) |
| Granularidade guardada | Célula H3 × ano × mês | [importacao-regioes.md](importacao-regioes.md) |
| Consulta | Pré-agregada. A API não consulta o FIRMS na hora | [requisitos.md](requisitos.md), RNF04 |
| Início do calendário | Janeiro de 2003 | [plano-extracao-amazonia.md](plano-extracao-amazonia.md) |

## A decidir

| # | Ponto | Opções levantadas | Escolha | Responsável |
| --- | --- | --- | --- | --- |
| 1 | Linguagem do pipeline | Python | Python (pandas, geopandas, pyarrow) | frente A |
| 2 | Banco de dados | PostgreSQL + PostGIS + h3-pg; DuckDB | PostgreSQL + PostGIS (H3 calculado no Python, ver [banco.md](banco.md)) | frente A |
| 3 | Resolução H3 | 5, 6, 7 | 6 (proposta em [banco.md](banco.md)) | frentes A e C |
| 4 | Linguagem e framework da API | Python + FastAPI | Python confirmado por Rafael para a primeira parte do backend; framework HTTP a decidir | frente C |
| 5 | Framework do front | | a decidir | |
| 6 | Biblioteca de mapa e desenho de área (RD01) | Leaflet; MapLibre GL | Leaflet com renderizador canvas + Leaflet-Geoman para desenhar | proposta da frente C, frente D revisa |
| 7 | Biblioteca de gráficos do calendário | | a decidir | |
| 8 | Paleta acessível (RD04) | viridis ou cividis; escala linear ou log | cividis com escala logarítmica | proposta da frente C, frente D revisa |
| 9 | Formato do download (RF13) | PNG, PDF, CSV | a decidir | |
| 10 | Granularidade mostrada no calendário | mensal ou diária | a decidir | |
| 11 | Onde roda o job NRT e a recarga SP | | a decidir | |
| 12 | Hospedagem pública (front, API e banco) | VPS; Postgres gerenciado | VPS com `docker compose`, incluindo `focos` (decidido no PR #2, ver [banco.md](banco.md)) | frentes A e C |
| 13 | Cálculo da anomalia (RF11, RF12) | mediana histórica, média de vários anos | a decidir | |

Ao decidir um ponto, preencha a escolha e escreva abaixo, em uma ou duas frases, por que ela foi escolhida.

## Justificativas

- **1. Python no pipeline:** preferência do time de dados. Tem as bibliotecas de dado geoespacial prontas (geopandas para o recorte por polígono, pyarrow para parquet) e já roda o download e a análise ([pipeline-dados.md](pipeline-dados.md)).
- **2. PostgreSQL:** escolha do time de dados. Tem PostGIS para os polígonos de `regioes`. O H3 é calculado no Python e guardado como `BIGINT`, então qualquer Postgres serve ([banco.md](banco.md)). Serve tanto para o pipeline quanto para a API, e tem hospedagem gratuita em vários provedores.
- **6. Leaflet (canvas):** num teste lado a lado com os mesmos pontos (14/11/2026), Leaflet e MapLibre ficaram a 61 fps ao arrastar com até 60.000 focos, e o Leaflet desenhou mais rápido (141 ms contra 309 ms com 60.000). Com o desempenho empatado no nosso volume, ganhou o mais simples de colocar no ar: mais exemplos prontos e desenho de polígono, retângulo e círculo pelo Geoman. Os focos usam o renderizador canvas (`preferCanvas`), não marcadores DOM. A camada de focos recentes vem da nossa API, porque as camadas de fogo do GIBS são vector tiles (o Leaflet não lê sem plugin) e deram erro nos testes. A camada de nomes do GIBS (`Reference_Labels_15m`) deixou blocos pretos no mapa e não deve ser usada.
- **8. Cividis com escala logarítmica:** o cividis é o mais seguro para daltonismo e é citado no desafio (RD04). A escala é logarítmica porque setembro tem cerca de 30× mais focos que março: numa escala linear, todos os meses fora da temporada ficariam da mesma cor. Estados especiais (mês incompleto, estimado pelo MODIS, fora da cobertura) são marcados por hachura, borda ou rótulo, nunca só por cor.

## Componentes

### data-pipeline

- **Faz:** importa os CSVs, recorta por região, calcula os fatores, gera os `agregados` e roda os jobs NRT e SP.
- **Entrada:** CSVs do FIRMS e shapefile de biomas do IBGE.
- **Saída:** tabelas preenchidas no banco.
- **Comandos previstos:** `importar <arquivo.csv>`, `recalcular <regiao>`.

### backend

- **Faz:** recebe área e período, soma os `agregados` das células H3 da área e devolve o calendário, a sazonalidade, o ranking de anos e as anomalias.
- **Contrato:** ver `api.md` nesta pasta (a escrever).

### frontend

- **Faz:** mapa para escolher a área, seletor de datas, calendário em heatmap, indicadores principais e downloads.
- **Requisitos que cobre:** RF06–RF13 e RD01–RD07.

## Ambientes e variáveis

| Variável | Uso | Onde fica |
| --- | --- | --- |
| `FIRMS_MAP_KEY` | API do FIRMS (jobs NRT e SP) | a decidir |
| _(conexão com o banco)_ | Pipeline e API | a decidir |

## Princípios de código

Valem para todo código novo, principalmente a API, que ainda não começou.

### Camadas da API

| Camada | Faz | Não faz |
| --- | --- | --- |
| **Rotas** (HTTP) | Recebem o pedido, validam a entrada e devolvem a resposta no formato do [api.md](api.md) | Conta nenhuma e SQL nenhum |
| **Serviços** (regras) | Fórmula do calendário, cenários e percentis, janela recente, alerta, classe de intensidade | Não sabem que existe HTTP nem SQL |
| **Repositórios** (SQL) | Só consultam o banco e traduzem os nomes do banco (em português) para os do domínio (em inglês) | Regra de negócio |

- **S (uma responsabilidade por parte):** cada camada muda por um motivo só. Mudar o banco não mexe na fórmula. Mudar a fórmula não mexe no HTTP.
- **D (depender de abstrações):** os serviços recebem o repositório de fora. Nos testes, entra um repositório com dados falsos, sem banco.
- **O (aberto para extensão):** a regra do alerta ([config/alert_rules.json](../config/alert_rules.json)) e as regiões (`regioes.json`) vêm de configuração. Uma regra ou uma região nova não exige mexer no código antigo.
- **L e I pesam menos aqui.** Não vale criar classes e interfaces só para cumprir a sigla.

### Orientação a objetos com moderação

- **Contas são funções puras.** Mediana, percentis, fatores e a classe de intensidade recebem números e devolvem números. São as mais fáceis de testar e de auditar, e combinam com o pacote de auditoria.
- **Objetos para os dados do domínio** (área, mês do calendário, janela, regra) e para o acesso ao banco (repositórios).
- Nenhum desses princípios é o objetivo em si. O objetivo é código fácil de testar e de mudar.

### Transações (ACID)

O PostgreSQL é ACID, mas só protege o que estiver dentro de uma transação.

- **Escrita (pipeline):** os dados novos e a versão (`config.updated_at`) vão no mesmo commit, para a API nunca ler metade de uma atualização. Verificação do pipeline na issue #15.
- **Leitura (API):** cada pedido abre uma transação `REPEATABLE READ` e lê o `updated_at` dentro dela. Assim, todas as consultas do pedido veem o banco no mesmo instante, mesmo que o job faça commit no meio.
- **Recarga SP**, quando voltar: apagar o NRT e inserir o SP numa transação só.

## Qualidade e testes

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
