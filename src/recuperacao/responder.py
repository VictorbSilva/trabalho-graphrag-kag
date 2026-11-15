"""Ponto de entrada da recuperação: responder(pergunta, modo).

Busca vetorial nos trechos (V1) e, no modo graphrag, expansão multi-hop a partir
deles (V3). O texto da resposta ainda é provisório: a geração com o LLM entra na
issue V4 e o cálculo da confiança na V5.
"""

from src.contrato import Resposta
from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.conexao import obter_driver
from src.recuperacao.embeddings import gerar_embedding
from src.recuperacao.multi_hop import expandir, montar_grafo

MODOS = ("graphrag", "vetorial")
AVISO_SEM_LLM = "Geração da resposta com o LLM ainda não ligada (issue V4)."


def responder(pergunta: str, modo: str = "graphrag", *, driver=None) -> dict:
    """Responde a pergunta no formato do contrato (src/contrato.py)."""
    if modo not in MODOS:
        raise ValueError(f"Modo inválido: {modo!r}. Use 'graphrag' ou 'vetorial'.")
    driver = driver or obter_driver()

    resultados = buscar_chunks(driver, gerar_embedding(pergunta), k=5)
    fontes = [{"id": f"F{i}", **r} for i, r in enumerate(resultados, 1)]

    if modo == "graphrag":
        brutos = expandir(
            driver,
            [r["chunk_id"] for r in resultados],
            limite=5,
            scores={r["chunk_id"]: r["score"] for r in resultados},
        )
        caminhos, subgrafo, nos_consultados = montar_grafo(brutos)
    else:
        caminhos, subgrafo, nos_consultados = [], {"nos": [], "arestas": []}, []

    dados = {
        "pergunta": pergunta,
        "modo": modo,
        "resposta": (
            f"Encontrei {len(caminhos)} caminhos no grafo e {len(fontes)} trechos relacionados."
        ),
        "confianca": {"valor": 0.0, "nivel": "baixa", "criterio": "Ainda não calculado (issue V5)."},
        "cypher": None,
        "caminhos": caminhos,
        "subgrafo": subgrafo,
        "nos_consultados": nos_consultados,
        "fontes": fontes,
        "avisos": [AVISO_SEM_LLM],
    }
    return Resposta.model_validate(dados).model_dump()
