"""Plano B da demo (issue #33, PE7): respostas reais gravadas, sem banco nem LLM.

Com API_FONTE=gravado, a API responde às perguntas que o sistema real já respondeu e
que estão versionadas no repositório:

- docs/artigo/exemplo-resposta-real.json: a pergunta de exemplo do artigo (graphrag);
- data/avaliacao/resultados/respostas.json: as 15 perguntas de avaliação nos dois modos.

Toda resposta gravada leva um aviso dizendo que não foi gerada agora. Uma pergunta que
não está gravada recebe uma resposta do contrato explicando isso, com confiança baixa.
"""

import json
from copy import deepcopy
from functools import lru_cache

from src.api import config

ARQUIVO_EXEMPLO_REAL = config.RAIZ / "docs" / "artigo" / "exemplo-resposta-real.json"
ARQUIVO_AVALIACAO = config.RAIZ / "data" / "avaliacao" / "resultados" / "respostas.json"

AVISO_GRAVADA = (
    "Resposta gravada (plano B da demo): gerada antes pelo sistema real com o grafo semente, "
    "não agora."
)
AVISO_NAO_GRAVADA = "Pergunta fora do roteiro gravado (plano B da demo)."


def _chave(pergunta: str, modo: str) -> tuple[str, str]:
    """Ignora maiúsculas, espaços repetidos e o ponto de interrogação final."""
    return " ".join(pergunta.casefold().split()).rstrip(" ?"), modo


@lru_cache(maxsize=1)
def _gravadas() -> dict[tuple[str, str], dict]:
    respostas = [json.loads(ARQUIVO_EXEMPLO_REAL.read_text(encoding="utf-8"))]
    respostas += [
        item["resposta"]
        for item in json.loads(ARQUIVO_AVALIACAO.read_text(encoding="utf-8"))
        if item.get("resposta") and not item.get("erro")
    ]
    gravadas: dict[tuple[str, str], dict] = {}
    for resposta in respostas:
        gravadas.setdefault(_chave(resposta["pergunta"], resposta["modo"]), resposta)
    return gravadas


def perguntas_gravadas() -> list[tuple[str, str]]:
    """(pergunta, modo) de cada resposta gravada, na ordem dos arquivos."""
    return [(r["pergunta"], r["modo"]) for r in _gravadas().values()]


def responder_gravado(pergunta: str, modo: str) -> dict:
    gravada = _gravadas().get(_chave(pergunta, modo))
    if gravada is None:
        return {
            "pergunta": pergunta,
            "modo": modo,
            "resposta": (
                "Esta pergunta não está entre as respostas gravadas do plano B. "
                "Use uma das perguntas do roteiro da demo (docs/demo/roteiro.md), no mesmo modo."
            ),
            "confianca": {
                "valor": 0.0,
                "nivel": "baixa",
                "criterio": "plano B: nenhuma resposta gravada para esta pergunta e este modo",
            },
            "cypher": None,
            "caminhos": [],
            "subgrafo": {"nos": [], "arestas": []},
            "nos_consultados": [],
            "fontes": [],
            "avisos": [AVISO_NAO_GRAVADA],
        }
    resposta = deepcopy(gravada)
    resposta["pergunta"] = pergunta
    resposta["avisos"] = [*resposta.get("avisos", []), AVISO_GRAVADA]
    return resposta
