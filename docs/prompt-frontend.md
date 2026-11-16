# Prompt do frontend (frente D)

Nov 14, 2026 · frente D · **rascunho, a equipe aprova antes de usar**

Prompt para um agente de IA construir o front do firesync.

Antes de rodar, a equipe precisa decidir os pontos da seção "Decisões que o agente não toma". O CLAUDE.md proíbe o agente de escolher stack por conta própria.

---

## O prompt

Você vai construir o front do **firesync**, projeto do NASA Space Apps 2026, desafio *MODIS and VIIRS Hot Spots*. O app mostra um calendário meses × anos de detecções de fogo para uma área e um período, juntando MODIS (2003 em diante) e VIIRS (2012 em diante) numa escala única.

Quem vai ver: os jurados do Space Apps (critérios: **Impact, Creativity, Validity, Relevance, Presentation**) e o público do desafio (equipes de alerta precoce, resposta a emergências, bombeiros, gestores de terras, cientistas). O jurado decide em poucos segundos, muitas vezes só pelo vídeo de 30 s ou por 7 slides. O usuário real pode estar no meio de uma emergência. O front tem que servir aos dois: impressionar na primeira tela e ser rápido de ler e de usar em seguida.

Nível esperado: front-end sênior especialista em visualização de dados e em animação (GSAP, ScrollTrigger, Lenis, canvas, WebGL). Moderno, limpo e diferente dos dashboards de fogo que já existem (FIRMS Fire Map, Global Forest Watch, painel do INPE).

### Antes de desenhar

1. Leia, nesta ordem: [README.md](../README.md), [CLAUDE.md](../CLAUDE.md), [requisitos.md](requisitos.md), [arquitetura.md](arquitetura.md), [tarefas.md](tarefas.md) (frente D), [api.md](api.md), [api-exemplo.json](api-exemplo.json), [decisoes-harmonizacao.md](decisoes-harmonizacao.md) e [pipeline-dados.md](pipeline-dados.md). Os documentos são a fonte de verdade.
2. Mexa só em `frontend/`, na branch `d-frontend`. Atualize o status das tarefas D1–D8 em [tarefas.md](tarefas.md) ao começar e ao terminar.
3. **Nada sem fonte.** Todo número da tela vem da API ou do `api-exemplo.json`. Toda frase sobre o método (fator, anos de calibração, troca de sensor, resolução) vem dos documentos acima. Não invente contagem, porcentagem, data de satélite, horário de passagem, resolução ou nome de pessoa. O que não tiver fonte entra com um comentário `<!-- TODO(confirm): ... -->` e vai para a lista de pendências do resumo final.
4. **Honestidade dos dados vale mais que o efeito visual.** Regras do contrato que a tela tem que respeitar:
   - Todo número mostra a origem: **observado (VIIRS)** ou **estimado a partir do MODIS, com faixa de incerteza** (`band_low`–`band_high`). A faixa só aparece nos estimados.
   - A troca de sensor (fev/2012) fica marcada no calendário, para ninguém ler 2011 → 2012 como aumento real.
   - **Zero, sem dados (`missing_days`) e fora da cobertura são três estados visuais diferentes.** Nunca pinte "sem dados" com a cor do zero.
   - A unidade é **detections** (detecções de fogo), nunca "fires" ou "incêndios".
   - O FRP em MW não aparece. A intensidade aparece como classe `low` / `medium` / `high`, e só no período VIIRS.
   - Crédito ao NASA FIRMS visível em todas as telas.
5. Liste as perguntas reais que cada público faz ao abrir o app e use isso para guiar títulos e a ordem da tela. Exemplos: "Is this fire season worse than usual here?", "Which months burn the most in the Pantanal?", "Was 2024 a record year?", "What happened in the last 7 days?", "Can I trust numbers before 2012?". Use as palavras do desafio e do contrato (*hot spots*, *fire detections*, *anomaly*, *seasonal pattern*).
6. Se faltar imagem, o design se apoia em dado real, tipografia e num efeito próprio. Nada de banco de imagens, nada de foto de floresta em chamas genérica, nada de arte gerada por IA.

### Direção de design

