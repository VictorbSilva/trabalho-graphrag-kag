"""Grafo semente (data/semente/): formato, cobertura do domínio e caminho multi-hop.

Os testes de arquivo não precisam do banco. Os de banco ingerem a semente com
os ids prefixados por teste:: e apagam tudo no final.
"""

import re
from collections import deque

import pytest

from conftest import (
    PASTA_NEO4J,
    PREFIXO,
    carregar_cypher,
    carregar_dominio,
    carregar_semente,
    com_prefixo,
    id_canonico,
    ingerir,
)

SEMENTE = carregar_semente()
DOMINIO = carregar_dominio()
PREFIXO_POR_ROTULO = {r["nome"]: r["prefixo_id"] for r in DOMINIO["rotulos"]}
RELACOES = {r["tipo"]: r for r in DOMINIO["relacoes"]}


def todas_entidades() -> dict[str, dict]:
    return {e["id"]: e for artigo in SEMENTE.values() for e in artigo["entidades"]}


def relacoes_distintas() -> set[tuple[str, str, str]]:
    return {
        (r["origem"], r["tipo"], r["destino"])
        for artigo in SEMENTE.values()
        for r in artigo["relacoes"]
    }


def citado(entidade: dict, texto: str) -> bool:
    """O texto cita a entidade pelo nome, por um apelido ou, para pessoas, pelo sobrenome."""
    formas = [entidade["name"], *entidade["aliases"]]
    if entidade["type"] == "Pessoa":
        formas.append(entidade["name"].split()[-1])
    return any(
        re.search(rf"(?<!\w){re.escape(forma)}(?!\w)", texto, re.IGNORECASE) for forma in formas
    )


# ---------- Arquivos ----------

def test_tem_3_ou_4_artigos():
    assert 3 <= len(SEMENTE) <= 4


@pytest.mark.parametrize("nome", sorted(SEMENTE))
def test_arquivo_segue_o_contrato(nome):
    artigo = SEMENTE[nome]
    formato = DOMINIO["arquivo_por_artigo"]
    assert set(artigo) == {"documento", "chunks", "entidades", "relacoes"}
    assert set(artigo["documento"]) == set(formato["documento"])
    for chave in ("chunks", "entidades", "relacoes"):
        for item in artigo[chave]:
            assert set(item) == set(formato[chave]), f"{nome}: {chave} fora do formato"
    assert artigo["documento"]["source"].startswith("https://pt.wikipedia.org/wiki/")


@pytest.mark.parametrize("nome", sorted(SEMENTE))
def test_ids_seguem_a_regra(nome):
    artigo = SEMENTE[nome]
    doc_id = artigo["documento"]["id"]
    assert doc_id.startswith("wikipedia:")
    assert [c["index"] for c in artigo["chunks"]] == list(range(len(artigo["chunks"])))
    for c in artigo["chunks"]:
        assert c["id"] == f"{doc_id}#{c['index']}"
    for e in artigo["entidades"]:
        assert e["id"] == id_canonico(PREFIXO_POR_ROTULO[e["type"]], e["name"])


@pytest.mark.parametrize("nome", sorted(SEMENTE))
def test_referencias_internas_existem(nome):
    artigo = SEMENTE[nome]
    chunks = {c["id"] for c in artigo["chunks"]}
    entidades = {e["id"] for e in artigo["entidades"]}
    for e in artigo["entidades"]:
        assert set(e["chunk_ids"]) <= chunks, e["id"]
    for r in artigo["relacoes"]:
        assert r["origem"] in entidades and r["destino"] in entidades, r
        assert r["chunk_id"] in chunks, r


@pytest.mark.parametrize("nome", sorted(SEMENTE))
def test_tipos_e_direcoes_seguem_o_dominio(nome):
    artigo = SEMENTE[nome]
    tipo_de = {e["id"]: e["type"] for e in artigo["entidades"]}
    for e in artigo["entidades"]:
        assert e["type"] in PREFIXO_POR_ROTULO
    for r in artigo["relacoes"]:
        regra = RELACOES[r["tipo"]]
        assert tipo_de[r["origem"]] in regra["de"], f"{r} tem origem fora da direção do domínio"
        assert tipo_de[r["destino"]] in regra["para"], f"{r} tem destino fora da direção do domínio"


@pytest.mark.parametrize("nome", sorted(SEMENTE))
def test_trechos_citam_as_entidades_anotadas(nome):
    """Condição mínima para o trecho sustentar o fato: ele cita as duas pontas da relação."""
    artigo = SEMENTE[nome]
    texto = {c["id"]: c["text"] for c in artigo["chunks"]}
    ent = {e["id"]: e for e in artigo["entidades"]}
    for e in artigo["entidades"]:
        for chunk_id in e["chunk_ids"]:
            assert citado(e, texto[chunk_id]), f"{e['name']} não aparece em {chunk_id}"
    for r in artigo["relacoes"]:
        for ponta in (r["origem"], r["destino"]):
            assert citado(ent[ponta], texto[r["chunk_id"]]), f"{ponta} não aparece em {r['chunk_id']}"


