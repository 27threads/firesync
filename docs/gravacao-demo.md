# Gravação da demo (vídeo v5)

Nov 15, 2026 · plano de tomadas para quem grava a tela do site. O roteiro, as regras do vídeo e de onde vem cada número estão em [pitch.md](pitch.md). Aqui fica só **o que aparece na tela em cada segundo**, casado com o áudio já gravado.

Critério: **Presentation** (o vídeo mostra o site funcionando) e **Validity** (o que aparece na tela foi medido).

## Arquivos

| Arquivo | Uso |
| --- | --- |
| [video/firesync-v5-legenda.srt](video/firesync-v5-legenda.srt) | Legenda em inglês, frase por frase. Sobe junto com o vídeo no YouTube |
| [video/firesync-v5-legenda-karaoke.ass](video/firesync-v5-legenda-karaoke.ass) | Mesma fala, palavra por palavra (destaque amarelo), para queimar no vídeo. 1280 × 720, embaixo e no centro, margem de 44 px |

A fala termina em **29,80 s**. O vídeo final não pode passar de 30,00 s, então não há tela depois da última palavra.

**Área livre:** a legenda ocupa a faixa de baixo (cerca de 15% da altura). Nada que o jurado precise ler fica nessa faixa: o painel do assistente e os textos sobrepostos vão no meio ou no topo.

## Tomadas

Os tempos são os da legenda. Grave cada tomada mais longa (3 a 5 s de sobra) e corte na edição.

| # | Tempo | Fala | Tela (site) | Texto sobreposto (inglês) |
| --- | --- | --- | --- | --- |
| 1 | 0,15–3,43 | "The Amazon is burning. Where should firefighters act first?" | Abrir <https://firesync.nogranlabs.com.br>. A descida do globo termina no mapa em tela cheia, aba `Fire now`, com os focos da Amazônia | Topo: `FireSync · Team [NAME] · [MEMBERS] · NASA Space Apps 2026 · MODIS and VIIRS Hot Spots` |
| 2 | 3,43–6,81 | "I am Mateus, and FireSync shows which areas are critical today." | No painel `Where to look first`, clicar no primeiro item `Critical`. O mapa centraliza na área | — |
| 3 | 6,81–12,44 | "We combined 24 years of data from NASA's MODIS and VIIRS satellites into a fire history calendar" | Calendário da Amazônia (região `Amazônia`, período inteiro, 2003 a 2026). Passar o mouse num mês hachurado (era MODIS) para mostrar a faixa de incerteza | Canto: `NASA FIRMS · MODIS C6.1 (2003–2012) + VIIRS C2 (2012–2026), one harmonized series` |
| 4 | 12,44–14,64 | "and a risk map for the following days." | Voltar ao mapa e clicar na aba `Risk, next 14 days` | — |
| 5 | 14,64–22,88 | "In tests, our AI predicted half of the Amazon's major fire outbreaks, about ten days ahead. That's time to act before fires spread." | Abrir `Ask firesync`, colar o prompt abaixo e enviar. A resposta aparece com `Critical fire now` e `Very high 14-day risk` | Topo: `Tested on Amazon 2021–2024 · trained only on past years · 51 of 100 significant outbreaks warned, half of them 10+ days ahead` |
| 6 | 22,88–29,80 | "With crews on the ground, that could save over 700,000 acres. Starting with the Amazon, then forests worldwide." | Fechar o assistente. Mapa de risco escurecido (ou o globo se afastando) | Centro, grande: `Could mean 700,000+ fewer acres burned (~290,000 ha)`. Embaixo: `In a year like 2024 (Jun–Aug) · based on a Cerrado brigade study (−12% burned area) · pilot hypothesis`. Rodapé: `Data: NASA FIRMS (MODIS, VIIRS), NASA GIBS · INPE · firesync.nogranlabs.com.br` |

Se o assistente falhar na tomada 5 (`Daily limit reached`, `Assistant unavailable` ou `429`), troque por zoom nas áreas `Very high` da aba `Risk, next 14 days`, com o mesmo texto sobreposto.

