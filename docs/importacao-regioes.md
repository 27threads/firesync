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
| `fatores_harmonizacao` | Região (bioma) × par de satélites × mês × dia/noite × ano de calibração | `regiao_id`, `satelite_origem`, `satelite_destino`, `mes`, `periodo`, `ano_calibracao`, `fator` (proposta: + `n_focos_origem`, `fusao_com`) | Job de calibração |
| `agregados` (contrato 1) | Célula H3 × ano × mês × satélite × dia/noite | `h3`, `ano`, `mes`, `regiao_id`, `satelite`, `periodo`, `focos_brutos`, `frp_soma` | Job de agregação |

O formato segue o `docs/banco.md` e a migration `001_inicial.sql` da frente A (PR #2). Pontos principais:

- `agregados` guarda a contagem **bruta**, sem harmonizar. Mês sem focos não tem linha, e a API preenche com zero.
- Cada ano de calibração é um **cenário**. A API soma as contagens brutas da área, multiplica pelos fatores de cada cenário e só então calcula a mediana e o P10 e o P90, porque a soma dos P10 das células não é o P10 da soma. Mudar um fator não exige refazer `agregados`.
- **Origem de cada mês (regra da API):** mês com focos do VIIRS na área é `observado_viirs`, sem faixa. Mês só com Aqua é `estimado_modis`, com mediana e faixa. A coluna não é gravada no banco.
- **FRP:** a API só mostra `frp_soma` das linhas do VIIRS, porque o FRP do MODIS e o do VIIRS não são comparáveis.
- **Proposta para a frente A (migration 002):** acrescentar `n_focos_origem` e `fusao_com` em `fatores_harmonizacao`, para registrar o mínimo de focos por condição e a fusão com a condição vizinha.

Detalhes e decisões em [decisoes-harmonizacao.md](decisoes-harmonizacao.md).

A API usa a `cobertura` para responder "sem dados para esta área" quando a área desenhada cai fora das regiões carregadas, em vez de devolver um calendário vazio. A coluna `sem_dados` marca os meses em que o FIRMS informa falha de satélite (`missing_data`), para não confundir com zero focos.

## Harmonização por região

O fator de harmonização é calculado para cada região, porque a razão VIIRS/MODIS muda de bioma para bioma. Fogo de floresta, de cerrado e agrícola têm tamanhos e temperaturas diferentes, e o VIIRS ganha mais detecções onde o fogo é pequeno. Na Amazônia, em 2024, o S-NPP detectou cerca de 6,3× mais focos que o Aqua. Esse número não vale para outra região.

Cadeia de calibração, aplicada a cada região:

1. **Escala final: VIIRS (S-NPP como referência).** Decisão do Weberson em 14/11/2026. Os anos só-MODIS (2003 a 2011) são convertidos para a escala do VIIRS, e cada mês fica rotulado como observado ou estimado (`origem`).
2. **Aqua → S-NPP:** fator por **bioma × mês × dia/noite**, calculado em contagens por célula H3, com calibração em 2012 a 2021 (10 cenários) e teste em 2022 a 2024. Cada ano de calibração é um cenário. Só confiança nominal e alta entra. Os 6 biomas do IBGE são calibrados. O fator da série é a mediana dos cenários, e a faixa de incerteza é o P10 e o P90 entre eles, calculados na API depois de somar a área. Só o Aqua entra (Terra fora, calendário a partir de 2003). 2025 em diante fica fora, porque a razão S-NPP/Aqua cai para 4,8, provavelmente pela deriva de órbita do Aqua. Ver [decisoes-harmonizacao.md](decisoes-harmonizacao.md).
3. **NOAA-20 → S-NPP:** fator calculado na sobreposição de 01/04/2018 a 02/11/2026 (as razões ficam entre 0,97 e 1,04). Mantém a continuidade do VIIRS depois do fim do S-NPP.
4. **NOAA-21:** só se o NOAA-20 falhar, calibrado contra o NOAA-20 a partir de 01/03/2023.

Regras:

- O fator é calculado só com focos de confiança nominal ou alta e `tipo = 0`.
- O FRP não é condição do fator, porque nos anos só-MODIS os fogos que o MODIS não viu não têm FRP.
- Cada condição precisa de um mínimo de focos do Aqua. Abaixo disso, junta com a condição vizinha e registra em `fusao_com`. O valor do mínimo é definido com a base limpa.
- Suposição declarada no Método: a razão entre os sensores em 2003 a 2011 é parecida com a de 2012 a 2021. Não há como testar, porque não há VIIRS antes de 2012.
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
