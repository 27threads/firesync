# RFC 0003: Modelo de risco treinado (experimento)

- **Status:** Experimento concluído em 15/11/2026. **Não entra no produto.** O alerta da submissão continua sendo a regra `v1` ([RFC 0001](0001-backtest-alerta.md)). Decisão do Weberson (frente B)
- **Autor:** Weberson (frente B)
- **Data:** 2026-11-15

Critério que melhora (ver [premiacao.md](../premiacao.md)): **Validity**. A tela de Método pode dizer, com números, por que ficamos com uma regra simples e explicável em vez de um modelo treinado.

## Pergunta

Um modelo treinado com o histórico de fogo e com dados de clima antecipa as semanas de "muito fogo" melhor que a regra `v1` do alerta?

Este modelo é diferente do modelo A ([RFC 0002](0002-modelo-a.md)). O modelo A estima a chance de o MODIS ver um fogo que o VIIRS viu, para explicar a harmonização. Este tenta prever **onde vai haver muito fogo**.

## Como foi feito

- **Alvo:** o mesmo gabarito do backtest do alerta, sem mudar nada nele. Para cada domingo e cada célula H3 de resolução 4 (cerca de 1.770 km²), os 14 dias seguintes ficam acima do P90 do normal e têm pelo menos 10 detecções. O modelo não é treinado com o nível de alerta, porque isso seria só copiar a regra.
- **Pistas, todas com dias até o domingo avaliado (nenhuma olha o futuro, com teste):**
  - **fogo:** detecções em 7, 14 e 30 dias, tendência, potência (FRP) em 7 dias, detecções nas células vizinhas, o mesmo período no ano anterior e na média dos anos anteriores, semana do ano, posição e bioma da célula;
  - **ONI** (El Niño e La Niña, NOAA CPC), só da estação já publicada;
  - **clima** (NASA POWER): chuva em 30 e 90 dias, dias secos, temperatura máxima, umidade e vento em 7 dias, brutos e como anomalia (o valor menos a média dos anos **anteriores**).
- **Modelo:** gradient boosting (`HistGradientBoostingClassifier`, o mesmo do modelo A).
- **Validação em avanço:** para cada ano de teste de 2017 a 2023, o modelo treina só com semanas cujo gabarito termina antes daquele ano.
- **Comparação justa:** o modelo, a regra e a ingênua (persistência) dão o **mesmo número de alertas** em cada ano. O número que decide é o acerto, ou seja, a parte dos alertas seguida de muito fogo.
- **Dados:** série diária montada dos arquivos anuais públicos do FIRMS (VIIRS S-NPP, Brasil, 2012 a 2024), com a limpeza do `pipeline.py`. **Ela reproduz o banco da frente A:** o backtest sobre ela dá Crítico em 4,39% das semanas, acerto de 21,2% e ganho de +3,13 pontos (a rodada da frente A no banco deu 4,4%, 21,2% e +3,1), e +6,12 com o piso contínuo (+6,0 no banco).

**Regra para uma pista ficar no modelo, fixada antes das rodadas de clima:** melhorar o ganho em pelo menos 5 dos 7 anos de teste **e** em média pelo menos +0,5 ponto sobre o modelo só de fogo.

## Resultado

### Contra a `v1` (piso contínuo), a regra que vai para a tela

Modelo só de fogo, com o número de alertas da `v1` em cada ano:

| Ano | Alertas | Acerto do modelo | Acerto da `v1` | Acerto da ingênua | Ganho sobre a `v1` |
| --- | --- | --- | --- | --- | --- |
| 2017 | 6.646 | 25,7% | 25,1% | 16,0% | +0,7 |
| 2018 | 3.992 | 15,9% | 14,7% | 10,5% | +1,2 |
| 2019 | 6.928 | 24,3% | 23,9% | 18,1% | +0,3 |
| 2020 | 7.604 | 28,8% | 27,2% | 22,4% | +1,6 |
| 2021 | 5.927 | 27,0% | 25,9% | 19,9% | +1,1 |
| 2022 | 5.990 | 27,2% | 28,3% | 23,8% | **−1,1** |
| 2023 | 6.983 | 35,8% | 33,4% | 27,2% | +2,4 |
| **Média 2017 a 2023** | | **26,4%** | **25,5%** | **19,7%** | **+0,9** |
| 2024 (relato) | 7.242 | 39,2% | 36,7% | 33,6% | +2,5 |

