"""Configuração comum da suíte (issue #30, PE4).

`python -m pytest` na raiz roda todos os módulos. Os testes que dependem de serviço
externo ficam marcados e podem ser rodados à parte:

    python -m pytest -m neo4j               só os que precisam do Neo4j no ar
    python -m pytest -m llm                 só os que precisam de chave de LLM
    python -m pytest -m "not neo4j and not llm"   só os que rodam em qualquer máquina (CI)

Todo teste que usa a fixture `driver` (direta ou indiretamente, como `banco` e
`grafo_exemplo` de tests/neo4j/conftest.py) recebe o marcador `neo4j`
automaticamente. Testes de tests/neo4j/ que não abrem conexão (ex.: os que só leem
neo4j/dominio.json ou data/semente/) rodam em qualquer máquina e no CI. Se o Neo4j
não estiver acessível, esses testes são pulados com o motivo no resumo, em vez de
derrubar a suíte inteira. Para exigir o banco (falhar em vez de pular), use
EXIGIR_NEO4J=1.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE_DO_BANCO = "driver"

load_dotenv(RAIZ / ".env")


def _motivo_neo4j_indisponivel() -> str | None:
    """Devolve por que o Neo4j não pode ser usado, ou None se ele estiver acessível."""
    senha = os.getenv("NEO4J_PASSWORD")
    if not senha:
        return "NEO4J_PASSWORD não definida no .env"
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    try:
        from neo4j import GraphDatabase

        with GraphDatabase.driver(uri, auth=("neo4j", senha), connection_timeout=3) as drv:
            drv.verify_connectivity()
    except Exception as erro:  # banco fora do ar, senha errada, driver ausente...
        return f"Neo4j inacessível em {uri} ({type(erro).__name__})"
    return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        # fixturenames inclui as fixtures indiretas (banco -> driver).
        if FIXTURE_DO_BANCO in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.neo4j)

    selecionados = [item for item in items if item.get_closest_marker("neo4j")]
    if not selecionados or os.getenv("EXIGIR_NEO4J") == "1":
        return

    motivo = _motivo_neo4j_indisponivel()
    if motivo:
        pular = pytest.mark.skip(reason=f"{motivo}. Suba o banco com 'docker compose up -d'.")
        for item in selecionados:
            item.add_marker(pular)
