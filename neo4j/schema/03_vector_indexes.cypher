// R08 - Índices vetoriais para os embeddings (busca por similaridade de cosseno).
//
// ATENÇÃO: vector.dimensions precisa ser igual ao tamanho do vetor gerado
// pelo modelo de embeddings escolhido pela equipe. Exemplos:
//   OpenAI text-embedding-3-small ........ 1536
//   Ollama nomic-embed-text ............... 768
//   sentence-transformers all-MiniLM-L6-v2  384
// Se o modelo mudar depois de criado o índice:
//   DROP INDEX chunk_embedding  (e entity_embedding), ajuste aqui e rode de novo.

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
