"""Contexto numerado para o LLM e checagem das citações da resposta (issue V4).

O LLM recebe os caminhos do grafo como C1, C2... e os trechos como F1, F2...,
e cita cada afirmação com esses identificadores entre colchetes. Pelo contrato,
toda citação precisa existir em caminhos ou em fontes; citacoes_invalidas()
aponta as que não existem.
"""

import re

from neo4j import RoutingControl

MENSAGEM_SEM_INFORMACAO = "Não encontrei essa informação no dataset."

INSTRUCOES = f"""Você responde perguntas usando só o contexto fornecido.
O contexto tem caminhos do grafo de conhecimento, identificados como [C1], [C2]..., e trechos de documentos, identificados como [F1], [F2]....
Regras:
- Responda só com base no contexto. Não use conhecimento de fora dele.
- Cite cada afirmação com os identificadores entre colchetes, por exemplo [C1] ou [F1].
- Não invente identificadores: use só os que aparecem no contexto.
- Se o contexto não tiver a resposta, responda exatamente: {MENSAGEM_SEM_INFORMACAO}
- Responda em até 3 frases."""

CONSULTA_TRECHOS = """
MATCH (c:Chunk)-[:PART_OF]->(d:Document) WHERE c.id IN $ids
RETURN c.id AS chunk_id, c.text AS trecho, d.title AS documento, d.source AS url
"""

CITACAO = re.compile(r"\[([CF]\d+)\]")


def resolver_trechos(driver, chunk_ids: list[str]) -> list[dict]:
    """Texto, documento e URL dos trechos com esses ids (os que não existem ficam de fora)."""
    if not chunk_ids:
        return []
    registros, _, _ = driver.execute_query(
        CONSULTA_TRECHOS, ids=list(chunk_ids), routing_=RoutingControl.READ
    )
    return [registro.data() for registro in registros]


def _uma_linha(texto: str) -> str:
    return " ".join(texto.split())


def _caminho_como_texto(caminho: dict, nomes: dict, direcoes: set) -> str:
    """Ex.: "C++ -[INFLUENCIADA_POR]-> C <-[CRIOU]- Dennis Ritchie"."""
    ids = caminho["nos"]
    partes = [nomes.get(ids[0], ids[0])]
    for origem, destino, tipo in zip(ids, ids[1:], caminho["relacoes"]):
        if (origem, tipo, destino) in direcoes:
            partes.append(f"-[{tipo}]->")
        elif (destino, tipo, origem) in direcoes:
            partes.append(f"<-[{tipo}]-")
        else:
            partes.append(f"-[{tipo}]-")
        partes.append(nomes.get(destino, destino))
    return " ".join(partes)


def montar_contexto(caminhos: list[dict], subgrafo: dict, fontes: list[dict]) -> str:
    """Uma linha por caminho ("[C1] ...") e uma por fonte ("[F1] (documento) trecho")."""
    nomes = {no["id"]: no["nome"] for no in subgrafo["nos"]}
    direcoes = {(a["origem"], a["tipo"], a["destino"]) for a in subgrafo["arestas"]}
    linhas = [f"[{c['id']}] {_caminho_como_texto(c, nomes, direcoes)}" for c in caminhos]
    linhas += [f"[{f['id']}] ({f['documento']}) {_uma_linha(f['trecho'])}" for f in fontes]
    return "\n".join(linhas)


def citacoes_invalidas(texto: str, caminhos: list[dict], fontes: list[dict]) -> list[str]:
    """Ids citados no texto ([C1], [F1]...) que não existem em caminhos nem em fontes."""
    existentes = {c["id"] for c in caminhos} | {f["id"] for f in fontes}
    invalidas = []
    for citado in CITACAO.findall(texto):
        if citado not in existentes and citado not in invalidas:
            invalidas.append(citado)
    return invalidas
