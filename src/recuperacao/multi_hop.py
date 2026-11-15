"""Expansão multi-hop a partir dos trechos da busca vetorial (issue V3).

Dos trechos chega às entidades citadas (MENTIONS) e anda de 1 a 3 saltos só
pelas relações do domínio, lidas de neo4j/dominio.json. montar_grafo() converte
os caminhos para o formato do contrato (src/contrato.py).
"""

import json
from pathlib import Path

from neo4j import RoutingControl

RAIZ = Path(__file__).resolve().parents[2]
DOMINIO = RAIZ / "neo4j" / "dominio.json"

RELACOES_DO_DOMINIO = tuple(
    r["tipo"] for r in json.loads(DOMINIO.read_text(encoding="utf-8"))["relacoes"]
)

# Tipos de relação e limite de saltos não podem ser parâmetro no Cypher. Entram no
# texto só os tipos lidos do dominio.json e um max_saltos já validado como int.
CONSULTA = """
MATCH (c:Chunk)-[:MENTIONS]->(inicio:Entity) WHERE c.id IN $chunk_ids
MATCH p = (inicio)(()-[:{tipos}]-()){{1,{max_saltos}}}(fim:Entity)
RETURN c.id AS chunk_origem,
       [n IN nodes(p) | {{id: n.id, nome: n.name, tipo: n.type,
                          pagerank: coalesce(n.pagerank, 0.0), comunidade: n.community}}] AS nos,
       [r IN relationships(p) | {{origem: startNode(r).id, destino: endNode(r).id, tipo: type(r),
                                  fontes: coalesce(r.source_chunk_ids, [])}}] AS arestas
LIMIT 2000
"""

CAMPOS_DO_NO = ("id", "nome", "tipo", "pagerank", "comunidade")


def _chave(arestas: list[dict]) -> frozenset:
    return frozenset((a["origem"], a["tipo"], a["destino"]) for a in arestas)


def _media_pagerank(caminho: dict) -> float:
    nos = caminho["nos"]
    return sum(n["pagerank"] for n in nos) / len(nos)


def expandir(
    driver,
    chunk_ids: list[str],
    max_saltos: int = 3,
    limite: int = 10,
    scores: dict[str, float] | None = None,
) -> list[dict]:
    """Caminhos de 1 a max_saltos saltos a partir das entidades citadas nos trechos.

    Cada caminho é {"chunk_origem", "nos", "arestas", "score"}, com o score do
    trecho de origem. Caminhos com o mesmo conjunto de arestas aparecem uma vez só
    (fica o de maior score). A ordem é por score, depois pela média do PageRank
    dos nós e por fim pelos caminhos mais curtos.
    """
    if isinstance(max_saltos, bool) or not isinstance(max_saltos, int) or not 1 <= max_saltos <= 3:
        raise ValueError("max_saltos precisa ser um inteiro entre 1 e 3.")
    if not chunk_ids:
        return []

    consulta = CONSULTA.format(tipos="|".join(RELACOES_DO_DOMINIO), max_saltos=max_saltos)
    registros, _, _ = driver.execute_query(
        consulta, chunk_ids=list(chunk_ids), routing_=RoutingControl.READ
    )

    scores = scores or {}
    melhores: dict[frozenset, dict] = {}
    for registro in registros:
        caminho = {
            "chunk_origem": registro["chunk_origem"],
            "nos": registro["nos"],
            "arestas": registro["arestas"],
            "score": scores.get(registro["chunk_origem"], 0.0),
        }
        chave = _chave(caminho["arestas"])
        if chave not in melhores or caminho["score"] > melhores[chave]["score"]:
            melhores[chave] = caminho

    ordenados = sorted(
        melhores.values(),
        key=lambda c: (-c["score"], -_media_pagerank(c), len(c["arestas"])),
    )
    return ordenados[:limite]


def montar_grafo(caminhos: list[dict]) -> tuple[list[dict], dict, list[str]]:
    """Converte os caminhos de expandir() para o contrato.

    Devolve (caminhos, subgrafo, nos_consultados): os caminhos com ids "C1",
    "C2"... e as fontes como a união ordenada das fontes das arestas; o subgrafo
    com nós e arestas sem repetição; e os ids dos nós do subgrafo.
    """
    caminhos_contrato = []
    nos: dict[str, dict] = {}
    arestas: dict[tuple, dict] = {}

    for i, caminho in enumerate(caminhos, 1):
        for no in caminho["nos"]:
            nos.setdefault(no["id"], {campo: no[campo] for campo in CAMPOS_DO_NO})

        fontes: set[str] = set()
        for aresta in caminho["arestas"]:
            fontes.update(aresta["fontes"])
            chave = (aresta["origem"], aresta["tipo"], aresta["destino"])
            if chave not in arestas:
                arestas[chave] = {
                    "origem": aresta["origem"],
                    "destino": aresta["destino"],
                    "tipo": aresta["tipo"],
                    "fontes": list(aresta["fontes"]),
                }
            else:
                juntas = arestas[chave]["fontes"]
                juntas.extend(f for f in aresta["fontes"] if f not in juntas)

        caminhos_contrato.append(
            {
                "id": f"C{i}",
                "nos": [no["id"] for no in caminho["nos"]],
                "relacoes": [aresta["tipo"] for aresta in caminho["arestas"]],
                "fontes": sorted(fontes),
            }
        )

    subgrafo = {"nos": list(nos.values()), "arestas": list(arestas.values())}
    nos_consultados = [no["id"] for no in subgrafo["nos"]]
    return caminhos_contrato, subgrafo, nos_consultados
