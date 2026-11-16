
"""PA4-B: resolução conservadora de entidades por mapeamentos explícitos.

Não consulta LLM/Neo4j e NÃO altera data/processado/extraido/.
Os arquivos gerados em .cache/pa4_previa/ são apenas prévias, NÃO prontos para
importação: relações rejeitadas/pendentes continuam presentes até a curadoria.

Uso na raiz do repositório:
    python src/pipeline/resolucao_entidades.py
"""

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA_PADRAO = RAIZ / "data" / "processado" / "extraido"
MAPEAMENTOS_PADRAO = RAIZ / "data" / "avaliacao" / "equivalencias_entidades_pa4.json"
SAIDA_PADRAO = RAIZ / ".cache" / "pa4_previa"
RELATORIO_PADRAO = RAIZ / ".cache" / "resolucao_entidades.json"


def ler_artigos(pasta: Path) -> dict[str, dict]:
    arquivos = sorted(pasta.glob("*.json")) if pasta.is_dir() else []

    if not arquivos:
        raise ValueError(f"Nenhum JSON de extração em {pasta}")

    artigos = {}

    for arquivo in arquivos:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        artigo = dados.get("documento", {}).get("id")

        if artigo != arquivo.stem:
            raise ValueError(
                f"ID do documento não corresponde ao nome do arquivo: {arquivo.name}"
            )

        artigos[artigo] = dados

    return artigos


def _distintos(itens):
    vistos, resultado = set(), []

    for item in itens:
        if not isinstance(item, str):
            continue

        item = item.strip()

        if item and item.casefold() not in vistos:
            vistos.add(item.casefold())
            resultado.append(item)

    return resultado


