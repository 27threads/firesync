# Simulação do sistema e auditoria pelos logs

Nov 14, 2026 · para quem roda a simulação (Eduardo) e para quem corrige o que ela achar

O objetivo é rodar o sistema de ponta a ponta, num banco descartável, e responder pelos logs: **o sistema entrega o que os 5 critérios de [premiacao.md](premiacao.md) cobram?** Cada achado vira uma melhoria (issue) para deixar o sistema mais real e útil.

Os logs são uma linha JSON por evento (formato e lista de eventos em [pipeline-dados.md](pipeline-dados.md), seção "Logs estruturados").

## 1. Preparar (uma vez)

Bash, a partir de `data-pipeline/`, com Docker aberto.

```bash
pip install -r requirements-dev.txt
```

```bash
docker run -d --rm --name firesync-sim -e POSTGRES_PASSWORD=sim -e POSTGRES_DB=firesync_sim -p 5436:5432 postgis/postgis:16-3.4
```

```bash
export DATABASE_URL=postgresql://postgres:sim@localhost:5436/firesync_sim
```

```bash
for f in migrations/*.sql; do docker exec -i firesync-sim psql -q -v ON_ERROR_STOP=1 -U postgres -d firesync_sim < "$f"; done
```

```bash
mkdir -p data/logs
```

Os logs vão para `data/logs/`, que fica fora do git.

## 2. Carga com os dados de 2024 (não precisa de MAP_KEY)

```bash
python pipeline.py cadastrar 2>> data/logs/simulacao.jsonl
```

```bash
python pipeline.py importar data/DL_FIRE_*.zip 2>> data/logs/simulacao.jsonl
```

```bash
python agregar.py 2>> data/logs/simulacao.jsonl
```

O `cadastrar` baixa o shapefile de biomas do IBGE (precisa de internet).

## 3. Job NRT (precisa da `FIRMS_MAP_KEY`)

```bash
export FIRMS_MAP_KEY=<sua chave>
```

| Cenário | Comando | O que o log deve mostrar |
| --- | --- | --- |
| Rodada normal | `python job_nrt.py 2>> data/logs/nrt.jsonl` | `nrt_run_started` e `nrt_run_finished` com o mesmo `run_id`, focos novos e `updated_at` |
| Rodada repetida | o mesmo comando de novo | `detections_inserted` perto de 0 e `detections_updated` alto: nada duplica |
| Duas ao mesmo tempo | `python job_nrt.py 2>> data/logs/nrt.jsonl & python job_nrt.py 2>> data/logs/nrt.jsonl; wait` | uma termina, a outra registra `nrt_run_skipped` com `reason: lock_held` |
| FIRMS falhando | `FIRMS_MAP_KEY=chave-errada python job_nrt.py 2>> data/logs/nrt.jsonl` | o esperado é `nrt_run_failed` com `step: download`. **Se a rodada terminar com 0 focos e sem erro, é um achado:** o sistema diria "atualizado" sem ter dado novo |

Depois de cada rodada que deu certo, confira a versão que a API vai ler:

```bash
docker exec firesync-sim psql -U postgres -d firesync_sim -c "SELECT * FROM config WHERE chave IN ('atualizado_em', 'data_version')"
```

## 4. Ler os logs

Um evento por linha, sem o traceback:

```bash
python -c "import json,sys; [print(e['ts'][11:19], e['level'], e['event'], {k: v for k, v in e.items() if k not in ('ts', 'level', 'logger', 'event', 'traceback')}) for e in map(json.loads, open(sys.argv[1], encoding='utf-8'))]" data/logs/simulacao.jsonl
```

Só os erros e avisos:

```bash
grep -E '"level": "(error|warning)"' data/logs/*.jsonl
```

Uma rodada do job inteira:

```bash
grep '"run_id": "<run_id>"' data/logs/nrt.jsonl
```

## 5. Auditoria: o que cada critério cobra e onde ver no log

