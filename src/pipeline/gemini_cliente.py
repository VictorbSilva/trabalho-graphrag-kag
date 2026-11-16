"""Cliente HTTP do Gemini para a extração PA3/PA5, sem dependências extras."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class ErroGemini(Exception):
    def __init__(self, status: int, mensagem: str, espera: float | None = None):
        self.status = status
        self.espera = espera
        super().__init__(f"HTTP {status}: {mensagem}")


def _espera(headers, dados) -> float | None:
    valor = headers.get("Retry-After") or headers.get("retry-after")
    if valor:
        try:
            return float(valor)
        except ValueError:
            pass
    for detalhe in (dados.get("error") or {}).get("details", []):
        valor = detalhe.get("retryDelay")
        if isinstance(valor, str) and valor.endswith("s"):
            try:
                return float(valor[:-1])
            except ValueError:
                pass
    return None


def conversar_gemini(modelo: str, mensagens: list[dict], max_tokens: int = 3000) -> tuple[str, int]:
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        raise ErroGemini(401, "GEMINI_API_KEY não configurada no .env")
    instrucao = "\n\n".join(m["content"] for m in mensagens if m["role"] == "system")
    usuario = "\n\n".join(m["content"] for m in mensagens if m["role"] != "system")
    modelo = modelo.removeprefix("models/")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", modelo):
        raise ValueError("Nome de modelo Gemini inválido")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(modelo)}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": instrucao}]},
        "contents": [{"role": "user", "parts": [{"text": usuario}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": max_tokens,
            "temperature": 0,
        },
    }
    if modelo.startswith("gemini-2.5-flash"):
        payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    req = Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                  headers={"Content-Type": "application/json", "x-goog-api-key": chave}, method="POST")
    try:
        with urlopen(req, timeout=180) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except HTTPError as erro:
        bruto = erro.read().decode("utf-8", errors="replace")
        try:
            dados_erro = json.loads(bruto)
            mensagem = (dados_erro.get("error") or {}).get("message", bruto[:500])
        except ValueError:
            dados_erro, mensagem = {}, bruto[:500]
        raise ErroGemini(erro.code, mensagem, _espera(erro.headers, dados_erro)) from erro
    except TimeoutError as erro:
        raise ErroGemini(0, "Tempo limite de 180 segundos excedido ao aguardar o Gemini") from erro
    except URLError as erro:
        raise ErroGemini(0, f"Falha de rede: {erro.reason}") from erro
    try:
        partes = dados["candidates"][0]["content"]["parts"]
        texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
        if not texto.strip():
            raise ValueError("Resposta vazia")
    except (KeyError, IndexError, ValueError) as erro:
        raise ErroGemini(200, f"Resposta sem texto JSON: {str(dados)[:500]}") from erro
    usados = int((dados.get("usageMetadata") or {}).get("totalTokenCount") or 0)
    return texto, usados
