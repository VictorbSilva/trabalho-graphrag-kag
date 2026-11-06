"""R05 a R09: o schema aplicado pelo docker compose está completo e funcionando."""

import pytest
from neo4j.exceptions import ConstraintError

from conftest import PREFIXO

CONSTRAINTS = {"document_id_unique", "chunk_id_unique", "entity_id_unique"}

INDICES = {
    # R06 - Range
    "entity_name", "entity_type", "entity_pagerank", "entity_community", "document_source",
    # R07 - Fulltext
    "entity_search", "chunk_text",
    # R08 - Vector
    "chunk_embedding", "entity_embedding",
}


def test_constraints_de_unicidade_existem(driver):
    registros, _, _ = driver.execute_query("SHOW CONSTRAINTS YIELD name RETURN collect(name) AS nomes")
    faltando = CONSTRAINTS - set(registros[0]["nomes"])
    assert not faltando, f"Constraints faltando: {faltando}"


def test_indices_existem_e_estao_online(driver):
    registros, _, _ = driver.execute_query("SHOW INDEXES YIELD name, state RETURN name, state")
    estados = {r["name"]: r["state"] for r in registros}
    faltando = INDICES - estados.keys()
    assert not faltando, f"Índices faltando: {faltando}"
    fora_do_ar = {n: estados[n] for n in INDICES if estados[n] != "ONLINE"}
    assert not fora_do_ar, f"Índices que não estão ONLINE: {fora_do_ar}"


def test_indices_vetoriais_usam_cosseno_e_mesma_dimensao(driver):
    registros, _, _ = driver.execute_query(
        "SHOW VECTOR INDEXES YIELD name, options RETURN name, options.indexConfig AS cfg"
    )
    configs = {r["name"]: r["cfg"] for r in registros}
    for nome in ("chunk_embedding", "entity_embedding"):
        assert configs[nome]["vector.similarity_function"].lower() == "cosine"
    assert configs["chunk_embedding"]["vector.dimensions"] == configs["entity_embedding"]["vector.dimensions"]


def test_unicidade_impede_entidade_duplicada(banco):
    entidade_id = f"{PREFIXO}pessoa:maria_silva"
    banco.execute_query("CREATE (:Entity {id: $id, name: 'Maria Silva'})", id=entidade_id)
    with pytest.raises(ConstraintError):
        banco.execute_query("CREATE (:Entity {id: $id, name: 'Maria S.'})", id=entidade_id)


@pytest.mark.parametrize("rotulo", ["Document", "Chunk"])
def test_unicidade_vale_para_documentos_e_trechos(banco, rotulo):
    no_id = f"{PREFIXO}{rotulo.lower()}-1"
    banco.execute_query(f"CREATE (:{rotulo} {{id: $id}})", id=no_id)
    with pytest.raises(ConstraintError):
        banco.execute_query(f"CREATE (:{rotulo} {{id: $id}})", id=no_id)


def test_plugins_apoc_e_gds_instalados(driver):
    registros, _, _ = driver.execute_query("RETURN apoc.version() AS apoc, gds.version() AS gds")
    assert registros[0]["apoc"]
    assert registros[0]["gds"]
