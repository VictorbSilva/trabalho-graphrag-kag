"""Comparação RAG vetorial vs GraphRAG nas 15 perguntas de avaliação (issue V7).

Roda cada pergunta de data/avaliacao/perguntas.json nos dois modos do responder()
e mede, sem LLM juiz:

- evidência recuperada: todos os trechos de `evidencias` estão contidos no trecho de
  alguma fonte (comparando com espaços normalizados);
- caminho completo: todas as triplas de `caminho_esperado` aparecem como
  (origem, tipo, destino) em subgrafo.arestas, que guarda a direção;
- recusa correta: nas perguntas sem_resposta, a resposta traz MENSAGEM_SEM_INFORMACAO.

A classificação correta / incompleta / alucinada é manual (sem LLM juiz, issue #28)
e fica em data/avaliacao/classificacao.json, que sobrevive a novas execuções. A
única regra automática é a das perguntas sem_resposta, cujo gabarito é recusar:
recusa correta vira "correta", e qualquer outra resposta vira "alucinada". O
executor só acrescenta essas entradas quando ainda não existem e nunca sobrescreve
uma classe do arquivo. A planilha para classificar as outras sai em
docs/avaliacao-planilha.md. O resultado depende do que estiver carregado no banco.

    python -m src.avaliacao.comparar
    python -m src.avaliacao.comparar --so-relatorio

Com --so-relatorio, o executor não chama o responder(): refaz só o relatório a
partir de data/avaliacao/resultados/respostas.json e da classificação, sem gravar
respostas, classificação nem planilha.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.recuperacao.grounding import MENSAGEM_SEM_INFORMACAO
from src.recuperacao.responder import responder

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_PERGUNTAS = RAIZ / "data" / "avaliacao" / "perguntas.json"
ARQUIVO_RESPOSTAS = RAIZ / "data" / "avaliacao" / "resultados" / "respostas.json"
ARQUIVO_RELATORIO = RAIZ / "docs" / "avaliacao-resultados.md"
ARQUIVO_CLASSIFICACAO = RAIZ / "data" / "avaliacao" / "classificacao.json"
ARQUIVO_PLANILHA = RAIZ / "docs" / "avaliacao-planilha.md"

MODOS = ("vetorial", "graphrag")
TIPOS = ("um_salto", "multi_hop", "sem_resposta")
METRICAS = ("evidencia_recuperada", "caminho_completo", "recusa_correta")
CLASSES = ("correta", "incompleta", "alucinada")


def carregar_perguntas(caminho: Path = ARQUIVO_PERGUNTAS) -> list[dict]:
    """As perguntas do gabarito (lista "perguntas" do arquivo)."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))["perguntas"]


