"""Garantias conservadoras da exportação de relações aceitas do PA4."""
import json
from copy import deepcopy

import pytest

from src.banco.ingestor import carregar_dominio, validar_artigo
from src.pipeline.exportar_pa4 import (
    CORRECOES_PADRAO,
    ENTRADA_PADRAO,
    EQUIVALENCIAS_PADRAO,
    REVISOES_PADRAO,
    RAIZ,
    exportar,
)
from src.pipeline.integrar_pa4 import integrar
from src.pipeline.resolucao_entidades import ler_artigos

CURADO = RAIZ / "data" / "processado" / "curado"


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


# Com incluir_pendentes=True: o que vai para o banco (data/processado/curado).

def test_incluir_pendentes_exclui_rejeitadas_e_mantem_todas_as_entidades():
    dados, revisoes, eq = exemplo()
    saida, auditoria = exportar(dados, revisoes, eq, incluir_pendentes=True)
    assert len(saida["doc"]["relacoes"]) == 1
    assert saida["doc"]["relacoes"][0]["origem"] == "pessoa:alice"
    assert {e["id"] for e in saida["doc"]["entidades"]} == {"pessoa:alice", "tecnologia:x", "tecnologia:y"}
    assert auditoria["resumo"]["relacoes_rejeitadas_excluidas"] == 1
    assert auditoria["resumo"]["relacoes_pendentes_exportadas"] == 0


def test_incluir_pendentes_sem_revisoes_exporta_todas_com_ids_canonicos():
    dados, _, eq = exemplo()
    saida, auditoria = exportar(dados, {"decisoes": []}, eq, incluir_pendentes=True)
    relacoes = saida["doc"]["relacoes"]
    assert len(relacoes) == 2
    assert {r["origem"] for r in relacoes} == {"pessoa:alice"}
    assert {r["destino"] for r in relacoes} == {"tecnologia:x", "tecnologia:y"}
    assert auditoria["resumo"]["relacoes_pendentes_exportadas"] == 2
    assert auditoria["resumo"]["relacoes_pendentes_excluidas"] == 0


def test_incluir_pendentes_mantem_chunk_original_e_registra_sugestao():
    dados, _, eq = exemplo()
    rr = dados["doc"]["relacoes"][1]
    corrigir = {"correcoes": [{"artigo": "doc", **rr,
        "chunk_id_anterior": "doc#1", "chunk_id_sugerido": "doc#0", "justificativa": "Trecho mais específico"}]}
    del corrigir["correcoes"][0]["chunk_id"]
    saida, audit = exportar(dados, {"decisoes": []}, eq, corrigir, incluir_pendentes=True)
    rel1 = [r for r in saida["doc"]["relacoes"] if r["destino"] == "tecnologia:y"]
    assert [r["chunk_id"] for r in rel1] == ["doc#1"]
    itens = [i for i in audit["pendentes_exportadas"] if i["relacao"]["destino"] == "tecnologia:y"]
    assert len(itens) == 1
    assert len(itens[0]["sugestoes_correcao_evidencia"]) == 1


@pytest.fixture(scope="module")
def dados_reais():
    artigos = ler_artigos(ENTRADA_PADRAO)
    revisoes = json.loads(REVISOES_PADRAO.read_text(encoding="utf-8"))
    equivalencias = json.loads(EQUIVALENCIAS_PADRAO.read_text(encoding="utf-8"))
    correcoes = json.loads(CORRECOES_PADRAO.read_text(encoding="utf-8"))
    saida, auditoria = exportar(artigos, revisoes, equivalencias, correcoes, incluir_pendentes=True)
    integrado = integrar(artigos, revisoes, equivalencias)
    return saida, auditoria, integrado


def test_dados_reais_exportam_aceitas_e_pendentes_sem_rejeitadas(dados_reais):
    saida, auditoria, integrado = dados_reais
    resumo = integrado["resumo"]
    assert sum(len(d["relacoes"]) for d in saida.values()) == resumo["aceita"] + resumo["pendente"]
    assert auditoria["resumo"]["relacoes_pendentes_exportadas"] == resumo["pendente"]
    assert auditoria["resumo"]["relacoes_rejeitadas_excluidas"] == resumo["rejeitada"]
    rejeitadas = [r for r in integrado["relacoes"] if r["status"] == "rejeitada"]
    assert rejeitadas
    for registro in rejeitadas:
        assert registro["relacao"] not in saida[registro["artigo"]]["relacoes"]
    dominio = carregar_dominio()
    for nome, artigo in saida.items():
        assert validar_artigo(artigo, dominio) == [], nome


def test_pasta_curado_esta_em_dia(dados_reais):
    saida, _, _ = dados_reais
    aviso = "rode python src/pipeline/exportar_pa4.py --incluir-pendentes --saida data/processado/curado"
    extraidos = {p.name for p in ENTRADA_PADRAO.glob("*.json") if not p.name.startswith("manifesto")}
    assert {p.name for p in CURADO.glob("*.json")} == extraidos, aviso
    for nome, artigo in saida.items():
        assert json.loads((CURADO / f"{nome}.json").read_text(encoding="utf-8")) == artigo, f"{nome}: {aviso}"
