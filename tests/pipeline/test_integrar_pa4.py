"""Testes da integração conservadora entre revisão e resolução (PA4-C)."""

from copy import deepcopy

import pytest

from src.pipeline.integrar_pa4 import integrar


def amostra():
    artigos = {
        "art": {
            "documento": {"id": "art"},
            "chunks": [{"id": "art#0", "index": 0, "text": "A e A Nome influenciaram X."}],
            "entidades": [
                {"id": "pessoa:a", "name": "A Nome", "type": "Pessoa", "aliases": [], "description": "", "chunk_ids": ["art#0"]},
                {"id": "pessoa:apelido", "name": "A", "type": "Pessoa", "aliases": [], "description": "", "chunk_ids": ["art#0"]},
                {"id": "tecnologia:x", "name": "X", "type": "Tecnologia", "aliases": [], "description": "", "chunk_ids": ["art#0"]},
            ],
            "relacoes": [
                {"origem": "pessoa:a", "tipo": "CRIOU", "destino": "tecnologia:x", "chunk_id": "art#0"},
                {"origem": "pessoa:apelido", "tipo": "CRIOU", "destino": "tecnologia:x", "chunk_id": "art#0"},
            ],
        }
    }
    equivalencias = {"equivalencias": [{"de": "pessoa:apelido", "para": "pessoa:a", "justificativa": "Mesmo indivíduo"}]}
    return artigos, equivalencias


def decisao(origem, status):
    return {"artigo": "art", "origem": origem, "tipo": "CRIOU", "destino": "tecnologia:x",
            "chunk_id": "art#0", "status": status, "justificativa": "Trecho revisado"}


def test_sem_revisao_nunca_aprova():
    artigos, equivalencias = amostra()
    r = integrar(artigos, {"decisoes": []}, equivalencias)
    assert r["resumo"]["aceita"] == 0
    assert r["resumo"]["pendente"] == 1


def test_mapeia_ids_antes_de_agrupar():
    artigos, equivalencias = amostra()
    r = integrar(artigos, {"decisoes": [decisao("pessoa:a", "aceita"),
                                           decisao("pessoa:apelido", "aceita")]}, equivalencias)
    assert r["resumo"]["relacoes_originais"] == 2
    assert r["resumo"]["relacoes_canonicas"] == 1
    assert r["relacoes"][0]["relacao"]["origem"] == "pessoa:a"
    assert len(r["relacoes"][0]["proveniencia"]) == 2
    assert r["resumo"]["aceita"] == 1


def test_status_divergentes_ficam_pendentes():
    artigos, equivalencias = amostra()
    r = integrar(artigos, {"decisoes": [decisao("pessoa:a", "aceita"),
                                           decisao("pessoa:apelido", "rejeitada")]}, equivalencias)
    assert r["resumo"]["conflitos_apos_resolucao"] == 1
    assert r["resumo"]["pendente"] == 1
    assert r["resumo"]["aceita"] == 0
    assert "STATUS_CONFLITANTES_APOS_RESOLUCAO" in r["relacoes"][0]["alertas"]


def test_sem_mutacao_dos_originais():
    artigos, equivalencias = amostra()
    copia = deepcopy(artigos)
    integrar(artigos, {"decisoes": []}, equivalencias)
    assert artigos == copia


def test_rejeitada_permanece_rejeitada():
    artigos, equivalencias = amostra()
    r = integrar(artigos, {"decisoes": [decisao("pessoa:a", "rejeitada"),
                                           decisao("pessoa:apelido", "rejeitada")]}, equivalencias)
    assert r["resumo"]["rejeitada"] == 1
    assert r["resumo"]["pendente"] == 0


def test_revisao_para_aresta_inexistente_gera_erro():
    artigos, equivalencias = amostra()
    d = decisao("pessoa:inventada", "aceita")
    with pytest.raises(ValueError):
        integrar(artigos, {"decisoes": [d]}, equivalencias)
