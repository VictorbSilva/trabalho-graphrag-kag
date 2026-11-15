"""Conexão com o Neo4j do docker-compose, lida do .env."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

RAIZ = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def obter_driver():
    """Driver do Neo4j (um só por processo), com NEO4J_URI e NEO4J_PASSWORD do .env."""
    load_dotenv(RAIZ / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    senha = os.getenv("NEO4J_PASSWORD")
    if not senha:
        raise RuntimeError(
            "NEO4J_PASSWORD não definida. Copie .env.example para .env e preencha a senha do Neo4j."
        )
    return GraphDatabase.driver(uri, auth=("neo4j", senha))
