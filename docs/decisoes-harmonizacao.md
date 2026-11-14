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
3. Cada ano de calibração gera um fator, e cada fator é um **cenário**. A faixa de incerteza é o percentil 10 e o percentil 90 entre os cenários (13 ou 10, conforme o item 4).
4. **Escolha dos anos pela validação, com critério fixado antes de rodar** (equipe, PR 3; aceito pelo Weberson em 14/11/2026):
   - **Base:** sobreposição Aqua × S-NPP de 2012 a 2024 (13 anos).
   - **Validação deixando um ano de fora:** para cada ano, calcular o fator com os outros 12, aplicar ao Aqua do ano deixado de fora e comparar com o S-NPP real.
   - **Erro do ano:** erro relativo médio mensal por bioma, isto é, a média de `|estimado − observado| / observado` nos 12 meses. Para a decisão vale a Amazônia, que tem mais focos. Há uma proposta de troca desta medida pelo erro ponderado, em "Regras de cálculo da calibração" abaixo.
   - **Critério:** se o erro médio de 2022 a 2024 passar de **1,5×** o erro médio de 2012 a 2021, a deriva de órbita do Aqua atrapalhou, e a calibração fica com **2012 a 2021 (10 cenários)**. Senão, ficam os **13 anos**. O limite de 1,5× é ESCOLHA DA EQUIPE, não um padrão estatístico.
   - **Registro:** a tabela com o erro de cada ano e a decisão entram neste documento, e o resumo vai para a tela de Método. Também reportar quantas vezes o valor real cai dentro da faixa de 80%.
5. 2025 em diante fica fora do cálculo. A razão S-NPP/Aqua caiu para 4,8 (contra cerca de 6), provavelmente pela deriva de órbita do Aqua. Com a escala VIIRS, isso não afeta o calendário recente: de 2012 em diante os números são do VIIRS, e o Aqua só é usado em 2003 a 2011, quando a órbita ainda era normal.

**Regras de cálculo da calibração (DECIDIDO, Weberson, 14/11/2026, salvo onde indicado):**

- **Fator = razão das somas.** `F_k(b, m, p) = S_k(b, m, p) / A_k(b, m, p)`, em que `S_k` e `A_k` são os totais de focos do S-NPP e do Aqua (confiança nominal e alta, `tipo = 0`) nas células do bioma `b`, no mês `m`, no período `p` (D ou N) e no ano `k`. Nunca a média das razões por célula, que explode em células com pouco Aqua.
- **Dias sem dado ficam fora.** Na calibração, sai todo dia em que o Aqua ou o S-NPP aparece em `dias_sem_dados`, dos dois satélites ao mesmo tempo. Sem isso, a falha de um só satélite distorce a razão do mês.
- **Janeiro de 2012 fica fora.** O S-NPP só começa em 20/01/2012. O mês de janeiro fica com um cenário a menos.
- **Ordem da fusão** quando `A_k` não atinge o mínimo de focos: 1º somar com os meses vizinhos (`m − 1` e `m + 1`) no mesmo período; 2º usar o ano inteiro do bioma **no mesmo período** (noite com noite); 3º só em último caso, o ano inteiro com dia e noite juntos. A fusão usada fica em `fusao_com`, e `n_focos_origem` guarda o `A_k` que sustentou o fator. Ordem trocada pelo Weberson em 14/11/2026 depois do protótipo B1: o fator noturno é cerca de 5× o diurno (Amazônia 2024: dia 2,4 a 4,5, noite 12 a 25), e juntar dia e noite cedo puxava a noite para o fator do dia (Caatinga, março, noite: 25,4 próprio, 9,4 com dia e noite, 23,8 com o ano inteiro da noite).
- **Validação deixando um ano de fora:** para o ano `y`, o fator de cada condição é a **mediana** dos `F_k` dos outros anos (como na série). Estimado = soma de `A_y × mediana`. Observado = `S_y`. A cobertura da faixa usa o P10 e o P90 dos `F_k` dos outros anos.
- **Medida de erro (PROPOSTA do Weberson, precisa de acordo da equipe antes de rodar):** trocar a média de `|estimado − observado| / observado` mês a mês pelo **erro ponderado do ano**, `soma dos |estimado − observado| / soma dos observados` nos 12 meses. Motivo: num mês com pouco fogo, um erro pequeno vira uma porcentagem enorme e pode disparar o critério de 1,5× sozinho, mesmo sem efeito no calendário. O critério de 1,5× não muda.

**Salvaguardas obrigatórias (aceitas junto com a decisão):**

