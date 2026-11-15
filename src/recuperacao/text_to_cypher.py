"""Text-to-Cypher com validação antes de executar (issue V2).

O LLM gera uma consulta Cypher a partir da pergunta. O prompt traz o schema lido
de neo4j/dominio.json, os ids reais das entidades citadas na pergunta (achados
pelo índice fulltext entity_search) e três exemplos. A consulta ganha LIMIT 25
quando não tem, passa por EXPLAIN e só então executa, sempre em transação de
leitura: o banco recusa CREATE, MERGE, SET e DELETE. Se a consulta falhar, o LLM
recebe o erro e tem mais uma tentativa.

Os caminhos devolvidos saem no formato de expandir() (src/recuperacao/multi_hop.py),
para o responder juntá-los aos da expansão multi-hop.
"""

import json
import re
import string
from pathlib import Path

from neo4j import RoutingControl
from neo4j.exceptions import Neo4jError
from neo4j.graph import Path as CaminhoNeo4j

from src.recuperacao.llm import gerar_texto

RAIZ = Path(__file__).resolve().parents[2]
DOMINIO = json.loads((RAIZ / "neo4j" / "dominio.json").read_text(encoding="utf-8"))
RELACOES_DO_DOMINIO = frozenset(r["tipo"] for r in DOMINIO["relacoes"])

LIMITE_PADRAO = 25
ENTIDADES_POR_TERMO = 5
NOVAS_TENTATIVAS = 1

# Consulta 1 de neo4j/consultas/exemplos.cypher, com o top 5 por termo.
BUSCA_ENTIDADES = """
CALL db.index.fulltext.queryNodes('entity_search', $termo) YIELD node, score
RETURN node.id AS id, node.name AS nome, node.type AS tipo, score
ORDER BY score DESC
LIMIT $k
"""

# Pares (pergunta, Cypher) sobre o domínio, com os ids da semente.
EXEMPLOS = (
    (
        "Quem criou o Unix?",
        "MATCH p = (:Pessoa)-[:CRIOU]->(:Tecnologia {id: 'tecnologia:unix'}) RETURN p LIMIT 25",
    ),
    (
        "Que prêmios recebeu quem criou o C?",
        "MATCH p = (:Tecnologia {id: 'tecnologia:c'})<-[:CRIOU]-(:Pessoa)-[:RECEBEU]->(:Premio) "
        "RETURN p LIMIT 25",
    ),
    (
        "De quais linguagens o C++ descende, direta ou indiretamente?",
        "MATCH p = (:Tecnologia {id: 'tecnologia:c_mais_mais'})(()-[:INFLUENCIADA_POR]->()){1,4}"
        "(:Tecnologia) RETURN p LIMIT 25",
    ),
)

REGRAS = f"""Regras:
- Só leitura: use MATCH, WHERE, WITH, RETURN, ORDER BY e LIMIT. Nunca use CREATE, MERGE, SET, DELETE, REMOVE nem DETACH.
- Devolva caminhos: guarde o padrão numa variável p (MATCH p = ...) e termine com RETURN p, sem outras colunas.
- Ande só pelas relações do domínio, na direção indicada no schema. Não use MENTIONS, PART_OF nem NEXT no caminho.
- Use os ids das entidades encontradas exatamente como aparecem, ex.: {{id: '...'}}. Não invente ids.
- Saltos variáveis: no Neo4j 5.26 use o padrão quantificado, ex.: (a)(()-[:INFLUENCIADA_POR]->()){{1,4}}(b). [*1..4] com filtro de tipo não funciona.
- Use LIMIT de no máximo {LIMITE_PADRAO}.
- Responda só com a consulta Cypher, sem explicação e sem bloco de código."""


