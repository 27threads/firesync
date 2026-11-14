# Regras entre as variáveis (rascunho para a equipe revisar)

Origem: documento de contexto do Weberson, revisado com os dados brutos de 2024 e com a revisão do PR 1. Itens marcados como **ESCOLHA DA EQUIPE** são decisões nossas, não fatos. As decisões de método estão em [decisoes-harmonizacao.md](decisoes-harmonizacao.md). A limpeza real é feita pelo `pipeline.py clean` (frente A).

## 1. Colunas por base

| Coluna | MODIS (Aqua) | VIIRS | Observação |
| --- | --- | --- | --- |
| latitude, longitude | sim | sim | graus decimais |
| brightness, bright_t31 | sim | sim (nomes do arquivo NRT) | no VIIRS SP aparecem como bright_ti4 e bright_ti5 |
| scan, track | sim | sim | tamanho do pixel no chão, em km. Não filtrar |
| acq_date, acq_time | sim | sim | acq_time em UTC, HHMM (a API manda sem zero à esquerda) |
| satellite | Aqua, Terra | SNPP, N20, N21 | só o Aqua entra no cálculo |
| confidence | número de 0 a 100 | n, h ou l | escalas diferentes, nunca misturar |
| version | 61.03 ou 6.03 conforme a fonte | 2 | arquivos SP em 2024: sem NRT |
| frp | sim | sim | potência do fogo, em MW. Não comparável entre sensores |
| daynight | D ou N | D ou N | |
| type | sim | sim | vazio no NRT |
| bioma / regiao | sim | sim | só no conjunto de treino e nos agregados (ver seção 2) |

## 2. Regras de remoção (registrar quantas linhas saíram em cada uma)

1. `type != 0` sai (nos dois sensores). No NRT o `type` vem vazio: mantém, marcado como provisório.
2. `frp` vazio, zero ou negativo sai (nos dois).
3. MODIS: `confidence < 30` vai para arquivo à parte.
4. VIIRS: `confidence = l` com `daynight = N` sai (Anomalia Magnética do Atlântico Sul). `l` de dia vai para arquivo à parte.
5. O recorte por bioma (Amazônia e Pantanal) vale só para o conjunto de treino e para os agregados. A tabela `focos` guarda o Brasil inteiro.
6. `scan` e `track` não são filtrados.

## 3. Regras de duplicata

- MODIS: mesmo satélite, mesma data, horário igual ou com até 1 minuto de diferença, distância menor que metade do `scan`. Fica o de maior confiança.
- VIIRS: só linhas idênticas. Pontos vizinhos não se juntam.

## 4. Regras de ligação entre MODIS e VIIRS (só para o classificador complementar)

- Mesma `acq_date` e mesmo `daynight`, com diferença de horário de até 10 minutos. **ESCOLHA DA EQUIPE**
- "MODIS viu": a distância entre os dois pontos é menor ou igual a metade do maior entre `scan` e `track` do MODIS, mais metade do pixel do VIIRS (375 m).
- "MODIS estava olhando": existe foco do Aqua a até 50 km, na mesma passagem. **ESCOLHA DA EQUIPE.** Esta regra gera viés: descarta justamente as áreas onde o VIIRS viu fogo pequeno e o MODIS nada, e por isso o fator da série **não** usa essa regra. Vale só para o classificador complementar, com o viés declarado.

## 5. Regras de uso das variáveis

**Fator da série (decidido):**

- Condições: bioma × mês × dia/noite. O FRP não entra.
- Calculado em contagens por célula H3, na sobreposição de 2012 a 2024, com um cenário por ano.
- Faixa de incerteza: P10 e P90 entre os cenários.
- Nunca comparar a contagem bruta de pontos do VIIRS com a do MODIS. Sempre por célula da grade ou por evento.

**Classificador complementar (decidido):**

- Rótulo: `modis_viu` (1 ou 0), só onde o Aqua estava observando a área.
- Pistas: frp, temperatura, confiança, dia/noite, mês, bioma, `modis_scan_mediano`.
- Treino 2019 a 2022 e teste 2023 e 2024, em volume pequeno. **ESCOLHA DA EQUIPE**
- Com só os arquivos de 2024: corte no espaço (metade das células H3 para treino, metade para teste, todos os meses dos dois lados).

## 6. Perguntas já respondidas

1. Suomi NPP depois de 02/11/2026: não entra. A série segue com NOAA-20.
2. Tamanho da célula: grade H3 (resolução definida com a frente C).
3. Dados NRT (provisórios): entram só no mês corrente, marcados como provisórios, fora do cálculo do fator.

## 7. Perguntas em aberto

1. Mínimo de focos por condição (definir com a base limpa).
2. Faixas de FRP para o classificador e para os indicadores de áreas críticas (sugestão inicial a partir dos dados brutos de 2024: 2, 5, 10 e 25 MW, a reconferir depois da limpeza).
