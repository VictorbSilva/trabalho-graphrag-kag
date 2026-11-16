"""Origem das respostas da API: JSON de exemplo ou a função responder() da recuperação."""

import importlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Callable

from src.api import config

Responder = Callable[[str, str], dict]


@lru_cache(maxsize=1)
def _exemplo() -> dict:
    with config.ARQUIVO_EXEMPLO.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def responder_exemplo(pergunta: str, modo: str) -> dict:
    """Devolve o JSON de exemplo do contrato, com a pergunta e o modo recebidos."""
    resposta = deepcopy(_exemplo())
    resposta["pergunta"] = pergunta
    resposta["modo"] = modo
    return resposta


def carregar_responder(fonte: str = config.FONTE, alvo: str = config.RESPONDER) -> Responder:
    """Escolhe a função que responde às perguntas conforme a configuração."""
    if fonte == "exemplo":
        return responder_exemplo
    if fonte == "recuperacao":
        if ":" not in alvo:
            raise ValueError(
                "Com API_FONTE=recuperacao, defina API_RESPONDER no formato 'modulo:funcao'."
            )
        modulo, funcao = alvo.split(":", 1)
        return getattr(importlib.import_module(modulo), funcao)
    raise ValueError("API_FONTE inválida. Use 'exemplo' ou 'recuperacao'.")


def verificar_neo4j() -> None:
    """Lança exceção se o Neo4j do .env não responder. Usada pela rota /saude.

    Usa o mesmo driver da recuperação (src.recuperacao.conexao), que lê NEO4J_URI e
    NEO4J_PASSWORD do .env. O import fica aqui dentro para o modo exemplo não precisar
    do driver do Neo4j instalado.
    """
    from src.recuperacao.conexao import obter_driver

    obter_driver().verify_connectivity()
