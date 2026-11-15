"""Busca vetorial top-k nos trechos (issue V1)."""

from neo4j import RoutingControl

CONSULTA = """
CALL db.index.vector.queryNodes('chunk_embedding', $k, $embedding) YIELD node, score
MATCH (node)-[:PART_OF]->(d:Document)
RETURN node.id AS chunk_id, node.text AS trecho, d.title AS documento,
       d.source AS url, score
ORDER BY score DESC
"""


def buscar_chunks(driver, embedding: list[float], k: int = 5) -> list[dict]:
    """Os k trechos mais parecidos com o embedding, do mais para o menos parecido."""
    if k < 1:
        raise ValueError("k precisa ser pelo menos 1.")
    registros, _, _ = driver.execute_query(
        CONSULTA, embedding=embedding, k=k, routing_=RoutingControl.READ
    )
    return [registro.data() for registro in registros]