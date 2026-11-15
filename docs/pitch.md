# Pitch e vídeo de demonstração

Nov 14, 2026 · **rascunho** para a equipe revisar

## Formato

**Vídeo de 30 segundos:** gravação da tela do site funcionando, com a voz de alguém da equipe e legenda em inglês.

Por que este formato:

- **Mostra o produto real.** Os jurados avaliam Validity e Presentation. Uma gravação do site funcionando prova que ele existe e funciona.
- **A voz da equipe passa autoria.** O guia do Space Apps pede que a ideia seja da equipe. Um vídeo inteiro gerado por IA, com voz sintética, pode parecer o contrário, e o uso de IA precisa ser declarado de qualquer jeito.
- **A fala pode ser em português**, desde que a legenda seja em inglês. Fale na língua em que você soa mais natural.

Regras que tiram o projeto do julgamento se não forem cumpridas (ver [requisitos.md](requisitos.md)):

- [ ] No máximo **30 segundos**
- [ ] Legenda em **inglês**
- [ ] Nome da equipe, nomes dos membros, desafio escolhido, imagem do projeto, experiência do usuário e como os dados da NASA tornaram o projeto possível
- [ ] Nenhuma imagem, vídeo ou voz de menores de 18 anos
- [ ] Hospedado fora do site (YouTube, Drive ou GitHub), com o link testado numa janela anônima

## Roteiro (30 s)

Os nomes dos membros aparecem **escritos na tela**, não falados, para caber no tempo. A fala em inglês tem 63 palavras, perto do limite para 30 s num ritmo claro. A versão em português é um pouco mais longa, então fale sem pausas longas ou corte a última frase.

| Tempo | Tela | Fala (inglês) | Fala (português) |
| --- | --- | --- | --- |
| 0–4 s | Título: **firesync** · nome da equipe · "NASA Space Apps 2026 · MODIS and VIIRS Hot Spots" | "When fires spread, response teams ask one question: is this normal?" | "Quando o fogo se espalha, as equipes de resposta perguntam uma coisa: isso é normal?" |
| 4–10 s | Alguém desenha uma área na Amazônia, no mapa | "firesync answers in seconds. Draw any area in Brazil…" | "O firesync responde em segundos. Desenhe qualquer área do Brasil…" |
| 10–18 s | O calendário aparece, de 2003 a 2026. Passar o mouse num mês estimado mostra a faixa | "…and see 24 years of fire activity: MODIS and VIIRS merged into one consistent series, with the uncertainty shown." | "…e veja 24 anos de fogo: MODIS e VIIRS unidos numa série só, com a incerteza à mostra." |
| 18–25 s | Cartão "Last 7 days: +54% vs. typical" e o alerta | "The last seven days are compared with the same season in past years, so teams know when to act." | "Os últimos sete dias são comparados com a mesma época dos outros anos, para a equipe saber quando agir." |
| 25–30 s | Créditos: nomes dos membros, "Data: NASA FIRMS (MODIS, VIIRS)", link do site | "Built on NASA FIRMS open data." | "Feito com os dados abertos do NASA FIRMS." |

O número do cartão ("+54%") é do JSON de exemplo. Na gravação final, use o que o site mostrar com os dados reais.

## Legenda em inglês (SRT)

Salvar como `pitch.en.srt` e subir junto com o vídeo. Os tempos se ajustam depois da gravação.

```
1
00:00:00,000 --> 00:00:04,000
When fires spread, response teams ask one question: is this normal?

2
00:00:04,000 --> 00:00:10,000
firesync answers in seconds. Draw any area in Brazil...

3
00:00:10,000 --> 00:00:18,000
...and see 24 years of fire activity: MODIS and VIIRS merged
into one consistent series, with the uncertainty shown.

4
00:00:18,000 --> 00:00:25,000
The last seven days are compared with the same season
in past years, so teams know when to act.

5
00:00:25,000 --> 00:00:30,000
Built on NASA FIRMS open data.
```

