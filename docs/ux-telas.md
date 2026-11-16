# UX: racional das telas

Nov 14, 2026 · frente B (Weberson) → frente D · rascunho para a equipe revisar

Este documento define, para cada tela, o objetivo, as tarefas do usuário e as decisões que ele pode tomar. Contrato de dados em [api.md](api.md). Decisões de harmonização em [decisoes-harmonizacao.md](decisoes-harmonizacao.md). A interface é em inglês; os textos de exemplo abaixo estão em inglês quando aparecem na tela.

## Princípio

Quem usa está muitas vezes sob pressão (RD07). Por isso a ordem é: **primeiro o agora, depois a história, por último o detalhe.**

**Simples até para uma criança.** A resposta vem primeiro em palavras do dia a dia, e o número técnico fica um clique abaixo:

- No topo do explorador, um veredito em uma frase: "More fire than usual", "About as much fire as usual" ou "Less fire than usual", com cor e um ícone de forma diferente (▲ ● ▼), para não depender só da cor. A régua é a mesma do cartão dos 7 dias (faixa P25–P75). A frase mostra a faixa em números inteiros arredondados para dentro, então um número na frase nunca contradiz o veredito. O link "Why? See the numbers" leva aos cartões com os percentis.
- A escolha da área mostra só a região e o desenho no mapa. Latitude, longitude, raio e período ficam recolhidos em "More options".

Cada tela separa dois tipos de decisão:

- **No app:** o que o usuário escolhe ver.
- **No mundo real:** o que ele pode fazer com a informação.

## Público

- Centros de comando e equipes de combate a incêndio (bombeiros, brigadas).
- Equipes de alerta precoce e de resposta a emergências.
- Gestores de terras e de áreas protegidas.
- Cientistas e pesquisadores.

## Fluxo principal

