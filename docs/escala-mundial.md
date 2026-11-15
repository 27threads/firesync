# Restrições para levar o sistema ao mundo

Nov 14, 2026 · frente C

A cobertura da submissão é **o Brasil**. O desenho já evita depender de uma região (região é dado, não código), mas ainda há pontos que **só aparecem em escala mundial**. Nenhum deles bloqueia a submissão. Este documento existe para ninguém descobrir isso depois, em produção.

Cada item diz o problema, o que acontece se for ignorado e a saída proposta.

## Seleção de área (`POST /calendar`)

| # | Problema | Se ignorar | Saída proposta |
| --- | --- | --- | --- |
| 1 | **Polígono que cruza a longitude ±180°** (Pacífico, leste da Rússia, Fiji) | A conversão em hexágonos interpreta o polígono pelo lado errado do planeta e devolve a área errada, sem erro | Cortar o polígono em dois na linha de ±180° antes de converter. O Leaflet pode mandar longitudes fora de −180 a 180, então normalizar antes |
| 2 | **Áreas do tamanho de continentes** | Na resolução 6, a África dá mais de 800 mil células. Passa do limite de 250.000 e, mesmo sem limite, a conversão e a consulta levariam muitos segundos | Tabela agregada em **resolução 4** (~1.770 km²), gravada pelo mesmo job de agregação. A África cabe em uns 17 mil hexágonos. A API escolhe a tabela pelo tamanho da área. Custo: até ~40 km de erro na borda, informado em `area_km2` |
| 3 | **Cobertura é um país só** (`config.cobertura_pais = 'Brazil'`) | Não dá para ter dois países | Trocar por uma lista ou tabela de países cobertos. A resposta `coverage` já trata área parcial |

## Camada de focos recentes (`GET /detections/recent`)

| # | Problema | Se ignorar | Saída proposta |
| --- | --- | --- | --- |
| 4 | **Volume com o mapa do mundo** | Algumas centenas de milhares de focos em 7 dias numa consulta só (estimativa), mais a junção de hexágonos na API, que pode levar segundos | O job NRT grava, a cada 3 h, a contagem por hexágono nas resoluções 4, 5 e 6 para 24 h, 72 h e 7 dias. O mapa do mundo vira uma leitura pronta. É a pré-agregação que o RNF04 pede |
| 5 | **Juntar hexágonos no Python** | Uma chamada de `cell_to_parent` por célula, centenas de milhares de vezes | Calcular o hexágono pai no SQL com operações de bits, como já fazemos no `CHECK` da resolução |
| 6 | **Bbox que dá a volta no mundo** | Ao arrastar o mapa mais de uma volta, o Leaflet manda longitudes como 200° e a consulta volta vazia | Normalizar o bbox para −180 a 180 e, se ele cruzar ±180°, dividir em duas consultas |
| 7 | **Atualização pela API de área do FIRMS** | Limite de 5.000 transações a cada 10 minutos. O mundo inteiro em pedaços de bbox estoura o limite | Usar os arquivos globais de NRT que o FIRMS publica (24 h, 48 h e 7 dias) |

## Dados e banco

| # | Problema | Se ignorar | Saída proposta |
| --- | --- | --- | --- |
| 8 | **Tamanho da tabela `focos`** | O Brasil já tem 46,4 milhões de focos. O mundo deve passar de dez vezes isso | Particionar `focos` por ano. Avaliar se o histórico completo precisa ficar no banco ou só em parquet, para o export de auditoria |
| 9 | **Focos NRT se acumulam** | Sem a recarga SP mensal (cortada no escopo atual), os focos NRT nunca são substituídos, e essa parte da tabela só cresce | Voltar com a recarga SP, ou apagar o NRT de meses que já têm SP |
| 10 | **Download do histórico** | O resumo anual por país tem um arquivo por país e por ano. O mundo são centenas de países × 25 anos | Script de download com retomada (o da frente A já retoma) e uma lista de países em configuração |
| 11 | **Regiões de calibração no mundo** | O fator Aqua → S-NPP muda por bioma. Fora do Brasil não existe o polígono do IBGE | Usar um mapa global de biomas ou ecorregiões, cadastrado pelo mesmo `regioes.json`. Regiões com pouca sobreposição usam a região vizinha mais parecida, como já previsto |
| 12 | **Validação fora do Brasil** | A série do INPE só cobre o Brasil | Usar a área queimada global da NASA (MCD64A1 / GlobFire), a mesma da issue #9 |

## Tempo e calendário

| # | Problema | Se ignorar | Saída proposta |
| --- | --- | --- | --- |
| 13 | **Meses e dias em UTC** | Num fuso de UTC−10 ou UTC+12, um foco perto da meia-noite cai no dia, ou até no mês, vizinho. No mês, o efeito é pequeno. Na janela de 7 dias, pode mudar a contagem | Documentar que tudo é UTC. Se incomodar, calcular o dia pelo fuso local da célula |
| 14 | **Hemisférios** | Nenhum: o calendário e a janela de ±15 dias já comparam a mesma época de cada lugar | — |
| 15 | **Mapa perto dos polos** | O mapa (Web Mercator) não mostra acima de ~85° de latitude | Nenhum impacto prático: há pouco fogo acima de ~70° |

## Interface

| # | Problema | Se ignorar | Saída proposta |
| --- | --- | --- | --- |
| 16 | **Nomes de regiões** | `name` vem com o nome oficial da fonte (por exemplo, "Amazônia") | Campo de nome em inglês, ou tradução no front |

## O que fazer antes

Ordem sugerida quando o mundo entrar no escopo:

1. Itens **2, 4 e 5**: pré-agregação em resolução grossa. É o que mais pesa no desempenho.
2. Itens **1 e 6**: a longitude ±180°. Bugs silenciosos, que devolvem resultado errado sem erro.
3. Itens **3, 8, 10 e 11**: dados e banco.
4. Os demais.

**Teste mínimo:** carregar o arquivo global de NRT de 7 dias do FIRMS no banco de teste e medir, com o mapa mostrando o mundo, o tempo do banco, o tempo da API, o tamanho da resposta e quanto o Leaflet leva para desenhar.
