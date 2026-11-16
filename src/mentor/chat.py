"""Chat de terminal com o agente Mentor (issue #19).

O system prompt é o oficial da seção 2 do enunciado, lido sem alterações de
src/mentor/system_prompt.txt. O LLM é o mesmo da recuperação (Abacus RouteLLM, via
gerar_texto de src/recuperacao/llm.py, temperatura 0). O Mentor orienta: explica
conceitos, corrige modelagens e sugere estratégias de depuração, mas não gera o
código da solução do projeto (o próprio prompt proíbe).

Uso:
    python -m src.mentor.chat                     conversa interativa
    python -m src.mentor.chat --uma "pergunta"    responde uma vez e sai
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

PROMPT = Path(__file__).with_name("system_prompt.txt")
TIMEOUT_S = 60  # respostas do Mentor são mais longas que as da recuperação (30 s)
COMANDO_SAIR = "sair"

Gerador = Callable[[list[dict]], str]


def carregar_system_prompt() -> str:
    """Devolve o system prompt oficial, só sem a quebra de linha final do arquivo."""
    return PROMPT.read_text(encoding="utf-8").removesuffix("\n")


def montar_mensagens(historico: list[dict], pergunta: str) -> list[dict]:
    """Monta as mensagens no formato chat: system, histórico e a nova pergunta."""
    return [
        {"role": "system", "content": carregar_system_prompt()},
        *historico,
        {"role": "user", "content": pergunta},
    ]


def _gerar_com_abacus(mensagens: list[dict]) -> str:
    from src.recuperacao.llm import gerar_texto

    return gerar_texto(mensagens, timeout=TIMEOUT_S)


def perguntar(
    historico: list[dict], pergunta: str, gerar: Gerador | None = None
) -> tuple[str, list[dict]]:
    """Faz uma pergunta ao Mentor e devolve (resposta, novo_historico).

    O histórico recebido não é modificado. gerar recebe as mensagens e devolve o
    texto; sem ele, usa o LLM da Abacus.
    """
    if not pergunta.strip():
        raise ValueError("A pergunta está vazia.")
    gerar = gerar or _gerar_com_abacus
    resposta = gerar(montar_mensagens(historico, pergunta))
    novo_historico = [
        *historico,
        {"role": "user", "content": pergunta},
        {"role": "assistant", "content": resposta},
    ]
    return resposta, novo_historico


def _conversar(gerar: Gerador | None) -> None:
    print(f"Mentor GraphRAG/KAG. Digite '{COMANDO_SAIR}' ou deixe a linha vazia para encerrar.")
    historico: list[dict] = []
    while True:
        try:
            pergunta = input("Você: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not pergunta.strip() or pergunta.strip().lower() == COMANDO_SAIR:
            return
        resposta, historico = perguntar(historico, pergunta, gerar=gerar)
        print(f"\nMentor: {resposta}\n")


def main(argv: list[str] | None = None, gerar: Gerador | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.mentor.chat",
        description="Conversa com o agente Mentor (system prompt oficial do enunciado).",
    )
    parser.add_argument("--uma", metavar="PERGUNTA", help="responde uma pergunta e sai")
    args = parser.parse_args(argv)

    try:
        if args.uma is not None:
            resposta, _ = perguntar([], args.uma, gerar=gerar)
            print(resposta)
        else:
            _conversar(gerar)
    except Exception as erro:  # chave faltando, falha do cliente, pergunta vazia...
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
