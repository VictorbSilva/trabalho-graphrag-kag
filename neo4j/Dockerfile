# Neo4j 5.26 LTS com APOC e Graph Data Science já instalados na imagem.
#
# Por que não usar a variável NEO4J_PLUGINS: com ela o container baixa o GDS
# (65 MB) toda vez que sobe. Se a rede ainda não estiver pronta, por exemplo
# logo depois de abrir o Docker Desktop, o download falha e o Neo4j não inicia.
# Aqui o download acontece uma vez só, na construção da imagem, e é conferido
# pelo checksum.
#
# Ao mudar a versão do Neo4j, mude também a imagem dos serviços neo4j-schema
# e neo4j-gds no docker-compose.yml.
FROM neo4j:5.26.32-community

# GDS 2.13 é a linha compatível com o Neo4j 5.26.
ARG GDS_VERSION=2.13.14
ARG GDS_SHA256=24eef4e1ca6626770b1b0de465c9099db207b639f917146770fbed0e686661e9

RUN cp /var/lib/neo4j/labs/apoc-*-core.jar /var/lib/neo4j/plugins/ \
 && wget -q --tries 5 --timeout 120 \
      -O /var/lib/neo4j/plugins/graph-data-science.jar \
      "https://graphdatascience.ninja/neo4j-graph-data-science-${GDS_VERSION}.jar" \
 && echo "${GDS_SHA256}  /var/lib/neo4j/plugins/graph-data-science.jar" | sha256sum -c -

ENV NEO4J_dbms_security_procedures_unrestricted="apoc.*,gds.*"
