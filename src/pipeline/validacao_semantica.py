"""PA4-A: triagem conservadora de relações extraídas, sem alterar os JSONs originais.

Uso (na raiz do repositório):
    python src/pipeline/validacao_semantica.py
    python src/pipeline/validacao_semantica.py --entrada data/processado/extraido

Este módulo SINALIZA possíveis problemas; não garante a veracidade de relações,
não remove nem inverte arestas automaticamente e não utiliza serviços externos.
"""

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA_PADRAO = RAIZ / "data" / "processado" / "extraido"
SAIDA_PADRAO = RAIZ / ".cache" / "validacao_semantica.json"
CLASSIFICADAS_PADRAO = RAIZ / ".cache" / "relacoes_classificadas.json"
REVISOES_PADRAO = RAIZ / "data" / "avaliacao" / "revisao_relacoes_pa4.json"


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().casefold()


def entidade_mencionada(entidade: dict, texto: str) -> bool:
    texto = normalizar(texto)
    nomes = [entidade.get("name", ""), *(entidade.get("aliases") or [])]
    for nome in nomes:
        nome = normalizar(nome).strip()
        if nome and re.search(r"(?<![\w])" + re.escape(nome) + r"(?![\w])", texto):
            return True
    return False


def analisar(arquivos: dict[str, dict]) -> dict:
    """Retorna um relatório de suspeitas. Nenhuma conclusão semântica é automática."""
    alertas = []
    triplas = defaultdict(list)
    total_relacoes = 0

    def registrar(codigo: str, artigo: str, relacao: dict, explicacao: str):
        alertas.append({
            "codigo": codigo,
            "artigo": artigo,
            "relacao": dict(relacao),
            "observacao": explicacao,
            "acao": "revisao_humana",
        })

    for artigo, dados in sorted(arquivos.items()):
        entidades = {e["id"]: e for e in dados.get("entidades", []) if isinstance(e, dict) and "id" in e}
        chunks = {c["id"]: c.get("text", "") for c in dados.get("chunks", []) if isinstance(c, dict) and "id" in c}
        for relacao in dados.get("relacoes", []):
            total_relacoes += 1
            if not isinstance(relacao, dict):
                registrar("RELACAO_MALFORMADA", artigo, {"valor": str(relacao)}, "Relação não é um objeto JSON.")
                continue
            origem, destino = relacao.get("origem"), relacao.get("destino")
            tipo, chunk_id = relacao.get("tipo"), relacao.get("chunk_id")
            if origem not in entidades or destino not in entidades:
                registrar("ENTIDADE_DESCONHECIDA", artigo, relacao, "Origem ou destino não pertence às entidades do artigo.")
            if chunk_id not in chunks:
                registrar("CHUNK_INVALIDO", artigo, relacao, "Referência a chunk inexistente no artigo.")
            if origem in entidades and destino in entidades and chunk_id in chunks:
                texto = chunks[chunk_id]
                if not (entidade_mencionada(entidades[origem], texto)
                        or entidade_mencionada(entidades[destino], texto)):
                    registrar("EVIDENCIA_A_REVISAR", artigo, relacao,
                              "O trecho indicado não menciona nominalmente nenhuma das entidades. Pode haver referência indireta.")
            if isinstance(origem, str) and isinstance(destino, str) and isinstance(tipo, str):
                triplas[(origem, tipo, destino)].append({"artigo": artigo, "chunk_id": chunk_id})

    # As duas direções podem, em casos raros, ser verdadeiras. Apenas sinalizar.
    vistos = set()
    for (origem, tipo, destino), evidencias in sorted(triplas.items()):
        if tipo != "INFLUENCIADA_POR" or origem == destino:
            continue
        oposta = (destino, tipo, origem)
        par = tuple(sorted((origem, destino)))
        if oposta in triplas and par not in vistos:
            vistos.add(par)
            alertas.append({
                "codigo": "INFLUENCIA_NOS_DOIS_SENTIDOS",
                "entidades": list(par),
                "evidencias": {f"{origem} -> {destino}": evidencias,
                               f"{destino} -> {origem}": triplas[oposta]},
                "observacao": "Há influência nos dois sentidos. Verificar qual direção cada fonte sustenta.",
                "acao": "revisao_humana",
            })

    return {
        "resumo": {"artigos": len(arquivos), "relacoes": total_relacoes, "alertas": len(alertas)},
        "alertas": alertas,
        "observacao": "Este relatório é uma triagem. Ausência de alerta NÃO significa validação factual.",
    }



def chave_relacao(artigo: str, relacao: dict) -> tuple:
    """Decisão identificada por artigo + tripla + evidência, sem efeitos globais."""
    return (artigo, relacao.get("origem"), relacao.get("tipo"),
            relacao.get("destino"), relacao.get("chunk_id"))


