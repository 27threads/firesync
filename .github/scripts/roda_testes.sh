#!/usr/bin/env bash
# Lê do stdin a lista de arquivos mudados no PR (um por linha) e imprime "false" se todos forem .md
# (os testes de código podem ser pulados) ou "true" se algum não for. Lista vazia imprime "true".
set -euo pipefail
arquivos=$(grep -v '^$' || true)
if [ -n "$arquivos" ] && ! grep -qv '\.md$' <<< "$arquivos"; then
  echo false
else
  echo true
fi
