# Decisões da harmonização

Responsável pelas decisões: Weberson. Itens marcados como **ESCOLHA DA EQUIPE** são decisões nossas, não fatos. Itens marcados como **PROPOSTA** esperam confirmação da equipe.

Este documento incorpora a revisão feita no PR 1 (comentário de nogran). Onde a revisão corrigiu um erro da primeira versão, isso está indicado.

## 1. Decidido

| Tema | Decisão | Origem |
| --- | --- | --- |
| Escala da série final | **Escala VIIRS.** Os anos só-MODIS são convertidos para a escala do VIIRS. ESCOLHA DA EQUIPE | Weberson, 14/11/2026 |
| Cuidado com as escalas | Ver seção 2 | Weberson, 14/11/2026 |
| Satélite do MODIS | Só o Aqua. Terra fora do cálculo, calendário a partir de 2003 | Time de dados (`pipeline-dados.md`) |
| Grade | H3. A resolução é decidida com a frente C (sugestão do time de dados: 6) | `importacao-regioes.md` |
| FRP | Fica no projeto, mas **fora das condições do fator** (seção 3) | Revisão do PR 1 |
| Áreas críticas | Diferencial do app: contagem de focos mais energia (`frp_soma`) por célula, no período do VIIRS | Weberson, 14/11/2026 |

## 2. Cuidados para não misturar as escalas

1. Todo número carrega a escala e a origem: **observado pelo VIIRS** ou **estimado a partir do MODIS, com faixa**. Nunca aparece um número sem rótulo. A API deduz a origem: mês com focos do VIIRS na área é observado, mês só com Aqua é estimado.
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

1. Contar, por célula H3 e mês, os focos do Aqua e os do S-NPP, nos anos de sobreposição (2012 a 2024, 13 anos).
2. Somar por bioma, mês e dia/noite e calcular o fator Aqua para S-NPP (quantos focos do VIIRS cada foco do Aqua representa).
3. Cada ano da sobreposição gera um fator, e cada fator é um **cenário**. A faixa de incerteza é o percentil 10 e o percentil 90 entre os 13 cenários.
4. Validação por ano deixado de fora: o fator vem dos outros 12 anos, é aplicado ao Aqua do ano deixado de fora e comparado ao S-NPP real. Reportar o erro e quantas vezes o real cai dentro da faixa de 80%.
5. 2025 fica fora do cálculo. A razão S-NPP/Aqua caiu para 4,8 (contra cerca de 6), possivelmente pela deriva de órbita do Aqua, e isso precisa ser investigado antes de congelar o fator.

**Salvaguardas obrigatórias (aceitas junto com a decisão):**

- **Suposição declarada no Método:** o fator supõe que a razão entre os sensores em 2003 a 2011 é parecida com a de 2012 a 2024. Isso não pode ser testado, porque não há VIIRS antes de 2012. A queda de 2025 mostra que a razão pode mudar. A faixa mede só a variação entre anos, e não esse risco.
- **Mínimo de focos por condição:** cada combinação de bioma, mês e dia/noite precisa de um mínimo de focos do Aqua para ter fator próprio. Abaixo disso, junta com a condição vizinha e registra a fusão em `fatores_harmonizacao`. O valor do mínimo é definido com a base limpa. ESCOLHA DA EQUIPE.

Por que contagens por célula e não o classificador ponto a ponto: é mais barato, usa 13 pontos para a faixa em vez de 4, e dispensa a regra "MODIS estava olhando", que gerava viés (descartava justamente as áreas onde o VIIRS viu fogo e o MODIS nada).

**Contrato para a API (DECIDIDO, Weberson, 14/11/2026):** adotamos o formato da frente A (`docs/banco.md`, PR #2). `agregados` guarda a contagem **bruta** por célula × ano × mês × satélite × dia/noite, e `fatores_harmonizacao` guarda um fator por cenário (ano de calibração). A API soma as contagens da área, multiplica pelos fatores de cada cenário e só então calcula a mediana e o P10 e o P90, porque a soma dos P10 das células não é o P10 da soma. Mudar um fator não exige refazer `agregados`.

Pedido à frente A (migration 002): acrescentar `n_focos_origem` e `fusao_com` em `fatores_harmonizacao`, para a salvaguarda do mínimo de focos.

**Em aberto com a frente A: anos de calibração.** Nós decidimos 2012 a 2024 (13 cenários, 2025 fora). A frente A propõe 2012 a 2021 (10 cenários), antes de o Aqua sair da órbita original em 2022. As razões de 2022, 2023 e 2024 (5,9, 6,1 e 6,2) parecem normais, e só 2025 cai (4,8). Sugestão: a validação deixando um ano de fora mostra se os anos depois de 2022 erram mais, e a escolha final sai desse resultado.

## 5. DECIDIDO (Weberson, 14/11/2026): o classificador (modelo A) como análise complementar

O classificador aprende a chance de o MODIS ver cada fogo do VIIRS, usando FRP, temperatura, confiança, mês, dia/noite, bioma e `modis_scan_mediano`. Ele **não gera o fator da série**. Serve para a tela de Método mostrar quais fogos o MODIS perde por potência (fraco ou forte).

- Roda em volume pequeno (treino 2019 a 2022, teste 2023 e 2024, confirmado pelo Weberson como recorte para esta análise).
- A regra "MODIS estava olhando" (foco do Aqua a até 50 km) vale só aqui, e o viés que ela causa é declarado.
- Se só houver os arquivos de 2024, o corte é **no espaço**: metade das células H3 para treino e metade para teste, com todos os meses dos dois lados.

## 6. Limites a declarar no método

- O fator é por bioma, mês e dia/noite. Não corrige por potência do fogo.
- A faixa de incerteza reflete a variação entre anos de sobreposição e não cobre outras fontes de erro.
- A deriva de órbita do Aqua pode afetar os anos recentes.
- Treinado com Amazônia e Pantanal. Não vale automaticamente para outros biomas.
- O uso de IA neste trabalho é declarado no campo "Use of Super Intelligence" e no README.

## 7. Pendências

1. Decidir com a frente A os anos de calibração (2012 a 2024 ou 2012 a 2021) e pedir a migration 002.
2. Definir o mínimo de focos por condição com a base limpa.
3. Investigar a queda de S-NPP/Aqua em 2025.
4. Esta decisão muda o que o contexto do projeto dizia sobre o modelo A (o classificador deixa de gerar o fator da série). A equipe deve concordar com a mudança.
