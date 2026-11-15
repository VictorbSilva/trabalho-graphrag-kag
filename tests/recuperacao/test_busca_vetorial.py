"""Testes da busca vetorial top-k (issue V1). Precisam do Neo4j no ar."""

import pytest

from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.embeddings import dimensoes_do_indice
from tests.recuperacao.conftest import PREFIXO

CAMPOS = {"chunk_id", "trecho", "documento", "url", "score"}


def vetor_unitario(dim: int, posicao: int) -> list[float]:
    """Vetor que aponta só numa direção: fácil de prever na busca por cosseno."""
    v = [0.0] * dim
    v[posicao] = 1.0
    return v


@pytest.fixture
def chunks_de_teste(banco):
    dim = dimensoes_do_indice()
    chunks = [
        {"id": f"{PREFIXO}doc#{i}", "index": i, "text": f"Trecho de teste {i}.",
         "embedding": vetor_unitario(dim, i)}
        for i in range(3)
    ]
    banco.execute_query(
        """
        CREATE (d:Document {id: $doc, title: 'Documento de teste', source: 'https://exemplo.org/teste'})
        WITH d
        UNWIND $chunks AS ch
        CREATE (c:Chunk {id: ch.id, index: ch.index, text: ch.text, embedding: ch.embedding})
        CREATE (c)-[:PART_OF]->(d)
        """,
        doc=f"{PREFIXO}doc",
        chunks=chunks,
    )
    return banco, dim


def test_o_chunk_na_mesma_direcao_vem_primeiro(chunks_de_teste):
    banco, dim = chunks_de_teste
    resultados = buscar_chunks(banco, vetor_unitario(dim, 1), k=3)
    assert resultados[0]["chunk_id"] == f"{PREFIXO}doc#1"
    assert resultados[0]["score"] == pytest.approx(1.0, abs=1e-3)


def test_devolve_no_maximo_k_em_ordem_de_score(chunks_de_teste):
    banco, dim = chunks_de_teste
    resultados = buscar_chunks(banco, vetor_unitario(dim, 1), k=2)
    assert len(resultados) == 2
    scores = [r["score"] for r in resultados]
    assert scores == sorted(scores, reverse=True)


def test_resultado_traz_trecho_documento_e_url(chunks_de_teste):
    banco, dim = chunks_de_teste
    primeiro = buscar_chunks(banco, vetor_unitario(dim, 2), k=1)[0]
    assert set(primeiro) == CAMPOS
    assert primeiro["trecho"] == "Trecho de teste 2."
    assert primeiro["documento"] == "Documento de teste"
    assert primeiro["url"] == "https://exemplo.org/teste"


def test_k_menor_que_um_e_recusado(chunks_de_teste):
    banco, dim = chunks_de_teste
    with pytest.raises(ValueError):
        buscar_chunks(banco, vetor_unitario(dim, 0), k=0)