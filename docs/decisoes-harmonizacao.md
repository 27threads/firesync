# Decisões da harmonização

Responsável pelas decisões: Weberson. Itens marcados como **ESCOLHA DA EQUIPE** são decisões nossas, não fatos. Itens marcados como **PROPOSTA** esperam confirmação da equipe.

Este documento incorpora a revisão feita no PR 1 (comentário de nogran). Onde a revisão corrigiu um erro da primeira versão, isso está indicado.

## 1. Decidido

| Tema | Decisão | Origem |
| --- | --- | --- |
| Escala da série final | **Escala VIIRS.** Os anos só-MODIS são convertidos para a escala do VIIRS. ESCOLHA DA EQUIPE | Weberson, 14/11/2026 |
| Cuidado com as escalas | Ver seção 2 | Weberson, 14/11/2026 |
| Satélite do MODIS | Só o Aqua. Terra fora do cálculo, calendário a partir de 2003 | Time de dados (`pipeline-dados.md`) |
| Grade | H3 resolução 6 | `banco.md` (PR #2) |
| FRP | Fica no projeto, mas **fora das condições do fator** (seção 3) | Revisão do PR 1 |
| Áreas críticas | Diferencial do app: contagem de focos mais energia (`frp_soma`) por célula, no período do VIIRS | Weberson, 14/11/2026 |
| Anos de calibração | **Decididos pela validação, com critério fixado antes** (seção 4): base 2012 a 2024, e os 10 cenários de 2012 a 2021 se a deriva do Aqua atrapalhar. 2025 em diante fora | Equipe (PR 3), aceito pelo Weberson |
| NOAA-20 → S-NPP | **Fator 1 (tratados como iguais).** O mês atual mostra a mesma contagem do FIRMS. A diferença medida (razões entre 0,97 e 1,04) é declarada no Método | Weberson, 14/11/2026 |
| Baixa confiança | Guardada à parte, **fora do fator e do calendário** (seção 4) | Equipe (PR 1), aceito pelo Weberson |
| Biomas calibrados | Os **6 biomas do IBGE**. A demo destaca Amazônia e Pantanal, e os outros biomas aparecem na seleção da interface | Equipe (PR 1), aceito pelo Weberson |
| Dados provisórios (NRT) | Marcados com `qualidade = NRT`, fora do cálculo do fator | `banco.md` (PR #2) |
| Duplicatas | Só linhas idênticas, nos dois sensores. O calendário conta **detecções de fogo**. Motivos em `regras-variaveis.md` | Weberson, 14/11/2026 |

## 2. Cuidados para não misturar as escalas

1. Todo número carrega a escala e a origem: **observado pelo VIIRS** ou **estimado a partir do MODIS, com faixa**. Nunca aparece um número sem rótulo. A origem depende só da data: até janeiro de 2012 é estimado (Aqua × fator), de fevereiro de 2012 em diante é observado pelo VIIRS. Uma área sem fogo continua com origem definida.
2. O calendário marca a troca de sensor (2012), para ninguém ler a diferença entre 2011 e 2012 como aumento real de fogo.
3. Nunca somar nem comparar a contagem bruta do MODIS com a do VIIRS. Toda comparação entre sensores passa pelo fator ou é feita por célula da grade.
4. O INPE só se compara pela **forma da curva** (anos altos, meses de pico), nunca pelo valor absoluto, porque o INPE conta na escala de um satélite só.
5. A faixa de incerteza aparece só nos números estimados. Os meses observados pelo VIIRS não ganham faixa de conversão.
6. No teste do modelo, o MODIS convertido é comparado só com o VIIRS real do mesmo ano.

## 3. O papel do FRP

O FRP (potência do fogo, em MW) continua no projeto, em quatro usos: pista do classificador, coluna `frp_soma` em `agregados`, indicador de áreas críticas e regra de limpeza (FRP vazio, zero ou negativo sai).

Ele **sai só das condições do fator de conversão**. Motivo (correção da primeira versão): o fator precisa de condições que existam também nos anos só-MODIS, e os fogos que o MODIS não viu não têm FRP registrado.

Cuidado: o FRP do MODIS e o do VIIRS não são comparáveis, porque o pixel do MODIS é muito maior. A intensidade por célula só é mostrada no período do VIIRS (2012 em diante). Para 2003 a 2011, a intensidade não é mostrada na demonstração. ESCOLHA DA EQUIPE.

## 4. DECIDIDO (Weberson, 14/11/2026): como calcular o fator e a faixa

Condições do fator: **bioma × mês × dia/noite**. Essas são as condições que existem nos dois períodos.

1. Contar, por célula H3 e mês, os focos do Aqua e os do S-NPP nos anos de calibração (definidos pela regra do item 4). Só confiança nominal e alta: o arquivo de baixa confiança (MODIS abaixo de 30, VIIRS `l` de dia) fica guardado à parte e **não entra no fator nem no calendário**, porque os dois precisam usar o mesmo filtro.
2. Somar por bioma, mês e dia/noite e calcular o fator Aqua para S-NPP (quantos focos do VIIRS cada foco do Aqua representa). Calibrar os 6 biomas do IBGE.
3. Cada ano de calibração gera um fator, e cada fator é um **cenário**. A faixa de incerteza é o **percentil 5 e o percentil 95** entre os cenários, por interpolação linear (trocado de P10 a P90 pelo Weberson em 14/11/2026, ver "Resultado da calibração").
4. **Escolha dos anos pela validação, com critério fixado antes de rodar** (equipe, PR 3; aceito pelo Weberson em 14/11/2026):
   - **Base:** sobreposição Aqua × S-NPP de 2012 a 2024 (13 anos).
   - **Validação deixando um ano de fora:** para cada ano, calcular o fator com os outros 12, aplicar ao Aqua do ano deixado de fora e comparar com o S-NPP real.
   - **Erro do ano:** erro ponderado por bioma, `soma dos |estimado − observado| / soma dos observados` nos 12 meses (aprovado pelo Mateus no PR #4, no lugar da média simples). Para a decisão vale a Amazônia, que tem mais focos.
   - **Critério:** se o erro médio de 2022 a 2024 passar de **1,5×** o erro médio de 2012 a 2021, a deriva de órbita do Aqua atrapalhou, e a calibração fica com **2012 a 2021 (10 cenários)**. Senão, ficam os **13 anos**. O limite de 1,5× é ESCOLHA DA EQUIPE, não um padrão estatístico.
   - **Registro:** a tabela com o erro de cada ano e a decisão entram neste documento, e o resumo vai para a tela de Método. Também reportar quantas vezes o valor real cai dentro da faixa (P5 a P95).
5. 2025 em diante fica fora do cálculo. A razão S-NPP/Aqua caiu para 4,8 (contra cerca de 6), provavelmente pela deriva de órbita do Aqua. Com a escala VIIRS, isso não afeta o calendário recente: de 2012 em diante os números são do VIIRS, e o Aqua só é usado em 2003 a 2011, quando a órbita ainda era normal.

**Regras de cálculo da calibração (DECIDIDO, Weberson, 14/11/2026, salvo onde indicado):**

- **Fator = razão das somas.** `F_k(b, m, p) = S_k(b, m, p) / A_k(b, m, p)`, em que `S_k` e `A_k` são os totais de focos do S-NPP e do Aqua (confiança nominal e alta, `tipo = 0`) nas células do bioma `b`, no mês `m`, no período `p` (D ou N) e no ano `k`. Nunca a média das razões por célula, que explode em células com pouco Aqua.
- **Dias sem dado ficam fora.** Na calibração, sai todo dia em que o Aqua ou o S-NPP aparece em `dias_sem_dados`, dos dois satélites ao mesmo tempo. Sem isso, a falha de um só satélite distorce a razão do mês.
- **Janeiro de 2012 fica fora.** O S-NPP só começa em 20/01/2012. O mês de janeiro fica com um cenário a menos.
- **Ordem da fusão** quando `A_k` não atinge o mínimo de focos: 1º somar com os meses vizinhos (`m − 1` e `m + 1`) no mesmo período e no mesmo ano (o vizinho de dezembro é o janeiro do mesmo ano, e não o do ano seguinte: cada cenário usa só o próprio ano, e os dois meses são da mesma estação); 2º usar o ano inteiro do bioma **no mesmo período** (noite com noite); 3º só em último caso, o ano inteiro com dia e noite juntos. A fusão usada fica em `fusao_com`, e `n_focos_origem` guarda o `A_k` que sustentou o fator. Ordem trocada pelo Weberson em 14/11/2026 depois do protótipo B1: o fator noturno é cerca de 5× o diurno (Amazônia 2024: dia 2,4 a 4,5, noite 12 a 25), e juntar dia e noite cedo puxava a noite para o fator do dia (Caatinga, março, noite: 25,4 próprio, 9,4 com dia e noite, 23,8 com o ano inteiro da noite).
- **Validação deixando um ano de fora:** para o ano `y`, o fator de cada condição é a **mediana** dos `F_k` dos outros anos (como na série). Estimado = soma de `A_y × mediana`. Observado = `S_y`. A cobertura da faixa usa o P5 e o P95 dos `E_k` dos outros anos.
- **Medida de erro (DECIDIDO, aprovado no PR #4):** **erro ponderado do ano**, `soma dos |estimado − observado| / soma dos observados` nos 12 meses, no lugar da média de `|estimado − observado| / observado` mês a mês. Motivo: num mês com pouco fogo, um erro pequeno vira uma porcentagem enorme e poderia disparar o critério de 1,5× sozinho, mesmo sem efeito no calendário. O critério de 1,5× não muda.

**Salvaguardas obrigatórias (aceitas junto com a decisão):**

- **Suposição declarada no Método:** o fator supõe que a razão entre os sensores em 2003 a 2011 é parecida com a dos anos de calibração. Isso não pode ser testado, porque não há VIIRS antes de 2012. A queda de 2025 mostra que a razão pode mudar. A faixa mede só a variação entre anos, e não esse risco.
- **Mínimo de focos por condição:** cada combinação de bioma, mês e dia/noite precisa de um mínimo de focos do Aqua para ter fator próprio. Abaixo disso, junta com a condição vizinha e registra a fusão em `fatores_harmonizacao`. O valor do mínimo é definido com a base limpa. ESCOLHA DA EQUIPE.

Por que contagens por célula e não o classificador ponto a ponto: é mais barato, usa 10 ou 13 pontos para a faixa em vez de 4, e dispensa a regra "MODIS estava olhando", que gerava viés (descartava justamente as áreas onde o VIIRS viu fogo e o MODIS nada).

**Contrato para a API (DECIDIDO, Weberson, 14/11/2026):** adotamos o formato da frente A (`docs/banco.md`, PR #2). `agregados` guarda a contagem **bruta** por célula × ano × mês × satélite × dia/noite, e `fatores_harmonizacao` guarda um fator por cenário (ano de calibração). A API soma as contagens da área, multiplica pelos fatores de cada cenário e só então calcula a mediana e a faixa (P5 e P95), porque a soma dos percentis das células não é o percentil da soma. Mudar um fator não exige refazer `agregados`.

### Resultado da calibração (B3, primeira rodada, 14/11/2026)

O Eduardo rodou `data-pipeline/harmonizacao/calibrar.py` (branch `trabalho/harmonizacao`) no banco de teste com o histórico completo (46,4 milhões de focos, `dias_sem_dados` com 169 dias), sem gravar. Mínimo de 30 focos, 1.860 condições, 451 com fusão.

**Decisão dos anos: ficam os 13 (2012 a 2024).** A deriva do Aqua não atrapalhou.

| Medida de erro (Amazônia) | 2012 a 2021 | 2022 a 2024 | Razão | Limite |
| --- | --- | --- | --- | --- |
| Ponderado (decidida) | 5,7% | 6,4% | 1,13 | 1,5 |
| Simples (original) | 9,2% | 11,4% | 1,24 | 1,5 |

Erro ponderado por ano na Amazônia: de 2,4% (2017) a 12,6% (2020).

**Cobertura da faixa:** com P10 a P90, o valor real caiu dentro em 0,58 a 0,69 dos meses (Amazônia 0,69). Isso é o esperado pela aritmética: com poucos cenários, a faixa entre percentis cobre menos do que o nome sugere. Numa simulação com anos intercambiáveis (200 mil sorteios), um ano novo cai dentro de:

| Faixa | 12 cenários (validação) | 13 cenários (série) |
| --- | --- | --- |
| P10 a P90 | 68% | 69% |
| **P5 a P95 (decidida)** | **78%** | **79%** |

Por isso a faixa passou a ser **P5 a P95**, que corresponde a "cerca de 8 em 10".

### Resultado final da calibração (B3, gravada em 14/11/2026)

O Eduardo rodou a versão final (`calibrar.py` com P5 a P95 e erro ponderado, branch `trabalho/harmonizacao`) com `--gravar` no banco de teste. O autoteste passou.

- **Anos:** os 13 (2012 a 2024). Razão do erro ponderado 1,13, abaixo de 1,5×.
- **Fatores gravados:** 1.860 em `fatores_harmonizacao` (Aqua → SNPP), 6 biomas, 13 anos, 12 meses, dia e noite. Mínimo de 30 focos do Aqua; 451 condições com fusão.
- **Cobertura medida da faixa P5 a P95** (fração dos meses em que o valor real caiu dentro, média dos anos):

| Bioma | Cobertura | Na tela |
| --- | --- | --- |
| Cerrado | 0,80 | cerca de 8 em 10 |
| Amazônia | 0,79 | cerca de 8 em 10 |
| Mata Atlântica | 0,77 | cerca de 8 em 10 |
| Caatinga | 0,76 | cerca de 8 em 10 |
| Pantanal | 0,76 | cerca de 8 em 10 |
| Pampa | 0,68 | cerca de 7 em 10 |

Cinco biomas ficaram no valor esperado pela teoria (cerca de 0,78). O Pampa ficou abaixo, porque tem pouquíssimos focos e quase todos os fatores noturnos dele precisaram de fusão.

**Regra da tela (combinada com o Mateus no PR #4):** a tela diz "cerca de N em 10" com o **N medido de cada bioma**, sem prometer um número que não foi medido.

**Anos excepcionais:** na Amazônia, a cobertura caiu em 2020 (0,67) e 2024 (0,58), anos de seca e fogo extremos. O erro ponderado também foi o maior nesses anos (12,6% e 9,5%). Limite a declarar no Método: em anos que fogem do padrão, a estimativa erra mais e a faixa cobre menos.

**Cobertura dentro e fora da temporada de fogo (pedida pelo Mateus no PR #4):** calculada com o `validacao_meses.csv` da rodada gravada (930 linhas, enviado pelo Eduardo no PR #21). A cobertura geral de cada bioma confere com o relatório da rodada. A **temporada de fogo** de cada bioma são os meses com mais fogo que, juntos, somam 80% das detecções do ano, pela média do VIIRS observado de 2012 a 2024 (ESCOLHA DA EQUIPE, porque a estação seca muda de bioma para bioma).

| Bioma | Temporada de fogo | Cobertura na temporada | Cobertura fora | Erro ponderado na temporada | Erro ponderado fora | Parte do fogo na temporada |
| --- | --- | --- | --- | --- | --- | --- |
| Amazônia | ago, set, out, nov | **0,87** | 0,75 | 5,2% | 10,2% | 82% |
| Pantanal | jul, ago, set, out, nov | **0,86** | 0,68 | 10,0% | 13,2% | 86% |
| Caatinga | ago, set, out, nov, dez | **0,83** | 0,71 | 10,2% | 16,1% | 86% |
| Mata Atlântica | jan, jul, ago, set, out, nov, dez | 0,78 | 0,77 | 8,1% | 11,6% | 81% |
| Cerrado | jul, ago, set, out | 0,77 | 0,82 | 4,8% | 8,7% | 84% |
| Pampa | 9 meses, sem temporada clara | 0,66 | 0,72 | 16,2% | 21,4% | 83% |

Leitura: nos meses que concentram mais de 80% do fogo, a faixa acerta cerca de 8,5 em 10 na Amazônia, no Pantanal e na Caatinga, e o erro cai pela metade na Amazônia. A conversão é mais confiável quando as equipes mais precisam dela. Os meses fora da temporada acertam menos, mas têm pouco fogo.

Dois alertas:

- **Pampa subestimado:** na temporada, quando o real fica fora da faixa, ele fica **acima** em 30 de 39 casos. A estimativa do Pampa sai baixa, coerente com o Aqua quase sem fogo noturno lá e com a fusão de dia e noite no último recurso.
- **2024 na Amazônia:** 3 dos 4 meses da temporada ficaram fora da faixa (seca extrema), o que confirma o limite dos anos excepcionais.

**Classe de intensidade na tela (aprovada no PR #4, `api.md`):** `low` abaixo de 5 MW, `medium` de 5 a 25 MW, `high` de 25 MW ou mais **ou** pixel saturado do VIIRS (confiança alta). Limites fixos na tela. A regra do pixel saturado vale só para o VIIRS: no MODIS, confiança alta não indica saturação.

As colunas `n_focos_origem` e `fusao_com`, pedidas à frente A para a salvaguarda do mínimo de focos, entraram na migration 002 (PR #2) e já foram preenchidas pela calibração gravada.

**Anos de calibração:** ver o item 4. A diferença de processamento entre 10 e 13 cenários é desprezível. O que pesa é o risco da deriva do Aqua, e o critério fixado antes de rodar evita escolher os anos depois de ver o resultado.

**NOAA-20 → S-NPP (DECIDIDO, Weberson, 14/11/2026): fator 1.** O NOAA-20 só é usado de novembro de 2026 em diante, ou seja, no mês atual, que o RF11 compara com a mediana. Tratar os dois como iguais faz o mês atual mostrar a mesma contagem que o usuário vê no FIRMS. As razões anuais NOAA-20/S-NPP ficaram entre 0,97 e 1,04, e um fator por mês e dia/noite teria mais ruído que a própria diferença. A razão de 1,12 em 2026 não conta, porque o S-NPP parou no meio do ano. Limite declarado no Método: diferença de até 4% entre os dois VIIRS.

## 5. DECIDIDO (Weberson, 14/11/2026): o classificador (modelo A) como análise complementar

O classificador aprende a chance de o MODIS ver cada fogo do VIIRS, usando FRP, temperatura, confiança, mês, dia/noite, bioma e `modis_scan_mediano`. Ele **não gera o fator da série**. Serve para a tela de Método mostrar quais fogos o MODIS perde por potência (fraco ou forte).

- Roda em volume pequeno (treino 2019 a 2021, teste 2022 a 2024).
- A regra "MODIS estava olhando" (foco do Aqua a até 50 km) vale só aqui, e o viés que ela causa é declarado.
- Se só houver os arquivos de 2024, o corte é **no espaço**: metade das células H3 para treino e metade para teste, com todos os meses dos dois lados.

## 6. Limites a declarar no método

- O fator é por bioma, mês e dia/noite. Não corrige por potência do fogo.
- A faixa de incerteza reflete a variação entre anos de sobreposição e não cobre outras fontes de erro. Cobertura medida: cerca de 8 em 10 em cinco biomas, cerca de 7 em 10 no Pampa. Na temporada de fogo, cerca de 8,5 em 10 na Amazônia, no Pantanal e na Caatinga.
- No Pampa, a estimativa tende a ficar abaixo do real (pouquíssimo fogo noturno visto pelo Aqua).
- Em anos de fogo excepcional (como 2020 e 2024 na Amazônia), a estimativa erra mais e a faixa cobre menos.
- A deriva de órbita do Aqua (depois de 2022) só pode afetar a calibração, e a validação deixando um ano de fora mede isso. O calendário de 2012 em diante usa o VIIRS e não é afetado.
- **Contagem baixa do Aqua no período estimado:** se o Aqua viu zero ou poucos focos numa área pequena num mês fraco, a estimativa também fica zero ou baixa, mesmo que o VIIRS fosse ver fogos pequenos. A faixa não captura isso. PROPOSTA para a frente C: a API marca o mês estimado como "estimativa pouco confiável" quando a contagem bruta do Aqua na área for menor que 10 (limite ESCOLHA DA EQUIPE).
- Calibrado por bioma do IBGE. Não vale automaticamente para regiões fora do Brasil.
- O número do calendário conta **detecções de fogo** (fire detections, convenção do FIRMS), e não incêndios: uma frente de fogo gera várias detecções.
- O NOAA-20 (mês atual) é tratado como igual ao S-NPP. A diferença medida entre os dois é de até 4%.
- O uso de IA neste trabalho é declarado no campo "Use of Super Intelligence" e no README.

## 7. Pendências

1. ~~Cobertura da faixa por estação~~: feita (seção "Cobertura dentro e fora da temporada de fogo").
2. **B6, comparação com o INPE.** O script está pronto (`data-pipeline/harmonizacao/validar_inpe.py`, branch `trabalho/harmonizacao`) e passou no autoteste com dados inventados (degrau de +1% com fatores certos, +102% com fatores pela metade). O PR #21 (série do INPE com o satélite de referência: NOAA-12 até 03/07/2002, Aqua depois) já entrou na `main`.

   **Estado em 14/11/2026:** o Eduardo fez uma primeira rodada no banco de teste, e a revisão do Mateus (PR #26) achou três erros no script, já corrigidos com um teste para cada um: a faixa anual somava os percentis dos meses (agora soma por cenário), meses sem detecção saíam da comparação (agora entram como zero) e gravar os fatores não mudava a versão dos dados. Falta o Eduardo **rodar a B6 de novo** com a versão corrigida. **Só depois dessa rodada** os números entram aqui e os gráficos vão para a página do projeto.

   **Resultado da primeira rodada (PROVISÓRIO, de uma versão com os erros acima; não usar na página do projeto nem no vídeo):**

   - Forma da série: correlação mensal de 0,94 a 0,99 por bioma (Amazônia 0,992), anual de 0,89 a 0,99, sazonalidade de 0,95 a 1,00; 4 ou 5 dos 5 anos com mais fogo em comum com o INPE; mês de pico igual (tolerância de 1 mês) em 83% a 100% dos anos.
   - Degrau em 2012: Amazônia −2,4%, Caatinga +2,9%, Cerrado +5,9%, Pantanal +9,9%, Pampa +10,8%, Mata Atlântica −14,1%. Três biomas ficam entre 10% e 14%, o que é pequeno diante do teste inventado com erro (+102%), mas não é "quase nada" e precisa ser declarado no Método se a segunda rodada confirmar.
   - O Pantanal saiu com 275 meses e 22 anos completos, contra 276 e 23 dos outros biomas: é a marca do erro dos meses zerados, então os números dele são os que mais devem mudar.
   - A queda da razão em 2025 (cerca de 4,9) aparece no gráfico e já está declarada nos limites.

   A comparação mede, por bioma: correlação mensal e anual, os 5 anos com mais fogo, o mês de pico, a sazonalidade e o **degrau em 2012** (razão firesync/INPE antes e depois da troca de satélite; perto de zero quer dizer que a troca não inventou fogo). Contexto da frente A (issue #19): a série do Aqua no FIRMS já tem correlação mensal de 0,998 com a do INPE e o mesmo mês de pico em 23 de 23 anos, então o degrau em 2012 mede principalmente a nossa conversão.
3. **Levar o código da B3 e da B6 para o `main`.** Os scripts (`prototipo_fator.py`, `calibrar.py`, `validar_inpe.py` e os autotestes) estão só na branch `trabalho/harmonizacao`. O envio direto ao `main` foi bloqueado pelo controle de permissões em 14/11/2026. Depende de decisão do Weberson: abrir um PR ou liberar o envio.
4. Confirmar o mínimo de focos por condição (a calibração gravada usou 30).
5. Investigar a queda de S-NPP/Aqua em 2025.
6. Esta decisão muda o que o contexto do projeto dizia sobre o modelo A (o classificador deixa de gerar o fator da série). A equipe deve concordar com a mudança.
