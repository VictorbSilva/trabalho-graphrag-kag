"""Modelo de ingestão, consultas de referência, GDS e proteção contra escrita."""

import pytest
from neo4j.exceptions import Neo4jError

from conftest import (
    PASTA_NEO4J,
    PREFIXO,
    carregar_cypher,
    dimensao_vetorial,
    ingerir,
    vetor_base,
)


def contar(driver, rotulo: str) -> int:
    registros, _, _ = driver.execute_query(
        f"MATCH (n:{rotulo}) WHERE n.id STARTS WITH $p RETURN count(n) AS total", p=PREFIXO
    )
    return registros[0]["total"]


def contar_relacoes(driver) -> int:
    registros, _, _ = driver.execute_query(
        "MATCH (n)-[r]->() WHERE (n:Chunk OR n:Entity) AND n.id STARTS WITH $p RETURN count(r) AS total",
        p=PREFIXO,
    )
    return registros[0]["total"]


def consulta_exemplo(numero: int) -> str:
    return carregar_cypher(PASTA_NEO4J / "consultas" / "exemplos.cypher")[numero - 1]


# ---------- Ingestão (R12, R14) ----------

def test_ingestao_cria_o_grafo_esperado(grafo_exemplo):
    driver, _ = grafo_exemplo
    assert contar(driver, "Document") == 1
    assert contar(driver, "Chunk") == 3
    assert contar(driver, "Entity") == 4
    # 3 PART_OF + 2 NEXT + 6 MENTIONS + 3 relações de domínio
    assert contar_relacoes(driver) == 14


def test_ingestao_adiciona_rotulo_do_dominio(grafo_exemplo):
    driver, _ = grafo_exemplo
    registros, _, _ = driver.execute_query(
        "MATCH (e:Entity {id: $id}) RETURN labels(e) AS rotulos", id=f"{PREFIXO}pessoa:maria_silva"
    )
    assert set(registros[0]["rotulos"]) == {"Entity", "Pessoa"}


def test_ingestao_e_idempotente(grafo_exemplo):
    driver, payload = grafo_exemplo
    ingerir(driver, payload)  # segunda vez com o mesmo documento
    assert contar(driver, "Entity") == 4
    assert contar(driver, "Chunk") == 3
    assert contar_relacoes(driver) == 14


def test_mesma_entidade_em_outro_documento_vira_um_no_so(grafo_exemplo):
    driver, payload = grafo_exemplo
    p = PREFIXO
    dim = len(payload["chunks"][0]["embedding"])
    ingerir(driver, {
        "documento": {"id": f"{p}doc2", "title": "Outro documento", "source": "testes"},
        "chunks": [{"id": f"{p}doc2#0", "index": 0, "text": "Maria S. lidera a Acme.",
                    "embedding": vetor_base(dim, 3, 0.01)}],
        "entidades": [
            # a resolução de entidades já mapeou "Maria S." para o mesmo id canônico
            {"id": f"{p}pessoa:maria_silva", "name": "Maria S.", "type": "Pessoa",
             "aliases": ["Maria S."], "description": None, "chunk_ids": [f"{p}doc2#0"]},
            {"id": f"{p}organizacao:acme", "name": "Acme", "type": "Organizacao",
             "aliases": [], "description": None, "chunk_ids": [f"{p}doc2#0"]},
        ],
        "relacoes": [{"origem": f"{p}pessoa:maria_silva", "destino": f"{p}organizacao:acme",
                      "tipo": "TRABALHA_EM", "chunk_id": f"{p}doc2#0"}],
    })
    registros, _, _ = driver.execute_query(
        """MATCH (e:Entity {id: $id})-[r:TRABALHA_EM]->()
           RETURN e.name AS nome, e.aliases AS aliases, r.source_chunk_ids AS fontes""",
        id=f"{p}pessoa:maria_silva",
    )
    assert len(registros) == 1, "a relação TRABALHA_EM não pode duplicar"
    maria = registros[0]
    assert maria["nome"] == "Maria Silva", "o nome original é mantido"
    assert set(maria["aliases"]) == {"M. Silva", "Maria S."}
    assert set(maria["fontes"]) == {f"{p}doc1#0", f"{p}doc2#0"}
    assert contar(driver, "Entity") == 4


# ---------- Consultas de referência (neo4j/consultas/exemplos.cypher) ----------

def test_consultas_de_exemplo_sao_validas(driver):
    dim = dimensao_vetorial(driver, "chunk_embedding")
    params = {"termo": "x", "embedding": [0.1] * dim, "k": 5, "origem": "a", "destino": "b"}
    consultas = carregar_cypher(PASTA_NEO4J / "consultas" / "exemplos.cypher")
    assert len(consultas) == 6
    for consulta in consultas:
        driver.execute_query("EXPLAIN " + consulta, params)


