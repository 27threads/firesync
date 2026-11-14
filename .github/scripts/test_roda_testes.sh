#!/usr/bin/env bash
# Testa o roda_testes.sh. A esteira roda este arquivo antes de decidir se pula os testes de código.
set -euo pipefail
script="$(cd "$(dirname "$0")" && pwd)/roda_testes.sh"
falhas=0
ok() { if [ "$1" = "$2" ]; then echo "ok    $3"; else echo "FALHA $3: veio '$1', esperado '$2'"; falhas=$((falhas + 1)); fi; }
r() { printf '%b' "$1" | bash "$script"; }

ok "$(r 'README.md\ndocs/api.md\n')"                 "false" "só .md: pula"
ok "$(r 'docs/sub/pasta/x.md\n')"                    "false" ".md em subpasta: pula"
ok "$(r 'docs/api.md\ndocs/api-exemplo.json\n')"     "true"  ".json em docs/ é testado pelo contrato: roda"
ok "$(r 'data-pipeline/pipeline.py\n')"              "true"  "código: roda"
ok "$(r '.github/workflows/ci.yml\n')"               "true"  "mudança na esteira: roda"
ok "$(r 'docs/notas.md.bak\n')"                      "true"  "termina diferente de .md: roda"
ok "$(r 'CHANGELOG.MD\n')"                           "true"  "só .md minúsculo conta"
ok "$(r '')"                                         "true"  "lista vazia: roda, por segurança"
exit "$falhas"
