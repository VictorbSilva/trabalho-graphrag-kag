"""Tipo de entidade que a pergunta pede (src/recuperacao/tipo_resposta.py).

Sem banco e sem modelo: roda no CI.
"""

import json

import pytest

from src.recuperacao.tipo_resposta import PALAVRAS_POR_TIPO, tipo_esperado
from tests.recuperacao.conftest import RAIZ


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("Que prêmio recebeu quem criou a linguagem que influenciou o C++?", "Premio"),
        ("Que prêmio Niklaus Wirth recebeu em 1984?", "Premio"),
        ("Quem criou a linguagem de programação Python?", "Pessoa"),
        ("Quais pessoas que trabalharam no Bell Labs receberam o Prêmio Turing?", "Pessoa"),
        ("Qual pessoa que trabalhou no CERN recebeu o Prêmio Turing?", "Pessoa"),
        ("Em qual organização a linguagem Java foi desenvolvida?", "Organizacao"),
        ("Em qual organização trabalhava um dos inventores do Smalltalk?", "Organizacao"),
        ("Que linguagens inspiraram o C++?", "Tecnologia"),
        ("Em que ano a linguagem C foi criada?", None),
        ("Onde Ken Thompson nasceu?", None),
        ("Por que a linguagem se chama C?", None),
    ],
)
def test_reconhece_o_tipo_pedido(pergunta, esperado):
    assert tipo_esperado(pergunta) == esperado


def test_maiusculas_e_acentos_nao_mudam_o_resultado():
    assert tipo_esperado("QUE PREMIO recebeu Dennis Ritchie?") == "Premio"


def test_tipos_sao_os_rotulos_do_dominio():
    dominio = json.loads((RAIZ / "neo4j" / "dominio.json").read_text(encoding="utf-8"))
    assert set(PALAVRAS_POR_TIPO) == {r["nome"] for r in dominio["rotulos"]}