Tela 1 (desenhar a área) → Tela 2 (é normal?) → Tela 3 (contexto histórico). É o fluxo do vídeo ([pitch.md](pitch.md), PR #11). As telas 4 e 5 ficam acessíveis, mas fora do caminho de quem tem pressa.

## Tela 1. Mapa: escolher a área e ver o fogo de agora

**Objetivo:** responder em segundos "onde está o fogo agora e quão forte".

**Tarefas do usuário**

- Desenhar a área no mapa (polígono, retângulo ou círculo) ou digitar latitude e longitude (RD01, RD02).
- Ver os focos das últimas 24 horas ou 7 dias, com a **classe de intensidade** (`low`, `medium`, `high`) por símbolo ou tamanho, além da cor (RD04).
- Aproximar e afastar: de longe, hexágonos com a contagem; de perto, os pontos (`GET /detections/recent`).
- Ligar a camada de **risco dos próximos 14 dias** (modelo treinado, RFC 0003): as células de faixa muito alta ou alta entram na lista "onde olhar primeiro" **mesmo sem fogo agora** (aviso antecipado). A lista mostra 10 células e o botão "Show all", porque no pico da temporada cerca de 29% das células ficam em "muito alto". As faixas aparecem na lista, no tooltip e na legenda em vermelho, laranja, amarelo e cinza (`frontend/src/hero/heroMapModel.ts`, D10).

**Decisões no app:** qual área analisar; janela de 24 horas ou 7 dias (para trás, a partir de agora). O horizonte de 14 dias do risco é fixo e não tem seletor.

**Decisões no mundo real:** quais pontos olhar primeiro, pela concentração de detecções fortes.

**Status visíveis**

- Última atualização (`meta.updated_at`, job a cada 3 horas).
- "No data for this area" quando a área fica fora da cobertura (hoje, o Brasil). Nunca um mapa vazio sem explicação.

## Tela 2. Agora contra o normal (resumo da área)

**Objetivo:** dizer, numa frase, se a situação é normal para o lugar e a época.

**Tarefas do usuário**

- Ler o cartão dos últimos 7 dias contra o normal da época (exemplo: "Last 7 days: +54% vs. typical").
- Ver o mês até hoje contra a mediana da época (RF11).
- Ver os indicadores: total de detecções e quantas são fortes (`n_high`, `high_share`) (RD06).

**Decisões no app:** abrir o histórico (tela 3) para entender o contexto.

**Decisões no mundo real**

- Acionar ou reforçar equipes.
- Priorizar esta área em relação a outras.
- Manter observação, se estiver dentro do normal.

**Status visíveis**

- Acima ou abaixo do normal, com a faixa típica da época (P25 a P75 entre os anos). Nomear de forma diferente da faixa de incerteza do calendário, para não confundir: uma é a variação natural entre anos, a outra é a incerteza da conversão.
- Dados provisórios (mês em andamento, NRT).
- Dados incompletos (3 dias ou mais sem satélite no mês).
- **Em proposta:** nível Normal, Atenção ou Crítico, com uma frase de explicação (PR #4).
- **Risco dos 14 dias** (RFC 0003): a faixa da célula (muito alto, alto, médio, menor) com "calculado em…" e a frequência com que a faixa teve fogo relevante no passado (82%, 46%, 27% e 3% nos testes). O alerta v1 fica como selo ("incomum para a época"), e o risco responde outra pergunta: onde tende a haver fogo.
- Sem nota recente de risco, a tela não mostra a camada, e não mostra risco zerado.

## Tela 3. Calendário histórico

**Objetivo:** mostrar o padrão do fogo na área desde 2003, numa escala só (VIIRS).

**Tarefas do usuário**

- Ler o calendário meses × anos em heatmap (cividis, escala logarítmica) (RF08, RD03, RD04).
- Tocar num mês para ver o número e, nos meses estimados, a faixa de incerteza ("the real value falls in this range in about 8 out of 10 cases").
- Ver o padrão sazonal (meses mais críticos) e o ranking de anos (RF09, RF10).
- Ver as anomalias em relação aos anos anteriores (RF12).

**Decisões no app:** mudar o período; comparar anos.

**Decisões no mundo real**

- Planejar a temporada: quando reforçar equipes e recursos.
- Identificar se este ano segue o padrão ou foge dele.
- Usar a série em relatórios e pesquisa.

**Status visíveis**

- Linha da troca de satélite em 2012, para ninguém ler a mudança de sensor como aumento de fogo.
- Meses estimados pelo MODIS (até janeiro de 2012) com hachura e faixa; meses observados pelo VIIRS sem faixa.
- Meses incompletos por hachura, borda ou rótulo, nunca só por cor.
- Mês com zero detecções com cor própria (a escala logarítmica não representa o zero).
- **Em proposta:** "estimativa pouco confiável" quando o MODIS viu menos de 10 focos na área no mês.

## Tela 4. Método e confiança

**Objetivo:** explicar, sem jargão, como os satélites foram unidos e quanto confiar nos números.

**Tarefas do usuário**

- Ler como a conversão funciona: um fator por bioma, mês e dia ou noite, calibrado em 13 anos em que os dois satélites funcionaram juntos.
- Ver os resultados da validação: erro médio de cerca de 6% por ano na Amazônia, cobertura medida da faixa e comparação com o INPE pela forma da curva.
- Ler os limites: o risco dos 14 dias é a **frequência do passado, não uma garantia**; a classe de intensidade ajuda a priorizar, mas não substitui informação de campo; o calendário conta detecções, e não incêndios.
- Ver como o risco foi testado (2021 a 2024, treinando só com anos anteriores): na Amazônia, precisão de 78% e cobertura de 74%; fora da temporada de fogo a cobertura cai para 62%; comparação com o índice do INPE (25% a 31% contra 59% a 64% de acerto nas 10% células mais arriscadas); e os limites: só detecções, sem clima previsto, Pantanal com poucos dados, testes com S-NPP.
- Ver o crédito ao NASA FIRMS e a declaração de uso de IA.

**Decisões no app:** nenhuma de navegação; é uma tela de consulta.

**Decisões no mundo real:** confiar ou não num número estimado antes de usá-lo numa decisão ou num relatório.

**Status visíveis:** versão dos dados (`data_version`) e das regras de alerta (`alert_rules.json`).

## Tela 5. Exportar

**Objetivo:** levar os resultados para fora do app (RF13, RD05).

**Tarefas do usuário**

- Baixar o calendário e os gráficos (CSV e PNG).
- Baixar os focos da área.
- Baixar o pacote de auditoria (`result.csv`, `counts.csv`, `factors.csv`, `metadata.json`, `detections.csv`), com o qual qualquer pessoa refaz o cálculo.

**Decisões no app:** o que baixar e em qual formato.

**Decisões no mundo real:** compartilhar com a equipe, anexar a relatórios, refazer o cálculo de forma independente.

**Status visíveis:** aviso quando a área tem mais de 500 mil focos, sugerindo uma área ou um período menor.

## Alinhamento com os critérios de julgamento

O que estas telas precisam deixar visível para os jurados:

| Critério | O que mostrar | Tela |
| --- | --- | --- |
| Impact | Prioridade de combate pela classe de intensidade, além de "é normal?" | 1 e 2 |
| Creativity | Fator separado para dia e noite; faixa de incerteza à mostra | 3 e 4 |
| Validity | Números medidos: erro de cerca de 6% ao ano, 13 anos testados, faixa de cerca de 8 em 10, comparação com o INPE | 4 |
| Relevance | Continuidade depois do fim do MODIS (2027), com o NOAA-20 seguindo a série; tudo feito com o NASA FIRMS | 3 e 4 |
| Presentation | Fluxo curto e claro (telas 1, 2 e 3), o mesmo do vídeo | 1, 2 e 3 |

Afirmações que precisam ser verdade antes da entrega: comparação com o INPE (B6) e teste retroativo do alerta ([validacao-alerta.md](validacao-alerta.md)), com o texto da tela fixado lá.

## Pendências que afetam as telas

1. Nível Normal, Atenção ou Crítico (tela 2): aguarda decisão da equipe.
2. "Estimativa pouco confiável" (tela 3): aguarda decisão da equipe.

A faixa de incerteza já está no contrato como `band_low` e `band_high` (percentis 5 e 95), no [api.md](api.md).
