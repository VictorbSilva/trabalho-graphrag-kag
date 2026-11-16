"""Plano B da demo: API_FONTE=gravado (issue #33, PE7). Não precisa de banco nem de LLM."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import criar_app
from src.api.gravado import (
    AVISO_GRAVADA,
    AVISO_NAO_GRAVADA,
    perguntas_gravadas,
    responder_gravado,
)
from src.api.servico import carregar_responder
from src.contrato import Resposta

PERGUNTA_DO_ARTIGO = "Que prêmio recebeu quem criou a linguagem que influenciou o C++?"
# Perguntas do roteiro da demo (docs/demo/roteiro.md).
ROTEIRO = [
    (PERGUNTA_DO_ARTIGO, "graphrag"),
    ("Que prêmio recebeu quem criou a linguagem que deu origem ao C?", "vetorial"),
    ("Que prêmio recebeu quem criou a linguagem que deu origem ao C?", "graphrag"),
    ("Quais pessoas que trabalharam no Bell Labs receberam o Prêmio Turing?", "graphrag"),
    ("Quem criou a linguagem de programação Rust?", "graphrag"),
]


def test_tem_as_31_respostas_gravadas():
    # 15 perguntas de avaliação x 2 modos + a pergunta do artigo
    assert len(perguntas_gravadas()) == 31


@pytest.mark.parametrize("pergunta, modo", perguntas_gravadas())
def test_toda_resposta_gravada_segue_o_contrato_e_avisa(pergunta, modo):
    resposta = responder_gravado(pergunta, modo)
    Resposta.model_validate(resposta)
    assert resposta["modo"] == modo
    assert resposta["avisos"][-1] == AVISO_GRAVADA


@pytest.mark.parametrize("pergunta, modo", ROTEIRO)
def test_perguntas_do_roteiro_estao_gravadas(pergunta, modo):
    assert responder_gravado(pergunta, modo)["avisos"][-1] == AVISO_GRAVADA


def test_busca_ignora_maiusculas_espacos_e_interrogacao():
    variacao = "  que PRÊMIO recebeu quem criou a linguagem   que influenciou o c++  "
    resposta = responder_gravado(variacao, "graphrag")
    assert resposta["avisos"][-1] == AVISO_GRAVADA
    assert "Dennis Ritchie" in resposta["resposta"]


def test_pergunta_nao_gravada_responde_no_contrato_sem_inventar():
    resposta = responder_gravado("Quem criou o Haskell?", "graphrag")
    Resposta.model_validate(resposta)
    assert resposta["avisos"] == [AVISO_NAO_GRAVADA]
    assert resposta["confianca"]["nivel"] == "baixa"
    assert resposta["caminhos"] == [] and resposta["fontes"] == []


def test_modo_que_nao_foi_gravado_nao_reaproveita_o_outro():
    # A pergunta do artigo só foi gravada no modo graphrag.
    assert responder_gravado(PERGUNTA_DO_ARTIGO, "vetorial")["avisos"] == [AVISO_NAO_GRAVADA]


def test_resposta_gravada_nao_e_alterada_entre_chamadas():
    primeira = responder_gravado(PERGUNTA_DO_ARTIGO, "graphrag")
    primeira["avisos"].append("lixo")
    segunda = responder_gravado(PERGUNTA_DO_ARTIGO, "graphrag")
    assert segunda["avisos"].count(AVISO_GRAVADA) == 1 and "lixo" not in segunda["avisos"]


def test_api_com_fonte_gravado():
    assert carregar_responder("gravado", "") is responder_gravado
    cliente = TestClient(criar_app(responder=carregar_responder("gravado", "")))
    resposta = cliente.post("/perguntar", json={"pergunta": PERGUNTA_DO_ARTIGO, "modo": "graphrag"})
    assert resposta.status_code == 200
    assert "Prêmio Turing" in resposta.json()["resposta"]
