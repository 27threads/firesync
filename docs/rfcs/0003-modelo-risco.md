# RFC 0003: Modelo de risco treinado (experimento)

- **Status:** Experimento concluído em 15/11/2026. O modelo da pergunta "fogo acima do normal?" não entra no produto. O **modelo treinado de "onde vai ter fogo?" entra** como o risco dos próximos 14 dias (seção "Segunda pergunta"), e a `v1` entra como **nível de alerta**, com a frequência histórica como contexto (decisão 4). O alerta da submissão continua sendo a regra `v1` ([RFC 0001](0001-backtest-alerta.md)). Decisão do Weberson (frente B)
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
4. **A `v1` entra no produto como *nível de alerta* ("fora do normal para a época"), e a palavra "risco" fica para o modelo treinado (Weberson, 15/11/2026).** O backtest da `v1` responde, por nível, com que frequência houve muito fogo nos 14 dias seguintes, na mesma célula de resolução 4 em que foi medido. Isso é o contexto do nível de alerta, e não o risco dos 14 dias do modelo; assim a tela não mostra duas medidas de "risco" na mesma célula:

   | Nível da `v1` | Parte das semanas | Seguido de muito fogo nos 14 dias seguintes | Em relação à média (4,2%) |
   | --- | --- | --- | --- |
   | Normal | 85% | 2,6% | 0,6× |
   | Atenção | 12% | 10,7% | 2,5× |
   | Crítico | 3% | 26,6% | 6,3× |

   O mapa de focos recentes, que é a entrada principal do usuário, passa a marcar cada célula de resolução 4 com o seu nível e a listar "onde olhar primeiro" (Crítico, depois Atenção), com essa frequência (`docs/api.md`, `GET /detections/recent`, bloco `alerts`). As taxas ficam no `alert_rules.json` 1.1. É uma frequência do passado, não uma previsão. **Limite declarado:** metade (52%) das semanas de muito fogo acontece em células que estavam em Normal.

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

## Acerto na Amazônia (2021 a 2024)

Só as células do bioma Amazônia (2.129 células, pelo centro da célula), todos os domingos de 2021 a 2024, treinando cada ano só com os anteriores. Alvo: 10 ou mais detecções VIIRS nos 14 dias seguintes. "Aviso" é uma nota de 50% ou mais.

| Pergunta | Resultado |
| --- | --- |
| Quando o modelo avisa, houve fogo relevante? (precisão) | **78,5%** |
| Dos locais com fogo relevante, quantos foram avisados? (cobertura) | **74,0%** |
| Em quantas células ele acertou, avisando ou não? (acerto geral) | 93,7%, contra 86,3% de quem dissesse sempre "sem fogo" |

O acerto geral **exagera**, porque a maioria das células não tem fogo. Mostrar a precisão e a cobertura, e nunca o acerto geral sozinho.

| | Ago a out | Resto do ano |
| --- | --- | --- |
| Células com fogo relevante | 34% | 7% |
| Precisão | 82% | 71% |
| Cobertura | 81% | 61% |

Fora da temporada o modelo deixa passar quase 4 de cada 10 locais com fogo relevante. Por ano (precisão e cobertura): 2021, 73% e 77%; 2022, 77% e 71%; 2023, 82% e 73%; 2024, 81% e 76%. O AUC é de 0,970 (0,966 a 0,972 por ano).

Faixas do mapa na Amazônia: muito alto (11% das células) teve fogo relevante em 83%; alto (4%), em 45%; médio (5%), em 27%; menor (80%), em 2%. São as mesmas taxas do Brasil (82%, 46%, 27%, 3%).

**Calibração:** a nota média é 14,1% e a frequência observada é 13,7%. Mas no meio da escala (notas de 30% a 80%) o modelo **exagera de 3 a 5 pontos percentuais** (no máximo 5,2). Exemplo: nota de 65% e frequência observada de 60%. Nos extremos (abaixo de 20% e acima de 80%) a diferença é de 0 a 2 pontos. O erro é para o lado de avisar um pouco demais. "Ponto percentual" é a diferença entre duas porcentagens da mesma coisa: 65% menos 60% são 5 pontos, e não 5% de erro.

## Acerto por bioma

Mesmo modelo (treinado até 2020), mesmos domingos de 2021 a 2024, mesma regra de aviso (nota de 50% ou mais), para a comparação ser justa. Alvo: 10 ou mais detecções VIIRS nos 14 dias seguintes. A célula entra no bioma pelo centro dela.

| Bioma | Células | Fogo relevante | Precisão | Cobertura | Acerto geral | AUC |
| --- | --- | --- | --- | --- | --- | --- |
| Amazônia | 2.129 | 13,7% | 77,8% | **74,5%** | 93,6% | **0,970** |
| Caatinga | 408 | 19,9% | **81,4%** | 62,9% | 89,8% | 0,940 |
| Cerrado | 1.020 | 23,2% | 77,2% | 67,1% | 87,8% | 0,918 |
| Mata Atlântica | 613 | 12,9% | 64,5% | 45,9% | 89,8% | 0,888 |
| Pantanal | 88 | 13,5% | 64,7% | 45,9% | 89,3% | 0,853 |
| Pampa | 132 | 2,7% | 39,7% | 8,1% | 97,2% | 0,864 |
| **Brasil (com o Pantanal)** | 4.598 | 15,4% | 76,5% | 66,4% | 91,7% | 0,947 |

