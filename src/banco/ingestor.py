"""Ingestor de comando único e idempotente (issue #12, N3).

Lê os JSON de artigo de uma pasta (formato `arquivo_por_artigo` de neo4j/dominio.json),
valida cada um contra o schema do domínio, calcula o embedding de cada trecho com o
módulo único (src/recuperacao/embeddings.py) e grava no Neo4j com a ingestão oficial
(neo4j/consultas/ingestao_modelo.cypher), um artigo por transação.

- Rodar duas vezes com a mesma pasta não muda as contagens: tudo é MERGE pelo id.
- Não apaga nada: o que saiu de um artigo extraído de novo continua no banco. Para trocar
  os dados, recrie o banco antes (ver neo4j/README.md).
- Arquivo inválido gera erro com o nome do arquivo e nada dele vai para o banco.
  Os outros artigos da pasta continuam sendo ingeridos.
- Arquivos manifesto*.json são ignorados (não são artigos).

Uso:
    python -m src.banco.ingestor                  # data/processado/extraido
    python -m src.banco.ingestor data/semente
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from neo4j.exceptions import Neo4jError

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / "data" / "processado" / "extraido"
INGESTAO = RAIZ / "neo4j" / "consultas" / "ingestao_modelo.cypher"
DOMINIO = RAIZ / "neo4j" / "dominio.json"


class ArquivoInvalido(Exception):
    """Arquivo de artigo fora do formato ou do schema do domínio."""

    def __init__(self, arquivo: str, erros: list[str]):
        self.arquivo = arquivo
        self.erros = erros
        super().__init__(f"{arquivo}: " + "; ".join(erros))


@dataclass
class Resultado:
    ingeridos: list[str] = field(default_factory=list)
    invalidos: dict[str, list[str]] = field(default_factory=dict)
    ignorados: list[str] = field(default_factory=list)
    contagens: dict[str, int] = field(default_factory=dict)


def carregar_dominio() -> dict:
    return json.loads(DOMINIO.read_text(encoding="utf-8"))


def comandos_cypher(caminho: Path = INGESTAO) -> list[str]:
    """Comandos de um arquivo .cypher, sem as linhas de comentário."""
    linhas = [
        linha
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if not linha.strip().startswith("//")
    ]
    return [cmd.strip() for cmd in "\n".join(linhas).split(";") if cmd.strip()]


def _texto(valor) -> bool:
    return isinstance(valor, str) and valor.strip() != ""


def validar_artigo(artigo, dominio: dict) -> list[str]:
    """Lista de problemas do artigo (vazia se ele pode ser ingerido)."""
    if not isinstance(artigo, dict):
        return ["o arquivo não é um objeto JSON"]
    faltando = [c for c in ("documento", "chunks", "entidades", "relacoes") if c not in artigo]
    if faltando:
        return [f"falta a chave '{c}'" for c in faltando]
    if not isinstance(artigo["documento"], dict):
        return ["'documento' precisa ser um objeto"]
    erros = [f"'{c}' precisa ser uma lista" for c in ("chunks", "entidades", "relacoes")
             if not isinstance(artigo[c], list)]
    if erros:
        return erros

    for campo in dominio["arquivo_por_artigo"]["documento"]:
        if not _texto(artigo["documento"].get(campo)):
            erros.append(f"documento.{campo} ausente ou vazio")

    # Trechos
    chunk_ids: set[str] = set()
    if not artigo["chunks"]:
        erros.append("o artigo não tem trechos")
    for i, c in enumerate(artigo["chunks"]):
        onde = f"chunks[{i}]"
        if not isinstance(c, dict):
            erros.append(f"{onde} não é um objeto")
            continue
        if not _texto(c.get("id")):
            erros.append(f"{onde}.id ausente ou vazio")
        elif c["id"] in chunk_ids:
            erros.append(f"{onde}.id '{c['id']}' repetido")
        else:
            chunk_ids.add(c["id"])
        if not isinstance(c.get("index"), int) or isinstance(c.get("index"), bool):
            erros.append(f"{onde}.index precisa ser um número inteiro")
        if not _texto(c.get("text")):
            erros.append(f"{onde}.text ausente ou vazio")

    # Entidades
    prefixos = {r["nome"]: r["prefixo_id"] for r in dominio["rotulos"]}
    tipo_de: dict[str, str] = {}
    for i, e in enumerate(artigo["entidades"]):
        onde = f"entidades[{i}]"
        if not isinstance(e, dict):
            erros.append(f"{onde} não é um objeto")
            continue
        eid, tipo = e.get("id"), e.get("type")
        if not _texto(eid):
            erros.append(f"{onde}.id ausente ou vazio")
            continue
        onde = f"entidade '{eid}'"
        if eid in tipo_de:
            erros.append(f"{onde} aparece duas vezes no arquivo")
        if not _texto(e.get("name")):
            erros.append(f"{onde}: name ausente ou vazio")
        if tipo not in prefixos:
            erros.append(f"{onde}: tipo '{tipo}' fora do schema (válidos: {', '.join(prefixos)})")
        elif not eid.startswith(prefixos[tipo] + ":"):
            erros.append(f"{onde}: o id deveria começar com '{prefixos[tipo]}:'")
        if not isinstance(e.get("aliases"), list) or not all(isinstance(a, str) for a in e["aliases"]):
            erros.append(f"{onde}: aliases precisa ser uma lista de textos")
        if e.get("description") is not None and not isinstance(e["description"], str):
            erros.append(f"{onde}: description precisa ser texto ou null")
        if not isinstance(e.get("chunk_ids"), list):
            erros.append(f"{onde}: chunk_ids precisa ser uma lista")
        else:
            for chunk_id in e["chunk_ids"]:
                if chunk_id not in chunk_ids:
                    erros.append(f"{onde}: chunk_id '{chunk_id}' não existe no arquivo")
        tipo_de[eid] = tipo

    # Relações
    regras = {r["tipo"]: r for r in dominio["relacoes"]}
    for i, r in enumerate(artigo["relacoes"]):
        onde = f"relacoes[{i}]"
        if not isinstance(r, dict):
            erros.append(f"{onde} não é um objeto")
            continue
        tipo, origem, destino = r.get("tipo"), r.get("origem"), r.get("destino")
        onde = f"relação {origem} {tipo} {destino}"
        if tipo not in regras:
            erros.append(f"{onde}: tipo '{tipo}' fora do schema (válidos: {', '.join(regras)})")
        for papel, ponta in (("origem", origem), ("destino", destino)):
            if ponta not in tipo_de:
                erros.append(f"{onde}: {papel} '{ponta}' não está nas entidades do arquivo")
        if tipo in regras and origem in tipo_de and destino in tipo_de:
            if tipo_de[origem] not in regras[tipo]["de"] or tipo_de[destino] not in regras[tipo]["para"]:
                erros.append(
                    f"{onde}: direção fora do schema ({tipo_de[origem]} -> {tipo_de[destino]}; "
                    f"o domínio pede {'/'.join(regras[tipo]['de'])} -> {'/'.join(regras[tipo]['para'])})"
                )
        if r.get("chunk_id") not in chunk_ids:
            erros.append(f"{onde}: chunk_id '{r.get('chunk_id')}' não existe no arquivo")
    return erros


def com_prefixo(artigo: dict, prefixo: str) -> dict:
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


def ingerir_artigo(driver, artigo: dict, comandos: list[str] | None = None) -> None:
    """Grava um artigo (já com os embeddings) numa única transação: entra tudo ou nada."""
    comandos = comandos or comandos_cypher()

    def escrever(tx):
        for comando in comandos:
            tx.run(comando, artigo).consume()

    with driver.session() as sessao:
        sessao.execute_write(escrever)


def contar(driver, prefixo: str = "") -> dict[str, int]:
    """Documentos, trechos, entidades e relações entre entidades com ids que começam com o prefixo."""
    consultas = {
        "documentos": "MATCH (n:Document) WHERE n.id STARTS WITH $p RETURN count(n) AS total",
        "trechos": "MATCH (n:Chunk) WHERE n.id STARTS WITH $p RETURN count(n) AS total",
        "entidades": "MATCH (n:Entity) WHERE n.id STARTS WITH $p RETURN count(n) AS total",
        "relacoes": """MATCH (a:Entity)-[r]->(b:Entity)
                       WHERE a.id STARTS WITH $p AND b.id STARTS WITH $p
                       RETURN count(r) AS total""",
    }
    return {
        nome: driver.execute_query(consulta, p=prefixo).records[0]["total"]
        for nome, consulta in consultas.items()
    }


def ingerir_pasta(driver, pasta: Path, prefixo: str = "", gerar_vetores=None) -> Resultado:
    """Valida e ingere todos os artigos de uma pasta. Devolve o que entrou, o que não entrou e as contagens."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")
    if gerar_vetores is None:
        from src.recuperacao.embeddings import gerar_embeddings as gerar_vetores

    dominio = carregar_dominio()
    dimensoes = dominio["embedding"]["dimensoes"]
    comandos = comandos_cypher()
    resultado = Resultado()

    for caminho in sorted(pasta.glob("*.json")):
        if caminho.name.startswith("manifesto"):
            resultado.ignorados.append(caminho.name)
            continue
        try:
            artigo = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            resultado.invalidos[caminho.name] = [f"JSON mal formado: {erro}"]
            continue
        erros = validar_artigo(artigo, dominio)
        if erros:
            resultado.invalidos[caminho.name] = erros
            continue

        vetores = gerar_vetores([c["text"] for c in artigo["chunks"]])
        if len(vetores) != len(artigo["chunks"]) or any(len(v) != dimensoes for v in vetores):
            raise ValueError(f"O gerador de embeddings não devolveu um vetor de {dimensoes} posições por trecho.")
        chunks = [{**c, "embedding": list(v)} for c, v in zip(artigo["chunks"], vetores)]
        try:
            ingerir_artigo(driver, com_prefixo({**artigo, "chunks": chunks}, prefixo), comandos)
        except Neo4jError as erro:
            resultado.invalidos[caminho.name] = [f"o Neo4j recusou o artigo: {erro.message}"]
            continue
        resultado.ingeridos.append(caminho.name)

    resultado.contagens = contar(driver, prefixo)
    return resultado


