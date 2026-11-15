"""Testes do contrato da resposta (issue #2)."""

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contrato import Confianca, Resposta

RAIZ = Path(__file__).resolve().parents[2]
EXEMPLO = RAIZ / "data" / "exemplo_resposta.json"
DOMINIO = RAIZ / "neo4j" / "dominio.json"
SEMENTE = RAIZ / "data" / "semente"


def carregar_exemplo() -> dict:
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


def ids_da_semente() -> tuple[set[str], set[str]]:
    chunks, entidades = set(), set()
    for arquivo in SEMENTE.glob("*.json"):
        artigo = json.loads(arquivo.read_text(encoding="utf-8"))
        chunks |= {c["id"] for c in artigo["chunks"]}
        entidades |= {e["id"] for e in artigo["entidades"]}
    return chunks, entidades

def textos_da_semente() -> dict[str, str]:
        textos = {}
        for arquivo in SEMENTE.glob("*.json"):
            artigo = json.loads(arquivo.read_text(encoding="utf-8"))
            for chunk in artigo["chunks"]:
                textos[chunk["id"]] = chunk["text"]
        return textos


# --- formato ---------------------------------------------------------------

def test_exemplo_segue_o_contrato():
    Resposta.model_validate(carregar_exemplo())


@pytest.mark.parametrize("nivel", ["Alta", "média", "MEDIA", ""])
def test_nivel_fora_da_lista_e_recusado(nivel):
    with pytest.raises(ValidationError):
        Confianca(valor=0.5, nivel=nivel, criterio="teste")


def test_campo_desconhecido_e_recusado():
    dados = carregar_exemplo()
    dados["aviso"] = ["digitado errado"]
    with pytest.raises(ValidationError):
        Resposta.model_validate(dados)


def test_avisos_como_texto_solto_e_recusado():
    dados = carregar_exemplo()
    dados["avisos"] = "sem caminho"
    with pytest.raises(ValidationError):
        Resposta.model_validate(dados)


def test_modo_vetorial_sem_cypher_e_valido():
    dados = carregar_exemplo()
    dados["modo"] = "vetorial"
    dados["cypher"] = None
    Resposta.model_validate(dados)


# --- significado -----------------------------------------------------------

def test_nos_dos_caminhos_existem_no_subgrafo():
    resposta = Resposta.model_validate(carregar_exemplo())
    ids = {no.id for no in resposta.subgrafo.nos}
    for caminho in resposta.caminhos:
        assert set(caminho.nos) <= ids, caminho.id


def test_citacoes_da_resposta_existem():
    resposta = Resposta.model_validate(carregar_exemplo())
    citados = set(re.findall(r"\[([CF]\d+)\]", resposta.resposta))
    existentes = {c.id for c in resposta.caminhos} | {f.id for f in resposta.fontes}
    assert citados, "o exemplo deveria citar pelo menos um caminho ou fonte"
    assert citados <= existentes


def test_tipos_seguem_o_dominio():
    dominio = json.loads(DOMINIO.read_text(encoding="utf-8"))
    rotulos = {r["nome"] for r in dominio["rotulos"]}
    relacoes = {r["tipo"] for r in dominio["relacoes"]}
    resposta = Resposta.model_validate(carregar_exemplo())
    assert {no.tipo for no in resposta.subgrafo.nos} <= rotulos
    assert {a.tipo for a in resposta.subgrafo.arestas} <= relacoes
    for caminho in resposta.caminhos:
        assert set(caminho.relacoes) <= relacoes


def test_ids_do_exemplo_existem_na_semente():
    chunks, entidades = ids_da_semente()
    resposta = Resposta.model_validate(carregar_exemplo())
    usados = {f.chunk_id for f in resposta.fontes}
    usados |= {c for caminho in resposta.caminhos for c in caminho.fontes}
    usados |= {c for a in resposta.subgrafo.arestas for c in a.fontes}
    assert usados <= chunks, sorted(usados - chunks)
    assert {no.id for no in resposta.subgrafo.nos} <= entidades

def test_trechos_do_exemplo_batem_com_a_semente():
    textos = textos_da_semente()
    resposta = Resposta.model_validate(carregar_exemplo())
    for fonte in resposta.fontes:
        assert fonte.trecho == textos.get(fonte.chunk_id), fonte.id