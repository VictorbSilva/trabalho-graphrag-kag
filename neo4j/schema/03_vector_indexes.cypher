// R08 - Índices vetoriais para os embeddings (busca por similaridade de cosseno).
//
// 384 dimensões: decisão do grupo (issue #3). vector.dimensions precisa ser
// igual ao tamanho do vetor gerado pelo módulo único de embeddings (V1).
// Se o modelo mudar depois de criado o índice, apague os dois índices
// (DROP INDEX chunk_embedding e DROP INDEX entity_embedding), ajuste aqui
// e rode o schema de novo (ver neo4j/README.md).
//
// entity_embedding fica criado, mas vazio nesta entrega: por enquanto só
// os trechos (Chunk) recebem embedding.

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};
