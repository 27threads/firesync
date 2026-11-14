# firesync

Calendário harmonizado de focos de calor (MODIS + VIIRS) para o NASA Space Apps 2026, desafio [MODIS and VIIRS Hot Spots](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/).

O usuário escolhe uma área e um período e vê um calendário meses × anos com o número de focos de calor. A série junta MODIS (2003 em diante) e VIIRS (2012 em diante) numa escala única, então o sensor de origem não importa mais para quem lê o calendário.

**Prazo da submissão:** domingo, 15/11/2026, 23h59 (horário do evento local).

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
| 7 | [Restrições para o mundo](docs/escala-mundial.md) | O que muda quando a cobertura passar do Brasil para o mundo, com a saída proposta para cada ponto | Antes de mexer em cobertura, seleção de área ou camada de focos |

Regras para agentes: [CLAUDE.md](CLAUDE.md).

## Estrutura do repositório

```
firesync/
├── README.md              este arquivo (mapa do projeto)
├── CLAUDE.md              regras para agentes
├── docs/                  todos os documentos do projeto (tabela acima)
├── data-pipeline/         importador, harmonização, agregação e jobs de atualização
│   └── data/              ZIPs do FIRMS (Brasil, 2024, SP) para testes
├── backend/               API que serve os agregados para o front
└── frontend/              aplicação web (mapa, calendário, indicadores, downloads)
```

`backend/` e `frontend/` ainda estão vazios. `data-pipeline/data/` tem os quatro ZIPs de teste:

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
- Cadeia de calibração: NOAA-20 → S-NPP → Aqua. Fator calculado por região, com confiança nominal ou alta e `type = 0`.
- Fatores ficam congelados depois da carga histórica. Jobs de atualização só aplicam o fator.
- Chave única do foco: (`satelite`, `lat`, `lon`, `datahora_utc`). Recarga SP apaga o NRT do período e insere o SP numa transação.
- Mês sem dado de satélite (`sem_dados`) é diferente de mês com zero focos.
- Front e API não conhecem regiões específicas. Adicionar região é dado, não código.
- Interface em inglês, com crédito ao FIRMS visível.

## Estado atual

- [x] Requisitos e checklist da submissão
- [x] Levantamento do FIRMS e plano de extração
- [x] Modelo de dados e processo de importação
- [x] Dados de teste (Brasil, 2024)
- [ ] Stack e arquitetura definidas
- [ ] Contrato da API
- [ ] Importador e pipeline
- [ ] API
- [ ] Frontend
- [ ] Deploy público
- [ ] Demo e página do projeto

## Uso de IA

A submissão exige identificar o código gerado com IA. Registre aqui quais partes foram geradas ou assistidas por IA, e com qual ferramenta, à medida que o código entra.

| Parte | Ferramenta | Como foi usada |
| --- | --- | --- |
| | | |

## Dados e créditos

- Focos de calor: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS C6.1 e VIIRS C2)
- Polígonos de biomas: IBGE, Biomas do Brasil 1:250.000
- Série de validação: INPE, Programa Queimadas
