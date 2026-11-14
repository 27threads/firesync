# firesync

Calendário harmonizado de focos de calor (MODIS + VIIRS) para o NASA Space Apps 2026, desafio [MODIS and VIIRS Hot Spots](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/).

O usuário escolhe uma área e um período e vê um calendário meses × anos com o número de focos de calor. A série junta MODIS (2003 em diante) e VIIRS (2012 em diante) numa escala única, então o sensor de origem não importa mais para quem lê o calendário.

**Prazo da submissão:** domingo, 15/11/2026, 23h59 (horário do evento local).

**Objetivo: ganhar um prêmio global.** Primeiro, nota alta nos 5 critérios de julgamento, que decidem quem chega à final. Depois, as categorias-alvo (Best Use of Data, Best Use of Science e Local Impact), que guiam a história na página e no vídeo. Tudo em [docs/premiacao.md](docs/premiacao.md). Leia antes de qualquer tarefa.

## Para agentes: ordem de leitura

Leia nesta ordem antes de escrever código. Os documentos são a fonte de verdade. Se o código e um documento discordarem, pergunte antes de mudar qualquer um dos dois.

| # | Documento | O que define | Quando ler |
| --- | --- | --- | --- |
| 1 | [Requisitos](docs/requisitos.md) | O que o desafio exige (RF), o que dá pontos (RD), requisitos não funcionais e checklist da submissão | Sempre |
| 2 | [FIRMS — extração e dados disponíveis](docs/firms-extracao-dados.md) | Sensores, datas, formas de baixar (arquivo, API, WMS), colunas dos CSVs | Antes de mexer em importação ou API do FIRMS |
| 3 | [Plano de extração — Brasil (Amazônia)](docs/plano-extracao-amazonia.md) | Quais dados baixar, papel de cada satélite, dados de validação (IBGE, INPE), jobs de atualização | Antes de mexer no pipeline |
| 4 | [Importação de novas regiões](docs/importacao-regioes.md) | Importador, tabelas, chave única, fatores de harmonização por região, como adicionar região | Antes de mexer no banco, no pipeline ou na API |
| 5 | [Arquitetura e stack](docs/arquitetura.md) | Stack de cada componente, o que já está decidido e o que falta decidir | Antes de escrever qualquer código |
| 6 | [Tarefas](docs/tarefas.md) | Frentes, responsáveis, branches, pastas de cada um, marcos e status | Antes de começar qualquer tarefa |
| 7 | [Pipeline de dados — o que já foi feito](docs/pipeline-dados.md) | Download do histórico, filtros de qualidade, análise por satélite, achados | Antes de mexer em `data-pipeline/` |
| 8 | [Banco de dados — decisões para o backend](docs/banco.md) | Imagem, H3, resolução, schema, consulta da API, compose sugerido, benchmark | Antes de mexer no banco ou na API |
| 9 | [Contrato da API](docs/api.md) | Endpoints, pedido, resposta, erros, export de auditoria. JSON de exemplo em [api-exemplo.json](docs/api-exemplo.json) | Antes de mexer na API ou no front |
| 10 | [Prompt do frontend](docs/prompt-frontend.md) | Prompt para o agente que constrói o front: direção de design, regras de dado na tela, animação, performance e etapas de construção | Antes de começar a frente D |

Regras para agentes: [CLAUDE.md](CLAUDE.md).

## Estrutura do repositório

```
firesync/
├── README.md              este arquivo (mapa do projeto)
├── CLAUDE.md              regras para agentes
├── docs/                  todos os documentos do projeto (tabela acima)
├── data-pipeline/         download, importação, calibração, agregação e job NRT (frentes A e B)
│   ├── migrations/        schema do banco, aplicado em ordem
│   └── data/              ZIPs do FIRMS (Brasil, 2024, SP) para testes
├── backend/               API que serve o calendário, a janela recente e o export (frente C)
├── frontend/              aplicação web: mapa, calendário, alerta, downloads (frente D)
├── config/                regras que mudam sem mudar o código, como o alert_rules.json
└── infra/                 deploy na VPS: docker-compose, servidor web, .env.example (frente C)
```

Cada pasta tem um `README.md` com o que vai nela, quem é responsável e as regras que valem ali. `backend/`, `frontend/` e `infra/` ainda não têm código. `data-pipeline/data/` tem os quatro ZIPs de teste:

