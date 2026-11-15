#!/usr/bin/env bash
# Executa, em ordem alfabética, todos os arquivos .cypher de uma ou mais pastas
# (as pastas também são executadas na ordem em que foram passadas).
# Usado pelos serviços neo4j-schema, neo4j-gds e neo4j-recriar-indices do docker-compose.yml.
set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Informe ao menos uma pasta com arquivos .cypher" >&2
  exit 1
fi
uri="${NEO4J_URI:-bolt://neo4j:7687}"

shopt -s nullglob
for dir in "$@"; do
  files=("$dir"/*.cypher)
  if [ ${#files[@]} -eq 0 ]; then
    echo "Nenhum arquivo .cypher em $dir" >&2
    exit 1
  fi
  for f in "${files[@]}"; do
    echo ">> $(basename "$f")"
    cypher-shell -a "$uri" -u neo4j -p "$NEO4J_PASSWORD" --format plain -f "$f"
  done
  echo "OK: ${#files[@]} arquivo(s) executado(s) de $dir"
done
