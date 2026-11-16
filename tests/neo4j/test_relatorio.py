"""Relatório de validação do grafo (src/banco/relatorio.py, issue #13).

Carrega a semente com ids prefixados por teste:: e vetores falsos e confere os
números do relatório contra os próprios arquivos da semente.
"""

from collections import Counter
from datetime import date

import pytest

from conftest import PREFIXO, PASTA_SEMENTE, carregar_semente
from src.banco.ingestor import carregar_dominio, ingerir_pasta
from src.banco.relatorio import coletar, gerar_markdown, possiveis_duplicatas

DIMENSOES = carregar_dominio()["embedding"]["dimensoes"]


def vetores_falsos(textos):
    return [[1.0] + [0.0] * (DIMENSOES - 1) for _ in textos]


@pytest.fixture
def semente_no_banco(banco):
    ingerir_pasta(banco, PASTA_SEMENTE, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    return banco


def esperado_da_semente():
    entidades = {e["id"]: e for a in carregar_semente().values() for e in a["entidades"]}
    relacoes = {(r["origem"], r["tipo"], r["destino"]) for a in carregar_semente().values() for r in a["relacoes"]}
    return (
        Counter(e["type"] for e in entidades.values()),
        Counter(tipo for _, tipo, _ in relacoes),
    )


# ---------- Sem banco ----------

def test_duplicatas_por_apelido_e_por_nome_contido():
    entidades = [
        {"nome": "Bell Labs", "tipo": "Organizacao", "aliases": ["AT&T Bell Labs"]},
        {"nome": "AT&T Bell Labs", "tipo": "Organizacao", "aliases": []},
        {"nome": "Alfred Aho", "tipo": "Pessoa", "aliases": []},
        {"nome": "Alfred V. Aho", "tipo": "Pessoa", "aliases": []},
        {"nome": "C", "tipo": "Tecnologia", "aliases": []},
        {"nome": "C++", "tipo": "Tecnologia", "aliases": []},
    ]
    pares = {(p["a"], p["b"]) for p in possiveis_duplicatas(entidades)}
    assert pares == {("Bell Labs", "AT&T Bell Labs"), ("Alfred Aho", "Alfred V. Aho")}


def test_tipos_diferentes_nao_sao_duplicata():
    entidades = [
        {"nome": "Java", "tipo": "Tecnologia", "aliases": []},
        {"nome": "Java", "tipo": "Organizacao", "aliases": []},
    ]
    assert possiveis_duplicatas(entidades) == []


# ---------- Com banco ----------

def test_contagens_batem_com_os_arquivos_da_semente(semente_no_banco):
    por_rotulo, por_relacao = esperado_da_semente()
    dados = coletar(semente_no_banco, PREFIXO)
    assert len(dados["documentos"]) == len(carregar_semente())
    assert dados["trechos"] == sum(len(a["chunks"]) for a in carregar_semente().values())
    assert dados["entidades"] == sum(por_rotulo.values())
    assert dados["por_rotulo"] == dict(por_rotulo)
    assert dados["por_relacao"] == dict(por_relacao)
    assert dados["relacoes"] == sum(por_relacao.values())


def test_semente_nao_tem_problemas_de_qualidade(semente_no_banco):
    dados = coletar(semente_no_banco, PREFIXO)
    assert dados["sem_fonte"] == []
    assert dados["sem_relacao"] == []
    assert dados["possiveis_duplicatas"] == []


def test_aponta_entidade_solta_e_duplicata(semente_no_banco):
    semente_no_banco.execute_query(
        "CREATE (:Entity:Organizacao {id: $id, name: 'AT&T Bell Labs', type: 'Organizacao', aliases: []})",
        id=PREFIXO + "organizacao:att_bell_labs",
    )
    dados = coletar(semente_no_banco, PREFIXO)
    assert {"nome": "AT&T Bell Labs", "tipo": "Organizacao"} in dados["sem_relacao"]
    assert any({p["a"], p["b"]} == {"Bell Labs", "AT&T Bell Labs"} for p in dados["possiveis_duplicatas"])


def test_markdown_tem_as_secoes_e_avisa_quando_o_gds_nao_rodou(semente_no_banco):
    dados = coletar(semente_no_banco, PREFIXO)
    texto = gerar_markdown(dados, "data/semente", hoje=date(2026, 11, 15))
    for secao in ("## Resumo", "## Por documento", "## Entidades por rótulo", "## Relações por tipo",
                  "## Qualidade da extração", "## Entidades mais importantes (PageRank)"):
        assert secao in texto
    assert "15/11/2026" in texto
    assert "O GDS ainda não rodou" in texto  # a semente de teste não recebeu pagerank


def test_markdown_lista_o_top_5_do_pagerank(semente_no_banco):
    semente_no_banco.execute_query(
        """MATCH (e:Entity) WHERE e.id STARTS WITH $p
           SET e.pagerank = CASE e.name WHEN 'Dennis Ritchie' THEN 9.0 ELSE 1.0 END, e.community = 1""",
        p=PREFIXO,
    )
    dados = coletar(semente_no_banco, PREFIXO)
    assert dados["top_pagerank"][0]["nome"] == "Dennis Ritchie"
    assert len(dados["top_pagerank"]) == 5
    texto = gerar_markdown(dados, "data/semente")
    assert "| 1 | Dennis Ritchie | `Pessoa` | 9.000 |" in texto
    assert "## Comunidades (Louvain)" in texto