def test_fulltext_encontra_entidade_pelo_apelido(grafo_exemplo):
    driver, _ = grafo_exemplo
    registros, _, _ = driver.execute_query(consulta_exemplo(1), termo='"M. Silva"')
    ids = [r["id"] for r in registros]
    assert ids and ids[0] == f"{PREFIXO}pessoa:maria_silva"


def test_busca_vetorial_retorna_trecho_mais_parecido(grafo_exemplo):
    driver, payload = grafo_exemplo
    dim = len(payload["chunks"][0]["embedding"])
    pergunta = vetor_base(dim, 1, 0.02)  # próxima do trecho 1 ("A Acme tem sede em Recife.")
    registros, _, _ = driver.execute_query(consulta_exemplo(2), embedding=pergunta, k=3)
    assert registros[0]["chunk"] == f"{PREFIXO}doc1#1"
    assert registros[0]["documento"] == "Documento de teste"


def test_busca_hibrida_alcanca_entidade_a_dois_saltos(grafo_exemplo):
    driver, payload = grafo_exemplo
    dim = len(payload["chunks"][0]["embedding"])
    pergunta = vetor_base(dim, 0, 0.02)  # trecho 0 só cita Maria e Acme
    registros, _, _ = driver.execute_query(consulta_exemplo(3), embedding=pergunta, k=1)
    alcancados = {nome for r in registros for nome in (r["caminho_nos"] or [])}
    assert "João" in alcancados, "Maria -> Acme -> Recife <- João precisa aparecer na expansão"


def test_caminho_mais_curto_e_multi_hop(grafo_exemplo):
    driver, _ = grafo_exemplo
    registros, _, _ = driver.execute_query(
        consulta_exemplo(4), origem=f"{PREFIXO}pessoa:maria_silva", destino=f"{PREFIXO}pessoa:joao"
    )
    assert registros[0]["saltos"] == 3
    assert registros[0]["nos"] == ["Maria Silva", "Acme", "Recife", "João"]
    assert registros[0]["relacoes"] == ["TRABALHA_EM", "SEDIADA_EM", "MORA_EM"]


def test_procedencia_da_relacao_aponta_o_trecho_de_origem(grafo_exemplo):
    driver, _ = grafo_exemplo
    registros, _, _ = driver.execute_query(
        consulta_exemplo(5), origem=f"{PREFIXO}organizacao:acme", destino=f"{PREFIXO}cidade:recife"
    )
    assert [(r["relacao"], r["trecho"]) for r in registros] == [("SEDIADA_EM", "A Acme tem sede em Recife.")]


# ---------- GDS (R20) ----------

def test_scripts_do_gds_gravam_pagerank_e_comunidade(grafo_exemplo):
    driver, _ = grafo_exemplo
    for arquivo in sorted((PASTA_NEO4J / "gds").glob("*.cypher")):
        for comando in carregar_cypher(arquivo):
            driver.execute_query(comando)

    registros, _, _ = driver.execute_query(
        """MATCH (e:Entity) WHERE e.id STARTS WITH $p
           RETURN e.name AS nome, e.pagerank AS pagerank, e.community AS comunidade
           ORDER BY pagerank DESC""",
        p=PREFIXO,
    )
    assert all(r["pagerank"] is not None and r["comunidade"] is not None for r in registros)
    # Recife (2 conexões) e Acme (2 conexões) são mais centrais que Maria e João (1 conexão)
    assert {registros[0]["nome"], registros[1]["nome"]} == {"Recife", "Acme"}

    # a projeção em memória foi removida no final
    existe, _, _ = driver.execute_query("CALL gds.graph.exists('entidades') YIELD exists RETURN exists")
    assert existe[0]["exists"] is False

    registros, _, _ = driver.execute_query(consulta_exemplo(6))
    assert registros, "consulta de comunidades deve retornar resultado depois do GDS"


# ---------- Segurança para o Text-to-Cypher ----------

def test_transacao_de_leitura_recusa_escrita(banco):
    """Consultas geradas pelo LLM devem rodar assim: o banco bloqueia CREATE/MERGE/DELETE."""
    with banco.session() as sessao:
        with pytest.raises(Neo4jError) as erro:
            sessao.execute_read(
                lambda tx: tx.run("CREATE (:Entity {id: $id})", id=f"{PREFIXO}intruso").consume()
            )
    assert "AccessMode" in (erro.value.code or "")
    assert contar(banco, "Entity") == 0