- **Ache a ideia central no mundo real do problema** e transforme isso na primeira tela: uma animação ou interação que só faria sentido para ESTE projeto. Levante pelo menos 3 conceitos vindos de fontes diferentes, por exemplo:
  - um instrumento ou objeto do ofício (a faixa de varredura do satélite, o pixel de 1 km do MODIS e o de 375 m do VIIRS, a grade hexagonal H3);
  - um momento que o usuário vive (o satélite passando e acendendo os focos, desenhar a área no mapa e ver a história dela aparecer);
  - o próprio dado (276+ meses de fogo virando uma faixa de cor que se dobra no calendário meses × anos);
  - o resultado que o usuário leva (saber se agora está acima do normal; duas séries de sensores diferentes virando uma só).

  Escolha o mais específico e surpreendente. Se outro painel de fogo ou de clima pudesse usar a mesma ideia, ela é genérica demais. A ideia mais forte costuma ser a que **explica a harmonização** (o diferencial do projeto) sem precisar de texto.
- **A equipe aprova o conceito antes de você construir.** O guia do Space Apps diz que a IA não deve criar a ideia de como resolver o desafio. O conceito visual é apresentação, não método, mas a escolha final é da equipe. Proponha, não decida.
- **A primeira tela tem que impressionar nos primeiros segundos** e funcionar gravada num vídeo de 30 s: uma sequência marcante (presa na rolagem com pin do ScrollTrigger, ou interação direta com cursor/dedo), em canvas, SVG ou WebGL quando o efeito pedir. Ela termina dentro da ferramenta, não num botão "Get started" genérico.
- **O conceito não pode morrer na primeira tela.** Ele volta em pelo menos 2 ou 3 momentos úteis da ferramenta, por exemplo:
  - a área desenhada no mapa "acende" as células e a contagem chega ao calendário;
  - um controle que mostra a mesma área em MODIS bruto, VIIRS bruto e série harmonizada, para o jurado ver a costura;
  - a faixa de incerteza que "aperta" quando a série passa de estimada para observada;
  - "last 7 days vs. typical" desenhado como a janela atual sobre a distribuição das janelas históricas.
  Uma versão que só tem a primeira tela bonita e depois um dashboard padrão de cards é considerada simples demais.
- **Entre esses momentos, o essencial fica direto e fácil de achar:** escolher a área, escolher o período, ler o calendário, ver os indicadores, baixar os arquivos. Um bombeiro não pode precisar rolar uma animação para chegar no número.
- **Paleta de 5 a 6 cores com nomes**, tirada do mundo real do projeto (imagem térmica, terra queimada, noite vista de órbita, a cor do bioma). A rampa do heatmap é separada da paleta de marca e tem que ser **perceptualmente uniforme e legível para daltônicos** (RD04: viridis, cividis ou equivalente validado). Teste com simulação de deuteranopia e protanopia. Vermelho/verde não carregam significado sozinhos.
- **Tipografia escolhida para o projeto** (uma ou duas famílias bem distintas), com números tabulares nos dados, escala modular e linhas com menos de 80 caracteres.
- **Evite os sinais de "site feito por IA":** rótulos em CAIXA ALTA espaçada acima de títulos, "A · B · C" com ponto médio, seta "→" em botões, fonte mono para rótulos, uma palavra destacada em itálico ou cor no título, cards idênticos com sombra cinza, fundo creme com acento terracota, preto com acento verde-ácido, gradiente roxo-azul de "tech", glassmorphism em tudo. Numeração 1/2/3 só se o conteúdo for de fato uma sequência.
- **Confira o tom.** Fogo é dano real para pessoas e florestas. O tom é **científico, sério e confiável**, como uma missão da NASA, não um filme de catástrofe. Nada de chamas animadas, fumaça dramática, contagem regressiva, sirene ou vermelho piscando. A emoção vem do dado bem mostrado.

### Telas e seções (adapte)

