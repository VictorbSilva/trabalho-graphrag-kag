"""Nível de confiança da resposta a partir de sinais observáveis (issue V5).

A regra está documentada em docs/confianca.md. O score do índice vetorial do
Neo4j (cosseno) vem convertido para 0 a 1 como (1 + cosseno) / 2, então a
regra volta para o cosseno com 2 * score - 1 antes de usar.
"""

LIMITE_ALTA = 0.7
LIMITE_MEDIA = 0.4
PENALIDADE_CYPHER = 0.1


def _nivel(valor: float) -> str:
    if valor >= LIMITE_ALTA:
        return "alta"
    if valor >= LIMITE_MEDIA:
        return "media"
    return "baixa"


def calcular_confianca(
    *,
    melhor_score: float | None,
    caminhos: int,
    caminhos_com_fonte: int,
    cypher_ok: bool | None = None,
    sem_contexto: bool = False,
) -> dict:
    """Devolve {valor, nivel, criterio} no formato de Confianca (src/contrato.py)."""
    cosseno = max(0.0, 2 * melhor_score - 1) if melhor_score is not None else 0.0

    if sem_contexto:
        valor = 0.0
    elif caminhos > 0:
        valor = 0.5 * cosseno + 0.5 * (caminhos_com_fonte / caminhos)
    else:
        valor = 0.7 * cosseno

    if cypher_ok is False:
        valor -= PENALIDADE_CYPHER

    valor = round(min(1.0, max(0.0, valor)), 2)

    partes = []
    if sem_contexto:
        partes.append("sem contexto recuperado")
    if melhor_score is None:
        partes.append(f"score ausente (cosseno {cosseno:.2f})")
    else:
        partes.append(f"score {melhor_score:.2f} (cosseno {cosseno:.2f})")
    if caminhos > 0:
        partes.append(f"{caminhos_com_fonte} de {caminhos} caminhos com trecho de origem")
    else:
        partes.append("0 caminhos no grafo (só busca vetorial)")
    if cypher_ok is False:
        partes.append(f"Cypher com erro (menos {PENALIDADE_CYPHER})")

    return {"valor": valor, "nivel": _nivel(valor), "criterio": ", ".join(partes)}