- O modelo ganha da `v1` em 6 de 7 anos, por **menos de 1 ponto** em média. Ele separa bem as semanas (AUC média de 0,84), mas, com o mesmo número de alertas, escolhe quase as mesmas células que a `v1`.
- Contra a regra antiga (piso só na mediana zero), o ganho era de +2,8 pontos. A diferença veio de a `v1` ser uma regra melhor, não de o modelo piorar.
- O modelo não foi testado nas variações do gabarito (P80, P95, mínimo de 5 e de 20) nem com intervalo de confiança. Pelo critério que a `v1` teve de cumprir, **não dá para afirmar que o modelo ganha dela**.
- **2024 não é teste virgem:** ele apareceu em várias rodadas exploratórias. Fica como relato. As decisões usaram só 2017 a 2023.

### O clima e o ONI não ajudaram

| Pistas somadas às de fogo | Anos melhores que só fogo (de 7) | Diferença média | Resultado |
| --- | --- | --- | --- |
| ONI | 1 | −2,0 pontos | fora |
| Chuva bruta | 3 | +0,2 | fora |
| Anomalias de chuva, temperatura e umidade | 2 | −0,6 | fora |
| Clima completo (chuva, temperatura, umidade e vento, brutos e anomalias) | 2 | −0,5 | fora |

As diferenças do clima são contra a `v1`. A do ONI e a da chuva bruta, de rodadas anteriores, são contra a regra antiga, e a comparação "com e sem a pista" vale igual.

- As pistas que mais pesam são as detecções recentes (30, 7 e 14 dias), a temperatura máxima, o normal e a tendência. O modelo usa o clima, mas ele repete o que o fogo recente já diz: onde está seco e quente, já está queimando.
- **O ONI** é um número único para o país, que muda devagar. Em 13 anos há poucos episódios de El Niño e La Niña para o modelo aprender, e o efeito do fenômeno é diferente em cada região. Ele pode servir como **texto de cenário** ("se o El Niño previsto se confirmar..."), com a previsão da NOAA, mas não como pista validada.

## Decisão

1. **O modelo da pergunta "fogo acima do normal?" não entra no produto.** Menos de 1 ponto de ganho não justifica trocar uma regra transparente por um modelo de 13 pistas. O alerta continua sendo a `v1`. (O modelo da pergunta "onde vai ter fogo?" **entra**, ver a seção seguinte.)
2. **O resultado entra na tela de Método** como prova de que a regra simples foi testada contra um modelo treinado. Sugestão de frase, em inglês:
   > *We also trained a machine-learning model on 13 years of fire history plus rainfall, temperature, humidity, wind and El Niño data. With the same number of alerts, it was right only 0.9 points more often than rule v1 (26.4% vs 25.5%, 2017–2023), so we kept the simpler, explainable rule.*
3. **O código fica no repositório** (`data-pipeline/validacao/modelo_risco.py`), com testes, para quem quiser refazer.

## Segunda pergunta: "onde vai ter fogo nos próximos 14 dias?" (entra no produto)

Decisão do Weberson (15/11/2026). A pergunta é outra: não "vai passar do normal?", e sim **em quais células de ~1.770 km² haverá fogo relevante (10 ou mais detecções) nos 14 dias seguintes**. É o que um comandante precisa para posicionar equipes.

