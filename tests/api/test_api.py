"""Testes da API (issues #24 e #30). Não precisam de banco nem de LLM."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from src.api import config
from src.api.app import criar_app
from src.api.servico import carregar_responder, responder_exemplo

CAMPOS_DO_CONTRATO = {
    "pergunta", "modo", "resposta", "confianca", "cypher",
    "caminhos", "subgrafo", "nos_consultados", "fontes", "avisos",
}


@pytest.fixture
def cliente():
    return TestClient(criar_app(responder=responder_exemplo))


# --- sucesso -----------------------------------------------------------------

def test_saude_responde_200(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


@pytest.mark.parametrize("modo", ["graphrag", "vetorial"])
def test_perguntar_devolve_json_de_exemplo(cliente, modo):
    resposta = cliente.post("/perguntar", json={"pergunta": "Quem criou o C?", "modo": modo})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert CAMPOS_DO_CONTRATO <= corpo.keys()
    assert corpo["pergunta"] == "Quem criou o C?"
    assert corpo["modo"] == modo

    exemplo = json.loads(config.ARQUIVO_EXEMPLO.read_text(encoding="utf-8"))
    for campo in CAMPOS_DO_CONTRATO - {"pergunta", "modo"}:
        assert corpo[campo] == exemplo[campo], campo


def test_modo_padrao_e_graphrag(cliente):
    resposta = cliente.post("/perguntar", json={"pergunta": "Quem criou o C?"})
    assert resposta.status_code == 200
    assert resposta.json()["modo"] == "graphrag"


def test_resposta_da_recuperacao_volta_sem_alteracao():
    objeto = {"resposta": "x", "campo_extra": [1, 2, 3], "confianca": {"valor": 0.1}}
    cliente = TestClient(criar_app(responder=lambda p, m: objeto))
    resposta = cliente.post("/perguntar", json={"pergunta": "Oi?", "modo": "vetorial"})
    assert resposta.status_code == 200
    assert resposta.json() == objeto


def test_pergunta_chega_sem_espacos_nas_pontas():
    recebido = {}

    def responder(pergunta, modo):
        recebido.update(pergunta=pergunta, modo=modo)
        return {}

    cliente = TestClient(criar_app(responder=responder))
    cliente.post("/perguntar", json={"pergunta": "  Quem criou o C?  ", "modo": "vetorial"})
    assert recebido == {"pergunta": "Quem criou o C?", "modo": "vetorial"}


def test_cors_liberado_para_a_interface_local(cliente):
    origem = config.CORS_ORIGENS[0]
    resposta = cliente.options(
        "/perguntar",
        headers={"Origin": origem, "Access-Control-Request-Method": "POST"},
    )
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem


# --- entrada inválida --------------------------------------------------------

@pytest.mark.parametrize(
    "corpo, trecho_da_mensagem",
    [
        ({"pergunta": "", "modo": "graphrag"}, "não pode ser vazio"),
        ({"pergunta": "   ", "modo": "graphrag"}, "não pode ser vazio"),
        ({"modo": "graphrag"}, "'pergunta' é obrigatório"),
        ({"pergunta": "Quem criou o C?", "modo": "outro"}, "'graphrag' ou 'vetorial'"),
        ({"pergunta": 123, "modo": "graphrag"}, "deve ser um texto"),
        ({"pergunta": "x" * 1001, "modo": "graphrag"}, "no máximo"),
        ([], "Envie um JSON"),
    ],
)
def test_entrada_invalida_devolve_422_legivel(cliente, corpo, trecho_da_mensagem):
    resposta = cliente.post("/perguntar", json=corpo)
    assert resposta.status_code == 422
    assert trecho_da_mensagem in resposta.json()["erro"]


def test_corpo_vazio_devolve_422(cliente):
    resposta = cliente.post("/perguntar")
    assert resposta.status_code == 422
    assert "pergunta" in resposta.json()["erro"]


def test_json_malformado_devolve_422(cliente):
    resposta = cliente.post(
        "/perguntar", content="{nao e json", headers={"Content-Type": "application/json"}
    )
    assert resposta.status_code == 422
    assert "JSON válido" in resposta.json()["erro"]


# --- erro da recuperação -----------------------------------------------------

def test_excecao_na_recuperacao_vira_500_sem_stack_trace():
    def responder(pergunta, modo):
        raise RuntimeError("segredo interno: senha=123")

    cliente = TestClient(criar_app(responder=responder), raise_server_exceptions=False)
    resposta = cliente.post("/perguntar", json={"pergunta": "Quem criou o C?", "modo": "graphrag"})

    assert resposta.status_code == 500
    assert "erro" in resposta.json()
    assert "segredo" not in resposta.text
    assert "Traceback" not in resposta.text


def test_tempo_limite_estourado_vira_504():
    def responder(pergunta, modo):
        time.sleep(1)
        return {}

    cliente = TestClient(criar_app(responder=responder, timeout_s=0.05))
    resposta = cliente.post("/perguntar", json={"pergunta": "Quem criou o C?", "modo": "graphrag"})

    assert resposta.status_code == 504
    assert "não respondeu" in resposta.json()["erro"]


# --- configuração ------------------------------------------------------------

def test_fonte_exemplo_usa_o_json_de_exemplo():
    assert carregar_responder("exemplo", "") is responder_exemplo


def test_fonte_recuperacao_importa_a_funcao_configurada():
    assert carregar_responder("recuperacao", "json:dumps") is json.dumps


@pytest.mark.parametrize("fonte, alvo", [("recuperacao", ""), ("outra", "")])
def test_configuracao_invalida_falha_com_mensagem(fonte, alvo):
    with pytest.raises(ValueError, match="API_"):
        carregar_responder(fonte, alvo)
