"""Camada de acesso aos dados: JSON local ou API HTTP."""

import json
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pydantic import ValidationError
from src.contrato import Resposta

from src.interface.config import (
    API_URL,
    API_TIMEOUT_S_INTERFACE,
    ARQUIVO_EXEMPLO,
    FONTE_DADOS,
)

def _validar_resposta(dados: dict) -> dict:
    """Valida os dados utilizando o contrato oficial."""
    try:
        resposta = Resposta.model_validate(dados)
        return resposta.model_dump()
    except ValidationError as erro:
        raise ValueError(
            "A resposta recebida não segue o contrato oficial: "
            + str(erro)
        ) from erro

def carregar_exemplo(pergunta: str, modo: str) -> dict:
    """Carrega o JSON estático para desenvolver a interface sem depender da API."""
    if not ARQUIVO_EXEMPLO.exists():
        raise FileNotFoundError(
            f"Arquivo de demonstração não encontrado: {ARQUIVO_EXEMPLO}"
        )

    with ARQUIVO_EXEMPLO.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    dados = deepcopy(dados)
    dados["pergunta"] = pergunta
    dados["modo"] = modo
    return _validar_resposta(dados)

def consultar_api(pergunta: str, modo: str) -> dict:
    """Envia pergunta e modo à API utilizando o contrato oficial."""
    payload = json.dumps(
        {"pergunta": pergunta, "modo": modo},
        ensure_ascii=False
    ).encode("utf-8")

    requisicao = Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )

    try:
        with urlopen(requisicao, timeout=API_TIMEOUT_S_INTERFACE) as resposta_http:
            dados = json.loads(resposta_http.read().decode("utf-8"))

    except HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")

        try:
            conteudo = json.loads(corpo)
            detalhe = (
                conteudo.get("erro", corpo)
                if isinstance(conteudo, dict)
                else corpo
            )
        except json.JSONDecodeError:
            detalhe = corpo

        raise RuntimeError(
            f"Erro HTTP {erro.code}: {detalhe}"
        ) from erro

    except URLError as erro:
        raise RuntimeError(
            f"Não foi possível conectar à API em {API_URL}. "
            "Verifique se o backend está em execução."
        ) from erro

    except TimeoutError as erro:
        raise RuntimeError(
            "A API demorou demais para responder."
        ) from erro

    return _validar_resposta(dados)

def responder(pergunta: str, modo: str) -> dict:
    """Seleciona a fonte configurada sem alterar a tela."""
    if FONTE_DADOS == "json":
        return carregar_exemplo(pergunta, modo)
    if FONTE_DADOS == "api":
        return consultar_api(pergunta, modo)
    raise ValueError(
        "FONTE_DADOS inválida. Utilize 'json' ou 'api' no arquivo de ambiente."
    )
