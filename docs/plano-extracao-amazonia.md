# Plano de extração de dados — Brasil (Amazônia)

Nov 14, 2026 · @Mateus Nogueira

## Resumo

Baixamos do FIRMS os focos do **Brasil inteiro**, de 01/11/2000 até hoje, com três sensores: MODIS, VIIRS S-NPP e VIIRS NOAA-20. O recorte da Amazônia é feito depois, no processamento, com o polígono do bioma do IBGE. Assim, o Pantanal e outras regiões ficam disponíveis sem baixar nada novo. Depois da carga, a API do FIRMS mantém os dados atualizados todos os dias.

## Dados a extrair

Três sensores do FIRMS cobrem a série de 2000 até hoje. As datas de início e fim abaixo são as informadas no formulário do FIRMS em 14/11/2026.

| Sensor | Satélite | Resolução | Disponível de | Disponível até | Período que usamos | Papel na série |
| --- | --- | --- | --- | --- | --- | --- |
| MODIS C6.1 | Terra | 1 km | 01/11/2000 | hoje | não entra no cálculo | Baixado junto com o Aqua, descartado na harmonização |
| MODIS C6.1 | Aqua | 1 km | 04/07/2002 | hoje | 01/01/2003 até 31/01/2012, e na calibração | Única fonte de 2003 a janeiro de 2012, convertida para a escala do VIIRS |
| VIIRS C2 | S-NPP | 375 m | 20/01/2012 | 02/11/2026 (encerrado) | 01/02/2012 a 31/10/2026 | Escala de referência da série. Base da calibração do Aqua |
| VIIRS C2 | NOAA-20 | 375 m | 01/04/2018 | hoje | 01/11/2026 até hoje | Continuidade após o fim do S-NPP, com fator 1 (igual ao S-NPP) |
| VIIRS C2 | NOAA-21 | 375 m | 01/03/2023 | hoje | só no job diário (NRT) | Reserva caso o NOAA-20 falhe. Não entra na carga histórica |

O calendário começa em **janeiro de 2003**, o primeiro ano completo do Aqua. Somar Terra e Aqua criaria um salto artificial em julho de 2002, quando o Aqua entra.

**Escala da série: VIIRS (S-NPP).** De fevereiro de 2012 em diante, o calendário mostra a contagem real do VIIRS. De 2003 a janeiro de 2012, mostra o Aqua convertido para a escala do VIIRS, com faixa de incerteza.

**Calibração:**

- Aqua → S-NPP: fator por bioma × mês × dia/noite, um cenário por ano. Os anos saem da validação deixando um ano de fora (2012–2024, ou 2012–2021 se a deriva da órbita do Aqua pesar). 2025 em diante fica fora.
- NOAA-20 → S-NPP: fator 1. As razões anuais ficaram entre 0,97 e 1,04 na sobreposição de 2018 a 2026.

Regras completas em [importacao-regioes.md](importacao-regioes.md) e [decisoes-harmonizacao.md](decisoes-harmonizacao.md).

Os três VIIRS veem praticamente os mesmos focos. Em cada período usamos **um VIIRS só**, nunca a soma.

## De onde veio o histórico

O histórico veio dos **resumos anuais por país** do FIRMS (Brasil, SP), que não passam por fila de aprovação, e da API para 2026 (tarefa A1, [pipeline-dados.md](pipeline-dados.md)). O pedido pelo [Archive Download](https://firms.modaps.eosdis.nasa.gov/download/create.php) não foi usado. Ele continua sendo o caminho para uma região fora do Brasil ([importacao-regioes.md](importacao-regioes.md), "Como adicionar uma região nova").

## Polígono da região e série de validação

Esses dois dados não vêm do FIRMS. São downloads separados, usados no processamento.

| Dado | Fonte | Onde | Uso |
| --- | --- | --- | --- |
| Polígono do bioma Amazônia | IBGE, "Biomas do Brasil" (escala 1:250.000) | Site do IBGE → Geociências → Biomas (shapefile) | Recortar os focos da Amazônia. Traz os seis biomas, incluindo o Pantanal |
| Focos mensais do bioma Amazônia | INPE, Programa Queimadas (BDQueimadas), satélite de referência | Portal do Programa Queimadas → estatísticas por bioma | Validar a forma da série harmonizada de 2003 até hoje |

Usamos o bioma, e não a Amazônia Legal, porque é o mesmo recorte das estatísticas do INPE. Isso permite comparar as duas séries. Os valores absolutos não vão bater, porque o INPE usa um único satélite. O que precisa bater é a forma da curva: os mesmos anos altos (2007, 2010, 2024) e os mesmos meses de pico.

## Atualização depois da carga

A carga histórica é feita uma vez. Depois disso, um job mantém a base em dia pela [API do FIRMS](https://firms.modaps.eosdis.nasa.gov/api), que exige uma MAP\_KEY gratuita e tem limite de 5000 transações a cada 10 minutos.

| Job | Frequência | Fontes | Janela | O que faz |
| --- | --- | --- | --- | --- |
| Atualização NRT (`data-pipeline/job_nrt.py`, feito) | A cada 3 h | `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT` | Últimas 48 h | Upsert dos focos novos, refaz em `agregados` os meses da janela, atualiza `dias_sem_dados` e grava `config.atualizado_em` (a chave do cache da API) |
| Recarga SP | Mensal | `VIIRS_NOAA20_SP` | Últimos \~6 meses | **Fora do escopo da submissão.** Substituiria os dados NRT pelos de qualidade científica, que chegam com cerca de 5 meses de defasagem |

O MODIS não entra no job NRT, porque o Aqua só é usado até janeiro de 2012. O NOAA-21 entra só como reserva. O fator de calibração fica congelado depois da carga histórica. Os jobs só aplicam o fator, nunca recalibram. Os dados NRT não trazem a coluna `type`: o foco NRT entra marcado como provisório, como manda o [regras-variaveis.md](regras-variaveis.md). O filtro por células H3 marcadas como `type = 2` no histórico SP não foi implementado.

## Dados de teste já baixados

Os arquivos de 2024 (Brasil inteiro, SP), usados nos testes do pipeline, e as contagens por satélite estão em [firms-extracao-dados.md](firms-extracao-dados.md), seção 4. Na Amazônia, o S-NPP detecta cerca de 6,3× mais focos que o Aqua. Os três VIIRS têm contagens quase iguais em todos os meses, e todos os sensores têm o pico em setembro.

## Checklist

- [x] Histórico do FIRMS: trocado pelos resumos anuais por país (Brasil, sem fila de aprovação) + API para 2026 ([pipeline-dados.md](pipeline-dados.md))
- [x] Baixar o shapefile de biomas do IBGE (`pipeline.py cadastrar`)
- [x] Baixar a série mensal do INPE (`pipeline.py inpe`, os 6 biomas)
- [x] Pedir a MAP\_KEY do FIRMS para os jobs de atualização
- [x] Testar o importador com os arquivos de 2024 (contagens batem com a tabela acima, diferença < 0,2%)
- [x] Carregar o histórico completo (banco de teste: 46,4 milhões de focos)
- [ ] Carregar o banco na VPS e ligar o job NRT (roteiro em [banco.md](banco.md), depende do `docker-compose` do backend)
