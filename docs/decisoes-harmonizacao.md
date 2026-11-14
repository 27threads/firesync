# Decisões da harmonização (rascunho)

Responsável pela decisão: Weberson. Itens marcados como **ESCOLHA DA EQUIPE** são decisões nossas, não fatos. Itens marcados como **PROPOSTA** esperam confirmação.

## 1. Decisão

Seguimos um caminho do meio entre o plano de fatores por região (`importacao-regioes.md`) e o modelo A (chance de o MODIS ver cada fogo do VIIRS).

- Mantemos o **modelo A** e a **faixa de incerteza**, como diferencial.
- Treinamos com **volume menor de dados** e **período mais curto**. Para a apresentação, o modelo mostra o método e não precisa ser robusto. **ESCOLHA DA EQUIPE.**
- A faixa de incerteza fica menos confiável por usar poucos anos. Isso aparece escrito na tela de Método.

## 2. Condições de conversão (vêm do modelo A)

O fator de conversão é calculado por condição, e não um só por região:

| Condição | Valores |
| --- | --- |
| Bioma | Amazônia (Pantanal só se sobrar tempo) |
| Mês do ano | 1 a 12 |
| Dia ou noite | D e N |
| Faixa de potência (FRP) | faixas definidas na tabela por faixa de FRP |

Cada fator diz quantos fogos do VIIRS cada foco do MODIS representa naquela condição.

## 3. Recorte reduzido (CONFIRMADO pelo Weberson em 14/11/2026, ESCOLHA DA EQUIPE)

| Ponto | Proposta | Motivo |
| --- | --- | --- |
| Área | Bioma Amazônia | Pantanal é o primeiro corte, como já está no `CLAUDE.md` |
| Satélites no treino | Aqua e S-NPP | NOAA-20 e Terra ficam fora do treino |
| Anos de treino | 2019 a 2022 (4 anos) | Poucos anos, mas com variação entre anos para a faixa |
| Anos de teste | 2023 e 2024 | Anos que o modelo não vê |
| Faixa de incerteza | Percentis 10 e 90 do fator entre os 4 anos de treino | Com poucos anos, vira faixa de demonstração |
| Pistas do modelo | frp, bright_ti4, confidence, daynight, mês, bioma, `modis_scan_mediano` | As mesmas do modelo A |

Plano reserva, se só os arquivos de 2024 estiverem disponíveis: treinar com os meses de janeiro a junho de 2024 e testar de julho a dezembro. Nesse caso a faixa mostra só a variação entre meses, e isso precisa ser dito na tela de Método.

## 4. O que muda nas tarefas da parte B

| Tarefa | Ajuste |
| --- | --- |
| B1 | Protótipo calcula o fator por condição (mês, dia/noite, faixa de FRP), e não um só |
| B2 | Regra de escolha do satélite por mês continua. Acrescenta a conversão por condição e a faixa |
| B3 | Grava os fatores com colunas de condição e de faixa (mínimo e máximo) |
| B6 | Além da comparação com o INPE, reportar o erro nos anos de teste e quantas vezes o valor real caiu dentro da faixa |

## 5. Limites a declarar no método

- O modelo foi treinado com poucos anos e uma região. Mostra o método e não vale para outros biomas.
- A faixa de incerteza com poucos anos é aproximada.
- A geometria do MODIS onde ele não detectou é aproximada pela mediana do `scan`.
- A deriva de órbita do Aqua pode afetar 2023 e 2024.
- O uso de IA neste trabalho será declarado no campo "Use of Super Intelligence".

## 6. Pendências

1. Anos de treino (2019 a 2022) e de teste (2023 e 2024) confirmados. Se os dados desses anos não chegarem do FIRMS, vale o plano reserva.
2. Confirmar as faixas de FRP.
3. Autorizar rodar o Python (ainda não foi autorizado).
