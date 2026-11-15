"""Exportação conservadora da curadoria PA4 para preparação do PA5.

Uso na raiz do projeto:
    python src/pipeline/exportar_pa4.py

Preserva os JSONs do PA3. Gera um JSON por artigo com o contrato de
neo4j/dominio.json, incluindo APENAS as relações com status 'aceita'.
relações pendentes. A curadoria foi inicialmente assistida por IA e
posteriormente conferida e ajustada manualmente. A exportação ainda
depende de verificações finais antes da ingestão no Neo4j.
"""

import argparse
import json
from copy import deepcopy
from pathlib import Path

try:
    from .integrar_pa4 import integrar
    from .resolucao_entidades import ler_artigos, resolver
except ImportError:
    from integrar_pa4 import integrar
    from resolucao_entidades import ler_artigos, resolver

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA_PADRAO = RAIZ / "data" / "processado" / "extraido"
REVISOES_PADRAO = RAIZ / "data" / "avaliacao" / "revisao_relacoes_pa4.json"
EQUIVALENCIAS_PADRAO = RAIZ / "data" / "avaliacao" / "equivalencias_entidades_pa4.json"
CORRECOES_PADRAO = RAIZ / "data" / "avaliacao" / "correcoes_evidencia_pa4.json"
SAIDA_PADRAO = RAIZ / ".cache" / "pa4_curado"
AUDITORIA_PADRAO = RAIZ / ".cache" / "pa4_exportacao_auditoria.json"


def chave(artigo: str, relacao: dict) -> tuple[str, str, str, str, str]:
    return (artigo, relacao["origem"], relacao["tipo"], relacao["destino"], relacao["chunk_id"])


