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
- **Mais variáveis não ajudam.** Dez variáveis extras (fogo de 90 dias, dias com fogo, dias desde o último fogo, vizinhança de 2º anel, frequência histórica da janela) somaram só +0,1 a +0,2 ponto, abaixo do critério de +0,5 fixado antes. Clima (chuva, temperatura, umidade, vento) e El Niño também não ajudam. Para subir o acerto, o que falta é informação nova (previsão do tempo, secura da vegetação), e não mais variáveis de fogo.
- Dentro de cada bioma o ranking funciona (49% a 62% de acerto nas 10% mais arriscadas), exceto no Pampa, onde quase não há fogo.

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

## Limites

- Escala de célula H3 res 4, avaliação semanal, horizonte de 14 dias. Em escala mais fina ou horizonte mais longo, o resultado pode ser outro.
- O gabarito mede detecções do VIIRS, não área queimada.
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