- **Precisão:** dos avisos, quantos tiveram fogo relevante. **Cobertura:** dos locais com fogo relevante, quantos foram avisados. **Acerto geral:** parte das células em que o modelo acertou, avisando ou não, e que exagera, porque a maioria das células não tem fogo (dizer sempre "sem fogo" acerta 84,6% no Brasil). **AUC:** em um par de células, uma com fogo e outra sem, a chance de o modelo dar a nota maior à que teve fogo.
- **A Amazônia é o melhor caso**, principalmente na cobertura. O Brasil fica abaixo porque a média inclui os biomas onde o modelo é fraco. No Pampa o fogo relevante é raro (2,7%) e o modelo avisa só 8% dele.
- **Pantanal: cautela.** São só 88 células, e o fogo de 2020 foi muito acima do normal e entra no treino. Os números dele são menos confiáveis que os dos outros biomas. Ele ficava fora dos testes e entra aqui, a pedido da equipe, como bioma separado e no total do Brasil (sem ele o Brasil dava 76,6% e 66,8%).
- **Método:** esta tabela usa um modelo só (treino até 2020), e a seção "Acerto na Amazônia" usa um treino por ano (cada ano treinado só com os anteriores). Por isso a Amazônia dá 77,8% e 74,5% aqui, e 78,5% e 74,0% lá. A diferença vem do método.
- Na temporada (ago a out) e fora dela: na Amazônia, 82,3% de precisão e 81,6% de cobertura na temporada, e 69,4% e 62,4% fora; no Brasil, 79,2% e 77,7% na temporada, e 71,3% e 50,9% fora.

## O que foi testado e não melhorou (e foi registrado mesmo assim)

Os resultados abaixo vêm de scripts locais que ainda não estão versionados no repositório. Os critérios foram fixados antes de rodar cada teste.

### Mais anos de histórico (o que um MODIS de 2002 a 2011 acrescentaria)

O modelo de risco **não usa o MODIS**: só contagens do VIIRS S-NPP de 2012 em diante. O MODIS entra na harmonização do modelo A, e não no treino. Para saber se mais histórico ajudaria, treinei o mesmo modelo com 3, 5, 7 e 8 anos e testei nos mesmos domingos de 2021 a 2024 (Brasil sem o Pantanal):

| Anos de treino | AUC | Brier | Amazônia: precisão e cobertura |
| --- | --- | --- | --- |
| 3 | 0,9464 | 0,0618 | 75,1% e 76,8% |
| 5 | 0,9464 | 0,0612 | 76,5% e 75,1% |
| 7 | 0,9474 | 0,0604 | 77,8% e 74,1% |
| 8 | 0,9479 | 0,0602 | 77,8% e 74,5% |

De 7 para 8 anos o AUC sobe 0,0004 e o Brier cai 0,4%. A curva já está achatada, e dobrar o histórico com o MODIS harmonizado traria pouco ganho e o erro da harmonização. Limite: a curva vai até 8 anos de treino, e não 20.

### Ajuste dos parâmetros

O modelo usa os valores padrão (200 rodadas, taxa 0,1, 31 folhas) e nunca foi ajustado. Escolhi a melhor entre 6 configurações num período de validação (treino até 2018, validação 2019 e 2020) e só depois testei em 2021 a 2024 (treino até 2020), contra o padrão. Critério: o AUC sobe 0,005 ou o Brier cai 2%, em pelo menos 3 dos 4 anos.

| | AUC | Brier | Amazônia: precisão e cobertura |
| --- | --- | --- | --- |
| Padrão | 0,9479 | 0,06017 | 77,8% e 74,5% |
| Escolhida (400 rodadas, taxa 0,05) | 0,9480 | 0,06006 | 78,1% e 74,4% |

Ganho de +0,0001 no AUC e +0,2% no Brier, em 0 dos 4 anos: **sem ganho relevante**. Na validação, as seis configurações ficaram entre 0,0596 e 0,0599 de Brier. Limite: só seis configurações.

### Dias da semana

O modelo é treinado só em domingos e usado em qualquer dia. Apliquei o modelo (treino até 2020) a cada dia da semana de 2021 a 2024, de 3 em 3 semanas, com as mesmas semanas para os sete dias (69 datas por dia). Critério: nenhum dia pode ficar mais de 0,005 de AUC abaixo, nem mais de 2% de Brier acima, do domingo.

