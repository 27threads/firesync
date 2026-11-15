# Pitch e vídeo de demonstração

Nov 15, 2026 · versão final validada pela equipe (issues #116 e #135)

## Formato

**Vídeo de 30 segundos:** gravação da tela do site funcionando (<https://firesync.nogranlabs.com.br>), com a voz de alguém da equipe e legenda em inglês.

Por que este formato:

- **Mostra o produto real.** Os jurados avaliam Validity e Presentation. Uma gravação do site funcionando prova que ele existe e funciona.
- **A voz da equipe passa autoria.** O guia do Space Apps pede que a ideia seja da equipe. Um vídeo inteiro gerado por IA, com voz sintética, pode parecer o contrário, e o uso de IA precisa ser declarado de qualquer jeito.
- **A fala pode ser em português**, desde que a legenda e todos os textos escritos na tela estejam em **inglês** ([Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/#tips-for-creating-a-project-demo)).

Regras que tiram o projeto do julgamento se não forem cumpridas (ver [requisitos.md](requisitos.md)):

- [ ] No máximo **30 segundos**
- [ ] Legenda e textos de tela em **inglês**
- [ ] Nome da equipe, nomes dos membros, desafio escolhido, imagem do projeto, experiência do usuário e como os dados da NASA tornaram o projeto possível
- [ ] Nenhuma imagem, vídeo ou voz de menores de 18 anos
- [ ] Hospedado fora do site (YouTube, Drive ou GitHub), com o link testado numa janela anônima

## Roteiro final (30 s) — A jornada do comandante no app

O vídeo segue o arco **Problema → Decisão → Entrega (harmonização MODIS e VIIRS) → Prova → Impacto Global**, com o comandante usando o sistema na prática. Os nomes dos membros aparecem **escritos na tela**, não falados, para caber no tempo.

| Ato e tempo | O que mostrar na tela (textos na tela em inglês) | Fala (português) | Legenda (inglês) |
| --- | --- | --- | --- |
| **1. Problema**<br>`0–4 s` | Globo da abertura descendo para o mapa da Amazônia com focos de calor reais.<br>**Topo:** `firesync · Team [Name] · [Members] · NASA Space Apps 2026 · MODIS and VIIRS Hot Spots` | "O fogo avança na Amazônia. Com poucas brigadas, o comandante precisa decidir: onde agir primeiro?" | "Fire is spreading across the Amazon. With few brigades, the commander must decide: where to act first?" |
| **2. Decisão**<br>`4–9 s` | No explorador (`Fire now`), o comandante clica na área crítica em `"Where to look first"` e aparece o veredito `"▲ More fire than usual"`. | "No firesync, um clique mostra onde o fogo de hoje já foge do normal." | "In firesync, one click shows where today's fire is already above normal." |
| **3. Entrega**<br>`9–18 s` | • **9–14 s:** Abre o **calendário de 24 anos** (`2003–2026`), passando o mouse num mês estimado (hachurado) para mostrar a faixa de incerteza.<br>• **14–18 s:** Muda para o **risco dos próximos 14 dias**, destacando as áreas `"Very high"` e `"High"`. | "Isso só é possível porque harmonizamos 24 anos dos satélites MODIS e VIIRS da NASA numa série única — que alimenta o calendário histórico e o risco para 14 dias." | "That's possible because we harmonized 24 years of NASA's MODIS and VIIRS sensors into one series—powering the historical calendar and 14-day risk map." |
| **4. Prova**<br>`18–23 s` | Mapa de risco da Amazônia em destaque.<br>**Selo na tela:** `Tested on Amazon 2021–2024 (trained only on past years)` | "Nos testes, esse mapa avisou, em geral 10 dias antes, metade dos começos de fogo importante da Amazônia — dando tempo de agir antes que o fogo espalhe." | "In tests, this map warned usually 10 days ahead on half of the Amazon's significant fire outbreaks—giving time to act before fire spreads." |
| **5. Impacto Global**<br>`23–30 s` | Mapa de risco ao fundo, escurecido.<br>**Centro (grande):** `Could mean ~290,000 ha & 3.8M t CO₂ less`<br>**Abaixo (menor):** `in a year like 2024 (June–August) · hypothesis to test in a pilot · built to scale worldwide`<br>**Rodapé:** `Team [Name]: [Members] · Data: NASA FIRMS (MODIS C6.1, VIIRS C2), NASA GIBS, INPE/AEB · firesync.nogranlabs.com.br` | "Com brigadas em campo, isso pode significar 290 mil hectares a menos queimados — começando na Amazônia para proteger florestas no mundo inteiro." | "With brigades on the ground, that could mean 290,000 fewer hectares burned—starting in the Amazon to help protect forests worldwide." |

### Fala corrida para gravar

> **[0–4 s · Problema]** "O fogo avança na Amazônia. Com poucas brigadas, o comandante precisa decidir: onde agir primeiro?"
>
> **[4–9 s · Decisão]** "No firesync, um clique mostra onde o fogo de hoje já foge do normal."
>
> **[9–18 s · Entrega]** "Isso só é possível porque harmonizamos 24 anos dos satélites MODIS e VIIRS da NASA numa série única — que alimenta o calendário histórico e o risco para 14 dias."
>
> **[18–23 s · Prova]** "Nos testes, esse mapa avisou, em geral 10 dias antes, metade dos começos de fogo importante da Amazônia — dando tempo de agir antes que o fogo espalhe."
>
> **[23–30 s · Impacto Global]** "Com brigadas em campo, isso pode significar 290 mil hectares a menos queimados — começando na Amazônia para proteger florestas no mundo inteiro."

### Racional de UX e gravação no frontend (complementaridade áudio × vídeo)

A voz nunca lê o que está escrito nos botões: ela narra a decisão do comandante enquanto o cursor mostra a resposta acontecendo na tela:

- **`0–4 s` (Problema):** A descida do globo 3D (`OrbitalOpening`, camada `BlueMarble` do NASA GIBS com os modelos do Aqua e do Suomi NPP) até o mapa prende a atenção visual enquanto o cabeçalho já entrega o nome da equipe, os integrantes e o desafio sem gastar tempo de locução.
- **`4–9 s` (Decisão):** O clique em `"Where to look first"` (`EarlyWarning.tsx`) centraliza o mapa na célula crítica e exibe o veredito simples `"▲ More fire than usual"` (`Verdict.tsx`), provando que a interface responde em segundos para quem está sob pressão (RD07).
- **`9–18 s` (Entrega):** Mostra a conexão direta entre o núcleo do desafio (o calendário harmonizado `CalendarSvg.tsx` em paleta `cividis` com hachura e faixa P5–P95 nos meses do MODIS) e a preparação para as próximas duas semanas (as faixas de risco de 14 dias).
- **`18–23 s` (Prova):** Coloca a antecedência (`10 dias antes`) na frente, explicando por que o aviso antecipado permite à brigada agir antes que o fogo se espalhe.
- **`23–30 s` (Impacto Global):** O mapa de risco permanece ao fundo (escurecido para leitura) enquanto os números de potencial (`~290,000 ha & 3.8M t CO₂ less`) ficam grandes no centro da tela e o rodapé fecha os créditos dos dados abertos da NASA (`FIRMS`, `GIBS`) e da agência parceira (`INPE/AEB`).

## Legenda em inglês (SRT)

Salvar como `pitch.en.srt` e subir junto com o vídeo. Os tempos se ajustam depois da gravação.

```srt
1
00:00:00,000 --> 00:00:04,000
Fire is spreading across the Amazon. With few brigades,
the commander must decide: where to act first?

2
00:00:04,000 --> 00:00:09,000
In firesync, one click shows where today's fire
is already above normal.

3
00:00:09,000 --> 00:00:18,000
That's possible because we harmonized 24 years of NASA's MODIS and VIIRS
sensors into one series—powering the historical calendar and 14-day risk map.

4
00:00:18,000 --> 00:00:23,000
In tests, this map warned usually 10 days ahead on half of the Amazon's
significant fire outbreaks—giving time to act before fire spreads.

5
00:00:23,000 --> 00:00:30,000
With brigades on the ground, that could mean 290,000 fewer hectares burned—
starting in the Amazon to help protect forests worldwide.
```

## Como gravar

1. **Prepare antes:** o site no ar (<https://firesync.nogranlabs.com.br>), com dados reais, o navegador em tela cheia, sem abas nem notificações, e uma área da Amazônia já testada.
2. **Grave a tela** em 1920 × 1080 (OBS Studio, ou o gravador do sistema). Grave cada trecho separado, mais longo do que precisa, para cortar depois.
3. **Grave a voz** em um lugar silencioso, com o celular perto da boca. Leia o roteiro em voz alta umas 3 vezes antes.
4. **Monte** num editor simples (CapCut, DaVinci Resolve, Clipchamp): corte, sincronize a voz, adicione o título, os destaques em inglês, os créditos e a legenda.
5. **Confira** se dá 30 s ou menos, depois suba e teste o link numa janela anônima.

## Pitch em uma frase

Para a página do projeto e para falar com os jurados:

> **The FIRMS map shows where fires burn now. firesync helps commanders decide where to act first today and where to position brigades for the next 14 days: 24 years of MODIS and VIIRS in one consistent calendar (with uncertainty shown) plus an early-warning risk map tested on past Amazon fire seasons.**

## Possível impacto (frase de potencial)

Uma frase curta, em três partes: **o que medimos** (a antecedência do aviso), **o potencial** (a partir de um estudo publicado, não do nosso modelo) e **as emissões**. É a abordagem de **antecedência e potencial em hectares** (discussão com o Mateus nas issues #116 e #135).

**Inglês, para o slide e a página do projeto (301 caracteres)**
> In the Amazon, our model warned of 51 in every 100 significant fire outbreaks, usually 10 days ahead. Brigades cut burned area by 12% in the Cerrado. In a year like 2024 (June–August), that could mean about 290,000 hectares and 3.8 million tonnes of CO₂ less in the Amazon. A hypothesis to test in a pilot.

**Português (318 caracteres)**
> Na Amazônia, nosso modelo avisou 51 de cada 100 começos de fogo importante, em geral 10 dias antes. No Cerrado, brigadas reduziram em 12% a área queimada. Em um ano como 2024 (junho a agosto), isso pode significar cerca de 290 mil hectares e 3,8 milhões de toneladas de CO₂ a menos na Amazônia. É uma hipótese a testar em piloto.

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
| **51 de cada 100** e **em geral 10 dias antes** | Nossa medição: Amazônia, 2021 a 2024, nota de 50% ou mais, um modelo treinado por ano só com dados anteriores ([RFC 0003](rfcs/0003-modelo-risco.md)). "Em geral" quer dizer que, entre os avisos, metade veio com 10 dias ou mais | **Medido** |
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

Cuidados de palavra: **"importante" não é "incêndio grande"**. Não usar "15 dias" (o horizonte é de 14) nem "clima e vegetação" (o modelo usa só contagens de focos de calor do VIIRS). Sobre as palavras proibidas nas telas, ver as regras do [RFC 0003](rfcs/0003-modelo-risco.md).

### Outros números medidos que podem entrar (Amazônia, 2021 a 2024)

- Dos avisos (nota de 50% ou mais), **78,5%** tiveram fogo importante em 14 dias; dos locais com fogo importante, **74%** foram avisados.
- Olhando só as **20% áreas de maior nota** por semana, uma brigada captura **66%** do fogo importante medido por focos VIIRS (10%: 42%; sorteando, 10%).
- De cada 100 começos de fogo importante, **51** foram avisados, **42** com 3 dias ou mais de antecedência e **33** com 7 dias ou mais.
- **Limite honesto:** com o corte de 50%, 49% dos começos de fogo chegam sem aviso. Em áreas que estavam quietas (zero focos de calor em 30 dias), 34% foram avisados, em geral 4 dias antes.
- O "68%" que circulou antes **media outra coisa** (só os avisos que deram certo) e foi substituído pelo 42%.

Os números vêm de scripts de referência em `data-pipeline/validacao/experimentos/` (PR 105) e podem mudar quando o Eduardo repetir a medição para 2025 e 2026. Detalhes no [RFC 0003](rfcs/0003-modelo-risco.md).

## Pendências

- [ ] Nome da equipe
- [ ] Nomes dos membros como vão aparecer nos créditos
- [ ] Quem grava a voz e quem monta o vídeo
