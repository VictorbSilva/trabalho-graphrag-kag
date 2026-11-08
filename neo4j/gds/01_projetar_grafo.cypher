// R20 - Projeção em memória do grafo de entidades para o GDS.
// Rode depois da ingestão:  docker compose run --rm neo4j-gds
//
// Projeta só os nós Entity e as relações entre eles (Chunks e Documents ficam de fora).
// As relações são tratadas como não direcionadas, o que faz sentido para
// comunidades (Louvain) e centralidade geral (PageRank).

// Para com uma mensagem clara se a ingestão ainda não rodou.
MATCH (e:Entity)
WITH count(e) AS total
CALL apoc.util.validate(total = 0, 'Nenhum nó Entity no banco. Rode a ingestão antes do GDS.', [])
RETURN total AS entidades;

// Remove uma projeção anterior, se existir (o false evita erro quando não existe).
CALL gds.graph.drop('entidades', false) YIELD graphName
RETURN graphName AS projecao_removida;

MATCH (origem:Entity)
OPTIONAL MATCH (origem)-[r]->(destino:Entity)
WITH gds.graph.project(
  'entidades',
  origem,
  destino,
  {},
  {undirectedRelationshipTypes: ['*']}
) AS g
RETURN g.graphName AS grafo, g.nodeCount AS nos, g.relationshipCount AS relacoes;