def exportar(artigos: dict, revisoes: dict, equivalencias: dict, correcoes: dict | None = None) -> tuple[dict, dict]:
    """Retorna (artigos_curados, auditoria) sem modificar os dados de entrada."""
    integrado = integrar(artigos, revisoes, equivalencias)
    resolvidos, _ = resolver(artigos, equivalencias)
    if integrado["colisoes"]:
        # Conflitos não são aprovados em integrar(), mas exigem atenção explícita.
        raise ValueError("Existem colisões após resolver IDs; revise antes de exportar")

    sugestoes = {}
    for item in (correcoes or {}).get("correcoes", []):
        referencia = {
            "origem": item["origem"], "tipo": item["tipo"],
            "destino": item["destino"], "chunk_id": item["chunk_id_anterior"]
        }
        k = chave(item["artigo"], referencia)
        if k in sugestoes:
            raise ValueError(f"Correção de evidência duplicada: {k}")
        if item["artigo"] not in artigos:
            raise ValueError(f"Artigo não encontrado: {item['artigo']}")
        originais = artigos[item["artigo"]]["relacoes"]
        if referencia not in originais:
            raise ValueError(f"Correção aponta para uma relação que não existe: {k}")
        chunks = {c["id"] for c in artigos[item["artigo"]]["chunks"]}
        if item["chunk_id_sugerido"] not in chunks:
            raise ValueError(f"Novo chunk não existe: {item['chunk_id_sugerido']}")
        if not str(item.get("justificativa", "")).strip():
            raise ValueError(f"Correção sem justificativa: {k}")
        sugestoes[k] = {"chunk_id_sugerido": item["chunk_id_sugerido"],
                       "justificativa": item["justificativa"]}

    aceitas_por_artigo = {nome: [] for nome in resolvidos}
    excluidas = []
    sugestoes_usadas = set()
    for registro in integrado["relacoes"]:
        nome, relacao = registro["artigo"], registro["relacao"]
        if registro["status"] == "aceita":
            aceitas_por_artigo[nome].append(deepcopy(relacao))
        else:
            item = deepcopy(registro)
            aplicaveis = []
            for origem in item["proveniencia"]:
                k = chave(nome, origem["relacao_original"])
                if k in sugestoes:
                    aplicaveis.append(sugestoes[k])
                    sugestoes_usadas.add(k)
            if aplicaveis:
                item["sugestoes_correcao_evidencia"] = aplicaveis
            excluidas.append(item)

    if set(sugestoes) != sugestoes_usadas:
        raise ValueError("Correção de evidência aponta para relação já aceita; não aplicar automaticamente")

    saidas = {}
    for nome, dados in resolvidos.items():
        copia = deepcopy(dados)
        chaves = {(r["origem"], r["tipo"], r["destino"], r["chunk_id"]) for r in copia["relacoes"]}
        chunks = {c["id"] for c in copia["chunks"]}
        entidades = {e["id"]: e for e in copia["entidades"]}
        aprovadas = []
        ids_usados = set()
        for r in aceitas_por_artigo[nome]:
            k = r["origem"], r["tipo"], r["destino"], r["chunk_id"]
            if k not in chaves or r["chunk_id"] not in chunks:
                raise ValueError(f"Relação aprovada sem correspondência válida em {nome}: {r}")
            if r["origem"] not in entidades or r["destino"] not in entidades:
                raise ValueError(f"Relação aprovada sem entidade correspondente em {nome}: {r}")
            ids_usados.update((r["origem"], r["destino"]))
            aprovadas.append(r)
        copia["relacoes"] = aprovadas
        # Reduz entidades ao subconjunto necessário para as relações aprovadas.
        # Chunks/documento permanecem para preservar toda evidência textual.
        copia["entidades"] = [e for e in copia["entidades"] if e["id"] in ids_usados]
        saidas[nome] = copia

    total = sum(len(d["relacoes"]) for d in saidas.values())
    if total != integrado["resumo"]["aceita"]:
        raise ValueError("Contagem de relações exportadas diverge da revisão")
    auditoria = {
        "resumo": {
            "artigos": len(saidas),
            "relacoes_aceitas_exportadas": total,
            "relacoes_rejeitadas_excluidas": integrado["resumo"]["rejeitada"],
            "relacoes_pendentes_excluidas": integrado["resumo"]["pendente"],
            "sugestoes_de_correcao": len(sugestoes),
            "ids_canonicos_no_conjunto_original": integrado["resumo"]["ids_distintos"],
            "ids_utilizados_na_exportacao": len({e["id"] for d in saidas.values() for e in d["entidades"]}),
        },
        "unificacoes": integrado["unificacoes"],
        "excluidas": excluidas,
        "observacao": "Curadoria inicialmente assistida por IA, seguida de conferencia e ajustes manuais. Correcoes de evidencia sugeridas nao sao aprovadas automaticamente. A ingestao no Neo4j depende de verificacao final e testes de integracao.",
    }
    return saidas, auditoria


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PA4: exporta relações aceitas para prévia do PA5")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--revisoes", type=Path, default=REVISOES_PADRAO)
    parser.add_argument("--equivalencias", type=Path, default=EQUIVALENCIAS_PADRAO)
    parser.add_argument("--correcoes", type=Path, default=CORRECOES_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--auditoria", type=Path, default=AUDITORIA_PADRAO)
    args = parser.parse_args(argv)
    try:
        artigos = ler_artigos(args.entrada)
        revisoes = json.loads(args.revisoes.read_text(encoding="utf-8"))
        equivalencias = json.loads(args.equivalencias.read_text(encoding="utf-8"))
        correcoes = json.loads(args.correcoes.read_text(encoding="utf-8")) if args.correcoes.exists() else {}
        saidas, auditoria = exportar(artigos, revisoes, equivalencias, correcoes)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    args.saida.mkdir(parents=True, exist_ok=True)
    for nome, dados in saidas.items():
        destino = args.saida / f"{nome}.json"
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.auditoria.parent.mkdir(parents=True, exist_ok=True)
    args.auditoria.write_text(json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = auditoria["resumo"]
    print(f"{r['artigos']} artigos; {r['relacoes_aceitas_exportadas']} relações aceitas exportadas.")
    print(f"Excluídas: {r['relacoes_rejeitadas_excluidas']} rejeitadas; {r['relacoes_pendentes_excluidas']} pendentes.")
    print(f"Sugestões de correção de evidência: {r['sugestoes_de_correcao']} (sem aprovação automática).")
    print(f"Prévia para PA5: {args.saida}")
    print(f"Auditoria: {args.auditoria}")
    print("ATENÇÃO: curadoria revisada manualmente; verificar dados e integração antes da ingestão no Neo4j.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