**O modelo** é um gradient boosting com 10 variáveis, todas da contagem diária de detecções por célula: fogo de 7, 14 e 30 dias, tendência, fogo nas células vizinhas, o que aconteceu na mesma época em anos anteriores, semana do ano e posição. Ele dá uma **probabilidade** para cada célula, que vira faixa de risco (`config/risk_rules.json`).

| Faixa | Probabilidade | Frequência observada de fogo relevante nos 14 dias seguintes | Parte das células |
| --- | --- | --- | --- |
| Muito alto | 60% ou mais | **82%** | 11% (29% na temporada de ago a out) |
| Alto | 40% a 60% | 46% | 5% |
| Médio | 20% a 40% | 27% | 7% |
| Menor | abaixo de 20% | 3% | 77% |

Teste ano a ano, treinando só com anos anteriores (2021 a 2024, sem o Pantanal, que tem anomalias): a probabilidade prevista fica a cerca de 4 pontos da observada, na temporada e fora dela, então a legenda vale o ano todo.

**O que o teste mostrou**
- Contra a melhor régua simples (fogo dos últimos 30 dias mais a média da mesma época), o modelo acerta **2,4 pontos a mais** nas 10% de células mais arriscadas (59,7% contra 57,5%, com o modelo base de 12 variáveis), em 8 de 8 anos.
- **Mais variáveis não ajudam.** Dez variáveis extras (fogo de 90 dias, dias com fogo, dias desde o último fogo, vizinhança de 2º anel, frequência histórica da janela) somaram só +0,1 a +0,2 ponto, abaixo do critério de +0,5 fixado antes. O clima da NASA POWER (chuva, temperatura, umidade e vento, só do passado, em grade de ~55 km) também não ajudou **neste teste, que foi parcial** (6 de 8 anos: melhorou em 0 de 6, média de −0,15 ponto). Isso **não é uma conclusão sobre clima em geral**: o clima foi testado com mais cuidado só na pergunta antiga ("acima do normal?"), e a comparação com o índice oficial de risco de fogo do INPE (120 dias de chuva, dias sem chuva, vegetação) está em andamento. Para subir o acerto, o que falta é informação nova (previsão do tempo, secura da vegetação), e não mais variáveis de fogo.
- Dentro de cada bioma o ranking funciona (49% a 62% de acerto nas 10% mais arriscadas), exceto no Pampa, onde quase não há fogo.

**Comparação com o índice oficial de Risco de Fogo do INPE (15/11/2026, exploratória).** O INPE publica um índice diário de 0 a 1 de **propensão** da vegetação a queimar (chuva dos últimos 120 dias, dias sem chuva, temperatura, umidade, tipo de vegetação e focos recentes), em arquivos NetCDF de ~1 km (versão 2.2). Comparei os domingos de **quatro anos (2021 a 2024)**, mais de 200 semanas (arquivos do servidor público do INPE, todos da mesma versão 2.2), com o índice convertido para as nossas células e o mesmo alvo (10 ou mais detecções nos 14 dias seguintes), sem o Pantanal. Em cada ano de teste, o nosso modelo foi treinado só com os anos anteriores. O critério foi fixado antes de rodar: a conclusão só se mantém se o nosso modelo ganhar do INPE em **cada** um dos anos.

| Ano | Acerto nas 10% mais arriscadas: nosso modelo | Régua simples | Índice do INPE | AUC: nosso | AUC: INPE |
| --- | --- | --- | --- | --- | --- |
| 2021 | **59%** | 57% | 27% | 0,947 | 0,776 |
| 2022 | **59%** | 57% | 25% | 0,944 | 0,739 |
| 2023 | **63%** | 60% | 29% | 0,948 | 0,763 |
| 2024 | **64%** | 61% | 31% | 0,952 | 0,808 |

Na temporada (ago a out) o nosso acerto fica entre 94% e 98% e o do INPE entre 54% e 55%; fora dela, 46% a 53% contra 15% a 23%.

