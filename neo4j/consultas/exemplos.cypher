// Catálogo de consultas de referência sobre o schema base.
// Ponto de partida para a recuperação híbrida (Victor) e para testar o modelo.
// Parâmetros usados: $termo, $embedding, $k, $origem, $destino.
// Não é executado automaticamente. Os testes validam a sintaxe e rodam cada
// consulta sobre um mini-grafo de exemplo (tests/neo4j/test_ingestao_e_consultas.py).
//
// Multi-hop: no Neo4j 5 o filtro de tipo com ! (ex.: :!MENTIONS) não funciona
// em [*1..4]. Use o padrão quantificado (()-[:!MENTIONS]-()){1,4}, como abaixo.

// 1. Busca por palavra-chave nas entidades (índice fulltext entity_search)
CALL db.index.fulltext.queryNodes('entity_search', $termo) YIELD node, score
RETURN node.id AS id, node.name AS nome, node.type AS tipo, score
ORDER BY score DESC
LIMIT 10;

// 2. Busca vetorial nos trechos de texto (cosseno, índice chunk_embedding)
CALL db.index.vector.queryNodes('chunk_embedding', $k, $embedding) YIELD node, score
MATCH (node)-[:PART_OF]->(d:Document)
RETURN node.id AS chunk, node.text AS texto, d.title AS documento, score
ORDER BY score DESC;

// 3. Híbrida: trechos similares, entidades citadas neles e vizinhança de até 2 saltos
CALL db.index.vector.queryNodes('chunk_embedding', $k, $embedding) YIELD node AS chunk, score
MATCH (chunk)-[:MENTIONS]->(e:Entity)
OPTIONAL MATCH caminho = (e)(()-[:!MENTIONS]-()){1,2}(vizinho:Entity)
RETURN chunk.id AS chunk, score, e.name AS entidade,
       [n IN nodes(caminho) | n.name] AS caminho_nos,
       [r IN relationships(caminho) | type(r)] AS caminho_relacoes
ORDER BY score DESC, e.pagerank DESC
LIMIT 50;

// 4. Caminho mais curto entre duas entidades (só por relações de domínio, até 4 saltos)
MATCH p = SHORTEST 1 (a:Entity {id: $origem})(()-[:!MENTIONS]-()){1,4}(b:Entity {id: $destino})
RETURN [n IN nodes(p) | n.name] AS nos, [r IN relationships(p) | type(r)] AS relacoes, length(p) AS saltos;

// 5. Procedência de uma relação: de quais trechos e documentos ela foi extraída
MATCH (a:Entity {id: $origem})-[r]-(b:Entity {id: $destino})
UNWIND r.source_chunk_ids AS chunk_id
MATCH (c:Chunk {id: chunk_id})-[:PART_OF]->(d:Document)
RETURN type(r) AS relacao, c.text AS trecho, d.title AS documento, d.source AS fonte;

// 6. Entidades mais importantes de cada comunidade (precisa ter rodado o GDS)
MATCH (e:Entity)
WHERE e.community IS NOT NULL
WITH e.community AS comunidade, e
ORDER BY e.pagerank DESC
WITH comunidade, count(e) AS tamanho, collect(e.name)[..5] AS principais
RETURN comunidade, tamanho, principais
ORDER BY tamanho DESC;
