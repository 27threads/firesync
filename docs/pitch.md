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

Uma frase curta, de até 300 caracteres, com três partes: **o que medimos**, **o potencial (de estudo, não do nosso modelo)** e **as emissões**. Escolher uma das três. Origem dos números e limites logo abaixo (issue 116).

**Inglês, para o slide e o vídeo (259 caracteres)**
> Our model flagged 51% of significant fire starts in the Amazon, a median 10 days ahead. If that helped brigades cut burned area 12% (Cerrado study), on 2024's 2.4 Mha the potential is ~290k ha and ~3.8 Mt CO₂e avoided. Reference, not our result: pilot needed.

**Português (277 caracteres)**
> Nosso modelo avisou, com mediana de 10 dias de antecedência, 51% dos inícios de fogo relevante na Amazônia. Se isso levasse a brigadas 12% mais eficazes (estudo no Cerrado), o potencial seria ~290 mil ha e ~3,8 Mt de CO₂e evitáveis (base: 2,4 Mha de 2024). A validar em piloto.

**Mais curta, em português (229 caracteres)**
> Medimos até 10 dias de antecedência para preparar o combate. Brigadas reduzem ~12% da área queimada (estudo no Cerrado): na Amazônia de 2024, ~290 mil ha e ~3,8 Mt de CO₂e com potencial de evitar. Referência, a validar em piloto.

### De onde vem cada número

| Número | Origem | Tipo |
| --- | --- | --- |
| **51%** e **10 dias** | Nossa medição: Amazônia, 2021 a 2024, nota de 50% ou mais, um modelo treinado por ano só com dados anteriores | **Medido** |
| **12%** | Estudo de brigadas em unidades de conservação do **Cerrado** (Oliveira et al.), via [Aliança da Terra](https://www.aliancadaterra.org/_files/ugd/18a265_69d4f963acd24c3ab3f32f3a4b711f7e.pdf) e [Sano, Embrapa](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1136281/1/Sano-implementation-of-fire-policies-in-Brazil.pdf) | Referência externa |
| **2,4 Mha** | Área queimada de junho a agosto de 2024, [IPAM](https://ipam.org.br/co2-emissions-from-fires-in-the-amazon-grow-by-60/) | Referência externa |
| **~290 mil ha** | 12% de 2,4 Mha = 288 mil ha | Conta |
| **~3,8 Mt de CO₂e** | 288 mil ha × 13,1 t por ha (IPAM: 31,5 Mt ÷ 2,4 Mha) = 3,77 Mt | Conta |

### O que a frase assume e não prova

1. **O 12% do Cerrado vale para a Amazônia.** Não vale automaticamente. Por isso a frase diz "se" e "estudo no Cerrado".
2. **A antecedência do modelo é o que torna a brigada mais eficaz.** O estudo mostra o efeito de ter brigadas, e não o de ter aviso antecipado. Só um piloto fecha essa ligação.
3. **2024 foi um ano de seca extrema**, e o número é só de junho a agosto. Em um ano médio, o potencial seria menor.

Resposta curta se um jurado perguntar: "É um cenário de escala com referências publicadas. O que nós medimos é a antecedência. O resto é o que queremos validar em piloto."

### O que pode e o que não pode dizer

| Pode dizer | Não pode dizer |
| --- | --- |
| "Avisou antes 51 de cada 100 inícios de atividade de fogo significativa" | "Prevê incêndios" |
| "Mediana de 10 dias de antecedência quando avisou" | "Evita", "reduz" ou "salva" hectares |
| "Testado ano a ano, só com dados anteriores" | "Prova que protege a floresta" |
| "É uma lista de prioridades para a decisão humana" | "Substitui brigadas" |
| "Com potencial de reduzir área e emissões, a validar em piloto" | Números de redução como resultado nosso |
| "Quase metade ainda chega sem aviso" | Esconder os 49% restantes |

Cuidados de palavra: **"relevante" não é "incêndio grande"**: é a célula (~1.770 km²) chegar a 10 ou mais detecções de satélite em 14 dias. A tela chama as detecções de **"hot spots"** (o termo do desafio). Não usar "15 dias" (o horizonte é de 14), nem "clima e vegetação" (o modelo usa só contagens de focos do VIIRS), nem as palavras "validado" e "acurácia" nas telas.

### Outros números medidos que podem entrar (Amazônia, 2021 a 2024)

- Dos avisos (nota de 50% ou mais), **78,5%** tiveram fogo relevante em 14 dias; dos locais com fogo relevante, **74%** foram avisados.
- Olhando só as **20% células de maior nota** por semana, uma brigada captura **66%** do fogo relevante (10%: 42%; sorteando, 10%).
- De cada 100 inícios de fogo relevante, **51** foram avisados, **42** com 3 dias ou mais de antecedência e **33** com 7 dias ou mais.
- **Limite honesto:** com o corte de 50%, 49% dos inícios de fogo chegam sem aviso. Em células quietas (zero detecções em 30 dias), 34% foram avisados, com mediana de 4 dias.
- O "68%" que circulou antes **media outra coisa** (só os avisos que deram certo) e foi substituído pelo 42%.

Os números vêm de scripts de referência em `data-pipeline/validacao/experimentos/` (PR 105) e podem mudar quando o Eduardo repetir a medição para 2025 e 2026. Detalhes no [RFC 0003](rfcs/0003-modelo-risco.md).

## Pendências

- [ ] Nome da equipe
- [ ] Nomes dos membros como vão aparecer nos créditos
- [ ] Quem grava a voz e quem monta o vídeo
- [ ] Link final do site
- [ ] Escolher uma das três frases de potencial (seção "Possível impacto")
