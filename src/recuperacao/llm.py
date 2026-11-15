"""Geração de texto com o LLM da Abacus RouteLLM (issue V4).

A RouteLLM tem API compatível com a da OpenAI, então o cliente é o SDK openai
apontado para a base da Abacus. A chave e o modelo vêm do .env (ABACUS_API_KEY e
ABACUS_MODELO). O timeout de 30 s fica abaixo dos 60 s da API (API_TIMEOUT_S).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

RAIZ = Path(__file__).resolve().parents[2]
BASE_URL = "https://routellm.abacus.ai/v1"
TIMEOUT_S = 30


def gerar_texto(mensagens: list[dict], timeout: float = TIMEOUT_S) -> str:
    """Manda as mensagens (formato chat da OpenAI) ao LLM e devolve o texto da resposta.

    timeout (em segundos) vai para o cliente; o padrão é o da resposta final.
    """
    load_dotenv(RAIZ / ".env")
    chave = os.getenv("ABACUS_API_KEY")
    modelo = os.getenv("ABACUS_MODELO")
    if not chave:
        raise RuntimeError("ABACUS_API_KEY não definida. Preencha a chave da Abacus no .env.")
    if not modelo:
        raise RuntimeError("ABACUS_MODELO não definido. Preencha o nome do modelo da Abacus no .env.")

    cliente = OpenAI(base_url=BASE_URL, api_key=chave, timeout=timeout)
    resposta = cliente.chat.completions.create(model=modelo, messages=mensagens, temperature=0)
    return resposta.choices[0].message.content.strip()
