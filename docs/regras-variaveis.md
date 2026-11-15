# Regras entre as variáveis (rascunho para a equipe revisar)

Origem: documento de contexto do Weberson, revisado com os dados brutos de 2024 e com a revisão do PR 1. Itens marcados como **ESCOLHA DA EQUIPE** são decisões nossas, não fatos. As decisões de método estão em [decisoes-harmonizacao.md](decisoes-harmonizacao.md). A limpeza real é feita pelo `pipeline.py clean` (frente A).

## 1. Colunas por base

| Coluna | MODIS (Aqua) | VIIRS | Observação |
| --- | --- | --- | --- |
| latitude, longitude | sim | sim | graus decimais |
| brightness, bright_t31 | sim | sim | o nome no VIIRS depende da fonte: no Archive Download (inclusive os arquivos SP de 2024) vem `brightness`/`bright_t31`; segundo o `pipeline-dados.md`, outras fontes trazem `bright_ti4`/`bright_ti5`. O importador normaliza |
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
5. **O arquivo de baixa confiança fica guardado, mas não entra no fator nem no calendário** (nem em `agregados`). O fator e o calendário precisam usar o mesmo filtro, senão a série fica distorcida.
6. O recorte por bioma vale só para a calibração. A tabela `focos` guarda o Brasil inteiro.
7. `scan` e `track` não são filtrados.

## 3. Regras de duplicata

**DECIDIDO (Weberson, 14/11/2026):** nos dois sensores, remover **só as linhas idênticas** (`latitude`, `longitude`, `acq_date`, `acq_time`, `satellite`), como o `pipeline.py clean` já faz. Pontos vizinhos não se juntam.

Motivos:

- O calendário compara meses e anos. O que importa é contar sempre do mesmo jeito, e os pixels repetidos do MODIS (cerca de 4%, efeito bow-tie) entram no cálculo do fator e na aplicação, e se cancelam.
- Uma frente de fogo ocupa vários pixels lado a lado. Juntar vizinhos pode apagar fogo de verdade.
- A distância para juntar teria de ser diferente em cada sensor (pixel do MODIS de 1 km até quase 5 km, do VIIRS de 375 m), e qualquer escolha mudaria as contagens de forma arbitrária.
- Cruzar milhões de focos por distância não cabe no prazo.

Consequência na interface: o número do calendário se chama **"detecções de fogo"** (fire detections, convenção do FIRMS), com a nota "uma frente de fogo gera várias detecções".

Ideia futura, fora do prazo: agrupar detecções em **eventos** para a visão de áreas críticas, só com o VIIRS e no período recente (localização pelo centro ponderado pelo FRP, FRP somado, primeira e última detecção).

## 4. Regras de ligação entre MODIS e VIIRS (só para o classificador complementar)

- Mesma `acq_date` e mesmo `daynight`, com diferença de horário de até 10 minutos. **ESCOLHA DA EQUIPE.** Essa janela vale quando o Aqua estava na órbita original (até 2021). **Em 2024 ela precisa ser de 90 minutos**: o Aqua passa 44 minutos (dia) e 63 minutos (noite) depois do S-NPP no mesmo lugar, e só 6% a 9% dos pares ficam dentro de 10 minutos. A janela é o parâmetro `--janela` do `modelo_a.py`.
- "MODIS viu": a distância entre os dois pontos é menor ou igual a metade do maior entre `scan` e `track` do MODIS, mais metade do pixel do VIIRS (375 m).
- "MODIS estava olhando": existe foco do Aqua a até 50 km, na mesma passagem. **ESCOLHA DA EQUIPE.** Esta regra gera viés: descarta justamente as áreas onde o VIIRS viu fogo pequeno e o MODIS nada, e por isso o fator da série **não** usa essa regra. Vale só para o classificador complementar, com o viés declarado.

## 5. Regras de uso das variáveis

**Fator da série (decidido):**

- Condições: bioma × mês × dia/noite. O FRP não entra.
- Calculado em contagens por célula H3, um cenário por ano. Base 2012 a 2024, com os anos escolhidos pela validação deixando um ano de fora: se o erro de 2022 a 2024 passar de 1,5× o de 2012 a 2021, ficam só 2012 a 2021 (10 cenários); senão, os 13 anos. 2025 em diante fica fora.
- NOAA-20 tratado como igual ao S-NPP (fator 1).
- Só confiança nominal e alta (arquivo principal). Os 6 biomas do IBGE são calibrados.
- Faixa de incerteza: P5 e P95 entre os cenários (cerca de 8 em 10; ver o resultado da calibração em decisoes-harmonizacao.md).
- Fator = razão das somas por bioma, mês e período. Sem os dias em `dias_sem_dados` de qualquer um dos dois satélites e sem janeiro de 2012. Fusão quando faltar foco: meses vizinhos no mesmo período, depois o ano inteiro no mesmo período, e só em último caso o ano inteiro com dia e noite juntos. Detalhes em [decisoes-harmonizacao.md](decisoes-harmonizacao.md).
- Nunca comparar a contagem bruta de pontos do VIIRS com a do MODIS. Sempre pelo fator ou por célula da grade.

**Classificador complementar (decidido):**

- Rótulo: `modis_viu` (1 ou 0), só onde o Aqua estava observando a área.
- Pistas: frp, temperatura, confiança, dia/noite, mês, bioma, `modis_scan_mediano`.
- Treino 2019 a 2021 e teste 2022 a 2024, em volume pequeno. **ESCOLHA DA EQUIPE**
- Com só os arquivos de 2024: corte no espaço (metade das células H3 para treino, metade para teste, todos os meses dos dois lados).

## 6. Perguntas já respondidas

1. Suomi NPP depois de 02/11/2026: não entra. A série segue com NOAA-20.
2. Tamanho da célula: grade H3 resolução 6 (`banco.md`, PR #2).
3. Dados NRT (provisórios): marcados com `qualidade = NRT` (PR #2), fora do cálculo do fator.

## 7. Perguntas em aberto

1. Mínimo de focos por condição: a calibração gravada usou 30, e falta a equipe confirmar ([decisoes-harmonizacao.md](decisoes-harmonizacao.md), seção 7).
2. Faixas de FRP para os indicadores de áreas críticas. As do classificador já estão decididas no [RFC 0002](rfcs/0002-modelo-a.md): 2, 5, 10 e 25 MW, rodadas na base limpa de 2024.
