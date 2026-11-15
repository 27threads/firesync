# Validação da API com a carga real — Eduardo

## Estado da entrega

C1–C6 implementados em `c-api-http-routes`. Foram testados os cinco endpoints, cálculos históricos/recentes, erros, rate limit, cache e ZIP com dados sintéticos, incluindo PostgreSQL/PostGIS e navegador em desktop/celular. **A carga real não foi acessada nesta entrega.** Conforme combinado, Eduardo executa os testes abaixo antes de fechar D7/M2. Este documento é o roteiro de repasse, não um relatório de resultados reais.

A tarefa melhora **Validity** (números verificáveis), **Impact** (janela atual disponível para decisão) e sustenta a categoria **Best Use of Science** (contagens, fatores e método no ZIP).

## Preparação e smoke test

1. Usar esta branch com as dependências de `backend/pyproject.toml` e as migrations 001–004 aplicadas no banco carregado. Não executar `demo_data.py` na carga real.
2. Configurar `DATABASE_URL` no ambiente, sem compartilhar a credencial. Subir a API com os comandos de [backend/README.md](../backend/README.md).
3. Na raiz, com a API no ar, executar:

```powershell
$env:API_URL = 'http://127.0.0.1:8000'
python -m pytest backend/tests/contract/test_api_contract.py -k live_api -q
```

Esse teste lê health/regions, consulta 2024 na primeira região disponível, consulta o mapa e abre o ZIP retornado. Ele não altera o banco. Não configurar `TEST_DATABASE_URL` com a carga real: essa variável pertence aos testes com schemas descartáveis.

4. Subir o front apontando o proxy para a API. Selecionar região, área desenhada e ponto/raio; confirmar que a tela deixou o modo demo, recebeu dados da API e baixou `firesync-YYYY-MM-DD.zip`.

## Conferências solicitadas

| Conferência | O que comparar/registrar |
| --- | --- |
| Metadados | `GET /health` versus `config.data_version`, `config.atualizado_em`, resolução 6 e último mês de `cobertura`. Confirmar valores após duas cargas no mesmo dia. |
| Calendário | Em uma área pequena, conferir 2003-01 (Aqua × cenários), 2012-01/02 (troca de origem), 2024 completo e 2026-11 (N20). Refazer `result.csv` com `counts.csv` e `factors.csv`, alinhando cenários antes dos percentis. |
| Limite da cobertura | Conferir se `cobertura.data_fim` representa o último dia disponível também em dias sem focos, por região/satélite. A API usa o último dia comum da cobertura VIIRS dos biomas selecionados, para não mover a janela para trás só porque não houve fogo. |
| Janela recente | Somar `agregados_diarios` nas células selecionadas de `data_through - 6` até `data_through`, e do dia 1 até essa data. Comparar com `recent`. Repetir com outro período histórico: `recent` deve permanecer igual. |
| Normal da época | Conferir mediana/P25–P75 de janelas do mesmo tamanho com deslocamentos −15…+15 dias nos anos VIIRS anteriores. São até 31 por ano; janelas com dias sem cobertura ou falha ficam fora. Registrar `n_years`/`n_windows`, sobretudo em janeiro, fevereiro e datas com falhas do FIRMS. Confirmar com a equipe os casos sem referências, que retornam estatísticas `null`. |
| Intensidade | Conferir `n_high` nos focos filtrados da janela: FRP ≥ 25 ou confiança alta no VIIRS. O total da janela vem de `agregados_diarios`; `n_high` vem de `focos`, na mesma transação. Verificar que ambos representam a mesma carga e que `n_high <= detections`. |
| Satélite | Conferir que a API usa só SNPP até 2026-10 e N20 de 2026-11 em diante, inclusive em consultas que cruzam a troca. N21 e Aqua não podem duplicar o mapa recente. |
| Qualidade e CSV | Conferir os filtros de confiança, tipo, FRP positivo e satélite nos CSVs. O mapa é NRT; o export pode conter SP e NRT do período. Valores públicos usam `high`, `nominal`, `SP`, `NRT`, `D` e `N`. Abrir o CSV no Excel e conferir acentos, cabeçalhos e números. |
| Mapa | Comparar 24/72/168 h com o SQL filtrado por tempo/bbox. Zoom 4/5/7 deve devolver H3 4/5/6; zoom ≥ 8 deve devolver pontos até 50.000, depois hexágonos 6. A soma das classes deve ser o total, sem truncar. |
| ZIP grande | Para mais de 500.000 focos, confirmar ausência de `detections.csv` e presença de `detections_omitted`, `detections_count` e mensagem em `metadata.json`. O restante do ZIP deve continuar completo. |
| Cobertura | Seleção fora da carga retorna `coverage.status=none`, sem calendário de zeros; seleção parcialmente coberta usa só as células disponíveis. |
| Frescor/cache | Após uma rodada NRT, conferir mudança de `updated_at`/ETag e dos números. Após nova calibração/carga completa, conferir recarga dos fatores por `data_version`, incluindo hora. |
| Latência | Medir primeira chamada e repetição para região pronta, área de ~100 × 100 km e Amazônia. Registrar hardware, número de células, horário/versão, duração e tamanho do ZIP. Não extrapolar desempenho sintético para o histórico completo. |

## Retorno para fechar M2

Registrar o resultado do smoke test, período e área usados, versões dos dados, comparação manual de um mês estimado/observado e das duas janelas recentes, total do mapa, arquivos do ZIP e tempos medidos. Se houver divergência, enviar o pedido JSON e os valores esperado/obtido, sem credenciais nem dumps grandes. Só depois dessa conferência marcar D7/M2 como concluído em [tarefas.md](tarefas.md).

Deploy, limite adicional no proxy, monitoramento de carga atrasada e validação científica do nível de alerta continuam em suas frentes próprias. A regra de harmonização e o contrato permanecem os documentos de referência; este roteiro não redefine o método.