def classificar(arquivos: dict[str, dict], revisoes: dict | None = None) -> dict:
    """Associa revisão humana às relações. Sem revisão, status é 'pendente'.

    'aceita' NÃO é inferido pela ausência de alertas. Os dados originais
    nunca são alterados. A ingestão só deve considerar relações aprovadas
    após uma revisão apropriada do conjunto.
    """
    relatorio = analisar(arquivos)
    chaves_existentes = {
        chave_relacao(artigo, relacao)
        for artigo, dados in arquivos.items()
        for relacao in dados.get("relacoes", [])
        if isinstance(relacao, dict)
    }
    chaves_revisadas = {}
    for decisao in (revisoes or {}).get("decisoes", []):
        if not isinstance(decisao, dict):
            raise ValueError("Toda decisão deve ser um objeto JSON.")
        chave = chave_relacao(decisao.get("artigo", ""), decisao)
        if chave not in chaves_existentes:
            raise ValueError(f"Decisão não corresponde a uma relação da extração: {chave}")
        if chave in chaves_revisadas:
            raise ValueError(f"Decisão duplicada para a relação: {chave}")
        if decisao.get("status") not in {"aceita", "rejeitada", "pendente"}:
            raise ValueError(f"Status de revisão inválido para: {chave}")
        if not str(decisao.get("justificativa", "")).strip():
            raise ValueError(f"Decisão sem justificativa: {chave}")
        chaves_revisadas[chave] = decisao

    alertas_por_relacao = defaultdict(set)
    for alerta in relatorio["alertas"]:
        if "relacao" in alerta:
            relacao = alerta["relacao"]
            if isinstance(relacao, dict):
                alertas_por_relacao[chave_relacao(alerta["artigo"], relacao)].add(alerta["codigo"])
        elif alerta["codigo"] == "INFLUENCIA_NOS_DOIS_SENTIDOS":
            for evidencias in alerta["evidencias"].values():
                for evidencia in evidencias:
                    # Aponta os dois lados da contradição para revisão.
                    artigo = evidencia["artigo"]
                    chunk_id = evidencia["chunk_id"]
                    for relacao in arquivos[artigo].get("relacoes", []):
                        if (isinstance(relacao, dict)
                                and relacao.get("chunk_id") == chunk_id
                                and relacao.get("tipo") == "INFLUENCIADA_POR"
                                and set((relacao.get("origem"), relacao.get("destino")))
                                == set(alerta["entidades"])):
                            alertas_por_relacao[chave_relacao(artigo, relacao)].add(alerta["codigo"])

    resultados = []
    contagens = {"aceita": 0, "rejeitada": 0, "pendente": 0}
    for artigo, dados in sorted(arquivos.items()):
        for relacao in dados.get("relacoes", []):
            if not isinstance(relacao, dict):
                resultados.append({"artigo": artigo, "relacao": relacao,
                                   "status": "pendente", "origem_status": "sem_revisao",
                                   "alertas": ["RELACAO_MALFORMADA"]})
                contagens["pendente"] += 1
                continue
            chave = chave_relacao(artigo, relacao)
            decisao = chaves_revisadas.get(chave)
            status = decisao["status"] if decisao else "pendente"
            motivos = sorted(alertas_por_relacao[chave])
            # Não declarar aprovada uma relação que tem referências quebradas.
            if status == "aceita" and {"ENTIDADE_DESCONHECIDA", "CHUNK_INVALIDO"} & set(motivos):
                raise ValueError(f"Decisão aceita com referência inválida: {chave}")
            contagens[status] += 1
            item = {"artigo": artigo, "relacao": dict(relacao),
                    "status": status, "origem_status": "revisao_humana" if decisao else "sem_revisao",
                    "alertas": motivos}
            if decisao:
                item["justificativa"] = decisao["justificativa"]
            resultados.append(item)
    return {"resumo": {"artigos": len(arquivos), "relacoes": len(resultados),
                       "alertas": relatorio["resumo"]["alertas"], **contagens,
                       "decisoes_manuais": len(chaves_revisadas)},
            "relacoes": resultados,
            "alertas": relatorio["alertas"],
            "observacao": "Somente relações aceitas por revisão explícita recebem status 'aceita'; pendente não significa falsa. Não há aprovação automática."}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sinaliza suspeitas na extração sem alterar dados.")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--classificadas", type=Path, default=CLASSIFICADAS_PADRAO)
    parser.add_argument("--revisoes", type=Path, default=REVISOES_PADRAO)
    args = parser.parse_args(argv)

    entrada = args.entrada
    arquivos = sorted(entrada.glob("*.json")) if entrada.is_dir() else []
    if not arquivos:
        parser.error(f"nenhum JSON encontrado em {entrada}")
    dados = {arquivo.stem: json.loads(arquivo.read_text(encoding="utf-8")) for arquivo in arquivos}
    resultado = analisar(dados)
    revisoes = json.loads(args.revisoes.read_text(encoding="utf-8")) if args.revisoes.is_file() else None
    classificados = classificar(dados, revisoes)
    args.classificadas.parent.mkdir(parents=True, exist_ok=True)
    args.classificadas.write_text(json.dumps(classificados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resumo = resultado["resumo"]
    print(f"{resumo['artigos']} artigos, {resumo['relacoes']} relações, {resumo['alertas']} alertas de revisão.")
    print(f"Relatório: {args.saida}")
    contagens = classificados["resumo"]
    print(f"Curadoria: {contagens['aceita']} aceitas, {contagens['rejeitada']} rejeitadas, {contagens['pendente']} pendentes.")
    print(f"Relações classificadas: {args.classificadas}")
    if revisoes is None:
        print("AVISO: arquivo de revisões não encontrado. Todas as relações ficaram pendentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
