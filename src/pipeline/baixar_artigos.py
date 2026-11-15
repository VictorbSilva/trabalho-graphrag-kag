"""PA1: baixa o texto dos artigos da Wikipédia em português e gera o manifesto.

Uso, na raiz do repositório:

    python src/pipeline/baixar_artigos.py            # baixa só o que falta (retoma de onde parou)
    python src/pipeline/baixar_artigos.py --forcar   # baixa todos de novo

Lê data/lista_artigos.txt e grava:
    data/bruto/<slug>.txt        texto puro do artigo, sem marcação wiki (títulos de seção em linha própria)
    data/bruto/manifesto.json    título, URL, revisão, data de acesso, licença e nº de palavras

Só usa a biblioteca padrão do Python.
O manifesto nunca perde um artigo já baixado: se um pedido falha, o registro anterior é mantido,
e no fim o script confere se cada .txt tem registro no manifesto e vice-versa.
O texto da Wikipédia é CC BY-SA 4.0: o manifesto guarda o que é preciso para o crédito.
"""

import argparse
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
MANIFESTO = SAIDA / "manifesto.json"
API = "https://pt.wikipedia.org/w/api.php"

# A Wikipédia pede um User-Agent com contato.
USER_AGENT = "trabalho-graphrag-kag/0.1 (trabalho academico; contato: github.com/Extremezi)"
LICENCA = "CC BY-SA 4.0"
PAUSA_ENTRE_PEDIDOS = 1.0  # segundos, para ser gentil com o servidor
TENTATIVAS = 5
ERROS_PARA_REPETIR = (429, 500, 502, 503, 504)

# Seções sem conteúdo útil para extração (listas de referências e links).
SECOES_EXATAS = {"ver também", "ver tambem", "leitura adicional", "fontes", "links externos"}
SECOES_PREFIXOS = ("referências", "referencias", "notas", "ligações externas", "ligacoes externas", "bibliografia")
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


def secao_ignorada(nome: str) -> bool:
    nome = nome.lower()
    return nome in SECOES_EXATAS or nome.startswith(SECOES_PREFIXOS)


def limpar_texto(texto: str) -> str:
    """Tira a marcação de seção (== Título ==) e as seções de referências, notas e links.

    Os títulos ficam como linhas próprias, sem marcação. O texto restante já vem puro da API.
    """
    saida, nivel_ignorado = [], None
    for linha in texto.splitlines():
        achou = TITULO_SECAO.match(linha.strip())
        if achou:
            nivel, nome = len(achou.group(1)), achou.group(2)
            if nivel_ignorado is not None and nivel > nivel_ignorado:
                continue  # subseção de uma seção ignorada
            nivel_ignorado = nivel if secao_ignorada(nome) else None
            if nivel_ignorado is None:
                saida.extend(["", nome, ""])
        elif nivel_ignorado is None:
            saida.append(linha.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(saida)).strip()


def ler_lista(caminho: Path) -> list[str]:
    titulos = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            titulos.append(linha)
    return titulos


def carregar_manifesto_anterior() -> dict[str, dict]:
    """Registros já existentes, indexados pelo título pedido na lista."""
    if not MANIFESTO.exists():
        return {}
    try:
        registros = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return {r["titulo_pedido"]: r for r in registros if "titulo_pedido" in r}


