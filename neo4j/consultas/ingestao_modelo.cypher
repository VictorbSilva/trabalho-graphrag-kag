// Modelo de ingestão que respeita o schema (contrato com o pipeline do Patrick).
// Todas as escritas usam MERGE pelo id canônico, então rodar duas vezes
// com o mesmo documento não duplica nada (R14).
//
// Parâmetros esperados (um documento por vez):
//   $documento  {id, title, source}
//   $chunks     [{id, index, text, embedding}]
//   $entidades  [{id, name, type, aliases, description, chunk_ids}]
//   $relacoes   [{origem, destino, tipo, chunk_id}]
// type e tipo viram rótulo e tipo de relação: use PascalCase para type
// (ex.: Pessoa) e MAIUSCULAS_COM_UNDERSCORE para tipo (ex.: TRABALHA_EM).

// 1. Documento e trechos
MERGE (d:Document {id: $documento.id})
SET d.title = $documento.title, d.source = $documento.source
WITH d
UNWIND $chunks AS ch
MERGE (c:Chunk {id: ch.id})
SET c.text = ch.text, c.index = ch.index, c.embedding = ch.embedding
MERGE (c)-[:PART_OF]->(d);

// 2. Ordem dos trechos (permite expandir o contexto para o trecho vizinho)
MATCH (c:Chunk)-[:PART_OF]->(:Document {id: $documento.id})
WITH c ORDER BY c.index
WITH collect(c) AS cs
UNWIND range(0, size(cs) - 2) AS i
WITH cs[i] AS atual, cs[i + 1] AS proximo
MERGE (atual)-[:NEXT]->(proximo);

// 3. Entidades (id já canonicalizado pela resolução de entidades) e menções
UNWIND $entidades AS ent
MERGE (e:Entity {id: ent.id})
ON CREATE SET e.name = ent.name, e.type = ent.type
SET e:$(ent.type),
    e.aliases = apoc.coll.toSet(coalesce(e.aliases, []) + coalesce(ent.aliases, [])),
    e.description = coalesce(ent.description, e.description)
WITH e, ent
UNWIND ent.chunk_ids AS chunk_id
MATCH (c:Chunk {id: chunk_id})
MERGE (c)-[:MENTIONS]->(e);

// 4. Relações entre entidades, guardando de quais trechos cada uma saiu
UNWIND $relacoes AS rel
MATCH (a:Entity {id: rel.origem}), (b:Entity {id: rel.destino})
MERGE (a)-[r:$(rel.tipo)]->(b)
SET r.source_chunk_ids = apoc.coll.toSet(coalesce(r.source_chunk_ids, []) + [rel.chunk_id]);
