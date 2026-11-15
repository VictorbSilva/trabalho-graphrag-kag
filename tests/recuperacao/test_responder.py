"""Testes do responder() sem banco e sem modelo (issues V1 e V3).

A busca vetorial, o embedding e a expansão são trocados por funções falsas, para
conferir só como o responder monta a resposta. Rodam no CI.
"""

import json

import pytest

import src.recuperacao.responder as modulo
from src.api.servico import carregar_responder
from src.contrato import Resposta
from src.recuperacao.responder import responder

PERGUNTA = "Que prêmio recebeu quem criou a linguagem que influenciou o C++?"

RESULTADOS = [
    {
        "chunk_id": "c_mais_mais#0",
        "trecho": "C++ foi criada por Bjarne Stroustrup.",
        "documento": "C++",
        "url": "https://pt.wikipedia.org/wiki/C%2B%2B",
        "score": 0.9,
    },
    {
        "chunk_id": "c#0",
        "trecho": "C foi criada por Dennis Ritchie.",
        "documento": "C (linguagem de programação)",
        "url": "https://pt.wikipedia.org/wiki/C_(linguagem_de_programa%C3%A7%C3%A3o)",
        "score": 0.8,
    },
]

CAMINHO = {
    "chunk_origem": "c_mais_mais#0",
    "nos": [
        {"id": "tecnologia:c_mais_mais", "nome": "C++", "tipo": "Tecnologia",
         "pagerank": 0.0, "comunidade": None},
        {"id": "tecnologia:c", "nome": "C", "tipo": "Tecnologia",
         "pagerank": 0.0, "comunidade": None},
    ],
    "arestas": [
        {"origem": "tecnologia:c_mais_mais", "destino": "tecnologia:c",
         "tipo": "INFLUENCIADA_POR", "fontes": ["c_mais_mais#0"]},
    ],
    "score": 0.9,
}


@pytest.fixture
def chamadas(monkeypatch):
    """Troca embedding, busca e expansão por funções falsas e registra a expansão."""
    registro = {"expandir": False}

    def buscar_falso(driver, embedding, k=5):
        return [dict(r) for r in RESULTADOS]

    def expandir_falso(driver, chunk_ids, **kwargs):
        registro["expandir"] = True
        return [CAMINHO]

    monkeypatch.setattr(modulo, "gerar_embedding", lambda t: [0.0])
    monkeypatch.setattr(modulo, "buscar_chunks", buscar_falso)
    monkeypatch.setattr(modulo, "expandir", expandir_falso)
    return registro


def test_graphrag_devolve_caminho_e_fontes(chamadas):
    dados = responder(PERGUNTA, "graphrag", driver=object())
    Resposta.model_validate(dados)
    assert dados["modo"] == "graphrag"
    assert [c["id"] for c in dados["caminhos"]] == ["C1"]
    assert [f["id"] for f in dados["fontes"]] == ["F1", "F2"]
    assert chamadas["expandir"]


def test_vetorial_nao_expande(chamadas):
    dados = responder(PERGUNTA, "vetorial", driver=object())
    Resposta.model_validate(dados)
    assert dados["caminhos"] == []
    assert not chamadas["expandir"]


def test_modo_invalido_e_recusado(chamadas):
    with pytest.raises(ValueError):
        responder(PERGUNTA, "hibrido", driver=object())


def test_resposta_vira_json(chamadas):
    json.dumps(responder(PERGUNTA, driver=object()), ensure_ascii=False)


def test_api_carrega_o_responder_pela_configuracao():
    alvo = "src.recuperacao.responder:responder"
    assert carregar_responder("recuperacao", alvo) is responder