## Prompt do assistente (tomada 5)

Colar exatamente, sem mudar nada:

```
Answer in English. I lead fire crews in the Amazon. Which areas are critical today, and where is fire risk very high for the next 14 days? Three short bullets with place coordinates. No probabilities, no cell IDs.
```

Por que este texto (testado na API no ar em 16/11/2026 00:08 UTC):

- Sem o "Answer in English", perguntas em inglês voltaram em português. O chip `Where is it burning right now?` está com uma resposta assim no cache, então **não use os chips no vídeo**.
- "No probabilities, no cell IDs" tira `prob 0.99`, `look_first` e o ID do hexágono H3 da resposta. Sem isso, o modelo também escreveu "≥90% probability" para o nível `very_high`, que é falso (o corte é 0,6).
- A primeira resposta de uma pergunta fica em cache até a próxima rodada do job NRT (a cada 3 h). Dentro dessa janela, o mesmo texto devolve a mesma resposta na hora e sem gastar cota.
- Antes de gravar, confira a resposta: em inglês, três itens, sem probabilidade, e sem a nota "could not be traced".
- O `/ask` aceita **5 pedidos por IP** na janela. Não ensaie muitas vezes seguidas da mesma rede.

## Prompt para o agente que opera o navegador

Para um agente (por exemplo, Claude in Chrome) preparar e executar as tomadas enquanto a equipe grava a tela:

```
You are operating the FireSync website for a screen recording. Do not change any data or settings on the site.

Setup: browser in full screen at 1920x1080 (or 1280x720), no other tabs, no notifications, no bookmarks bar, zoom 100%. Close any cookie or info banner.

Perform these shots in order. Pause about 3 seconds before and after each one so the editor can cut. Move the mouse slowly and directly; no hovering over unrelated elements.

1. Open https://firesync.nogranlabs.com.br and wait until the globe animation ends on the full-screen map with the "Fire now" tab selected. Hold still for 4 seconds.
2. In the "Where to look first" panel, click the first item marked Critical. Wait until the map is centered on it. Hold 4 seconds.
3. Open the fire calendar for the region "Amazônia" covering the whole period (2003 to the latest month). Hover one hatched month from the MODIS era (2003–2011) so its uncertainty range shows. Hold 6 seconds.
4. Go back to the map and click the "Risk, next 14 days" tab. Hold 3 seconds.
5. Open the "Ask firesync" chat. Paste exactly this text and press Enter:
   Answer in English. I lead fire crews in the Amazon. Which areas are critical today, and where is fire risk very high for the next 14 days? Three short bullets with place coordinates. No probabilities, no cell IDs.
   Wait for the answer and hold 8 seconds. If the answer is not in English, shows probabilities, or shows an error, stop and report it instead of retrying more than once (the assistant allows only 5 requests per IP).
6. Close the chat and stay on the "Risk, next 14 days" map. Hold 7 seconds.

At the end, report what you did in each shot and anything that looked different from these steps.
```

## Texto do áudio contra as regras do pitch

O áudio já está gravado, e a legenda tem que repetir o que é falado. Duas palavras ficam fora da regra de redação de [pitch.md](pitch.md): "predicted" (o modelo avisa, não prevê) e "save" (o número é potencial, não resultado). Os números estão certos: 51 de 100 começos de fogo importante, metade dos avisos com 10 dias ou mais, e 288 mil ha ≈ 712 mil acres. Por isso o texto sobreposto da tomada 6 diz "could mean", "based on a Cerrado brigade study" e "pilot hypothesis", e as fontes do 12% (estudo de brigadas no Cerrado) e dos 2,4 milhões de ha (IPAM) precisam estar em References na página do projeto.

## Pendências

- [ ] Nome da equipe e nomes dos membros no texto da tomada 1
- [ ] IPAM e o estudo de brigadas no Cerrado em References ([pagina-projeto.md](pagina-projeto.md))
- [ ] Link do vídeo no campo "Link to Project Demo", testado numa janela anônima
