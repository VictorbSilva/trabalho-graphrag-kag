"""PA1: baixa o texto dos artigos da Wikipédia em português e gera o manifesto.

Uso, na raiz do repositório:

    python src/pipeline/baixar_artigos.py

Lê data/lista_artigos.txt e grava:
    data/bruto/<slug>.txt        texto puro do artigo, sem marcação wiki (títulos de seção em linha própria)
    data/bruto/manifesto.json    título, URL, revisão, data de acesso, licença e nº de palavras

Só usa a biblioteca padrão do Python. Rodar de novo refaz tudo (idempotente).
O texto da Wikipédia é CC BY-SA 4.0: o manifesto guarda o que é preciso para o crédito.
"""

import json
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[2]
LISTA = RAIZ / "data" / "lista_artigos.txt"
SAIDA = RAIZ / "data" / "bruto"
API = "https://pt.wikipedia.org/w/api.php"

# A Wikipédia pede um User-Agent com contato. TROQUE pelo seu e-mail ou usuário do GitHub.
USER_AGENT = "trabalho-graphrag-kag/0.1 (trabalho academico; contato: github.com/Extremezi)"
LICENCA = "CC BY-SA 4.0"
PAUSA_ENTRE_PEDIDOS = 0.5  # segundos, para ser gentil com o servidor
TENTATIVAS = 3

# Seções sem conteúdo útil para extração (listas de referências e links).
SECOES_IGNORADAS = {
    "referências", "referencias", "ligações externas", "ligacoes externas",
    "ver também", "ver tambem", "notas", "bibliografia", "leitura adicional",
    "fontes", "links externos",
}
TITULO_SECAO = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")


def gerar_slug(titulo: str) -> str:
    """Id do documento: minúsculas, sem acento, sem a desambiguação entre parênteses.

    'Dennis Ritchie' -> 'dennis_ritchie'; 'C++' -> 'c_mais_mais';
    'Java (linguagem de programação)' -> 'java'.
    """
    titulo = re.sub(r"\s*\(.*?\)", "", titulo)
    titulo = titulo.replace("+", " mais ")
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def limpar_texto(texto: str) -> str:
    """Tira a marcação de seção (== Título ==) e as seções de referências e links.

    Os títulos ficam como linhas próprias, sem marcação. O texto restante já vem puro da API.
    """
    saida, ignorando = [], False
    for linha in texto.splitlines():
        achou = TITULO_SECAO.match(linha.strip())
        if achou:
            nivel, nome = len(achou.group(1)), achou.group(2)
            if nivel == 2:
                ignorando = nome.lower() in SECOES_IGNORADAS
            if not ignorando:
                saida.extend(["", nome, ""])
        elif not ignorando:
            saida.append(linha.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(saida)).strip()


def ler_lista(caminho: Path) -> list[str]:
    titulos = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            titulos.append(linha)
    return titulos


def buscar(titulo: str) -> dict | None:
    """Pede à API o texto completo do artigo. Devolve None se a página não existe."""
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "prop": "extracts|info|pageprops",
        "explaintext": "1",
        "exsectionformat": "wiki",
        "inprop": "url",
        "ppprop": "disambiguation",
        "titles": titulo,
    }
    pedido = Request(f"{API}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with urlopen(pedido, timeout=30) as resposta:
                dados = json.load(resposta)
            pagina = dados["query"]["pages"][0]
            return None if pagina.get("missing") else pagina
        except (HTTPError, URLError, TimeoutError) as erro:
            if tentativa == TENTATIVAS:
                raise RuntimeError(f"falha ao buscar '{titulo}': {erro}") from erro
            time.sleep(2 * tentativa)


def main() -> int:
    titulos = ler_lista(LISTA)
    SAIDA.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    manifesto, problemas, slugs_vistos = [], [], {}

    for i, titulo in enumerate(titulos, start=1):
        print(f"[{i}/{len(titulos)}] {titulo} ... ", end="", flush=True)
        try:
            pagina = buscar(titulo)
        except RuntimeError as erro:
            print("ERRO")
            problemas.append((titulo, str(erro)))
            continue

        if pagina is None:
            print("NÃO EXISTE")
            problemas.append((titulo, "página não existe: confira o título na Wikipédia"))
            continue
        if "disambiguation" in pagina.get("pageprops", {}):
            print("DESAMBIGUAÇÃO")
            problemas.append((titulo, "é página de desambiguação: use o título completo, ex.: 'X (linguagem de programação)'"))
            continue

        slug = gerar_slug(pagina["title"])
        if slug in slugs_vistos:
            print("SLUG REPETIDO")
            problemas.append((titulo, f"slug '{slug}' já usado por '{slugs_vistos[slug]}'"))
            continue
        slugs_vistos[slug] = pagina["title"]

        texto = limpar_texto(pagina["extract"])
        arquivo = SAIDA / f"{slug}.txt"
        arquivo.write_text(texto + "\n", encoding="utf-8")

        revisao = pagina["lastrevid"]
        manifesto.append({
            "id": slug,
            "titulo": pagina["title"],
            "titulo_pedido": titulo,
            "url": pagina["fullurl"],
            "url_revisao": f"https://pt.wikipedia.org/w/index.php?title={pagina['title'].replace(' ', '_')}&oldid={revisao}",
            "revisao": revisao,
            "data_acesso": hoje,
            "licenca": LICENCA,
            "palavras": len(texto.split()),
            "arquivo": f"data/bruto/{arquivo.name}",
        })
        print(f"ok ({manifesto[-1]['palavras']} palavras)")
        time.sleep(3)

    (SAIDA / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\n{len(manifesto)} artigos salvos em {SAIDA}")
    if manifesto:
        maiores = sorted(manifesto, key=lambda m: m["palavras"], reverse=True)[:5]
        print("Maiores (para decidir o corte no chunking):")
        for m in maiores:
            print(f"  {m['palavras']:>6}  {m['titulo']}")
    if problemas:
        print(f"\n{len(problemas)} título(s) com problema:")
        for titulo, motivo in problemas:
            print(f"  - {titulo}: {motivo}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
