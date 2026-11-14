#!/usr/bin/env bash
# Calcula a próxima versão SemVer pelos commits desde a última tag vX.Y.Z (docs/versionamento.md).
#   fix/perf -> PATCH | feat -> MINOR | "tipo!:" ou "BREAKING CHANGE" -> MAJOR (na fase 0.y.z, vira MINOR)
# Uso: proxima_versao.sh [auto|patch|minor|major]   (padrão: auto)
# Saída: a versão nova (sem o "v") ou nada, se não houver commit que gere versão.
set -euo pipefail
tipo="${1:-auto}"

ultima=$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1)
ultima=${ultima:-v0.0.0}
IFS=. read -r major minor patch <<< "${ultima#v}"

if [ "$tipo" = auto ]; then
  intervalo="HEAD"; [ "$ultima" != v0.0.0 ] && intervalo="$ultima..HEAD"
  mensagens=$(git log --no-merges --format='%s%n%b%n--fim--' "$intervalo")
  if grep -qE '^[a-z]+(\([^)]*\))?!:|^BREAKING CHANGE' <<< "$mensagens"; then tipo=major
  elif grep -qE '^feat(\([^)]*\))?:' <<< "$mensagens"; then tipo=minor
  elif grep -qE '^(fix|perf)(\([^)]*\))?:' <<< "$mensagens"; then tipo=patch
  else exit 0
  fi
  # fase 0.y.z: mudança que quebra sobe o MINOR; o 1.0.0 é escolhido à mão (tipo=major)
  [ "$tipo" = major ] && [ "$major" -eq 0 ] && tipo=minor
fi

case "$tipo" in
  major) echo "$((major + 1)).0.0" ;;
  minor) echo "$major.$((minor + 1)).0" ;;
  patch) echo "$major.$minor.$((patch + 1))" ;;
  *) echo "tipo inválido: $tipo (use auto, patch, minor ou major)" >&2; exit 2 ;;
esac