## Como gravar

1. **Prepare antes:** o site no ar, com dados reais, o navegador em tela cheia, sem abas nem notificações, e uma área já testada.
2. **Grave a tela** em 1920 × 1080 (OBS Studio, ou o gravador do sistema). Grave cada trecho separado, mais longo do que precisa, para cortar depois.
3. **Grave a voz** em um lugar silencioso, com o celular perto da boca. Leia o roteiro em voz alta umas 3 vezes antes.
4. **Monte** num editor simples (CapCut, DaVinci Resolve, Clipchamp): corte, sincronize a voz, adicione o título, os créditos e a legenda.
5. **Confira** se dá 30 s ou menos, depois suba e teste o link numa janela anônima.

O que dá para pedir ao Claude: ajustar o roteiro, gerar a legenda com os tempos da gravação final, e montar o título e os créditos como imagem. A voz e a gravação da tela ficam com a equipe.

## Pitch em uma frase

Para a página do projeto e para falar com os jurados:

> **The FIRMS map shows where fires are now. firesync tells you whether that is normal for this place and this time of year: 24 years of MODIS and VIIRS in one consistent calendar, with the uncertainty shown.**

## Possível impacto (frase de potencial)

Uma frase curta, de até 300 caracteres, em três partes: **o que medimos** (a antecedência do aviso), **o potencial** (a partir de um estudo publicado, não do nosso modelo) e **as emissões**. É a abordagem de **antecedência e potencial em hectares**. A validação com área queimada da NASA ([validacao-area-queimada.md](validacao-area-queimada.md)) é evidência do modelo e **não faz parte desta frase**. Discussão com o Matheus na issue 116.

**Inglês, para o slide e o vídeo (272 caracteres)**
> In the Amazon, our model warned of 51 in every 100 starts of significant fire, usually 10 days ahead. Brigades cut burned area by 12% in the Cerrado. In the Amazon, that could mean about 290,000 hectares and 3.8 million tonnes of CO₂ less. A hypothesis to test in a pilot.

**Português (292 caracteres)**
> Na Amazônia, nosso modelo avisou 51 de cada 100 começos de fogo importante, em geral 10 dias antes. No Cerrado, brigadas reduziram em 12% a área queimada. Na Amazônia, isso pode significar cerca de 290 mil hectares e 3,8 milhões de toneladas de CO₂ a menos. É uma hipótese a testar em piloto.

### Regra de redação (decisão do Weberson, 15/11/2026)

- **Tudo o que não foi provado usa "pode" ou "poderia" ("could").** O que foi medido, ou vem de um estudo publicado, é dito como fato. Que o resultado de brigadas no Cerrado **pode** valer também na Amazônia é uma hipótese, mesmo sendo biomas diferentes, e o texto diz isso.
- **Linguagem simples**, que qualquer pessoa entenda:

| Em vez de | Usar |
| --- | --- |
| mediana de 10 dias | em geral 10 dias antes |
| inícios de fogo relevante | começos de fogo importante (nota: 10 ou mais focos de calor numa área de cerca de 1.770 km², em 14 dias) |
| Mha, Mt de CO₂e | milhões de hectares, milhões de toneladas de CO₂ |
| células | áreas |
| detecções | focos de calor (hot spots, o termo do desafio) |
| evitáveis, evitados | a menos, sempre com "pode" |
| "Referência, não resultado nosso" | "Hipótese a testar em piloto" |

### De onde vem cada número

