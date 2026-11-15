"""Embeddings dos trechos e das perguntas (issue V1).

O mesmo módulo é usado pela ingestão (N3) e pela pergunta do usuário. Se cada
lado gerasse o vetor de um jeito, a busca compararia coisas diferentes.
"""

import json
from functools import lru_cache
from pathlib import Path

from sentence_transformers import SentenceTransformer

RAIZ = Path(__file__).resolve().parents[2]
NOME_DO_MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def dimensoes_do_indice() -> int:
    """Dimensão que o índice vetorial espera, lida do schema do domínio."""
    dominio = json.loads((RAIZ / "neo4j" / "dominio.json").read_text(encoding="utf-8"))
    return dominio["embedding"]["dimensoes"]


@lru_cache(maxsize=1)
def carregar_modelo() -> SentenceTransformer:
    modelo = SentenceTransformer(NOME_DO_MODELO)
    esperado = dimensoes_do_indice()
    gerado = modelo.get_embedding_dimension()
    if gerado != esperado:
        raise RuntimeError(
            f"O modelo gera vetores de {gerado} dimensões, mas o índice espera {esperado}."
        )
    return modelo


def gerar_embeddings(textos: list[str]) -> list[list[float]]:
    """Vetores normalizados de vários textos de uma vez (usado pela ingestão)."""
    vetores = carregar_modelo().encode(textos, normalize_embeddings=True, batch_size=32)
    return vetores.tolist()


def gerar_embedding(texto: str) -> list[float]:
    """Vetor normalizado de um texto (usado pela pergunta do usuário)."""
    return gerar_embeddings([texto])[0]