# Importação de novas regiões — modelo de dados e processo

Nov 14, 2026 · @Mateus Nogueira

## Resumo

A primeira versão cobre a Amazônia, mas nada no sistema depende dela. O foco não guarda a região. As regiões são polígonos numa tabela própria, e os fatores de harmonização são calculados por região. Adicionar o Pantanal, a Califórnia ou qualquer outro lugar é carregar um CSV do FIRMS e cadastrar um polígono. Front e API não mudam.

## Importador único

Um só importador lê qualquer CSV do FIRMS: pedido de arquivo por país ou região, resumo anual por país ou resposta da API. Todos têm praticamente as mesmas colunas. O importador normaliza cada linha assim:

| Campo normalizado | Origem no CSV | Regra |
| --- | --- | --- |
| `sensor` | `instrument` | MODIS ou VIIRS |
| `satelite` | `satellite` | Terra, Aqua, SNPP, N20, N21 |
| `lat`, `lon` | `latitude`, `longitude` | — |
| `datahora_utc` | `acq_date` + `acq_time` | `acq_time` vem como HHMM em UTC |
| `confianca` | `confidence` | VIIRS: `l`/`n`/`h` → baixa/nominal/alta. MODIS: < 30 baixa, 30–79 nominal, ≥ 80 alta |
| `frp` | `frp` | Potência radiativa (MW) |
| `periodo` | `daynight` | D ou N |
| `tipo` | `type` | Pode ficar vazio: o NRT não traz essa coluna |
| `qualidade` | nome do arquivo ou fonte da API | SP (arquivo) ou NRT |
| `arquivo_origem` | nome do arquivo | Rastreabilidade |
| `h3` | calculado na carga | Célula H3 de lat/lon |

**Chave única:** (`satelite`, `lat`, `lon`, `datahora_utc`). A gravação é um upsert, então reimportar ou sobrepor arquivos nunca duplica focos. Na recarga SP, as coordenadas podem mudar um pouco em relação ao NRT, então o upsert não basta. A recarga apaga os focos NRT daquele satélite e período e insere os SP no lugar, numa única transação.

## Tabelas

Cinco tabelas separam o dado bruto, as regiões, a cobertura, a calibração e o resultado pronto para a API.

| Tabela | Uma linha por | Colunas principais | Quem grava |
| --- | --- | --- | --- |
| `focos` | Foco detectado | Campos normalizados do importador + `h3` | Importador e jobs de atualização |
| `regioes` | Região | `id`, `nome`, `geom` (polígono), `celulas_h3`, `fonte_poligono` | Cadastro manual |
| `cobertura` | Região × satélite | `regiao_id`, `satelite`, `data_inicio`, `data_fim`, `atualizado_em` | Importador |
| `fatores_harmonizacao` | Região × par de satélites | `regiao_id`, `satelite_origem`, `satelite_destino`, `fator`, `periodo_calibracao`, `n_meses` | Job de calibração |
| `agregados` (contrato 1) | Célula H3 × ano × mês | `h3`, `ano`, `mes`, `focos_harmonizados`, `focos_brutos`, `frp_soma`, `sem_dados` | Job de agregação |

A API usa a `cobertura` para responder "sem dados para esta área" quando a área desenhada cai fora das regiões carregadas, em vez de devolver um calendário vazio. A coluna `sem_dados` marca os meses em que o FIRMS informa falha de satélite (`missing_data`), para não confundir com zero focos.

## Harmonização por região

O fator de harmonização é calculado para cada região, porque a razão VIIRS/MODIS muda de bioma para bioma. Fogo de floresta, de cerrado e agrícola têm tamanhos e temperaturas diferentes, e o VIIRS ganha mais detecções onde o fogo é pequeno. Na Amazônia, em 2024, o S-NPP detectou cerca de 6,3× mais focos que o Aqua. Esse número não vale para outra região.

Cadeia de calibração, aplicada a cada região:

1. **Referência:** MODIS Aqua, de 2003 em diante.
2. **S-NPP → Aqua:** fator calculado na sobreposição de 20/01/2012 a 02/11/2026.
3. **NOAA-20 → S-NPP:** fator calculado na sobreposição de 01/04/2018 a 02/11/2026. Aplicado depois do fator anterior, leva o NOAA-20 à escala Aqua.
4. **NOAA-21:** só se o NOAA-20 falhar, calibrado contra o NOAA-20 a partir de 01/03/2023.

Regras:

- O fator é calculado só com focos de confiança nominal ou alta e `tipo = 0`.
- O fator fica congelado depois da carga histórica. Os jobs de atualização só aplicam o fator.
- Região sem sobreposição suficiente (menos de 24 meses com focos nos dois sensores) usa o fator da região vizinha mais parecida, e isso fica registrado em `fatores_harmonizacao`.

## Como adicionar uma região nova

Adicionar uma região leva quatro passos e não muda nada no front nem na API.

1. **Baixar os focos.** Pedido no [Archive Download do FIRMS](https://firms.modaps.eosdis.nasa.gov/download/create.php), por país ou região customizada, com MODIS, VIIRS S-NPP e VIIRS NOAA-20, de 2000-11-01 até hoje, em CSV. Se a região está dentro de um país já carregado (por exemplo, o Pantanal dentro do Brasil), este passo é pulado.
2. **Importar.** `importar <arquivo.csv>` grava em `focos` e atualiza `cobertura`.
3. **Cadastrar o polígono.** Inserir a região em `regioes` com o polígono oficial (IBGE para biomas brasileiros, fonte oficial do país nos outros casos). O cadastro calcula `celulas_h3`.
4. **Recalcular.** `recalcular <regiao>` calcula os fatores de harmonização da região, gera os `agregados` das células dela e invalida o cache dessas células.

Depois disso, os jobs de atualização diária e de recarga mensal passam a incluir a região automaticamente, usando o bounding box do polígono.

**Próximas regiões previstas:** Pantanal (sem download novo, já está no Brasil) e Califórnia (precisa de um pedido novo no FIRMS) para os casos de 2020 na demo.
