"""Comparação RAG vetorial vs GraphRAG nas 15 perguntas de avaliação (issue V7).

Roda cada pergunta de data/avaliacao/perguntas.json nos dois modos do responder()
e mede, sem LLM juiz:

- evidência recuperada: todos os trechos de `evidencias` estão contidos no trecho de
  alguma fonte (comparando com espaços normalizados);
- caminho completo: todas as triplas de `caminho_esperado` aparecem como
  (origem, tipo, destino) em subgrafo.arestas, que guarda a direção;
- recusa correta: nas perguntas sem_resposta, a resposta traz MENSAGEM_SEM_INFORMACAO.

A classificação correta / incompleta / alucinada é manual, numa coluna vazia da
tabela gerada. O resultado depende do que estiver carregado no banco.

    python -m src.avaliacao.comparar
"""

import json
from datetime import datetime
from pathlib import Path

from src.recuperacao.grounding import MENSAGEM_SEM_INFORMACAO
from src.recuperacao.responder import responder

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_PERGUNTAS = RAIZ / "data" / "avaliacao" / "perguntas.json"
ARQUIVO_RESPOSTAS = RAIZ / "data" / "avaliacao" / "resultados" / "respostas.json"
ARQUIVO_RELATORIO = RAIZ / "docs" / "avaliacao-resultados.md"

MODOS = ("vetorial", "graphrag")
TIPOS = ("um_salto", "multi_hop", "sem_resposta")
METRICAS = ("evidencia_recuperada", "caminho_completo", "recusa_correta")


def carregar_perguntas(caminho: Path = ARQUIVO_PERGUNTAS) -> list[dict]:
    """As perguntas do gabarito (lista "perguntas" do arquivo)."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))["perguntas"]


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


def _linha_com_erro(pergunta: dict, modo: str, erro: Exception) -> dict:
    """Linha de uma pergunta em que o responder() levantou exceção: sem métricas."""
    return {
        "id": pergunta["id"],
        "tipo": pergunta["tipo"],
        "modo": modo,
        **{metrica: None for metrica in METRICAS},
        "confianca": None,
        "erro": f"{type(erro).__name__}: {erro}",
    }


def _fracao(valores: list) -> float | None:
    """Fração de True entre os valores que não são None (None se não sobrar nenhum)."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def resumir(linhas: list[dict]) -> dict:
    """Por modo e por tipo: perguntas, erros e a fração de acertos de cada métrica.

    As linhas com erro contam em "erros" e ficam fora das frações.
    """
    resumo: dict = {}
    for modo in MODOS:
        resumo[modo] = {}
        for tipo in TIPOS:
            grupo = [l for l in linhas if l["modo"] == modo and l["tipo"] == tipo]
            sem_erro = [l for l in grupo if l["erro"] is None]
            resumo[modo][tipo] = {
                "perguntas": len(grupo),
                "erros": len(grupo) - len(sem_erro),
                **{metrica: _fracao([l[metrica] for l in sem_erro]) for metrica in METRICAS},
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


def _tabela_por_pergunta(linhas: list[dict]) -> list[str]:
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
        saida.append(f"| {l['id']} | {l['tipo']} | {l['modo']} | " + " | ".join(celulas) + " |  |")
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
    return saida


def _relatorio(linhas: list[dict], resumo: dict, gerado_em: datetime) -> str:
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
        "Rodar o executor de novo sobrescreve este arquivo, inclusive a classificação manual.",
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
        "- **Classificação (manual)**: correta, incompleta ou alucinada, preenchida por quem "
        "conferir a resposta contra o gabarito.",
        "",
        "## Resultado por pergunta",
        "",
        *_tabela_por_pergunta(linhas),
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


def main() -> None:
    perguntas = carregar_perguntas()
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

    ARQUIVO_RESPOSTAS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_RESPOSTAS.write_text(json.dumps(respostas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ARQUIVO_RELATORIO.write_text(_relatorio(linhas, resumir(linhas), datetime.now()) + "\n", encoding="utf-8")
    print(f"Respostas em {ARQUIVO_RESPOSTAS.relative_to(RAIZ)}")
    print(f"Relatório em {ARQUIVO_RELATORIO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