Primeira tela com a ideia central → frase curta e factual do que é o app → **ferramenta** (área + período → indicadores → calendário → sazonalidade → ranking de anos → últimos 7 dias e mês atual vs. normal → downloads) → **Method** (como a harmonização funciona, troca de sensor, faixa de incerteza, limites da classe de intensidade, comparação com o INPE só pela forma da curva) → **Data & credits** (NASA FIRMS, MODIS C6.1, VIIRS C2, IBGE, INPE, bibliotecas, uso de IA).

Requisitos que cada parte cobre:

| Parte | Requisitos |
| --- | --- |
| Escolha de área: mapa com polígono e retângulo, lat/lon digitado, biomas prontos de `GET /regions` | RF06, RD01, RD02 |
| Intervalo de datas | RF07 |
| Calendário meses × anos em heatmap, com origem, faixa, `missing_days` e troca de sensor | RF08, RD03, RD04 |
| Meses com mais fogo | RF09 |
| Ranking de anos, com faixa nos anos estimados | RF10 |
| Mês atual e últimos 7 dias vs. normal (`recent`) | RF11, RF12, RD07 |
| Indicadores principais (`indicators`) | RD06 |
| Download das análises (imagem) e do pacote de auditoria (`POST /export`) | RF13, RD05 |
| Focos recentes no mapa com classe de intensidade (`GET /detections/recent`) | RD07 |
| Estados de erro do contrato (`no_data`, fora da cobertura, `429 rate_limited`) com mensagem útil | RNF05 |

### Texto e conteúdo

- **Interface toda em inglês**, escrita para quem usa o dado, sem jargão de marketing.
- Logo abaixo da primeira tela, um parágrafo curto e factual que funciona sozinho: o que é, que dados usa, que período cobre, para quem serve. É o trecho que um jurado copia para entender o projeto.
- Todo texto de método e de crédito fica em HTML real, legível com JavaScript desligado. O efeito da primeira tela fica por cima ou ao lado de texto HTML de verdade (H1, explicação), nunca no lugar dele. A ferramenta pode exigir JS, mas sem JS a página mostra o que o app é, o método, os créditos e um aviso.
- Cada número da ferramenta tem rótulo, unidade e origem. Tooltip do calendário: mês, ano, detecções, origem, faixa (se houver), dias sem dado.
- Não escreva nada que os documentos não sustentem. Prefira frases tiradas dos achados de [pipeline-dados.md](pipeline-dados.md) e de [decisoes-harmonizacao.md](decisoes-harmonizacao.md).

### On-page e compartilhamento

O app não precisa rankear no Google. Precisa abrir bem quando o link for colado na página do projeto, no Slack do evento ou no WhatsApp de um jurado.

- `<html lang="en">`, um único H1, hierarquia H2/H3 sem pular nível.
- HTML semântico: header, nav, main, section com `aria-labelledby`, footer, `<time>` nas datas, tabelas reais onde o dado é tabela.
- `<title>` de até ~60 caracteres e meta description de ~150, com o diferencial real (série única MODIS + VIIRS desde 2003).
- Open Graph e Twitter Card completos, com `og:image` 1200×630 feita a partir de um calendário real do app (dado do exemplo ou da API, nunca inventado).
- `theme-color`, `site.webmanifest`, `favicon.ico`, `icon.svg`, `apple-touch-icon.png` (180 px).
- JSON-LD opcional: `WebApplication` e `Dataset` com `creator`, `temporalCoverage`, `spatialCoverage` e `isBasedOn` apontando para o FIRMS. Tudo o que estiver no JSON-LD tem que estar visível na página.
- Links externos (FIRMS, INPE, IBGE, repositório) com `rel="noopener"`.

### Animação (GSAP + ScrollTrigger + Lenis)

- Uma sequência orquestrada no carregamento + interações que respondem ao usuário + poucos efeitos de scroll com propósito (pin, clip-path, texto que entra). Nada de fade-up genérico em toda seção.
- **Dentro da ferramenta, animação só para explicar mudança de estado** (área nova, período novo, troca de visão). Transições curtas (até ~300 ms), interrompíveis, nunca bloqueando o clique seguinte. Lenis e pins ficam fora da área da ferramenta para não brigar com o arrastar do mapa.
- Canvas 2D ou WebGL quando o efeito pedir, com IntersectionObserver para pausar fora da tela.
- Texto nunca começa com `opacity: 0` no CSS. O estado inicial das animações é aplicado pelo JS.
- `prefers-reduced-motion` respeitado: a primeira tela vira uma imagem estática bem composta, e tudo fica legível.

