// R06 - Índices Range (no Neo4j 5 o índice BTree foi substituído pelo Range).
CREATE RANGE INDEX entity_name IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE RANGE INDEX entity_type IF NOT EXISTS
FOR (e:Entity) ON (e.type);

// Preenchidos pelos algoritmos do GDS (pasta neo4j/gds).
CREATE RANGE INDEX entity_pagerank IF NOT EXISTS
FOR (e:Entity) ON (e.pagerank);

CREATE RANGE INDEX entity_community IF NOT EXISTS
FOR (e:Entity) ON (e.community);

CREATE RANGE INDEX document_source IF NOT EXISTS
FOR (d:Document) ON (d.source);

// R07 - Índices Fulltext (busca por palavra-chave, com tolerância a variações).
// Se o dataset for em português, troque o analyzer para 'brazilian'
// (melhora o stemming). Para mudar, é preciso DROP INDEX e criar de novo.
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.aliases, e.description];

CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.text];