| Dia | AUC | Brier | Amazônia: precisão e cobertura |
| --- | --- | --- | --- |
| Domingo | 0,9495 | 0,0592 | 77,5% e 75,0% |
| Segunda | 0,9502 | 0,0587 | 78,5% e 74,4% |
| Terça | 0,9504 | 0,0587 | 78,0% e 74,7% |
| Quarta | 0,9502 | 0,0589 | 78,0% e 75,0% |
| Quinta | 0,9494 | 0,0592 | 78,3% e 75,2% |
| Sexta | 0,9484 | 0,0597 | 78,4% e 75,4% |
| Sábado | 0,9481 | 0,0600 | 79,1% e 75,1% |

Ressalva: são 69 datas por dia da semana, de 3 em 3 semanas, **as mesmas semanas para os sete dias**; por isso a comparação entre os dias é justa, mas o AUC do domingo desta tabela (0,9495) não deve ser comparado com o das outras tabelas (por exemplo, 0,9479). A pior queda de AUC é de 0,0014 e a pior alta de Brier é de 1,4% (sábado), dentro dos limites: **o dia da semana não importa**. Sexta e sábado ficam um pouco piores, e sábado é o que mais se aproxima do limite de Brier.

### O dia de hoje, ainda incompleto

O job roda a cada 3 horas, e o dia corrente entra nas janelas de 7, 14 e 30 dias com só parte dos dados. Simulei, com o VIIRS S-NPP de 2022 a 2024, o que o job enxerga em cada hora (domingos de 3 em 3 semanas, 53 datas, sem o Pantanal, treino só com anos anteriores). De manhã (até 12:00 UTC) chega de 25% a 43% do dia; às 18:00 UTC, de 92% a 98%.

| | Erro de calibração | Brier | AUC | Acerto nas 10% mais arriscadas |
| --- | --- | --- | --- | --- |
| Dia completo | +0,10 pp | 0,0586 | 0,9494 | 62,2% |
| Manhã (dia parcial) | −0,19 pp | 0,0591 | 0,9487 | 62,0% |
| Ontem (`hoje − 1`) | +0,19 pp | 0,0595 | 0,9482 | 61,9% |

Na manhã, 0,92% das células descem uma faixa. Usar ontem é um pouco pior que usar o dia parcial, e 3,2% das células mudam de faixa (1,4% descem e 1,8% sobem). **Decisão:** o job continua pontuando com o dia corrente. Limite: o corte por horário simula o que já chegou, e não os atrasos e lotes reais do NRT.

### O que não foi testado, e por quê

**Aprendizado por reforço** ("voltar no tempo, ver o gabarito e ajustar"): não testado. O gabarito é conhecido para cada exemplo, então o problema é de aprendizado supervisionado, e o gradient boosting já se ajusta contra o gabarito, rodada a rodada. Não há decisões que mudem o ambiente. O teste em avanço (treinar só com anos anteriores) já é a forma de "voltar no tempo" sem decorar o passado.

**Conclusão dos testes:** o modelo parece estar no teto do que as 10 variáveis atuais permitem. Mais anos, ajuste de parâmetros e outros dias da semana não mudam o resultado. Para a acurácia subir, precisam entrar variáveis novas (ver o próximo passo).

## Limites

- Escala de célula H3 res 4, avaliação semanal, horizonte de 14 dias. Em escala mais fina ou horizonte mais longo, o resultado pode ser outro.
- O gabarito mede detecções do VIIRS, não área queimada.
- Só quatro anos de teste (2021 a 2024), com domingos. Falta testar 2025 e 2026 fora da amostra.
- **Troca de satélite (S-NPP para NOAA-20): testada, sem prejuízo** (Eduardo, issue 102). O modelo foi treinado só com S-NPP, e o banco usa o NOAA-20 desde 01/11/2026. De abril de 2018 a 2024, o NOAA-20 vê 0,99 vez o S-NPP (0,97 a 1,03 por ano). Pontuando 69 domingos de 2021 a 2024 com o modelo treinado até 2020: só S-NPP, AUC 0,9490 e Brier 0,0592; **últimos 30 dias do NOAA-20 e o resto S-NPP (como na produção)**, AUC 0,9496 (+0,0007) e Brier 0,0586 (−0,9%); só NOAA-20, AUC 0,9483 e Brier 0,0600 (perde um pouco por não ter os anos antes de 2018). Dentro do critério (AUC −0,005 ou Brier +2%). Limite: o gabarito vem do S-NPP; não foi testado com o alvo pelo NOAA-20.
- **Dado em tempo real (NRT) contra dado de arquivo (SP): não dá para testar hoje.** O modelo foi treinado com arquivo e o job pontua com NRT, que é provisório. O banco apaga o NRT quando o SP chega, e o SP do FIRMS só vai até 31/07/2026, onde o NRT começa (01/08). Não há período com os dois. Para testar, é preciso esperar o SP de agosto em diante, ou guardar o NRT de um período antes de o SP chegar.
- **Atribuição de célula:** a série de teste usa `latlng_to_cell` e o banco usa o pai da célula de resolução 6, e cerca de 6% das detecções caem em célula diferente (achado da auditoria). As faixas e as taxas (82%, 46%, 27% e 3%) vêm da atribuição de teste e serão recalculadas com a do banco.
- **Pantanal:** poucos dados (88 células) e um ano anômalo no treino. Interpretar com cautela.
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
