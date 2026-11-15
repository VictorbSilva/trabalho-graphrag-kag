"""Carga de data/semente/ no Neo4j com os embeddings do módulo único.

A demo e os testes da recuperação usam esta mesma função. Os embeddings vêm de
src/recuperacao/embeddings.py, o mesmo módulo usado na pergunta, e a escrita usa
a ingestão oficial (neo4j/consultas/ingestao_modelo.cypher), que faz MERGE pelo
id: carregar duas vezes não duplica nada.

Não carregue junto com data/processado/: a semente usa os mesmos ids de
documento e de trecho (ver data/semente/README.md).

Uso: python -m src.recuperacao.carregar_semente
"""

import json
from pathlib import Path

from src.recuperacao.conexao import obter_driver
from src.recuperacao.embeddings import gerar_embeddings

RAIZ = Path(__file__).resolve().parents[2]
PASTA_SEMENTE = RAIZ / "data" / "semente"
INGESTAO = RAIZ / "neo4j" / "consultas" / "ingestao_modelo.cypher"


def _comandos_cypher(caminho: Path) -> list[str]:
    """Comandos de um arquivo .cypher, sem as linhas de comentário."""
    linhas = [
        linha
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if not linha.strip().startswith("//")
    ]
    return [cmd.strip() for cmd in "\n".join(linhas).split(";") if cmd.strip()]


def _com_prefixo(artigo: dict, prefixo: str) -> dict:
    """Cópia do artigo com todos os ids prefixados (com prefixo "", os mesmos valores)."""
    p = prefixo
    return {
        "documento": {**artigo["documento"], "id": p + artigo["documento"]["id"]},
        "chunks": [{**c, "id": p + c["id"]} for c in artigo["chunks"]],
        "entidades": [
            {**e, "id": p + e["id"], "chunk_ids": [p + c for c in e["chunk_ids"]]}
            for e in artigo["entidades"]
        ],
        "relacoes": [
            {**r, "origem": p + r["origem"], "destino": p + r["destino"], "chunk_id": p + r["chunk_id"]}
            for r in artigo["relacoes"]
        ],
    }


def _contar(driver, consulta: str, prefixo: str) -> int:
    registros, _, _ = driver.execute_query(consulta, p=prefixo)
    return registros[0]["total"]


def carregar_semente_no_banco(driver, prefixo: str = "", gerar_vetores=gerar_embeddings) -> dict:
    """Ingere os arquivos de data/semente/ com o embedding de cada trecho.

    Devolve quantos documentos, trechos, entidades e relações de domínio com o
    prefixo existem no banco depois da carga.
    """
    comandos = _comandos_cypher(INGESTAO)
    for caminho in sorted(PASTA_SEMENTE.glob("*.json")):
        artigo = json.loads(caminho.read_text(encoding="utf-8"))
        vetores = gerar_vetores([c["text"] for c in artigo["chunks"]])
        chunks = [{**c, "embedding": v} for c, v in zip(artigo["chunks"], vetores)]
        payload = _com_prefixo({**artigo, "chunks": chunks}, prefixo)
        for comando in comandos:
            driver.execute_query(comando, payload)

    return {
        "documentos": _contar(
            driver, "MATCH (n:Document) WHERE n.id STARTS WITH $p RETURN count(n) AS total", prefixo
        ),
        "trechos": _contar(
            driver, "MATCH (n:Chunk) WHERE n.id STARTS WITH $p RETURN count(n) AS total", prefixo
        ),
        "entidades": _contar(
            driver, "MATCH (n:Entity) WHERE n.id STARTS WITH $p RETURN count(n) AS total", prefixo
        ),
        "relacoes": _contar(
            driver,
            """
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE a.id STARTS WITH $p AND b.id STARTS WITH $p AND type(r) <> 'MENTIONS'
            RETURN count(r) AS total
            """,
            prefixo,
        ),
    }


def main() -> None:
    contagens = carregar_semente_no_banco(obter_driver())
    print(json.dumps(contagens))
    print("Para calcular PageRank e comunidades: docker compose run --rm neo4j-gds")


if __name__ == "__main__":
    main()
