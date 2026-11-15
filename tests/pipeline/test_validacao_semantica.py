"""Testes do primeiro validador do PA4; não requer Groq nem Neo4j."""

from src.pipeline.validacao_semantica import analisar, entidade_mencionada


def artigo(ident, origem, destino, texto):
    return {
        "documento": {"id": ident},
        "chunks": [{"id": f"{ident}#0", "index": 0, "text": texto}],
        "entidades": [
            {"id": origem, "name": origem.split(":", 1)[1].upper(), "aliases": []},
            {"id": destino, "name": destino.split(":", 1)[1].upper(), "aliases": []},
        ],
        "relacoes": [{"origem": origem, "destino": destino, "tipo": "INFLUENCIADA_POR",
                     "chunk_id": f"{ident}#0"}],
    }


def test_influencias_contraditorias_sao_sinalizadas_sem_corrigir():
    c = artigo("c", "tecnologia:c", "tecnologia:b", "C foi derivada de B")
    b = artigo("b", "tecnologia:b", "tecnologia:c", "B precedeu C")
    resultado = analisar({"c": c, "b": b})
    assert "INFLUENCIA_NOS_DOIS_SENTIDOS" in [a["codigo"] for a in resultado["alertas"]]
    assert b["relacoes"][0]["origem"] == "tecnologia:b"  # originais intactos


def test_referencia_a_chunk_inexistente_e_reportada():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "C deriva de B")
    a["relacoes"][0]["chunk_id"] = "a#99"
    resultado = analisar({"a": a})
    assert "CHUNK_INVALIDO" in [alerta["codigo"] for alerta in resultado["alertas"]]


def test_nenhuma_entidade_mencionada_gera_aviso_nao_erro():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "Este parágrafo não nomeia tecnologias.")
    resultado = analisar({"a": a})
    assert "EVIDENCIA_A_REVISAR" in [alerta["codigo"] for alerta in resultado["alertas"]]


def test_alias_e_acento_sao_reconhecidos():
    entidade = {"name": "Prêmio Turing", "aliases": ["Turing Award"]}
    assert entidade_mencionada(entidade, "Recebeu o Premio Turing")
    assert entidade_mencionada(entidade, "He won the Turing Award")

from copy import deepcopy

import pytest
from src.pipeline.validacao_semantica import classificar


def test_sem_curadoria_nada_e_aceito_automaticamente():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "C deriva de B")
    resultado = classificar({"a": a})
    assert resultado["resumo"]["aceita"] == 0
    assert resultado["relacoes"][0]["status"] == "pendente"


def test_curadoria_aceita_ou_rejeita_sem_alterar_original():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "C deriva de B")
    original = deepcopy(a)
    rel = a["relacoes"][0]
    revisoes = {"decisoes": [{"artigo": "a", **rel, "status": "aceita",
                              "justificativa": "Texto afirma derivação."}]}
    resultado = classificar({"a": a}, revisoes)
    assert resultado["relacoes"][0]["status"] == "aceita"
    assert resultado["resumo"]["decisoes_manuais"] == 1
    assert a == original


def test_decisao_sem_relacao_correspondente_e_erro():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "C deriva de B")
    rel = dict(a["relacoes"][0], chunk_id="a#999")
    with pytest.raises(ValueError, match="não corresponde"):
        classificar({"a": a}, {"decisoes": [{"artigo": "a", **rel,
                                              "status": "rejeitada", "justificativa": "Teste"}]})


def test_curadoria_duplicada_e_erro():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "C deriva de B")
    decisao = {"artigo": "a", **a["relacoes"][0],
               "status": "pendente", "justificativa": "Revisão em andamento"}
    with pytest.raises(ValueError, match="duplicada"):
        classificar({"a": a}, {"decisoes": [decisao, decisao]})


def test_relacao_sem_evidencia_aceita_apenas_por_curadoria_explicita():
    a = artigo("a", "tecnologia:c", "tecnologia:b", "Nenhuma tecnologia aqui.")
    rel = a["relacoes"][0]
    resultado = classificar({"a": a}, {"decisoes": [{"artigo": "a", **rel,
                                       "status": "pendente", "justificativa": "Sem evidência"}]})
    assert resultado["relacoes"][0]["status"] == "pendente"
    assert "EVIDENCIA_A_REVISAR" in resultado["relacoes"][0]["alertas"]
