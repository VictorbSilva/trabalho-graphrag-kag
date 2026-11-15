"""Garantias conservadoras da exportação de relações aceitas do PA4."""
from copy import deepcopy

import pytest

from src.pipeline.exportar_pa4 import exportar


def exemplo():
    dados = {"doc": {
        "documento": {"id": "doc", "title": "Teste", "source": "https://exemplo.test"},
        "chunks": [{"id": "doc#0", "index": 0, "text": "Alice criou X."},
                   {"id": "doc#1", "index": 1, "text": "Alice criou Y."}],
        "entidades": [
            {"id": "pessoa:alice", "name": "Alice", "type": "Pessoa", "aliases": [], "description": "", "chunk_ids": ["doc#0", "doc#1"]},
            {"id": "pessoa:apelido", "name": "A.", "type": "Pessoa", "aliases": [], "description": "", "chunk_ids": ["doc#0"]},
            {"id": "tecnologia:x", "name": "X", "type": "Tecnologia", "aliases": [], "description": "", "chunk_ids": ["doc#0"]},
            {"id": "tecnologia:y", "name": "Y", "type": "Tecnologia", "aliases": [], "description": "", "chunk_ids": ["doc#1"]},
        ],
        "relacoes": [
            {"origem": "pessoa:apelido", "destino": "tecnologia:x", "tipo": "CRIOU", "chunk_id": "doc#0"},
            {"origem": "pessoa:alice", "destino": "tecnologia:y", "tipo": "CRIOU", "chunk_id": "doc#1"},
        ]
    }}
    revisoes = {"decisoes": [
        {"artigo": "doc", **dados["doc"]["relacoes"][0], "status": "aceita", "justificativa": "Evidência"},
        {"artigo": "doc", **dados["doc"]["relacoes"][1], "status": "rejeitada", "justificativa": "Não comprovada"},
    ]}
    equivalencias = {"equivalencias": [{"de": "pessoa:apelido", "para": "pessoa:alice", "justificativa": "Mesma pessoa"}]}
    return dados, revisoes, equivalencias


def test_exporta_apenas_aceitas_e_ids_canonicos():
    dados, revisoes, eq = exemplo()
    saida, auditoria = exportar(dados, revisoes, eq)
    assert len(saida["doc"]["relacoes"]) == 1
    assert saida["doc"]["relacoes"][0]["origem"] == "pessoa:alice"
    assert {e["id"] for e in saida["doc"]["entidades"]} == {"pessoa:alice", "tecnologia:x"}
    assert len(saida["doc"]["chunks"]) == 2
    assert auditoria["resumo"]["relacoes_rejeitadas_excluidas"] == 1


def test_sem_revisoes_nao_exporta_relacoes():
    dados, _, eq = exemplo()
    saida, auditoria = exportar(dados, {"decisoes": []}, eq)
    assert saida["doc"]["relacoes"] == []
    assert auditoria["resumo"]["relacoes_pendentes_excluidas"] == 2


def test_nao_modifica_entradas():
    dados, revisoes, eq = exemplo()
    antes = deepcopy((dados, revisoes, eq))
    exportar(dados, revisoes, eq)
    assert (dados, revisoes, eq) == antes


def test_correcao_pendente_e_so_sugestao():
    dados, _, eq = exemplo()
    rr = dados["doc"]["relacoes"][1]
    corrigir = {"correcoes": [{"artigo": "doc", **rr,
        "chunk_id_anterior": "doc#1", "chunk_id_sugerido": "doc#0", "justificativa": "Trecho mais específico"}]}
    del corrigir["correcoes"][0]["chunk_id"]
    saida, audit = exportar(dados, {"decisoes": []}, eq, corrigir)
    assert not saida["doc"]["relacoes"]
    assert len(audit["excluidas"][1]["sugestoes_correcao_evidencia"]) == 1


def test_correcao_inexistente_falha():
    dados, revisoes, eq = exemplo()
    rr = dados["doc"]["relacoes"][1]
    bad = {"correcoes": [{"artigo": "doc", "origem": rr["origem"], "tipo": rr["tipo"],
        "destino": rr["destino"], "chunk_id_anterior": rr["chunk_id"],
        "chunk_id_sugerido": "doc#99", "justificativa": "Teste"}]}
    with pytest.raises(ValueError, match="Novo chunk não existe"):
        exportar(dados, revisoes, eq, bad)


def test_correcao_de_relacao_aceita_nao_pode_ser_aplicada_sem_revisao():
    dados, revisoes, eq = exemplo()
    rr = dados["doc"]["relacoes"][0]
    bad = {"correcoes": [{"artigo": "doc", "origem": rr["origem"], "tipo": rr["tipo"],
        "destino": rr["destino"], "chunk_id_anterior": rr["chunk_id"],
        "chunk_id_sugerido": "doc#1", "justificativa": "Teste"}]}
    with pytest.raises(ValueError, match="já aceita"):
        exportar(dados, revisoes, eq, bad)
