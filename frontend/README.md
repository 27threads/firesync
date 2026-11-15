# frontend

Aplicação web: mapa para escolher a área, calendário em heatmap, janela recente com o alerta, camada de focos e downloads.

- **Frente responsável:** D
- **Consome:** a API descrita em [docs/api.md](../docs/api.md) (`GET /api/v1/health`, `GET /api/v1/regions`, `GET /api/v1/detections/recent`, `POST /api/v1/calendar`, `POST /api/v1/export`). Em `dev` e `preview`, o Vite faz proxy de `/api` para `VITE_DEV_API_PROXY` (padrão `http://localhost:8000`), mantendo `VITE_API_URL` quando definido. Quando a API não responde, entra em modo demo com [docs/api-exemplo.json](../docs/api-exemplo.json).
- **Decisões já registradas** ([docs/arquitetura.md](../docs/arquitetura.md)):
  - mapa: Leaflet com renderizador canvas (`preferCanvas`) + Leaflet-Geoman para desenhar em carga tardia (confirmado pela frente D); mapa base do NASA EOSDIS GIBS, sem chave de API: `BlueMarble_ShadedRelief_Bathymetry` (padrão, a mesma camada do fim da abertura) ou `VIIRS_Black_Marble`, com `Coastlines_15m` (o CARTO passou a exigir chave; ver ponto 6 de [docs/arquitetura.md](../docs/arquitetura.md)), mais camada de focos recentes (`24 h`, `72 h`, `7 days`) em hexágonos H3 (`cividis` log) ou pontos diferenciados por raio/borda e cor segundo a classe de intensidade (`low`, `medium`, `high`);
  - cores: cividis em escala logarítmica. Mês incompleto, estimado ou fora da cobertura vão marcados por hachura, borda ou rótulo, nunca só por cor.
- **Requisitos que cobre:** RF06–RF13 e RD01–RD07 ([docs/requisitos.md](../docs/requisitos.md)), mais o aviso antecipado do RFC 0003 (D10): lista "Where to look first", selo do alerta e legenda do risco, só quando a API manda `alerts` e `alerts.risk`.

Comandos: `npm ci`, `npm test` (Vitest), `npm run dev` (porta 5173), `npm run build` e `npm run preview`. O texto fixo (intro, Method, Data & credits e o crédito ao FIRMS) fica no `index.html`, para a página abrir completa sem JavaScript; o React monta a abertura em `#opening-root` e a ferramenta em `#tool-root`.

Design (D9, tema claro desde a D11): fundo claro em toda a página, âmbar só para seleção e ações (texto em âmbar usa o tom escuro `--amber-ink`), cividis só na escala científica. A página abre com o globo (`src/hero/OrbitalOpening.tsx`, three.js) e segue direto para o explorador. Tipografia Archivo (variável, eixo de largura) via Fontsource, com números tabulares. O calendário principal (`src/history/HistoryPanel.tsx` + `src/calendar/CalendarSvg.tsx`) usa GSAP (`src/hero/heroIntro.ts`): quando entra na tela, os meses aparecem como uma faixa cronológica MODIS → VIIRS e se dobram no calendário; o React já desenha o estado final, então sem animação (ou com `prefers-reduced-motion`) nada se perde.

Regras que valem aqui:

- Interface em inglês, com crédito ao NASA FIRMS visível.
- A camada de focos recentes vem da nossa API, não do GIBS.
- Não use a camada de nomes do GIBS (`Reference_Labels_15m`): ela deixa blocos pretos no mapa.
- O FRP em MW não aparece na tela. Use a classe de intensidade (`low`, `medium`, `high`).

Stack (pontos 5 e 7 de [docs/arquitetura.md](../docs/arquitetura.md)): **Vite + React + TypeScript**, com o calendário e os gráficos em **D3 + SVG próprio**. A esteira sobe o front com `npm run build` e `npm run preview` na porta 5173.
