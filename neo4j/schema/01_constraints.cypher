// R05 - Constraints de unicidade.
// Cada constraint de unicidade também cria um índice Range sobre a propriedade,
// então buscas por id já ficam indexadas.
//
// Observação (Neo4j Community): constraints de existência (IS NOT NULL),
// de tipo de propriedade e NODE KEY são exclusivas da edição Enterprise.
// Na Community, a obrigatoriedade de propriedades é garantida pela ingestão
// e verificada nos testes.

// Grafo léxico: documentos e trechos de texto
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Grafo de domínio: toda entidade tem o rótulo Entity + um rótulo do domínio.
// O id é a forma canônica gerada pela resolução de entidades (R12),
// por exemplo 'pessoa:maria_silva'. É o que impede nós duplicados.
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;
