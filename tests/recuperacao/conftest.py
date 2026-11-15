"""Fixtures dos testes da recuperação que usam o Neo4j."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

RAIZ = Path(__file__).resolve().parents[2]
PREFIXO = "teste_rec::"

load_dotenv(RAIZ / ".env")


def limpar_dados_de_teste(driver) -> None:
    for rotulo in ("Entity", "Chunk", "Document"):
        driver.execute_query(
            f"MATCH (n:{rotulo}) WHERE n.id STARTS WITH $p DETACH DELETE n",
            p=PREFIXO,
        )


@pytest.fixture(scope="session")
def driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    senha = os.environ.get("NEO4J_PASSWORD")
    if not senha:
        pytest.exit("Defina NEO4J_PASSWORD no arquivo .env antes de rodar os testes.")
    drv = GraphDatabase.driver(uri, auth=("neo4j", senha))
    drv.verify_connectivity()
    yield drv
    drv.close()


@pytest.fixture
def banco(driver):
    """Driver com os dados de teste limpos antes e depois de cada teste."""
    limpar_dados_de_teste(driver)
    yield driver
    limpar_dados_de_teste(driver)