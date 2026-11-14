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

## Como preencher o pedido no FIRMS

O pedido é feito em [Archive Download](https://firms.modaps.eosdis.nasa.gov/download/create.php), com login do Earthdata ou código por e-mail. Não é preciso preencher polígono nem coordenadas.

| Campo | Valor |
| --- | --- |
| Região | Country → Brazil |
| Buffer | 0 km |
| Fire Source | MODIS, VIIRS S-NPP e VIIRS NOAA-20 |
| From | 2000-11-01 |
| To | data de hoje |
| Formato | Comma-Separated Text (.csv) |
| E-mail de confirmação | Marcar |

Cada sensor vem só no período em que existe, então um pedido único de 2000-11-01 até hoje já cobre os três. Se o formulário recusar um período tão longo, dividam assim:

1. MODIS: 2000-11-01 até hoje
2. VIIRS S-NPP: 2012-01-20 a 2026-11-02
3. VIIRS NOAA-20: 2018-04-01 até hoje

O formulário avisa que os pedidos são monitorados e aprovados pela equipe do FIRMS. O arquivo não sai na hora, então façam o pedido o quanto antes. Enquanto ele não chega, o pipeline é testado com os arquivos de 2024 que já temos.

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
| Atualização NRT | A cada 3 h | `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT` | Últimas 48 h | Upsert dos focos novos, recalcula os dias e o mês atuais em `agregados` e renova o cache da API |
| Recarga SP | Mensal | `VIIRS_NOAA20_SP` | Últimos \~6 meses | **Fora do escopo da submissão.** Substituiria os dados NRT pelos de qualidade científica, que chegam com cerca de 5 meses de defasagem |

O MODIS não entra no job NRT, porque o Aqua só é usado até janeiro de 2012. O NOAA-21 entra só como reserva. O fator de calibração fica congelado depois da carga histórica. Os jobs só aplicam o fator, nunca recalibram. Os dados NRT não trazem a coluna `type`, então as fontes estáticas são filtradas pelas células H3 marcadas como `type = 2` no histórico SP.

## Dados de teste já baixados

Temos o Brasil inteiro de 01/01/2024 a 31/12/2024, dados de arquivo (SP), para testar o pipeline enquanto o pedido completo não chega.

| Arquivo | Satélite | Focos no Brasil | Amazônia Legal (bbox aprox.) |
| --- | --- | --- | --- |
| `fire_archive_M-C61_848018.csv` | Aqua | 319.074 | 242.292 |
| `fire_archive_M-C61_848018.csv` | Terra | 208.820 | 165.440 |
| `fire_archive_SV-C2_848021.csv` | S-NPP | 1.935.740 | 1.524.471 |
| `fire_archive_J1V-C2_848019.csv` | NOAA-20 | 1.988.404 | 1.564.429 |
| `fire_archive_J2V-C2_848020.csv` | NOAA-21 | 1.948.842 | 1.531.634 |

Na Amazônia, o S-NPP detecta cerca de 6,3× mais focos que o Aqua. Os três VIIRS têm contagens quase iguais em todos os meses, e todos os sensores têm o pico em setembro.

## Checklist

- [ ] Fazer o pedido no FIRMS (Brasil, 2000-11-01 até hoje, MODIS + S-NPP + NOAA-20, CSV)
- [ ] Baixar o shapefile de biomas do IBGE
- [ ] Baixar a série mensal do bioma Amazônia do INPE
- [ ] Pedir a MAP\_KEY do FIRMS para os jobs de atualização
- [ ] Testar o importador com os arquivos de 2024
- [ ] Carregar o histórico completo quando o pedido chegar
