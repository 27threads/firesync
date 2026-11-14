# Regras entre as variáveis (rascunho para a equipe revisar)

Origem: CLAUDE.md do projeto. Tudo marcado como **ESCOLHA DA EQUIPE** é decisão nossa, não fato. Nenhum dado real foi usado.

## 1. Colunas obrigatórias por base

| Coluna | MODIS (Aqua/Terra) | VIIRS | Observação |
| --- | --- | --- | --- |
| latitude, longitude | sim | sim | graus decimais |
| brightness, bright_t31 | sim | não | temperatura do pixel (MODIS) |
| bright_ti4, bright_ti5 | não | sim | temperatura do pixel (VIIRS) |
| scan, track | sim | sim | tamanho do pixel no chão, em km. Não filtrar, são variáveis do modelo |
| acq_date | sim | sim | data (AAAA-MM-DD) |
| acq_time | sim | sim | hora e minuto em UTC (4 dígitos, ex.: 0530) |
| satellite | sim | sim | Aqua, Terra, N (Suomi NPP), etc. |
| confidence | número 0 a 100 | n, h ou l | escalas diferentes, nunca misturar |
| version | sim | sim | 6.1 padrão ou 6.1NRT (provisório) |
| frp | sim | sim | potência radiativa do fogo, em MW |
| daynight | D ou N | D ou N | |
| type | sim | sim | |
| bioma | sim | sim | Amazônia ou Pantanal (polígono do IBGE) |

## 2. Regras de remoção (registrar quantas linhas saíram em cada uma)

1. `type != 0` sai (nos dois sensores).
2. `frp` vazio, zero ou negativo sai (nos dois).
3. MODIS: `confidence < 30` vai para arquivo à parte.
4. VIIRS: `confidence = l` com `daynight = N` sai (Anomalia Magnética do Atlântico Sul). `l` de dia vai para arquivo à parte.
5. Fora dos biomas Amazônia e Pantanal sai.
6. `scan` e `track` não são filtrados.

## 3. Regras de duplicata

- MODIS: mesmo satélite, mesma data, horário igual ou com até 1 minuto de diferença, distância menor que metade do `scan`. Fica o de maior confiança.
- VIIRS: só linhas idênticas. Pontos vizinhos não se juntam.

## 4. Regras de ligação entre MODIS e VIIRS (passo 2)

- Mesma `acq_date` e mesmo `daynight`.
- Diferença de horário de até 10 minutos (o FIRMS só traz hora e minuto). **ESCOLHA DA EQUIPE**
- "MODIS viu": a distância entre os dois pontos é menor ou igual a metade do maior entre `scan` e `track` do MODIS, mais metade do pixel do VIIRS (375 m).
- "MODIS estava olhando": existe foco do Aqua a até 50 km, na mesma passagem. Sem isso, o foco do VIIRS fica fora do rótulo. **ESCOLHA DA EQUIPE.** Limite a declarar: exclui áreas sem nenhum foco do MODIS por perto.
- Treino só com Aqua e Suomi NPP. Terra e NOAA-20/21 ficam em arquivos separados.

## 5. Regras de uso das variáveis no modelo A (passo 3)

- Rótulo: `modis_viu` (1 ou 0), só onde `modis_coberto = 1`.
- Pistas: frp, bright_ti4, confidence, daynight, mês, bioma, `modis_scan_mediano`.
- Treino 2015 a 2021, teste 2022 a 2024. **ESCOLHA DA EQUIPE**
- Faixa de incerteza: percentis 10 e 90 do fator entre os anos de treino. **ESCOLHA DA EQUIPE**
- Nunca comparar a contagem de pontos do VIIRS com a do MODIS. Sempre por célula da grade ou por evento.

## 6. Perguntas em aberto (preciso da decisão de vocês)

1. A data de corte do Suomi NPP é 02/11/2026. Linhas depois disso entram?
2. Tamanho da célula da grade (0,25° ou 1 km)?
3. Quando `version` for 6.1NRT, o valor entra na série com marca de provisório?
