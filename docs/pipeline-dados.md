# Pipeline de dados — o que já foi feito (frente A)

Nov 14, 2026 · branch `a-importador`

## Resumo

O histórico do FIRMS já está baixado e não depende do pedido do Archive Download. Usamos os **resumos anuais por país** (Brasil, versão SP) até 2025 e a **API** para 2026. Um pipeline em Python cadastra as regiões de calibração (os 6 biomas do IBGE) no banco, mantém todos os focos da cobertura (Brasil inteiro), aplica os filtros de qualidade do time de dados e gera uma análise exploratória por satélite.

O banco já tem schema (A4) e as regiões cadastradas. Ainda **não** existe o importador de `focos` com upsert (A5). Esta etapa serviu para conhecer os dados e decidir o pré-processamento antes de escrever o importador.

## Arquitetura atual

```
regioes.json ──▶ python pipeline.py cadastrar ──▶ `regioes` + `celula_regiao` (6 biomas)
                                                        │ (bbox e cobertura vêm daqui)
FIRMS (arquivos anuais por país + API)                  ▼
            │  python pipeline.py download
            ▼
data/raw/country/   CSV do país da cobertura, 1 por sensor e ano (SP, com `type`)
data/raw/api/       CSV de 5 em 5 dias, bbox da cobertura (2026 SP + NRT, NOAA-21)
data/raw/ibge/      polígonos
            │
            ▼  python pipeline.py stage    (sem filtro de qualidade, sem coluna de região)
data/staged/{modis,viirs}/   parquet por arquivo: só pontos dentro da cobertura (Brasil),
                             colunas normalizadas
            │
            ├──▶ python eda.py            → reports/eda.html + CSVs de contagem
            │
            ├──▶ python pipeline.py importar → tabela `focos` (tudo, upsert) + `cobertura`
            │
            ▼  python pipeline.py clean    (filtros do time de dados)
data/processed/{modis,viirs}_{main,lowconf}/satellite=…/daynight=…/year=…/
            + data/processed/clean_report.json (quantas linhas cada filtro tirou)
```

Tudo roda **um arquivo de cada vez**, porque o histórico (~30 milhões de focos no recorte) não cabe na memória de uma vez.

| Arquivo | O que faz |
| --- | --- |
| `data-pipeline/pipeline.py` | `cadastrar`, `download`, `stage`, `clean` |
| `data-pipeline/migrations/` | Schema do banco ([banco.md](banco.md)) |
| `data-pipeline/regioes.json` | Entrada do `cadastrar`: os 6 biomas (nome, fonte do polígono, URL, campo e valor). Só o `cadastrar` lê este arquivo |
| `data-pipeline/eda.py` | Análise exploratória por satélite, antes dos filtros |
| `data-pipeline/test_pipeline.py` | Self-check dos filtros com casos sintéticos |
| `data-pipeline/requirements.txt` | Dependências |

## De onde vêm os dados

| Fonte | Período | Como | Observação |
| --- | --- | --- | --- |
| `data/country/modis/{ano}/modis_{ano}_Brazil.csv` | 2000–2025 | download direto, sem chave | Terra + Aqua juntos; versão `6.03` (C6.1 SP) |
| `data/country/viirs-snpp/...` | 2012–2025 | idem | versão `2` (SP) |
| `data/country/viirs-jpss1/...` (NOAA-20) | 2018–2025 | idem | |
| NOAA-21 | — | **não existe** arquivo por país | só pela API |
| API `/api/area/csv/{KEY}/{FONTE}/{bbox}/{dias}/{data}` | 2026 e NOAA-21 desde 03/2023 | MAP_KEY, no máximo 5 dias por chamada | SP até ~jul/ago 2026, NRT depois |

Disponibilidade consultada em 14/11/2026 (`/api/data_availability`):

| Fonte | SP até | NRT até |
| --- | --- | --- |
| MODIS | 2026-08-31 | 2026-11-14 |
| VIIRS S-NPP | 2026-07-31 | 2026-11-02 (encerrado) |
| VIIRS NOAA-20 | 2026-07-31 | 2026-11-14 |
| VIIRS NOAA-21 | 2026-07-31 (SP desde 2023-03-01) | 2026-11-14 |

