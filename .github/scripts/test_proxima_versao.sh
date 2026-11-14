#!/usr/bin/env bash
# Testa o proxima_versao.sh num repositório git temporário. A esteira roda este arquivo.
set -euo pipefail
script="$(cd "$(dirname "$0")" && pwd)/proxima_versao.sh"
dir=$(mktemp -d); trap 'rm -rf "$dir"' EXIT
cd "$dir" && git init -q && git config user.email teste@teste && git config user.name teste
falhas=0
c() { git commit -q --allow-empty -m "$1" ${2:+-m "$2"}; }
ok() { if [ "$1" = "$2" ]; then echo "ok    $3"; else echo "FALHA $3: veio '$1', esperado '$2'"; falhas=$((falhas + 1)); fi; }

c "docs: só documentação";            ok "$(bash "$script")" ""      "sem tag e só docs: nenhuma versão"
c "fix: corrige";                      ok "$(bash "$script")" "0.0.1" "sem tag e um fix: 0.0.1"
git tag v0.1.0
c "docs: x"; c "fix(api): y";          ok "$(bash "$script")" "0.1.1" "fix sobe o PATCH"
c "feat(front): z";                    ok "$(bash "$script")" "0.2.0" "feat sobe o MINOR"
c "feat!: quebra";                     ok "$(bash "$script")" "0.2.0" "quebra na fase 0.y.z sobe o MINOR"
ok "$(bash "$script" major)" "1.0.0"   "major escolhido à mão: 1.0.0"
git tag v1.0.0; c "feat: nova";        ok "$(bash "$script")" "1.1.0" "depois do 1.0, feat sobe o MINOR"
c "refactor: x" "BREAKING CHANGE: muda o contrato"
ok "$(bash "$script")" "2.0.0"         "BREAKING CHANGE no corpo sobe o MAJOR"
git tag v2.0.0; c "chore: x";          ok "$(bash "$script")" ""      "só chore: nenhuma versão"
ok "$(bash "$script" patch)" "2.0.1"   "patch escolhido à mão"
if bash "$script" errado 2>/dev/null; then echo "FALHA tipo inválido deveria falhar"; falhas=$((falhas + 1)); else echo "ok    tipo inválido falha"; fi
exit "$falhas"
