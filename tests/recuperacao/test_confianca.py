"""Nível de confiança da resposta (src/recuperacao/confianca.py).

Sem banco e sem modelo: roda no CI.
"""

import pytest

from src.contrato import Confianca
from src.recuperacao.confianca import calcular_confianca


def test_score_alto_com_todos_os_caminhos_com_fonte_da_alta():
    c = calcular_confianca(melhor_score=0.95, caminhos=3, caminhos_com_fonte=3)
    assert c["valor"] == 0.95
    assert c["nivel"] == "alta"


@pytest.mark.parametrize(
    "sinais",
    [
        {"melhor_score": 0.95, "caminhos": 3, "caminhos_com_fonte": 3},
        {"melhor_score": 1.0, "caminhos": 5, "caminhos_com_fonte": 5, "cypher_ok": True},
        {"melhor_score": None, "caminhos": 0, "caminhos_com_fonte": 0, "cypher_ok": False},
    ],
)
def test_sem_contexto_zera_o_valor(sinais):
    c = calcular_confianca(**sinais, sem_contexto=True)
    assert c["valor"] == 0.0
    assert c["nivel"] == "baixa"


def test_so_vetorial_com_score_alto_fica_media():
    c = calcular_confianca(melhor_score=0.95, caminhos=0, caminhos_com_fonte=0)
    assert c["valor"] == 0.63
    assert c["nivel"] == "media"


def test_pergunta_fora_do_dominio_fica_baixa():
    c = calcular_confianca(melhor_score=0.6, caminhos=0, caminhos_com_fonte=0)
    assert c["nivel"] == "baixa"


def test_cypher_com_erro_tira_um_decimo():
    base = calcular_confianca(melhor_score=0.95, caminhos=3, caminhos_com_fonte=3)
    com_erro = calcular_confianca(
        melhor_score=0.95, caminhos=3, caminhos_com_fonte=3, cypher_ok=False
    )
    assert com_erro["valor"] == round(base["valor"] - 0.1, 2)


def test_cypher_ausente_nao_muda_o_valor():
    base = calcular_confianca(melhor_score=0.95, caminhos=3, caminhos_com_fonte=3)
    sem_cypher = calcular_confianca(
        melhor_score=0.95, caminhos=3, caminhos_com_fonte=3, cypher_ok=None
    )
    assert sem_cypher["valor"] == base["valor"]
    assert sem_cypher["nivel"] == base["nivel"]


@pytest.mark.parametrize(("caminhos", "caminhos_com_fonte"), [(0, 0), (2, 2), (4, 1)])
def test_score_ausente_conta_como_cosseno_zero(caminhos, caminhos_com_fonte):
    ausente = calcular_confianca(
        melhor_score=None, caminhos=caminhos, caminhos_com_fonte=caminhos_com_fonte
    )
    cosseno_zero = calcular_confianca(
        melhor_score=0.5, caminhos=caminhos, caminhos_com_fonte=caminhos_com_fonte
    )
    assert ausente["valor"] == cosseno_zero["valor"]


@pytest.mark.parametrize(
    "sinais",
    [
        {"melhor_score": 1.0, "caminhos": 3, "caminhos_com_fonte": 3},
        {"melhor_score": 1.0, "caminhos": 0, "caminhos_com_fonte": 0},
        {"melhor_score": 0.0, "caminhos": 0, "caminhos_com_fonte": 0},
        {"melhor_score": 0.0, "caminhos": 0, "caminhos_com_fonte": 0, "cypher_ok": False},
        {"melhor_score": 0.0, "caminhos": 2, "caminhos_com_fonte": 0, "cypher_ok": False},
        {"melhor_score": None, "caminhos": 3, "caminhos_com_fonte": 1},
        {"melhor_score": 0.95, "caminhos": 3, "caminhos_com_fonte": 3, "sem_contexto": True},
    ],
)
def test_resultado_valida_no_contrato_e_fica_entre_0_e_1(sinais):
    c = calcular_confianca(**sinais)
    Confianca.model_validate(c)
    assert 0.0 <= c["valor"] <= 1.0


@pytest.mark.parametrize(
    "sinais",
    [
        {"melhor_score": 0.95, "caminhos": 3, "caminhos_com_fonte": 3},
        {"melhor_score": 0.95, "caminhos": 0, "caminhos_com_fonte": 0},
        {"melhor_score": None, "caminhos": 2, "caminhos_com_fonte": 1, "cypher_ok": False},
    ],
)
def test_criterio_cita_os_sinais_usados(sinais):
    criterio = calcular_confianca(**sinais)["criterio"]
    assert isinstance(criterio, str)
    assert "score" in criterio
    assert "caminhos" in criterio