Diferenças de formato que o `normalize` corrige:

- A API devolve `acq_time` sem zero à esquerda (`14` em vez de `0014`). Sempre UTC.
- A API escreve a versão do MODIS como `61.03`. O arquivo por país usa `6.03`.
- O Archive Download NRT do VIIRS usa `brightness`/`bright_t31`. O SP usa `bright_ti4`/`bright_ti5`.
- **NRT não tem a coluna `type`.** Linhas NRT ficam com `type` vazio e `provisional = True`.

**Variáveis:** `FIRMS_MAP_KEY` e `DATABASE_URL`, como variáveis de ambiente ou no arquivo `data-pipeline/.env` (fora do git).

## Importador (`importar`)

Lê o `stage` (ou um CSV/ZIP do FIRMS passado como argumento) e grava em `focos` **tudo o que está na cobertura**, sem filtro de qualidade. Os filtros entram depois, na agregação.

| Etapa | Regra |
| --- | --- |
| Satélite | `Terra`, `Aqua`, `N` → `SNPP`, `N20`, `N21`. Valor desconhecido faz o arquivo falhar |
| Confiança | VIIRS `l`/`n`/`h` → baixa/nominal/alta. MODIS `< 30` baixa, `30–79` nominal, `≥ 80` alta |
| Data e hora | `acq_date` + `acq_time` (HHMM, UTC) → `datahora_utc` |
| Qualidade | `NRT` se a versão tem "NRT", senão `SP` |
| H3 | célula na resolução da tabela `config` (o banco recusa outra) |
| Chave única | (`satelite`, `lat`, `lon`, `datahora_utc`): `INSERT ... ON CONFLICT DO UPDATE`. Repetidos no mesmo arquivo viram uma linha |
| Transação | um arquivo por transação: entra inteiro ou não entra |
| `cobertura` | período do arquivo por satélite, gravado para todas as regiões (a cobertura é o país, não o bioma), sempre ampliando. Usar a data do último foco de cada bioma confundiria "zero focos" com "sem dados" |

Reimportar o mesmo arquivo não duplica: tudo vira "atualizado".

Teste com os ZIPs de 2024 do repo (Brasil, SP), em ~3 min:

| Satélite | Plano de extração | Importado | Diferença |
| --- | --- | --- | --- |
| Aqua | 319.074 | 318.716 | −0,11% |
| Terra | 208.820 | 208.585 | −0,11% |
| S-NPP | 1.935.740 | 1.932.612 | −0,16% |
| NOAA-20 | 1.988.404 | 1.985.271 | −0,16% |
| NOAA-21 | 1.948.842 | 1.945.784 | −0,16% |

A diferença são focos fora dos 6 biomas (mar e ilhas). A reimportação do MODIS deu 0 novos e 527.301 atualizados. Os 6,4 milhões de focos de 2024 ocupam **1,7 GB** com os índices, então o histórico inteiro do Brasil deve passar de 6 GB.

## Filtros de qualidade (`clean`)

Implementados conforme as especificações de filtro do time de dados.

| Regra | MODIS | VIIRS |
| --- | --- | --- |
| `type = 0` (só vegetação) | remove o resto | remove o resto |
| NRT sem `type` | mantém, `provisional = True` | idem |
| `frp` vazio, zero ou negativo | remove | remove |
| Duplicata exata (`latitude`, `longitude`, `acq_date`, `acq_time`, `satellite`) | remove | remove |
| Confiança baixa | `< 30` → arquivo `lowconf` | `l` de dia → arquivo `lowconf` |
| Confiança baixa à noite | — | `l` + `N` removido (Anomalia do Atlântico Sul) |
| Alta confiança | — | coluna `high_conf` (pixel saturado, FRP menos preciso) |
| Pontos vizinhos | **não** junta | **não** junta (fogo grande vira vários pixels) |
| `scan`, `track` | sem filtro | sem filtro |
| Separação dia/noite e satélite | partição `daynight=`/`satellite=` | idem |

## O que os dados mostraram

### Funil de 2020 (Amazônia + Pantanal)

