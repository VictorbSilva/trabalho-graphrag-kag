"""Cliente mínimo da API do Groq (compatível com a da OpenAI), só com a biblioteca padrão.

A chave vem de GROQ_API_KEY, lida do .env na raiz do projeto (que não vai para o Git).
"""

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[2]
USER_AGENT = "trabalho-graphrag-kag/0.1 (trabalho academico; github.com/Extremezi)"


class ErroGroq(Exception):
    def __init__(self, status: int, mensagem: str, cabecalhos: dict[str, str]):
        super().__init__(f"HTTP {status}: {mensagem}")
        self.status = status
        self.cabecalhos = cabecalhos


def carregar_env(caminho: Path = RAIZ / ".env") -> None:
    """Lê o .env sem bibliotecas externas. Variáveis já definidas no ambiente têm prioridade."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


def chave_api() -> str:
    carregar_env()
    chave = os.getenv("GROQ_API_KEY", "").strip()
    if not chave:
        raise RuntimeError("GROQ_API_KEY vazia. Preencha no seu .env (nunca no .env.example).")
    return chave


def base_url() -> str:
    return os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


def requisitar(caminho: str, corpo: dict | None = None, timeout: int = 60) -> tuple[dict, dict[str, str]]:
    """GET (sem corpo) ou POST (com corpo). Devolve (json, cabeçalhos em minúsculas).

    Em erro HTTP levanta ErroGroq, com os cabeçalhos (inclui retry-after e x-ratelimit-*).
    """
    cabecalhos = {
        "Authorization": f"Bearer {chave_api()}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode("utf-8")
        cabecalhos["Content-Type"] = "application/json"
    pedido = Request(f"{base_url()}{caminho}", data=dados, headers=cabecalhos)
    try:
        with urlopen(pedido, timeout=timeout) as resposta:
            return json.load(resposta), {k.lower(): v for k, v in resposta.headers.items()}
    except HTTPError as erro:
        texto = erro.read().decode("utf-8", errors="replace")[:300]
        raise ErroGroq(erro.code, texto, {k.lower(): v for k, v in erro.headers.items()}) from erro
    except URLError as erro:
        raise RuntimeError(f"falha de rede ao falar com o Groq: {erro.reason}") from erro


def listar_modelos() -> list[dict]:
    dados, _ = requisitar("/models")
    return sorted(dados.get("data", []), key=lambda m: m["id"])


def conversar(modelo: str, mensagens: list[dict], **opcoes) -> tuple[dict, dict[str, str]]:
    corpo = {"model": modelo, "messages": mensagens, "temperature": 0, **opcoes}
    return requisitar("/chat/completions", corpo)


def limites_dos_cabecalhos(cabecalhos: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in sorted(cabecalhos.items()) if k.startswith("x-ratelimit") or k == "retry-after"}


def esperar(segundos: float) -> None:
    time.sleep(segundos)
