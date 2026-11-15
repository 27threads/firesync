# Validação do modelo de risco com a área queimada da NASA

Este documento explica, em linguagem simples, como testamos se o mapa de risco acerta, e o que o teste mostrou. Os números completos e o método técnico estão no [RFC 0003](rfcs/0003-modelo-risco.md#validação-com-área-queimada-da-nasa-issue-107). Issue: #107.

## A pergunta

O modelo de risco dá a cada pedaço do Brasil (hexágono H3 de ~1.770 km²) a chance de ter **fogo relevante nos próximos 14 dias**: 10 ou mais detecções do satélite VIIRS. Essa chance vira uma faixa no mapa: **muito alto** (60% ou mais), **alto** (40% a 60%), **médio** (20% a 40%) e **menor** (abaixo de 20%).

A dúvida: **a faixa acerta onde o fogo de fato acontece?**

## Por que um "corretor de fora"

O modelo aprende com focos de calor do VIIRS e é avaliado contra focos do VIIRS. Seria como o aluno corrigir a própria prova. Por isso usamos uma medida **independente**: a **área queimada do MCD64A1 v061 da NASA**. Ela vem de outro satélite (MODIS), mede outra coisa (a cicatriz que o fogo deixa no chão, pela mudança de cor da superfície, em pixels de 500 m) e marca o dia em que cada pixel queimou.

## Como foi feito: "voltar no tempo"

1. Para cada domingo de 2021 a 2024, o modelo foi treinado **só com os anos anteriores**. Para pontuar 2023, por exemplo, ele só conhecia até 2022. Ele nunca viu o futuro que estava prevendo.
2. Com isso, ele deu a nota de cada hexágono da Amazônia naquele domingo.
3. Depois comparamos com o que a NASA mapeou como queimado **nos 14 dias seguintes**.

São 2.128 hexágonos × 207 domingos, cerca de **440 mil previsões**.

**A régua foi fixada antes de rodar**, para não ajustá-la ao resultado:

- **Regra 1, a escadinha:** em todo ano, a área queimada média tem que cair de faixa em faixa (muito alto > alto > médio > menor).
- **Regra 2, a nota separa bem:** pegando um lugar que queimou (1 km² ou mais) e um que não queimou, o modelo tem que dar a nota maior para o que queimou em pelo menos 80% das vezes (AUC ≥ 0,80).

Antes de confiar no resultado, conferimos o processamento. A área queimada na Amazônia deu de 25 mil a 85 mil km² por ano (o pico em 2024, o ano da seca). O arquivo da NASA tem os valores esperados. Os hexágonos são os mesmos do banco.

## Resultado: passou nas duas regras

**Regra 1.** A escadinha se manteve nos quatro anos. Área queimada média por hexágono nos 14 dias seguintes, de 2021 a 2024:

| Faixa | Área queimada média | Parte das previsões | Parte de toda a área queimada |
| --- | --- | --- | --- |
| Muito alto | 5,84 km² | 11% | **75,5%** |
| Alto | 1,38 km² | 3,7% | 6,0% |
| Médio | 0,89 km² | 5,1% | 5,3% |
| Menor | 0,14 km² | 80% | 13,3% |

**Regra 2.** O AUC deu **0,898**, entre 0,880 e 0,904 em cada ano. Em cerca de 9 de cada 10 pares, o lugar que queimou recebeu a nota maior.

**Em palavras simples:**

- A faixa "muito alto" é só 11% das previsões e concentrou **três quartos de toda a área queimada**.
- Quando o modelo **não** avisa ("menor" ou "médio"), 97,5% das vezes não queimou.
- Dos lugares que queimaram, **69% estavam avisados** ("alto" ou "muito alto").

## Os lugares que queimaram sem aviso

23% das queimadas caíram na faixa "menor". Olhando um por um:

- **Em 81% deles, nem o VIIRS viu fogo relevante.** Pelo próprio alvo do modelo, não havia fogo para prever.
- **Mais da metade está no sul da Amazônia, de dezembro a abril**, na época de chuva. Fogo de verdade é raro nessa época. A explicação provável, ainda não comprovada, é que a NASA registrou a cicatriz com atraso: o fogo foi na seca, debaixo de fumaça e nuvem, e só "apareceu" quando o céu abriu.
- **Os erros de verdade**, em que os dois satélites viram fogo e o modelo deu nota baixa, são **cerca de 4,5% de todas as queimadas**. Quase todos são o fogo que "começa do nada": estação seca, num lugar sem nenhum foco no mês anterior. O modelo só olha fogo passado, então não tem pista nesses casos.

## Observação: o modelo pode ser ainda melhor do que o medido

O mapa da NASA **não marca todo fogo que existiu**:

- **o fogo é pequeno:** o pixel tem 500 m (~25 ha), e queimada menor que isso, ou em faixa estreita, quase não aparece;
- **havia nuvem ou fumaça:** sem enxergar o chão, o pixel vira "sem dado", e na temporada a fumaça é pesada;
- **o lugar já tinha queimado:** se queimou de novo no mesmo ano, ou é pasto queimado todo ano, a mudança de cor é pequena;
- **o fogo é de sub-bosque:** queima por baixo da copa da floresta, e o satélite vê a copa verde;
- **a data cai fora da janela:** o dia da queima tem incerteza de alguns dias.

Os números confirmam: das semanas com 10 ou mais focos VIIRS, só 37% tiveram cicatriz de 1 km² ou mais mapeada. Então parte dos "erros" do modelo é **falta de registro na referência**, e não erro de previsão. Os 69% de queimadas avisadas são um **piso**: o acerto real tende a ser maior.

## Limites

- Testado só na Amazônia e só de 2021 a 2024. Os outros biomas não foram testados.
- Domingos seguidos têm janelas de 14 dias que se sobrepõem, então as previsões não são todas independentes.
- A área queimada da NASA sai com meses de atraso. Ela valida o passado, não a nota de hoje.
- O teste mostra que o modelo **aponta onde vai queimar**. Ele não mede quanto fogo uma ação feita a partir do mapa evitaria.

## Decisão

O resultado é bom para o que o modelo propõe. A equipe decidiu (15/11/2026) **não mexer mais no modelo** antes da submissão. O que poderia ajudar depois (desmatamento recente, secura da vegetação, previsão do tempo, para o fogo que "começa do nada") está em [Próximo passo no RFC 0003](rfcs/0003-modelo-risco.md#próximo-passo-depois-da-submissão).

## Como refazer

Dentro de `data-pipeline/`, com `pip install pyhdf` e uma conta do NASA Earthdata (`EARTHDATA_TOKEN` no `.env`):

```bash
python validacao/area_queimada.py baixar      # 576 arquivos HDF, 2,4 GB, fora do git
python validacao/area_queimada.py processar   # área queimada por hexágono e dia
python validacao/area_queimada.py avaliar     # grava relatorios/area_queimada/relatorio.txt
```
