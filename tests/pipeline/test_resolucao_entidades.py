"""Testes isolados do PA4-B. Sem API Groq nem serviço Neo4j."""

from copy import deepcopy

import pytest

from src.pipeline.resolucao_entidades import resolver


def base():
    return {
        "teste": {
            "documento": {"id": "teste", "title": "Teste", "source": "fonte"},
            "chunks": [
                {"id": "teste#0", "index": 0, "text": "Aho criou AWK"},
                {"id": "teste#1", "index": 1, "text": "Alfred V. Aho criou AWK"},
            ],
            "entidades": [
                {"id": "pessoa:alfred_aho", "name": "Alfred Aho", "type": "Pessoa", "aliases": [],
                 "description": "Pessoa", "chunk_ids": ["teste#0"]},
                {"id": "pessoa:alfred_v_aho", "name": "Alfred V. Aho", "type": "Pessoa", "aliases": [],
                 "description": "Autor", "chunk_ids": ["teste#1"]},
                {"id": "tecnologia:awk", "name": "AWK", "type": "Tecnologia", "aliases": [],
                 "description": "Linguagem", "chunk_ids": ["teste#0", "teste#1"]},
            ],
            "relacoes": [
                {"origem": "pessoa:alfred_aho", "destino": "tecnologia:awk", "tipo": "CRIOU", "chunk_id": "teste#0"},
                {"origem": "pessoa:alfred_v_aho", "destino": "tecnologia:awk", "tipo": "CRIOU", "chunk_id": "teste#1"},
            ],
        }
    }


def regra(de="pessoa:alfred_aho", para="pessoa:alfred_v_aho"):
    return {"equivalencias": [{"de": de, "para": para, "justificativa": "mesma pessoa"}]}


def test_unifica_aliases_e_mantem_chunks_das_duas_mencoes():
    resolvidos, relatorio = resolver(base(), regra())
    entidades = resolvidos["teste"]["entidades"]
    assert len(entidades) == 2
    aho = next(e for e in entidades if e["id"] == "pessoa:alfred_v_aho")
    assert aho["name"] == "Alfred V. Aho"
    assert "Alfred Aho" in aho["aliases"]
    assert aho["chunk_ids"] == ["teste#0", "teste#1"]
    assert relatorio["resumo"]["ids_distintos_antes"] == 3
    assert relatorio["resumo"]["ids_distintos_depois"] == 2


def test_reescreve_relacoes_sem_perder_evidencias_ou_alterar_entrada():
    artigos = base()
    anterior = deepcopy(artigos)
    saida, relatorio = resolver(artigos, regra())
    assert artigos == anterior
    assert len(saida["teste"]["relacoes"]) == 2
    assert {r["chunk_id"] for r in saida["teste"]["relacoes"]} == {"teste#0", "teste#1"}
    assert {r["origem"] for r in saida["teste"]["relacoes"]} == {"pessoa:alfred_v_aho"}
    assert relatorio["resumo"]["relacoes_depois"] == 2


def test_sem_regra_nao_unifica_simplesmente_por_parecer_nome():
    saida, _ = resolver(base(), {"equivalencias": []})
    assert len(saida["teste"]["entidades"]) == 3


def test_rejeita_unificacao_entre_tipos_diferentes():
    with pytest.raises(ValueError, match="tipos diferentes"):
        resolver(base(), regra("pessoa:alfred_aho", "tecnologia:awk"))


def test_rejeita_id_desconhecido():
    with pytest.raises(ValueError, match="desconhecido"):
        resolver(base(), regra("pessoa:desconhecida", "pessoa:alfred_v_aho"))


def test_rejeita_equivalencias_ciclicas():
    regras = {"equivalencias": [
        {"de": "pessoa:alfred_aho", "para": "pessoa:alfred_v_aho", "justificativa": "x"},
        {"de": "pessoa:alfred_v_aho", "para": "pessoa:alfred_aho", "justificativa": "y"},
    ]}
    with pytest.raises(ValueError, match="Ciclo"):
        resolver(base(), regras)


def test_preserva_subunidade_quando_nao_consta_em_equivalencias():
    artigos = base()
    artigos["teste"]["entidades"].append({
        "id": "organizacao:centro", "name": "Bell Labs Computing Science Research Center",
        "type": "Organizacao", "aliases": ["Bell Labs"], "description": "Unidade", "chunk_ids": ["teste#0"]})
    saida, _ = resolver(artigos, regra())
    assert "organizacao:centro" in {e["id"] for e in saida["teste"]["entidades"]}


def test_rejeita_relacao_com_referencia_invalida():
    artigos = base()
    artigos["teste"]["relacoes"][0]["chunk_id"] = "teste#99"
    with pytest.raises(ValueError, match="sem chunk"):
        resolver(artigos, regra())
