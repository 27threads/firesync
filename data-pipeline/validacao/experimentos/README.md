# Scripts dos testes do modelo de risco (referência)

Rascunho. Estes são os scripts que geraram os números do [RFC 0003](../../../docs/rfcs/0003-modelo-risco.md). Foram escritos e rodados no computador de quem fez a frente B, **com caminhos locais** (a série `serie.parquet`, os CSV do FIRMS e os arquivos do IBGE ficavam numa pasta temporária). Servem de ponto de partida para refazer os testes com a série do banco. Antes de rodar, ajustar os caminhos no começo de cada arquivo (`sys.path`, `velha`, `base`, `saida`).

Cada script traz, no começo, o critério fixado **antes** de rodar. Não rodam em CI e não têm testes.

| Script | O que responde | Tabela do RFC 0003 |
| --- | --- | --- |
| `amazonia.py` | Precisão, cobertura, acerto geral e calibração na Amazônia, treino por ano (2021 a 2024) | Acerto na Amazônia |
| `por_bioma.py` | A mesma métrica por bioma e no Brasil, com um modelo treinado até 2020 | Acerto por bioma |
| `melhorar_acuracia.py` | Curva de aprendizado (3, 5, 7 e 8 anos de treino) e ajuste de parâmetros com escolha na validação | Mais histórico; ajuste dos parâmetros |
| `dias_da_semana.py` | O modelo treinado só em domingos vale nos outros dias? | Dias da semana |
| `dia_parcial.py` | O dia de hoje, incompleto, distorce as notas? E `hoje − 1`? | O dia de hoje, ainda incompleto |
| `comparar_inpe_anos.py` | Comparação com o índice de Risco de Fogo do INPE, 2021 a 2024 | Comparação com o INPE |
| `refutar_inpe.py` | Hipóteses de viés da comparação com o INPE | Comparação com o INPE |
| `modelo_onde4.py` | Variáveis do modelo final (10) contra as extras | Segunda pergunta |

Todos usam `risco_celulas.py` (treino e variáveis) e `validacao/modelo_risco.py` e `validacao/backtest_alerta.py` (série e janelas). A série de entrada tem as colunas `unidade, data, n` (célula H3 de resolução 4 e contagem diária de detecções VIIRS), o mesmo formato do `--serie` do `risco_celulas.py`.

## Números do pitch (antecedência e captura)

| Script | O que responde |
| --- | --- |
| `diario.py` | Antecedência do aviso com notas **diárias** na Amazônia (51% dos inícios de fogo relevante avisados, mediana de 10 dias entre os avisados) |
| `captura.py` | Curva de captura: que parte do fogo relevante uma brigada pega olhando só as X% células de maior nota |
| `quietas.py` | Células quietas (zero detecções em 30 dias): quantas existem, quantas têm início de fogo, e a captura por faixa de nota |
| `antecedencia.py` | Primeira versão da antecedência, só com notas de domingo (substituída pelo `diario.py`; ficou com um viés, ver o RFC) |
