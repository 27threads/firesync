# frontend

Aplicação web: mapa para escolher a área, calendário em heatmap, janela recente com o alerta, camada de focos e downloads.

- **Frente responsável:** D
- **Consome:** a API descrita em [docs/api.md](../docs/api.md). Até a API existir, use o [docs/api-exemplo.json](../docs/api-exemplo.json).
- **Decisões já registradas** ([docs/arquitetura.md](../docs/arquitetura.md)):
  - mapa: Leaflet com renderizador canvas + Leaflet-Geoman para desenhar;
  - cores: cividis em escala logarítmica. Mês incompleto, estimado ou fora da cobertura vão marcados por hachura, borda ou rótulo, nunca só por cor.
- **Requisitos que cobre:** RF06–RF13 e RD01–RD07 ([docs/requisitos.md](../docs/requisitos.md)).

Comandos: `npm ci`, `npm test` (Vitest), `npm run dev` (porta 5173), `npm run build` e `npm run preview`. O texto fixo (intro, Method, Data & credits e o crédito ao FIRMS) fica no `index.html`, para a página abrir completa sem JavaScript; o React monta só a ferramenta em `#tool-root`. As cores em `src/styles.css` são provisórias até a equipe aprovar o plano de design.

Regras que valem aqui:

- Interface em inglês, com crédito ao NASA FIRMS visível.
- A camada de focos recentes vem da nossa API, não do GIBS.
- Não use a camada de nomes do GIBS (`Reference_Labels_15m`): ela deixa blocos pretos no mapa.
- O FRP em MW não aparece na tela. Use a classe de intensidade (`low`, `medium`, `high`).

Ainda a decidir: framework (ponto 5) e biblioteca de gráficos (ponto 7, proposta: ECharts).