- **Suposição declarada no Método:** o fator supõe que a razão entre os sensores em 2003 a 2011 é parecida com a dos anos de calibração. Isso não pode ser testado, porque não há VIIRS antes de 2012. A queda de 2025 mostra que a razão pode mudar. A faixa mede só a variação entre anos, e não esse risco.
- **Mínimo de focos por condição:** cada combinação de bioma, mês e dia/noite precisa de um mínimo de focos do Aqua para ter fator próprio. Abaixo disso, junta com a condição vizinha e registra a fusão em `fatores_harmonizacao`. O valor do mínimo é definido com a base limpa. ESCOLHA DA EQUIPE.

Por que contagens por célula e não o classificador ponto a ponto: é mais barato, usa 10 ou 13 pontos para a faixa em vez de 4, e dispensa a regra "MODIS estava olhando", que gerava viés (descartava justamente as áreas onde o VIIRS viu fogo e o MODIS nada).

**Contrato para a API (DECIDIDO, Weberson, 14/11/2026):** adotamos o formato da frente A (`docs/banco.md`, PR #2). `agregados` guarda a contagem **bruta** por célula × ano × mês × satélite × dia/noite, e `fatores_harmonizacao` guarda um fator por cenário (ano de calibração). A API soma as contagens da área, multiplica pelos fatores de cada cenário e só então calcula a mediana e o P10 e o P90, porque a soma dos P10 das células não é o P10 da soma. Mudar um fator não exige refazer `agregados`.

Pedido à frente A (migration 002): acrescentar `n_focos_origem` e `fusao_com` em `fatores_harmonizacao`, para a salvaguarda do mínimo de focos.

**Anos de calibração:** ver o item 4. A diferença de processamento entre 10 e 13 cenários é desprezível. O que pesa é o risco da deriva do Aqua, e o critério fixado antes de rodar evita escolher os anos depois de ver o resultado.

**NOAA-20 → S-NPP (DECIDIDO, Weberson, 14/11/2026): fator 1.** O NOAA-20 só é usado de novembro de 2026 em diante, ou seja, no mês atual, que o RF11 compara com a mediana. Tratar os dois como iguais faz o mês atual mostrar a mesma contagem que o usuário vê no FIRMS. As razões anuais NOAA-20/S-NPP ficaram entre 0,97 e 1,04, e um fator por mês e dia/noite teria mais ruído que a própria diferença. A razão de 1,12 em 2026 não conta, porque o S-NPP parou no meio do ano. Limite declarado no Método: diferença de até 4% entre os dois VIIRS.

## 5. DECIDIDO (Weberson, 14/11/2026): o classificador (modelo A) como análise complementar

O classificador aprende a chance de o MODIS ver cada fogo do VIIRS, usando FRP, temperatura, confiança, mês, dia/noite, bioma e `modis_scan_mediano`. Ele **não gera o fator da série**. Serve para a tela de Método mostrar quais fogos o MODIS perde por potência (fraco ou forte).

- Roda em volume pequeno (treino 2019 a 2021, teste 2022 a 2024).
- A regra "MODIS estava olhando" (foco do Aqua a até 50 km) vale só aqui, e o viés que ela causa é declarado.
- Se só houver os arquivos de 2024, o corte é **no espaço**: metade das células H3 para treino e metade para teste, com todos os meses dos dois lados.

## 6. Limites a declarar no método

- O fator é por bioma, mês e dia/noite. Não corrige por potência do fogo.
- A faixa de incerteza reflete a variação entre anos de sobreposição e não cobre outras fontes de erro.
- A deriva de órbita do Aqua (depois de 2022) só pode afetar a calibração, e a validação deixando um ano de fora mede isso. O calendário de 2012 em diante usa o VIIRS e não é afetado.
- **Contagem baixa do Aqua no período estimado:** se o Aqua viu zero ou poucos focos numa área pequena num mês fraco, a estimativa também fica zero ou baixa, mesmo que o VIIRS fosse ver fogos pequenos. A faixa não captura isso. PROPOSTA para a frente C: a API marca o mês estimado como "estimativa pouco confiável" quando a contagem bruta do Aqua na área for menor que 10 (limite ESCOLHA DA EQUIPE).
- Calibrado por bioma do IBGE. Não vale automaticamente para regiões fora do Brasil.
- O número do calendário conta **detecções de fogo** (fire detections, convenção do FIRMS), e não incêndios: uma frente de fogo gera várias detecções.
- O NOAA-20 (mês atual) é tratado como igual ao S-NPP. A diferença medida entre os dois é de até 4%.
- O uso de IA neste trabalho é declarado no campo "Use of Super Intelligence" e no README.

## 7. Pendências

1. Acordo da equipe sobre a medida de erro da validação (erro ponderado), antes de rodar.
2. Definir o mínimo de focos por condição com a base limpa. (As colunas `n_focos_origem` e `fusao_com` já estão na migration 002 do PR #2.)
3. Investigar a queda de S-NPP/Aqua em 2025.
4. Esta decisão muda o que o contexto do projeto dizia sobre o modelo A (o classificador deixa de gerar o fator da série). A equipe deve concordar com a mudança.
