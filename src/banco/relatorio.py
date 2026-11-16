"""Relatório de validação do grafo carregado no Neo4j (issue #13, N4).

Conta nós e relações, procura problemas de extração (relações sem trecho de
origem, entidades soltas, possíveis duplicatas) e lista as entidades de maior
PageRank e as comunidades do Louvain. Gera docs/relatorio-grafo.md.

Uso, depois de ingerir e rodar o GDS:
    python -m src.banco.ingestor
    docker compose run --rm neo4j-gds
    python -m src.banco.relatorio
"""

import argparse
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

from src.pipeline.baixar_artigos import gerar_slug

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_PADRAO = RAIZ / "docs" / "relatorio-grafo.md"
LIMITE_EXEMPLOS = 12  # mantém o relatório curto: listas longas viram contagem + exemplos

CONSULTAS = {
    "documentos": """
        MATCH (d:Document) WHERE d.id STARTS WITH $p
        OPTIONAL MATCH (c:Chunk)-[:PART_OF]->(d)
        OPTIONAL MATCH (c)-[:MENTIONS]->(e:Entity)
        RETURN d.id AS id, d.title AS titulo, count(DISTINCT c) AS trechos, count(DISTINCT e) AS entidades
        ORDER BY id""",
    "por_rotulo": """
        MATCH (e:Entity) WHERE e.id STARTS WITH $p
        UNWIND [r IN labels(e) WHERE r <> 'Entity'] AS rotulo
        RETURN rotulo, count(*) AS total ORDER BY total DESC, rotulo""",
    "por_relacao": """
        MATCH (a:Entity)-[r]->(b:Entity) WHERE a.id STARTS WITH $p AND b.id STARTS WITH $p
        RETURN type(r) AS tipo, count(*) AS total ORDER BY total DESC, tipo""",
    "sem_fonte": """
        MATCH (a:Entity)-[r]->(b:Entity) WHERE a.id STARTS WITH $p AND b.id STARTS WITH $p
          AND (r.source_chunk_ids IS NULL OR size(r.source_chunk_ids) = 0)
        RETURN a.name AS origem, type(r) AS tipo, b.name AS destino ORDER BY origem, tipo, destino""",
    "sem_relacao": """
        MATCH (e:Entity) WHERE e.id STARTS WITH $p AND NOT EXISTS { (e)--(:Entity) }
        RETURN e.name AS nome, e.type AS tipo ORDER BY tipo, nome""",
    "trechos_sem_entidade": """
        MATCH (c:Chunk) WHERE c.id STARTS WITH $p
        RETURN count(c) AS total, count(CASE WHEN NOT EXISTS { (c)-[:MENTIONS]->() } THEN 1 END) AS sem_entidade""",
    "entidades": """
        MATCH (e:Entity) WHERE e.id STARTS WITH $p
        RETURN e.id AS id, e.name AS nome, e.type AS tipo, coalesce(e.aliases, []) AS aliases ORDER BY id""",
    "top_pagerank": """
        MATCH (e:Entity) WHERE e.id STARTS WITH $p AND e.pagerank IS NOT NULL
        RETURN e.name AS nome, e.type AS tipo, e.pagerank AS pagerank
        ORDER BY pagerank DESC, nome LIMIT 5""",
    "comunidades": """
        MATCH (e:Entity) WHERE e.id STARTS WITH $p AND e.community IS NOT NULL
        WITH e.community AS comunidade, e ORDER BY e.pagerank DESC, e.name
        WITH comunidade, count(e) AS tamanho, collect(e.name)[..5] AS principais
        RETURN comunidade, tamanho, principais ORDER BY tamanho DESC, comunidade""",
}


def _linhas(driver, nome: str, prefixo: str) -> list[dict]:
    return [r.data() for r in driver.execute_query(CONSULTAS[nome], p=prefixo).records]


