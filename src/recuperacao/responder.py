"""Ponto de entrada da recuperação: responder(pergunta, modo) (issue V1).

Por enquanto devolve o JSON de exemplo do contrato, validado, para a API e a
interface já trabalharem. A recuperação de verdade entra nas issues V2 a V5.
"""

import json
from pathlib import Path

from src.contrato import Resposta

RAIZ = Path(__file__).resolve().parents[2]
EXEMPLO = RAIZ / "data" / "exemplo_resposta.json"
AVISO_ESQUELETO = "Resposta de exemplo: a recuperação ainda não está ligada."


def responder(pergunta: str, modo: str = "graphrag") -> dict:
    """Responde a pergunta no formato do contrato (src/contrato.py)."""
    dados = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    dados["pergunta"] = pergunta
    dados["modo"] = modo
    if modo == "vetorial":
        dados["cypher"] = None
    dados["avisos"] = [*dados["avisos"], AVISO_ESQUELETO]
    return Resposta.model_validate(dados).model_dump()