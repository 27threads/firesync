# data-pipeline

Baixa os focos do FIRMS, normaliza, aplica os filtros de qualidade, carrega no banco, calibra os fatores e gera os agregados.

- **Frentes responsáveis:** A (download, importação, banco e job NRT) e B (calibração e agregação). Combinem as subpastas antes de criar arquivos novos, para não editarem os mesmos.
- **Grava no banco** todas as tabelas que o `backend/` lê.
- **Documentos:** [docs/pipeline-dados.md](../docs/pipeline-dados.md), [docs/banco.md](../docs/banco.md), [docs/importacao-regioes.md](../docs/importacao-regioes.md) e [docs/decisoes-harmonizacao.md](../docs/decisoes-harmonizacao.md).

| Caminho | O que é |
| --- | --- |
| `pipeline.py` | `cadastrar`, `download`, `stage`, `importar`, `sem_dados`, `inpe`, `clean` |
| `agregar.py` | Gera `agregados` e `agregados_diarios` (B4) |
| `job_nrt.py`, `Dockerfile` | Job NRT: rodada a cada 3 h, no container |
| `eda.py` | Análise exploratória por satélite |
| `test_pipeline.py` | Testes dos filtros |
| `test_banco.py`, `tests/` | Testes de integração num Postgres descartável |
| `referencia/` | Série mensal do INPE por bioma (`pipeline.py inpe`), usada na validação |
| `regioes.json` | Entrada das regiões. A fonte de verdade é a tabela `regioes`, gravada pelo `cadastrar` |
| `migrations/` | Schema do banco, aplicado em ordem |
| `data/` | ZIPs de teste versionados. Dados baixados e gerados ficam fora do git |

Comandos: ver a seção "Comandos" do [CLAUDE.md](../CLAUDE.md).
