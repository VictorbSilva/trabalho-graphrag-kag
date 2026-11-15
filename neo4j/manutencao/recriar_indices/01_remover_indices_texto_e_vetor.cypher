// Remove os índices fulltext e vetoriais para que o schema os recrie com a
// configuração atual (analyzer e dimensões). Constraints e índices Range
// não são tocados, e nenhum nó é apagado.
// Uso: docker compose run --rm neo4j-recriar-indices

DROP INDEX entity_search IF EXISTS;
DROP INDEX chunk_text IF EXISTS;
DROP INDEX chunk_embedding IF EXISTS;
DROP INDEX entity_embedding IF EXISTS;