def carregar_classificacao(caminho: Path = ARQUIVO_CLASSIFICACAO) -> dict:
    """A classificação manual {"P01": {"vetorial": "correta", ...}}, ou {} sem arquivo.

    Levanta ValueError se alguma classe não for correta, incompleta ou alucinada.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    classificacao = json.loads(caminho.read_text(encoding="utf-8"))
    for id_pergunta, por_modo in classificacao.items():
        for modo, classe in por_modo.items():
            if classe not in CLASSES:
                raise ValueError(
                    f"Classe inválida em {caminho.name}, {id_pergunta} {modo}: {classe!r}. "
                    f"Use {', '.join(CLASSES)}."
                )
    return classificacao


def classificar_sem_resposta(linhas: list[dict]) -> dict:
    """A classe das perguntas sem_resposta pela recusa, no formato do arquivo.

    O gabarito delas é recusar: recusa correta vira "correta", qualquer outra
    resposta vira "alucinada". Linhas com erro (recusa_correta None) ficam de fora.
    """
    classes: dict = {}
    for l in linhas:
        if l["tipo"] != "sem_resposta" or l["recusa_correta"] is None:
            continue
        classes.setdefault(l["id"], {})[l["modo"]] = "correta" if l["recusa_correta"] else "alucinada"
    return classes


def acrescentar_classificacao(existente: dict, novas: dict) -> dict:
    """Cópia de existente com as entradas de novas que ainda não existem, por id e modo.

    Nunca sobrescreve uma classe que já está em existente.
    """
    resultado = {id_pergunta: dict(por_modo) for id_pergunta, por_modo in existente.items()}
    for id_pergunta, por_modo in novas.items():
        destino = resultado.setdefault(id_pergunta, {})
        for modo, classe in por_modo.items():
            destino.setdefault(modo, classe)
    return dict(sorted(resultado.items()))


def _classe(classificacao: dict | None, linha: dict) -> str | None:
    return (classificacao or {}).get(linha["id"], {}).get(linha["modo"])


def _normalizar(texto: str) -> str:
    return " ".join(texto.split())


def _tudo_ou_none(encontradas: int, total: int) -> bool | None:
    """True se achou todas, False se faltou alguma, None se não havia nada a procurar."""
    return None if total == 0 else encontradas == total


def avaliar(pergunta: dict, resposta: dict) -> dict:
    """Linha da tabela para uma resposta do contrato a uma pergunta do gabarito."""
    trechos = [_normalizar(f["trecho"]) for f in resposta["fontes"]]
    evidencias = [_normalizar(e["trecho"]) for e in pergunta["evidencias"]]
    evidencias_encontradas = sum(1 for e in evidencias if any(e in t for t in trechos))

    arestas = {(a["origem"], a["tipo"], a["destino"]) for a in resposta["subgrafo"]["arestas"]}
    triplas = [(t["origem"], t["tipo"], t["destino"]) for t in pergunta["caminho_esperado"]]
    triplas_encontradas = sum(1 for t in triplas if t in arestas)

    recusa = None
    if pergunta["tipo"] == "sem_resposta":
        recusa = MENSAGEM_SEM_INFORMACAO in resposta["resposta"]

    return {
        "id": pergunta["id"],
        "tipo": pergunta["tipo"],
        "modo": resposta["modo"],
        "evidencia_recuperada": _tudo_ou_none(evidencias_encontradas, len(evidencias)),
        "evidencias_encontradas": evidencias_encontradas,
        "evidencias_total": len(evidencias),
        "caminho_completo": _tudo_ou_none(triplas_encontradas, len(triplas)),
        "triplas_encontradas": triplas_encontradas,
        "triplas_total": len(triplas),
        "recusa_correta": recusa,
        "confianca": {"valor": resposta["confianca"]["valor"], "nivel": resposta["confianca"]["nivel"]},
        "erro": None,
    }


def _linha_com_erro(pergunta: dict, modo: str, erro: Exception | str) -> dict:
    """Linha de uma pergunta em que o responder() levantou exceção: sem métricas.

    erro é a exceção ou o texto dela já salvo em respostas.json.
    """
    return {
        "id": pergunta["id"],
        "tipo": pergunta["tipo"],
        "modo": modo,
        **{metrica: None for metrica in METRICAS},
        "confianca": None,
        "erro": erro if isinstance(erro, str) else f"{type(erro).__name__}: {erro}",
    }


def avaliar_respostas_salvas(perguntas: list[dict], respostas: list[dict]) -> list[dict]:
    """As linhas da tabela refeitas a partir de respostas.json, sem chamar o responder().

    respostas são as de main(): {"id", "modo", "resposta", "erro"}. Uma resposta
    salva com erro vira linha com erro, como na execução original.
    """
    por_id = {p["id"]: p for p in perguntas}
    linhas = []
    for registro in respostas:
        pergunta = por_id[registro["id"]]
        if registro["resposta"] is None:
            linhas.append(_linha_com_erro(pergunta, registro["modo"], registro["erro"] or "sem resposta"))
        else:
            linhas.append(avaliar(pergunta, registro["resposta"]))
    return linhas


def _fracao(valores: list) -> float | None:
    """Fração de True entre os valores que não são None (None se não sobrar nenhum)."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def resumir(linhas: list[dict], classificacao: dict | None = None) -> dict:
    """Por modo e por tipo: perguntas, erros, a fração de acertos de cada métrica e,
    em "classificacao", quantas respostas têm cada classe do arquivo.

    As linhas com erro contam em "erros" e ficam fora das frações. As linhas sem
    classe ficam fora da contagem das classes.
    """
    resumo: dict = {}
    for modo in MODOS:
        resumo[modo] = {}
        for tipo in TIPOS:
            grupo = [l for l in linhas if l["modo"] == modo and l["tipo"] == tipo]
            sem_erro = [l for l in grupo if l["erro"] is None]
            classes = [_classe(classificacao, l) for l in grupo]
            resumo[modo][tipo] = {
                "perguntas": len(grupo),
                "erros": len(grupo) - len(sem_erro),
                **{metrica: _fracao([l[metrica] for l in sem_erro]) for metrica in METRICAS},
                "classificacao": {classe: classes.count(classe) for classe in CLASSES},
            }
    return resumo