A coluna "Medido" é a primeira simulação (14/11/2026, um notebook, banco no Docker). Compare a sua com ela.

| Critério | Pergunta | Evento e campo | Medido | Sinal de problema |
| --- | --- | --- | --- | --- |
| Validity, Best Use of Data | Os dados da NASA entram inteiros? | `import_file_done.rows_read` | NOAA-20 1.988.404, NOAA-21 1.948.842, S-NPP 1.935.740, MODIS 527.894: igual à tabela de [plano-extracao-amazonia.md](plano-extracao-amazonia.md) | qualquer diferença |
| Validity | O recorte pelos biomas perde pouco? | `rows_in_coverage / rows_read` | 99,84% nos VIIRS, 99,89% no MODIS (o resto está fora do Brasil, no mar ou na fronteira) | abaixo de 99% |
| Validity | Nada conta duas vezes? | `import_file_done.duplicate_keys_dropped`, `nrt_replaced_by_sp` | 2, 1, 0 e 0 chaves repetidas; 0 NRT trocados (só tinha SP) | NRT e SP do mesmo dia juntos no banco |
| Best Use of Science | Um VIIRS por período, nunca a soma? | `aggregate_window_done.satellite` e `detections` | 2024 só com S-NPP: 1.764.578 focos. NOAA-20 e NOAA-21 ficam fora do calendário | `detections > 0` de dois VIIRS no mesmo período |
| Best Use of Science | Os filtros (confiança, `type`, FRP) tiram o que deviam? | `detections` contra `rows_in_coverage` do mesmo satélite | S-NPP: 1.764.578 de 1.932.612 (91,3% ficam) | muito longe disso sem explicação |
| Validity, Impact | O dado é recente para quem decide numa emergência? | `nrt_run_finished.updated_at`, intervalo entre rodadas | não medido (sem MAP_KEY na primeira simulação) | intervalo acima de 6 h (RNF07) |
| Validity | O sistema aguenta falha sem mostrar dado errado? | `nrt_run_failed.step`, `atualizado_em` sem mudar | coberto pelos testes de integração; falta rodar contra o FIRMS de verdade | rodada com erro e `atualizado_em` novo |
| Validity | A carga cabe no tempo do evento? | `duration_ms` de `command_finished` e `aggregate_finished` | `cadastrar` 290 s (com o download do IBGE), `importar` 339 s (6,4 mi de focos), `agregar` 38 s | rodada do job NRT acima de alguns minutos |

## 6. Achados da primeira simulação

| Achado | O que foi feito |
| --- | --- |
| No Windows, o log gravava `Amaz�nia` (stderr em cp1252) | Corrigido: a saída é sempre UTF-8. Teste em `tests/test_logs.py` |
| O log da agregação dava linhas (célula × mês), não focos | Corrigido: `aggregate_window_done` ganhou `detections`, conferido contra a consulta direta em `focos` |
| Com só os ZIPs de 2024, a janela do Aqua (2003 a jan/2012) fica com 0 focos | Esperado com dado de teste. O calendário de 2003 em diante precisa do histórico completo (já carregado no banco de teste da frente A) |

## 7. O que os logs ainda não mostram

- **API:** endpoint, tempo de resposta, células da área e status HTTP (RNF07). A API está no PR #41, ainda sem logs.
- **Fatores de harmonização e validação contra o INPE:** `calibrar.py` e `validar_inpe.py` estão na branch `trabalho/harmonizacao` (PR #26), sem logs estruturados.
- **Aviso de dado velho** (mais de 6 h sem rodada): o evento existe (`nrt_run_finished.updated_at`), mas ninguém é avisado ainda.

## 8. Como registrar um achado

Abra uma issue com: o critério afetado, o `run_id` (no job NRT), as linhas do log e o que era esperado. **Antes de colar, confira que não há MAP_KEY no texto** (o pipeline mascara, mas confira). Se for bug, a correção começa por um teste que reproduz o problema ([testes.md](testes.md)).
