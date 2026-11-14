# Pipeline de dados — o que já foi feito (frente A)

Nov 14, 2026 · branch `a-importador`

## Resumo

O histórico do FIRMS já está baixado e não depende do pedido do Archive Download. Usamos os **resumos anuais por país** (Brasil, versão SP) até 2025 e a **API** para 2026. Um pipeline de arquivos em Python recorta as regiões de `data-pipeline/regioes.json`, aplica os filtros de qualidade do time de dados e gera uma análise exploratória por satélite.

Ainda **não** existe banco, H3 nem importador com upsert (tarefas A4 e A5). Esta etapa serviu para conhecer os dados e decidir o pré-processamento antes de escrever o importador.

## Arquitetura atual

```
FIRMS (arquivos anuais por país + API)      IBGE (Biomas 1:250.000)
            │                                         │
            ▼  python pipeline.py download            ▼
data/raw/country/   CSV Brasil inteiro, 1 por sensor e ano (SP, com `type`)
data/raw/api/       CSV de 5 em 5 dias, bbox das regiões (2026 SP + NRT, NOAA-21)
data/raw/ibge/      polígonos
            │
            ▼  python pipeline.py stage    (sem filtro de qualidade)
data/staged/{modis,viirs}/   parquet por arquivo: só pontos dentro das regiões,
                             colunas normalizadas, coluna `regiao`
            │
            ├──▶ python eda.py            → reports/eda.html + CSVs de contagem
            │
            ▼  python pipeline.py clean    (filtros do time de dados)
data/processed/{modis,viirs}_{main,lowconf}/satellite=…/daynight=…/year=…/
            + data/processed/clean_report.json (quantas linhas cada filtro tirou)
```

Tudo roda **um arquivo de cada vez**, porque o histórico (~30 milhões de focos no recorte) não cabe na memória de uma vez.

| Arquivo | O que faz |
| --- | --- |
| `data-pipeline/pipeline.py` | `download`, `stage`, `clean` |
| `data-pipeline/regioes.json` | Regiões como dado: nome, fonte do polígono, URL, campo e valor do filtro |
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

**MAP_KEY:** variável de ambiente `FIRMS_MAP_KEY` ou arquivo `data-pipeline/.env` com `FIRMS_MAP_KEY=...` (fora do git).

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

### Por satélite (antes dos filtros)

Parcial, com S-NPP até 2023. Atualizar quando a análise completa rodar.

| Satélite | Focos | % noite | FRP mediana | Pixel (`scan`) mediano |
| --- | --- | --- | --- | --- |
| MODIS Terra (2000–2025) | 1,90 mi | 46% | 17 MW | 1,30 km |
| MODIS Aqua (2002–2025) | 3,27 mi | 11% | 26 MW | 1,30 km |
| VIIRS S-NPP (2012–2023) | 7,96 mi | 34% | 5,6 MW | 0,44 km |

Achados:

1. **`l` à noite = 0** em todo o S-NPP SP. O arquivo SP já vem sem esses pontos, então esse filtro só age no NRT.
2. **Os filtros removem menos de 1%** dos focos. Duplicatas exatas e `frp ≤ 0` são praticamente zero.
3. **Terra e Aqua são bem diferentes.** Os horários de passagem não são os mesmos (Terra ~10:30/22:30 e Aqua ~13:30/01:30 no horário local), e por isso o Terra tem 46% dos focos à noite e o Aqua só 11%.
4. **A FRP mediana do VIIRS é ~5× menor que a do MODIS.** O VIIRS conta muitos fogos fracos que o MODIS não vê.
5. **A razão S-NPP/Aqua muda mês a mês.** Na Amazônia em 2020 foi de 3,7× (abril) a 9,5× (agosto). Tabela completa em `reports/razao_snpp_aqua.csv`. É o dado de entrada da harmonização (frente B).
6. No MODIS, **8.331 pares (4%)** de focos na mesma passagem ficam a menos de ~1 km um do outro. Pode ser o efeito "bow-tie" na borda da faixa ou fogos vizinhos de verdade. Não foram removidos.

## Como rodar

Comandos em bash, a partir de `data-pipeline/`:

```bash
pip install -r requirements.txt
python test_pipeline.py          # self-check dos filtros
python pipeline.py download      # ~3,5 GB; retoma de onde parou
python pipeline.py stage
python eda.py                    # reports/eda.html
python pipeline.py clean
```

Para adicionar uma região: acrescente uma entrada em `regioes.json` e rode `stage` de novo. O código não muda.

## Diferenças em relação aos outros documentos

| Ponto | Documento diz | Este pipeline faz | Situação |
| --- | --- | --- | --- |
| Fonte do histórico | Archive Download (pedido) | Resumos anuais por país | Mesmo dado SP, sem fila de aprovação (A1) |
| NOAA-21 | Só reserva no NRT | Baixa também o SP desde 03/2023 | Extra, não atrapalha. É só não usar |
| Terra | Fora do cálculo | Baixado e mantido separado (`satellite=Terra`) | Decisão em aberto, abaixo |
| Banco e H3 | Tabelas `focos`, `regioes`, `cobertura` com H3 | Ainda em parquet | A4–A6 pendentes |

## Pendências e decisões em aberto

- [ ] Decidir se o Terra entra (fator próprio) ou fica fora (só Aqua, a partir de 2003)
- [ ] Banco de dados (arquitetura, ponto 2) e resolução H3 (ponto 3)
- [ ] Baixar a série mensal do INPE (A2)
- [ ] Rodar `stage`, `eda` e `clean` no histórico completo e atualizar os números acima
- [ ] Importador para o banco (A4–A7), reaproveitando `normalize` e os filtros daqui