def test_mesma_entidade_tem_os_mesmos_dados_em_todos_os_artigos():
    vistos: dict[str, tuple] = {}
    for artigo in SEMENTE.values():
        for e in artigo["entidades"]:
            dados = (e["name"], e["type"], tuple(e["aliases"]), e["description"])
            assert vistos.setdefault(e["id"], dados) == dados, e["id"]


def test_cobre_os_quatro_rotulos_e_as_cinco_relacoes():
    entidades = todas_entidades()
    relacoes = relacoes_distintas()
    assert len(entidades) >= 12
    assert len(relacoes) >= 15
    assert {e["type"] for e in entidades.values()} == set(PREFIXO_POR_ROTULO)
    assert {tipo for _, tipo, _ in relacoes} == set(RELACOES)


def test_existe_caminho_de_3_saltos_entre_artigos_diferentes():
    vizinhos: dict[str, set[str]] = {}
    for origem, _, destino in relacoes_distintas():
        vizinhos.setdefault(origem, set()).add(destino)
        vizinhos.setdefault(destino, set()).add(origem)
    inicio, fim = "tecnologia:c_plus_plus", "premio:premio_turing"
    distancia = {inicio: 0}
    fila = deque([inicio])
    while fila:
        atual = fila.popleft()
        for prox in vizinhos.get(atual, ()):
            if prox not in distancia:
                distancia[prox] = distancia[atual] + 1
                fila.append(prox)
    assert distancia.get(fim) == 3
    artigos_com = lambda eid: {n for n, a in SEMENTE.items() if eid in {e["id"] for e in a["entidades"]}}
    assert "c_plus_plus.json" in artigos_com(inicio)
    assert "c_plus_plus.json" not in artigos_com(fim)


# ---------- Banco ----------

@pytest.fixture
def semente_no_banco(banco):
    for artigo in SEMENTE.values():
        ingerir(banco, com_prefixo(artigo))
    return banco


def test_semente_ingerida_junta_entidades_repetidas(semente_no_banco):
    registros, _, _ = semente_no_banco.execute_query(
        """MATCH (e:Entity) WHERE e.id STARTS WITH $p
           OPTIONAL MATCH (e)-[r]->(:Entity)
           RETURN count(DISTINCT e) AS entidades, count(r) AS relacoes""",
        p=PREFIXO,
    )
    assert registros[0]["entidades"] == len(todas_entidades())
    assert registros[0]["relacoes"] == len(relacoes_distintas())


def test_relacao_repetida_guarda_trechos_dos_dois_artigos(semente_no_banco):
    registros, _, _ = semente_no_banco.execute_query(
        """MATCH (:Entity {id: $cpp})-[r:INFLUENCIADA_POR]->(:Entity {id: $c})
           RETURN r.source_chunk_ids AS fontes""",
        cpp=PREFIXO + "tecnologia:c_plus_plus", c=PREFIXO + "tecnologia:c",
    )
    fontes = {f.removeprefix(PREFIXO).split("#")[0] for f in registros[0]["fontes"]}
    assert fontes == {"wikipedia:c_plus_plus", "wikipedia:c_linguagem_de_programacao"}


def test_consulta_de_caminho_mais_curto_acha_3_saltos(semente_no_banco):
    """Critério da issue #4: a consulta 4 de exemplos.cypher acha o caminho entre artigos."""
    consulta = carregar_cypher(PASTA_NEO4J / "consultas" / "exemplos.cypher")[3]
    registros, _, _ = semente_no_banco.execute_query(
        consulta, origem=PREFIXO + "tecnologia:c_plus_plus", destino=PREFIXO + "premio:premio_turing"
    )
    assert registros[0]["saltos"] == 3
    assert registros[0]["nos"][0] == "C++" and registros[0]["nos"][-1] == "Prêmio Turing"


def test_caminho_cpp_c_ritchie_turing_existe(semente_no_banco):
    registros, _, _ = semente_no_banco.execute_query(
        """MATCH (:Entity {id: $cpp})-[:INFLUENCIADA_POR]->(c:Entity)<-[:CRIOU]-(p:Pessoa)
                 -[:RECEBEU]->(:Entity {id: $turing})
           RETURN c.name AS linguagem, p.name AS pessoa""",
        cpp=PREFIXO + "tecnologia:c_plus_plus", turing=PREFIXO + "premio:premio_turing",
    )
    assert {(r["linguagem"], r["pessoa"]) for r in registros} == {("C", "Dennis Ritchie")}