| Número | Origem | Tipo |
| --- | --- | --- |
| **51 de cada 100** e **em geral 10 dias antes** | Nossa medição: Amazônia, 2021 a 2024, nota de 50% ou mais, um modelo treinado por ano só com dados anteriores. "Em geral" quer dizer que, entre os avisos, metade veio com 10 dias ou mais | **Medido** |
| **12%** | Estudo de brigadas em unidades de conservação do **Cerrado** (Oliveira et al.), via [Aliança da Terra](https://www.aliancadaterra.org/_files/ugd/18a265_69d4f963acd24c3ab3f32f3a4b711f7e.pdf) e [Sano, Embrapa](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1136281/1/Sano-implementation-of-fire-policies-in-Brazil.pdf) | Fato do estudo, no Cerrado |
| **2,4 milhões de hectares** | Área queimada de junho a agosto de 2024, [IPAM](https://ipam.org.br/co2-emissions-from-fires-in-the-amazon-grow-by-60/) | Referência externa |
| **~290 mil hectares** | 12% de 2,4 milhões = 288 mil | Conta |
| **~3,8 milhões de toneladas de CO₂** | 288 mil ha × 13,1 t por ha (IPAM: 31,5 milhões de toneladas ÷ 2,4 milhões de hectares) = 3,77 milhões | Conta |

### O que a frase assume e não prova

1. **O 12% do Cerrado pode valer para a Amazônia.** É uma hipótese. Por isso a frase diz "pode" e "estudo no Cerrado".
2. **A antecedência do modelo pode tornar a brigada mais eficaz.** O estudo mostra o efeito de ter brigadas, e não o de ter aviso antecipado. Só um piloto fecha essa ligação.
3. **2024 foi um ano de seca extrema**, e o número é só de junho a agosto. Em um ano médio, o potencial seria menor.

Resposta curta se um jurado perguntar: "É um cenário de escala com referências publicadas. O que nós medimos é a antecedência. O resto é o que queremos validar em piloto."

### O que pode e o que não pode dizer

| Pode dizer | Não pode dizer |
| --- | --- |
| "Avisou antes 51 de cada 100 começos de fogo importante" | "Prevê incêndios" |
| "Em geral 10 dias antes, quando avisou" | "Evita", "reduz" ou "salva" hectares |
| "Testado ano a ano, só com dados anteriores" | "Prova que protege a floresta" |
| "É uma lista de prioridades para a decisão humana" | "Substitui brigadas" |
| "Isso pode significar X hectares a menos, a validar em piloto" | Números de redução como resultado nosso |
| "Quase metade ainda chega sem aviso" | Esconder os 49% restantes |

Cuidados de palavra: **"importante" não é "incêndio grande"**. Não usar "15 dias" (o horizonte é de 14), nem "clima e vegetação" (o modelo usa só contagens de focos de calor do VIIRS), nem as palavras "validado" e "acurácia" nas telas.

### Outros números medidos que podem entrar (Amazônia, 2021 a 2024)

- Dos avisos (nota de 50% ou mais), **78,5%** tiveram fogo importante em 14 dias; dos locais com fogo importante, **74%** foram avisados.
- Olhando só as **20% áreas de maior nota** por semana, uma brigada captura **66%** do fogo importante (10%: 42%; sorteando, 10%).
- De cada 100 começos de fogo importante, **51** foram avisados, **42** com 3 dias ou mais de antecedência e **33** com 7 dias ou mais.
- **Limite honesto:** com o corte de 50%, 49% dos começos de fogo chegam sem aviso. Em áreas que estavam quietas (zero focos de calor em 30 dias), 34% foram avisados, em geral 4 dias antes.
- O "68%" que circulou antes **media outra coisa** (só os avisos que deram certo) e foi substituído pelo 42%.

Os números vêm de scripts de referência em `data-pipeline/validacao/experimentos/` (PR 105) e podem mudar quando o Eduardo repetir a medição para 2025 e 2026. Detalhes no [RFC 0003](rfcs/0003-modelo-risco.md).

## Pendências

- [ ] Nome da equipe
- [ ] Nomes dos membros como vão aparecer nos créditos
- [ ] Quem grava a voz e quem monta o vídeo
- [ ] Link final do site
- [ ] O Matheus valida as duas frases de potencial (seção "Possível impacto", issue 116)