def possiveis_duplicatas(entidades: list[dict]) -> list[dict]:
    """Pares do mesmo tipo que podem ser a mesma coisa com ids diferentes."""
    pares = []
    for a, b in combinations(entidades, 2):
        if a["tipo"] != b["tipo"]:
            continue
        nome_a, nome_b = gerar_slug(a["nome"]), gerar_slug(b["nome"])
        apelidos_a = {gerar_slug(x) for x in a["aliases"]}
        apelidos_b = {gerar_slug(x) for x in b["aliases"]}
        motivo = None
        if nome_a == nome_b:
            motivo = "mesmo nome normalizado"
        elif nome_a in apelidos_b or nome_b in apelidos_a:
            motivo = "o nome de uma é apelido da outra"
        else:
            curto, longo = sorted((nome_a.split("_"), nome_b.split("_")), key=len)
            if len("".join(curto)) >= 4 and set(curto) < set(longo):
                motivo = "um nome contém o outro"
        if motivo:
            pares.append({"a": a["nome"], "b": b["nome"], "tipo": a["tipo"], "motivo": motivo})
    return pares


def coletar(driver, prefixo: str = "") -> dict:
    """Todos os números do relatório, só das entidades e documentos com ids que começam com o prefixo."""
    trechos = _linhas(driver, "trechos_sem_entidade", prefixo)[0]
    por_relacao = {r["tipo"]: r["total"] for r in _linhas(driver, "por_relacao", prefixo)}
    entidades = _linhas(driver, "entidades", prefixo)
    return {
        "documentos": _linhas(driver, "documentos", prefixo),
        "trechos": trechos["total"],
        "trechos_sem_entidade": trechos["sem_entidade"],
        "entidades": len(entidades),
        "relacoes": sum(por_relacao.values()),
        "por_rotulo": {r["rotulo"]: r["total"] for r in _linhas(driver, "por_rotulo", prefixo)},
        "por_relacao": por_relacao,
        "sem_fonte": _linhas(driver, "sem_fonte", prefixo),
        "sem_relacao": _linhas(driver, "sem_relacao", prefixo),
        "possiveis_duplicatas": possiveis_duplicatas(entidades),
        "top_pagerank": _linhas(driver, "top_pagerank", prefixo),
        "comunidades": _linhas(driver, "comunidades", prefixo),
    }


