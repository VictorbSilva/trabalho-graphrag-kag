"""Carga de data/semente/ no Neo4j com embeddings (src/recuperacao/carregar_semente.py).

Usa vetores falsos no lugar do modelo, para conferir só a carga: contagens,
embedding em todo trecho e que carregar duas vezes não duplica nada.
Precisa do Neo4j no ar.
"""

from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.embeddings import dimensoes_do_indice
from tests.recuperacao.conftest import PREFIXO


def vetores_falsos(textos):
    dim = dimensoes_do_indice()
    return [[1.0] + [0.0] * (dim - 1) for _ in textos]


def contar_nos(driver, rotulo: str) -> int:
    registros, _, _ = driver.execute_query(
        f"MATCH (n:{rotulo}) WHERE n.id STARTS WITH $p RETURN count(n) AS total",
        p=PREFIXO,
    )
    return registros[0]["total"]


def relacoes_de_dominio(driver) -> list[dict]:
    registros, _, _ = driver.execute_query(
        """
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE a.id STARTS WITH $p AND b.id STARTS WITH $p AND type(r) <> 'MENTIONS'
        RETURN size(r.source_chunk_ids) AS fontes
        """,
        p=PREFIXO,
    )
    return [r.data() for r in registros]


def test_conta_documentos_trechos_e_entidades(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert contar_nos(banco, "Document") == 4
    assert contar_nos(banco, "Chunk") == 12
    assert contar_nos(banco, "Entity") == 13


def test_relacoes_de_dominio_tem_trecho_de_origem(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    relacoes = relacoes_de_dominio(banco)
    assert len(relacoes) == 19
    assert all(r["fontes"] > 0 for r in relacoes)


def test_todo_trecho_tem_embedding_com_a_dimensao_do_indice(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    registros, _, _ = banco.execute_query(
        "MATCH (c:Chunk) WHERE c.id STARTS WITH $p RETURN size(c.embedding) AS dim",
        p=PREFIXO,
    )
    assert [r["dim"] for r in registros] == [dimensoes_do_indice()] * 12


def test_carregar_duas_vezes_nao_duplica(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert contar_nos(banco, "Entity") == 13
    assert len(relacoes_de_dominio(banco)) == 19


def test_retorna_as_contagens(banco):
    contagens = carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert contagens == {"documentos": 4, "trechos": 12, "entidades": 13, "relacoes": 19}
