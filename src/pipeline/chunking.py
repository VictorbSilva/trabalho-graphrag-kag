"""PA2: divide cada artigo de data/bruto/ em trechos (chunks) para o grafo e para os embeddings.

Uso, na raiz do repositório:

    python src/pipeline/chunking.py
    python src/pipeline/chunking.py --max-chunks 40   # opcional: limita os trechos por artigo

Lê data/bruto/manifesto.json e grava um arquivo por artigo em data/processado/chunks/<id>.json:

    {"documento": {"id": "...", "title": "...", "source": "<URL do artigo>"},
     "chunks": [{"id": "<id>#0", "index": 0, "text": "..."}, ...]}

É o formato de documento e chunks do contrato (neo4j/dominio.json, "arquivo_por_artigo").
A extração (PA3) acrescenta entidades e relações a esse mesmo formato. Sem embeddings:
quem calcula é o ingestor.

Como os trechos são cortados:
- Nunca no meio de uma frase (só uma frase maior que o limite é quebrada, entre palavras).
- Até TAMANHO_MAXIMO caracteres: o modelo de embeddings de 384 dimensões lê cerca de 128 tokens,
  e o que passa disso é ignorado na busca vetorial.
- A última frase de cada trecho se repete no começo do seguinte (sobreposição de uma frase).
- Título de seção fica colado ao primeiro parágrafo dele.
"""

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MANIFESTO = RAIZ / "data" / "bruto" / "manifesto.json"
ENTRADA = RAIZ / "data" / "bruto"
SAIDA = RAIZ / "data" / "processado" / "chunks"

TAMANHO_MAXIMO = 450       # caracteres por trecho (conferir com o tokenizer quando o V1 fixar o modelo)
SOBREPOSICAO_MAXIMA = 150  # a frase repetida do trecho anterior não pode passar disso

FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\"«(\[])")  # sem dígitos: não corta 'c. 12 de outubro'


def e_titulo(paragrafo: str) -> bool:
    """Linha curta sem pontuação final, como 'Biografia' ou 'Prêmios e honrarias'."""
    return len(paragrafo) <= 60 and "\n" not in paragrafo and not paragrafo.endswith((".", "!", "?", ":", ";", ","))


def juntar_titulos(paragrafos: list[str]) -> list[str]:
    """Cola cada título ao parágrafo seguinte. Título sem parágrafo depois (seção vazia) é descartado."""
    juntos, pendentes = [], []
    for paragrafo in paragrafos:
        if e_titulo(paragrafo):
            pendentes.append(paragrafo)
        else:
            juntos.append("\n".join(pendentes + [paragrafo]))
            pendentes = []
    return juntos


def quebrar_frase_longa(frase: str, tamanho_maximo: int) -> list[str]:
    """Frase maior que o limite: quebra entre palavras, nunca no meio de uma."""
    if len(frase) <= tamanho_maximo:
        return [frase]
    partes, atual = [], ""
    for palavra in frase.split(" "):
        if atual and len(atual) + 1 + len(palavra) > tamanho_maximo:
            partes.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}" if atual else palavra
    if atual:
        partes.append(atual)
    return partes


def dividir_em_trechos(texto: str, tamanho_maximo: int = TAMANHO_MAXIMO,
                       sobreposicao_maxima: int = SOBREPOSICAO_MAXIMA) -> list[str]:
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    unidades = []
    for paragrafo in juntar_titulos(paragrafos):
        for frase in FIM_DE_FRASE.split(paragrafo):
            unidades.extend(quebrar_frase_longa(frase.strip(), tamanho_maximo))

    trechos, atual = [], []
    for unidade in unidades:
        if atual and len(" ".join(atual + [unidade])) > tamanho_maximo:
            trechos.append(" ".join(atual))
            ultima = atual[-1]
            cabe = len(ultima) <= sobreposicao_maxima and len(ultima) + 1 + len(unidade) <= tamanho_maximo
            atual = [ultima] if cabe else []
        atual.append(unidade)
    if atual:
        trechos.append(" ".join(atual))
    return trechos


def main() -> int:
    parser = argparse.ArgumentParser(description="Divide os artigos de data/bruto/ em trechos.")
    parser.add_argument("--max-chunks", type=int, default=None, help="máximo de trechos por artigo (padrão: sem limite)")
    args = parser.parse_args()

    if not MANIFESTO.exists():
        print(f"Manifesto não encontrado: {MANIFESTO}. Rode antes: python src/pipeline/baixar_artigos.py")
        return 1
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))

    SAIDA.mkdir(parents=True, exist_ok=True)
    for antigo in SAIDA.glob("*.json"):  # refaz tudo: não deixa sobra de execuções anteriores
        antigo.unlink()

    problemas, contagens, maior = [], [], 0
    for registro in manifesto:
        caminho = RAIZ / registro["arquivo"]
        if not caminho.exists():
            problemas.append(f"{registro['id']}: arquivo {registro['arquivo']} não existe")
            continue
        trechos = dividir_em_trechos(caminho.read_text(encoding="utf-8"))
        if args.max_chunks:
            trechos = trechos[: args.max_chunks]
        if not trechos:
            problemas.append(f"{registro['id']}: nenhum trecho gerado (arquivo vazio?)")
            continue

        saida = {
            "documento": {"id": registro["id"], "title": registro["titulo"], "source": registro["url"]},
            "chunks": [{"id": f"{registro['id']}#{i}", "index": i, "text": t} for i, t in enumerate(trechos)],
        }
        (SAIDA / f"{registro['id']}.json").write_text(
            json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        contagens.append((registro["id"], len(trechos)))
        maior = max(maior, max(len(t) for t in trechos))

    sem_registro = sorted({p.stem for p in ENTRADA.glob("*.txt")} - {r["id"] for r in manifesto})
    if sem_registro:
        problemas.append(f"em data/bruto/ sem registro no manifesto (ignorados): {', '.join(sem_registro)}")

    total = sum(n for _, n in contagens)
    print(f"{len(contagens)} artigos, {total} trechos em {SAIDA} (maior trecho: {maior} caracteres)")
    for nome, n in sorted(contagens, key=lambda x: -x[1])[:5]:
        print(f"  {n:>4} trechos  {nome}")
    if problemas:
        print("\nProblemas:")
        for p in problemas:
            print(f"  - {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
