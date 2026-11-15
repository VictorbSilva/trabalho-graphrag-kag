"""Confere a extração contra as relações que as perguntas de avaliação esperam (PA5).

Uso, na raiz do repositório:

    python src/pipeline/conferir_extracao.py                 # lê data/processado/extraido/
    python src/pipeline/conferir_extracao.py data/processado # lê o resultado final da resolução

Cada pergunta de data/avaliacao/perguntas.json traz o caminho do grafo que a responde
(`caminho_esperado`). O script diz quantas dessas relações a extração encontrou. É uma medida
de cobertura (recall) das perguntas; a precisão continua sendo conferida à mão em uma amostra.
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PERGUNTAS = RAIZ / "data" / "avaliacao" / "perguntas.json"

# Ids que a resolução de entidades pode escolher de formas diferentes (ver o campo `observacao`
# das perguntas). Qualquer um do grupo vale.
EQUIVALENTES = [
    {"organizacao:cern", "organizacao:organizacao_europeia_para_a_investigacao_nuclear"},
    {"organizacao:xerox_parc", "organizacao:xerox"},
    {"tecnologia:simula", "tecnologia:simula_67"},
]


def grupo(ident: str) -> set[str]:
    for equivalentes in EQUIVALENTES:
        if ident in equivalentes:
            return equivalentes
    return {ident}


def carregar_relacoes(pasta: Path) -> set[tuple[str, str, str]]:
    encontradas = set()
    for arquivo in sorted(pasta.glob("*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for r in dados.get("relacoes", []):
            encontradas.add((r["origem"], r["tipo"], r["destino"]))
    return encontradas


def main(argv: list[str]) -> int:
    pasta = Path(argv[1]) if len(argv) > 1 else RAIZ / "data" / "processado" / "extraido"
    if not pasta.is_absolute():
        pasta = RAIZ / pasta
    if not pasta.exists() or not list(pasta.glob("*.json")):
        print(f"Nada em {pasta}. Rode antes: python src/pipeline/extracao.py")
        return 1

    encontradas = carregar_relacoes(pasta)
    perguntas = json.loads(PERGUNTAS.read_text(encoding="utf-8"))["perguntas"]
    esperadas: dict[tuple, list[str]] = {}
    for p in perguntas:
        for passo in p["caminho_esperado"]:
            esperadas.setdefault((passo["origem"], passo["tipo"], passo["destino"]), []).append(p["id"])

    achadas, faltando = [], []
    for (origem, tipo, destino), ids in sorted(esperadas.items()):
        existe = any((o, tipo, d) in encontradas for o in grupo(origem) for d in grupo(destino))
        (achadas if existe else faltando).append(((origem, tipo, destino), ids))

    print(f"{len(encontradas)} relações extraídas em {len(list(pasta.glob('*.json')))} artigos.")
    print(f"Relações esperadas pelas perguntas: {len(achadas)} de {len(esperadas)} encontradas "
          f"({len(achadas) / len(esperadas):.0%}).")
    if faltando:
        print("\nFaltando:")
        for (o, t, d), ids in faltando:
            print(f"  {o} -{t}-> {d}   [{', '.join(ids)}]")

    por_pergunta = {}
    for p in perguntas:
        passos = [(s["origem"], s["tipo"], s["destino"]) for s in p["caminho_esperado"]]
        if passos:
            ok = sum(any((o, t, d) in encontradas for o in grupo(a) for d in grupo(c)) for a, t, c in passos)
            por_pergunta[p["id"]] = (ok, len(passos))
    completas = [i for i, (ok, total) in por_pergunta.items() if ok == total]
    print(f"\nPerguntas com o caminho inteiro no grafo: {len(completas)} de {len(por_pergunta)}")
    print("  " + ", ".join(f"{i} ({ok}/{total})" for i, (ok, total) in por_pergunta.items()))
    return 0 if not faltando else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
