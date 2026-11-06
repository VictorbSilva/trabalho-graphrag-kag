#!/usr/bin/env bash
# Executa, em ordem alfabética, todos os arquivos .cypher de uma pasta.
# Usado pelos serviços neo4j-schema e neo4j-gds do docker-compose.yml.
set -euo pipefail

dir="${1:?Informe a pasta com os arquivos .cypher}"
uri="${NEO4J_URI:-bolt://neo4j:7687}"

shopt -s nullglob
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