def _schema() -> str:
    """O schema do domínio em texto, lido de neo4j/dominio.json."""
    linhas = ["Rótulos do domínio (toda entidade tem o rótulo Entity mais um destes):"]
    for rotulo in DOMINIO["rotulos"]:
        linhas.append(
            f"- {rotulo['nome']} (id com prefixo '{rotulo['prefixo_id']}:'): {rotulo['descricao']}"
        )

    linhas.append("")
    linhas.append("Relações do domínio, sempre nesta direção:")
    for relacao in DOMINIO["relacoes"]:
        de = "|".join(relacao["de"])
        para = "|".join(relacao["para"])
        linhas.append(f"- (:{de})-[:{relacao['tipo']}]->(:{para}): {relacao['descricao']}")

    lexico = DOMINIO["grafo_lexico"]
    linhas.append("")
    linhas.append("Grafo léxico (propriedades de cada rótulo):")
    for rotulo, propriedades in lexico["rotulos"].items():
        linhas.append(f"- {rotulo}: {', '.join(propriedades)}")
    for relacao in lexico["relacoes"]:
        linhas.append(f"- {relacao}")
    for observacao in lexico["observacoes"]:
        linhas.append(f"- {observacao}")
    return "\n".join(linhas)


def _termos(pergunta: str) -> list[str]:
    """Palavras da pergunta sem a pontuação das pontas (mantém + e #, de C++ e C#)."""
    pontuacao = string.punctuation.replace("+", "").replace("#", "")
    termos = []
    for palavra in pergunta.split():
        termo = palavra.strip(pontuacao)
        if termo and termo not in termos:
            termos.append(termo)
    return termos


def _como_frase_lucene(termo: str) -> str:
    """O termo entre aspas, para o Lucene não ler + - : AND OR como operadores."""
    return '"' + termo.replace("\\", "\\\\").replace('"', '\\"') + '"'


def resolver_entidades(driver, pergunta: str) -> list[dict]:
    """Entidades com nome parecido com algum termo da pergunta (top 5 por termo).

    Devolve [{"id", "nome", "tipo", "score"}] sem repetição, do maior score para o
    menor, com o maior score de cada entidade entre os termos.
    """
    melhores: dict[str, dict] = {}
    for termo in _termos(pergunta):
        registros, _, _ = driver.execute_query(
            BUSCA_ENTIDADES,
            termo=_como_frase_lucene(termo),
            k=ENTIDADES_POR_TERMO,
            routing_=RoutingControl.READ,
        )
        for registro in registros:
            entidade = dict(registro)
            atual = melhores.get(entidade["id"])
            if atual is None or entidade["score"] > atual["score"]:
                melhores[entidade["id"]] = entidade
    return sorted(melhores.values(), key=lambda e: -e["score"])


def montar_prompt(
    pergunta: str,
    entidades: list[dict],
    erro: str | None = None,
    consulta_anterior: str | None = None,
) -> list[dict]:
    """Mensagens (formato chat) para o LLM gerar a Cypher da pergunta.

    Com erro, a mensagem do usuário traz a consulta anterior e o erro do Neo4j
    para o LLM corrigir.
    """
    exemplos = "\n\n".join(f"Pergunta: {p}\nCypher: {c}" for p, c in EXEMPLOS)
    sistema = (
        "Você traduz perguntas sobre história da computação em uma consulta Cypher "
        "para o Neo4j 5.26.\n\n"
        f"{_schema()}\n\n{REGRAS}\n\nExemplos:\n\n{exemplos}"
    )

    if entidades:
        linhas = [f"- {e['id']}: {e['nome']} ({e['tipo']})" for e in entidades]
        usuario = "Entidades encontradas pelo nome (ids reais no banco):\n" + "\n".join(linhas)
    else:
        usuario = "Nenhuma entidade encontrada pelo nome. Use os rótulos e as relações."
    usuario += f"\n\nPergunta: {pergunta}"
    if erro:
        usuario += (
            f"\n\nA consulta anterior falhou:\n{consulta_anterior or ''}\n"
            f"Erro do Neo4j: {erro}\nCorrija a consulta."
        )

    return [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]


def garantir_limit(consulta: str) -> str:
    """A consulta sem ; no fim e com LIMIT 25 quando ela não termina em LIMIT."""
    consulta = consulta.strip().rstrip(";").strip()
    if re.search(r"\bLIMIT\s+(\d+|\$\w+)$", consulta, re.IGNORECASE):
        return consulta
    return f"{consulta} LIMIT {LIMITE_PADRAO}"


def _mensagem(erro: Neo4jError) -> str:
    return erro.message or str(erro)