| Arquivo | Conteúdo |
| --- | --- |
| `DL_FIRE_M-C61_848018.zip` | MODIS C6.1 (Terra + Aqua) |
| `DL_FIRE_SV-C2_848021.zip` | VIIRS S-NPP |
| `DL_FIRE_J1V-C2_848019.zip` | VIIRS NOAA-20 |
| `DL_FIRE_J2V-C2_848020.zip` | VIIRS NOAA-21 |

## Como os dados fluem

```
CSV do FIRMS (arquivo SP ou API NRT)
  → importador         normaliza colunas, calcula H3, upsert em `focos`
  → recorte por região polígono em `regioes` (bioma IBGE)
  → calibração         fatores por região em `fatores_harmonizacao` (congelados após a carga)
  → agregação          `agregados`: célula H3 × ano × mês, focos harmonizados
  → API                soma as células da área desenhada, responde "sem dados" fora da `cobertura`
  → frontend           calendário, sazonalidade, ranking de anos, anomalias, downloads
```

Detalhes de cada etapa: documento 4.

## Regras que não mudam sem falar com a equipe

- O calendário começa em **janeiro de 2003**. Terra não entra no cálculo, só Aqua.
- **Um VIIRS por período, nunca a soma.** S-NPP até 02/11/2026, NOAA-20 depois. NOAA-21 só como reserva no NRT.
- Escala VIIRS: Aqua × fator (bioma × mês × dia/noite, um cenário por ano) de jan/2003 a jan/2012; S-NPP real de fev/2012 a out/2026; NOAA-20 real (fator 1) de nov/2026 em diante. Só confiança nominal ou alta e `type = 0`.
- Fatores ficam congelados depois da carga histórica. Jobs de atualização só aplicam o fator.
- Chave única do foco: (`satelite`, `lat`, `lon`, `datahora_utc`). Recarga SP apaga o NRT do período e insere o SP numa transação.
- Mês com falha de satélite (tabela `dias_sem_dados`) é diferente de mês com zero focos.
- Front e API não conhecem regiões específicas. Adicionar região é dado, não código.
- Interface em inglês, com crédito ao FIRMS visível.

## Estado atual

- [x] Requisitos e checklist da submissão
- [x] Levantamento do FIRMS e plano de extração
- [x] Modelo de dados e processo de importação
- [x] Dados de teste (Brasil, 2024)
- [ ] Stack e arquitetura definidas
- [ ] Contrato da API
- [x] Histórico do FIRMS baixado e análise por satélite ([pipeline-dados.md](docs/pipeline-dados.md))
- [x] Importador, pipeline, agregação, job NRT e série do INPE ([pipeline-dados.md](docs/pipeline-dados.md))
- [ ] API
- [ ] Frontend
- [ ] Deploy público
- [ ] Demo e página do projeto

## Uso de IA

A submissão exige identificar o código gerado com IA. Registre aqui quais partes foram geradas ou assistidas por IA, e com qual ferramenta, à medida que o código entra.

| Parte | Ferramenta | Como foi usada |
| --- | --- | --- |
| `data-pipeline/pipeline.py`, `agregar.py`, `eda.py`, `test_pipeline.py`, `test_banco.py`, `job_nrt.py`, `Dockerfile`, `migrations/` | Claude Code (Claude Opus 5.5) | Código gerado a partir das especificações de filtro escritas pelo time de dados. Revisado pela equipe |
| `docs/banco.md`, `data-pipeline/migrations/001_inicial.sql` | Claude Code (Claude Opus 5.5) | Schema e documento de decisões gerados a partir dos docs do repo e de um benchmark local. Revisado pela equipe |
| `docs/pipeline-dados.md` | Claude Code (Claude Opus 5.5) | Redação do relatório do que foi feito e dos achados da análise exploratória |
| `docs/prompt-frontend.md` | Claude Code (Claude Opus 5.5) | Prompt do front escrito a partir dos docs do repo. A equipe aprova antes de usar |
| `docs/api.md`, `docs/api-exemplo.json` (issues #22 e #29) | Claude Code (Claude Opus 5.5) | Correções do contrato escritas a partir das issues da auditoria. Revisado pela equipe |
| `.github/workflows/ci.yml` (job "Só documentação?"), `.github/scripts/roda_testes.sh`, `test_roda_testes.sh` | Claude Code (Claude Opus 5.5) | Filtro que pula os testes de código em PR só de `.md`. Revisado pela equipe |

## Dados e créditos

- Focos de calor: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS C6.1 e VIIRS C2)
- Polígonos de biomas: IBGE, Biomas do Brasil 1:250.000
- Série de validação: INPE, Programa Queimadas
