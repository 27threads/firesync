# Validação do nível de alerta (solução A + B)

Nov 14, 2026 · proposta da frente A, em revisão no PR #42 · issue #9 · implementação: [RFC 0001](rfcs/0001-backtest-alerta.md)

Critérios que melhora (ver [premiacao.md](premiacao.md)): **Validity** (prova que o alerta funciona), **Best Use of Science** (número medido, com os limites declarados) e **Impact** (regra transparente e versionada).

## Contexto

A issue #9 pede para validar o nível de alerta (Normal / Atenção / Crítico) contra um gabarito, para escolher os limites da regra e mostrar na tela uma frase sobre o resultado do teste (texto fixado em "Texto da tela", abaixo).

O gabarito proposto era a **área queimada da NASA** (MCD64A1). A verificação das fontes ([comentário na #9](https://github.com/27threads/firesync/issues/9#issuecomment-6884153059)) mostrou que é viável, mas caro para o prazo:

- exige conta e token do Earthdata (o download devolve `401` sem login);
- são ~10,6 GB de HDF4 (3.432 arquivos) para o Brasil de 2012 a 2024;
- ler HDF4 pede uma biblioteca nova (`pyhdf` ou GDAL);
- são ~5 h só da frente A, antes do teste da frente B, da API e da tela.

O GlobFire só vai até 2020, e o AQ1km do INPE é mensal (sem o dia). Como a API e o front ainda não têm código, a frente A propõe um gabarito **mais simples, com dados que já estão no banco**: a solução **A + B**. A área queimada fica como próximo passo.

## O que já está validado (e não depende desta solução)

| O que | Gabarito | Resultado |
| --- | --- | --- |
| Contagem bruta (Aqua) | Série mensal do INPE (A2) | correlação 0,998, mesmo mês de pico em 23 de 23 anos |
| Série harmonizada (calendário) | INPE (B6, código corrigido, issue #40) | correlação mensal de 0,94 a 0,99 por bioma; degrau em 2012 perto de zero (Mata Atlântica −14,1% e Pampa +10,8% declarados no Método) |

Esta solução cobre o que falta: **o alerta**.

## Solução A: teste retroativo com "o que veio depois"

**Pergunta:** quando a regra disse Crítico, o fogo de fato ficou muito acima do normal nas semanas seguintes?

**Gabarito:** uma semana é de **muito fogo** quando as detecções dos **14 dias seguintes** ficam acima do **P90** das janelas de 14 dias do mesmo lugar, na mesma época (±15 dias), nos outros anos, e somam pelo menos **10 detecções** (para não contar lugares quase sem fogo).

**Dados:** só `agregados_diarios` (VIIRS, 2012-02 a 2024-12, nominal e alta, `tipo = 0`), que já está no banco. Não baixa nada e **não grava nada**: só lê e gera CSVs.

**Como roda:**

1. **Unidades de teste.** Para imitar as áreas que o usuário desenha, as células H3 res 6 são agrupadas na célula-mãe **res 4** (~1.770 km², cerca de 5 mil unidades no Brasil). Os 6 biomas inteiros também entram, para a linha da tela por bioma.
2. **Uma avaliação por semana**, de 2013 a 2024, em cada unidade. As janelas **não se sobrepõem** (ver "Janelas", abaixo).
3. **O nível de cada semana** sai da regra do `config/alert_rules.json` (hoje a `0.2`): os 7 dias contra o normal de ±15 dias, como no `recent` do [api.md](api.md). Para não usar o futuro, o normal de cada ano usa **só os outros anos** (deixa o próprio ano de fora).
4. **Grade de limites** para a frente B escolher, por exemplo: razão para Crítico em {1,5; 2; 2,5; 3}, tendência de 3 dias ligada ou desligada, Atenção acima de P75 ou P90.
5. **Comparação com uma regra ingênua** ("se esta semana está acima do P90, a próxima também está"). Uma regra só vale a pena se acertar mais do que ela. O fogo de uma semana costuma continuar na seguinte, então quase qualquer regra "acerta": o acerto do Crítico sozinho mede, em boa parte, só que o fogo continua. **O número que importa é o ganho sobre a ingênua.** Para a comparação ser justa, a ingênua também roda com a mesma frequência de alerta da regra testada (o percentil dela é ajustado até dar a mesma % de semanas em alerta).

**Janelas** (dia `t` = último dia da semana avaliada):

| Janela | Dias | Usada para |
| --- | --- | --- |
| Nível | `t−6` a `t` (7 dias) | razão contra o normal e P75 |
| Tendência | `t−2` a `t` contra `t−5` a `t−3` | condição de alta do Crítico |
| Gabarito | `t+1` a `t+14` (14 dias) | "muito fogo depois" |

O gabarito começa **no dia seguinte ao último dia usado pelo nível**. Nenhum dia entra nas duas janelas. O autoteste tem um caso com dados inventados que quebra se houver sobreposição: fogo só na semana avaliada e zero depois tem que dar "sem muito fogo".

**Números de cada regra testada:**

| Medida | O que diz | Meta da #9 |
| --- | --- | --- |
| Frequência de cada nível | % das semanas em Normal, Atenção e Crítico | Crítico em 2% a 5% |
| Acerto do Crítico | % das semanas Crítico seguidas de muito fogo | quanto mais, melhor |
| Cobertura | % das semanas de muito fogo que tiveram Crítico ou Atenção antes | quanto mais, melhor |
| Alarme falso | % das semanas Crítico sem muito fogo depois | quanto menos, melhor |
| Estabilidade | trocas de nível por unidade por mês | poucas |
| Ganho sobre a regra ingênua | acerto da regra − acerto da ingênua | positivo |

**Regra de decisão (fixada antes de rodar):**

- A `v1` só é escolhida entre as regras com **ganho positivo** sobre a ingênua (na mesma frequência de alerta), e o ganho tem que ser positivo **no total e na maioria dos anos** (pelo menos 7 dos 12). O tamanho mínimo do ganho é escolha da frente B e fica registrado aqui antes da rodada.
- **Se nenhuma regra tiver ganho positivo** (ou ele der perto de zero), a tela **não** mostra acerto. Mostra só a frequência de cada nível e o limite declarado: *"Rule v1 flags Critical in X% of weeks (2013–2024). It did not beat a simple persistence rule at anticipating high-detection weeks, so we show it as a context indicator, not a forecast."* A regra continua útil para dizer "está acima do normal", mas não é vendida como previsão.

**Saída:** `relatorios/alerta/backtest.csv` (uma linha por regra testada) e `relatorios/alerta/por_bioma.csv`.

**Texto da tela** (inglês, fixo; os números saem do `backtest.csv`; sem "validated" nem "accuracy"):

> *Rule v1, backtested 2013–2024: when it flagged Critical, the next 14 days had unusually high VIIRS detections X% of the time, Y points more than a simple persistence rule. It measures detections, not burned area.*

## Solução B: eventos conhecidos

**Pergunta:** nas crises de fogo que todo mundo lembra, o alerta teria ficado Crítico, e com quantas semanas de antecedência?

**Gabarito:** uma lista curta de crises com data, lugar e fonte, num arquivo versionado `data-pipeline/referencia/eventos_conhecidos.csv` (`nome, bioma ou UF, inicio, fim, fonte`).

**Candidatos, a confirmar cada um com fonte oficial** (INPE, Infoqueima, decreto de emergência ou relatório do governo) antes de entrar na lista:

- Pantanal, temporada de 2020;
- Amazônia, agosto de 2019;
- Pantanal, início antecipado da temporada de 2024;
- Amazônia e Cerrado, temporada de 2024.

Nenhuma data entra sem a fonte ao lado. O próprio banco ajuda a conferir o pico de cada evento.

**Números de cada evento:** o nível semana a semana no lugar do evento e a **antecedência** (quantas semanas antes do início o nível já estava em Atenção ou Crítico).

**Uso:** é **ilustração, não prova**, para a tela de Método e o vídeo ("o alerta teria ficado Crítico X semanas antes da crise de..."). As crises são conhecidas justamente porque tiveram muitas detecções, então o alerta fica Crítico nelas de qualquer jeito. A informação útil é a **antecedência**. Com poucos casos, não é estatística: a estatística é a solução A. O vídeo segue a mesma regra.

## Limites (vão para o Método)

- **O gabarito vem do mesmo sensor.** A solução A mede se o alerta **antecipa semanas de muito fogo detectado pelo VIIRS**, e não se a área realmente queimou. Isso é o que o MCD64A1 mediria (próximo passo).
- **O P90 e o mínimo de 10 detecções são escolha da equipe.** O teste mostra o resultado com outros valores, para não depender de uma escolha só.
- **Unidades res 4 não são as áreas do usuário.** Elas imitam o tamanho de uma área desenhada, mas o resultado vale "em média", não para cada polígono.
- **2025 e 2026 ficam de fora.** 2025 tem a deriva do Aqua, e 2026 ainda é NRT.

## Próximo passo (depois da submissão)

- **Área queimada completa (MCD64A1):** gabarito independente do VIIRS, ~11 GB de HDF4 (ver #9).
- **Meio-termo barato:** baixar só os blocos e meses de **um evento** (por exemplo, o Pantanal em 2020) e comparar com o nível semana a semana dali. São poucos arquivos, mas ainda exige conta no Earthdata e leitura de HDF4. Só entra se sobrar tempo.

## Divisão

| Frente | Tarefa | Esforço |
| --- | --- | --- |
| **A** | Script `data-pipeline/validacao/backtest_alerta.py`: só lê o banco, roda a solução A e o nível semana a semana dos eventos da B. Autoteste com dados inventados. Montar o `eventos_conhecidos.csv` com as fontes | ~2 h + ~1 h da lista |
| **B** | Fixar o ganho mínimo antes da rodada. Escolher a regra pela tabela (frequência, acerto e ganho sobre a ingênua) e publicar a `v1` no `alert_rules.json`. A escolha dos limites é da equipe (regra do Space Apps) | — |
| **C** | Ler a `v1` do `alert_rules.json` (já previsto) e pôr a versão no pacote de auditoria | — |
| **D** | Mostrar o texto fixo da tela ("Texto da tela", acima, ou a versão sem ganho) e um evento da B na tela de Método | — |

## Pronto quando

- O `backtest.csv` tem as medidas de cada regra testada, inclusive a ingênua na mesma frequência.
- O autoteste passa, inclusive o caso de sobreposição das janelas.
- A `v1` está no `alert_rules.json`, escolhida pela tabela e pela regra de decisão, ou a equipe registrou que nenhuma regra ganhou da ingênua.
- A tela de Método mostra o texto fixo e pelo menos um evento conhecido, com a fonte.