| Etapa | MODIS | VIIRS S-NPP |
| --- | --- | --- |
| Dentro do bbox | 359.792 | 1.470.841 |
| Dentro das regiões | 221.539 | 921.361 |
| `type ≠ 0` removidos | 1.623 | 3.916 |
| `frp ≤ 0` removidos | 33 | 287 |
| `l` à noite removidos | — | 0 |
| **Arquivo principal** | **205.568** | **853.173** |
| Arquivo de baixa confiança | 14.315 | 63.983 |

### Histórico completo após o `clean`

| | MODIS (Terra + Aqua) | VIIRS (S-NPP + NOAA-20 + NOAA-21) |
| --- | --- | --- |
| Dentro das regiões | 5.274.745 | 18.039.745 |
| `type ≠ 0` removidos | 79.984 | 73.666 |
| `frp ≤ 0` removidos | 425 | 6.129 |
| Duplicatas exatas | 0 | 7 |
| `l` à noite | — | 0 |
| **Principal** | **4.890.798** | **16.811.011** |
| Baixa confiança | 303.538 | 1.148.932 |

### Por satélite (antes dos filtros, Amazônia + Pantanal)

| Satélite | Período | Focos | % noite | % NRT sem `type` | FRP mediana | Pixel (`scan`) mediano |
| --- | --- | --- | --- | --- | --- | --- |
| MODIS Terra | 2000-11 → 2026-11 | 1,94 mi | 46% | 1,5% | 17 MW | 1,30 km |
| MODIS Aqua | 2002-07 → 2026-11 | 3,33 mi | 11% | 1,3% | 26 MW | 1,30 km |
| VIIRS S-NPP | 2012-01 → 2026-11-02 | 9,67 mi | 35% | 3,0% | 5,5 MW | 0,44 km |
| VIIRS NOAA-20 | 2018-04 → 2026-11 | 5,90 mi | 37% | 5,6% | 5,5 MW | 0,44 km |
| VIIRS NOAA-21 | 2023-03 → 2026-11 | 2,47 mi | 41% | 13% | 6,0 MW | 0,44 km |

### Razões anuais entre satélites (Amazônia)

| Ano | S-NPP / Aqua | NOAA-20 / S-NPP | NOAA-21 / NOAA-20 |
| --- | --- | --- | --- |
| 2012 | 6,0 | | |
| 2013 | 5,4 | | |
| 2014 | 5,8 | | |
| 2015 | 6,7 | | |
| 2016 | 5,9 | | |
| 2017 | 6,2 | | |
| 2018 | 5,8 | 0,91 (desde abril) | |
| 2019 | 6,2 | 0,98 | |
| 2020 | 7,0 | 0,99 | |
| 2021 | 5,9 | 0,99 | |
| 2022 | 5,9 | 1,04 | |
| 2023 | 6,1 | 1,00 | 0,99 (desde março) |
| 2024 | 6,2 | 1,03 | 0,99 |
| 2025 | **4,8** | 0,99 | 0,97 |
| 2026 (parcial) | 5,4 | 1,12 (S-NPP parou em 02/11) | 0,98 |

### Aqua × Terra como referência (Amazônia, 2012–2023)

| | contra o Aqua | contra o Terra |
| --- | --- | --- |
| Razão anual S-NPP/MODIS | 5,4 a 7,0 | 9,9 a 13,7 |
| Variação da razão mensal (desvio/média) | **0,20** | **0,44** |
| Correlação mensal com o S-NPP | 0,99 | 0,987 |

A série mensal do Terra tem correlação de 0,977 com a do Aqua (2003–2025).

### Tamanho da grade H3 (Aqua, 2002–2025)

| Resolução | Hexágono | Células com fogo | Linhas célula × mês |
| --- | --- | --- | --- |
| 4 | ~1.770 km² | 2.243 | 190 mil |
| 5 | ~253 km² | 11.305 | 508 mil |
| 6 | ~36 km² | 57.517 | 1,05 mi |
| 7 | ~5 km² | 294.237 | 1,85 mi |

Achados:

1. **`l` à noite = 0** em todos os satélites, inclusive no NRT recortado nas regiões. Esse filtro não muda nada aqui. Fica no código para regiões onde ele agir.
2. **Os filtros removem menos de 1%** dos focos. Duplicatas exatas e `frp ≤ 0` são praticamente zero.
3. **Terra e Aqua são bem diferentes.** Os horários de passagem não são os mesmos (Terra ~10:30/22:30 e Aqua ~13:30/01:30 no horário local), e por isso o Terra tem 46% dos focos à noite e o Aqua só 11%.
4. **A FRP mediana do VIIRS é ~5× menor que a do MODIS.** O VIIRS conta muitos fogos fracos que o MODIS não vê.
5. **A razão S-NPP/Aqua muda mês a mês.** Na Amazônia em 2020 foi de 3,7× (abril) a 9,5× (agosto). Tabela completa em `reports/razao_snpp_aqua.csv`. É o dado de entrada da harmonização (frente B).
6. **Os três VIIRS são equivalentes:** NOAA-20/S-NPP e NOAA-21/NOAA-20 ficam entre 0,97 e 1,04 nos anos completos. Isso confirma a regra "um VIIRS por período".
7. **Calibrar contra o Aqua é duas vezes mais estável que contra o Terra** (variação mensal de 0,20 contra 0,44), e o Terra repete a série do Aqua (correlação de 0,977).
8. **S-NPP/Aqua caiu para 4,8 em 2025**, contra ~6 nos anos anteriores. Pode ser efeito da deriva da órbita do Aqua (saiu do A-Train em 2022) ou só um ano de fogo diferente. Precisa ser investigado antes de congelar o fator.
9. No MODIS, **8.331 pares (4%)** de focos na mesma passagem ficam a menos de ~1 km um do outro. Pode ser o efeito "bow-tie" na borda da faixa ou fogos vizinhos de verdade. Não foram removidos.

## Como rodar

Comandos em bash, a partir de `data-pipeline/`:

```bash
pip install -r requirements.txt
python test_pipeline.py          # self-check dos filtros
python pipeline.py cadastrar     # precisa do banco com a migration aplicada
python pipeline.py download      # ~3,5 GB; retoma de onde parou
python pipeline.py stage
python pipeline.py sem_dados     # dias sem dado de satélite (FIRMS) -> dias_sem_dados
python pipeline.py importar      # data/staged/ -> focos + cobertura (ou: importar arquivo.csv|.zip ...)
python eda.py                    # reports/eda.html
python pipeline.py clean
```

Para adicionar uma região de calibração: acrescente uma entrada em `regioes.json` e rode `cadastrar`. Para outro país: troque `config.cobertura_pais` e rode `download` e `stage`. O código não muda.

## Diferenças em relação aos outros documentos

| Ponto | Documento diz | Este pipeline faz | Situação |
| --- | --- | --- | --- |
| Fonte do histórico | Archive Download (pedido) | Resumos anuais por país | Mesmo dado SP, sem fila de aprovação (A1) |
| NOAA-21 | Só reserva no NRT | Baixa também o SP desde 03/2023 | Extra, não atrapalha. É só não usar |
| Terra | Fora do cálculo | Baixado e mantido separado (`satellite=Terra`) | Confirmado. Escala da série: VIIRS, com Aqua só para 2003–2011 e calibração (PR #2) |
| Banco e H3 | Tabelas `focos`, `regioes`, `cobertura` com H3 | Schema pronto (A4), `regioes` com os 6 biomas (A6). `focos` ainda em parquet | A5 e A7 pendentes |
| Regiões | Amazônia (e Pantanal) | Cobertura = Brasil inteiro; regiões de calibração = 6 biomas | Decidido no PR #2 |

## Pendências e decisões em aberto

- [x] Terra fora do cálculo (decisão do time de dados, com base na tabela "Aqua × Terra"). O Terra continua baixado e separado
- [x] Escala da série: VIIRS. Aqua só para 2003–2011 e para a calibração (PR #2)
- [x] Só confiança nominal e alta entra em `agregados`. O arquivo `lowconf` do `clean` fica guardado, mas não entra no calendário nem no fator (PR #2)
- [x] Banco de dados: PostgreSQL
- [ ] Resolução H3 (ponto 3), combinada com a frente C. Sugestão: res 6
- [ ] Investigar a queda de S-NPP/Aqua em 2025
- [ ] Baixar a série mensal do INPE (A2)
- [x] Rodar `stage`, `eda` e `clean` no histórico completo
- [ ] Importador para o banco (A4–A7), reaproveitando `normalize` e os filtros daqui
