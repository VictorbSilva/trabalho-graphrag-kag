"""Expansão multi-hop a partir dos trechos da busca vetorial (src/recuperacao/multi_hop.py).

Usa a semente carregada com vetores falsos: a expansão parte dos trechos e não
depende do embedding. Precisa do Neo4j no ar, menos o teste de max_saltos inválido.
"""

import json

import pytest

from src.contrato import Caminho, No, Subgrafo
from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.multi_hop import (
    FRASES_DAS_RELACOES,
    RELACOES_DO_DOMINIO,
    expandir,
    montar_grafo,
    verbalizar_caminho,
)
from tests.recuperacao.conftest import PREFIXO, RAIZ
from tests.recuperacao.test_carregar_semente import vetores_falsos

P = PREFIXO
TIPOS_DO_DOMINIO = {
    r["tipo"]
    for r in json.loads((RAIZ / "neo4j" / "dominio.json").read_text(encoding="utf-8"))["relacoes"]
}


@pytest.fixture
def semente(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    return banco


def todos_os_trechos(driver) -> list[str]:
    registros, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.id STARTS WITH $p RETURN c.id AS id ORDER BY id", p=PREFIXO
    )
    return [r["id"] for r in registros]


def chave(caminho: dict) -> frozenset:
    return frozenset((a["origem"], a["tipo"], a["destino"]) for a in caminho["arestas"])


@pytest.mark.parametrize(
    ("chunk", "extremo_a", "extremo_b", "saltos"),
    [
        ("c_mais_mais#0", "tecnologia:c_mais_mais", "premio:premio_turing", 3),
        ("ken_thompson#0", "tecnologia:unix", "premio:premio_turing", 2),
        ("c#1", "tecnologia:c", "tecnologia:bcpl", 2),
        ("c_mais_mais#1", "tecnologia:simula", "pessoa:bjarne_stroustrup", 2),
        ("dennis_ritchie#2", "organizacao:lucent_technologies", "organizacao:bell_labs", 2),
    ],
)
def test_chega_ao_extremo_esperado(semente, chunk, extremo_a, extremo_b, saltos):
    caminhos = expandir(semente, [P + chunk], limite=1000)
    esperado = {P + extremo_a, P + extremo_b}
    assert any(
        {c["nos"][0]["id"], c["nos"][-1]["id"]} == esperado and len(c["arestas"]) == saltos
        for c in caminhos
    )


def test_so_anda_por_relacoes_do_dominio_com_fontes(semente):
    caminhos = expandir(semente, todos_os_trechos(semente), limite=1000)
    assert caminhos
    for caminho in caminhos:
        for aresta in caminho["arestas"]:
            assert aresta["tipo"] in TIPOS_DO_DOMINIO
            assert aresta["fontes"]


def test_max_saltos_1_devolve_so_caminhos_de_uma_aresta(semente):
    caminhos = expandir(semente, todos_os_trechos(semente), max_saltos=1, limite=1000)
    assert caminhos
    assert all(len(c["arestas"]) == 1 for c in caminhos)


def test_respeita_o_limite(semente):
    assert len(expandir(semente, todos_os_trechos(semente), limite=3)) <= 3


def test_nao_repete_o_mesmo_conjunto_de_arestas(semente):
    caminhos = expandir(semente, todos_os_trechos(semente), limite=1000)
    chaves = [chave(c) for c in caminhos]
    assert len(chaves) == len(set(chaves))


def test_sem_trechos_devolve_lista_vazia(banco):
    assert expandir(banco, []) == []


def test_montar_grafo_segue_o_contrato(semente):
    caminhos = expandir(semente, [P + "c_mais_mais#0"], limite=1000)
    assert caminhos
    caminhos_contrato, subgrafo, nos_consultados = montar_grafo(caminhos)

    assert [c["id"] for c in caminhos_contrato] == [f"C{i}" for i in range(1, len(caminhos) + 1)]
    ids_do_subgrafo = {n["id"] for n in subgrafo["nos"]}
    for bruto, contrato in zip(caminhos, caminhos_contrato):
        assert set(contrato["nos"]) <= ids_do_subgrafo
        uniao = sorted({f for a in bruto["arestas"] for f in a["fontes"]})
        assert contrato["fontes"] == uniao
        Caminho.model_validate(contrato)

    Subgrafo.model_validate(subgrafo)
    for no in subgrafo["nos"]:
        No.model_validate(no)
    assert nos_consultados == [n["id"] for n in subgrafo["nos"]]


@pytest.mark.parametrize("max_saltos", [0, 4])
def test_max_saltos_fora_de_1_a_3_e_recusado(max_saltos):
    with pytest.raises(ValueError):
        expandir(object(), [P + "c#0"], max_saltos=max_saltos)


def test_toda_relacao_do_dominio_tem_frase():
    assert set(FRASES_DAS_RELACOES) == set(RELACOES_DO_DOMINIO)


def test_verbaliza_cada_aresta_de_origem_para_destino():
    caminho = {
        "nos": [
            {"id": "tecnologia:c_mais_mais", "nome": "C++"},
            {"id": "tecnologia:c", "nome": "C"},
            {"id": "pessoa:dennis_ritchie", "nome": "Dennis Ritchie"},
        ],
        "arestas": [
            {"origem": "tecnologia:c_mais_mais", "destino": "tecnologia:c", "tipo": "INFLUENCIADA_POR"},
            {"origem": "pessoa:dennis_ritchie", "destino": "tecnologia:c", "tipo": "CRIOU"},
        ],
    }
    assert verbalizar_caminho(caminho) == "C++ foi influenciada por C; Dennis Ritchie criou C"


def vetores_por_palavra(textos):
    return [[1.0, 0.0] if "Prêmio Turing" in t else [0.0, 1.0] for t in textos]


def test_com_pergunta_ordena_pela_semelhanca_com_o_caminho(semente):
    caminhos = expandir(
        semente, [P + "c#2"], limite=3, pergunta="Prêmio Turing", gerar_vetores=vetores_por_palavra
    )
    assert len(caminhos) == 3
    for caminho in caminhos:
        assert P + "premio:premio_turing" in {n["id"] for n in caminho["nos"]}


def test_corte_da_consulta_fica_com_os_trechos_de_maior_score(semente):
    caminhos = expandir(
        semente,
        [P + "c#0", P + "c#2"],
        limite=1000,
        limite_consulta=10,
        scores={P + "c#2": 0.9, P + "c#0": 0.1},
    )
    assert caminhos
    assert all(c["chunk_origem"] == P + "c#2" for c in caminhos)