def validar_cypher(driver, consulta: str) -> str | None:
    """None se o Neo4j aceita a consulta (EXPLAIN, sem executar), senão a mensagem de erro."""
    try:
        driver.execute_query("EXPLAIN " + consulta, routing_=RoutingControl.READ)
    except Neo4jError as erro:
        return _mensagem(erro)
    return None


def _limpar_resposta(texto: str) -> str:
    """Tira o bloco de código (```cypher ... ```) quando o LLM o devolve."""
    texto = texto.strip()
    bloco = re.fullmatch(r"```[A-Za-z]*\s*(.*?)\s*```", texto, re.DOTALL)
    return bloco.group(1) if bloco else texto


def _do_dominio(caminho: CaminhoNeo4j) -> bool:
    """Só caminhos como os de expandir(): entidades ligadas por relações do domínio."""
    return bool(caminho.relationships) and all(
        "Entity" in no.labels for no in caminho.nodes
    ) and all(r.type in RELACOES_DO_DOMINIO for r in caminho.relationships)


def _no(no) -> dict:
    pagerank = no.get("pagerank")
    return {
        "id": no.get("id"),
        "nome": no.get("name"),
        "tipo": no.get("type"),
        "pagerank": 0.0 if pagerank is None else pagerank,
        "comunidade": no.get("community"),
    }


def _aresta(relacao) -> dict:
    return {
        "origem": relacao.start_node.get("id"),
        "destino": relacao.end_node.get("id"),
        "tipo": relacao.type,
        "fontes": list(relacao.get("source_chunk_ids") or []),
    }


def _caminhos(registros) -> list[dict]:
    """Os caminhos (Path) do resultado no formato de expandir(), sem repetir arestas.

    Não há trecho de origem nem score da busca: chunk_origem fica None e score 0.0.
    """
    caminhos: dict[frozenset, dict] = {}
    for registro in registros:
        for valor in registro.values():
            if not isinstance(valor, CaminhoNeo4j) or not _do_dominio(valor):
                continue
            arestas = [_aresta(r) for r in valor.relationships]
            chave = frozenset((a["origem"], a["tipo"], a["destino"]) for a in arestas)
            caminhos.setdefault(
                chave,
                {
                    "chunk_origem": None,
                    "nos": [_no(n) for n in valor.nodes],
                    "arestas": arestas,
                    "score": 0.0,
                },
            )
    return list(caminhos.values())


def _falha(erro: str) -> dict:
    return {"cypher": None, "caminhos": [], "erro": erro}


def gerar_e_executar(driver, pergunta: str, llm=gerar_texto) -> dict:
    """Gera a Cypher da pergunta, valida e executa em transação de leitura.

    Devolve {"cypher", "caminhos", "erro"}: a consulta executada e os caminhos
    dela, ou cypher None, caminhos vazios e a mensagem de erro. Uma consulta que
    falha na validação ou na execução volta ao LLM com o erro uma vez só. Nunca
    levanta exceção: a falha do Text-to-Cypher não pode derrubar a resposta.
    """
    try:
        entidades = resolver_entidades(driver, pergunta)
    except Exception as erro:
        return _falha(f"Falha ao buscar as entidades da pergunta ({type(erro).__name__}).")

    erro = None
    consulta = None
    for _ in range(1 + NOVAS_TENTATIVAS):
        try:
            texto = llm(montar_prompt(pergunta, entidades, erro, consulta))
        except Exception as falha_llm:
            return _falha(f"Falha ao chamar o LLM ({type(falha_llm).__name__}).")

        consulta = garantir_limit(_limpar_resposta(texto or ""))
        try:
            erro = validar_cypher(driver, consulta)
            if erro is not None:
                continue
            registros, _, _ = driver.execute_query(consulta, routing_=RoutingControl.READ)
        except Neo4jError as falha_neo4j:
            erro = _mensagem(falha_neo4j)
            continue
        except Exception as falha:
            return _falha(f"Falha ao executar a Cypher ({type(falha).__name__}).")
        return {"cypher": consulta, "caminhos": _caminhos(registros), "erro": None}

    return _falha(erro)