def main(argv: list[str] | None = None, gerar_vetores=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.banco.ingestor",
        description="Ingere no Neo4j os JSON de artigo de uma pasta (idempotente).",
    )
    parser.add_argument("pasta", nargs="?", default=str(PASTA_PADRAO),
                        help="pasta com um JSON por artigo (padrão: data/processado/extraido)")
    parser.add_argument("--prefixo", default="",
                        help="texto adicionado a todos os ids, para carregar uma cópia separada (ex.: testes)")
    args = parser.parse_args(argv)

    from src.recuperacao.conexao import obter_driver

    pasta = Path(args.pasta)
    print(f"Ingerindo os artigos de {pasta}")
    try:
        resultado = ingerir_pasta(obter_driver(), pasta, prefixo=args.prefixo, gerar_vetores=gerar_vetores)
    except FileNotFoundError as erro:
        print(erro)
        return 1

    for nome in resultado.ingeridos:
        print(f"  ok        {nome}")
    for nome in resultado.ignorados:
        print(f"  ignorado  {nome} (não é artigo)")
    for nome, erros in resultado.invalidos.items():
        print(f"  INVÁLIDO  {nome}: nada deste arquivo foi gravado")
        for erro in erros[:10]:
            print(f"            - {erro}")
        if len(erros) > 10:
            print(f"            ... e mais {len(erros) - 10} problema(s)")
    if not resultado.ingeridos and not resultado.invalidos:
        print("  Nenhum artigo encontrado.")

    c = resultado.contagens
    filtro = f" (ids com o prefixo '{args.prefixo}')" if args.prefixo else ""
    print(
        f"\nNo banco{filtro}: {c['documentos']} documentos, {c['trechos']} trechos, "
        f"{c['entidades']} entidades e {c['relacoes']} relações entre entidades."
    )
    print("Para calcular PageRank e comunidades: docker compose run --rm neo4j-gds")
    return 1 if resultado.invalidos or not resultado.ingeridos else 0


if __name__ == "__main__":
    sys.exit(main())