### Performance (obrigatório)

- Nada de camada de tela cheia com `mix-blend-mode`. Se usar grão, `position: fixed; inset: 0`, sem blend, opacidade baixa.
- Nada de `filter` CSS em imagem que se move. Trate a imagem no arquivo.
- Canvas de efeitos difusos em meia resolução. Loops param quando ociosos ou fora da tela. Animações cíclicas simples via CSS.
- `filter: blur` animado só em blocos inteiros, nunca letra por letra. Letras animam só `opacity` e `transform`.
- Evite rotação 3D com perspectiva em muitos elementos.
- O mapa (WebGL) e as bibliotecas da ferramenta carregam só quando a ferramenta entra na tela ou quando o usuário pede, não na primeira pintura.
- O calendário de 24 anos × 12 meses redesenha em menos de 100 ms ao trocar de área. Sem layout thrashing no tooltip.
- Imagens com no máximo 1600 px, AVIF/WebP com JPG de fallback, `srcset`, lazy loading abaixo da dobra, preload da fonte e da imagem da primeira tela, `fetchpriority="high"` no LCP. `width`/`height` fixos em tudo para não haver CLS.
- JS com `defer` ou módulo, sem bloquear a renderização.
- Meça com Playwright + Chrome headless (os testes ficam em `frontend/e2e/`), com CPU 4× mais lenta no perfil de celular: FCP, LCP, CLS, INP (ou TBT), FPS na primeira tela e na rolagem, long tasks. Metas: LCP < 2,5 s, CLS < 0,1, INP < 200 ms, ~60 fps parado e mais de 50 fps rolando no celular. Isole o que pesa desligando um efeito por vez.
- Lighthouse no perfil celular: meta ≥ 95 em Acessibilidade e Boas práticas, ≥ 90 em SEO, e Performance o mais alto possível sem sacrificar a primeira tela.

### Qualidade mínima

- Responsivo de 360 px a 1440 px+. No celular (até 560 px), o calendário e os gráficos usam uma geometria estreita: os 12 meses cabem na largura da tela, o texto não encolhe e as notas do calendário vão para baixo da grade. Sem rolagem horizontal da página.
- Foco de teclado visível. Calendário navegável pelo teclado (setas entre células, leitura da célula pelo leitor de tela). O desenho de área tem alternativa por teclado (lat/lon digitado ou bioma da lista).
- Contraste acessível (WCAG AA) em texto e nos rótulos sobre o heatmap.
- Os dados do calendário também existem como tabela acessível (escondida visualmente ou atrás de um botão "View as table").
- Página legível e completa com JavaScript desligado, como descrito em "Texto e conteúdo".
- Funciona com a API real e com o `api-exemplo.json` (modo demo marcado na tela), para a demo não depender da API estar no ar.

### Processo em etapas

Construa em etapas, **uma por vez**. Cada etapa termina com commit na `d-frontend`, screenshots desktop (1440) e celular (390) do que mudou, e uma parada para a equipe revisar. Não comece a etapa seguinte sem o "ok".

**A ordem põe o obrigatório antes do efeito.** O prazo é domingo, 23h59. Se o tempo acabar na etapa 5, o app ainda cumpre o desafio. Se acabar na etapa 3 com a primeira tela pronta e sem ferramenta, não cumpre.

