"""Exporta a avaliação RAG vetorial vs GraphRAG para o Hugging Face Datasets.

Lê as 15 perguntas de data/avaliacao/perguntas.json e as respostas e classificações
das duas rodadas (semente e completo) e grava em hf_dataset/:

- perguntas.jsonl: uma linha por pergunta, com o gabarito;
- respostas.jsonl: uma linha por resposta (15 perguntas x 2 modos x 2 bancos = 60),
  com a classificação manual e o contexto que o LLM recebeu (trechos e caminhos);
- README.md: o dataset card, copiado de data/avaliacao/hf/README.md.

    python -m src.avaliacao.exportar_hf
    python -m src.avaliacao.exportar_hf --pasta outra_pasta

Não chama o responder(), o banco nem o LLM: só reorganiza arquivos que já estão no
repositório. Ficam de fora o subgrafo (pagerank e comunidade), a Cypher, a confiança,
os nós consultados e os avisos.
"""

import argparse
import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PASTA_AVALIACAO = RAIZ / "data" / "avaliacao"
ARQUIVO_PERGUNTAS = PASTA_AVALIACAO / "perguntas.json"
ARQUIVO_CARD = PASTA_AVALIACAO / "hf" / "README.md"
PASTA_SAIDA = RAIZ / "hf_dataset"

# banco -> (respostas.json, classificacao.json). As mesmas da avaliação, ver comparar.caminhos().
RODADAS = {
    "semente": (
        PASTA_AVALIACAO / "resultados" / "respostas.json",
        PASTA_AVALIACAO / "classificacao.json",
    ),
    "completo": (
        PASTA_AVALIACAO / "resultados" / "completo" / "respostas.json",
        PASTA_AVALIACAO / "resultados" / "completo" / "classificacao.json",
    ),
}

# O respostas.json não guarda o modelo. Fonte: seção Avaliação de docs/artigo/artigo.tex
# (Abacus RouteLLM, temperatura 0 nas duas rodadas).
MODELO_LLM = {
    "semente": "claude-opus-5-5-fast",
    "completo": "claude-haiku-5-5",
}

CLASSES = ("correta", "incompleta", "alucinada")

CAMPOS_PERGUNTA = (
    "id",
    "pergunta",
    "tipo",
    "saltos",
    "resposta_esperada",
    "caminho_esperado",
    "evidencias",
)
CAMPOS_RESPOSTA = (
    "id_pergunta",
    "banco",
    "modo",
    "modelo_llm",
    "resposta",
    "classificacao",
    "trechos",
    "caminhos",
)
CAMPOS_TRECHO = ("id", "chunk_id", "documento", "url", "trecho", "score")
CAMPOS_CAMINHO = ("id", "nos", "relacoes", "fontes")


def _ler_json(caminho: Path):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def _so(campos: tuple, registro: dict) -> dict:
    return {campo: registro[campo] for campo in campos}


def exportar_perguntas(caminho: Path = ARQUIVO_PERGUNTAS) -> list[dict]:
    """As 15 perguntas só com os campos de CAMPOS_PERGUNTA, na ordem do arquivo."""
    return [_so(CAMPOS_PERGUNTA, p) for p in _ler_json(caminho)["perguntas"]]


def exportar_respostas(
    rodadas: dict | None = None, caminho_perguntas: Path = ARQUIVO_PERGUNTAS
) -> list[dict]:
    """Uma linha por resposta de cada rodada, com a classe manual da rodada.

    Levanta ValueError se uma resposta apontar para uma pergunta que não existe,
    se tiver erro de execução, se não tiver classe ou se a classe não for uma de CLASSES.
    """
    rodadas = rodadas or RODADAS
    ids = {p["id"] for p in _ler_json(caminho_perguntas)["perguntas"]}
    linhas = []
    for banco, (arquivo_respostas, arquivo_classes) in rodadas.items():
        classes = _ler_json(arquivo_classes)
        for registro in _ler_json(arquivo_respostas):
            id_pergunta, modo = registro["id"], registro["modo"]
            onde = f"{banco} {id_pergunta} {modo}"
            if id_pergunta not in ids:
                raise ValueError(f"Resposta {onde} aponta para uma pergunta que não existe: {id_pergunta}")
            if registro.get("erro") or registro.get("resposta") is None:
                raise ValueError(f"Resposta {onde} tem erro de execução: {registro.get('erro')}")
            classe = classes.get(id_pergunta, {}).get(modo)
            if classe is None:
                raise ValueError(f"Resposta {onde} sem classificação manual")
            if classe not in CLASSES:
                raise ValueError(f"Classe inválida em {onde}: {classe!r}")
            resposta = registro["resposta"]
            linhas.append({
                "id_pergunta": id_pergunta,
                "banco": banco,
                "modo": modo,
                "modelo_llm": MODELO_LLM[banco],
                "resposta": resposta["resposta"],
                "classificacao": classe,
                "trechos": [_so(CAMPOS_TRECHO, f) for f in resposta["fontes"]],
                "caminhos": [_so(CAMPOS_CAMINHO, c) for c in resposta["caminhos"]],
            })
    return linhas


def _gravar_jsonl(registros: list[dict], caminho: Path) -> None:
    caminho.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in registros), encoding="utf-8"
    )


def exportar(pasta: Path = PASTA_SAIDA) -> dict:
    """Grava perguntas.jsonl, respostas.jsonl e README.md em pasta e devolve os caminhos."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "perguntas": pasta / "perguntas.jsonl",
        "respostas": pasta / "respostas.jsonl",
        "card": pasta / "README.md",
    }
    _gravar_jsonl(exportar_perguntas(), arquivos["perguntas"])
    _gravar_jsonl(exportar_respostas(), arquivos["respostas"])
    shutil.copyfile(ARQUIVO_CARD, arquivos["card"])
    return arquivos


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Exporta a avaliação para o Hugging Face Datasets.")
    parser.add_argument("--pasta", type=Path, default=PASTA_SAIDA, help="pasta de saída (padrão: hf_dataset/)")
    args = parser.parse_args(argv)
    for nome, caminho in exportar(args.pasta).items():
        print(f"{nome}: {caminho}")


if __name__ == "__main__":
    main()
