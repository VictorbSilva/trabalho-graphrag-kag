"""Camada de acesso aos dados: JSON local ou API HTTP."""

import json
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.interface.config import API_URL, ARQUIVO_EXEMPLO, FONTE_DADOS


def _validar_resposta(dados: dict) -> dict:
    """Verifica se o retorno contém os campos essenciais do contrato C3/C4."""
    campos = {
        "pergunta", "modo", "resposta", "confianca", "cypher",
        "caminhos", "subgrafo", "nos_consultados", "fontes", "avisos"
    }
    ausentes = campos.difference(dados.keys())
    if ausentes:
        raise ValueError(
            "A resposta não segue o contrato C3/C4. Campos ausentes: "
            + ", ".join(sorted(ausentes))
        )
    if not isinstance(dados["confianca"], dict):
        raise ValueError("O campo 'confianca' precisa ser um objeto JSON.")
    if not isinstance(dados["subgrafo"], dict):
        raise ValueError("O campo 'subgrafo' precisa ser um objeto JSON.")
    return dados


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
    """Envia pergunta e modo à API que implementará o contrato C4."""
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
        with urlopen(requisicao, timeout=30) as resposta_http:
            dados = json.loads(resposta_http.read().decode("utf-8"))
    except HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"A API respondeu com HTTP {erro.code}: {detalhe}"
        ) from erro
    except URLError as erro:
        raise RuntimeError(
            f"Não foi possível conectar à API em {API_URL}. "
            "Verifique se o backend está em execução."
        ) from erro
    except TimeoutError as erro:
        raise RuntimeError("A API demorou demais para responder.") from erro

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