# --- relatório em Markdown ----------------------------------------------------

def _sim_nao(valor: bool | None, encontradas: int | None = None, total: int | None = None) -> str:
    if valor is None:
        return "n/a"
    texto = "sim" if valor else "não"
    if total and not valor:
        texto += f" ({encontradas}/{total})"
    return texto


def _porcentagem(fracao: float | None) -> str:
    return "n/d" if fracao is None else f"{fracao:.0%}"


def _tabela_por_pergunta(linhas: list[dict], classificacao: dict | None = None) -> list[str]:
    saida = [
        "| ID | Tipo | Modo | Evidência recuperada | Caminho completo | Recusa correta | Confiança | Classificação (manual) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for l in linhas:
        if l["erro"] is not None:
            celulas = ["erro"] * 4
        else:
            celulas = [
                _sim_nao(l["evidencia_recuperada"], l["evidencias_encontradas"], l["evidencias_total"]),
                _sim_nao(l["caminho_completo"], l["triplas_encontradas"], l["triplas_total"]),
                _sim_nao(l["recusa_correta"]),
                f"{l['confianca']['nivel']} ({l['confianca']['valor']:.2f})",
            ]
        classe = _classe(classificacao, l) or ""
        saida.append(f"| {l['id']} | {l['tipo']} | {l['modo']} | " + " | ".join(celulas) + f" | {classe} |")
    return saida


def _tabelas_de_resumo(resumo: dict) -> list[str]:
    saida = [
        "| Modo | Tipo | Perguntas | Com erro | Evidência recuperada | Caminho completo |",
        "|---|---|---|---|---|---|",
    ]
    for modo in MODOS:
        for tipo in ("um_salto", "multi_hop"):
            r = resumo[modo][tipo]
            saida.append(
                f"| {modo} | {tipo} | {r['perguntas']} | {r['erros']} | "
                f"{_porcentagem(r['evidencia_recuperada'])} | {_porcentagem(r['caminho_completo'])} |"
            )
    saida += [
        "",
        "| Modo | Perguntas sem resposta | Com erro | Recusa correta |",
        "|---|---|---|---|",
    ]
    for modo in MODOS:
        r = resumo[modo]["sem_resposta"]
        saida.append(f"| {modo} | {r['perguntas']} | {r['erros']} | {_porcentagem(r['recusa_correta'])} |")
    saida += [
        "",
        "| Modo | Tipo | Perguntas | Classificadas | Correta | Incompleta | Alucinada |",
        "|---|---|---|---|---|---|---|",
    ]
    for modo in MODOS:
        for tipo in TIPOS:
            r = resumo[modo][tipo]
            contagem = r["classificacao"]
            saida.append(
                f"| {modo} | {tipo} | {r['perguntas']} | {sum(contagem.values())} | "
                + " | ".join(str(contagem[classe]) for classe in CLASSES)
                + " |"
            )
    return saida


def _relatorio(
    linhas: list[dict], resumo: dict, gerado_em: datetime, classificacao: dict | None = None
) -> str:
    erros = [l for l in linhas if l["erro"] is not None]
    saida = [
        "# Avaliação: RAG vetorial vs GraphRAG",
        "",
        f"Gerado por `python -m src.avaliacao.comparar` em {gerado_em:%Y-%m-%d %H:%M}, "
        "com as 15 perguntas de [data/avaliacao/perguntas.json](../data/avaliacao/perguntas.json) "
        "nos modos `vetorial` e `graphrag`. As respostas completas ficam em "
        "[data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). "
        "Os números dependem do que estava carregado no Neo4j quando o executor rodou.",
        "",
        "A classificação manual fica em "
        "[data/avaliacao/classificacao.json](../data/avaliacao/classificacao.json) e sobrevive "
        "a novas execuções do executor. A planilha para preenchê-la está em "
        "[docs/avaliacao-planilha.md](avaliacao-planilha.md).",
        "",
        "## Como ler",
        "",
        "- **Evidência recuperada**: todos os trechos de `evidencias` da pergunta aparecem dentro "
        "de alguma fonte da resposta (espaços normalizados). Quando falta algum, entre parênteses "
        "vai quantos foram achados.",
        "- **Caminho completo**: todas as triplas de `caminho_esperado` aparecem, na direção do "
        "schema, nas arestas do subgrafo da resposta. O modo `vetorial` não monta subgrafo.",
        "- **Recusa correta**: só nas perguntas `sem_resposta`, a resposta diz "
        f"\"{MENSAGEM_SEM_INFORMACAO}\"",
        "- **n/a**: a métrica não se aplica ao tipo da pergunta. **n/d**: sem dados para calcular.",
        "- **Classificação (manual)**: correta, incompleta ou alucinada, lida de "
        "`data/avaliacao/classificacao.json` e preenchida por quem conferir a resposta contra "
        "o gabarito. Nas perguntas `sem_resposta`, cujo gabarito é recusar, a recusa correta "
        "vira correta e qualquer outra resposta vira alucinada.",
        "",
        "## Resultado por pergunta",
        "",
        *_tabela_por_pergunta(linhas, classificacao),
        "",
    ]
    if erros:
        saida += ["### Erros na execução", ""]
        saida += [f"- {l['id']} ({l['modo']}): `{l['erro']}`" for l in erros]
        saida.append("")
    saida += [
        "## Resumo",
        "",
        *_tabelas_de_resumo(resumo),
        "",
        "Limite da amostra: 15 perguntas; os números indicam tendência, não diferença "
        "estatisticamente significativa.",
        "",
        "## Análise de erros",
        "",
        "Três casos escolhidos a partir da tabela acima.",
        "",
    ]
    for numero in (1, 2, 3):
        saida += [
            f"### Caso {numero}",
            "",
            "- Pergunta e modo:",
            "- O que aconteceu:",
            "- Causa provável:",
            "",
        ]
    return "\n".join(saida)


# --- planilha para a classificação manual -------------------------------------

def _citacao(texto: str) -> list[str]:
    """O texto como citação em Markdown, linha a linha."""
    return [f"> {linha}".rstrip() for linha in texto.splitlines()] or [">"]


def gerar_planilha(linhas: list[dict], perguntas: list[dict], respostas: list[dict]) -> str:
    """Markdown com, para cada pergunta e modo, o gabarito, a resposta do sistema,
    as métricas automáticas e uma linha "Classificação: ____" para preencher.

    linhas são as de avaliar() e respostas as de main(): {"id", "modo", "resposta", "erro"}.
    """
    por_linha = {(l["id"], l["modo"]): l for l in linhas}
    por_resposta = {(r["id"], r["modo"]): r for r in respostas}
    saida = [
        "# Planilha de classificação manual",
        "",
        "Gerada por `python -m src.avaliacao.comparar`, a partir das respostas em "
        "[data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). "
        "Para cada pergunta e modo, compare a resposta do sistema com a resposta esperada e "
        "escreva correta, incompleta ou alucinada.",
        "",
        "As classes ficam em [data/avaliacao/classificacao.json](../data/avaliacao/classificacao.json), "
        'no formato `{"P01": {"vetorial": "correta", "graphrag": "incompleta"}}`. As perguntas '
        "`sem_resposta` já entram nesse arquivo pela regra: recusa correta vira correta, e "
        "qualquer outra resposta vira alucinada. Rodar o executor de novo regenera esta planilha, "
        "mas não apaga o arquivo de classificação.",
        "",
    ]
    for pergunta in perguntas:
        saida += [
            f"## {pergunta['id']} ({pergunta['tipo']})",
            "",
            f"Pergunta: {pergunta['pergunta']}",
            "",
            f"Resposta esperada: {pergunta['resposta_esperada']}",
            "",
        ]
        for modo in MODOS:
            linha = por_linha.get((pergunta["id"], modo))
            registro = por_resposta.get((pergunta["id"], modo))
            saida += [f"### {pergunta['id']} {modo}", ""]
            if registro is None or registro["resposta"] is None:
                erro = (registro or {}).get("erro") or (linha or {}).get("erro") or "sem resposta"
                saida += [f"Resposta do sistema: erro na execução, `{erro}`", ""]
            else:
                saida += ["Resposta do sistema:", "", *_citacao(registro["resposta"]["resposta"]), ""]
            if linha is not None and linha["erro"] is None:
                saida += [
                    "Evidência recuperada: "
                    + _sim_nao(linha["evidencia_recuperada"], linha["evidencias_encontradas"], linha["evidencias_total"]),
                    "",
                    "Caminho completo: "
                    + _sim_nao(linha["caminho_completo"], linha["triplas_encontradas"], linha["triplas_total"]),
                    "",
                ]
            else:
                saida += ["Evidência recuperada: erro", "", "Caminho completo: erro", ""]
            saida += ["Classificação: ____", ""]
    return "\n".join(saida)


def so_relatorio() -> None:
    """Refaz só o relatório a partir das respostas salvas e da classificação."""
    perguntas = carregar_perguntas(ARQUIVO_PERGUNTAS)
    respostas = json.loads(ARQUIVO_RESPOSTAS.read_text(encoding="utf-8"))
    classificacao = carregar_classificacao(ARQUIVO_CLASSIFICACAO)
    linhas = avaliar_respostas_salvas(perguntas, respostas)
    ARQUIVO_RELATORIO.write_text(
        _relatorio(linhas, resumir(linhas, classificacao), datetime.now(), classificacao) + "\n",
        encoding="utf-8",
    )
    print(f"Relatório em {ARQUIVO_RELATORIO}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Comparação RAG vetorial vs GraphRAG (V7).")
    parser.add_argument(
        "--so-relatorio",
        action="store_true",
        help="refaz só o relatório a partir das respostas salvas, sem chamar o responder()",
    )
    if parser.parse_args(argv).so_relatorio:
        so_relatorio()
        return

    perguntas = carregar_perguntas()
    existente = carregar_classificacao()  # antes de rodar: uma classe inválida para já aqui
    linhas, respostas = [], []
    for pergunta in perguntas:
        for modo in MODOS:
            try:
                resposta = responder(pergunta["pergunta"], modo)
            except Exception as erro:
                linha = _linha_com_erro(pergunta, modo, erro)
                respostas.append({"id": pergunta["id"], "modo": modo, "resposta": None, "erro": linha["erro"]})
            else:
                linha = avaliar(pergunta, resposta)
                respostas.append({"id": pergunta["id"], "modo": modo, "resposta": resposta, "erro": None})
            linhas.append(linha)
            print(f"{pergunta['id']} {modo}: {'erro' if linha['erro'] else 'ok'}", flush=True)

    classificacao = acrescentar_classificacao(existente, classificar_sem_resposta(linhas))

    ARQUIVO_RESPOSTAS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_RESPOSTAS.write_text(json.dumps(respostas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ARQUIVO_CLASSIFICACAO.write_text(
        json.dumps(classificacao, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ARQUIVO_RELATORIO.write_text(
        _relatorio(linhas, resumir(linhas, classificacao), datetime.now(), classificacao) + "\n",
        encoding="utf-8",
    )
    ARQUIVO_PLANILHA.write_text(gerar_planilha(linhas, perguntas, respostas) + "\n", encoding="utf-8")
    print(f"Respostas em {ARQUIVO_RESPOSTAS.relative_to(RAIZ)}")
    print(f"Classificação em {ARQUIVO_CLASSIFICACAO.relative_to(RAIZ)}")
    print(f"Relatório em {ARQUIVO_RELATORIO.relative_to(RAIZ)}")
    print(f"Planilha em {ARQUIVO_PLANILHA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
