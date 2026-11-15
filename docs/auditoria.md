# Auditoria do repositório

Nov 15, 2026 · frente A (Eduardo) · `main` em `56c49f1`

Leitura de ponta a ponta do pipeline, da API e do front, com medições no banco de teste. Esta é a segunda rodada: a primeira gerou o PR #80. Quando um item for resolvido, marque o PR na tabela; quando todos estiverem resolvidos, este documento pode ser apagado.

## Como foi feita

- **Carga considerada:** uma VPS, um processo da API, um job NRT a cada 3 h e de dezenas a centenas de pessoas ao mesmo tempo durante o julgamento.
- **Verificação:** na `main`, todas as suítes passam: pipeline (94 testes e `test_pipeline.py`), backend (207 testes, cobertura de 97%), front (127 testes e `tsc`), `ruff` e `vulture`. A única falha é o `test_demo`, e só localmente, porque o Postgres de teste local exige senha e o teste monta a conexão com `conn.info.dsn`.
- **Medições:** as consultas da API foram medidas no banco de teste (46,4 milhões de focos), enviadas pelo psycopg como a API envia.

## Achados

| # | Gravidade | Frente | Achado | Correção | Situação |
| --- | --- | --- | --- | --- | --- |
| 1 | Precisa corrigir | C (deploy) | O limite de requisições é por IP. Atrás do servidor web do `docker-compose`, todos os usuários chegam com o IP do proxy e dividem o mesmo limite (10 calendários por minuto para o site inteiro) | A API conta pelo IP real com `CLIENT_IP_HEADER=CF-Connecting-IP`, atrás do Cloudflare Tunnel ([deploy.md](deploy.md)) | Resolvido no PR #93 |
| 2 | Deveria corrigir | D | Durante o carregamento de uma área nova, o botão de PNG continua ativo e gera a imagem com os meses da área anterior e o nome da área nova (`frontend/src/export/ExportBar.tsx:80`, `frontend/src/state/useExplorer.ts:203`) | Desligar o PNG enquanto `result.kind === 'loading'` | Aberto |
| 3 | Bom ter | C | A exportação conta os focos da área na tabela `focos` antes de montar o zip: o Pantanal inteiro leva 11,7 s (771 mil focos, acima do limite de 500 mil, então o arquivo nem entra), e a Amazônia de 2024 leva 3 s (`backend/src/adapters/outbound/postgres/api.py`, `detections()`) | Usar a soma do `snapshot.counts`, que tem os mesmos filtros, para pular a contagem quando passar do limite | Aberto |
| 4 | Bom ter | B | O modelo de risco agrupa cerca de 6% dos focos numa célula res 4 diferente da do banco: usa `latlng_to_cell(…, 4)`, e o banco usa a célula-mãe da res 6 (`data-pipeline/validacao/modelo_risco.py:60`). Observação da revisão do PR #81 | `cell_to_parent(latlng_to_cell(la, lo, 6), 4)` | Aberto |
| 5 | Bom ter | B | `empilhar()` decide pelo tamanho se um vetor é por semana ou por unidade. Com 624 unidades (o número de semanas), um vetor por unidade vira por semana, sem erro (`data-pipeline/validacao/modelo_risco.py:269`). Observação da revisão do PR #81 | Passar o eixo de forma explícita | Aberto |
| 6 | Bom ter | C | O `metadata.json` da exportação descreve as datas de troca de satélite num texto escrito à mão, a única cópia que sobrou fora do `SATELLITE_SWITCHES` (`backend/src/application/audit.py:32`) | Montar a frase a partir do `SATELLITE_SWITCHES` | Aberto |

## Conferido e sem problema

- **Consultas do calendário de um bioma inteiro:** medidas para a Amazônia (110 mil células), levam cerca de 2 s cada (`agregados`, 1,9 s; meses provisórios, 2,0 s). Uma medição feita com as células passadas por subconsulta levou 21 minutos, mas isso era do teste, não da API.
- **Correções da primeira rodada (PR #80):** continuam na `main`. A janela do job NRT parte do último dia gravado, a página de dias sem dados não trava a agregação, a API recusa corpo acima de 1 MB, e as datas de satélite ficam num lugar só.
- **Front:** datas formatadas em UTC, mapa com debounce (espera de 150 ms) e sem HTML vindo da API fora do `escapeHtml`, estados de erro sem reaproveitar números de outra área (exceto o achado 2).

## Não conferido

- `harmonizacao/modelo_a.py`, `harmonizacao/validar_inpe.py` e `eda.py`, que são análises offline e não rodam em produção.
- `frontend/src/map/MapStage.tsx` linha a linha (só o fluxo de pedidos e a limpeza de eventos), e o interior de `CalendarSvg.tsx` e `calendarPng.ts`.
- O PR #86, ainda aberto.
