# Critérios de julgamento e prêmios

Nov 14, 2026 · fonte: [Judging & Awards Guide 2026](https://www.spaceappschallenge.org/resources/judging-awards-guide/) (versão de 13/11/2026)

**Objetivo da equipe: ganhar um prêmio global.** Toda decisão de produto, código, documentação e apresentação deve aumentar a nota nos 5 critérios abaixo. Na dúvida entre duas opções, escolha a que vale mais nota.

## Critérios primeiro, categorias depois

**As categorias só são decididas na fase 3, e só entre os finalistas.** Para chegar lá, o projeto precisa passar pelas fases 1 e 2, e nelas conta **apenas a nota de 1 a 5 em cada um dos 5 critérios**. Um projeto pensado para uma categoria que tira nota baixa em Presentation não chega à fase em que as categorias são escolhidas.

Por isso:

1. **A ordem do trabalho segue os critérios.** Cada tarefa precisa subir a nota em pelo menos um dos 5 (Impact, Creativity, Validity, Relevance, Presentation). Nenhum critério pode ficar fraco.
2. **As categorias-alvo servem para contar a história** na página do projeto e no vídeo, para os executivos da fase 3 enxergarem o projeto nelas. Elas não definem o que fazer primeiro.
3. **As três categorias-alvo combinam com critérios fortes nossos:** Best Use of Data com Relevance, Best Use of Science com Validity, Local Impact com Impact.

A ordem de prioridade da frente A, por critério, está na issue #19.

## Como funciona o julgamento

| Fase | Quem julga | Resultado | Data |
| --- | --- | --- | --- |
| 1. Evento local | Jurados do evento local | Global Nominees | 03/12/2026 |
| 2. Global | Jurados especialistas | Global Finalists e Honorable Mentions | 17/12/2026 |
| 3. Executivo | Executivos da NASA e das agências parceiras | Global Winners, um por categoria | 26/01/2027 |

Em **todas as fases**, o projeto recebe nota de 1 a 5 em cada um dos 5 critérios. Para passar da fase 1, o projeto precisa de nota alta nos critérios. Na fase 3, os finalistas são indicados para uma das 10 categorias.

## Eliminatórios: sem isso, o projeto nem é julgado

- [ ] Responder a um desafio oficial (o nosso: MODIS and VIIRS Hot Spots)
- [ ] Todos os membros inscritos no **mesmo evento local**, aparecendo na aba Members do time. Máximo de 6 pessoas. Depois do envio, não dá para adicionar ninguém
- [ ] Todos os campos obrigatórios da página do projeto preenchidos
- [ ] Demo: **vídeo de até 30 s** ou **até 7 slides** (contando título e introdução)
- [ ] Tudo em **inglês**. No vídeo, a fala pode ser em português, mas com **legenda em inglês**
- [ ] Enviado até **domingo, 15/11, 23h59 no horário do evento local** (botão "submit" na aba Project)
- [ ] As duas caixas marcadas: termos e condições, e trabalho original com **todas as fontes externas listadas em References** (código, texto, imagens, bibliotecas, mesmo as abertas)
- [ ] Nenhum material com direito autoral sem permissão (música, imagem, texto)

## Os 5 critérios (nota de 1 a 5 em cada)

| Critério | O que vale 5 | Como o firesync pontua |
| --- | --- | --- |
| **Impact** | Resolve um problema importante, com alcance grande | Equipes de alerta e resposta a incêndios sabem se o fogo de agora é normal para o lugar e a época. Amazônia e Pantanal, com desenho pronto para o mundo |
| **Creativity** | Abordagem original, que melhora de forma relevante o que já existe | Série única MODIS + VIIRS com **faixa de incerteza** à mostra, "normal da época" com janela de ±15 dias, alerta com regra versionada e **pacote de auditoria** |
| **Validity** | Base científica, tecnicamente viável, pronto para o mundo real, **fácil de usar** | Calibração validada ano a ano, comparação com o INPE, teste retroativo do alerta com ganho sobre uma regra ingênua ([validacao-alerta.md](validacao-alerta.md)), cobertura da faixa medida (não prometida), interface simples para quem está sob pressão |
| **Relevance** | Responde diretamente ao desafio, com os **dados da NASA no centro** da solução, não como enfeite | O produto inteiro é feito do NASA FIRMS (MODIS C6.1 e VIIRS C2). Possível reforço: área queimada MCD64A1 na validação |
| **Presentation** | História clara e envolvente, apresentação organizada. **Vale tanto quanto os outros** | Vídeo de 30 s com o site funcionando ([pitch.md](pitch.md)) e página do projeto bem escrita. O guia pede atenção igual a este critério |

O guia avisa que muitas equipes capricham nos quatro primeiros e descuidam da apresentação. Não podemos ser uma delas.

## As 10 categorias e as nossas chances

| Categoria | O que premia | Chance | Por quê |
| --- | --- | --- | --- |
| **Best Use of Data** | Tornar dados espaciais acessíveis ou usá-los de forma única | **Alta, alvo 1** | Pegamos 25 anos de dois sensores incompatíveis e entregamos um calendário que qualquer pessoa lê em segundos |
| **Best Use of Science** | Uso melhor e mais válido do método científico | **Alta, alvo 2** | Hipótese (a razão entre os sensores), calibração, validação deixando um ano de fora, critério de corte fixado antes de rodar, incerteza medida, comparação com o INPE |
| **Local Impact Award** | Maior potencial de mudar a comunidade local | **Alta, alvo 3** | Amazônia e Pantanal são problema real e atual no Brasil, com público definido (brigadas, defesa civil, gestores) |
| **Galactic Impact** | Maior potencial de melhorar a vida na Terra | Média | Fogo é problema global, e o desenho escala ([escala-mundial.md](escala-mundial.md)), mas a cobertura atual é o Brasil |
| **Best Storytelling** | Comunicar com criatividade o potencial dos dados abertos | Média | Depende do vídeo. A frase "o FIRMS mostra onde o fogo está, o firesync diz se isso é normal" ajuda |
| **Best Use of Technology** | Uso mais inovador de tecnologia | Média-baixa | Usamos tecnologia sólida (H3, PostGIS, pré-agregação), não nova |
| **Most Inspirational** | O projeto que toca o coração | Baixa | Possível se a história mostrar pessoas reais afetadas pelo fogo |
| **Global Connection** | Conectar pessoas pelo mundo | Baixa | O foco é o Brasil |
| **Art & Technology** | Juntar técnica e criatividade artística | Baixa | Não é o nosso foco |
| **Best Mission Concept** | Conceito e design de missão mais plausíveis | Baixa | Não propomos missão espacial |

## O que fazer, por categoria-alvo

### Best Use of Data

- [ ] O calendário funcionando de ponta a ponta com dados reais, para qualquer área do Brasil
- [ ] A página do projeto explica a dificuldade: dois sensores, resoluções diferentes, 6× mais detecções no VIIRS, e como isso vira uma série só
- [ ] Os dados da NASA citados com nome e versão (FIRMS, MODIS C6.1, VIIRS C2) na tela, na página e no campo "NASA Data"
- [ ] O pacote de auditoria funcionando: qualquer um refaz os números
- [ ] Se der tempo: um segundo dado da NASA (área queimada MCD64A1, issue #9)

### Best Use of Science

- [ ] Uma tela de Método curta, com a hipótese, a calibração, a validação e os limites
- [ ] O gráfico de validação contra o INPE (forma da curva, anos altos, meses de pico)
- [ ] A cobertura **medida** da faixa de incerteza, por bioma (pedida no PR #4)
- [ ] Os limites declarados com honestidade: deriva do Aqua, suposição de que a razão de 2003–2011 é parecida com a de 2012–2024, saturação do VIIRS
- [ ] Se der tempo: o teste do alerta contra área queimada (issue #9)

### Local Impact Award

- [ ] A demo mostra uma área real da Amazônia ou do Pantanal, de preferência um caso conhecido (como 2020 no Pantanal ou 2024 na Amazônia)
- [ ] A janela "últimos 7 dias contra o normal" e o alerta, em linguagem de quem decide
- [ ] Citar o INPE (agência espacial parceira) nas referências

### Presentation (vale para todas)

- [ ] Vídeo de 30 s com legenda em inglês ([pitch.md](pitch.md)), testado numa janela anônima
- [ ] Página do projeto: summary, descrição detalhada, NASA Data, referências e uso de IA, tudo em inglês
- [ ] Site público, sem login, rápido, funcionando no celular

## Regras que valem para toda a equipe e todos os agentes

1. **Priorize o que pontua.** Antes de começar uma tarefa, pergunte qual critério ou categoria ela melhora. Se não melhora nenhum, ela fica para depois da submissão.
2. **Funcionando vale mais que completo.** Validity premia o que está pronto para o mundo real. Um calendário que funciona vale mais que cinco telas pela metade.
3. **Os dados da NASA ficam visíveis.** Crédito ao FIRMS na tela, nomes e versões dos produtos na página e no método.
4. **Honestidade científica.** Prometa só o que foi medido. Os jurados são especialistas e percebem quando o número é inventado.
5. **Tudo o que o jurado vê fica em inglês:** site, página, vídeo (legenda) e repositório público.
6. **Toda fonte externa vai para References**, incluindo bibliotecas e imagens. Esquecer pode desclassificar.
7. **Uso de IA declarado** no campo "Use of Super Intelligence" e na tabela do README. A ideia de como resolver o desafio tem que ser da equipe.