- **O INPE ordena pior que o nosso modelo para esta pergunta, em todos os anos**, e não acrescenta informação a ele: numa regressão com validação cruzada por semana, o acerto nas 10% mais arriscadas é o mesmo com e sem o INPE nos quatro anos (diferença máxima de −0,01 ponto). Os dois critérios fixados antes de rodar foram mantidos.
- **Isso não diz que o INPE seja um mau indicador de perigo.** Ele mede a secura do combustível, que é outra coisa; o nosso alvo é a contagem de detecções, que depende muito do fogo recente (variável que o nosso modelo usa). A comparação mostra só que, **para "onde vai ter fogo nos próximos 14 dias", o índice não melhora o nosso modelo**.
- Limites: quatro anos (2021 a 2024), todos com a mesma versão do índice; o índice de ~1 km foi reduzido à média sobre as células de ~1.770 km²; a combinação foi linear (uma interação com a época do ano ou com o bioma não foi testada); a previsão de 3 dias do INPE não foi usada.
- **Hipóteses de viés testadas para tentar derrubar a conclusão** (todas refutadas: o nosso modelo continua à frente; os quatro primeiros testes em 2024, sem o Pantanal, AUC e acerto nas 10% mais arriscadas; o de células quietas foi repetido nos quatro anos e deu 0,92 a 0,94 para o nosso modelo contra 0,76 a 0,84 do INPE):
  - **A média escondia o INPE?** Não: com o máximo da célula o INPE tem AUC de 0,796 e acerto de 32%; com o P90, 0,795 e 32%; com a média, 0,808 e 31%. O nosso modelo: 0,952 e 64%.
  - **O alvo favorece quem usa fogo recente?** Não: em células quietas nos 30 dias anteriores (início de fogo), o nosso AUC é 0,92 contra 0,81 do INPE; com 1 a 9 detecções, 0,86 contra 0,72; com 10 a 99, 0,85 contra 0,69; com 100 ou mais, 0,89 contra 0,68.
  - **O INPE ganha em algum bioma?** Não: Amazônia 0,97 contra 0,86, Caatinga 0,93 contra 0,70, Cerrado 0,93 contra 0,79, Mata Atlântica 0,92 contra 0,78 e Pampa 0,89 contra 0,55.
  - **O INPE ganha em horizontes curtos?** Não: com alvo de 5 ou mais detecções em 3 dias, nosso 0,94 contra 0,80; em 7 dias, 0,95 contra 0,81.
  - **Um só ano (2024, excepcional)?** Não: o resultado se repete em 2021, 2022 e 2023, com o nosso acerto 27 a 34 pontos acima do INPE em todos os anos.
  - **Ainda não refutada:** o alvo é de detecções e, portanto, é "nosso": um alvo próprio do INPE (por exemplo, área queimada) não foi testado. Também não foram testados 2025 e 2026.
- **Uso no projeto (decisão do Weberson, 15/11/2026):** o índice do INPE fica registrado como **validação externa**: uma comparação independente com a referência oficial (o INPE é agência parceira), e **não** entra no modelo. Integrá-lo ao job pediria ler NetCDF todo dia e cruzar com as células, sem ganho medido.
- **Texto para a tela de Método (inglês).** Por regra da equipe, a tela não usa "validated" nem "accuracy", e o texto precisa dizer que as duas medidas são diferentes:
  > *We benchmarked our model against INPE's official fire-risk index over four years (2021–2024). INPE's index measures how dry and flammable the vegetation is, not where satellite detections will occur. For the question we answer (10 or more detections in a 1,770 km² area over the next 14 days), our model ranked areas better in every year: 59–64% of its top 10% areas had significant fire, against 25–31% for INPE's index.*
- Citar o INPE em "Data & credits" e nas referências da página do projeto (o `INPE, Programa Queimadas` já consta).