def resolver(artigos: dict[str, dict], regras: dict) -> tuple[dict[str, dict], dict]:
    """Une IDs apenas com justificativa explícita; preserva todas as evidências.

    Permite regras em cadeia, rejeita ciclos, IDs com tipos conflitantes e
    relações cujos extremos ou evidências sejam inválidos.

    Equivalências com origem ausente são ignoradas e registradas no relatório.
    Se a origem existir, o destino também deverá existir.
    """

    todas = defaultdict(list)

    for artigo, dados in artigos.items():
        for entidade in dados.get("entidades", []):
            if not isinstance(entidade, dict) or not isinstance(
                entidade.get("id"), str
            ):
                raise ValueError(f"Entidade inválida em {artigo}")

            todas[entidade["id"]].append(entidade)

    tipos = {}

    for ident, registros in todas.items():
        valores = {r.get("type") for r in registros}

        if len(valores) != 1 or None in valores:
            raise ValueError(
                f"Tipos conflitantes/ausentes para a entidade {ident}"
            )

        tipos[ident] = next(iter(valores))

    # ---------------------------------------------------------
    # PA5: resolução compatível com extrações progressivas
    # ---------------------------------------------------------

    mapeamento = {}
    motivos = {}
    equivalencias_ignoradas = []

    for regra in regras.get("equivalencias", []):
        origem, destino = regra.get("de"), regra.get("para")
        justificativa = str(regra.get("justificativa", "")).strip()

        # Uma equivalência antiga pode não existir na extração atual.
        # Nesse caso, ela é ignorada apenas nesta execução.
        if origem not in tipos:
            equivalencias_ignoradas.append({
                "de": origem,
                "para": destino,
                "motivo": "ID de origem ausente nos artigos processados"
            })
            continue

        # Se a origem existe, o destino precisa existir também.
        if destino not in tipos:
            raise ValueError(
                f"Destino da equivalência não encontrado: {origem} -> {destino}"
            )

        if origem == destino or origem in mapeamento:
            raise ValueError(
                f"Equivalência repetida ou reflexiva: {origem}"
            )

        if tipos[origem] != tipos[destino]:
            raise ValueError(
                f"Tentativa de unir tipos diferentes: {origem} -> {destino}"
            )

        if not justificativa:
            raise ValueError(
                f"Equivalência sem justificativa: {origem} -> {destino}"
            )

        mapeamento[origem] = destino
        motivos[origem] = justificativa

    def canonico(ident):
        visitados = set()
        atual = ident

        while atual in mapeamento:
            if atual in visitados:
                raise ValueError(
                    f"Ciclo de equivalências envolvendo {atual}"
                )

            visitados.add(atual)
            atual = mapeamento[atual]

        return atual

    for ident in mapeamento:
        canonico(ident)

    # Um registro do ID canônico é a fonte preferencial
    # para o nome principal.
    nomes = {}

    for ident in todas:
        if canonico(ident) == ident:
            nomes[ident] = next(
                (
                    r.get("name")
                    for r in todas[ident]
                    if r.get("name")
                ),
                ident
            )

    aliases_globais = defaultdict(list)

    for ident, registros in todas.items():
        alvo = canonico(ident)

        for e in registros:
            aliases_globais[alvo].extend([
                e.get("name", ""),
                *(e.get("aliases") or [])
            ])

    for ident in aliases_globais:
        aliases_globais[ident] = [
            x
            for x in _distintos(aliases_globais[ident])
            if x.casefold() != nomes[ident].casefold()
        ]

    resultado = {}

    relacoes_antes = 0
    relacoes_depois = 0
    entidades_antes = 0
    entidades_depois = 0

    for artigo, dados in sorted(artigos.items()):
        copia = deepcopy(dados)
        chunks = {c["id"] for c in copia.get("chunks", [])}

        agrupadas = {}

        entidades_antes += len(
            copia.get("entidades", [])
        )

        for e in copia.get("entidades", []):
            alvo = canonico(e["id"])

            if alvo not in agrupadas:
                agrupadas[alvo] = dict(e)
                agrupadas[alvo]["id"] = alvo
                agrupadas[alvo]["name"] = nomes[alvo]
                agrupadas[alvo]["aliases"] = aliases_globais[alvo][:]
                agrupadas[alvo]["chunk_ids"] = []

            registro = agrupadas[alvo]

            registro["chunk_ids"] = _distintos(
                registro["chunk_ids"]
                + list(e.get("chunk_ids") or [])
            )

            # Preferir a descrição do registro canônico
            # quando houver fusão.
            if e["id"] == alvo and e.get("description"):
                registro["description"] = e["description"]

        for e in agrupadas.values():
            if not set(e["chunk_ids"]).issubset(chunks):
                raise ValueError(
                    f"Entidade com chunk inválido em {artigo}: {e['id']}"
                )

        copia["entidades"] = sorted(
            agrupadas.values(),
            key=lambda e: e["id"]
        )

        entidades_depois += len(copia["entidades"])

        novas, chaves = [], set()

        for r in copia.get("relacoes", []):
            relacoes_antes += 1

            if r.get("origem") not in todas or r.get("destino") not in todas:
                raise ValueError(
                    f"Relação com ID desconhecido em {artigo}: {r}"
                )

            rr = dict(r)

            rr["origem"] = canonico(rr["origem"])
            rr["destino"] = canonico(rr["destino"])

            if rr["origem"] not in agrupadas or rr["destino"] not in agrupadas:
                raise ValueError(
                    f"Relação sem entidade local em {artigo}: {rr}"
                )

            if rr.get("chunk_id") not in chunks:
                raise ValueError(
                    f"Relação sem chunk em {artigo}: {rr}"
                )

            chave = (
                rr["origem"],
                rr["destino"],
                rr.get("tipo"),
                rr["chunk_id"]
            )

            if chave not in chaves:
                chaves.add(chave)
                novas.append(rr)

        copia["relacoes"] = novas
        relacoes_depois += len(novas)

        resultado[artigo] = copia

    unificacoes = [
        {
            "de": origem,
            "para": canonico(origem),
            "justificativa": motivos[origem]
        }
        for origem in sorted(mapeamento)
    ]

    relatorio = {
        "resumo": {
            "artigos": len(artigos),
            "registros_entidades_antes": entidades_antes,
            "registros_entidades_depois": entidades_depois,
            "ids_distintos_antes": len(todas),
            "ids_distintos_depois": len({
                canonico(i) for i in todas
            }),
            "relacoes_antes": relacoes_antes,
            "relacoes_depois": relacoes_depois,
            "equivalencias_explicitas": len(unificacoes),
            "equivalencias_ignoradas": len(equivalencias_ignoradas)
        },
        "unificacoes": unificacoes,
        "equivalencias_ignoradas": equivalencias_ignoradas,
        "aviso": (
            "PREVIA NAO CURADA: relações rejeitadas e pendentes "
            "continuam presentes. NAO importar para o Neo4j."
        )
    }

    return resultado, relatorio


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PA4-B: prévia de resolução de entidades, "
            "sem alterar entradas."
        )
    )

    parser.add_argument(
        "--entrada",
        type=Path,
        default=ENTRADA_PADRAO
    )

    parser.add_argument(
        "--mapeamentos",
        type=Path,
        default=MAPEAMENTOS_PADRAO
    )

    parser.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO
    )

    parser.add_argument(
        "--relatorio",
        type=Path,
        default=RELATORIO_PADRAO
    )

    args = parser.parse_args(argv)

    try:
        artigos = ler_artigos(args.entrada)

        if not args.mapeamentos.is_file():
            raise ValueError(
                f"Arquivo de equivalências não encontrado: "
                f"{args.mapeamentos}"
            )

        regras = json.loads(
            args.mapeamentos.read_text(encoding="utf-8")
        )

        resolvidos, relatorio = resolver(artigos, regras)

    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))

    args.saida.mkdir(parents=True, exist_ok=True)

    for artigo, dados in resolvidos.items():
        (args.saida / f"{artigo}.json").write_text(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2
            ) + "\n",
            encoding="utf-8"
        )

    args.relatorio.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    args.relatorio.write_text(
        json.dumps(
            relatorio,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    resumo = relatorio["resumo"]

    print(
        f"{resumo['artigos']} artigos, "
        f"{resumo['ids_distintos_antes']} -> "
        f"{resumo['ids_distintos_depois']} IDs distintos."
    )

    print(
        f"{resumo['equivalencias_explicitas']} equivalências explícitas, "
        f"{resumo['relacoes_depois']} relações preservadas."
    )

    print(
        f"Equivalências ignoradas: "
        f"{resumo['equivalencias_ignoradas']}"
    )

    print(f"Relatório: {args.relatorio}")

    print(
        "ATENÇÃO: arquivos em .cache/pa4_previa/ "
        "NÃO estão validados para ingestão no Neo4j."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
