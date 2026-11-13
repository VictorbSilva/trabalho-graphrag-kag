"""API HTTP do sistema de perguntas e respostas (issue #24, PE1).

Rodar na raiz do repositório:
    uvicorn src.api.app:app --reload --port 8000

Rotas:
    GET  /saude      verifica se a API está no ar
    POST /perguntar  recebe {"pergunta": "...", "modo": "graphrag" | "vetorial"}
                     e devolve o objeto do contrato da resposta
"""

import asyncio
import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.api import config
from src.api.servico import Responder, carregar_responder

log = logging.getLogger("api")

MODOS = ("graphrag", "vetorial")
TAMANHO_MAXIMO_PERGUNTA = 1000


class PedidoPergunta(BaseModel):
    pergunta: str = Field(description="Pergunta em linguagem natural.")
    modo: Literal["graphrag", "vetorial"] = Field(
        default="graphrag", description="Estratégia de recuperação."
    )

    @field_validator("pergunta")
    @classmethod
    def pergunta_preenchida(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("O campo 'pergunta' não pode ser vazio.")
        if len(valor) > TAMANHO_MAXIMO_PERGUNTA:
            raise ValueError(
                f"O campo 'pergunta' aceita no máximo {TAMANHO_MAXIMO_PERGUNTA} caracteres."
            )
        return valor


def _mensagem_de_validacao(erro: dict) -> str:
    """Traduz um erro do pydantic numa mensagem legível em português."""
    campo = next((str(p) for p in reversed(erro.get("loc", ())) if p != "body"), None)
    tipo = erro.get("type", "")
    if tipo == "json_invalid":
        return "O corpo da requisição não é um JSON válido."
    if campo is None or tipo == "model_attributes_type":
        return "Envie um JSON com os campos 'pergunta' e 'modo'."
    if tipo == "missing":
        return f"O campo '{campo}' é obrigatório."
    if campo == "modo":
        return "O campo 'modo' deve ser 'graphrag' ou 'vetorial'."
    if tipo == "value_error":
        return erro["msg"].removeprefix("Value error, ")
    if tipo == "string_type":
        return f"O campo '{campo}' deve ser um texto."
    return f"Valor inválido no campo '{campo}'."


def criar_app(responder: Responder | None = None, timeout_s: float | None = None) -> FastAPI:
    """Monta a aplicação. Os parâmetros permitem trocar a recuperação nos testes."""
    app = FastAPI(
        title="GraphRAG e KAG",
        description="Perguntas e respostas sobre o grafo de conhecimento no Neo4j.",
        version="0.1.0",
    )
    app.state.responder = responder or carregar_responder()
    app.state.timeout_s = timeout_s if timeout_s is not None else config.TIMEOUT_S

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGENS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def erro_de_validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
        mensagens = list(dict.fromkeys(_mensagem_de_validacao(e) for e in exc.errors()))
        return JSONResponse(status_code=422, content={"erro": " ".join(mensagens)})

    @app.get("/saude")
    async def saude() -> dict:
        return {"status": "ok", "fonte": config.FONTE}

    @app.post("/perguntar")
    async def perguntar(pedido: PedidoPergunta, request: Request):
        estado = request.app.state
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(estado.responder, pedido.pergunta, pedido.modo),
                timeout=estado.timeout_s,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "erro": f"A recuperação não respondeu em {estado.timeout_s:g} segundos. "
                    "Tente de novo ou reformule a pergunta."
                },
            )
        except Exception:
            # O detalhe vai para o log do servidor, nunca para o cliente.
            log.exception("Falha ao responder a pergunta: %r", pedido.pergunta)
            return JSONResponse(
                status_code=500,
                content={"erro": "Erro interno ao processar a pergunta. Consulte o log da API."},
            )

    return app


app = criar_app()
