"""Chat de terminal do agente Mentor (src/mentor/chat.py, issue #19).

Os testes sem o marcador `llm` usam um gerador falso passado por parâmetro, então
rodam sem chave e sem rede. O teste com `llm` chama a Abacus de verdade e é pulado
sem ABACUS_API_KEY no .env (tests/conftest.py).
"""

from pathlib import Path

import pytest

from src.mentor.chat import carregar_system_prompt, main, montar_mensagens, perguntar

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_PROMPT = RAIZ / "src" / "mentor" / "system_prompt.txt"


class GeradorFalso:
    """Guarda as mensagens recebidas e devolve uma resposta fixa."""

    def __init__(self, resposta="resposta do mentor"):
        self.resposta = resposta
        self.chamadas = []

    def __call__(self, mensagens):
        self.chamadas.append(mensagens)
        return self.resposta


def test_carregar_system_prompt_devolve_o_arquivo_oficial():
    esperado = ARQUIVO_PROMPT.read_text(encoding="utf-8").removesuffix("\n")
    prompt = carregar_system_prompt()
    assert prompt == esperado
    assert prompt.startswith("MENTOR TÉCNICO GRAPHRAG/KAG")


def test_montar_mensagens_sem_historico():
    prompt = carregar_system_prompt()
    assert montar_mensagens([], "pergunta") == [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "pergunta"},
    ]


def test_montar_mensagens_mantem_a_ordem_do_historico():
    historico = [
        {"role": "user", "content": "primeira"},
        {"role": "assistant", "content": "resposta da primeira"},
    ]
    mensagens = montar_mensagens(historico, "segunda")
    assert mensagens == [
        {"role": "system", "content": carregar_system_prompt()},
        {"role": "user", "content": "primeira"},
        {"role": "assistant", "content": "resposta da primeira"},
        {"role": "user", "content": "segunda"},
    ]


def test_perguntar_devolve_resposta_e_novo_historico():
    historico = [
        {"role": "user", "content": "antes"},
        {"role": "assistant", "content": "resposta de antes"},
    ]
    copia = [dict(m) for m in historico]
    falso = GeradorFalso("ok")

    resposta, novo = perguntar(historico, "p", gerar=falso)

    assert resposta == "ok"
    assert falso.chamadas == [montar_mensagens(copia, "p")]
    assert novo == copia + [
        {"role": "user", "content": "p"},
        {"role": "assistant", "content": "ok"},
    ]
    assert historico == copia


@pytest.mark.parametrize("pergunta", ["", "   ", "\n\t "])
def test_perguntar_vazia_levanta_erro_sem_chamar_o_gerador(pergunta):
    falso = GeradorFalso()
    with pytest.raises(ValueError):
        perguntar([], pergunta, gerar=falso)
    assert falso.chamadas == []


def test_main_uma_pergunta_imprime_a_resposta(capsys):
    falso = GeradorFalso("resposta única")
    assert main(["--uma", "p"], gerar=falso) == 0
    assert "resposta única" in capsys.readouterr().out
    assert len(falso.chamadas) == 1


def test_main_erro_do_llm_imprime_a_mensagem_e_devolve_1(capsys):
    def falha(mensagens):
        raise RuntimeError("ABACUS_API_KEY não definida.")

    assert main(["--uma", "p"], gerar=falha) == 1
    saida = capsys.readouterr()
    assert "ABACUS_API_KEY não definida." in saida.out + saida.err
    assert "Traceback" not in saida.out + saida.err


def test_main_interativo_encerra_com_sair(monkeypatch, capsys):
    entradas = iter(["primeira", "sair"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(entradas))
    falso = GeradorFalso("resposta interativa")

    assert main([], gerar=falso) == 0
    assert "resposta interativa" in capsys.readouterr().out
    assert len(falso.chamadas) == 1


@pytest.mark.llm
def test_perguntar_com_o_llm_real_devolve_texto():
    resposta, _ = perguntar([], "Em uma frase: para que serve um índice fulltext no Neo4j?")
    assert isinstance(resposta, str)
    assert resposta.strip()
