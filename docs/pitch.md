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

Os nomes dos membros aparecem **escritos na tela**, não falados, para caber no tempo. A fala em inglês tem 60 palavras, perto do limite para 30 s num ritmo claro. A versão em português é um pouco mais longa, então fale sem pausas longas ou corte a última frase.

| Tempo | Tela | Fala (inglês) | Fala (português) |
| --- | --- | --- | --- |
| 0–4 s | Título: **firesync** · nome da equipe · "NASA Space Apps 2026 · MODIS and VIIRS Hot Spots" | "When fires spread, response teams ask: is this normal, and where next?" | "Quando o fogo se espalha, as equipes perguntam: isso é normal, e onde vai ser o próximo?" |
| 4–10 s | Alguém desenha uma área na Amazônia, no mapa | "firesync answers in seconds. Draw any area in Brazil…" | "O firesync responde em segundos. Desenhe qualquer área do Brasil…" |
| 10–18 s | O calendário aparece, de 2003 a 2026. Passar o mouse num mês estimado mostra a faixa | "…and see 24 years of MODIS and VIIRS merged into one consistent calendar, uncertainty shown." | "…e veja 24 anos de MODIS e VIIRS unidos num calendário só, com a incerteza à mostra." |
| 18–25 s | Mapa de risco dos próximos 14 dias, com as células "very high" em destaque. Rodapé na tela: "Amazon, 2021–2024 · top 5% of cells each week · NASA MCD64A1 burned area" | "Its 14-day risk map, tested on NASA burned-area data, put 40% of what burned in just 5% of cells." | "O mapa de risco de 14 dias, testado com a área queimada da NASA, achou 40% do que queimou em só 5% das células." |
| 25–30 s | Créditos: nomes dos membros, "Data: NASA FIRMS (MODIS, VIIRS), NASA MCD64A1", link do site | "Built on NASA open data." | "Feito com dados abertos da NASA." |

Os números do mapa de risco (40% da área queimada em 5% das células, 8 vezes mais que ao acaso) foram medidos na Amazônia, de 2021 a 2024, contra a área queimada MCD64A1 ([validacao-area-queimada.md](validacao-area-queimada.md)). Não falar em redução de queimadas: isso não foi medido. O cartão "últimos 7 dias contra o normal" e o alerta saíram do roteiro para caber em 30 s; continuam no site.

## Legenda em inglês (SRT)

Salvar como `pitch.en.srt` e subir junto com o vídeo. Os tempos se ajustam depois da gravação.

```
1
00:00:00,000 --> 00:00:04,000
When fires spread, response teams ask:
is this normal, and where next?

2
00:00:04,000 --> 00:00:10,000
firesync answers in seconds. Draw any area in Brazil...

3
00:00:10,000 --> 00:00:18,000
...and see 24 years of MODIS and VIIRS merged
into one consistent calendar, uncertainty shown.

4
00:00:18,000 --> 00:00:25,000
Its 14-day risk map, tested on NASA burned-area data,
put 40% of what burned in just 5% of cells.

5
00:00:25,000 --> 00:00:30,000
Built on NASA open data.
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

## Pendências

- [ ] Nome da equipe
- [ ] Nomes dos membros como vão aparecer nos créditos
- [ ] Quem grava a voz e quem monta o vídeo
- [ ] Link final do site
