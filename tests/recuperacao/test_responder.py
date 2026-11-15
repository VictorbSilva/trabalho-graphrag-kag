"""Testes do esqueleto do responder() (issue V1)."""

import json

import pytest

from src.api.servico import carregar_responder
from src.contrato import Resposta
from src.recuperacao.responder import responder

PERGUNTA = "Quem criou a linguagem C?"


@pytest.mark.parametrize("modo", ["graphrag", "vetorial"])
def test_devolve_o_contrato_com_a_pergunta_e_o_modo(modo):
    dados = responder(PERGUNTA, modo)
    Resposta.model_validate(dados)
    assert dados["pergunta"] == PERGUNTA
    assert dados["modo"] == modo


def test_modo_padrao_e_graphrag():
    assert responder(PERGUNTA)["modo"] == "graphrag"


def test_modo_vetorial_nao_tem_cypher():
    assert responder(PERGUNTA, "vetorial")["cypher"] is None


def test_modo_invalido_e_recusado():
    with pytest.raises(ValueError):
        responder(PERGUNTA, "hibrido")


def test_resposta_vira_json():
    json.dumps(responder(PERGUNTA), ensure_ascii=False)


def test_api_carrega_o_responder_pela_configuracao():
    alvo = "src.recuperacao.responder:responder"
    assert carregar_responder("recuperacao", alvo) is responder