**Como entra no produto:** o cálculo roda **fora da API**, no job `data-pipeline/risco_celulas.py`, que treina com tudo o que existe até a data, pontua as células e grava em `risco_celulas` (migration 005). A API só lê a tabela (combinado na issue #90). Não há modelo nem scikit-learn no backend.

**Exemplo real, só com dados até a data** (o modelo não viu os 14 dias seguintes):

| Data | Células com fogo relevante nos 14 dias seguintes | Muito alto: previsto / observado | As 10% mais arriscadas acertaram |
| --- | --- | --- | --- |
| 8/9/2024 (pico) | 45% | 86% / 82% | 99% |
| 4/2/2024 (fora do pico) | 3% | 80% / 71% | 23% |

São duas datas escolhidas para ilustrar, e não uma medição. Na segunda, as faixas média e alta ficaram abaixo do previsto (12% e 34% observados, para 28% e 50% previstos). Isso é bem mais que a diferença média de cerca de 4 pontos medida em 2021 a 2024: numa data isolada o desvio pode ser grande, e a legenda mostra uma média do passado.

**Limites**
- O teste foi exploratório e sem o Pantanal. O treino usa semanas que terminam no domingo, e o job aplica o modelo em qualquer dia, o que não foi testado.
- As faixas e as taxas são do modelo final de 10 variáveis, o mesmo do job. Tirar a potência do fogo e o bioma não custou nada (acerto das 10% mais arriscadas: 59,7% nos dois modelos, em 2017 a 2024).
- O job precisa do banco com `agregados_diarios` e de um servidor onde rodar. Sem a VPS, as notas podem ser calculadas no banco local e levadas no dump.
- A frequência de uma faixa é uma média do passado, e não uma previsão para aquele lugar.

## Validação com área queimada da NASA (issue #107)

O modelo prevê detecções do VIIRS a partir de detecções do VIIRS. Para ver se as faixas acompanham o fogo de verdade, e não só o próprio gabarito, comparamos com uma medida independente: a **área queimada do MCD64A1 v061 da NASA** (MODIS, 500 m, banda "Burn Date" com o dia da queima), que mapeia a cicatriz pela mudança de reflectância, com outro sensor e outro método. O MapBiomas Fogo, a primeira opção, estava com o download suspenso.

**Critério fixado antes de rodar (15/11/2026).** Unidade: célula H3 res 4 num domingo `t` de 2021 a 2024, na Amazônia (bioma 1 do IBGE, pelo centro da célula). Modelo: o de `risco_celulas.py`, treinado só com os anos anteriores ao de `t` (um treino por ano), com a série do banco. Área queimada: soma dos pixels com "Burn Date" em `t+1..t+14`, a mesma janela do alvo do modelo.

1. Em **todos** os anos, a área queimada média cai de faixa em faixa (muito alto > alto > médio > menor).
2. AUC da nota contra "1 km² ou mais queimado nos 14 dias seguintes" de pelo menos **0,80**. Sensibilidade: 0,5 e 5 km².

**Resultado: os dois critérios passaram.** 2.128 células, 207 domingos, 440.496 células-domingo. Antes de confiar no número, conferimos o processamento: a área queimada total na Amazônia deu 25,3 mil km² (2021), 40,7 mil (2022), 38,1 mil (2023) e 85,4 mil (2024, o ano da seca); a banda "Burn Date" usa 0 (não queimou), -1 (sem dado), -2 (água) e 1..366; as células são as mesmas do banco (mãe da res 6 em res 4).

| Ano | Muito alto | Alto | Médio | Menor | Ordem |
| --- | --- | --- | --- | --- | --- |
| 2021 | 2,91 | 0,95 | 0,69 | 0,10 | mantida |
| 2022 | 5,12 | 1,41 | 0,77 | 0,12 | mantida |
| 2023 | 4,27 | 1,19 | 0,84 | 0,15 | mantida |
| 2024 | 10,68 | 2,01 | 1,28 | 0,20 | mantida |
| Todos | **5,84** | **1,38** | **0,89** | **0,14** | mantida |

Área queimada média (km²) por célula nos 14 dias seguintes, por faixa do modelo. Na faixa "muito alto" queima, em média, cerca de 40 vezes mais que na "menor".

| Limiar de área queimada | Células-domingo acima | AUC (todos) | 2021 | 2022 | 2023 | 2024 |
| --- | --- | --- | --- | --- | --- | --- |
| 0,5 km² | 8,2% | 0,896 | 0,879 | 0,899 | 0,901 | 0,901 |
| **1 km²** | 6,9% | **0,898** | 0,880 | 0,901 | 0,902 | 0,904 |
| 5 km² | 3,1% | 0,906 | 0,893 | 0,909 | 0,898 | 0,916 |

**O alvo do modelo e a área queimada.** Das células-domingo com fogo relevante (10 ou mais detecções em 14 dias), 36,9% tiveram 1 km² ou mais queimado, contra 2,2% das sem fogo relevante. Das que tiveram área queimada, 73,1% tinham fogo relevante. As duas medidas andam juntas, mas não são a mesma coisa: muita detecção sem cicatriz mapeada (nuvem, fumaça, queima pequena ou em área já queimada) e alguma cicatriz sem detecção.

**Limites e vieses**
- Só a Amazônia e só 2021 a 2024. Os outros biomas não foram testados.
- Nuvem e fumaça mascaram a área queimada (pixels -1), e queimas menores que ~25 ha quase não aparecem em 500 m: a área medida é um piso.
- A data de queima do MCD64A1 tem incerteza de alguns dias; uma queima perto da borda da janela pode cair na semana vizinha.
- Domingos seguidos têm janelas que se sobrepõem, então as células-domingo não são independentes, e a área média por faixa é puxada pela temporada (ago a out).
- O bioma é o do centro da célula; células na divisa entram inteiras. 35 células da Amazônia com área queimada (27,9 km² em 4 anos) não têm nenhuma detecção na série e ficam de fora.
- O produto sai com meses de atraso: valida o passado, não a nota de hoje.

**Como refazer** (dentro de `data-pipeline/`, com `pip install pyhdf` e `EARTHDATA_TOKEN` no `.env`): `python validacao/area_queimada.py baixar` (576 HDF, 2,4 GB, fora do git), `processar` e `avaliar`, que grava `relatorios/area_queimada/relatorio.txt`.

## Limites

- Escala de célula H3 res 4, avaliação semanal, horizonte de 14 dias. Em escala mais fina ou horizonte mais longo, o resultado pode ser outro.
- O gabarito do treino mede detecções do VIIRS, não área queimada. A comparação com a área queimada da NASA foi feita só na Amazônia ([seção acima](#validação-com-área-queimada-da-nasa-issue-107)).
- O clima do NASA POWER tem grade de 0,5° × 0,625° (cerca de 55 km), maior que a célula.

## Próximo passo (depois da submissão)

O que provavelmente faz diferença, e que não coube no prazo:

- **Secura da vegetação e do solo** (umidade do solo do SMAP, índices de vegetação do MODIS e do VIIRS);
- **Previsão do tempo** em vez de clima passado;
- **Alvo mais longo** (30 a 90 dias), em que a persistência do fogo pesa menos;
- testar o modelo nas variações do gabarito e com intervalo de confiança por bootstrap em blocos de ano.

## Como refazer

Dentro de `data-pipeline/`:

```bash
python validacao/modelo_risco.py --viirs viirs-snpp_2012_Brazil.csv ... viirs-snpp_2024_Brazil.csv --gravar-serie serie.parquet
python validacao/modelo_risco.py --serie serie.parquet --clima pasta_do_power --biomas Biomas_250mil.zip --saida relatorios/risco
```

Os arquivos do FIRMS são os anuais por país (`firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{ano}/viirs-snpp_{ano}_Brazil.csv`). O clima vem da API diária regional do NASA POWER (`PRECTOTCORR`, `T2M_MAX`, `RH2M`, `WS2M`), um parquet por variável e ano. Sem banco e sem gravar nada fora da pasta de saída.
