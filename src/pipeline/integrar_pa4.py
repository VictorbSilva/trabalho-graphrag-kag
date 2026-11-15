"""PA4-C: combina curadoria e resolução, sem aprovar relações automaticamente.

Executar na raiz do projeto:
    python src/pipeline/integrar_pa4.py

Saída: .cache/pa4_integrado.json (AUDITORIA, NÃO é entrada de Neo4j).

A ordem importa: as decisões manuais são ligadas às triplas originais
antes da troca de IDs. Se uma unificação fizer duas relações virarem a
mesma tripla com status diferentes, o resultado passa a 'pendente'.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

try:  # import como módulo (pytest)
    from .validacao_semantica import classificar
    from .resolucao_entidades import ler_artigos, resolver
except ImportError:  # execução direta no terminal
    from validacao_semantica import classificar
    from resolucao_entidades import ler_artigos, resolver

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA_PADRAO = RAIZ / "data" / "processado" / "extraido"
REVISOES_PADRAO = RAIZ / "data" / "avaliacao" / "revisao_relacoes_pa4.json"
EQUIVALENCIAS_PADRAO = RAIZ / "data" / "avaliacao" / "equivalencias_entidades_pa4.json"
SAIDA_PADRAO = RAIZ / ".cache" / "pa4_integrado.json"


def _chave(relacao: dict) -> tuple:
    return (relacao["origem"], relacao["tipo"], relacao["destino"], relacao["chunk_id"])


def integrar(artigos: dict[str, dict], revisoes: dict, equivalencias: dict) -> dict:
    """Integra as duas etapas usando os dados ORIGINAIS como fonte da curadoria."""
    classificados = classificar(artigos, revisoes)
    resolvidos, relatorio_resolucao = resolver(artigos, equivalencias)
    mapa = {item["de"]: item["para"] for item in relatorio_resolucao["unificacoes"]}

    # Confere que toda aresta canônica realmente está presente nos dados resolvidos.
    chaves_resolvidas = {
        artigo: {_chave(r) for r in dados["relacoes"]}
        for artigo, dados in resolvidos.items()
    }
    grupos = defaultdict(list)
    for item in classificados["relacoes"]:
        artigo = item["artigo"]
        r = item["relacao"]
        if not isinstance(r, dict):
            raise ValueError(f"Relação malformada em {artigo}; corrija antes da integração")
        canonica = dict(r)
        canonica["origem"] = mapa.get(r["origem"], r["origem"])
        canonica["destino"] = mapa.get(r["destino"], r["destino"])
        chave = _chave(canonica)
        if chave not in chaves_resolvidas[artigo]:
            raise ValueError(f"Relação ausente da resolução em {artigo}: {chave}")
        grupos[(artigo, chave)].append(item)

    resultados = []
    colisoes = []
    contagens = {"aceita": 0, "rejeitada": 0, "pendente": 0}
    for (artigo, chave), originais in sorted(grupos.items()):
        estados = {x["status"] for x in originais}
        conflito = len(estados) > 1
        # Regra conservadora: na dúvida, NUNCA promover para aceita.
        status = next(iter(estados)) if not conflito else "pendente"
        relacao = {k: v for k, v in zip(("origem", "tipo", "destino", "chunk_id"), chave)}
        alertas = sorted({a for x in originais for a in x.get("alertas", [])})
        if conflito:
            alertas.append("STATUS_CONFLITANTES_APOS_RESOLUCAO")
            colisoes.append({"artigo": artigo, "relacao": relacao,
                             "status_originais": sorted(estados)})
        resultados.append({
            "artigo": artigo,
            "relacao": relacao,
            "status": status,
            "alertas": alertas,
            "proveniencia": [{"relacao_original": x["relacao"],
                              "status_original": x["status"],
                              "justificativa": x.get("justificativa")}
                             for x in originais],
        })
        contagens[status] += 1

    ids_resolvidos = {e["id"] for d in resolvidos.values() for e in d["entidades"]}
    return {
        "resumo": {
            "artigos": len(artigos),
            "ids_distintos": len(ids_resolvidos),
            "relacoes_originais": classificados["resumo"]["relacoes"],
            "relacoes_canonicas": len(resultados),
            "equivalencias": relatorio_resolucao["resumo"]["equivalencias_explicitas"],
            **contagens,
            "conflitos_apos_resolucao": len(colisoes),
        },
        "unificacoes": relatorio_resolucao["unificacoes"],
        "colisoes": colisoes,
        "relacoes": resultados,
        "aviso": "RELATORIO DE AUDITORIA. NÃO IMPORTAR NO NEO4J. Relações pendentes NÃO estão aprovadas; revise antes de produzir um conjunto de ingestão.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PA4-C: integrar revisão + resolução em relatório auditável")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--revisoes", type=Path, default=REVISOES_PADRAO)
    parser.add_argument("--equivalencias", type=Path, default=EQUIVALENCIAS_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args(argv)
    try:
        artigos = ler_artigos(args.entrada)
        revisoes = json.loads(args.revisoes.read_text(encoding="utf-8"))
        equivalencias = json.loads(args.equivalencias.read_text(encoding="utf-8"))
        resultado = integrar(artigos, revisoes, equivalencias)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = resultado["resumo"]
    print(f"{r['artigos']} artigos, {r['ids_distintos']} IDs canônicos, {r['relacoes_canonicas']} relações.")
    print(f"Curadoria integrada: {r['aceita']} aceitas, {r['rejeitada']} rejeitadas, {r['pendente']} pendentes.")
    print(f"Colisões de status após unificação: {r['conflitos_apos_resolucao']}")
    print(f"Relatório: {args.saida}")
    print("ATENÇÃO: relatório apenas para auditoria, não para ingestão no Neo4j.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