def gerar_markdown(dados: dict, origem: str, hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    gds = bool(dados["top_pagerank"])
    l = [
        "# Relatório do grafo carregado no Neo4j",
        "",
        f"Gerado em {hoje.strftime('%d/%m/%Y')} por `python -m src.banco.relatorio`, com o banco carregado a partir de "
        f"`{origem}` ({len(dados['documentos'])} artigos). Para atualizar, ingira os dados, rode o GDS e gere de novo "
        "(ver o cabeçalho de `src/banco/relatorio.py`).",
        "",
        "## Resumo",
        "",
        "| Documentos | Trechos | Entidades | Relações entre entidades | Comunidades |",
        "|---|---|---|---|---|",
        f"| {len(dados['documentos'])} | {dados['trechos']} | {dados['entidades']} | {dados['relacoes']} | "
        f"{len(dados['comunidades']) if gds else 'GDS não rodou'} |",
        "",
        "## Por documento",
        "",
        "| Documento | Trechos | Entidades mencionadas |",
        "|---|---|---|",
        *[f"| {d['titulo']} (`{d['id']}`) | {d['trechos']} | {d['entidades']} |" for d in dados["documentos"]],
        "",
        "## Entidades por rótulo",
        "",
        "| Rótulo | Entidades |",
        "|---|---|",
        *[f"| `{r}` | {n} |" for r, n in dados["por_rotulo"].items()],
        "",
        "## Relações por tipo",
        "",
        "| Relação | Quantidade |",
        "|---|---|",
        *[f"| `{t}` | {n} |" for t, n in dados["por_relacao"].items()],
        "",
        "## Qualidade da extração",
        "",
    ]

    sem_fonte = dados["sem_fonte"]
    l.append(f"- **Relações sem `source_chunk_ids`:** {len(sem_fonte)}"
             + (" (toda relação aponta para o trecho que a justifica)." if not sem_fonte else "."))
    l += [f"  - {r['origem']} `{r['tipo']}` {r['destino']}" for r in sem_fonte]
    l.append(f"- **Trechos que não mencionam nenhuma entidade:** {dados['trechos_sem_entidade']} de {dados['trechos']}.")
    soltas = dados["sem_relacao"]
    l.append(f"- **Entidades sem nenhuma relação de domínio:** {len(soltas)} de {dados['entidades']}"
             + (". Aparecem nos trechos, mas não se ligam a nenhuma outra entidade." if soltas else "."))
    if soltas:
        por_tipo: dict[str, list[str]] = {}
        for e in soltas:
            por_tipo.setdefault(e["tipo"], []).append(e["nome"])
        for tipo, nomes in sorted(por_tipo.items(), key=lambda t: -len(t[1])):
            exemplos = ", ".join(nomes[:LIMITE_EXEMPLOS]) + (", ..." if len(nomes) > LIMITE_EXEMPLOS else "")
            l.append(f"  - `{tipo}`: {len(nomes)} (ex.: {exemplos})")

    dup = dados["possiveis_duplicatas"]
    provaveis = [p for p in dup if p["motivo"] != "um nome contém o outro"]
    parecidas = [p for p in dup if p["motivo"] == "um nome contém o outro"]
    l.append(f"- **Prováveis duplicatas** (mesmo nome normalizado, ou o nome de uma é apelido da outra): "
             f"{len(provaveis)}" + (":" if provaveis else "."))
    l += [f"  - {p['a']} / {p['b']} (`{p['tipo']}`)" for p in provaveis]
    l.append(f"- **Nomes contidos um no outro:** {len(parecidas)} pares do mesmo tipo. Muitos são versões ou "
             "variantes legítimas (ex.: Java e Java SE), mas alguns podem ser a mesma entidade"
             + (":" if parecidas else "."))
    l += [f"  - {p['a']} / {p['b']} (`{p['tipo']}`)" for p in parecidas[:LIMITE_EXEMPLOS]]
    if len(parecidas) > LIMITE_EXEMPLOS:
        l.append(f"  - ... e mais {len(parecidas) - LIMITE_EXEMPLOS} pares")

    l += ["", "## Entidades mais importantes (PageRank)", ""]
    if gds:
        l += ["| # | Entidade | Rótulo | PageRank |", "|---|---|---|---|"]
        l += [f"| {i} | {e['nome']} | `{e['tipo']}` | {e['pagerank']:.3f} |"
              for i, e in enumerate(dados["top_pagerank"], 1)]
        com_mais_de_uma = sum(1 for c in dados["comunidades"] if c["tamanho"] > 1)
        l += ["", "## Comunidades (Louvain)", "",
              f"{len(dados['comunidades'])} comunidades, {com_mais_de_uma} delas com mais de uma entidade "
              "(as entidades sem relação ficam sozinhas). As maiores, com as entidades de maior PageRank de cada uma:", "",
              "| Comunidade | Entidades | Principais |", "|---|---|---|"]
        l += [f"| {c['comunidade']} | {c['tamanho']} | {', '.join(c['principais'])} |"
              for c in dados["comunidades"][:8]]
    else:
        l.append("O GDS ainda não rodou neste banco: `docker compose run --rm neo4j-gds`.")

    l += [
        "",
        "## Como conferir no Neo4j Browser",
        "",
        "```cypher",
        "MATCH (d:Document) RETURN count(d);",
        "MATCH (e:Entity) UNWIND [r IN labels(e) WHERE r <> 'Entity'] AS rotulo RETURN rotulo, count(*);",
        "MATCH (:Entity)-[r]->(:Entity) RETURN type(r), count(*);",
        "MATCH (:Entity)-[r]->(:Entity) WHERE r.source_chunk_ids IS NULL OR size(r.source_chunk_ids) = 0 RETURN count(r);",
        "MATCH (e:Entity) RETURN e.name, e.pagerank ORDER BY e.pagerank DESC LIMIT 5;",
        "```",
        "",
    ]
    return "\n".join(l)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.banco.relatorio",
                                     description="Gera o relatório de validação do grafo carregado no Neo4j.")
    parser.add_argument("--saida", default=str(SAIDA_PADRAO), help="arquivo Markdown de saída")
    parser.add_argument("--origem", default="data/processado/curado",
                        help="pasta de onde os dados foram ingeridos (só aparece no texto)")
    args = parser.parse_args(argv)

    from src.recuperacao.conexao import obter_driver

    dados = coletar(obter_driver())
    if not dados["documentos"]:
        print("O banco está vazio. Rode antes: python -m src.banco.ingestor")
        return 1
    saida = Path(args.saida)
    saida.write_text(gerar_markdown(dados, args.origem), encoding="utf-8")
    print(f"Relatório gravado em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
