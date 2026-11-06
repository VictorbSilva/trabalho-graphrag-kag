"""Fixtures compartilhadas pelos testes do banco.

Os testes usam o Neo4j do docker-compose (precisa estar rodando) e só criam
nós cujo id começa com PREFIXO, que são apagados no início e no fim de cada teste.
Os dados reais do banco não são alterados (exceto pagerank/community, que o
próprio script do GDS recalcula).
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

RAIZ = Path(__file__).resolve().parents[2]
PASTA_NEO4J = RAIZ / "neo4j"
PREFIXO = "teste::"

load_dotenv(RAIZ / ".env")


def carregar_cypher(caminho: Path) -> list[str]:
    """Lê um arquivo .cypher e devolve a lista de comandos (sem comentários)."""
    linhas = [
        linha
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if not linha.strip().startswith("//")
    ]
    return [cmd.strip() for cmd in "\n".join(linhas).split(";") if cmd.strip()]


def limpar_dados_de_teste(driver) -> None:
    for rotulo in ("Entity", "Chunk", "Document"):
        driver.execute_query(
            f"MATCH (n:{rotulo}) WHERE n.id STARTS WITH $p DETACH DELETE n",
            p=PREFIXO,
        )


def dimensao_vetorial(driver, indice: str) -> int:
    registros, _, _ = driver.execute_query(
        "SHOW INDEXES YIELD name, options WHERE name = $nome RETURN options",
        nome=indice,
    )
    return registros[0]["options"]["indexConfig"]["vector.dimensions"]


def vetor_base(dim: int, posicao: int, ruido: float = 0.0) -> list[float]:
    """Vetor quase unitário na direção `posicao` (fácil de prever na busca por cosseno)."""
    v = [ruido] * dim
    v[posicao] = 1.0
    return v


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
    """Driver com os dados de teste limpos antes e depois do teste."""
    limpar_dados_de_teste(driver)
    yield driver
    limpar_dados_de_teste(driver)


def ingerir(driver, payload: dict) -> None:
    """Roda o modelo de ingestão (neo4j/consultas/ingestao_modelo.cypher) com um documento."""
    for comando in carregar_cypher(PASTA_NEO4J / "consultas" / "ingestao_modelo.cypher"):
        driver.execute_query(comando, payload)


def payload_exemplo(dim: int) -> dict:
    """Mini-documento: Maria trabalha na Acme, sediada em Recife, onde João mora.

    Maria e João só se conectam com 3 saltos (Maria -> Acme -> Recife <- João).
    """
    p = PREFIXO
    return {
        "documento": {"id": f"{p}doc1", "title": "Documento de teste", "source": "testes"},
        "chunks": [
            {"id": f"{p}doc1#0", "index": 0, "text": "Maria Silva trabalha na Acme.",
             "embedding": vetor_base(dim, 0, 0.01)},
            {"id": f"{p}doc1#1", "index": 1, "text": "A Acme tem sede em Recife.",
             "embedding": vetor_base(dim, 1, 0.01)},
            {"id": f"{p}doc1#2", "index": 2, "text": "João mora em Recife.",
             "embedding": vetor_base(dim, 2, 0.01)},
        ],
        "entidades": [
            {"id": f"{p}pessoa:maria_silva", "name": "Maria Silva", "type": "Pessoa",
             "aliases": ["M. Silva"], "description": "Engenheira", "chunk_ids": [f"{p}doc1#0"]},
            {"id": f"{p}organizacao:acme", "name": "Acme", "type": "Organizacao",
             "aliases": [], "description": None, "chunk_ids": [f"{p}doc1#0", f"{p}doc1#1"]},
            {"id": f"{p}cidade:recife", "name": "Recife", "type": "Cidade",
             "aliases": [], "description": None, "chunk_ids": [f"{p}doc1#1", f"{p}doc1#2"]},
            {"id": f"{p}pessoa:joao", "name": "João", "type": "Pessoa",
             "aliases": [], "description": None, "chunk_ids": [f"{p}doc1#2"]},
        ],
        "relacoes": [
            {"origem": f"{p}pessoa:maria_silva", "destino": f"{p}organizacao:acme",
             "tipo": "TRABALHA_EM", "chunk_id": f"{p}doc1#0"},
            {"origem": f"{p}organizacao:acme", "destino": f"{p}cidade:recife",
             "tipo": "SEDIADA_EM", "chunk_id": f"{p}doc1#1"},
            {"origem": f"{p}pessoa:joao", "destino": f"{p}cidade:recife",
             "tipo": "MORA_EM", "chunk_id": f"{p}doc1#2"},
        ],
    }


@pytest.fixture
def grafo_exemplo(banco):
    """Banco com o mini-documento de teste já ingerido. Devolve (driver, payload)."""
    payload = payload_exemplo(dimensao_vetorial(banco, "chunk_embedding"))
    ingerir(banco, payload)
    return banco, payload