| Etapa | O que faz | Tarefas | Pronto quando | Marco |
| --- | --- | --- | --- | --- |
| 0. Decisões | A equipe fecha os pontos 5–10 de "Decisões que o agente não toma". O agente só lista o que falta | T00 | Pontos preenchidos em [arquitetura.md](arquitetura.md) | M0 |
| 1. Plano de design | 3 conceitos (uma linha cada), qual recomenda e por quê; paleta com nomes e rampa do heatmap; tipografia; wireframe ASCII desktop e celular; título, H1, meta description; perguntas do público. Revise o que soar genérico | — | A equipe escolheu o conceito | — |
| 2. Esqueleto | Estrutura de pastas, fontes e vendor locais, tokens de cor e tipografia, layout das seções, texto do parágrafo factual, Method e Data & credits em HTML, crédito ao FIRMS, meta tags e ícones. Sem animação ainda | D1 | Abre local, completo com JS desligado, Lighthouse de Acessibilidade ≥ 95 | — |
| 3. Ferramenta com dados de exemplo | Calendário em heatmap (origem, faixa, `missing_days`, troca de sensor, tabela acessível, teclado), indicadores, sazonalidade, ranking de anos, últimos 7 dias e mês atual vs. normal, tudo lendo o `api-exemplo.json` | D4, D5 | Todos os campos do exemplo aparecem certos na tela, incluindo os três estados (zero, sem dados, fora da cobertura) | M1 |
| 4. Área e período | Mapa com polígono e retângulo, lat/lon digitado, biomas de `GET /regions`, seletor de datas, montagem do pedido do `api.md`, focos recentes com classe de intensidade | D2, D3 | A área desenhada e as datas viram o JSON do pedido, conferido no console | M1 |
| 5. Downloads e erros | Download das análises (imagem) e do pacote de auditoria, mensagens para `no_data`, fora da cobertura e `429` | D6 | Arquivos baixam e abrem; cada erro tem tela própria | — |
| 6. Ligação com a API | Troca o JSON de exemplo pela API real, com modo demo marcado na tela quando a API falhar | D7 | Front → API → `agregados` reais, local de ponta a ponta | M2 |
| 7. Primeira tela | O conceito aprovado: sequência de carregamento, pin na rolagem ou interação com cursor/dedo, versão estática para `prefers-reduced-motion` | — | Impressiona gravada em 30 s; FPS e LCP dentro das metas | — |
| 8. Momentos interativos | O conceito volta em 2 ou 3 pontos da ferramenta (ver "Direção de design") e as transições de estado | — | Cada momento ajuda a ler o dado, não só enfeita | — |
| 9. Qualidade e performance | Screenshots de todas as seções (inclusive no meio das animações), teste de todas as interações, screenshot sem JS, Playwright com CPU 4× mais lenta, Lighthouse, simulação de daltonismo. Desligar um efeito por vez para achar o que pesa | — | Metas de "Performance" e "Qualidade mínima" batidas, ou o desvio explicado | M3 (com o deploy da frente C) |
| 10. Demo e entrega | Captura de 30 s da primeira tela até um resultado na ferramenta, base do vídeo ou dos slides; linha na tabela "AI use" do README | D8 | Link público testado em janela anônima | M4 |

Se o tempo apertar, as etapas 7 e 8 encolhem (primeira tela mais simples, um momento interativo só). As etapas 2 a 6 não são cortadas.

Regras de todas as etapas: registre na tabela "AI use" do README o que foi gerado, no mesmo commit do código. Sem `Co-Authored-By` nos commits.

Entrega final: link local e/ou público, resumo curto do conceito, título e meta description, screenshots, números de performance e a lista de pendências (`TODO(confirm)`, campos do contrato que ainda não existem na API, textos que dependem de decisão da equipe).

---

## Decisões que o agente não toma

O agente para e pergunta se algum destes pontos de [arquitetura.md](arquitetura.md) ainda estiver "a decidir":

| # | Ponto | Por que importa para o prompt |
| --- | --- | --- |
| 5 | Framework do front | HTML/CSS/JS sem build ou um framework. Uma ferramenta com mapa, estado e downloads pode pedir um framework. Os dois funcionam com GSAP |
| 6 | Biblioteca de mapa e desenho de área | Define o peso do WebGL e como a área vira o pedido do `api.md` |
| 7 | Biblioteca de gráficos do calendário | D3, Observable Plot, canvas próprio etc. Muda o custo de redesenho e de acessibilidade |
| 8 | Paleta acessível do heatmap | viridis ou cividis (RD04) |
| 9 | Formato do download | PNG, PDF, CSV. O pacote de auditoria já está no `api.md` |
| 10 | Granularidade do calendário | Mensal ou diária |