def buscar(titulo: str) -> dict | None:
    """Pede à API o texto completo do artigo. Devolve None se a página não existe.

    Erros temporários (limite de requisições, servidor ocupado) são repetidos com espera.
    """
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
    url = f"{API}?{urlencode(params)}"
    for tentativa in range(1, TENTATIVAS + 1):
        espera = 5 * 2 ** (tentativa - 1)
        try:
            pedido = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(pedido, timeout=30) as resposta:
                dados = json.load(resposta)
            if "query" not in dados:
                raise RuntimeError(f"resposta inesperada da API: {str(dados)[:120]}")
            pagina = dados["query"]["pages"][0]
            return None if pagina.get("missing") else pagina
        except HTTPError as erro:
            if erro.code not in ERROS_PARA_REPETIR or tentativa == TENTATIVAS:
                raise RuntimeError(f"HTTP {erro.code} ao buscar '{titulo}'") from erro
            retry = erro.headers.get("Retry-After", "")
            espera = int(retry) if retry.isdigit() else espera
            print(f"(HTTP {erro.code}, espera {min(espera, 60)}s) ", end="", flush=True)
        except (URLError, TimeoutError, ValueError) as erro:
            if tentativa == TENTATIVAS:
                raise RuntimeError(f"falha ao buscar '{titulo}': {erro}") from erro
        time.sleep(min(espera, 60))


def verificar_consistencia(manifesto: list[dict]) -> bool:
    """Cada .txt de data/bruto/ precisa ter registro no manifesto, e cada registro precisa de .txt."""
    ids = {m["id"] for m in manifesto}
    arquivos = {p.stem for p in SAIDA.glob("*.txt")}
    sem_registro, sem_arquivo = sorted(arquivos - ids), sorted(ids - arquivos)
    if sem_registro:
        print(f"\nATENÇÃO: {len(sem_registro)} arquivo(s) em data/bruto/ SEM registro no manifesto "
              f"(falta crédito e licença): {', '.join(sem_registro)}")
        print("  Rode o script de novo; se continuar, apague o .txt ou corrija o título em data/lista_artigos.txt.")
    if sem_arquivo:
        print(f"\nATENÇÃO: {len(sem_arquivo)} registro(s) do manifesto SEM arquivo: {', '.join(sem_arquivo)}")
    return not (sem_registro or sem_arquivo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa os artigos da lista e gera o manifesto.")
    parser.add_argument("--forcar", action="store_true", help="baixa todos de novo, mesmo os já registrados")
    args = parser.parse_args()

    titulos = ler_lista(LISTA)
    SAIDA.mkdir(parents=True, exist_ok=True)
    anteriores = carregar_manifesto_anterior()
    hoje = date.today().isoformat()
    manifesto, problemas, slugs_vistos = [], [], {}

    def manter(antiga: dict) -> None:
        manifesto.append(antiga)
        slugs_vistos[antiga["id"]] = antiga["titulo"]

    for i, titulo in enumerate(titulos, start=1):
        print(f"[{i}/{len(titulos)}] {titulo} ... ", end="", flush=True)
        antiga = anteriores.get(titulo)
        arquivo_antigo_existe = bool(antiga) and (RAIZ / antiga["arquivo"]).exists()

        if arquivo_antigo_existe and not args.forcar:
            manter(antiga)
            print("já baixado")
            continue

        try:
            pagina = buscar(titulo)
        except RuntimeError as erro:
            if arquivo_antigo_existe:
                manter(antiga)
                print("ERRO (mantido o registro anterior)")
            else:
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

        texto = limpar_texto(pagina["extract"])
        arquivo = SAIDA / f"{slug}.txt"
        arquivo.write_text(texto + "\n", encoding="utf-8")

        revisao = pagina["lastrevid"]
        manter({
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
        time.sleep(PAUSA_ENTRE_PEDIDOS)

    MANIFESTO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{len(manifesto)} de {len(titulos)} artigos no manifesto ({MANIFESTO})")
    if manifesto:
        maiores = sorted(manifesto, key=lambda m: m["palavras"], reverse=True)[:5]
        print("Maiores (para decidir o corte no chunking):")
        for m in maiores:
            print(f"  {m['palavras']:>6}  {m['titulo']}")
    if problemas:
        print(f"\n{len(problemas)} título(s) com problema:")
        for titulo, motivo in problemas:
            print(f"  - {titulo}: {motivo}")
    consistente = verificar_consistencia(manifesto)
    return 0 if consistente and not problemas else 1


if __name__ == "__main__":
    sys.exit(main())
